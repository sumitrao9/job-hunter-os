/**
 * NS - Electron main process.
 *
 * The frontend package is an ES module package ("type": "module"), so this
 * file is loaded as ESM. `require`, `__dirname` and `__filename` are therefore
 * unavailable; the equivalents are derived from `import.meta.url` below.
 *
 * Loading strategy (never uses file://):
 *   development - Vite dev server on :5173, which proxies /api to the backend.
 *   production  - the FastAPI backend serves the built frontend and /api from
 *                 a single origin, so no CORS or file-origin issues occur.
 *
 * Mode selection: a packaged app always uses production. An unpackaged app
 * defaults to development, but JOB_HUNTER_DEV=0 forces the production path and
 * JOB_HUNTER_DEV=1 forces the dev server (start-mac.sh sets this explicitly).
 */

import { app, BrowserWindow, Menu, dialog, ipcMain, shell } from 'electron'
import { spawn } from 'node:child_process'
import fs from 'node:fs'
import http from 'node:http'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const HERE = path.dirname(fileURLToPath(import.meta.url))
const FRONTEND_DIR = path.resolve(HERE, '..')
const PROJECT_ROOT = path.resolve(HERE, '..', '..')
const BACKEND_DIR = path.join(PROJECT_ROOT, 'backend')

const IS_MAC = process.platform === 'darwin'
const IS_WIN = process.platform === 'win32'

const DEV =
  process.env.JOB_HUNTER_DEV === '1' ||
  (process.env.JOB_HUNTER_DEV !== '0' && !app.isPackaged)
const HOST = '127.0.0.1'
const PORT = Number(process.env.JOB_HUNTER_PORT) || 8000
const DEV_PORT = Number(process.env.JOB_HUNTER_DEV_PORT) || 5173
const BACKEND_URL = `http://${HOST}:${PORT}`
const HEALTH_URL = `${BACKEND_URL}/health`
const DEV_URL = `http://localhost:${DEV_PORT}`
const BACKEND_READY_TIMEOUT = Number(process.env.JOB_HUNTER_STARTUP_TIMEOUT) || 60000
const APP_DIR_NAME = 'NS'

const PRELOAD = path.join(HERE, 'preload.cjs')
const ICON = path.join(FRONTEND_DIR, 'build', 'icon.png')

// Single source of truth for storage: <appData>/NS.
// Matches the convention in backend/app/config.py so the backend and this
// wrapper never disagree about where the database lives.
app.setPath('userData', path.join(app.getPath('appData'), APP_DIR_NAME))

let backendProcess = null
let backendExe = null
let ownsBackend = false
let mainWindow = null
let isQuitting = false

function log(...args) {
  console.log('[ns]', ...args)
}

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

function userDataDir() {
  return app.getPath('userData')
}

function logPath() {
  return path.join(userDataDir(), 'logs', 'backend.log')
}

function appendToLog(message) {
  try {
    fs.mkdirSync(path.dirname(logPath()), { recursive: true })
    fs.appendFileSync(logPath(), `${message}\n`)
  } catch {
    /* logging must never break the app */
  }
}

/* ------------------------------------------------------------------ */
/* Backend discovery                                                    */
/* ------------------------------------------------------------------ */

function backendExeName() {
  return IS_WIN ? 'ns.exe' : 'ns'
}

/**
 * Packaged layout: extraResources copies backend/dist/NS into
 * resources/backend, so the executable lives there. In development the
 * backend is started from source with the project virtualenv.
 */
function getBackendPath() {
  if (!DEV) {
    const candidates = [
      path.join(process.resourcesPath, 'backend', backendExeName()),
      path.join(process.resourcesPath, backendExeName()),
    ]
    for (const candidate of candidates) {
      if (fs.existsSync(candidate)) return { type: 'binary', path: candidate }
    }
  }

  if (fs.existsSync(path.join(BACKEND_DIR, 'app', 'main.py'))) {
    return { type: 'python', path: BACKEND_DIR }
  }

  return null
}

function pythonInterpreter() {
  const venv = path.join(BACKEND_DIR, '.venv', IS_WIN ? 'Scripts' : 'bin', IS_WIN ? 'python.exe' : 'python')
  return fs.existsSync(venv) ? venv : (IS_WIN ? 'python' : 'python3')
}

/* ------------------------------------------------------------------ */
/* Backend lifecycle                                                    */
/* ------------------------------------------------------------------ */

function probeHealth() {
  return new Promise((resolve) => {
    let settled = false
    const finish = (value) => {
      if (!settled) {
        settled = true
        resolve(value)
      }
    }
    const req = http.get(HEALTH_URL, { timeout: 1500 }, (res) => {
      res.resume()
      finish(res.statusCode === 200)
    })
    req.on('timeout', () => {
      req.destroy()
      finish(false)
    })
    req.on('error', () => finish(false))
  })
}

async function waitForBackend(timeoutMs) {
  const deadline = Date.now() + timeoutMs
  while (Date.now() < deadline) {
    if (await probeHealth()) return true
    await delay(400)
  }
  return false
}

function broadcast(channel, payload) {
  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.webContents.send(channel, payload)
  }
}

async function startBackend() {
  const config = getBackendPath()
  if (!config) return { ok: false, error: 'Backend executable not found.' }

  // Another instance (or a dev server) may already own the port.
  if (await probeHealth()) {
    ownsBackend = false
    log(`reusing the backend already listening on ${BACKEND_URL}`)
    return { ok: true, reused: true }
  }

  const dataDir = userDataDir()
  fs.mkdirSync(path.join(dataDir, 'uploads'), { recursive: true })
  fs.mkdirSync(path.join(dataDir, 'backups'), { recursive: true })

  const env = {
    ...process.env,
    PYTHONUNBUFFERED: '1',
    JOB_HUNTER_DATA_DIR: dataDir,
    NS_PACKAGED: 'true',
  }

  let command
  let args
  let cwd

  if (config.type === 'python') {
    command = pythonInterpreter()
    args = ['-m', 'uvicorn', 'app.main:app', '--host', HOST, '--port', String(PORT)]
    cwd = config.path
  } else {
    command = config.path
    args = ['--port', String(PORT)]
    cwd = dataDir
  }

  let fd = 'ignore'
  try {
    fs.mkdirSync(path.dirname(logPath()), { recursive: true })
    fd = fs.openSync(logPath(), 'a')
  } catch {
    /* fall back to discarding backend output */
  }

  let child
  try {
    child = spawn(command, args, { cwd, env, windowsHide: true, stdio: ['ignore', fd, fd] })
  } catch (err) {
    return { ok: false, error: `Could not start ${command}: ${err.message}` }
  }

  backendProcess = child
  backendExe = command
  ownsBackend = true

  child.on('error', (err) => {
    appendToLog(`[electron] failed to start backend: ${err.message}`)
    log('backend process error:', err.message)
  })

  child.on('exit', (code, signal) => {
    if (backendProcess === child) backendProcess = null
    if (isQuitting || !ownsBackend) return
    appendToLog(`[electron] backend exited (code=${code} signal=${signal})`)
    broadcast('backend-status', 'crashed')
    // Self-heal: keep the UI alive so it can explain the failure and retry.
    setTimeout(() => {
      if (!isQuitting && !backendProcess) startBackend().catch(() => {})
    }, 4000)
  })

  const ok = await waitForBackend(BACKEND_READY_TIMEOUT)
  if (ok) log(`backend ready on ${BACKEND_URL}`)
  return { ok }
}

/** Stops the backend and resolves once the port is free again. */
function stopBackend() {
  ownsBackend = false
  const proc = backendProcess
  backendProcess = null
  if (!proc) return Promise.resolve()

  return new Promise((resolve) => {
    const done = () => resolve()
    proc.once('exit', done)
    try {
      proc.kill()
    } catch {
      return resolve()
    }
    setTimeout(done, 5000)
  })
}

/* ------------------------------------------------------------------ */
/* Window                                                               */
/* ------------------------------------------------------------------ */

function isTrustedUrl(url) {
  if (url === 'about:blank' || url.startsWith('devtools://')) return true
  if (DEV && url.startsWith(DEV_URL)) return true
  return url.startsWith(BACKEND_URL)
}

function showStartupError(headline, detail) {
  const file = path.join(app.getPath('temp'), 'ns-startup-error.html')
  const html = `<!doctype html>
<html><head><meta charset="utf-8"><title>NS</title>
<style>
  body { margin:0; font-family:-apple-system,system-ui,sans-serif; background:#0b1020; color:#e6e9f5; display:flex; align-items:center; justify-content:center; height:100vh; }
  .card { max-width:540px; padding:32px 36px; border:1px solid #26304d; border-radius:16px; background:#121a33; }
  h1 { margin:0 0 12px; font-size:20px; }
  p { margin:0 0 20px; line-height:1.6; color:#a9b3d0; white-space:pre-wrap; }
  button { padding:10px 18px; border:0; border-radius:8px; background:#4f7cff; color:#fff; font-size:14px; cursor:pointer; }
  button[disabled] { opacity:0.5; cursor:default; }
</style></head>
<body><div class="card">
<h1>${headline}</h1>
<p>${detail}</p>
<button id="retry">Retry</button>
</div>
<script>
  document.getElementById('retry').addEventListener('click', async () => {
    const button = document.getElementById('retry');
    button.disabled = true;
    const result = await window.electronAPI.restartBackend();
    if (result && result.success) window.electronAPI.reloadApp();
    else button.disabled = false;
  });
</script>
</body></html>`

  try {
    fs.writeFileSync(file, html)
    mainWindow.loadFile(file)
  } catch {
    mainWindow.loadURL('data:text/html,' + encodeURIComponent(`<h1>${headline}</h1><p>${detail}</p>`))
  }
}

async function loadApp() {
  if (DEV && (await probeUrl(DEV_URL))) {
    log(`dev mode: loading ${DEV_URL}`)
    await mainWindow.loadURL(DEV_URL)
    return
  }

  // The backend serves the built UI and /api from the same origin.
  if (!(await waitForBackend(3000))) {
    showStartupError(
      'Backend is not responding',
      `The NS backend could not be reached at ${BACKEND_URL}.\n\nStart it with ./start-mac.sh, then press Retry.\n\nLog: ${logPath()}`
    )
    return
  }

  log(`loading ${BACKEND_URL}/`)
  await mainWindow.loadURL(`${BACKEND_URL}/`)
}

function probeUrl(url) {
  return new Promise((resolve) => {
    let settled = false
    const finish = (value) => {
      if (!settled) {
        settled = true
        resolve(value)
      }
    }
    const req = http.get(url, { timeout: 800 }, (res) => {
      res.resume()
      finish(res.statusCode < 500)
    })
    req.on('timeout', () => {
      req.destroy()
      finish(false)
    })
    req.on('error', () => finish(false))
  })
}

function buildMenu() {
  const template = [
    ...(IS_MAC
      ? [{
          label: app.name,
          submenu: [
            { role: 'about' },
            { type: 'separator' },
            { role: 'hide' },
            { role: 'hideOthers' },
            { role: 'unhide' },
            { type: 'separator' },
            { role: 'quit' },
          ],
        }]
      : []),
    {
      label: 'File',
      submenu: [
        {
          label: 'Open Data Folder',
          click: () => shell.openPath(userDataDir()),
        },
        {
          label: 'Restart Backend',
          accelerator: 'CmdOrCtrl+Shift+R',
          click: async () => {
            await stopBackend()
            const result = await startBackend()
            broadcast('backend-status', result.ok ? 'started' : 'failed')
            if (mainWindow && !mainWindow.isDestroyed()) mainWindow.reload()
          },
        },
        { type: 'separator' },
        IS_MAC ? { role: 'close' } : { role: 'quit' },
      ],
    },
    { role: 'editMenu' },
    { role: 'viewMenu' },
    { role: 'windowMenu' },
  ]

  Menu.setApplicationMenu(Menu.buildFromTemplate(template))
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1366,
    height: 800,
    minWidth: 1024,
    minHeight: 600,
    show: false,
    title: 'NS',
    backgroundColor: '#0b2a5c',
    ...(fs.existsSync(ICON) ? { icon: ICON } : {}),
    webPreferences: {
      preload: PRELOAD,
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: true,
      spellcheck: false,
    },
  })

  mainWindow.once('ready-to-show', () => mainWindow.show())

  // Anything that tries to open a new window goes to the real browser.
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (/^https?:/i.test(url)) shell.openExternal(url)
    return { action: 'deny' }
  })

  mainWindow.webContents.on('will-navigate', (event, url) => {
    if (!isTrustedUrl(url)) {
      event.preventDefault()
      if (/^https?:/i.test(url)) shell.openExternal(url)
    }
  })

  mainWindow.webContents.on('did-fail-load', (_event, code, description) => {
    if (isQuitting) return
    log(`renderer failed to load (${code} ${description})`)
  })

  mainWindow.on('closed', () => {
    mainWindow = null
  })

  loadApp().catch((err) => {
    log('failed to load the interface:', err)
    if (mainWindow && !mainWindow.isDestroyed()) {
      showStartupError('Failed to open the interface', String(err && err.message ? err.message : err))
    }
  })
}

/* ------------------------------------------------------------------ */
/* IPC                                                                  */
/* ------------------------------------------------------------------ */

ipcMain.handle('get-backend-url', () => BACKEND_URL)

ipcMain.handle('get-data-dir', () => userDataDir())

ipcMain.handle('get-log-path', () => logPath())

ipcMain.handle('open-data-folder', () => {
  shell.openPath(userDataDir())
  return { success: true }
})

ipcMain.handle('restart-backend', async () => {
  await stopBackend()
  const result = await startBackend()
  broadcast('backend-status', result.ok ? 'started' : 'failed')
  return { success: result.ok, error: result.error || null }
})

ipcMain.handle('reload-app', () => {
  if (mainWindow && !mainWindow.isDestroyed()) loadApp()
  return { success: true }
})

ipcMain.handle('get-runtime-info', () => ({
  isDev: DEV,
  packaged: app.isPackaged,
  version: app.getVersion(),
  electron: process.versions.electron,
  chrome: process.versions.chrome,
  node: process.versions.node,
  platform: process.platform,
  arch: process.arch,
  backendUrl: BACKEND_URL,
  appUrl: DEV ? DEV_URL : `${BACKEND_URL}/`,
  backendExe,
  dataDir: userDataDir(),
  logPath: logPath(),
}))

ipcMain.handle('get-backend-log', () => {
  try {
    return fs.readFileSync(logPath(), 'utf8').split('\n').slice(-500).join('\n')
  } catch {
    return ''
  }
})

ipcMain.handle('open-external', (_event, url) => {
  if (typeof url === 'string' && /^https?:\/\//i.test(url)) {
    shell.openExternal(url)
    return { success: true }
  }
  return { success: false, error: 'Only http(s) URLs can be opened.' }
})

ipcMain.handle('open-path', async (_event, target) => {
  if (typeof target !== 'string' || !target) return { success: false }
  const message = await shell.openPath(target)
  return { success: !message, error: message || undefined }
})

ipcMain.handle('get-app-version', () => app.getVersion())

// The desktop shortcut created by the installer passes --open-data-folder.
if (process.argv.includes('--open-data-folder')) {
  app.whenReady().then(() => shell.openPath(userDataDir()))
}

/* ------------------------------------------------------------------ */
/* Bootstrap                                                            */
/* ------------------------------------------------------------------ */

const gotLock = app.requestSingleInstanceLock()
if (!gotLock) {
  app.quit()
} else {
  app.on('second-instance', () => {
    if (mainWindow && !mainWindow.isDestroyed()) {
      if (mainWindow.isMinimized()) mainWindow.restore()
      mainWindow.focus()
    }
  })

  app.whenReady().then(async () => {
    buildMenu()

    try {
      const result = await startBackend()
      if (!result.ok && !result.reused) {
        dialog.showErrorBox(
          'NS - backend failed to start',
          `The local service did not come up on port ${PORT}.\n\n` +
            `Check the log file at:\n${logPath()}\n\n${result.error || ''}`
        )
      }
    } catch (err) {
      dialog.showErrorBox('NS', String(err && err.message ? err.message : err))
    }

    createWindow()

    if (mainWindow && !mainWindow.isDestroyed()) {
      broadcast('backend-status', 'started')
    }

    app.on('activate', () => {
      if (BrowserWindow.getAllWindows().length === 0) createWindow()
    })
  })

  app.on('before-quit', () => {
    isQuitting = true
    if (ownsBackend) stopBackend()
  })

  app.on('window-all-closed', () => {
    if (!IS_MAC) app.quit()
  })
}
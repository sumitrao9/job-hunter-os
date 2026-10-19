/**
 * Preload bridge.
 *
 * This file must stay CommonJS: the package is "type": "module", and Electron
 * only supports ESM preload scripts when the renderer is unsandboxed and the
 * file uses the .mjs extension. Renaming to preload.cjs keeps contextIsolation
 * and the Chromium sandbox enabled, which is the safer configuration.
 */
const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('electronAPI', {
  isElectron: true,
  platform: process.platform,
  getBackendUrl: () => ipcRenderer.invoke('get-backend-url'),
  getRuntimeInfo: () => ipcRenderer.invoke('get-runtime-info'),
  getAppVersion: () => ipcRenderer.invoke('get-app-version'),
  restartBackend: () => ipcRenderer.invoke('restart-backend'),
  reloadApp: () => ipcRenderer.invoke('reload-app'),
  openExternal: (url) => ipcRenderer.invoke('open-external', url),
  openPath: (target) => ipcRenderer.invoke('open-path', target),
  openDataFolder: () => ipcRenderer.invoke('open-data-folder'),
  getDataDir: () => ipcRenderer.invoke('get-data-dir'),
  getLogPath: () => ipcRenderer.invoke('get-log-path'),
  getBackendLog: () => ipcRenderer.invoke('get-backend-log'),
  onBackendStatus: (callback) => {
    const listener = (_event, status) => callback(status)
    ipcRenderer.on('backend-status', listener)
    return () => ipcRenderer.removeListener('backend-status', listener)
  },
  onBackendLog: (callback) => {
    const listener = (_event, line) => callback(line)
    ipcRenderer.on('backend-log', listener)
    return () => ipcRenderer.removeListener('backend-log', listener)
  },
})
# Building Job Hunter OS for Windows

The Windows desktop app has two parts that are packaged together:

| Part | Built with | Output |
| --- | --- | --- |
| React UI (static files) | Vite | `frontend/dist/` |
| Python backend service | PyInstaller | `backend/dist/Job Hunter OS/` |
| Windows installer + portable exe | electron-builder | `frontend/dist-electron/*.exe` |

electron-builder copies the frozen backend into the app as
`resources/backend/`, and `frontend/electron/main.cjs` starts it on
`http://127.0.0.1:8000` and shows the UI.

---

## Why macOS cannot produce the Windows installer

**The Python backend is the blocker, not electron-builder.**

- **PyInstaller cannot cross-compile.** The frozen output embeds a platform
  bootloader plus CPython extension modules (`.pyd` on Windows). It must run
  on the platform it targets. Building it on macOS produces a macOS binary
  that Windows cannot execute, and no PyInstaller flag changes that.
- **electron-builder *can* build a Windows NSIS installer from macOS or
  Linux**, because the renderer is plain JavaScript with no native modules
  and the NSIS toolchain it downloads has macOS/Linux binaries. So the
  installer shell is not the problem — the missing Windows backend is.

Consequences:

- Doing only the electron-builder step on macOS gives you an app that
  launches and then reports "Backend executable not found". It is not
  shippable.
- Anything that produces a *working* Windows app needs a Windows
  environment: a real Windows PC, a Windows VM, a Windows CI runner, or
  Wine running a Windows Python.

The guard in `frontend/scripts/assert-build-prereqs.mjs` (wired to
`npm run predist`) fails the build if `backend/dist/Job Hunter OS/` has no
`job-hunter-os.exe`, so this mistake cannot silently ship.

---

## Option A - Windows machine or VM (recommended for first build)

### Prerequisites on the Windows machine

1. **Node.js 20 LTS** - <https://nodejs.org/> (keep "Add to PATH" ticked).
2. **Python 3.11 or 3.12 (64-bit)** - <https://www.python.org/downloads/windows/>
   Tick **"Add python.exe to PATH"** during setup. 3.13+ works but some
   transitive wheels lag behind, so 3.12 is the safe choice.
3. Nothing else. The script installs every other dependency, including
   PyInstaller and electron-builder's NSIS toolchain.

### Run the build

Open a normal Command Prompt (no admin rights needed for the build itself):

```bat
cd path\to\job-hunter-os
backend\packaging\build-windows.bat
```

The script performs, in order:

1. Verifies `node`, `npm` and `python`, creating `backend\.venv` if needed.
2. `pip install -r backend\requirements.txt` plus `pyinstaller`.
3. `npm ci` (falls back to `npm install`) and `npm run build` (Vite).
4. PyInstaller freeze into `backend\dist\Job Hunter OS\`.
5. `electron-builder --win --x64` for the NSIS installer and the portable exe.
6. Copies the `.exe` artifacts into `release\windows\`.

Useful switches:

```bat
backend\packaging\build-windows.bat --skip-frontend    :: reuse frontend\dist
backend\packaging\build-windows.bat --dir-only         :: unpacked app only, fastest smoke test
backend\packaging\build-windows.bat --installer-only   :: NSIS installer only
backend\packaging\build-windows.bat --portable-only    :: portable exe only
```

### Expected output

```
frontend\dist-electron\Job Hunter OS-0.1.0-x64-Setup.exe
frontend\dist-electron\Job Hunter OS-0.1.0-x64-portable.exe
release\windows\Job Hunter OS-0.1.0-x64-Setup.exe
release\windows\Job Hunter OS-0.1.0-x64-portable.exe
```

`build-windows.bat` pauses at the end unless `CI` is defined, so CI logs are
not blocked on a prompt.

---

## Option B - GitHub Actions (recommended for repeatable builds)

`.github/workflows/build-windows.yml` is included. It runs on
`windows-latest`, which gives you both the Windows Python *and* a real
Windows environment in a single job.

Push a tag or trigger it manually:

```bash
git tag v0.1.0
git push origin v0.1.0
# or: Actions tab -> build-windows -> Run workflow
```

Artifacts are uploaded as `job-hunter-os-windows`. The job calls the same
`build-windows.bat`, so local and CI builds are identical.

---

## Option C - Wine on macOS/Linux (possible, not recommended)

If you cannot get a Windows machine or CI runner, Wine can host a Windows
Python and therefore a Windows PyInstaller build. Treat it as a fallback.

```bash
brew install --cask wine-stable wine@stable   # macOS
# Linux: install wine64 from your distribution
```

Then, using a **Windows** Python (not the macOS one) inside Wine:

```bash
wine cmd /c "python -m venv .venv-win && .venv-win\\Scripts\\pip install -r backend\\requirements.txt pyinstaller"
wine .venv-win/Scripts/python.exe -m PyInstaller --clean --noconfirm backend/packaging/job-hunter-os.spec
```

Finally, with that `backend/dist/Job Hunter OS/job-hunter-os.exe` present, the
installer can be produced from macOS directly:

```bash
cd frontend
npm run build
npx electron-builder --win --x64 --publish never
```

Caveats:

- PyInstaller under Wine is fragile. `import` hooks, `.pyd` loading and
  `long path` handling can fail in ways that do not reproduce on real Windows.
- Always smoke test the result on real Windows 10 **and** Windows 11 before
  distributing anything.
- Wine is **not** needed for signing on macOS in electron-builder 25 (it uses
  a native resource editor), but it *is* needed on Linux for some code
  signing flows.

---

## Manual pipeline (if you prefer to run each step)

```bat
REM 1. backend dependencies
python -m venv backend\.venv
backend\.venv\Scripts\pip install -r backend\requirements.txt
backend\.venv\Scripts\pip install pyinstaller

REM 2. frontend
cd frontend
npm ci
npm run build
cd ..

REM 3. freeze the backend
backend\.venv\Scripts\python -m PyInstaller --clean --noconfirm backend\packaging\job-hunter-os.spec

REM 4. installer + portable
cd frontend
npx electron-builder --win --x64 --publish never
```

Step 3 must finish before step 4: `build.nsis.extraResources` reads
`../backend/dist/Job Hunter OS`, and electron-builder only warns (it does not
fail) when that folder is missing.

---

## Signing the installer

The installers produced above are **unsigned**, so SmartScreen shows
"Windows protected your PC" and users must click "More info -> Run anyway".
To remove that, buy or create a code-signing certificate and export it as a
Base64 `.pfx`, then set two environment variables before running
electron-builder:

```bat
set CSC_LINK=C:\certs\job-hunter-os.pfx
set CSC_KEY_PASSWORD=your-certificate-password
npx electron-builder --win --x64 --publish never
```

electron-builder signs both the inner Electron exe and the installer, and it
signs the portable exe as well. Self-signed certificates are not trusted by
default, so they do not remove the warning; you need a certificate from a CA
that Microsoft trusts.

---

## Verifying a build before shipping

1. Copy the portable exe to a clean Windows 10 VM and a clean Windows 11 VM.
2. Launch it. The window opens and the dashboard loads from
   `http://127.0.0.1:8000`.
3. Open `%APPDATA%\JobHunterOS\logs\backend.log` - the backend stdout and
   stderr are captured there. No tracebacks expected.
4. Confirm the database was created at `%APPDATA%\JobHunterOS\job_hunter.db`.
5. Close the app, confirm no leftover `job-hunter-os` process
   (`tasklist | findstr job-hunter-os`).
6. Install `Job Hunter OS-<version>-x64-Setup.exe` and check:
   - Start Menu > Job Hunter OS contains the app and uninstaller entries.
   - A desktop shortcut exists, plus "Job Hunter OS Data".
   - The license page appears and requires accepting.
   - The installer offers a folder choice and a per-user / all-users choice.
   - "Start Job Hunter OS" launches the app after install.
7. Run the uninstaller: shortcuts disappear, and
   `%APPDATA%\JobHunterOS` is **kept** (`nsis.deleteAppDataOnUninstall` is
   `false` on purpose - job history and resumes survive reinstalls).

---

## Configuration reference

| Setting | Location | Meaning |
| --- | --- | --- |
| `win.target` | `frontend/package.json` | `nsis` + `portable`, x64 |
| `nsis.oneClick: false` | `frontend/package.json` | Wizard-style installer with a folder page |
| `nsis.license` | `frontend/package.json` | Shows the EULA page. There is no `displayLicense` option in electron-builder 25; setting `license` is what enables that page |
| `nsis.include` | `frontend/package.json` | `frontend/build/installer.nsis`, the custom NSIS macros |
| `nsis.perMachine: false` | `frontend/package.json` | Defaults to per-user install; user can choose all-users |
| `nsis.deleteAppDataOnUninstall: false` | `frontend/package.json` | Keeps `%APPDATA%\JobHunterOS` |
| `extraResources` | `frontend/package.json` | Frozen backend -> `resources/backend/` |
| `!macro licensePage` | `frontend/build/installer.nsis` | EULA page text and accept button |
| `!macro customWelcomePage` | `frontend/build/installer.nsis` | Welcome page text |
| `!macro customFinishPage` | `frontend/build/installer.nsis` | Finish page plus de-elevated launch |
| `!macro customInstall` | `frontend/build/installer.nsis` | Start Menu and desktop shortcuts |

### Editing the installer UI

`frontend/build/installer.nsis` is compiled into the installer, so mistakes
are compile errors, not silent no-ops. Only the macro names electron-builder
actually calls will be used; check
`frontend/node_modules/app-builder-lib/templates/nsis/` if you add your own.

Validate a change with the fastest possible build:

```bat
backend\packaging\build-windows.bat --skip-frontend --installer-only
```

---

## Troubleshooting

**`ERROR: backend executable not found at ... job-hunter-os.exe`**
PyInstaller did not run or wrote somewhere else. Run step 3 on its own and
read its output.

**`file source doesn't exist from=.../backend/dist/Job Hunter OS`**
electron-builder warning, not an error: step 4 ran before step 3. Use
`npm run dist` (which runs `predist` first) instead of calling
`electron-builder` directly.

**`Invalid configuration object ... nsis has an unknown property`**
A key was renamed or removed. Check the valid list printed in the error, and
see `https://www.electron.build/nsis`.

**`makensis` / NSIS download fails**
No network access, or a proxy. Re-run once online;
electron-builder caches the toolchain under
`%LOCALAPPDATA%\electron-builder\Cache\nsis`.

**Installer builds but the app shows "Backend executable not found"**
The `extraResources` path resolved to an empty folder. Confirm
`backend\dist\Job Hunter OS\job-hunter-os.exe` exists and that the version
was built from the same checkout.

**App starts but the window is blank and the log shows a CORS error**
The UI is being loaded from `file://` instead of the backend. Confirm the
frozen bundle contains `frontend\dist`:

```bat
dir "resources\backend\Job Hunter OS\_internal\frontend\dist"
```

If it is missing, `frontend\dist` was not built before PyInstaller ran.
Rebuild with `npm run build` then re-run the build script.

**SmartScreen blocks the app**
Expected while unsigned. See the signing section.

**Long paths fail during `npm ci`**
Enable long paths: `reg add HKLM\SYSTEM\CurrentControlSet\Control\FileSystem /v LongPathsEnabled /t REG_DWORD /d 1 /f` (needs admin).
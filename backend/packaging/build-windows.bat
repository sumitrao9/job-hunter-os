@echo off
REM ============================================================================
REM  NS - Windows build script
REM
REM  Produces, in frontend\dist-electron\:
REM    NS-<version>-x64-Setup.exe    NSIS installer (Start Menu +
REM                                             Desktop shortcuts, license page)
REM    NS-<version>-x64-portable.exe  No-install portable build
REM
REM  It first builds the Python backend with PyInstaller into
REM  backend\dist\NS\, which electron-builder then copies into the
REM  app as resources\backend\.
REM
REM  Run from a Windows machine (or Windows CI runner):
REM    backend\packaging\build-windows.bat
REM
REM  Optional switches:
REM    --skip-frontend   reuse the existing frontend\dist (faster rebuilds)
REM    --dir-only        skip NSIS/portable packaging, produce an unpacked app
REM    --portable-only   build only the portable .exe
REM    --installer-only  build only the NSIS installer
REM
REM  NOTE: the Windows installer cannot be produced from macOS or Linux -
REM  see BUILD_WINDOWS.md for the wine / GitHub Actions route.
REM ============================================================================

setlocal EnableExtensions EnableDelayedExpansion

set "ROOT=%~dp0..\.."
set "FRONTEND=%ROOT%\frontend"
set "BACKEND=%ROOT%\backend"
set "VENV=%BACKEND%\.venv"
set "PY=%VENV%\Scripts\python.exe"
set "SPEC=%BACKEND%\packaging\ns.spec"
set "BACKEND_DIST=%BACKEND%\dist\NS"

set "SKIP_FRONTEND=0"
set "DIR_ONLY=0"
set "PORTABLE_ONLY=0"
set "INSTALLER_ONLY=0"

:parse_args
if "%~1"=="" goto args_done
if /i "%~1"=="--skip-frontend"  set "SKIP_FRONTEND=1"  & shift & goto parse_args
if /i "%~1"=="--dir-only"        set "DIR_ONLY=1"        & shift & goto parse_args
if /i "%~1"=="--portable-only"   set "PORTABLE_ONLY=1"   & shift & goto parse_args
if /i "%~1"=="--installer-only"  set "INSTALLER_ONLY=1"  & shift & goto parse_args
echo Unknown option: %~1
goto usage

:usage
echo Usage: build-windows.bat [--skip-frontend] [--dir-only] [--portable-only] [--installer-only]
exit /b 2

:args_done

echo.
echo ==========================================================
echo   NS - Windows build
echo   Project root: %ROOT%
echo ==========================================================
echo.

REM ---------------------------------------------------------------------------
REM  Step 0 - Preflight
REM ---------------------------------------------------------------------------
echo [0/6] Checking prerequisites...

where node  >nul 2>&1 || goto :no_node
where npm   >nul 2>&1 || goto :no_npm
where python >nul 2>&1 || goto :no_python

for /f "tokens=*" %%v in ('node --version')  do set "NODE_VER=%%v"
for /f "tokens=*" %%v in ('npm --version')   do set "NPM_VER=%%v"
for /f "tokens=*" %%v in ('python --version') do set "PY_VER=%%v"

echo   node    %NODE_VER%
echo   npm     %NPM_VER%
echo   python  %PY_VER%
echo.

if not exist "%VENV%\Scripts\python.exe" (
    echo   Creating virtual environment at %VENV%
    python -m venv "%VENV%"
    if errorlevel 1 (
        echo ERROR: failed to create the virtual environment.
        exit /b 1
    )
) else (
    echo   Reusing virtual environment at %VENV%
)
echo.

REM ---------------------------------------------------------------------------
REM  Step 1 - Python dependencies
REM ---------------------------------------------------------------------------
echo [1/6] Installing Python backend dependencies...
"%PY%" -m pip install --upgrade pip setuptools wheel
if errorlevel 1 goto :pip_failed
"%PY%" -m pip install -r "%BACKEND%\requirements.txt"
if errorlevel 1 goto :pip_failed
"%PY%" -m pip install pyinstaller
if errorlevel 1 goto :pip_failed
echo   Python dependencies OK.
echo.

REM ---------------------------------------------------------------------------
REM  Step 2 - Frontend dependencies and bundle
REM ---------------------------------------------------------------------------
echo [2/6] Installing frontend dependencies...
pushd "%FRONTEND%"
call npm ci
if errorlevel 1 (
    popd
    echo ERROR: npm ci failed. Falling back to npm install.
    pushd "%FRONTEND%"
    call npm install
    if errorlevel 1 (
        popd
        echo ERROR: npm install failed.
        exit /b 1
    )
)
popd

if "%SKIP_FRONTEND%"=="1" (
    echo   Skipping frontend build (--skip-frontend).
) else (
    echo   Building frontend with Vite...
    pushd "%FRONTEND%"
    call npm run build
    if errorlevel 1 (
        popd
        echo ERROR: frontend build failed.
        exit /b 1
    )
    popd
)

if not exist "%FRONTEND%\dist\index.html" (
    echo ERROR: %FRONTEND%\dist\index.html was not produced.
    exit /b 1
)
echo   Frontend bundle OK.
echo.

REM ---------------------------------------------------------------------------
REM  Step 3 - Python backend with PyInstaller
REM ---------------------------------------------------------------------------
echo [3/6] Freezing the Python backend with PyInstaller...

if exist "%BACKEND%\build" rmdir /s /q "%BACKEND%\build"
if exist "%BACKEND%\dist"  rmdir /s /q "%BACKEND%\dist"

pushd "%BACKEND%"
"%PY%" -m PyInstaller --clean --noconfirm "%SPEC%"
set "PYI_RESULT=%ERRORLEVEL%"
popd

if not "%PYI_RESULT%"=="0" (
    echo ERROR: PyInstaller failed.
    exit /b 1
)

if not exist "%BACKEND_DIST%\ns.exe" (
    echo ERROR: backend executable not found at:
    echo        %BACKEND_DIST%\ns.exe
    echo   Contents of %BACKEND%\dist:
    dir /b "%BACKEND%\dist"
    exit /b 1
)
echo   Backend frozen to %BACKEND_DIST%
echo.

REM ---------------------------------------------------------------------------
REM  Step 4 - Electron application
REM ---------------------------------------------------------------------------
echo [4/6] Packaging the Electron application with electron-builder...
pushd "%FRONTEND%"

if "%DIR_ONLY%"=="1" (
    echo   Unpacked build only (--dir-only).
    call npx electron-builder --win --x64 --dir --publish never
    goto :electron_done
)

if "%PORTABLE_ONLY%"=="1" (
    call npx electron-builder --win portable --x64 --publish never
    goto :electron_done
)

if "%INSTALLER_ONLY%"=="1" (
    call npx electron-builder --win nsis --x64 --publish never
    goto :electron_done
)

call npx electron-builder --win --x64 --publish never

:electron_done
set "EB_RESULT=%ERRORLEVEL%"
popd

if not "%EB_RESULT%"=="0" (
    echo ERROR: electron-builder failed with code %EB_RESULT%.
    exit /b 1
)
echo.

REM ---------------------------------------------------------------------------
REM  Step 5 - Collect artifacts
REM ---------------------------------------------------------------------------
echo [5/6] Collecting build artifacts...
if not exist "%FRONTEND%\dist-electron" (
    echo ERROR: %FRONTEND%\dist-electron does not exist.
    exit /b 1
)
echo   Artifacts in %FRONTEND%\dist-electron:
dir /b "%FRONTEND%\dist-electron"
echo.

REM  A single folder that is easy to copy to another machine.
set "COLLECT=%ROOT%\release\windows"
if exist "%COLLECT%" rmdir /s /q "%COLLECT%"
mkdir "%COLLECT%"
copy /y "%FRONTEND%\dist-electron\*.exe" "%COLLECT%\" >nul
if exist "%FRONTEND%\dist-electron\win-unpacked" (
    echo   Note: win-unpacked left in place for debugging.
)
echo   Collect folder: %COLLECT%
echo.

REM ---------------------------------------------------------------------------
REM  Step 6 - Summary
REM ---------------------------------------------------------------------------
echo [6/6] Done.
echo.
echo ==========================================================
echo   Windows build finished
echo ==========================================================
echo   Installer : %FRONTEND%\dist-electron\NS-*-Setup.exe
echo   Portable  : %FRONTEND%\dist-electron\NS-*-portable.exe
echo   Collect   : %COLLECT%
echo.
echo   The installers are UNSIGNED. Windows SmartScreen will show a
echo   "Windows protected your PC" warning until you code-sign them.
echo   See BUILD_WINDOWS.md for the signing step.
echo.
echo   Smoke test before shipping:
echo     1. Run the portable exe on a clean Windows 10 and Windows 11 VM.
echo     2. Confirm the window opens and the dashboard loads.
echo     3. Check %%APPDATA%%\NS\logs\backend.log for backend errors.
echo     4. Install the NSIS build and verify Start Menu + Desktop shortcuts.
echo.
if not defined CI pause
exit /b 0

REM ---------------------------------------------------------------------------
REM  Failure handlers
REM ---------------------------------------------------------------------------
:no_node
echo ERROR: Node.js is not installed or not on PATH.
echo   Install the LTS build from https://nodejs.org/ then reopen this prompt.
exit /b 1

:no_npm
echo ERROR: npm is not on PATH. Reinstall Node.js with npm included.
exit /b 1

:no_python
echo ERROR: Python is not installed or not on PATH.
echo   Install Python 3.11 or 3.12 from https://www.python.org/downloads/windows/
echo   and tick "Add python.exe to PATH" during setup.
exit /b 1

:pip_failed
echo ERROR: pip install failed. Check the output above.
exit /b 1
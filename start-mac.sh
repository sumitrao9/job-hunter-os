#!/usr/bin/env bash
#
# NS - one-click launcher for macOS.
#
#   ./start-mac.sh                 production-ish: build frontend if stale, start
#                                  the FastAPI backend, then open the Electron UI
#   ./start-mac.sh --dev           run the Vite dev server and open Electron on it
#   ./start-mac.sh --binary        use the PyInstaller executable instead of Python
#   ./start-mac.sh --backend-only  start only the backend (no Electron window)
#   ./start-mac.sh --help          full option list
#
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND="$ROOT/frontend"
BACKEND="$ROOT/backend"
RUN_DIR="$ROOT/.run"

PORT="${JOB_HUNTER_PORT:-8000}"
DEV_PORT="${JOB_HUNTER_DEV_PORT:-5173}"
BACKEND_URL="http://127.0.0.1:${PORT}"
HEALTH_URL="${BACKEND_URL}/health"
DEV_URL="http://localhost:${DEV_PORT}"

MODE="prod"          # prod | dev
USE_BINARY=0
BACKEND_ONLY=0
FORCE_BUILD=0
SKIP_BUILD=0
AUTO_SETUP=1
KEEP_BACKEND=0
START_TIMEOUT="${JOB_HUNTER_STARTUP_TIMEOUT:-180}"

# Persistent data directory (overridable via env).
DATA_DIR="${NS_DATA_DIR:-$HOME/Library/Application Support/NS}"

BACKEND_PID=""
VITE_PID=""
BACKEND_STARTED=0

if [ -t 1 ]; then
  C_RESET=$'\033[0m'; C_BLUE=$'\033[1;34m'; C_GREEN=$'\033[0;32m'
  C_YELLOW=$'\033[0;33m'; C_RED=$'\033[0;31m'; C_DIM=$'\033[2m'
else
  C_RESET=""; C_BLUE=""; C_GREEN=""; C_YELLOW=""; C_RED=""; C_DIM=""
fi

log()  { printf '%s[*]%s %s\n' "$C_BLUE" "$C_RESET" "$*"; }
ok()   { printf '%s[+]%s %s\n' "$C_GREEN" "$C_RESET" "$*"; }
warn() { printf '%s[!]%s %s\n' "$C_YELLOW" "$C_RESET" "$*" >&2; }
die()  { printf '%s[x]%s %s\n' "$C_RED" "$C_RESET" "$*" >&2; exit 1; }
dim()  { printf '%s    %s%s\n' "$C_DIM" "$*" "$C_RESET"; }

usage() {
  cat <<'USAGE'
NS - one-click macOS launcher

Usage: ./start-mac.sh [options]

Modes
  (default)          Build the frontend if needed, start the backend, open Electron
  --dev, -d          Start the Vite dev server (HMR) and open Electron against it
  --backend-only     Start the backend only, no Electron window
  --binary           Prefer the PyInstaller executable in backend/dist over Python

Options
  --build            Force a frontend production build
  --skip-build       Never build the frontend
  --port <n>         Backend port (default 8000)
  --dev-port <n>     Vite dev server port (default 5173)
  --timeout <sec>    Backend startup timeout (default 120)
  --no-setup         Do not run npm install / pip install automatically
  --keep-backend     Leave the backend running after Electron exits
  -h, --help         Show this help

     echo "Environment overrides: NS_DATA_DIR, JOB_HUNTER_PORT, JOB_HUNTER_DEV_PORT,"
       "JOB_HUNTER_STARTUP_TIMEOUT."
USAGE
}

while [ $# -gt 0 ]; do
  case "$1" in
    --dev|-d)        MODE="dev" ;;
    --backend-only)  BACKEND_ONLY=1 ;;
    --binary)        USE_BINARY=1 ;;
    --build)         FORCE_BUILD=1 ;;
    --skip-build)    SKIP_BUILD=1 ;;
    --keep-backend)  KEEP_BACKEND=1 ;;
    --no-setup)      AUTO_SETUP=0 ;;
    --port)          PORT="${2:?--port needs a value}"; shift ;;
    --dev-port)      DEV_PORT="${2:?--dev-port needs a value}"; shift ;;
    --timeout)       START_TIMEOUT="${2:?--timeout needs a value}"; shift ;;
    -h|--help)       usage; exit 0 ;;
    *)               usage; die "Unknown option: $1" ;;
  esac
  shift
done

mkdir -p "$RUN_DIR"

# ---------------------------------------------------------------- cleanup ----

kill_pid() {
  local pid="$1"
  [ -n "$pid" ] || return 0
  kill -0 "$pid" 2>/dev/null || return 0
  kill "$pid" 2>/dev/null
  for _ in 1 2 3 4 5 6 7 8 9 10; do
    kill -0 "$pid" 2>/dev/null || return 0
    sleep 0.3
  done
  kill -9 "$pid" 2>/dev/null
}

cleanup() {
  trap - EXIT INT TERM
  [ -n "$VITE_PID" ] && kill_pid "$VITE_PID"
  if [ "$BACKEND_STARTED" = "1" ] && [ "$KEEP_BACKEND" = "0" ]; then
    kill_pid "$BACKEND_PID"
    rm -f "$RUN_DIR/backend.pid"
  elif [ "$BACKEND_STARTED" = "1" ]; then
    warn "Backend left running (pid $BACKEND_PID) - stop it with: kill $BACKEND_PID"
  fi
}
trap cleanup EXIT INT TERM

# ------------------------------------------------------------- utilities ----

have() { command -v "$1" >/dev/null 2>&1; }

wait_for_url() {
  local url="$1" timeout="$2" label="$3" waited=0
  while [ "$waited" -lt "$timeout" ]; do
    if curl -fsS --max-time 2 "$url" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
    waited=$((waited + 1))
    if [ $((waited % 20)) -eq 0 ]; then
      dim "still waiting for $label (${waited}s)"
    fi
  done
  return 1
}

port_listener_pid() {
  lsof -nP -iTCP:"$1" -sTCP:LISTEN -t 2>/dev/null | head -1
}

http_ok() { curl -fsS --max-time 2 "$1" >/dev/null 2>&1; }

frontend_is_stale() {
  local index="$FRONTEND/dist/index.html"
  [ -f "$index" ] || return 0
  local newer
  newer=$(find "$FRONTEND/src" "$FRONTEND/index.html" "$FRONTEND/vite.config.ts" \
                "$FRONTEND/package.json" -newer "$index" -print -quit 2>/dev/null)
  [ -n "$newer" ]
}

# ------------------------------------------------------- 0. prerequisites ----

printf '\n%s  NS - macOS launcher%s  (%s mode)\n\n' "$C_BLUE" "$C_RESET" "$MODE"

log "checking prerequisites"
have node || die "node is required (https://nodejs.org)"
have npm  || die "npm is required"
have curl || die "curl is required"
[ "$(uname -s)" = "Darwin" ] || warn "this script targets macOS; continuing anyway"

if [ ! -d "$FRONTEND/node_modules" ]; then
  [ "$AUTO_SETUP" = "1" ] || die "frontend/node_modules is missing (run: npm install)"
  log "installing frontend dependencies (first run, this takes a while)"
  ( cd "$FRONTEND" && npm install ) || die "npm install failed"
fi

# electron's own postinstall uses extract-zip, which silently no-ops on newer
# Node releases and leaves node_modules/electron without a binary. Repair it.
if [ ! -f "$FRONTEND/node_modules/electron/path.txt" ]; then
  log "electron binary missing - running its installer"
  ( cd "$FRONTEND" && node node_modules/electron/install.js ) >/dev/null 2>&1
fi
if [ ! -f "$FRONTEND/node_modules/electron/path.txt" ]; then
  warn "electron postinstall did not unpack the binary - extracting manually"
  ELECTRON_ZIP="$( cd "$FRONTEND" && node -e '
    const p = require("path");
    const { downloadArtifact } = require("@electron/get");
    const pkg = require("./node_modules/electron/package.json");
    downloadArtifact({
      version: pkg.version,
      artifactName: "electron",
      checksums: require("./node_modules/electron/checksums.json"),
      platform: process.platform,
      arch: process.arch,
    }).then((zip) => console.log(zip)).catch(() => process.exit(1));
  ' )" || die "could not obtain the electron binary"
  rm -rf "$FRONTEND/node_modules/electron/dist"
  ditto -x -k "$ELECTRON_ZIP" "$FRONTEND/node_modules/electron/dist" || die "electron extraction failed"
  printf 'Electron.app/Contents/MacOS/Electron' > "$FRONTEND/node_modules/electron/path.txt"
fi
[ -x "$FRONTEND/node_modules/.bin/electron" ] || die "electron is not runnable ($FRONTEND/node_modules/.bin/electron missing)"

# ------------------------------------------------------- 1. python backend ----

PYTHON=""
resolve_python() {
  if [ -x "$BACKEND/.venv/bin/python" ]; then
    PYTHON="$BACKEND/.venv/bin/python"
  elif have python3; then
    PYTHON="$(command -v python3)"
  else
    PYTHON=""
  fi
}

resolve_python
if [ -z "$PYTHON" ]; then
  die "python3 is required to run the backend"
fi

if ! "$PYTHON" -c "import fastapi, uvicorn" >/dev/null 2>&1; then
  if [ "$AUTO_SETUP" != "1" ]; then
    die "backend dependencies missing - run: $PYTHON -m pip install -r backend/requirements.txt"
  fi
  if [ ! -x "$BACKEND/.venv/bin/python" ] && [ "$PYTHON" != "$BACKEND/.venv/bin/python" ]; then
    log "creating virtualenv at backend/.venv"
    "$PYTHON" -m venv "$BACKEND/.venv" || die "could not create the virtualenv"
    resolve_python
  fi
  log "installing backend dependencies (first run, this takes a while)"
  "$PYTHON" -m pip install --upgrade pip >/dev/null 2>&1
  "$PYTHON" -m pip install -r "$BACKEND/requirements.txt" || die "pip install failed"
fi

if "$PYTHON" -c "import app.main" >/dev/null 2>&1; then
  :
else
  (
    cd "$BACKEND" || exit 1
    "$PYTHON" -c "import app.main"
  ) >/dev/null 2>&1 || die "backend failed to import - check backend/.env and run: $PYTHON -m pip install -r backend/requirements.txt"
fi

# ------------------------------------------------------ 2. frontend build ----

if [ "$MODE" = "dev" ]; then
  log "dev mode: skipping the production build (Vite serves the sources)"
elif [ "$SKIP_BUILD" = "1" ]; then
  log "skipping the frontend build (--skip-build)"
elif [ "$FORCE_BUILD" = "1" ] || frontend_is_stale; then
  log "building the frontend"
  ( cd "$FRONTEND" && npm run build ) || die "frontend build failed"
  ok "frontend build complete"
else
  dim "frontend build is up to date"
fi

# ------------------------------------------------------- 3. start backend ----

PYINSTALLER_BIN=""
find_pyinstaller_bin() {
  local candidates=(
    "$BACKEND/dist/NS/ns"
    "$BACKEND/dist/ns"
  )
  for candidate in "${candidates[@]}"; do
    if [ -x "$candidate" ]; then
      PYINSTALLER_BIN="$candidate"
      return 0
    fi
  done
  return 1
}

if [ "$USE_BINARY" = "1" ]; then
  find_pyinstaller_bin || die "--binary requested but no PyInstaller build found in backend/dist"
fi

start_backend() {
  if http_ok "$HEALTH_URL"; then
    ok "backend already running at $BACKEND_URL (reusing it)"
    return 0
  fi

  local busy
  busy="$(port_listener_pid "$PORT")"
  if [ -n "$busy" ]; then
    warn "port $PORT is taken by pid $busy but $HEALTH_URL is not responding"
    die "free the port first: kill $busy"
  fi

  local log_file="$RUN_DIR/backend.log"
  : > "$log_file"

  if [ -n "$PYINSTALLER_BIN" ]; then
    log "starting the packaged backend: $PYINSTALLER_BIN"
     export NS_PACKAGED=true
     export JOB_HUNTER_DATA_DIR="$DATA_DIR"
     ( cd "$(dirname "$PYINSTALLER_BIN")" && exec "$PYINSTALLER_BIN" --port "$PORT" ) >>"$log_file" 2>&1 &
  else
    log "starting the backend with $PYTHON (log: $log_file)"
    ( cd "$BACKEND" && exec "$PYTHON" -m uvicorn app.main:app --host 127.0.0.1 --port "$PORT" ) >>"$log_file" 2>&1 &
  fi
  BACKEND_PID=$!
  BACKEND_STARTED=1
  echo "$BACKEND_PID" > "$RUN_DIR/backend.pid"

  if wait_for_url "$HEALTH_URL" "$START_TIMEOUT" "the backend"; then
    ok "backend ready at $BACKEND_URL (pid $BACKEND_PID)"
    return 0
  fi

  warn "backend did not become ready in ${START_TIMEOUT}s - last log lines:"
  tail -n 25 "$log_file" >&2 2>/dev/null
  return 1
}

start_backend || die "backend failed to start"

# -------------------------------------------------------- 4. start Electron ----

if [ "$BACKEND_ONLY" = "1" ]; then
  ok "backend-only mode: the API is live at $BACKEND_URL"
  [ "$BACKEND_STARTED" = "1" ] && dim "log: $RUN_DIR/backend.log"
  KEEP_BACKEND=1
  exit 0
fi

if [ "$MODE" = "dev" ]; then
  VITE_LOG="$RUN_DIR/vite.log"
  : > "$VITE_LOG"
  log "starting the Vite dev server on port $DEV_PORT (log: $VITE_LOG)"
  ( cd "$FRONTEND" && exec npx vite --port "$DEV_PORT" --strictPort ) >>"$VITE_LOG" 2>&1 &
  VITE_PID=$!
  wait_for_url "$DEV_URL" 60 "the Vite dev server" || {
    warn "Vite did not start - last log lines:"
    tail -n 25 "$VITE_LOG" >&2 2>/dev/null
    die "dev server failed to start"
  }
  ok "dev server ready at $DEV_URL"
fi

echo
ok "opening the NS window"
dim "press Cmd+Q in the app window (or Ctrl+C here) to quit"
echo

# The main process entry: ESM electron/main.js, falling back to the
# CommonJS shim if only that one is present.
ELECTRON_ENTRY=""
for candidate in electron/main.js electron/main.cjs; do
  if [ -f "$FRONTEND/$candidate" ]; then
    ELECTRON_ENTRY="$candidate"
    break
  fi
done
[ -n "$ELECTRON_ENTRY" ] || die "no Electron main process found in frontend/electron"

# Tell the main process which origin to load, so a stray Vite server on :5173
# cannot hijack the production launch.
JOB_HUNTER_DEV=0
[ "$MODE" = "dev" ] && JOB_HUNTER_DEV=1
export JOB_HUNTER_DEV JOB_HUNTER_PORT="$PORT" JOB_HUNTER_DEV_PORT="$DEV_PORT"

cd "$FRONTEND" || die "frontend directory is missing"
"$FRONTEND/node_modules/.bin/electron" "$ELECTRON_ENTRY"
ELECTRON_STATUS=$?

if [ "$ELECTRON_STATUS" -ne 0 ]; then
  warn "electron exited with status $ELECTRON_STATUS"
fi

exit 0
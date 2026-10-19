#!/bin/bash
# ============================================================================
#  NS - macOS build script
#
#  Produces a signed-or-not .app / .dmg / .zip in frontend/dist-electron/.
#
#  This is the exact mirror of backend/packaging/build-windows.bat:
#    1. Python dependencies
#    2. Frontend bundle (Vite)
#    3. Python backend frozen with PyInstaller
#    4. electron-builder packaging
#
#  Usage:
#    backend/packaging/build-macos.sh [--skip-frontend] [--dir-only] [--dmg-only]
# ============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
FRONTEND="$ROOT/frontend"
BACKEND="$ROOT/backend"
VENV="$BACKEND/.venv"
PY="$VENV/bin/python"
SPEC="$BACKEND/packaging/ns.spec"
BACKEND_DIST="$BACKEND/dist/NS"
EXE="$BACKEND_DIST/ns"

SKIP_FRONTEND=0
DIR_ONLY=0
DMG_ONLY=0

for arg in "$@"; do
  case "$arg" in
    --skip-frontend) SKIP_FRONTEND=1 ;;
    --dir-only)      DIR_ONLY=1 ;;
    --dmg-only)      DMG_ONLY=1 ;;
    -h|--help)       sed -n '2,14p' "$0"; exit 0 ;;
    *) echo "Unknown option: $arg" >&2; exit 2 ;;
  esac
done

banner() {
  echo
  echo "=========================================================="
  echo "  NS - macOS build"
  echo "  Project root: $ROOT"
  echo "=========================================================="
}

banner

# ---------------------------------------------------------------------------
# Step 0 - preflight
# ---------------------------------------------------------------------------
echo
echo "[0/5] Checking prerequisites..."
command -v node >/dev/null 2>&1 || { echo "ERROR: Node.js is not installed."; exit 1; }
command -v npm  >/dev/null 2>&1 || { echo "ERROR: npm is not installed."; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "ERROR: python3 is not installed."; exit 1; }

echo "  node    $(node --version)"
echo "  npm     $(npm --version)"
echo "  python  $(python3 --version 2>&1)"

if [ ! -x "$PY" ]; then
  echo "  Creating virtual environment at $VENV"
  python3 -m venv "$VENV"
fi
echo

# ---------------------------------------------------------------------------
# Step 1 - Python dependencies
# ---------------------------------------------------------------------------
echo "[1/5] Installing Python backend dependencies..."
"$PY" -m pip install --upgrade pip setuptools wheel
"$PY" -m pip install -r "$BACKEND/requirements.txt"
"$PY" -m pip install pyinstaller
echo "  Python dependencies OK."
echo

# ---------------------------------------------------------------------------
# Step 2 - frontend
# ---------------------------------------------------------------------------
echo "[2/5] Installing frontend dependencies..."
(cd "$FRONTEND" && npm ci) || (cd "$FRONTEND" && npm install)

if [ "$SKIP_FRONTEND" = "1" ]; then
  echo "  Skipping frontend build (--skip-frontend)."
else
  echo "  Building frontend with Vite..."
  (cd "$FRONTEND" && npm run build)
fi

[ -f "$FRONTEND/dist/index.html" ] || { echo "ERROR: $FRONTEND/dist/index.html was not produced."; exit 1; }
echo "  Frontend bundle OK."
echo

# ---------------------------------------------------------------------------
# Step 3 - freeze the Python backend
# ---------------------------------------------------------------------------
echo "[3/5] Freezing the Python backend with PyInstaller..."
rm -rf "$BACKEND/build" "$BACKEND/dist"
(cd "$BACKEND" && "$PY" -m PyInstaller --clean --noconfirm "$SPEC")

[ -x "$EXE" ] || {
  echo "ERROR: backend executable not found at $EXE"
  ls -la "$BACKEND/dist" || true
  exit 1
}
echo "  Backend frozen to $BACKEND_DIST"
echo

# ---------------------------------------------------------------------------
# Step 4 - package the macOS app
# ---------------------------------------------------------------------------
echo "[4/5] Packaging the macOS app with electron-builder..."
cd "$FRONTEND"
if [ "$DIR_ONLY" = "1" ]; then
  npx electron-builder --mac --dir --publish never
elif [ "$DMG_ONLY" = "1" ]; then
  npx electron-builder --mac dmg --publish never
else
  npx electron-builder --mac --publish never
fi
echo

# ---------------------------------------------------------------------------
# Step 5 - summary
# ---------------------------------------------------------------------------
echo "[5/5] Done."
echo
echo "=========================================================="
echo "  macOS build finished"
echo "=========================================================="
echo "  Unpacked : frontend/dist-electron/mac/NS.app"
echo "  Disk image: frontend/dist-electron/*.dmg"
echo "  Archive  : frontend/dist-electron/*.zip"
echo
echo "  User data lives in ~/Library/Application Support/NS"
echo "  Backend log: ~/Library/Application Support/NS/logs/backend.log"
echo
echo "  Without a Developer ID certificate the app is unsigned, so Gatekeeper"
echo "  blocks it on other Macs. See BUILD_WINDOWS.md for the equivalent"
echo "  Windows signing notes."
echo
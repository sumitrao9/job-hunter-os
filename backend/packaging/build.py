#!/usr/bin/env python3
"""Master build script for NS packaging.

Usage:
    python packaging/build.py                    # Build for current platform
    python packaging/build.py --platform macos   # Force macOS build
    python packaging/build.py --platform windows # Force Windows build

This script:
    1. Builds the frontend (vite build)
    2. Creates a launcher script
    3. Runs PyInstaller to create a standalone executable
    4. Copies the database and uploads to the dist folder
"""
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
FRONTEND_DIR = PROJECT_ROOT / "frontend"
PACKAGING_DIR = BACKEND_DIR / "packaging"
SPEC_FILE = PACKAGING_DIR / "ns.spec"


def build_frontend():
    """Build the React frontend for production."""
    print("[1/4] Building frontend...")
    subprocess.run(
        ["npm", "run", "build"],
        cwd=FRONTEND_DIR,
        check=True,
    )
    dist = FRONTEND_DIR / "dist"
    if not (dist / "index.html").exists():
        print("ERROR: Frontend build failed - index.html not found")
        sys.exit(1)
    print(f"  Frontend built to {dist}")


def prepare_env():
    """Ensure required packages are installed."""
    print("[2/4] Checking dependencies...")
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", str(BACKEND_DIR / "requirements.txt")],
        cwd=BACKEND_DIR,
        check=True,
    )
    # Install optional packages for packaging
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "pyinstaller"],
        check=True,
    )
    print("  Dependencies OK")


def build_executable(target_platform):
    """Run PyInstaller to create the executable."""
    print(f"[3/4] Packaging for {target_platform}...")

    # Clean previous builds
    for d in ["build", "dist"]:
        p = BACKEND_DIR / d
        if p.exists():
            shutil.rmtree(p)

    pyinstaller_cmd = [
        sys.executable, "-m", "PyInstaller",
        "--clean",
        "--noconfirm",
        str(SPEC_FILE),
    ]

    subprocess.run(pyinstaller_cmd, cwd=BACKEND_DIR, check=True)

    dist_dir = BACKEND_DIR / "dist" / "NS"
    if dist_dir.exists():
        print(f"  Built to {dist_dir}")
    else:
        # On macOS the bundle might be named differently
        dist_dir = BACKEND_DIR / "dist"
        print(f"  Built to {dist_dir}")
        for item in dist_dir.iterdir():
            print(f"    - {item.name}")


def finalize():
    """Copy runtime assets to the dist folder."""
    print("[4/4] Finalizing package...")
    dist_dir = BACKEND_DIR / "dist" / "NS"
    if not dist_dir.exists():
        dist_dir = BACKEND_DIR / "dist"

    # Copy database if it exists
    db_path = BACKEND_DIR / "job_hunter.db"
    if db_path.exists():
        shutil.copy2(db_path, dist_dir / "job_hunter.db")
        print("  Copied database")

    # Create .env template
    env_template = dist_dir / ".env.example"
    env_template.write_text(
        "# Copy to .env and fill in values\n"
        "OPENAI_API_KEY=\n"
        "OLLAMA_URL=http://localhost:11434\n"
        "ADZUNA_APP_ID=\n"
        "ADZUNA_APP_KEY=\n"
        "JSEARCH_API_KEY=\n"
        "USAJOBS_API_KEY=\n"
    )
    print("  Created .env.example")

    # Create launch script
    if platform.system() == "Darwin":
        launcher = dist_dir / "run.sh"
        launcher.write_text(
            "#!/bin/bash\n"
            "DIR=\"$(cd \"$(dirname \"$0\")\" && pwd)\"\n"
            "cd \"$DIR\"\n"
            "./ns --port 8000\n"
        )
        os.chmod(launcher, 0o755)
    else:
        launcher = dist_dir / "run.bat"
        launcher.write_text(
            "@echo off\n"
            "cd /d \"%~dp0\"\n"
            "ns.exe --port 8000\n"
        )

    print(f"\nPackage ready at: {dist_dir}")
    print(f"Run with: {launcher}")


def main():
    target_platform = "macos" if platform.system() == "Darwin" else "windows"
    if "--platform" in sys.argv:
        idx = sys.argv.index("--platform")
        target_platform = sys.argv[idx + 1]

    build_frontend()
    prepare_env()
    build_executable(target_platform)
    finalize()


if __name__ == "__main__":
    main()

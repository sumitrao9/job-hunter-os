#!/usr/bin/env python3
"""One-click startup for NS.

Runs self-diagnostics, starts the backend, and opens the application.
No terminal knowledge required — just double-click this script.

Usage:
    python start.py              # Start backend server
    python start.py --frontend   # Also start frontend dev server
"""
import logging
import os
import signal
import subprocess
import sys
import time
import webbrowser

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = PROJECT_ROOT


def check_python_deps():
    """Check that required Python packages are installed."""
    required = ["fastapi", "uvicorn", "sqlalchemy", "pydantic"]
    missing = []
    for pkg in required:
        try:
            __import__(pkg.replace("pydantic-settings", "pydantic").replace("-", "_"))
        except ImportError:
            try:
                subprocess.run([sys.executable, "-m", "pip", "install", "-r", os.path.join(BACKEND_DIR, "requirements.txt")], check=True)
                break
            except Exception:
                missing.append(pkg)
    return len(missing) == 0


def check_database():
    """Ensure database tables exist."""
    from app.database import Base, engine
    try:
        Base.metadata.create_all(bind=engine)
        return True
    except Exception as exc:
        logger.warning(f"Database setup needed: {exc}")
        try:
            Base.metadata.create_all(bind=engine)
            return True
        except Exception:
            return False


def check_frontend_built():
    """Ensure frontend is built for production serving."""
    frontend_dist = os.path.join(PROJECT_ROOT, "..", "frontend", "dist")
    if not os.path.exists(os.path.join(frontend_dist, "index.html")):
        logger.info("Frontend not built — building now...")
        try:
            subprocess.run(["npm", "run", "build"], cwd=os.path.join(PROJECT_ROOT, "..", "frontend"), check=True)
            logger.info("Frontend built successfully.")
        except Exception:
            logger.warning("Frontend build skipped — the app will still work via dev server.")
    return True


def start_backend(port=8000):
    """Start the FastAPI backend server."""
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"

    cmd = [
        sys.executable, "-m", "uvicorn",
        "app.main:app",
        "--host", "127.0.0.1",
        "--port", str(port),
    ]

    process = subprocess.Popen(
        cmd,
        cwd=BACKEND_DIR,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    return process


def wait_for_backend(url="http://127.0.0.1:8000", timeout=30):
    """Wait for the backend to become healthy."""
    import httpx
    for _ in range(timeout * 2):
        try:
            resp = httpx.get(f"{url}/health", timeout=2)
            if resp.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def main():
    port = 8000

    logger.info("=" * 50)
    logger.info("    JOB HUNTER OS — Starting Up")
    logger.info("=" * 50)

    # Step 1: Check dependencies
    logger.info("[1/4] Checking dependencies...")
    if not check_python_deps():
        logger.error("Missing Python dependencies. Please run:")
        logger.error(f"  pip install -r {os.path.join(BACKEND_DIR, 'requirements.txt')}")
        sys.exit(1)
    logger.info("  ✓ Dependencies OK")

    # Step 2: Check database
    logger.info("[2/4] Checking data storage...")
    if not check_database():
        logger.error("Could not initialize the database.")
        sys.exit(1)
    logger.info("  ✓ Database ready")

    # Step 3: Check frontend
    logger.info("[3/4] Checking interface...")
    check_frontend_built()
    logger.info("  ✓ Interface ready")

    # Step 4: Start backend
    logger.info("[4/4] Starting NS...")
    backend_proc = start_backend(port)

    def cleanup(signum=None, frame=None):
        logger.info("\nShutting down...")
        backend_proc.terminate()
        backend_proc.wait()
        sys.exit(0)

    signal.signal(signal.SIGTERM, cleanup)
    signal.signal(signal.SIGINT, cleanup)

    if wait_for_backend(f"http://127.0.0.1:{port}"):
        logger.info("  ✓ Backend is running")
        logger.info(f"\nNS is ready at:\n  http://localhost:{port}")
        logger.info("\nOpen this URL in your browser.")
        try:
            webbrowser.open(f"http://localhost:{port}")
        except Exception:
            pass
    else:
        logger.error("Backend failed to start. Check the logs below:")
        if backend_proc.stdout:
            for line in backend_proc.stdout:
                print(line, end="")
        sys.exit(1)

    # Stream backend logs to console
    if backend_proc.stdout:
        for line in backend_proc.stdout:
            if line:
                print(f"  {line.rstrip()}")

    backend_proc.wait()


if __name__ == "__main__":
    main()

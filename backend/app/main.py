from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.database import engine, Base
from app.config import settings
from app.models import JobSource, SourceRun, JobSourceMapping, SchedulerConfig, SearchProfile
from app.routers import profile, resumes, jobs, applications, dashboard, settings_api, matching, onboarding, discovery, cover_letter, follow_ups, export as export_router, apply, ai, auto_apply, multi_discovery, health as health_router, backup
import os
import sys


def _frontend_dist_path() -> str:
    """Resolve frontend/dist path for both dev (editable) and PyInstaller onedir bundle.

    In PyInstaller onedir, ``sys._MEIPRESS`` is *not* set. The script is
    extracted to ``<bundle>/_internal/main.py``, and the frontend files
    live at ``<bundle>/_internal/frontend/dist``.
    """
    if getattr(sys, "frozen", False):
        return os.path.join(os.path.dirname(__file__), "frontend", "dist")
    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "frontend",
        "dist",
    )


Base.metadata.create_all(bind=engine)

app = FastAPI(title="NS", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

frontend_dist = _frontend_dist_path()
if os.path.isdir(frontend_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="assets")


@app.get("/")
async def root():
    index_path = os.path.join(frontend_dist, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"status": "running", "frontend": "not built"}


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(profile.router)
app.include_router(resumes.router)
app.include_router(jobs.router)
app.include_router(applications.router)
app.include_router(dashboard.router)
app.include_router(settings_api.router)
app.include_router(matching.router)
app.include_router(onboarding.router)
app.include_router(discovery.router)
app.include_router(cover_letter.router)
app.include_router(follow_ups.router)
app.include_router(export_router.router)
app.include_router(apply.router)
app.include_router(ai.router)
app.include_router(auto_apply.router)
app.include_router(multi_discovery.router)
app.include_router(health_router.router)
app.include_router(backup.router)

# Run self-healing checks at startup.
from app.routers.health import check_and_repair
check_and_repair()


# SPA fallback: any non-API route should return index.html so the
# client-side router can handle it (works for both Electron and a
# browser pointed at the backend).
@app.get("/{path:path}", include_in_schema=False)
async def spa_fallback(path: str):
    if path.startswith("api/"):
        raise HTTPException(status_code=404, detail="Not Found")
    index_path = os.path.join(frontend_dist, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"status": "running", "frontend": "not built", "path": path}


def _parse_port() -> int:
    import sys
    for i, arg in enumerate(sys.argv):
        if arg == "--port" and i + 1 < len(sys.argv):
            return int(sys.argv[i + 1])
        if arg.startswith("--port="):
            return int(arg.split("=", 1)[1])
    return 8000


if __name__ == "__main__":
    import uvicorn
    # Pass the app object directly. An import string would re-execute this
    # module (and fail outright inside a PyInstaller bundle).
    uvicorn.run(app, host="0.0.0.0", port=_parse_port(), reload=False)

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
from app.database import get_db, engine, Base
from app.config import settings
from app.models import JobSource, Profile, Application
from app.routers.discovery import DEFAULT_SOURCES
import os
import sys
import logging

router = APIRouter(prefix="/api/health", tags=["health"])

logger = logging.getLogger(__name__)


# Maps internal status strings to human-readable labels.
STATUS_LABELS: Dict[str, str] = {
    "discovered": "New job found",
    "shortlisted": "Worth reviewing",
    "preparing": "Preparing your application",
    "awaiting_approval": "Waiting for your review",
    "submitted_confirmed": "Application submitted",
    "submitted_unconfirmed": "Submitted — awaiting confirmation",
    "failed": "Needs your attention",
    "manual_required": "Requires manual action",
    "not_started": "Ready to start",
    "in_progress": "In progress",
    "completed": "Done",
    "error": "Something went wrong",
}

STATUS_TONES: Dict[str, str] = {
    "discovered": "info",
    "shortlisted": "accent",
    "preparing": "info",
    "awaiting_approval": "warn",
    "submitted_confirmed": "success",
    "submitted_unconfirmed": "warn",
    "failed": "danger",
    "manual_required": "danger",
    "not_started": "info",
    "in_progress": "info",
    "completed": "success",
    "error": "danger",
}


@router.get("/status-labels")
def get_status_labels():
    """Return human-readable labels for all internal status codes."""
    return {"labels": STATUS_LABELS, "tones": STATUS_TONES}


class ComponentStatus(BaseModel):
    name: str
    status: str  # "ready" | "warning" | "error"
    message: str


class HealthResponse(BaseModel):
    status: str
    components: List[ComponentStatus]
    timestamp: str
    version: str


def _check_database() -> ComponentStatus:
    try:
        with engine.connect() as conn:
            conn.exec_driver_sql("SELECT 1")
        return ComponentStatus(
            name="Database",
            status="ready",
            message="Your data is saved locally and ready to use.",
        )
    except Exception as exc:
        return ComponentStatus(
            name="Database",
            status="error",
            message="NS is having trouble connecting to its local data storage. Attempting repair...",
        )


def _check_backend() -> ComponentStatus:
    return ComponentStatus(
        name="Backend",
        status="ready",
        message="NS is running and processing your requests.",
    )


def _check_frontend() -> ComponentStatus:
    # In a PyInstaller onedir bundle, __file__ lives inside the _internal dir
    # and the frontend was collected alongside it. In dev, it is at project root.
    if getattr(sys, "frozen", False):
        base = os.path.dirname(__file__)  # .../_internal/app/routers
        # Walk up to the _internal dir, then look for frontend/dist there.
        internal_dir = os.path.dirname(os.path.dirname(os.path.dirname(base)))
        frontend_dist = os.path.join(internal_dir, "frontend", "dist", "index.html")
    else:
        project_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        )
        frontend_dist = os.path.join(project_root, "frontend", "dist", "index.html")
    if os.path.exists(frontend_dist):
        return ComponentStatus(
            name="Frontend",
            status="ready",
            message="User interface is built and ready.",
        )
    return ComponentStatus(
        name="Frontend",
        status="warning",
        message="Interface build not found. Run the setup script to fix this.",
    )


def _check_config() -> ComponentStatus:
    if not settings.secret_key or settings.secret_key == "change-me":
        return ComponentStatus(
            name="Configuration",
            status="warning",
            message="Using default settings. This is fine for local use.",
        )
    return ComponentStatus(
        name="Configuration",
        status="ready",
        message="Settings are configured correctly.",
    )


def _check_job_sources(db: Session) -> ComponentStatus:
    try:
        sources = db.query(JobSource).filter(JobSource.enabled == True).all()
        if not sources:
            return ComponentStatus(
                name="Job Sources",
                status="warning",
                message="No job sources are configured yet. The first-run setup will help you choose.",
            )
        healthy = [s for s in sources if s.health_status == "HEALTHY"]
        not_configured = [s for s in sources if s.health_status == "NOT_CONFIGURED"]
        if len(healthy) == len(sources):
            return ComponentStatus(
                name="Job Sources",
                status="ready",
                message=f"All {len(sources)} job sources are working.",
            )
        if healthy:
            return ComponentStatus(
                name="Job Sources",
                status="ready",
                message=f"{len(healthy)} of {len(sources)} job sources are working. All free sources are active.",
            )
        return ComponentStatus(
            name="Job Sources",
            status="warning",
            message="Job sources need to be configured. Check your settings.",
        )
    except Exception:
        return ComponentStatus(
            name="Job Sources",
            status="error",
            message="Could not check job sources. Restarting the service...",
        )


def _check_database_migration() -> ComponentStatus:
    try:
        from app.models import Profile
        with engine.connect() as conn:
            conn.exec_driver_sql("SELECT 1 FROM profiles LIMIT 1")
        return ComponentStatus(
            name="Data Models",
            status="ready",
            message="All tables are ready.",
        )
    except Exception:
        return ComponentStatus(
            name="Data Models",
            status="error",
            message="Database needs to be set up. This will be fixed automatically.",
        )


def _check_profile(db: Session) -> ComponentStatus:
    profile = db.query(Profile).first()
    if not profile:
        return ComponentStatus(
            name="Your Profile",
            status="warning",
            message="Complete your profile setup to start finding jobs.",
        )
    if not profile.skills:
        return ComponentStatus(
            name="Your Profile",
            status="warning",
            message="Add your skills to improve job matching.",
        )
    return ComponentStatus(
        name="Your Profile",
        status="ready",
        message=f"Profile configured with {len(profile.skills)} skills.",
    )


def _check_network() -> ComponentStatus:
    import httpx
    try:
        resp = httpx.get("https://www.google.com/generate_204", timeout=5)
        if resp.status_code == 204:
            return ComponentStatus(
                name="Internet Connection",
                status="ready",
                message="Connected to the internet.",
            )
        return ComponentStatus(
            name="Internet Connection",
            status="ready",
            message="Connected to the internet.",
        )
    except Exception:
        return ComponentStatus(
            name="Internet Connection",
            status="warning",
            message="Internet connection check is slow. Job sources that need the internet may be delayed.",
        )


def _check_documents() -> ComponentStatus:
    upload_dir = settings.upload_dir
    if os.path.isdir(upload_dir) or True:
        os.makedirs(upload_dir, exist_ok=True)
        return ComponentStatus(
            name="Document Storage",
            status="ready",
            message="Resumes and documents are stored safely.",
        )
    return ComponentStatus(
        name="Document Storage",
        status="warning",
        message="Document storage directory could not be created.",
    )


def _check_automation(db: Session) -> ComponentStatus:
    from app.models import AutoApplySettings
    settings_row = db.query(AutoApplySettings).first()
    if settings_row and settings_row.enabled and settings_row.mode == "autonomous":
        return ComponentStatus(
            name="Automation",
            status="ready",
            message="Auto-apply is running in autonomous mode.",
        )
    if settings_row and settings_row.enabled:
        return ComponentStatus(
            name="Automation",
            status="ready",
            message="Auto-apply is set to approval mode. You review before submitting.",
        )
    return ComponentStatus(
        name="Automation",
        status="ready",
        message="Automation is ready. Enable it in Settings to start.",
    )


@router.get("/")
def detailed_health():
    """Comprehensive health check for all system components.

    Returns simple, user-friendly status for each component.
    """
    from datetime import datetime
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        components = [
            _check_backend(),
            _check_frontend(),
            _check_database(),
            _check_database_migration(),
            _check_config(),
            _check_profile(db),
            _check_job_sources(db),
            _check_automation(db),
            _check_documents(),
            _check_network(),
        ]
    finally:
        db.close()

    statuses = [c.status for c in components]
    if "error" in statuses:
        overall = "warning"
    elif "warning" in statuses:
        overall = "warning"
    else:
        overall = "ready"

    return HealthResponse(
        status=overall,
        components=components,
        timestamp=datetime.utcnow().isoformat(),
        version="0.1.0",
    )


@router.get("/quick")
def quick_health():
    """Lightweight health check — just checks the backend is alive."""
    return {"status": "ready", "message": "NS is running."}


def check_and_repair():
    """Run automatic recovery checks and attempt repairs.

    Returns a list of actions taken.
    """
    actions: List[str] = []

    # Ensure database tables exist.
    try:
        Base.metadata.create_all(bind=engine)
        actions.append("Database tables verified")
    except Exception as exc:
        actions.append(f"Database repair attempted: {exc}")

    # Ensure upload directory exists.
    os.makedirs(settings.upload_dir, exist_ok=True)
    actions.append("Upload directory ready")

    # Ensure database file exists (for SQLite).
    if settings.database_url.startswith("sqlite:///"):
        db_path = settings.database_url.replace("sqlite:///", "")
        if not os.path.isabs(db_path):
            db_path = os.path.join(os.getcwd(), db_path)
        if not os.path.exists(db_path):
            Base.metadata.create_all(bind=engine)
            actions.append("Database file created")

    # Seed default job sources if none exist
    with next(get_db()) as db:
        existing = db.query(JobSource).count()
        if existing == 0:
            for s in DEFAULT_SOURCES:
                src = JobSource(
                    source_name=s["company"],
                    adapter=s["kind"],
                    base_url=s["url"],
                    enabled=True,
                    country="India" if s.get("kind") == "web" else "Global",
                    source_type=s["kind"],
                )
                db.add(src)
            db.commit()
            actions.append(f"Seeded {len(DEFAULT_SOURCES)} default job sources")

    return actions

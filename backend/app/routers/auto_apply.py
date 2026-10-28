from __future__ import annotations

import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    ApplicationAttempt,
    ApprovalRecord,
    AutoApplySettings,
    Profile,
)
from app.services.auto_apply_workflow import (
    get_pending_approvals,
    get_stats,
    process_approval,
    run_auto_apply_pipeline,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auto-apply", tags=["auto-apply"])


# ---------- Schemas ----------

class AutoApplySettingsSchema(BaseModel):
    id: str = "singleton"
    enabled: bool = False
    emergency_stop: bool = False
    mode: str = "manual"
    min_match_score: int = 50
    max_per_day: int = 5
    preferred_titles: list[str] | None = None
    preferred_locations: list[str] | None = None
    min_salary: int | None = None
    remote_only: bool = False
    experience_level: str | None = None
    sources: list[str] | None = None
    default_resume_id: str | None = None
    generate_cover_letter: bool = True
    auto_submit_enabled: bool = False

    model_config = ConfigDict(from_attributes=True)


class AttemptSchema(BaseModel):
    id: str
    application_id: str | None
    job_id: str
    status: str
    step: str | None
    error: str | None
    started_at: datetime | None
    finished_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class ApprovalSchema(BaseModel):
    id: str
    attempt_id: str
    application_id: str | None
    decision: str
    reviewer: str | None
    notes: str | None
    decided_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


# ---------- Settings ----------

@router.get("/settings", response_model=AutoApplySettingsSchema)
def get_auto_apply_settings(db: Session = Depends(get_db)):
    settings_row = db.query(AutoApplySettings).first()
    if not settings_row:
        settings_row = AutoApplySettings(id="singleton")
        db.add(settings_row)
        db.commit()
        db.refresh(settings_row)
    return AutoApplySettingsSchema.model_validate(settings_row)


@router.post("/settings", response_model=AutoApplySettingsSchema)
def update_auto_apply_settings(payload: AutoApplySettingsSchema, db: Session = Depends(get_db)):
    row = db.query(AutoApplySettings).first()
    if not row:
        row = AutoApplySettings(id="singleton")
        db.add(row)
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return AutoApplySettingsSchema.model_validate(row)


# ---------- Execution ----------

class StartResponse(BaseModel):
    ok: bool
    message: str
    attempt_id: str | None = None


@router.post("/start", response_model=StartResponse)
def start_auto_apply(db: Session = Depends(get_db)):
    settings_row = db.query(AutoApplySettings).first()
    if not settings_row or not settings_row.enabled:
        raise HTTPException(status_code=400, detail="Auto-apply is disabled. Enable it in settings first.")
    if settings_row.emergency_stop:
        raise HTTPException(status_code=400, detail="Emergency stop is active. Clear it before starting.")
    profile = db.query(Profile).first()
    if not profile:
        raise HTTPException(status_code=400, detail="Complete your profile first.")

    attempt_id = uuid.uuid4().hex

    import threading
    def _run_pipeline():
        try:
            db2 = next(get_db())
            run_auto_apply_pipeline(db2, limit=20)
            db2.close()
        except Exception as exc:
            logger.error("Pipeline thread failed: %s", exc)

    thread = threading.Thread(target=_run_pipeline, daemon=True)
    thread.start()

    return StartResponse(ok=True, message="Auto-apply execution started.", attempt_id=attempt_id)


@router.get("/queue", response_model=list)
def get_approval_queue(db: Session = Depends(get_db)):
    """List pending approvals with full application context."""
    return get_pending_approvals(db)


@router.post("/approvals/{approval_id}/process", response_model=ApprovalSchema)
def process_approval_endpoint(
    approval_id: str,
    payload: ApprovalDecision,
    db: Session = Depends(get_db),
):
    result = process_approval(db, approval_id, payload.decision, payload.notes)
    if result["status"] == "not_found":
        raise HTTPException(status_code=404, detail="Approval record not found.")
    if result["status"] == "already_decided":
        raise HTTPException(status_code=400, detail="Approval already decided.")

    record = db.query(ApprovalRecord).filter(ApprovalRecord.id == approval_id).first()
    db.refresh(record)
    return ApprovalSchema.model_validate(record)


@router.get("/stats")
def get_auto_apply_stats(db: Session = Depends(get_db)):
    return get_stats(db)


@router.post("/stop")
def stop_auto_apply(db: Session = Depends(get_db)):
    settings_row = db.query(AutoApplySettings).first()
    if not settings_row:
        raise HTTPException(status_code=404, detail="Settings not found.")
    settings_row.emergency_stop = True
    db.commit()
    return {"ok": True, "message": "Emergency stop activated."}


@router.get("/status")
def get_auto_apply_status(db: Session = Depends(get_db)):
    settings_row = db.query(AutoApplySettings).first()
    active = (
        db.query(ApplicationAttempt)
        .filter(ApplicationAttempt.status == "in_progress")
        .order_by(ApplicationAttempt.started_at.desc())
        .first()
    )
    return {
        "enabled": bool(settings_row and settings_row.enabled),
        "emergency_stop": bool(settings_row and settings_row.emergency_stop),
        "mode": settings_row.mode if settings_row else "manual",
        "active_attempt": AttemptSchema.model_validate(active) if active else None,
    }


@router.get("/history", response_model=list[AttemptSchema])
def get_auto_apply_history(db: Session = Depends(get_db)):
    return (
        db.query(ApplicationAttempt)
        .order_by(ApplicationAttempt.started_at.desc())
        .limit(100)
        .all()
    )


# ---------- Approval Queue ----------

class ApprovalDecision(BaseModel):
    decision: str  # approved | rejected
    notes: str | None = None


class SubmitRequest(BaseModel):
    dry_run: bool = False


@router.post("/approvals/{approval_id}/submit", response_model=ApprovalSchema)
def submit_application(approval_id: str, payload: SubmitRequest, db: Session = Depends(get_db)):
    """Manually trigger Playwright submission for a queued application."""
    record = db.query(ApprovalRecord).filter(ApprovalRecord.id == approval_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Approval record not found.")
    if record.decision != "pending":
        raise HTTPException(status_code=400, detail="Approval already decided.")

    # Mark as approved, then trigger actual submission
    from app.services.auto_apply_workflow import process_approval
    result = process_approval(db, approval_id, "approved", f"Manual submit{' (dry-run)' if payload.dry_run else ''}")
    if result.get("status") != "ok":
        raise HTTPException(status_code=500, detail=result.get("message", "Submission failed"))

    db.refresh(record)
    return ApprovalSchema.model_validate(record)


@router.get("/approvals", response_model=list[ApprovalSchema])
def list_approvals(db: Session = Depends(get_db)):
    return (
        db.query(ApprovalRecord)
        .filter(ApprovalRecord.decision == "pending")
        .order_by(ApprovalRecord.decided_at.desc())
        .all()
    )


@router.post("/approvals/{approval_id}/decision", response_model=ApprovalSchema)
def decide_approval(approval_id: str, payload: ApprovalDecision, db: Session = Depends(get_db)):
    record = db.query(ApprovalRecord).filter(ApprovalRecord.id == approval_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Approval record not found.")
    if record.decision != "pending":
        raise HTTPException(status_code=400, detail="Approval already decided.")
    record.decision = payload.decision
    record.notes = payload.notes
    record.decided_at = datetime.utcnow()
    db.commit()
    db.refresh(record)
    return ApprovalSchema.model_validate(record)


@router.post("/attempts/{attempt_id}/complete")
def complete_attempt(
    attempt_id: str,
    status: str = "submitted_confirmed",
    db: Session = Depends(get_db),
):
    attempt = db.query(ApplicationAttempt).filter(ApplicationAttempt.id == attempt_id).first()
    if not attempt:
        raise HTTPException(status_code=404, detail="Attempt not found.")
    attempt.status = status
    attempt.finished_at = datetime.utcnow()
    db.commit()
    return {"ok": True, "status": attempt.status}

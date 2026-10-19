#!/usr/bin/env python3
"""Auto-apply workflow: discovery -> matching -> preparation -> approval queue.

This is the orchestration layer that ties together:
  1. multi_discovery.discover()  — find jobs from configured sources
  2. matching.score_job_against_profile() — score each job
  3. application_prep.prepare_application() — generate cover letter + form answers
  4. ApprovalRecord creation — human-in-the-loop before submission

In "autonomous" mode the workflow can also drive Playwright-based submission
on supported ATS platforms, but this is OFF by default and requires explicit
user opt-in with the emergency_stop reset.
"""
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.models import (
    Job,
    Profile,
    Application,
    ApplicationAttempt,
    ApprovalRecord,
    AutoApplySettings,
    JobSource,
    Resume,
)
from app.services.multi_discovery import discover
from app.services.matching import score_job_against_profile
from app.services.application_prep import prepare_application

logger = logging.getLogger(__name__)


def _get_settings(db: Session) -> Optional[AutoApplySettings]:
    return db.query(AutoApplySettings).first()


def _get_enabled_sources(db: Session) -> List[Dict]:
    sources = db.query(JobSource).filter(JobSource.enabled == True).all()
    return [
        {
            "id": s.id,
            "source_name": s.source_name,
            "adapter": s.adapter,
            "base_url": s.base_url,
            "config": s.config or {},
            "company": s.source_name,
        }
        for s in sources
    ]


def _filter_jobs(jobs: List[Job], profile: Profile, settings: AutoApplySettings) -> List[Job]:
    """Apply user-configured filters before preparing applications."""
    filtered = []
    keywords_include = (profile.search_keywords or []) if hasattr(profile, "search_keywords") else []
    keywords_exclude = (profile.search_exclusions or []) if hasattr(profile, "search_exclusions") else []
    preferred_titles = settings.preferred_titles or []
    preferred_locations = settings.preferred_locations or []

    for job in jobs:
        title_lower = (job.title or "").lower()
        desc_lower = (job.description or "").lower()
        combined = f"{title_lower} {desc_lower}"

        # Exclude keywords
        if keywords_exclude:
            if any(ex.lower() in combined for ex in keywords_exclude):
                continue
        if keywords_include:
            if not any(kw.lower() in combined for kw in keywords_include):
                continue

        # Preferred titles filter (if set)
        if preferred_titles:
            if not any(t.lower() in title_lower for t in preferred_titles):
                continue

        # Preferred locations filter (if set)
        if preferred_locations:
            loc = (job.location or "").lower()
            if loc and not any(l.lower() in loc for l in preferred_locations):
                continue

        # Remote-only filter
        if settings.remote_only and not job.remote:
            continue

        # Min salary filter
        if settings.min_salary and job.salary_min and job.salary_min < settings.min_salary:
            continue

        filtered.append(job)

    return filtered


def run_discovery_step(db: Session, settings: AutoApplySettings) -> Dict:
    """Run job discovery from all enabled sources."""
    sources = _get_enabled_sources(db)
    if not sources:
        return {"status": "no_sources", "total_found": 0, "sources": []}

    max_workers = 4 if len(sources) <= 16 else 8
    result = discover(sources, max_workers=max_workers)

    db.commit()
    logger.info(
        "Discovery complete: %d found, %d imported, %d duplicates, %d failed",
        result["total_found"],
        result["imported"],
        result["duplicates"],
        result["failed"],
    )
    return result


def run_matching_step(db: Session, profile: Profile, settings: AutoApplySettings, limit: int = 20) -> List[Job]:
    """Fetch recently-discovered jobs and score them against the profile.

    Only jobs that haven't been scored yet are processed.
    """
    jobs = (
        db.query(Job)
        .filter(Job.status == "discovered")
        .order_by(Job.scraped_at.desc())
        .limit(limit)
        .all()
    )

    scored = []
    for job in jobs:
        try:
            result = score_job_against_profile(profile, job)
            job.match_score = result.score
            job.match_evidence = result.evidence
            db.add(job)
            if result.score >= settings.min_match_score:
                scored.append(job)
        except Exception as exc:
            logger.warning("Scoring failed for job %s: %s", job.id, exc)

    db.commit()
    scored.sort(key=lambda j: j.match_score or 0, reverse=True)
    logger.info("Matching complete: %d/%d jobs passed min_score=%s", len(scored), len(jobs), settings.min_match_score)
    return scored


def run_preparation_step(db: Session, jobs: List[Job], profile: Profile, settings: AutoApplySettings) -> List[Application]:
    """Prepare application packages and queue them for approval."""
    # Check daily limit
    today = datetime.utcnow().date()
    today_start = datetime(today.year, today.month, today.day)
    today_applications = db.query(Application).filter(Application.date_discovered >= today_start).count()
    remaining = max(0, settings.max_per_day - today_applications)

    jobs_to_process = jobs[:remaining] if remaining else []
    prepared_applications: List[Application] = []

    for job in jobs_to_process:
        try:
            existing = db.query(Application).filter(Application.job_id == job.id).first()
            if existing:
                continue

            prepared = prepare_application(profile, job)

            application = Application(
                id=uuid.uuid4().hex,
                job_id=job.id,
                company=job.company or "",
                job_title=job.title or "",
                job_url=job.url,
                source=job.source,
                match_score=job.match_score or 0,
                status="preparing",
                cover_letter=prepared.get("cover_letter", ""),
                form_answers=prepared.get("form_answers", {}),
                date_discovered=datetime.utcnow(),
            )
            db.add(application)
            db.flush()

            # Create approval record in "approval" mode
            if settings.mode in ("approval", "autonomous"):
                approval = ApprovalRecord(
                    id=uuid.uuid4().hex,
                    attempt_id=None,
                    application_id=application.id,
                    decision="pending",
                    notes=None,
                )
                db.add(approval)

            # Mark job as shortlisted so we don't re-score it
            job.status = "shortlisted"
            db.add(job)
            db.flush()

            prepared_applications.append(application)

        except Exception as exc:
            logger.warning("Preparation failed for job %s: %s", job.id, exc)

    db.commit()
    logger.info("Preparation complete: %d applications prepared and queued", len(prepared_applications))
    return prepared_applications


def run_auto_apply_pipeline(db: Session, limit: int = 20) -> Dict:
    """Execute the full auto-apply pipeline: discover -> match -> prepare -> approve.

    Returns a summary dict with per-stage counts.
    """
    settings_row = _get_settings(db)
    if not settings_row or not settings_row.enabled:
        return {"status": "disabled", "message": "Auto-apply is not enabled."}
    if settings_row.emergency_stop:
        return {"status": "emergency_stop", "message": "Emergency stop is active."}

    profile = db.query(Profile).first()
    if not profile:
        return {"status": "no_profile", "message": "Complete your profile first."}

    attempt = ApplicationAttempt(
        id=uuid.uuid4().hex,
        application_id=None,
        job_id="",
        status="in_progress",
        step="discovery",
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)

    summary: Dict = {"attempt_id": attempt.id, "stages": {}}

    try:
        # Stage 1: Discovery
        attempt.step = "discovery"
        db.commit()
        discovery = run_discovery_step(db, settings_row)
        summary["stages"]["discovery"] = discovery

        # Stage 2: Matching
        attempt.step = "matching"
        db.commit()
        matched_jobs = run_matching_step(db, profile, settings_row, limit=limit)
        summary["stages"]["matching"] = {"scored": len(matched_jobs), "passed_threshold": len(matched_jobs)}

        # Stage 3: Preparation
        attempt.step = "preparation"
        db.commit()
        prepared = run_preparation_step(db, matched_jobs, profile, settings_row)
        summary["stages"]["preparation"] = {"prepared": len(prepared), "queued_for_approval": len(prepared)}

        # Stage 4: Approval
        attempt.step = "approval"
        attempt.status = "completed"
        attempt.finished_at = datetime.utcnow()
        db.commit()

        summary["status"] = "success"
        summary["total_prepared"] = len(prepared)

    except Exception as exc:
        logger.exception("Auto-apply pipeline failed")
        attempt.status = "failed"
        attempt.finished_at = datetime.utcnow()
        attempt.error = str(exc)[:500]
        db.commit()
        summary["status"] = "failed"
        summary["error"] = str(exc)[:200]

    return summary


def get_pending_approvals(db: Session, limit: int = 50) -> List[Dict]:
    """Return pending approval records with full application context."""
    approvals = (
        db.query(ApprovalRecord)
        .filter(ApprovalRecord.decision == "pending")
        .order_by(ApprovalRecord.decided_at.desc())
        .limit(limit)
        .all()
    )
    result = []
    for a in approvals:
        app = a.application
        job = app.job if app.job_id else None
        result.append({
            "approval_id": a.id,
            "application_id": a.application_id,
            "job_title": app.job_title if app else "",
            "company": app.company if app else "",
            "match_score": app.match_score if app else None,
            "cover_letter": app.cover_letter if app else "",
            "form_answers": app.form_answers if app else {},
            "job_url": app.job_url if app else "",
            "source": app.source if app else "",
            "created_at": a.decided_at.isoformat() if a.decided_at else None,
        })
    return result


def process_approval(db: Session, approval_id: str, decision: str, notes: Optional[str] = None) -> Dict:
    """Process an approval decision.

    If 'approved', attempts Playwright submission via application_submission.
    Otherwise just records the decision for manual follow-up.
    """
    record = db.query(ApprovalRecord).filter(ApprovalRecord.id == approval_id).first()
    if not record:
        return {"status": "not_found"}

    if record.decision != "pending":
        return {"status": "already_decided", "decision": record.decision}

    record.decision = decision
    record.notes = notes
    record.decided_at = datetime.utcnow()

    application = record.application
    if application:
        if decision == "approved":
            settings_row = _get_settings(db)
            # In autonomous mode OR when user clicks "Submit", run Playwright submission
            submit_result = _try_submit_application(db, application, settings_row)
            if submit_result.get("status") == "submitted_confirmed":
                application.status = "submitted_confirmed"
            elif submit_result.get("status") == "submitted_unconfirmed":
                application.status = "submitted_unconfirmed"
            else:
                application.status = "awaiting_submission"
            application.submission_log = json.dumps(submit_result)
        else:
            application.status = "rejected"

    db.commit()
    return {
        "status": "ok",
        "decision": decision,
        "application_id": record.application_id,
        "submission": json.loads(application.submission_log) if application and application.submission_log else None,
    }


def _try_submit_application(db: Session, application: Application, settings_row) -> Dict:
    """Attempt Playwright submission; returns immediately if Playwright unavailable."""
    import json as _json

    profile = db.query(Profile).first()
    if not profile:
        return {"status": "error", "message": "No profile configured"}

    profile_data = {
        "first_name": profile.full_name.split()[0] if profile.full_name else "",
        "last_name": " ".join(profile.full_name.split()[1:]) if profile.full_name else "",
        "full_name": profile.full_name or "",
        "email": profile.email or "",
        "phone": profile.phone or "",
    }

    resume_path = None
    resume = db.query(Resume).filter(Resume.is_default == True).first()
    if not resume:
        resume = db.query(Resume).order_by(Resume.created_at.desc()).first()
    if resume:
        candidate = os.path.join(settings.data_dir, "uploads", resume.stored_filename)
        if os.path.exists(candidate):
            resume_path = candidate

    job_url = application.job_url
    if not job_url:
        return {"status": "error", "message": "No job URL on application"}

    # Run submission in background thread (it's async)
    import threading

    result = {"status": "error", "message": "Submission not attempted"}

    def _run():
        nonlocal result
        try:
            from app.application_submission import submit_job_application
            _result = asyncio.run(submit_job_application(
                job_url=job_url,
                profile_data=profile_data,
                resume_path=resume_path,
                headless=True,
                dry_run=False,
            ))
            result = _result
        except Exception as exc:
            result = {"status": "error", "message": str(exc)}

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    thread.join(timeout=120)  # Wait up to 2 minutes for submission

    return result


def get_stats(db: Session) -> Dict:
    settings_row = _get_settings(db)
    pending_approvals = db.query(ApprovalRecord).filter(ApprovalRecord.decision == "pending").count()
    active_attempts = db.query(ApplicationAttempt).filter(ApplicationAttempt.status == "in_progress").count()

    return {
        "enabled": bool(settings_row and settings_row.enabled),
        "emergency_stop": bool(settings_row and settings_row.emergency_stop),
        "mode": settings_row.mode if settings_row else "manual",
        "min_match_score": settings_row.min_match_score if settings_row else 50,
        "max_per_day": settings_row.max_per_day if settings_row else 5,
        "pending_approvals": pending_approvals,
        "active_attempts": active_attempts,
        "auto_submit_enabled": bool(settings_row and settings_row.auto_submit_enabled),
    }

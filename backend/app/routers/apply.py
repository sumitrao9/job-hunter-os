from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Profile, Job, Application
from app.services.application_prep import prepare_application, generate_follow_up_message
from pydantic import BaseModel
from typing import Optional
import uuid
from datetime import datetime

router = APIRouter(prefix="/api/apply", tags=["apply"])


class PrepareRequest(BaseModel):
    job_id: Optional[str] = None
    application_id: Optional[str] = None


class FollowUpRequest(BaseModel):
    application_id: str


@router.post("/prepare")
def prepare_application_endpoint(request: PrepareRequest, db: Session = Depends(get_db)):
    """Build an application package. Never submits anything.

    Errors are raised as HTTP status codes so the UI can distinguish a
    failure from a successful package instead of rendering undefined fields.
    """
    if not request.job_id and not request.application_id:
        raise HTTPException(status_code=400, detail="Select a job or an application first.")

    application = None
    if request.application_id:
        application = (
            db.query(Application).filter(Application.id == request.application_id).first()
        )
        if not application:
            raise HTTPException(status_code=404, detail="Application not found.")

    job = None
    if request.job_id:
        job = db.query(Job).filter(Job.id == request.job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found.")
    elif application and application.job_id:
        job = db.query(Job).filter(Job.id == application.job_id).first()

    profile = db.query(Profile).first()
    if not profile:
        raise HTTPException(status_code=400, detail="Complete your profile before preparing an application.")

    if not job and application:
        # An application can exist without a linked job; build from what we have.
        job = Job(
            id=application.job_id or f"app-{application.id}",
            title=application.job_title,
            company=application.company,
            url=application.job_url,
        )
    if not job:
        raise HTTPException(status_code=400, detail="No job linked to this selection.")

    prepared = prepare_application(profile, job)

    # Fall back to the live job URL so the UI always has something to open.
    if not prepared.get("url") and job.url:
        prepared["url"] = job.url
    prepared["action"] = "open_url"
    prepared.setdefault(
        "instructions",
        "Review the generated cover letter and complete any missing answers, "
        "then open the original posting and submit it yourself.",
    )

    if application:
        application.cover_letter = prepared["cover_letter"]
        application.form_answers = prepared["form_answers"]
        if application.status in (None, "", "discovered", "shortlisted"):
            application.status = "preparing"
        db.commit()
        db.refresh(application)
        prepared["application_id"] = application.id
    elif request.job_id:
        application = Application(
            id=uuid.uuid4().hex,
            job_id=job.id,
            company=job.company,
            job_title=job.title,
            job_url=job.url,
            source=job.source,
            status="preparing",
            cover_letter=prepared["cover_letter"],
            form_answers=prepared["form_answers"],
            date_discovered=datetime.utcnow(),
        )
        db.add(application)
        db.commit()
        db.refresh(application)
        prepared["application_id"] = application.id

    return prepared


@router.post("/follow-up-message")
def get_follow_up_message(request: FollowUpRequest, db: Session = Depends(get_db)):
    profile = db.query(Profile).first()
    application = db.query(Application).filter(Application.id == request.application_id).first()
    if not profile or not application:
        raise HTTPException(status_code=404, detail="Profile or application not found.")
    return {"message": generate_follow_up_message(profile, application)}


@router.post("/complete/{application_id}")
def complete_application(application_id: str, db: Session = Depends(get_db)):
    """Mark a prepared application as submitted.

    Called by the user after they actually submit on the employer's site, so the
    pipeline reflects reality instead of guessing.
    """
    application = db.query(Application).filter(Application.id == application_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found.")
    application.status = "submitted"
    db.commit()
    db.refresh(application)
    return {"id": application.id, "status": application.status}
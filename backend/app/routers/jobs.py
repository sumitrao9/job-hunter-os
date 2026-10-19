import uuid
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List
from urllib.parse import urlparse
from app.database import get_db
from app.models import Job
from pydantic import BaseModel, ConfigDict
from datetime import datetime

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


class JobSchema(BaseModel):
    id: Optional[str] = None
    title: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    remote: Optional[bool] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    description: Optional[str] = None
    url: Optional[str] = None
    source: Optional[str] = None
    match_score: Optional[float] = None
    # Stored as a list of human-readable reasons, so the type must be a list.
    match_evidence: Optional[List[str]] = None
    status: Optional[str] = None
    is_saved: Optional[bool] = None
    is_duplicate: Optional[bool] = None
    scraped_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


@router.get("/", response_model=List[JobSchema])
def list_jobs(
    db: Session = Depends(get_db),
    search: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    company: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    saved: Optional[bool] = Query(None),
    remote: Optional[bool] = Query(None),
    min_score: Optional[float] = Query(None, ge=0, le=100),
    sort: str = Query("recent", pattern="^(recent|match|salary|company|title)$"),
    skip: int = 0,
    limit: int = 50,
):
    q = db.query(Job)
    if search:
        pattern = f"%{search}%"
        # The posting body is searchable too. It holds the responsibilities and
        # requirements, which is where most useful keywords actually appear.
        q = q.filter(
            (Job.title.ilike(pattern))
            | (Job.company.ilike(pattern))
            | (Job.location.ilike(pattern))
            | (Job.source.ilike(pattern))
            | (Job.description.ilike(pattern))
        )
    if source:
        q = q.filter(Job.source == source)
    if company:
        q = q.filter(Job.company == company)
    if status:
        q = q.filter(Job.status == status)
    if saved is not None:
        q = q.filter(Job.is_saved == saved)
    if remote is not None:
        q = q.filter(Job.remote == remote)
    if min_score is not None:
        q = q.filter(Job.match_score >= min_score)

    if sort == "match":
        # Unscored jobs sink below anything that was actually scored.
        q = q.order_by(Job.match_score.is_(None), Job.match_score.desc(), Job.created_at.desc())
    elif sort == "salary":
        q = q.order_by(Job.salary_max.is_(None), Job.salary_max.desc())
    elif sort == "company":
        q = q.order_by(Job.company.asc(), Job.created_at.desc())
    elif sort == "title":
        q = q.order_by(Job.title.asc())
    else:
        q = q.order_by(Job.created_at.desc())

    return q.offset(skip).limit(limit).all()


@router.get("/count")
def count_jobs(
    db: Session = Depends(get_db),
    search: Optional[str] = Query(None),
    company: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    saved: Optional[bool] = Query(None),
    remote: Optional[bool] = Query(None),
    min_score: Optional[float] = Query(None, ge=0, le=100),
):
    """Total matches for the active filters, so the UI can paginate honestly."""
    q = db.query(Job)
    if search:
        pattern = f"%{search}%"
        q = q.filter(
            (Job.title.ilike(pattern))
            | (Job.company.ilike(pattern))
            | (Job.location.ilike(pattern))
            | (Job.source.ilike(pattern))
            | (Job.description.ilike(pattern))
        )
    if company:
        q = q.filter(Job.company == company)
    if source:
        q = q.filter(Job.source == source)
    if status:
        q = q.filter(Job.status == status)
    if saved is not None:
        q = q.filter(Job.is_saved == saved)
    if remote is not None:
        q = q.filter(Job.remote == remote)
    if min_score is not None:
        q = q.filter(Job.match_score >= min_score)
    return {"total": q.count()}


class JobUpdate(BaseModel):
    is_saved: Optional[bool] = None
    status: Optional[str] = None


@router.patch("/{job_id}", response_model=JobSchema)
def update_job(job_id: str, update: JobUpdate, db: Session = Depends(get_db)):
    """Save/bookmark a job or move it through the pipeline."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if update.is_saved is not None:
        job.is_saved = update.is_saved
    if update.status is not None:
        job.status = update.status
    db.commit()
    db.refresh(job)
    return JobSchema.model_validate(job)


@router.get("/companies", response_model=List[str])
def list_companies(db: Session = Depends(get_db)):
    """Distinct companies so the UI filter is not limited to the current page."""
    rows = db.query(Job.company).filter(Job.company.isnot(None)).distinct().all()
    return sorted({row[0] for row in rows if row[0]})


@router.get("/{job_id}", response_model=JobSchema)
def get_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobSchema.model_validate(job)


@router.post("/", response_model=JobSchema)
def create_job(job_in: JobSchema, db: Session = Depends(get_db)):
    job = Job(id=job_in.id or uuid.uuid4().hex)
    for field, value in job_in.model_dump(exclude_unset=True).items():
        setattr(job, field, value)
    db.add(job)
    db.commit()
    db.refresh(job)
    return JobSchema.model_validate(job)


@router.post("/import")
def import_jobs(payload: dict, db: Session = Depends(get_db)):
    items = payload.get("jobs", [])
    imported = 0
    duplicates = 0
    for item in items:
        url = item.get("url")
        existing = None
        if url:
            existing = db.query(Job).filter(Job.url == url).first()
        if existing:
            duplicates += 1
            continue
        job = Job(id=uuid.uuid4().hex)
        title = item.get("title")
        if not title and url:
            parsed = urlparse(url)
            title = f"Job at {parsed.netloc}"
        job.title = title
        for field, value in item.items():
            if field in {"company", "location", "remote", "salary_min", "salary_max", "description", "url", "source"}:
                setattr(job, field, value)
        db.add(job)
        imported += 1
    db.commit()
    return {"imported": imported, "duplicates": duplicates}

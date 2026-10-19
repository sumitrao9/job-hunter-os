from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from app.database import get_db
from app.models import Application, Job, Resume
from pydantic import BaseModel, ConfigDict
from datetime import datetime
import uuid

router = APIRouter(prefix="/api/applications", tags=["applications"])


class ApplicationSchema(BaseModel):
    id: Optional[str] = None
    job_id: Optional[str] = None
    resume_id: Optional[str] = None
    company: Optional[str] = None
    job_title: Optional[str] = None
    job_url: Optional[str] = None
    source: Optional[str] = None
    match_score: Optional[float] = None
    status: Optional[str] = None
    cover_letter: Optional[str] = None
    form_answers: Optional[dict] = None
    notes: Optional[str] = None
    date_discovered: Optional[datetime] = None
    date_applied: Optional[datetime] = None
    follow_up_date: Optional[datetime] = None
    history: Optional[list] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


@router.get("/", response_model=List[ApplicationSchema])
def list_applications(
    db: Session = Depends(get_db),
    status: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    skip: int = 0,
    limit: int = 100,
):
    query = db.query(Application)
    if status:
        query = query.filter(Application.status == status)
    if q:
        query = query.filter(
            (Application.company.ilike(f"%{q}%"))
            | (Application.job_title.ilike(f"%{q}%"))
        )
    return query.order_by(Application.created_at.desc()).offset(skip).limit(limit).all()


@router.post("/", response_model=ApplicationSchema)
def create_application(app_in: ApplicationSchema, db: Session = Depends(get_db)):
    app = Application(id=app_in.id or uuid.uuid4().hex)
    for field, value in app_in.model_dump(exclude_unset=True).items():
        setattr(app, field, value)
    db.add(app)
    db.commit()
    db.refresh(app)
    return ApplicationSchema.model_validate(app)


@router.patch("/{application_id}", response_model=ApplicationSchema)
def update_application(application_id: str, app_in: ApplicationSchema, db: Session = Depends(get_db)):
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    data = app_in.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(app, field, value)
    db.commit()
    db.refresh(app)
    return ApplicationSchema.model_validate(app)


@router.delete("/{application_id}")
def delete_application(application_id: str, db: Session = Depends(get_db)):
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    db.delete(app)
    db.commit()
    return {"status": "deleted"}

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Application

router = APIRouter(prefix="/api/applications", tags=["applications"])


class ApplicationSchema(BaseModel):
    id: str | None = None
    job_id: str | None = None
    resume_id: str | None = None
    company: str | None = None
    job_title: str | None = None
    job_url: str | None = None
    source: str | None = None
    match_score: float | None = None
    status: str | None = None
    cover_letter: str | None = None
    form_answers: dict | None = None
    notes: str | None = None
    date_discovered: datetime | None = None
    date_applied: datetime | None = None
    follow_up_date: datetime | None = None
    history: list | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


@router.get("/", response_model=list[ApplicationSchema])
def list_applications(
    db: Session = Depends(get_db),
    status: str | None = Query(None),
    q: str | None = Query(None),
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

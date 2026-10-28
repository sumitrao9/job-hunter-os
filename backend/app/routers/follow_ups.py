from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Application

router = APIRouter(prefix="/api/follow-ups", tags=["follow-ups"])


class FollowUpResponse(BaseModel):
    id: str
    company: str
    job_title: str
    follow_up_date: str | None
    status: str

@router.get("/", response_model=list[FollowUpResponse])
def get_follow_ups(db: Session = Depends(get_db)):
    today = datetime.utcnow().date()
    apps = db.query(Application).filter(
        Application.follow_up_date >= today,
        Application.status.notin_(["rejected", "withdrawn", "offer"]),
    ).all()
    return [
        FollowUpResponse(
            id=a.id,
            company=a.company or "",
            job_title=a.job_title or "",
            follow_up_date=a.follow_up_date.isoformat() if a.follow_up_date else None,
            status=a.status or "",
        )
        for a in apps
    ]


class FollowUpRequest(BaseModel):
    application_id: str
    follow_up_date: str | None = None


@router.post("/set")
def set_follow_up(request: FollowUpRequest, db: Session = Depends(get_db)):
    app = db.query(Application).filter(Application.id == request.application_id).first()
    if not app:
        return {"error": "Application not found"}
    app.follow_up_date = datetime.fromisoformat(request.follow_up_date) if request.follow_up_date else None
    db.commit()
    db.refresh(app)
    return {"status": "ok"}

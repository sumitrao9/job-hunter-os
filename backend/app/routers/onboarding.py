from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Profile

router = APIRouter(prefix="/api/onboarding", tags=["onboarding"])


class OnboardingStatus(BaseModel):
    completed: bool
    profile_exists: bool

@router.get("/status", response_model=OnboardingStatus)
def get_onboarding_status(db: Session = Depends(get_db)):
    profile = db.query(Profile).first()
    if not profile or not profile.full_name or not profile.skills:
        return OnboardingStatus(completed=False, profile_exists=profile is not None)
    return OnboardingStatus(completed=True, profile_exists=True)

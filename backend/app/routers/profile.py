
from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Profile

router = APIRouter(prefix="/api/profile", tags=["profile"])


class ProfileSchema(BaseModel):
    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    preferred_locations: list[str] | None = None
    education: list[dict] | None = None
    experience: list[dict] | None = None
    skills: list[str] | None = None
    desired_roles: list[str] | None = None
    min_salary: int | None = None
    preferred_salary: int | None = None
    remote_preference: str | None = None
    experience_level: str | None = None
    notice_period: str | None = None
    preferred_industries: list[str] | None = None
    search_keywords: list[str] | None = None
    search_exclusions: list[str] | None = None

    model_config = ConfigDict(from_attributes=True)


@router.get("/", response_model=ProfileSchema)
def get_profile(db: Session = Depends(get_db)):
    profile = db.query(Profile).first()
    if not profile:
        return ProfileSchema()
    return ProfileSchema.model_validate(profile)


@router.post("/", response_model=ProfileSchema)
def create_or_update_profile(profile_in: ProfileSchema, db: Session = Depends(get_db)):
    profile = db.query(Profile).first()
    if not profile:
        profile = Profile(id="singleton")
        db.add(profile)

    data = profile_in.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(profile, field, value)

    db.commit()
    db.refresh(profile)
    return ProfileSchema.model_validate(profile)

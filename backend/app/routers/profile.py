from fastapi import APIRouter, Depends, HTTPException, Query, File, UploadFile, Form
from sqlalchemy.orm import Session
from typing import Optional, List
from app.database import get_db
from app.models import Profile, Resume, Job, Application, AgentLog, WorkflowConfig
from pydantic import BaseModel, ConfigDict
from datetime import datetime
import json
import os
import uuid
from app.config import settings

router = APIRouter(prefix="/api/profile", tags=["profile"])


class ProfileSchema(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    preferred_locations: Optional[List[str]] = None
    education: Optional[List[dict]] = None
    experience: Optional[List[dict]] = None
    skills: Optional[List[str]] = None
    desired_roles: Optional[List[str]] = None
    min_salary: Optional[int] = None
    preferred_salary: Optional[int] = None
    remote_preference: Optional[str] = None
    experience_level: Optional[str] = None
    notice_period: Optional[str] = None
    preferred_industries: Optional[List[str]] = None
    search_keywords: Optional[List[str]] = None
    search_exclusions: Optional[List[str]] = None

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

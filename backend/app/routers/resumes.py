import os
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Resume

router = APIRouter(prefix="/api/resumes", tags=["resumes"])


class ResumeSchema(BaseModel):
    id: str | None = None
    profile_id: str | None = None
    title: str
    original_filename: str
    file_type: str
    is_default: bool = False
    parsed_sections: dict | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


@router.get("/", response_model=list[ResumeSchema])
def list_resumes(db: Session = Depends(get_db)):
    return db.query(Resume).all()


@router.post("/", response_model=ResumeSchema)
def create_resume(
    title: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    os.makedirs(settings.upload_dir, exist_ok=True)
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in {".pdf", ".docx"}:
        raise HTTPException(status_code=400, detail="Only PDF and DOCX files are allowed.")

    stored = f"{uuid.uuid4().hex}{ext}"
    path = os.path.join(settings.upload_dir, stored)
    with open(path, "wb") as f:
        f.write(file.file.read())

    resume = Resume(
        id=uuid.uuid4().hex,
        profile_id="singleton",
        title=title,
        original_filename=file.filename or "resume",
        stored_filename=stored,
        file_type=ext.lstrip("."),
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)
    return ResumeSchema.model_validate(resume)


@router.delete("/{resume_id}")
def delete_resume(resume_id: str, db: Session = Depends(get_db)):
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    db.delete(resume)
    db.commit()
    return {"status": "deleted"}

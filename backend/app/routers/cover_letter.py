import os

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Application, Job, Profile
from app.services.application_prep import prepare_application
from app.services.knowledge_base import KnowledgeBase

router = APIRouter(prefix="/api/cover-letter", tags=["cover-letter"])

kb = KnowledgeBase()


class CoverLetterRequest(BaseModel):
    job_id: str | None = None
    application_id: str | None = None


@router.post("/generate")
def generate_cover_letter(request: CoverLetterRequest, db: Session = Depends(get_db)):
    profile = db.query(Profile).first()
    job = None
    application = None

    if request.job_id:
        job = db.query(Job).filter(Job.id == request.job_id).first()
    elif request.application_id:
        application = db.query(Application).filter(Application.id == request.application_id).first()
        if application and application.job_id:
            job = db.query(Job).filter(Job.id == request.job_id).first()

    if not profile or not job:
        return {"cover_letter": "Please complete your profile and select a job first."}

    # Generate cover letter from real profile data — no AI required.
    prepared = prepare_application(profile, job)
    cover_letter = prepared["cover_letter"]

    # Optionally enhance with knowledge base entries (TF-IDF matching, no AI).
    relevant_entries = kb.score_entries(
        job.title or "",
        job.description or "",
        top_n=3,
    )
    if relevant_entries:
        kb_note = "\n\nRelevant experience from your knowledge base:\n" + "\n".join(
            f"  - {entry['entry'][:200]}" for entry in relevant_entries[:3]
        )
        cover_letter += kb_note

    if application:
        application.cover_letter = cover_letter
        application.form_answers = prepared.get("form_answers", {})
        db.commit()
        db.refresh(application)

    return {
        "job_id": job.id,
        "cover_letter": cover_letter,
        "form_answers": prepared.get("form_answers", {}),
    }


class KnowledgeBaseUploadResponse(BaseModel):
    doc_id: str
    filename: str


@router.post("/knowledge-base/upload")
def upload_to_kb(file_path: str, doc_id: str | None = None):
    """Add a career document to the knowledge base (optional, no AI required)."""
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    doc_id = kb.add_document(file_path, doc_id)
    return KnowledgeBaseUploadResponse(doc_id=doc_id, filename=os.path.basename(file_path))


@router.get("/knowledge-base")
def list_kb():
    return {"documents": kb.list_documents()}


@router.delete("/knowledge-base/{doc_id}")
def delete_kb_entry(doc_id: str):
    removed = kb.remove_document(doc_id)
    return {"removed": removed}

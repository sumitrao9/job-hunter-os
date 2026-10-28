import os
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Job, Profile, Resume, TailoredResume
from app.services.llm import LLMService
from app.services.matching import score_ats_compatibility, score_job_against_profile

router = APIRouter(prefix="/api/ai", tags=["ai"])

llm = LLMService()


class ConnectionResponse(BaseModel):
    ok: bool
    models: list[str] = []
    error: str | None = None


@router.get("/test-connection", response_model=ConnectionResponse)
def test_llm_connection():
    result = llm.check_connection()
    return ConnectionResponse(ok=result["ok"], models=result.get("models", []), error=result.get("error"))


@router.get("/models")
def list_models():
    return llm.list_models()


@router.get("/providers")
def list_providers():
    result = llm.check_connection()
    return {"providers": llm.list_providers(), "active": result.get("provider", "none")}


class MatchJobRequest(BaseModel):
    job_id: str


class MatchJobResponse(BaseModel):
    job_id: str
    score: float
    evidence: list[str]
    gaps: list[str]
    components: dict


@router.post("/match-job", response_model=MatchJobResponse)
def match_job(request: MatchJobRequest, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == request.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    profile = db.query(Profile).first()
    if not profile:
        raise HTTPException(status_code=400, detail="Complete your profile first.")

    result = score_job_against_profile(profile, job)
    job.match_score = result.score
    job.match_evidence = result.evidence
    db.commit()
    db.refresh(job)

    return MatchJobResponse(
        job_id=job.id,
        score=result.score,
        evidence=result.evidence,
        gaps=result.gaps,
        components=result.components,
    )


class AnalyzeResumeRequest(BaseModel):
    resume_id: str


@router.post("/analyze-resume")
def analyze_resume(request: AnalyzeResumeRequest, db: Session = Depends(get_db)):
    from app.services.resume_parser import parse_resume_file

    resume = db.query(Resume).filter(Resume.id == request.resume_id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found.")
    path = os.path.join(settings.upload_dir, resume.stored_filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Resume file missing on disk.")

    parsed = parse_resume_file(path)
    resume.parsed_sections = parsed["sections"]
    db.commit()
    db.refresh(resume)
    return {"resume_id": resume.id, "sections": parsed["sections"]}


class ATSCheckRequest(BaseModel):
    resume_id: str
    job_id: str


@router.post("/ats-check")
def ats_check(request: ATSCheckRequest, db: Session = Depends(get_db)):
    from app.services.resume_parser import parse_resume_file

    resume = db.query(Resume).filter(Resume.id == request.resume_id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found.")
    job = db.query(Job).filter(Job.id == request.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    path = os.path.join(settings.upload_dir, resume.stored_filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Resume file missing on disk.")

    parsed = parse_resume_file(path)
    profile = db.query(Profile).first()
    profile_skills = profile.skills if profile else None

    ats_result = score_ats_compatibility(
        parsed.get("raw_text", ""),
        job.description or "",
        profile_skills=profile_skills,
    )
    return {
        "score": ats_result.score,
        "keyword_match": ats_result.keyword_match,
        "section_score": ats_result.section_score,
        "format_score": ats_result.format_score,
        "missing_keywords": ats_result.missing_keywords,
        "recommendations": ats_result.recommendations,
    }


class GenerateCoverLetterRequest(BaseModel):
    job_id: str
    resume_id: str | None = None


@router.post("/generate-cover-letter")
def generate_cover_letter(request: GenerateCoverLetterRequest, db: Session = Depends(get_db)):
    from app.services.application_prep import prepare_application

    job = db.query(Job).filter(Job.id == request.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    profile = db.query(Profile).first()
    if not profile:
        raise HTTPException(status_code=400, detail="Complete your profile first.")

    prepared = prepare_application(profile, job)
    body = prepared["cover_letter"]
    return {"job_id": job.id, "cover_letter": body.strip()}


class GenerateResumeRequest(BaseModel):
    job_id: str
    resume_id: str | None = None


@router.post("/generate-resume")
def generate_resume(request: GenerateResumeRequest, db: Session = Depends(get_db)):
    from app.services.documents import generate_resume_docx

    job = db.query(Job).filter(Job.id == request.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    profile = db.query(Profile).first()
    if not profile:
        raise HTTPException(status_code=400, detail="Complete your profile first.")

    result = score_job_against_profile(profile, job)
    path = generate_resume_docx(profile, job, result)

    tailored = TailoredResume(
        id=uuid.uuid4().hex,
        resume_id=request.resume_id or "",
        job_id=job.id,
        title=f"Tailored: {job.title}",
        file_path=path,
        file_type="docx",
        changes_summary=(
            f"Matched {result.score}% — {', '.join(result.evidence[:3])}"
        ),
    )
    db.add(tailored)
    db.commit()
    db.refresh(tailored)
    return {"tailored_resume_id": tailored.id, "file_path": path}

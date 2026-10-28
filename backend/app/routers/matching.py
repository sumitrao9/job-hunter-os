
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Job, Profile
from app.services.matching import score_job_against_profile

router = APIRouter(prefix="/api/matching", tags=["matching"])


class ScoreResponse(BaseModel):
    job_id: str
    score: float
    evidence: list[str]
    gaps: list[str]
    components: dict


@router.post("/score/{job_id}", response_model=ScoreResponse)
def score_job(job_id: str, db: Session = Depends(get_db)):
    """Score one job against the profile and persist the result."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    profile = db.query(Profile).first()
    if not profile:
        raise HTTPException(
            status_code=400, detail="Complete your profile before scoring jobs."
        )

    result = score_job_against_profile(profile, job)
    job.match_score = result.score
    job.match_evidence = result.evidence
    db.commit()
    db.refresh(job)

    return ScoreResponse(
        job_id=job.id,
        score=result.score,
        evidence=result.evidence,
        gaps=result.gaps,
        components=result.components,
    )

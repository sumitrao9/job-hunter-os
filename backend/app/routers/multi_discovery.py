from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import JobSource, SourceRun, SchedulerConfig, SearchProfile
from app.services.multi_discovery import discover

router = APIRouter(prefix="/api/discovery/v2", tags=["discovery-v2"])


# ---------- Source Management ----------

class SourceCreate(BaseModel):
    source_name: str
    country: str = "India"
    region: Optional[str] = None
    category: Optional[str] = None
    source_type: str = "ATS"
    adapter: str = "greenhouse"
    base_url: Optional[str] = None
    enabled: bool = True
    priority: int = 50
    schedule: str = "1h"
    rate_limit: int = 10
    requires_auth: bool = False
    requires_proxy: bool = False
    config: Optional[Dict[str, Any]] = None


class SourceUpdate(BaseModel):
    enabled: Optional[bool] = None
    priority: Optional[int] = None
    schedule: Optional[str] = None
    rate_limit: Optional[int] = None
    config: Optional[Dict[str, Any]] = None
    health_status: Optional[str] = None


@router.get("/sources")
def list_sources(
    db: Session = Depends(get_db),
    enabled: Optional[bool] = None,
    adapter: Optional[str] = None,
    health: Optional[str] = None,
):
    q = db.query(JobSource)
    if enabled is not None:
        q = q.filter(JobSource.enabled == enabled)
    if adapter:
        q = q.filter(JobSource.adapter == adapter)
    if health:
        q = q.filter(JobSource.health_status == health)
    sources = q.order_by(JobSource.priority.desc(), JobSource.source_name.asc()).all()
    return [
        {
            "id": s.id,
            "source_name": s.source_name,
            "country": s.country,
            "region": s.region,
            "category": s.category,
            "source_type": s.source_type,
            "adapter": s.adapter,
            "base_url": s.base_url,
            "enabled": s.enabled,
            "priority": s.priority,
            "schedule": s.schedule,
            "rate_limit": s.rate_limit,
            "requires_auth": s.requires_auth,
            "requires_proxy": s.requires_proxy,
            "last_run": s.last_run.isoformat() if s.last_run else None,
            "last_success": s.last_success.isoformat() if s.last_success else None,
            "last_failure": s.last_failure.isoformat() if s.last_failure else None,
            "jobs_found": s.jobs_found,
            "new_jobs": s.new_jobs,
            "duplicates": s.duplicates,
            "failed_jobs": s.failed_jobs,
            "health_status": s.health_status,
            "error_message": s.error_message,
            "config": s.config,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "updated_at": s.updated_at.isoformat() if s.updated_at else None,
        }
        for s in sources
    ]


@router.post("/sources")
def create_source(payload: SourceCreate, db: Session = Depends(get_db)):
    source = JobSource(
        id=payload.source_name.lower().replace(" ", "-").replace("/", "-")[:50],
        source_name=payload.source_name,
        country=payload.country,
        region=payload.region,
        category=payload.category,
        source_type=payload.source_type,
        adapter=payload.adapter,
        base_url=payload.base_url,
        enabled=payload.enabled,
        priority=payload.priority,
        schedule=payload.schedule,
        rate_limit=payload.rate_limit,
        requires_auth=payload.requires_auth,
        requires_proxy=payload.requires_proxy,
        config=payload.config or {},
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    return {"id": source.id, "status": "created"}


@router.put("/sources/{source_id}")
def update_source(source_id: str, payload: SourceUpdate, db: Session = Depends(get_db)):
    source = db.query(JobSource).filter(JobSource.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(source, field, value)
    db.commit()
    db.refresh(source)
    return {"id": source.id, "status": "updated"}


@router.delete("/sources/{source_id}")
def delete_source(source_id: str, db: Session = Depends(get_db)):
    source = db.query(JobSource).filter(JobSource.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    db.delete(source)
    db.commit()
    return {"status": "deleted"}


@router.get("/sources/{source_id}/runs")
def get_source_runs(source_id: str, db: Session = Depends(get_db), limit: int = 20):
    runs = db.query(SourceRun).filter(SourceRun.source_id == source_id).order_by(SourceRun.started_at.desc()).limit(limit).all()
    return [
        {
            "id": r.id,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "finished_at": r.finished_at.isoformat() if r.finished_at else None,
            "duration_seconds": r.duration_seconds,
            "jobs_found": r.jobs_found,
            "new_jobs": r.new_jobs,
            "duplicates": r.duplicates,
            "failed_jobs": r.failed_jobs,
            "status": r.status,
            "error_message": r.error_message,
            "queries_run": r.queries_run,
        }
        for r in runs
    ]


@router.get("/sources/stats")
def get_source_stats(db: Session = Depends(get_db)):
    total = db.query(JobSource).count()
    by_status = {}
    for s in db.query(JobSource).all():
        by_status[s.health_status] = by_status.get(s.health_status, 0) + 1
    return {
        "total": total,
        "by_status": by_status,
        "enabled": db.query(JobSource).filter(JobSource.enabled == True).count(),
    }


# ---------- Scheduler ----------

class SchedulerUpdate(BaseModel):
    enabled: Optional[bool] = None
    frequency_minutes: Optional[int] = None


@router.get("/scheduler")
def get_scheduler(db: Session = Depends(get_db)):
    cfg = db.query(SchedulerConfig).first()
    if not cfg:
        cfg = SchedulerConfig(id="default")
        db.add(cfg)
        db.commit()
        db.refresh(cfg)
    return {
        "id": cfg.id,
        "enabled": cfg.enabled,
        "frequency_minutes": cfg.frequency_minutes,
        "last_run": cfg.last_run.isoformat() if cfg.last_run else None,
        "next_run": cfg.next_run.isoformat() if cfg.next_run else None,
        "running": cfg.running,
        "total_runs": cfg.total_runs,
        "successful_runs": cfg.successful_runs,
        "failed_runs": cfg.failed_runs,
        "last_error": cfg.last_error,
    }


@router.put("/scheduler")
def update_scheduler(payload: SchedulerUpdate, db: Session = Depends(get_db)):
    cfg = db.query(SchedulerConfig).first()
    if not cfg:
        cfg = SchedulerConfig(id="default")
        db.add(cfg)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(cfg, field, value)
    cfg.updated_at = __import__("datetime").datetime.utcnow()
    db.commit()
    db.refresh(cfg)
    return {"status": "updated", "frequency_minutes": cfg.frequency_minutes}


# ---------- Discovery Execution ----------

@router.post("/run")
def run_discovery(
    sources: Optional[List[Dict[str, Any]]] = Body(None),
    score: bool = Body(False),
    db: Session = Depends(get_db),
):
    if sources is None:
        sources_q = db.query(JobSource).filter(JobSource.enabled == True).all()
        sources = [
            {
                "id": s.id,
                "source_name": s.source_name,
                "adapter": s.adapter,
                "base_url": s.base_url,
                "config": s.config or {},
                "company": s.source_name,
            }
            for s in sources_q
        ]
    if not sources:
        raise HTTPException(status_code=400, detail="No sources configured")
    result = discover(sources, max_workers=4)
    return result


# ---------- Search Profiles ----------

class SearchProfileCreate(BaseModel):
    name: str
    is_default: bool = False
    enabled: bool = True
    queries: Optional[List[Dict[str, str]]] = None
    sources: Optional[List[str]] = None
    keywords_include: Optional[List[str]] = None
    keywords_exclude: Optional[List[str]] = None
    locations: Optional[List[str]] = None
    remote_only: bool = False


@router.get("/profiles")
def list_profiles(db: Session = Depends(get_db)):
    profiles = db.query(SearchProfile).all()
    return [
        {
            "id": p.id,
            "name": p.name,
            "is_default": p.is_default,
            "enabled": p.enabled,
            "queries": p.queries,
            "sources": p.sources,
            "keywords_include": p.keywords_include,
            "keywords_exclude": p.keywords_exclude,
            "locations": p.locations,
            "remote_only": p.remote_only,
        }
        for p in profiles
    ]


@router.post("/profiles")
def create_profile(payload: SearchProfileCreate, db: Session = Depends(get_db)):
    profile = SearchProfile(
        id=__import__("uuid").uuid4().hex,
        name=payload.name,
        is_default=payload.is_default,
        enabled=payload.enabled,
        queries=payload.queries or [],
        sources=payload.sources or [],
        keywords_include=payload.keywords_include or [],
        keywords_exclude=payload.keywords_exclude or [],
        locations=payload.locations or [],
        remote_only=payload.remote_only,
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return {"id": profile.id, "status": "created"}

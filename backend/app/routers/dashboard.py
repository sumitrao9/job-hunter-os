from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Job, Application
from datetime import datetime, timedelta

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary")
def dashboard_summary(
    db: Session = Depends(get_db),
    from_date: str | None = Query(None),
    to_date: str | None = Query(None),
):
    from_filter = None
    to_filter = None
    if from_date:
        try:
            from_filter = datetime.fromisoformat(from_date)
        except ValueError:
            pass
    if to_date:
        try:
            to_filter = datetime.fromisoformat(to_date)
        except ValueError:
            pass

    total_jobs_query = db.query(Job)
    applications_query = db.query(Application)

    if from_filter:
        total_jobs_query = total_jobs_query.filter(Job.created_at >= from_filter)
        applications_query = applications_query.filter(Application.created_at >= from_filter)
    if to_filter:
        total_jobs_query = total_jobs_query.filter(Job.created_at <= to_filter)
        applications_query = applications_query.filter(Application.created_at <= to_filter)

    total_jobs = total_jobs_query.count()
    matching_jobs = total_jobs_query.filter(Job.match_score > 0).count()
    submitted = applications_query.filter(Application.status == "submitted").count()
    interviews = applications_query.filter(Application.status == "interview").count()
    offers = applications_query.filter(Application.status == "offer").count()
    rejected = applications_query.filter(Application.status == "rejected").count()
    applications = applications_query.count()
    response_rate = 0.0
    if submitted > 0:
        response_rate = round((interviews + offers + rejected) / submitted * 100, 2)

    recent_applications = applications_query.filter(
        Application.created_at >= datetime.utcnow() - timedelta(days=7)
    ).count()
    upcoming_follow_ups = db.query(Application).filter(
        Application.follow_up_date >= datetime.utcnow().date(),
        Application.status.notin_(["rejected", "withdrawn", "offer"]),
    ).count()

    return {
        "total_jobs": total_jobs,
        "matching_jobs": matching_jobs,
        "prepared": applications_query.filter(Application.status.in_(["preparing", "awaiting_approval"])).count(),
        "submitted": submitted,
        "interviews": interviews,
        "offers": offers,
        "rejected": rejected,
        "response_rate": response_rate,
        "applications": applications,
        "recent_applications": recent_applications,
        "upcoming_follow_ups": upcoming_follow_ups,
    }


@router.get("/trend")
def dashboard_trend(db: Session = Depends(get_db), days: int = Query(14, ge=1, le=90)):
    """Real per-day counts for jobs discovered and applications created."""
    today = datetime.utcnow().date()
    start = today - timedelta(days=days - 1)

    job_rows = (
        db.query(Job.created_at)
        .filter(Job.created_at >= datetime.combine(start, datetime.min.time()))
        .all()
    )
    app_rows = (
        db.query(Application.created_at)
        .filter(Application.created_at >= datetime.combine(start, datetime.min.time()))
        .all()
    )

    jobs_by_day: dict = {}
    for (created_at,) in job_rows:
        key = created_at.date().isoformat()
        jobs_by_day[key] = jobs_by_day.get(key, 0) + 1

    apps_by_day: dict = {}
    for (created_at,) in app_rows:
        key = created_at.date().isoformat()
        apps_by_day[key] = apps_by_day.get(key, 0) + 1

    series = []
    for offset in range(days):
        day = start + timedelta(days=offset)
        key = day.isoformat()
        series.append({
            "date": key,
            "label": day.strftime("%b %d"),
            "jobs_discovered": jobs_by_day.get(key, 0),
            "applications_created": apps_by_day.get(key, 0),
        })

    return {"days": days, "series": series}

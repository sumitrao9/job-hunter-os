import csv
import io

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Application, Job

router = APIRouter(prefix="/api/export", tags=["export"])


@router.get("/jobs.csv")
def export_jobs_csv(db: Session = Depends(get_db)):
    jobs = db.query(Job).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Title", "Company", "Location", "Remote", "Salary Min", "Salary Max", "URL", "Source", "Match Score", "Status"])
    for job in jobs:
        writer.writerow([
            job.id,
            job.title,
            job.company,
            job.location,
            job.remote,
            job.salary_min,
            job.salary_max,
            job.url,
            job.source,
            job.match_score,
            job.status,
        ])
    from fastapi.responses import Response
    return Response(content=output.getvalue(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=jobs.csv"})


@router.get("/applications.csv")
def export_applications_csv(db: Session = Depends(get_db)):
    apps = db.query(Application).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Company", "Job Title", "Status", "Match Score", "Date Applied", "Follow-up Date", "Notes"])
    for app in apps:
        writer.writerow([
            app.id,
            app.company,
            app.job_title,
            app.status,
            app.match_score,
            app.date_applied.isoformat() if app.date_applied else '',
            app.follow_up_date.isoformat() if app.follow_up_date else '',
            app.notes,
        ])
    from fastapi.responses import Response
    return Response(content=output.getvalue(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=applications.csv"})


@router.get("/jobs.json")
def export_jobs_json(db: Session = Depends(get_db)):
    jobs = db.query(Job).all()
    data = [
        {
            "id": job.id,
            "title": job.title,
            "company": job.company,
            "location": job.location,
            "remote": job.remote,
            "salary_min": job.salary_min,
            "salary_max": job.salary_max,
            "url": job.url,
            "source": job.source,
            "match_score": job.match_score,
            "status": job.status,
        }
        for job in jobs
    ]
    return {"jobs": data}


@router.get("/applications.json")
def export_applications_json(db: Session = Depends(get_db)):
    apps = db.query(Application).all()
    data = [
        {
            "id": app.id,
            "company": app.company,
            "job_title": app.job_title,
            "status": app.status,
            "match_score": app.match_score,
            "date_applied": app.date_applied.isoformat() if app.date_applied else None,
            "follow_up_date": app.follow_up_date.isoformat() if app.follow_up_date else None,
            "notes": app.notes,
        }
        for app in apps
    ]
    return {"applications": data}

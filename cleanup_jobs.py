#!/usr/bin/env python3
"""Cleanup job database: keep only relevant jobs for NSita, remove duplicates."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))
os.chdir(os.path.join(os.path.dirname(__file__), "backend"))

from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Job, Application
import uuid

# Keep ONLY these verified employers/sources that NSita can realistically apply to
# and ONLY relevant roles within those employers
KEEP_SOURCES = {
    "web:Barclays",
    "web:PwC", 
    "web:CSC",
    "web:Empenofore",
    "web:Hcbt",
    "web:AMLRightSource",
    "web:Randstad",
    "greenhouse:Razorpay",
    "greenhouse:Groww",
}

# For Razorpay/Groww, only keep these relevant titles
RELEVANT_TITLES = [
    "KYC", "Compliance", "Banking", "Audit", "Risk", "Customer", 
    "Onboarding", "Due Diligence", "Fraud", "Quality", "Operations",
    "Relationship Manager", "Internal Audit",
]

def clean_db(db: Session):
    # Get all jobs
    all_jobs = db.query(Job).all()
    print(f"Total jobs before cleanup: {len(all_jobs)}")
    
    # Find duplicates by (company, title) - keep first, delete rest
    seen_titles = {}
    duplicates = []
    for job in all_jobs:
        key = (job.company or "", job.title or "")
        if key in seen_titles:
            duplicates.append(job)
        else:
            seen_titles[key] = job.id
    
    print(f"Found {len(duplicates)} duplicate jobs")
    
    # Find jobs to delete (not in keep list AND not manually imported web jobs)
    to_delete = []
    for job in all_jobs:
        source = job.source or ""
        title = job.title or ""
        
        # Keep if in whitelist AND title is relevant
        if source in KEEP_SOURCES:
            # For Razorpay/Groww, only keep relevant titles
            if source in ("greenhouse:Razorpay", "greenhouse:Groww"):
                if not any(rt.lower() in title.lower() for rt in RELEVANT_TITLES):
                    to_delete.append(job)
                    continue
            # Keep all web: jobs (manually imported real jobs)
            continue
        
        # Delete everything else (bulk API imports, old test data, etc.)
        to_delete.append(job)
    
    print(f"Jobs to delete (not relevant): {len(to_delete)}")
    print(f"Jobs to keep: {len(all_jobs) - len(to_delete)}")
    
    # Delete applications for jobs we're deleting
    job_ids_to_delete = [j.id for j in to_delete]
    apps_to_delete = db.query(Application).filter(Application.job_id.in_(job_ids_to_delete)).all()
    print(f"Deleting {len(apps_to_delete)} applications for removed jobs")
    for app in apps_to_delete:
        db.delete(app)
    
    # Delete duplicates
    for job in duplicates:
        db.delete(job)
    
    # Delete non-relevant jobs
    for job in to_delete:
        db.delete(job)
    
    db.commit()
    
    # Verify
    remaining = db.query(Job).count()
    remaining_apps = db.query(Application).count()
    print(f"\nAfter cleanup:")
    print(f"  Jobs: {remaining}")
    print(f"  Applications: {remaining_apps}")
    
    # Show what we kept
    kept_jobs = db.query(Job).all()
    sources = {}
    for job in kept_jobs:
        s = job.source or "unknown"
        sources[s] = sources.get(s, 0) + 1
    print(f"\nJobs by source:")
    for s, count in sorted(sources.items(), key=lambda x: -x[1]):
        print(f"  {s}: {count}")

if __name__ == "__main__":
    db = SessionLocal()
    try:
        clean_db(db)
    finally:
        db.close()

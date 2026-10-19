#!/usr/bin/env python3
"""Seed initial job sources for NSita's search."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))
os.chdir(os.path.join(os.path.dirname(__file__), "backend"))

from app.database import SessionLocal
from app.models import JobSource, SearchProfile, SchedulerConfig
import uuid
from datetime import datetime

NISHITA_QUERIES = [
    {"search_term": "KYC Analyst", "location": "Gurugram"},
    {"search_term": "KYC Analyst", "location": "Noida"},
    {"search_term": "Video KYC", "location": "Noida"},
    {"search_term": "Video KYC Specialist", "location": "Delhi NCR"},
    {"search_term": "Banking Operations", "location": "Delhi"},
    {"search_term": "Banking Operations Executive", "location": "Delhi NCR"},
    {"search_term": "Banking Operations Associate", "location": "Gurgaon"},
    {"search_term": "Customer Due Diligence", "location": "Gurgaon"},
    {"search_term": "Customer Due Diligence Analyst", "location": "Delhi NCR"},
    {"search_term": "AML Compliance", "location": "Delhi NCR"},
    {"search_term": "AML Analyst", "location": "Gurugram"},
    {"search_term": "Compliance Analyst", "location": "Delhi"},
    {"search_term": "Client Onboarding", "location": "Gurgaon"},
    {"search_term": "Client Onboarding Specialist", "location": "Gurugram"},
    {"search_term": "Fraud Operations", "location": "Noida"},
    {"search_term": "Fraud Operations Analyst", "location": "Delhi NCR"},
    {"search_term": "Risk Operations", "location": "Delhi"},
    {"search_term": "Quality Analyst Banking", "location": "Gurgaon"},
    {"search_term": "Digital Banking Operations", "location": "Delhi NCR"},
    {"search_term": "Relationship Manager", "location": "Gurugram"},
]

SOURCES = [
    {"id": "linkedin-india", "source_name": "LinkedIn India", "adapter": "linkedin", "schedule": "1h", "priority": 100, "config": {"queries": NISHITA_QUERIES, "results_wanted": 20, "hours_old": 72}},
    {"id": "naukri-india", "source_name": "Naukri India", "adapter": "naukri", "schedule": "1h", "priority": 100, "config": {"queries": NISHITA_QUERIES, "results_wanted": 20, "hours_old": 72}},
    {"id": "indeed-india", "source_name": "Indeed India", "adapter": "indeed", "schedule": "2h", "priority": 90, "config": {"queries": NISHITA_QUERIES, "results_wanted": 15, "hours_old": 72}},
    {"id": "glassdoor-india", "source_name": "Glassdoor India", "adapter": "glassdoor", "schedule": "2h", "priority": 80, "config": {"queries": NISHITA_QUERIES, "results_wanted": 15, "hours_old": 72}},
    {"id": "ziprecruiter-india", "source_name": "ZipRecruiter", "adapter": "zip_recruiter", "schedule": "2h", "priority": 80, "config": {"queries": NISHITA_QUERIES, "results_wanted": 15, "hours_old": 72}},
    {"id": "google-jobs-india", "source_name": "Google Jobs", "adapter": "google", "schedule": "2h", "priority": 90, "config": {"queries": NISHITA_QUERIES, "results_wanted": 15, "hours_old": 72}},
    {"id": "bayt-india", "source_name": "Bayt", "adapter": "bayt", "schedule": "2h", "priority": 70, "config": {"queries": NISHITA_QUERIES, "results_wanted": 15, "hours_old": 72}},
    {"id": "bdjobs-india", "source_name": "BDJobs", "adapter": "bdjobs", "schedule": "2h", "priority": 60, "config": {"queries": NISHITA_QUERIES, "results_wanted": 15, "hours_old": 72}},
    {"id": "ats-greenhouse", "source_name": "Greenhouse ATS", "adapter": "greenhouse", "schedule": "4h", "priority": 70, "config": {"queries": NISHITA_QUERIES[:5]}},
    {"id": "ats-lever", "source_name": "Lever ATS", "adapter": "lever", "schedule": "4h", "priority": 70, "config": {"queries": NISHITA_QUERIES[:5]}},
    {"id": "ats-ashby", "source_name": "Ashby ATS", "adapter": "ashby", "schedule": "4h", "priority": 70, "config": {"queries": NISHITA_QUERIES[:5]}},
    {"id": "rss-weworkremotely", "source_name": "We Work Remotely", "adapter": "rss", "schedule": "6h", "priority": 50, "config": {"feed_urls": ["https://weworkremotely.com/remote-jobs.rss"]}},
    {"id": "rss-remotive", "source_name": "Remotive", "adapter": "rss", "schedule": "6h", "priority": 50, "config": {"feed_urls": ["https://remotive.com/remote-jobs/feed"]}},
    {"id": "rss-himalayas", "source_name": "Himalayas", "adapter": "rss", "schedule": "6h", "priority": 50, "config": {"feed_urls": ["https://himalayas.app/jobs/rss"]}},
    {"id": "rss-jobicy", "source_name": "Jobicy", "adapter": "rss", "schedule": "6h", "priority": 50, "config": {"feed_urls": ["https://jobicy.com/jobs/feed"]}},
    {"id": "rss-hackernews", "source_name": "Hacker News Who is Hiring", "adapter": "rss", "schedule": "6h", "priority": 50, "config": {"feed_urls": ["https://hnrss.org/whoishiring/jobs"]}},
    {"id": "api-adzuna-us", "source_name": "Adzuna USA", "adapter": "adzuna", "country": "USA", "schedule": "4h", "priority": 85, "config": {"queries": NISHITA_QUERIES, "results_wanted": 25, "hours_old": 72}},
    {"id": "api-adzuna-in", "source_name": "Adzuna India", "adapter": "adzuna", "country": "India", "schedule": "4h", "priority": 85, "config": {"queries": NISHITA_QUERIES, "results_wanted": 25, "hours_old": 72}},
    {"id": "api-remotive", "source_name": "Remotive API", "adapter": "remotive", "schedule": "6h", "priority": 70, "config": {"queries": [{"search_term": "KYC"}, {"search_term": "banking"}, {"search_term": "compliance"}, {"search_term": "AML"}, {"search_term": "operations"}], "results_wanted": 25, "hours_old": 168}},
    {"id": "api-jsearch", "source_name": "JSearch API", "adapter": "jsearch", "schedule": "8h", "priority": 80, "config": {"queries": NISHITA_QUERIES[:10], "results_wanted": 20, "hours_old": 72}},
    {"id": "api-usajobs", "source_name": "USAJOBS", "adapter": "usajobs", "country": "USA", "schedule": "24h", "priority": 60, "config": {"queries": [{"search_term": "Financial Analyst"}, {"search_term": "Risk Analyst"}, {"search_term": "Compliance Officer"}, {"search_term": "Operations Specialist"}, {"search_term": "Banking Specialist"}], "results_wanted": 25, "hours_old": 168}},
    {"id": "api-remoteok", "source_name": "RemoteOK", "adapter": "remoteok", "schedule": "6h", "priority": 75, "config": {"queries": [{"search_term": "KYC"}, {"search_term": "banking"}, {"search_term": "compliance"}, {"search_term": "AML"}, {"search_term": "operations"}, {"search_term": "fraud"}], "results_wanted": 50, "hours_old": 168}},
    {"id": "api-himalayas", "source_name": "Himalayas API", "adapter": "himalayas", "schedule": "6h", "priority": 75, "config": {"queries": [{"search_term": "KYC"}, {"search_term": "banking"}, {"search_term": "compliance"}], "results_wanted": 50, "hours_old": 168}},
]

def seed(db: Session):
    for s in SOURCES:
        existing = db.query(JobSource).filter(JobSource.id == s["id"]).first()
        if not existing:
            source = JobSource(
                id=s["id"],
                source_name=s["source_name"],
                country="India",
                source_type="JOB_BOARD",
                adapter=s["adapter"],
                enabled=True,
                priority=s["priority"],
                schedule=s["schedule"],
                rate_limit=10,
                config=s["config"],
                health_status="NOT_CONFIGURED",
            )
            db.add(source)
            print(f"Created source: {s['source_name']} ({s['id']})")
        else:
            print(f"Source exists: {s['source_name']}")
    
    # Create default search profile
    profile = db.query(SearchProfile).first()
    if not profile:
        profile = SearchProfile(
            id=uuid.uuid4().hex,
            name="NSita - Primary Search",
            is_default=True,
            enabled=True,
            queries=NISHITA_QUERIES,
            sources=[s["id"] for s in SOURCES],
            keywords_include=["KYC", "AML", "Banking", "Compliance", "CDD", "Fraud", "Onboarding", "Operations", "Risk", "Quality", "Relationship Manager", "Video KYC", "Customer Due Diligence"],
            keywords_exclude=["intern", "trainee", "entry level"],
            locations=["Gurugram", "Gurgaon", "Noida", "Delhi", "Delhi NCR", "NCR", "Haryana", "Remote India"],
            remote_only=False,
        )
        db.add(profile)
        print("Created default search profile")
    
    # Create scheduler config
    scheduler = db.query(SchedulerConfig).first()
    if not scheduler:
        scheduler = SchedulerConfig(
            id="default",
            enabled=True,
            frequency_minutes=60,
            total_runs=0,
            successful_runs=0,
            failed_runs=0,
        )
        db.add(scheduler)
        print("Created scheduler config")
    
    db.commit()
    print(f"\nSeeded {len(SOURCES)} sources")
    print(f"Total sources in DB: {db.query(JobSource).count()}")

if __name__ == "__main__":
    db = SessionLocal()
    try:
        seed(db)
    finally:
        db.close()

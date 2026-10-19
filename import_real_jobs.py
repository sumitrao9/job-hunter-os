#!/usr/bin/env python3
"""Import verified real KYC/Banking jobs for NSita."""
import sys
import os

# Ensure backend package is importable and its .env is loaded.
BACKEND_DIR = os.path.join(os.path.dirname(__file__), "backend")
sys.path.insert(0, BACKEND_DIR)
os.chdir(BACKEND_DIR)

from sqlalchemy.orm import Session
from app.database import SessionLocal, engine
from app.models import Job, Application, Profile
from datetime import datetime
import uuid

NISHITA_JOBS = [
    {
        "title": "KYC Analyst",
        "company": "Barclays",
        "location": "Gurugram, India",
        "remote": False,
        "description": "Conduct in-depth due diligence on clients, ensure compliance with regulatory requirements, and safeguard the organization. End-to-end KYC knowledge, CDD/EDD, client onboarding, periodic reviews, remediation. Knowledge of financial crime legislation.",
        "url": "https://search.jobs.barclays/en/job/gurugram/kyc-analyst/13015/97463249712",
        "source": "web:Barclays",
        "status": "discovered",
    },
    {
        "title": "KYC Analyst",
        "company": "Barclays",
        "location": "Noida, India",
        "remote": False,
        "description": "Provide first-class support by conducting in-depth due diligence, ensuring compliance with regulatory requirements, and safeguarding clients and organization. End-to-end KYC knowledge and experience in low, medium & high-risk review. Knowledge in CDD, EDD, company structures, ownership, PEPs, high risk jurisdictions.",
        "url": "https://search.jobs.barclays/job/noida/kyc-analyst/13015/96432429168",
        "source": "web:Barclays",
        "status": "discovered",
    },
    {
        "title": "IB KYC Refresh - Senior Analyst",
        "company": "Barclays",
        "location": "Gurugram, India",
        "remote": False,
        "description": "Take responsibility for client service and operational execution. Control risk and enhance controls. End-to-end KYC (E2E KYC), CDD and EDD, entity types like Corporates, Fund, trust, SPV and FI. Client onboarding, periodic reviews, renewals/refresh, remediation. Basics of Financial crime.",
        "url": "https://search.jobs.barclays/job/gurugram/ib-kyc-refresh-senior-analyst/13015/96334021808",
        "source": "web:Barclays",
        "status": "discovered",
    },
    {
        "title": "KYC Onboarding Specialist",
        "company": "Empenofore Technologies",
        "location": "Gurgaon, India",
        "remote": False,
        "description": "Conduct periodic reviews (ODD) on existing private/corporate clients. Perform remediation and SOF (Source of Funds) checks. Ensure compliance with Global Minimum KYC Standards and risk appetite. Review and validate client documentation and AML screening results.",
        "url": "https://www.linkedin.com/posts/poojarrani_hiringnow-jobalert-wearehiring-activity-7479833644262522881-HhSM",
        "source": "web:Empenofore",
        "status": "discovered",
    },
    {
        "title": "Associate Client Onboarding Specialist",
        "company": "CSC",
        "location": "Gurugram, Haryana, India",
        "remote": False,
        "description": "Conduct Client Onboarding for various jurisdictions, file reviews to confirm that all Customer/Client Due Diligence (CDD) and Know Your Customer/Client (KYC) documentation is in hand and up to date. Ensure compliance with regulatory standards.",
        "url": "https://emploive.com/jobs/5697039/associate-client-onboarding-specialist-csc",
        "source": "web:CSC",
        "status": "discovered",
    },
    {
        "title": "Onboarding Officer - Video KYC_Digital Banking",
        "company": "Hcbt (Kotak 811)",
        "location": "Noida, India",
        "remote": False,
        "description": "Complete full KYC verification for customers via secure video calls. Verify customer details, ensure documentation accuracy, and maintain high service standards throughout the VKYC process. Engage in cross-selling banking products.",
        "url": "https://growthroles.com/jobs/hcbt-onboarding-officer-video-kycdigital-banking-kotak-811-noida-19de5842ff8ad565",
        "source": "web:Hcbt",
        "status": "discovered",
    },
    {
        "title": "Financial Crime Compliance Analyst",
        "company": "AML RightSource",
        "location": "Delhi NCR, India",
        "remote": False,
        "description": "Detect and investigate unusual financial activity, perform quality control work, and review client files for KYC procedures. Identify data anomalies and red flags for money laundering, terrorist financing, fraud, sanctions violations.",
        "url": "https://amlrightsource.wd1.myworkdayjobs.com/en-US/amlrightsource/job/Financial-Crime-Compliance-Analyst--Delhi-NCR_R-101435",
        "source": "web:AMLRightSource",
        "status": "discovered",
    },
    {
        "title": "KYC Analyst",
        "company": "Randstad Enterprise",
        "location": "Noida, Uttar Pradesh, India",
        "remote": False,
        "description": "Perform reviews of KYC documents from clients to independently assess whether Client Due Diligence Policy and regulatory requirements have been adhered to. End-to-end KYC knowledge and experience required.",
        "url": "https://india.randstadenterprise.talent-community.com/projects/kyc-analyst/70140",
        "source": "web:Randstad",
        "status": "discovered",
    },
    {
        "title": "Specialist KYC/AML Internal Audit Services Advisory",
        "company": "PwC",
        "location": "Gurugram, India",
        "remote": False,
        "description": "Conduct thorough due diligence on clients by gathering and analyzing client information to verify compliance with regulatory requirements. Perform initial checks on client documents. Conduct sanction screening and adverse media screening. 3-6 years of experience in KYC, AML compliance.",
        "url": "https://pwc.wd3.myworkdayjobs.com/en-US/Global_Experienced_Careers/job/IN-Associate-Fraud-Investigation-Investigation-and-Dispute-Advisory-Gurgaon_734301WD-1",
        "source": "web:PwC",
        "status": "discovered",
    },
]


def seed_jobs(db: Session):
    profile = db.query(Profile).first()
    if not profile:
        print("No profile found. Run seed_profile.py first.")
        return

    imported = 0
    for item in NISHITA_JOBS:
        existing = db.query(Job).filter(Job.url == item["url"]).first()
        if existing:
            continue

        job = Job(
            id=uuid.uuid4().hex,
            title=item["title"],
            company=item["company"],
            location=item["location"],
            remote=item["remote"],
            description=item["description"],
            url=item["url"],
            source=item["source"],
            status=item["status"],
        )
        db.add(job)
        imported += 1

    db.commit()
    print(f"Imported {imported} jobs.")


def create_applications(db: Session):
    profile = db.query(Profile).first()
    if not profile:
        return

    jobs = db.query(Job).filter(Job.source.in_(["web:Barclays", "web:Empenofore", "web:CSC", "web:Hcbt", "web:AMLRightSource", "web:Randstad", "web:PwC"])).all()
    created = 0
    for job in jobs:
        existing = db.query(Application).filter(Application.job_id == job.id).first()
        if existing:
            continue

        app = Application(
            id=uuid.uuid4().hex,
            job_id=job.id,
            company=job.company,
            job_title=job.title,
            job_url=job.url,
            source=job.source,
            status="preparing",
            date_discovered=datetime.utcnow(),
        )
        db.add(app)
        created += 1

    db.commit()
    print(f"Created {created} applications.")


if __name__ == "__main__":
    db = SessionLocal()
    try:
        seed_jobs(db)
        create_applications(db)
    finally:
        db.close()

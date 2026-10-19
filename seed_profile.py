#!/usr/bin/env python3
"""Seed NSita's verified profile into the database."""
import sys
import os

BACKEND_DIR = os.path.join(os.path.dirname(__file__), "backend")
sys.path.insert(0, BACKEND_DIR)
os.chdir(BACKEND_DIR)

from sqlalchemy.orm import Session
from app.database import engine, Base, SessionLocal
from app.models import Profile, AutoApplySettings
from datetime import datetime

NISHITA_PROFILE = {
    "full_name": "NSita Sen",
    "email": "NSitasen8@gmail.com",
    "phone": "+91 9729887982",
    "location": "Rewari, Haryana 123401",
    "preferred_locations": ["Rewari, Haryana", "Gurgaon", "Delhi NCR"],
    "education": [
        {
            "degree": "MBA — Marketing & HR",
            "school": "Chandigarh University",
            "period": "2022–2024",
        },
        {
            "degree": "BBA — Marketing & HR",
            "school": "Shoolini University",
            "period": "2019–2022",
        },
    ],
    "experience": [
        {
            "title": "Assistant Manager — Banking Operations, KYC & Compliance",
            "company": "Axis Bank",
            "period": "October 2024 – Present",
            "bullets": [
                "Conduct video-based KYC verification according to regulatory guidelines.",
                "Follow RBI KYC guidelines and internal compliance policies.",
                "Maintain low compliance errors during verification.",
                "Maintain high quality scores in internal and external audits.",
                "Follow standard operating procedures consistently.",
                "Deliver professional and courteous customer interactions during video calls.",
                "Act on audit feedback and close gaps within timelines.",
                "Improve verification quality based on quality reviews.",
            ],
        },
        {
            "title": "Trainee — Store Management",
            "company": "American Eagle (Aditya Birla Fashion and Retail Ltd.)",
            "period": "June 2023 – August 2023",
            "bullets": [
                "Store management and development.",
                "Store layout and setting.",
            ],
        },
        {
            "title": "Trainee — Marketing & Research",
            "company": "The Times of India",
            "period": "July 2021 – August 2021",
            "bullets": [
                "Marketing and research development.",
                "Lead generation.",
                "Customer retention.",
            ],
        },
    ],
    "skills": [
        "Relationship Management",
        "Customer Due Diligence (CDD)",
        "Digital Banking Operations",
        "Quality Assurance and Audit Compliance",
        "Client Onboarding and Engagement",
        "Communication and Negotiation",
        "Regulatory Compliance (RBI Guidelines)",
        "Risk Assessment",
        "Attention to Detail",
        "Video KYC Operations",
        "Fraud Detection",
    ],
    "desired_roles": [
        "Banking Operations",
        "Assistant Manager — Banking Operations",
        "Video KYC",
        "KYC Operations",
        "Customer Due Diligence",
        "Client Onboarding",
        "Banking Compliance",
        "Regulatory Compliance",
        "Risk Assessment",
        "Quality Assurance",
        "Audit Compliance",
        "Digital Banking Operations",
        "Customer Relationship Management",
        "Banking Operations Associate",
    ],
    "search_keywords": [
        "KYC",
        "banking operations",
        "compliance",
        "video KYC",
        "customer due diligence",
        "client onboarding",
        "RBI",
        "audit",
        "quality assurance",
        "digital banking",
        "risk assessment",
        "fraud detection",
    ],
    "search_exclusions": [],
    "remote_preference": "onsite",
    "experience_level": "mid",
    "notice_period": "2 months",
}


def seed_profile(db: Session):
    existing = db.query(Profile).filter(Profile.id == "singleton").first()
    if existing:
        for key, value in NISHITA_PROFILE.items():
            setattr(existing, key, value)
        existing.updated_at = datetime.utcnow()
        print("Updated existing profile.")
    else:
        profile = Profile(id="singleton", **NISHITA_PROFILE)
        db.add(profile)
        print("Created new profile.")

    settings = db.query(AutoApplySettings).first()
    if not settings:
        settings = AutoApplySettings(
            id="singleton",
            enabled=False,
            emergency_stop=False,
            mode="manual",
            min_match_score=50,
            max_per_day=5,
            generate_cover_letter=True,
            auto_submit_enabled=False,
        )
        db.add(settings)
        print("Created default auto-apply settings.")

    db.commit()
    print("Profile seeded successfully.")


if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_profile(db)
    finally:
        db.close()

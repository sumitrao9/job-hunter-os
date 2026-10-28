
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Job, Profile
from app.services.matching import score_job_against_profile

router = APIRouter(prefix="/api/discovery", tags=["discovery"])

# Public boards that do not require a login. These are standard public ATS
# endpoints plus JobSpy-supported boards. No custom scraping.
DEFAULT_SOURCES: list[dict] = [
    # === Greenhouse (public API) ===
    {"kind": "greenhouse", "company": "GitLab", "url": "https://boards-api.greenhouse.io/v1/boards/gitlab/jobs"},
    {"kind": "greenhouse", "company": "Stripe", "url": "https://boards-api.greenhouse.io/v1/boards/stripe/jobs"},
    {"kind": "greenhouse", "company": "Fivetran", "url": "https://boards-api.greenhouse.io/v1/boards/fivetran/jobs"},
    {"kind": "greenhouse", "company": "Airbnb", "url": "https://boards-api.greenhouse.io/v1/boards/airbnb/jobs"},
    {"kind": "greenhouse", "company": "Razorpay", "url": "https://boards-api.greenhouse.io/v1/boards/razorpaysoftwareprivatelimited/jobs"},
    {"kind": "greenhouse", "company": "Groww", "url": "https://boards-api.greenhouse.io/v1/boards/groww/jobs"},
    {"kind": "greenhouse", "company": "Databricks", "url": "https://boards-api.greenhouse.io/v1/boards/databricks/jobs"},
    {"kind": "greenhouse", "company": "Wise", "url": "https://boards-api.greenhouse.io/v1/boards/wise/jobs"},
    {"kind": "greenhouse", "company": "Cloudflare", "url": "https://boards-api.greenhouse.io/v1/boards/cloudflare/jobs"},
    {"kind": "greenhouse", "company": "Superapp", "url": "https://boards-api.greenhouse.io/v1/boards/superapp/jobs"},
    {"kind": "greenhouse", "company": "OpenFX", "url": "https://boards-api.greenhouse.io/v1/boards/openfx/jobs"},
    {"kind": "greenhouse", "company": "Krafton India", "url": "https://boards-api.greenhouse.io/v1/boards/kraftonindia/jobs"},
    {"kind": "greenhouse", "company": "Slice", "url": "https://boards-api.greenhouse.io/v1/boards/slice/jobs"},
    {"kind": "greenhouse", "company": "Chime", "url": "https://boards-api.greenhouse.io/v1/boards/chime/jobs"},
    {"kind": "greenhouse", "company": "Branch", "url": "https://boards-api.greenhouse.io/v1/boards/branch/jobs"},
    {"kind": "greenhouse", "company": "Turing", "url": "https://boards-api.greenhouse.io/v1/boards/turing/jobs"},
    {"kind": "greenhouse", "company": "Datadog", "url": "https://boards-api.greenhouse.io/v1/boards/datadog/jobs"},
    {"kind": "greenhouse", "company": "Elastic", "url": "https://boards-api.greenhouse.io/v1/boards/elastic/jobs"},
    {"kind": "greenhouse", "company": "MongoDB", "url": "https://boards-api.greenhouse.io/v1/boards/mongodb/jobs"},
    {"kind": "greenhouse", "company": "Braze", "url": "https://boards-api.greenhouse.io/v1/boards/braze/jobs"},
    {"kind": "greenhouse", "company": "Reddit", "url": "https://boards-api.greenhouse.io/v1/boards/reddit/jobs"},
    {"kind": "greenhouse", "company": "Twilio", "url": "https://boards-api.greenhouse.io/v1/boards/twilio/jobs"},
    {"kind": "greenhouse", "company": "Intercom", "url": "https://boards-api.greenhouse.io/v1/boards/intercom/jobs"},
    {"kind": "greenhouse", "company": "Asana", "url": "https://boards-api.greenhouse.io/v1/boards/asana/jobs"},
    {"kind": "greenhouse", "company": "Justworks", "url": "https://boards-api.greenhouse.io/v1/boards/justworks/jobs"},
    {"kind": "greenhouse", "company": "OneTrust", "url": "https://boards-api.greenhouse.io/v1/boards/onetrust/jobs"},
    {"kind": "greenhouse", "company": "Vercel", "url": "https://boards-api.greenhouse.io/v1/boards/vercel/jobs"},
    {"kind": "greenhouse", "company": "Mixpanel", "url": "https://boards-api.greenhouse.io/v1/boards/mixpanel/jobs"},
    {"kind": "greenhouse", "company": "LaunchDarkly", "url": "https://boards-api.greenhouse.io/v1/boards/launchdarkly/jobs"},
    {"kind": "greenhouse", "company": "New Relic", "url": "https://boards-api.greenhouse.io/v1/boards/newrelic/jobs"},
    {"kind": "greenhouse", "company": "Fastly", "url": "https://boards-api.greenhouse.io/v1/boards/fastly/jobs"},
    {"kind": "greenhouse", "company": "Everlaw", "url": "https://boards-api.greenhouse.io/v1/boards/everlaw/jobs"},
    {"kind": "greenhouse", "company": "Komodo Health", "url": "https://boards-api.greenhouse.io/v1/boards/komodohealth/jobs"},
    {"kind": "greenhouse", "company": "Webflow", "url": "https://boards-api.greenhouse.io/v1/boards/webflow/jobs"},
    {"kind": "greenhouse", "company": "Pendo", "url": "https://boards-api.greenhouse.io/v1/boards/pendo/jobs"},
    {"kind": "greenhouse", "company": "Contentful", "url": "https://boards-api.greenhouse.io/v1/boards/contentful/jobs"},
    {"kind": "greenhouse", "company": "Coursera", "url": "https://boards-api.greenhouse.io/v1/boards/coursera/jobs"},
    {"kind": "greenhouse", "company": "Udemy", "url": "https://boards-api.greenhouse.io/v1/boards/udemy/jobs"},
    {"kind": "greenhouse", "company": "HP", "url": "https://boards-api.greenhouse.io/v1/boards/hp/jobs"},
    {"kind": "greenhouse", "company": "Western Union", "url": "https://boards-api.greenhouse.io/v1/boards/westernunion/jobs"},
    {"kind": "greenhouse", "company": "Checkr", "url": "https://boards-api.greenhouse.io/v1/boards/checkr/jobs"},
    {"kind": "greenhouse", "company": "Calendly", "url": "https://boards-api.greenhouse.io/v1/boards/calendly/jobs"},
    {"kind": "greenhouse", "company": "Salsify", "url": "https://boards-api.greenhouse.io/v1/boards/salsify/jobs"},
    {"kind": "greenhouse", "company": "Newsela", "url": "https://boards-api.greenhouse.io/v1/boards/newsela/jobs"},
    # === Lever (public API) ===
    {"kind": "lever", "company": "Crypto.com", "url": "https://api.lever.co/v0/postings/crypto"},
    {"kind": "lever", "company": "Metabase", "url": "https://api.lever.co/v0/postings/metabase"},
    {"kind": "lever", "company": "Outreach", "url": "https://api.lever.co/v0/postings/outreach"},
    {"kind": "lever", "company": "Finix", "url": "https://api.lever.co/v0/postings/finix"},
    {"kind": "lever", "company": "Greenlight", "url": "https://api.lever.co/v0/postings/greenlight"},
    {"kind": "lever", "company": "Wealthfront", "url": "https://api.lever.co/v0/postings/wealthfront"},
    {"kind": "lever", "company": "AppZen", "url": "https://api.lever.co/v0/postings/appzen"},
    {"kind": "lever", "company": "Secureframe", "url": "https://api.lever.co/v0/postings/secureframe"},
    {"kind": "lever", "company": "ChowNow", "url": "https://api.lever.co/v0/postings/chownow"},
    {"kind": "lever", "company": "Minted", "url": "https://api.lever.co/v0/postings/minted"},
    {"kind": "lever", "company": "Offchain Labs", "url": "https://api.lever.co/v0/postings/offchainlabs"},
    {"kind": "lever", "company": "Lyra Health", "url": "https://api.lever.co/v0/postings/lyrahealth"},
    {"kind": "lever", "company": "Getlabs", "url": "https://api.lever.co/v0/postings/getlabs"},
    {"kind": "lever", "company": "Hive", "url": "https://api.lever.co/v0/postings/hive"},
    {"kind": "lever", "company": "Sysdig", "url": "https://api.lever.co/v0/postings/sysdig"},
    {"kind": "lever", "company": "Side", "url": "https://api.lever.co/v0/postings/sideinc"},
    {"kind": "lever", "company": "Baselane", "url": "https://api.lever.co/v0/postings/baselane"},
    {"kind": "lever", "company": "Peerspace", "url": "https://api.lever.co/v0/postings/peerspace"},
    # === Manual verified sources (India-relevant) ===
    {"kind": "web", "company": "Barclays", "url": "https://search.jobs.barclays/en/job/gurugram/kyc-analyst/13015/97463249712"},
    {"kind": "web", "company": "PwC", "url": "https://pwc.wd3.myworkdayjobs.com/en-US/Global_Experienced_Careers/job/IN-Associate-Fraud-Investigation-Investigation-and-Dispute-Advisory-Gurgaon_734301WD-1"},
    {"kind": "web", "company": "CSC", "url": "https://emploive.com/jobs/5697039/associate-client-onboarding-specialist-csc"},
    {"kind": "web", "company": "Empenofore Technologies", "url": "https://www.linkedin.com/posts/poojarrani_hiringnow-jobalert-wearehiring-activity-7479833644262522881-HhSM"},
    {"kind": "web", "company": "Hcbt (Kotak 811)", "url": "https://growthroles.com/jobs/hcbt-onboarding-officer-video-kycdigital-banking-kotak-811-noida-19de5842ff8ad565"},
    {"kind": "web", "company": "AML RightSource", "url": "https://amlrightsource.wd1.myworkdayjobs.com/en-US/amlrightsource/job/Financial-Crime-Compliance-Analyst--Delhi-NCR_R-101435"},
    {"kind": "web", "company": "Randstad Enterprise", "url": "https://india.randstadenterprise.talent-community.com/projects/kyc-analyst/70140"},
]


class SourceConfig(BaseModel):
    kind: str
    url: str
    company: str | None = None
    name: str | None = None
    item_key: str | None = ""


class DiscoveryRequest(BaseModel):
    sources: list[SourceConfig] | None = None
    score: bool = True


class BulkScoreRequest(BaseModel):
    job_ids: list[str] | None = None
    unscored_only: bool = False
    limit: int = 100


@router.get("/sources")
def get_default_sources():
    return {"sources": DEFAULT_SOURCES}


@router.post("/run")
def run_discovery_endpoint(request: DiscoveryRequest, db: Session = Depends(get_db)):
    """Fetch jobs using JobSpy for job boards and public ATS APIs."""
    from app.services.multi_discovery import discover

    sources = (
        [s.model_dump(exclude_none=True) for s in request.sources]
        if request.sources
        else DEFAULT_SOURCES
    )
    if not sources:
        raise HTTPException(status_code=400, detail="No job sources selected.")
    return discover(sources, max_workers=4)


@router.post("/score")
def bulk_score(request: BulkScoreRequest, db: Session = Depends(get_db)):
    """Score many jobs at once."""
    profile = db.query(Profile).first()
    if not profile:
        raise HTTPException(
            status_code=400, detail="Complete your profile before scoring jobs."
        )

    query = db.query(Job)
    if request.job_ids is not None:
        if not request.job_ids:
            return {"scored": 0, "message": "No jobs selected to score."}
        query = query.filter(Job.id.in_(request.job_ids))
    elif request.unscored_only:
        query = query.filter(Job.match_score.is_(None))
    query = query.order_by(Job.created_at.desc()).limit(max(1, min(request.limit, 500)))

    jobs = query.all()
    scored = 0
    for job in jobs:
        result = score_job_against_profile(profile, job)
        job.match_score = result.score
        job.match_evidence = result.evidence
        scored += 1
    db.commit()

    return {
        "scored": scored,
        "message": f"Scored {scored} job{'s' if scored != 1 else ''}.",
    }

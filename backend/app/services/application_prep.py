import re
from typing import Dict, List
from app.models import Profile, Job, Application

# Words that carry no signal when matching skills to a posting.
STOPWORDS = {
    "and", "or", "the", "with", "for", "you", "our", "your", "we", "are", "will",
    "have", "has", "this", "that", "from", "team", "role", "work", "years", "year",
    "experience", "using", "use", "into", "across", "about", "who", "but", "not",
    "all", "can", "their", "them", "they", "what", "when", "where", "how", "more",
    "new", "job", "jobs", "candidate", "candidates", "ability", "strong", "good",
    "great", "plus", "must", "should", "would", "could", "may", "well", "also",
}


def _tokens(text: str) -> List[str]:
    if not text:
        return []
    return [t for t in re.split(r"[^a-z0-9+#.]+", text.lower()) if t and len(t) > 1]


def relevant_skills(profile: Profile, job: Job, limit: int = 5) -> List[str]:
    """Pick the candidate's real skills that actually overlap the posting.

    Returns only skills the user listed on their profile. Nothing is invented.
    """
    skills = [s for s in (profile.skills or []) if s]
    if not skills:
        return []

    posting = set(_tokens(job.title or "") + _tokens(job.description or ""))
    if not posting:
        return skills[:limit]

    scored = []
    for skill in skills:
        skill_tokens = set(_tokens(skill))
        overlap = {t for t in skill_tokens if t not in STOPWORDS} & posting
        # A multi-word skill whose parts all appear is a stronger signal.
        if skill_tokens and skill_tokens <= posting:
            overlap |= {t for t in skill_tokens if t not in STOPWORDS}
        if overlap:
            scored.append((len(overlap), skill))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [skill for _, skill in scored[:limit]]


def _experience_lines(profile: Profile, limit: int = 2) -> List[str]:
    """Render real experience entries as short bullet sentences."""
    lines: List[str] = []
    for entry in (profile.experience or [])[:limit]:
        if not isinstance(entry, dict):
            continue
        title = entry.get("title") or entry.get("role") or entry.get("position")
        company = entry.get("company") or entry.get("employer")
        if not title:
            continue
        period = entry.get("period") or entry.get("duration")
        if company and period:
            span = f"{company} ({period})"
        elif company:
            span = str(company)
        else:
            span = str(period) if period else ""
        lines.append(f"{title}" + (f" at {span}" if span else ""))
    return lines


def prepare_application(profile: Profile, job: Job) -> Dict:
    """Build a cover letter and form answers from real profile data only.

    Nothing is fabricated: every claim traces back to a field the user entered.
    """
    title = job.title or "this position"
    company = job.company or "your company"
    name = profile.full_name or "Applicant"
    location = profile.location or ""

    matched = relevant_skills(profile, job)
    profile_skills = [s for s in (profile.skills or []) if s]
    experience = _experience_lines(profile)

    if matched:
        skill_sentence = (
            f"The work you describe lines up closely with my background in "
            f"{', '.join(matched)}."
        )
    elif profile_skills:
        skill_sentence = (
            f"I bring hands-on experience with {', '.join(profile_skills[:5])}."
        )
    else:
        skill_sentence = (
            "I am keen to bring my existing engineering background to this role."
        )

    role_match = ""
    roles = [r for r in (profile.desired_roles or []) if r]
    if roles and title:
        role_match = f" I am specifically targeting {roles[0]} roles like this one."

    exp_block = ""
    if experience:
        bullets = "\n".join(f"  - {line}" for line in experience)
        exp_block = f"Relevant experience:\n{bullets}\n\n"

    availability = ""
    if profile.notice_period:
        availability = f" I can start within {profile.notice_period}."
    elif profile.remote_preference:
        availability = f" I am looking for {profile.remote_preference} work."

    signature = name + (f"\n{location}" if location else "")

    cover_letter = (
        f"Dear Hiring Manager,\n\n"
        f"I am applying for the {title} position at {company}. "
        f"{skill_sentence}{role_match}\n\n"
        f"{exp_block}"
        f"I am drawn to {company} because this role matches the kind of problems I want to work on, "
        f"and I would welcome the chance to discuss how I can contribute to the team.{availability}\n\n"
        f"Thank you for your time and consideration.\n\n"
        f"Best regards,\n{signature}\n"
    )

    # Normalise blank lines produced by the optional experience block.
    cover_letter = re.sub(r"\n{3,}", "\n\n", cover_letter).strip() + "\n"

    form_answers = {
        "full_name": profile.full_name or "",
        "email": profile.email or "",
        "phone": profile.phone or "",
        "location": profile.location or "",
        "desired_roles": profile.desired_roles or [],
        "skills": profile.skills or [],
        "remote_preference": profile.remote_preference or "",
        "experience_level": profile.experience_level or "",
        "notice_period": profile.notice_period or "",
    }

    return {
        "cover_letter": cover_letter,
        "form_answers": form_answers,
        "action": "open_url",
        "url": job.url or "",
        "instructions": (
            "Review the generated cover letter and complete any missing answers, "
            "then open the original posting and submit it yourself."
        ),
    }


def generate_follow_up_message(profile: Profile, application: Application) -> str:
    name = profile.full_name or "Applicant"
    company = application.company or "your team"
    role = application.job_title or "the position"
    last = application.created_at.strftime("%d %b %Y") if application.created_at else "recently"
    return f"""Subject: Following up — {role} at {company}

Hi {company} hiring team,

I applied for the {role} role on {last} and wanted to follow up. I remain very interested in the opportunity and would love to share anything else that would be useful.

Thank you for your time.

Best regards,
{name}
"""
"""Profile-to-job matching.

Scoring is deterministic and explainable. Every component is weighted, the total
is normalised to 100, and each contribution is reported as evidence so the user
can see exactly why a job ranked where it did.

Token matching is used rather than substring checks because substring matching
produces nonsense: "go" matches "google", "r" matches "react".
"""
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

from app.models import Profile, Job

# Words that carry no signal when comparing a skill to a posting.
STOPWORDS: Set[str] = {
    "a", "an", "and", "any", "are", "as", "at", "be", "been", "but", "by", "can",
    "could", "do", "does", "for", "from", "has", "have", "how", "in", "into", "is",
    "it", "its", "may", "more", "must", "new", "no", "not", "of", "on", "or",
    "our", "out", "over", "own", "she", "should", "so", "some", "such", "than",
    "that", "the", "their", "them", "then", "there", "these", "they", "this",
    "those", "through", "to", "too", "under", "up", "us", "use", "using", "very",
    "was", "we", "well", "were", "what", "when", "where", "which", "while", "who",
    "whom", "why", "will", "with", "would", "you", "your", "role", "roles", "job",
    "jobs", "work", "working", "years", "year", "experience", "team", "teams",
    "company", "candidate", "candidates", "ability", "strong", "good", "great",
    "plus", "well", "also", "help", "helps", "across", "about", "people",
}

# Remote signals used to infer the remote flag from free-text locations.
REMOTE_TOKENS = {"remote", "anywhere", "wfh", "workfromhome", "distributed", "virtual"}
# Seniority ordering used to compare a job's implied level to the target level.
SENIORITY_ORDER = ["junior", "entry", "intern", "mid", "intermediate", "senior", "staff", "lead", "principal", "director"]

WEIGHTS = {
    "skills": 45,
    "role": 20,
    "location": 15,
    "remote": 10,
    "salary": 10,
}

# Frameworks that compete with each other. A React candidate should not score
# highly on a Vue or Angular posting just because both are "frontend".
# Family -> (display label, token variants)
FRONTEND_FRAMEWORKS = {
    "react": ("React", {"react", "reactjs", "nextjs", "next"}),
    "vue": ("Vue", {"vue", "vuejs", "nuxt"}),
    "angular": ("Angular", {"angular", "angularjs"}),
    "svelte": ("Svelte", {"svelte", "sveltekit"}),
    "ember": ("Ember", {"ember", "emberjs"}),
}
# Penalty applied when the posting leads with a framework the candidate lacks.
FRAMEWORK_CONFLICT_PENALTY = 20


@dataclass
class MatchResult:
    score: float
    evidence: List[str] = field(default_factory=list)
    gaps: List[str] = field(default_factory=list)
    components: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "score": self.score,
            "evidence": self.evidence,
            "gaps": self.gaps,
            "components": self.components,
        }


_HAS_SKLEARN = False

def _has_sklearn() -> bool:
    """Lazy check if sklearn is available."""
    global _HAS_SKLEARN
    if not _HAS_SKLEARN:
        try:
            import sklearn
            _HAS_SKLEARN = True
        except ImportError:
            _HAS_SKLEARN = False
    return _HAS_SKLEARN


def tokenize(text: Optional[str]) -> List[str]:
    """Lowercase word tokens, keeping + and . so c++ and node.js survive."""
    if not text:
        return []
    raw = re.split(r"[^a-z0-9+#.]+", text.lower())
    return [t for t in raw if t and len(t) > 1]


def content_tokens(text: Optional[str]) -> Set[str]:
    return {t for t in tokenize(text) if t not in STOPWORDS}


def normalize_skill(skill: str) -> str:
    return skill.strip().lower()


def _skill_tokens(skill: str) -> Set[str]:
    """Tokens for a skill, splitting multi-word skills into their parts."""
    return {t for t in tokenize(skill) if t not in STOPWORDS}


def matched_skills(skills: List[str], haystack: Set[str]) -> List[str]:
    """Return the skills genuinely present in the posting.

    A skill counts when all of its significant tokens appear, so "React" needs
    "react" and "Node.js" needs "node". Partial overlap does not count.
    """
    hits: List[str] = []
    for skill in skills:
        tokens = _skill_tokens(skill)
        if tokens and tokens <= haystack:
            hits.append(skill)
    return hits


def _infer_remote(job: Job) -> bool:
    if job.remote is not None:
        return bool(job.remote)
    location = (job.location or "").lower()
    text = f"{location} {job.title or ''}".lower()
    return any(token in text for token in REMOTE_TOKENS)


def _implied_seniority(text: str) -> Optional[str]:
    tokens = set(tokenize(text))
    for level in reversed(SENIORITY_ORDER):
        if level in tokens:
            return level
    return None


def framework_conflict(profile_skills: List[str], job: Job) -> Optional[str]:
    """Return the competing framework a posting leads with that the user lacks.

    Uses the job title, because a posting titled "(Vue)" is a strong signal that
    the stack is Vue even when the body happens to mention React once.
    """
    owned: Set[str] = set()
    for skill in profile_skills:
        tokens = _skill_tokens(skill)
        for family, (_label, variants) in FRONTEND_FRAMEWORKS.items():
            if tokens & variants:
                owned.add(family)

    title_tokens = {t for t in tokenize(job.title) if t not in STOPWORDS}

    named_here = {
        family: label
        for family, (label, variants) in FRONTEND_FRAMEWORKS.items()
        if variants & title_tokens
    }
    if not named_here:
        return None
    if owned & set(named_here):
        return None  # candidate already knows a framework named in the title

    # Report the family the candidate has the least claim to.
    remaining = [f for f in named_here if f not in owned]
    if not remaining:
        return None
    return named_here[sorted(remaining)[0]]


def _location_matches(profile_location: str, job_location: str) -> bool:
    """Compare by city tokens rather than raw substring.

    "Bengaluru, India" should not match "Bangalore, Karnataka", and a bare
    country should match anywhere in that country.
    """
    profile_tokens = {t for t in tokenize(profile_location) if t not in {"india", "us", "usa", "uk", "remote"}}
    job_tokens = {t for t in tokenize(job_location) if t not in {"india", "us", "usa", "uk", "remote"}}
    if not profile_tokens or not job_tokens:
        return False
    return bool(profile_tokens & job_tokens)


def score_job_against_profile(profile: Profile, job: Job) -> MatchResult:
    """Score a job against the profile and explain every point awarded."""
    result = MatchResult(score=0.0)

    profile_skills = [s for s in (profile.skills or []) if s and s.strip()]
    if not profile_skills:
        result.gaps.append("Add skills to your profile to get match scores.")
        return result

    # Build the searchable text once.
    haystack = content_tokens(
        " ".join(filter(None, [job.title, job.company, job.description, job.location]))
    )
    if not haystack:
        result.gaps.append("This posting has too little detail to score reliably.")

    # --- Skills (45) ---
    hits = matched_skills(profile_skills, haystack)
    if profile_skills:
        coverage = len(hits) / len(profile_skills)
        earned = round(WEIGHTS["skills"] * coverage)
        result.components["skills"] = earned
        if hits:
            result.evidence.append(f"Skill match ({len(hits)}/{len(profile_skills)}): {', '.join(hits[:8])}")
        missing = [s for s in profile_skills if s not in hits]
        if missing and len(missing) <= 8:
            result.gaps.append(f"Not mentioned in posting: {', '.join(missing[:8])}")

    # --- Role (20) ---
    roles = [r for r in (profile.desired_roles or []) if r and r.strip()]
    role_hit = False
    if roles and job.title:
        title_tokens = content_tokens(job.title)
        role_hits = [r for r in roles if _skill_tokens(r) and _skill_tokens(r) <= title_tokens]
        if role_hits:
            role_hit = True
            result.components["role"] = WEIGHTS["role"]
            result.evidence.append(f"Role matches your target: {role_hits[0]}")
        else:
            result.gaps.append(f"Title is not one of your target roles: {', '.join(roles[:4])}")

    # --- Exclusions are disqualifying, and always reported ---
    exclusions = [e for e in (profile.search_exclusions or []) if e and e.strip()]
    text_lower = " ".join(filter(None, [job.title, job.company, job.description])).lower()
    excluded_by = next(
        (e for e in exclusions if e.strip().lower() in text_lower), None
    )

    # Relevance gate: perks like "remote" or a matching city are not a match on
    # their own. Without a single skill or role overlap, the posting is simply
    # not relevant to this candidate and secondary factors must not prop it up.
    if not hits and not role_hit:
        if excluded_by:
            result.components["excluded"] = -100.0
            result.gaps.append(f"Excluded by your filter: {excluded_by}")
        else:
            result.gaps.append("No skill or role overlap with your profile.")
        result.score = 0.0
        return result

    if excluded_by:
        result.components["excluded"] = -100.0
        result.gaps.append(f"Excluded by your filter: {excluded_by}")

    # --- Seniority (part of role, capped so it cannot exceed the role budget) ---
    profile_level = (profile.experience_level or "").strip().lower()
    if profile_level and job.title:
        wanted = SENIORITY_ORDER.index(profile_level) if profile_level in SENIORITY_ORDER else None
        implied = _implied_seniority(f"{job.title} {job.description or ''}")
        if wanted is not None and implied:
            delta = SENIORITY_ORDER.index(implied) - wanted
            if delta == 0:
                bump = 8
            elif abs(delta) == 1:
                bump = 4
            else:
                bump = 0
                result.gaps.append(f"Posting looks {implied}; you target {profile_level}.")
            if bump:
                room = max(0, WEIGHTS["role"] - result.components.get("role", 0))
                result.components["role"] = result.components.get("role", 0) + min(bump, room)
                if delta == 0 and bump:
                    result.evidence.append(f"Seniority aligns with {profile_level}")

    # --- Location (15) ---
    if profile.location and job.location:
        if _location_matches(profile.location, job.location):
            result.components["location"] = WEIGHTS["location"]
            result.evidence.append("Location aligns with your profile")
        else:
            result.gaps.append(f"Based in {job.location}; you are in {profile.location}")

    # --- Remote (10) ---
    remote = _infer_remote(job)
    preference = (profile.remote_preference or "").strip().lower()
    if preference and remote:
        if preference == "remote":
            result.components["remote"] = WEIGHTS["remote"]
            result.evidence.append("Remote role matches your preference")
        elif preference in {"hybrid", "onsite", "on-site", "office"}:
            result.components["remote"] = WEIGHTS["remote"] / 2
            result.evidence.append(f"Remote-friendly role; you prefer {preference}")
        else:
            result.gaps.append(f"Role is remote; you prefer {preference}")
    if profile.preferred_locations:
        for preferred in profile.preferred_locations:
            if job.location and _location_matches(preferred, job.location):
                result.components["location"] = WEIGHTS["location"]
                result.evidence.append(f"Matches your preferred location: {preferred}")
                break

    # --- Salary (10) ---
    if job.salary_max and profile.min_salary:
        if job.salary_max >= profile.min_salary:
            result.components["salary"] = WEIGHTS["salary"]
            result.evidence.append("Salary meets your minimum")
        else:
            result.gaps.append(f"Top of range is {job.salary_max}, below your minimum")
    elif job.salary_min and profile.min_salary and job.salary_min < profile.min_salary:
        result.gaps.append("Listed salary is below your minimum")

    # --- Competing framework (penalty) ---
    conflict = framework_conflict(profile_skills, job)
    if conflict:
        result.components["framework_conflict"] = -float(FRAMEWORK_CONFLICT_PENALTY)
        result.gaps.append(
            f"Posting is built on {conflict}, which is not in your skills."
        )

    total = sum(result.components.values())
    result.score = round(max(0.0, min(100.0, total)), 1)
    return result


@dataclass
class ATSScore:
    """ATS compatibility score (0–100) with breakdown."""
    score: float
    keyword_match: float
    section_score: float
    format_score: float
    missing_keywords: List[str]
    recommendations: List[str]


def score_ats_compatibility(
    resume_text: str,
    job_description: str,
    profile_skills: Optional[List[str]] = None,
) -> ATSScore:
    """Score how ATS-friendly a resume is for a given job description.

    Uses TF-IDF cosine similarity for keyword matching (from Budige/resume-ats-optimizer).
    Falls back to token-based scoring when scikit-learn is not installed.
    """
    if not resume_text or not job_description:
        return ATSScore(
            score=0.0, keyword_match=0.0, section_score=0.0, format_score=0.0,
            missing_keywords=[], recommendations=["Resume or job description is empty"],
        )

    # --- Keyword matching (TF-IDF cosine similarity) ---
    if _has_sklearn():
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics.pairwise import cosine_similarity
            vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), max_features=500)
            tfidf = vectorizer.fit_transform([resume_text.lower(), job_description.lower()])
            keyword_match = float(cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0])
        except Exception:
            keyword_match = _token_overlap_score(resume_text, job_description)
    else:
        keyword_match = _token_overlap_score(resume_text, job_description)

    keyword_pct = round(keyword_match * 100, 1)

    # --- Section completeness ---
    section_keywords = {
        "experience": ["experience", "work history", "employment", "career"],
        "skills": ["skills", "technical", "competencies"],
        "education": ["education", "degree", "university", "college"],
        "projects": ["projects", "portfolio"],
    }
    resume_lower = resume_text.lower()
    present_sections = sum(
        1 for kw_list in section_keywords.values()
        if any(kw in resume_lower for kw in kw_list)
    )
    section_score = round((present_sections / len(section_keywords)) * 100, 1)

    # --- Format compliance ---
    lines = [l for l in resume_text.split("\n") if l.strip()]
    has_bullets = any(l.strip().startswith(("•", "-", "*", "—")) for l in lines)
    has_dates = bool(re.search(r"\d{4}", resume_text))
    has_contact = bool(re.search(r"@\w+\.\w+", resume_text))
    format_checks = [has_bullets, has_dates, has_contact]
    format_score = round(sum(format_checks) / len(format_checks) * 100, 1)

    # --- Missing keywords ---
    missing_keywords = []
    if profile_skills:
        job_tokens = set(content_tokens(job_description))
        for skill in profile_skills:
            tokens = _skill_tokens(skill)
            if tokens and not tokens <= job_tokens:
                missing_keywords.append(skill)

    # --- Recommendations ---
    recommendations = []
    if keyword_pct < 40:
        recommendations.append("Add more keywords from the job description to your resume")
    if section_score < 75:
        missing_sections = [
            name for name, kws in section_keywords.items()
            if not any(kw in resume_lower for kw in kws)
        ]
        recommendations.append(f"Add missing sections: {', '.join(missing_sections)}")
    if format_score < 75:
        if not has_bullets:
            recommendations.append("Use bullet points for work experience entries")
        if not has_dates:
            recommendations.append("Include dates for all positions")
        if not has_contact:
            recommendations.append("Ensure contact info (email) is present")

    total = round(
        keyword_pct * 0.5 + section_score * 0.25 + format_score * 0.25,
        1,
    )
    total = min(100.0, total)

    return ATSScore(
        score=total,
        keyword_match=keyword_pct,
        section_score=section_score,
        format_score=format_score,
        missing_keywords=missing_keywords,
        recommendations=recommendations,
    )


def _token_overlap_score(text_a: str, text_b: str) -> float:
    """Simple Jaccard overlap fallback when sklearn is unavailable."""
    tokens_a = set(content_tokens(text_a))
    tokens_b = set(content_tokens(text_b))
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = len(tokens_a & tokens_b)
    union = len(tokens_a | tokens_b)
    return intersection / union if union > 0 else 0.0
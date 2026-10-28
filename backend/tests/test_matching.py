"""Tests for the deterministic matching and application-prep logic.

These cover the cases that previously produced wrong results: substring
collisions ("go" in "google"), framework conflicts, location mismatches, and
salary boundaries.
"""
import pytest

from app.services.application_prep import prepare_application, relevant_skills
from app.services.matching import (
    framework_conflict,
    matched_skills,
    score_job_against_profile,
    tokenize,
)


class FakeProfile:
    def __init__(self, **kw):
        self.full_name = kw.get("full_name", "Sumit Yadav")
        self.email = kw.get("email", "sumit@example.com")
        self.phone = kw.get("phone", "")
        self.location = kw.get("location", "Bengaluru, India")
        self.skills = kw.get("skills", ["React", "TypeScript", "Node.js"])
        self.desired_roles = kw.get("desired_roles", ["Frontend Engineer"])
        self.remote_preference = kw.get("remote_preference", "remote")
        self.experience_level = kw.get("experience_level", "mid")
        self.notice_period = kw.get("notice_period", "2 weeks")
        self.min_salary = kw.get("min_salary")
        self.preferred_locations = kw.get("preferred_locations")
        self.search_exclusions = kw.get("search_exclusions")
        self.experience = kw.get("experience", [])
        self.description = kw.get("description")


class FakeJob:
    def __init__(self, **kw):
        self.title = kw.get("title", "")
        self.company = kw.get("company", "Acme")
        self.location = kw.get("location", "Remote")
        self.remote = kw.get("remote", True)
        self.description = kw.get("description", "")
        self.url = kw.get("url", "https://example.com/job")
        self.salary_min = kw.get("salary_min")
        self.salary_max = kw.get("salary_max")


# --- tokenize ------------------------------------------------------------


def test_tokenize_keeps_language_suffixes():
    assert "c++" in tokenize("C++ development")
    assert "node.js" in tokenize("Node.js experience")


def test_tokenize_handles_empty():
    assert tokenize(None) == []
    assert tokenize("") == []


# --- matched_skills ------------------------------------------------------


def test_matched_skills_requires_full_token_overlap():
    haystack = {"react", "typescript", "graphql"}
    assert matched_skills(["React", "TypeScript"], haystack) == ["React", "TypeScript"]
    # "Node.js" is absent, so it must not match on the "node"-less partial.
    assert "Node.js" not in matched_skills(["Node.js"], haystack)


def test_matched_skills_does_not_match_substring_collisions():
    """The old implementation matched 'go' inside 'google'."""
    haystack = {"google", "analytics"}
    assert matched_skills(["Go"], haystack) == []


def test_matched_skills_handles_multiword_skills():
    haystack = {"node", "js", "express"}
    assert matched_skills(["Node JS"], haystack) == ["Node JS"]


# --- framework conflict --------------------------------------------------


@pytest.mark.parametrize(
    "title,skills,expected",
    [
        ("Senior Frontend Engineer (Vue)", ["React"], "Vue"),
        ("Senior Frontend Engineer (Angular)", ["React"], "Angular"),
        ("Full Stack Engineer (Svelte)", ["React"], "Svelte"),
        ("Senior React Engineer", ["React"], None),
        ("Senior Frontend Engineer", ["React"], None),
        ("Vue Developer", ["Vue"], None),          # candidate owns it
        ("Vue Developer", ["Vue", "React"], None),  # owns the named framework
        ("Backend Engineer, Go", ["React"], None),  # "Go" is not a frontend conflict
        ("Next.js Engineer", ["Next.js"], None),
    ],
)
def test_framework_conflict(title, skills, expected):
    assert framework_conflict(skills, FakeJob(title=title)) == expected


# --- scoring -------------------------------------------------------------


def test_score_requires_skills_in_profile():
    result = score_job_against_profile(FakeProfile(skills=[]), FakeJob(title="React Engineer"))
    assert result.score == 0.0
    assert "Add skills" in " ".join(result.gaps)


def test_score_is_zero_for_unrelated_role():
    profile = FakeProfile(skills=["React", "TypeScript"], desired_roles=["Frontend Engineer"])
    job = FakeJob(
        title="Cardiologist",
        description="Diagnose heart conditions in patients.",
        location="Remote",
    )
    result = score_job_against_profile(profile, job)
    assert result.score == 0.0


def test_skill_coverage_is_proportional():
    profile = FakeProfile(skills=["React", "TypeScript", "Kubernetes", "Terraform", "Rust"])
    strong = FakeJob(title="React Engineer", description="React and TypeScript required.")
    weak = FakeJob(title="React Engineer", description="Some React work.")
    assert score_job_against_profile(profile, strong).score > score_job_against_profile(
        profile, weak
    ).score


def test_score_is_bounded_to_100():
    profile = FakeProfile(
        skills=["React"],
        desired_roles=["React"],
        min_salary=1,
        preferred_locations=["Bengaluru"],
    )
    job = FakeJob(
        title="React Engineer",
        description="React",
        location="Bengaluru, India",
        remote=True,
        salary_max=999_999,
    )
    result = score_job_against_profile(profile, job)
    assert 0.0 <= result.score <= 100.0


def test_location_mismatch_reduces_score():
    profile = FakeProfile(location="Bengaluru, India", desired_roles=[])
    job = FakeJob(title="Engineer", location="Berlin, Germany", description="")
    result = score_job_against_profile(profile, job)
    assert "location" not in result.components


def test_salary_below_minimum_is_flagged():
    # The posting must be relevant, otherwise the relevance gate applies first.
    profile = FakeProfile(skills=["React"], min_salary=200_000, desired_roles=[])
    job = FakeJob(title="React Engineer", description="React", salary_max=120_000)
    result = score_job_against_profile(profile, job)
    assert "salary" not in result.components
    assert any("below your minimum" in g for g in result.gaps)


def test_salary_meeting_minimum_scores():
    profile = FakeProfile(skills=["React"], min_salary=200_000, desired_roles=[])
    job = FakeJob(title="React Engineer", description="React", salary_max=250_000)
    result = score_job_against_profile(profile, job)
    assert result.components.get("salary") == 10


def test_exclusion_zeroes_the_score():
    profile = FakeProfile(skills=["React"], search_exclusions=["cryptocurrency"])
    job = FakeJob(title="React Engineer", description="Build cryptocurrency systems")
    result = score_job_against_profile(profile, job)
    assert result.score == 0.0
    assert any("Excluded" in g for g in result.gaps)


def test_exclusion_reported_even_when_irrelevant():
    """An excluded job must say why, not just look like an unrelated one."""
    profile = FakeProfile(skills=["React"], search_exclusions=["cryptocurrency"])
    job = FakeJob(title="Cardiologist", description="cryptocurrency trader wanted")
    result = score_job_against_profile(profile, job)
    assert result.score == 0.0
    assert any("Excluded" in g for g in result.gaps)


def test_remote_alone_does_not_create_a_match():
    """Perks must not prop up a posting with no actual overlap."""
    profile = FakeProfile(
        skills=["React", "TypeScript"],
        desired_roles=["Frontend Engineer"],
        remote_preference="remote",
        location="Bengaluru, India",
    )
    job = FakeJob(
        title="Cardiologist",
        description="Diagnose heart conditions.",
        location="Remote",
        remote=True,
    )
    result = score_job_against_profile(profile, job)
    assert result.score == 0.0
    assert any("No skill or role overlap" in g for g in result.gaps)


def test_framework_conflict_penalises_score():
    profile = FakeProfile(skills=["React"], desired_roles=[])
    react = FakeJob(title="React Engineer", description="React")
    vue = FakeJob(title="Vue Engineer", description="Vue")
    assert score_job_against_profile(profile, vue).score < score_job_against_profile(
        profile, react
    ).score


def test_seniority_mismatch_is_reported():
    profile = FakeProfile(
        skills=["React"], experience_level="junior", desired_roles=[]
    )
    job = FakeJob(title="Principal React Engineer", description="React")
    result = score_job_against_profile(profile, job)
    assert any("senior" in g.lower() or "principal" in g.lower() for g in result.gaps)


def test_result_serialises_expected_keys():
    payload = score_job_against_profile(FakeProfile(), FakeJob(title="React")).to_dict()
    assert set(payload) == {"score", "evidence", "gaps", "components"}


# --- relevant skills for cover letters -----------------------------------


def test_relevant_skills_prefers_posting_overlaps():
    profile = FakeProfile(skills=["React", "TypeScript", "Node.js", "Python", "GraphQL", "AWS"])
    job = FakeJob(
        title="Senior React Engineer",
        description="React and TypeScript with Node.js and GraphQL. AWS experience required.",
    )
    picks = relevant_skills(profile, job)
    assert "React" in picks
    assert "Python" not in picks


def test_relevant_skills_without_posting_returns_initial_skills():
    profile = FakeProfile(skills=["React", "Go"])
    picks = relevant_skills(profile, FakeJob(title="", description=""))
    assert picks == ["React", "Go"]


# --- cover letter --------------------------------------------------------


def test_cover_letter_uses_real_profile_data_only():
    profile = FakeProfile(
        full_name="Sumit Yadav",
        skills=["React", "TypeScript"],
        experience=[{"title": "Frontend Engineer", "company": "Acme", "period": "2022-2025"}],
    )
    job = FakeJob(title="Senior React Engineer", company="TechCorp")
    letter = prepare_application(profile, job)["cover_letter"]

    assert "Sumit Yadav" in letter
    assert "Senior React Engineer" in letter
    assert "TechCorp" in letter
    assert "Frontend Engineer at Acme (2022-2025)" in letter
    # No fabricated achievements.
    assert "%" not in letter
    assert "$" not in letter


def test_cover_letter_signature_newline_is_real():
    profile = FakeProfile(full_name="Sumit Yadav", location="Bengaluru, India")
    letter = prepare_application(profile, FakeJob())["cover_letter"]
    assert "Sumit Yadav\nBengaluru, India" in letter
    assert "\\n" not in letter


def test_cover_letter_has_no_triple_blank_lines():
    profile = FakeProfile(experience=[{"title": "Engineer"}])
    letter = prepare_application(profile, FakeJob())["cover_letter"]
    assert "\n\n\n" not in letter


def test_form_answers_mirror_profile():
    profile = FakeProfile(email="s@e.com", phone="123", remote_preference="remote")
    answers = prepare_application(profile, FakeJob())["form_answers"]
    assert answers["email"] == "s@e.com"
    assert answers["phone"] == "123"
    assert answers["remote_preference"] == "remote"


def test_prepare_handles_sparse_profile_without_crashing():
    """An empty profile must not raise; the UI needs a letter it can still edit."""
    empty = FakeProfile(full_name="", email="", location="", skills=[], desired_roles=[],
                        experience=[], remote_preference="", experience_level="",
                        notice_period="")
    result = prepare_application(empty, FakeJob(title="Engineer", company="Acme"))
    assert result["cover_letter"].strip()
    assert result["form_answers"]["email"] == ""

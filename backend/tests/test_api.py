import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# conftest sets DATABASE_URL to a throwaway file and rebuilds the schema for
# every test, so the `client` fixture is shared and no test touches real data.
from fastapi.testclient import TestClient  # noqa: F401,E402


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_profile_crud(client):
    response = client.post("/api/profile/", json={"full_name": "Test", "email": "test@example.com"})
    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] == "Test"

    response = client.get("/api/profile/")
    assert response.status_code == 200
    assert response.json()["email"] == "test@example.com"


def test_jobs_and_applications(client):
    response = client.post("/api/jobs/", json={"title": "Dev", "company": "Acme", "source": "manual"})
    assert response.status_code == 200

    response = client.post("/api/applications/", json={"company": "Acme", "job_title": "Dev", "status": "discovered"})
    assert response.status_code == 200

    response = client.get("/api/dashboard/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["total_jobs"] >= 1


def test_onboarding_status(client):
    response = client.get("/api/onboarding/status")
    assert response.status_code == 200
    data = response.json()
    assert "completed" in data
    assert "profile_exists" in data


def test_discovery_sources(client):
    response = client.get("/api/discovery/sources")
    assert response.status_code == 200
    data = response.json()
    assert "sources" in data
    assert len(data["sources"]) > 0


def test_cover_letter_generation(client):
    client.post("/api/profile/", json={"full_name": "Test", "email": "test@example.com", "skills": ["react"], "desired_roles": ["frontend"]})
    client.post("/api/jobs/", json={"title": "Frontend Developer", "company": "Acme", "source": "manual"})
    response = client.post("/api/cover-letter/generate", json={"job_id": "1"})
    assert response.status_code == 200
    data = response.json()
    assert "cover_letter" in data
    assert len(data["cover_letter"]) > 0


def test_follow_ups(client):
    response = client.get("/api/follow-ups/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_export_endpoints(client):
    response = client.get("/api/export/jobs.json")
    assert response.status_code == 200
    assert "jobs" in response.json()

    response = client.get("/api/export/applications.json")
    assert response.status_code == 200
    assert "applications" in response.json()


def test_jobs_listing_survives_list_match_evidence(client):
    """Regression: match_evidence is a list, but was typed as dict.

    This 500'd /api/jobs, which is the app's main page.
    """
    client.post(
        "/api/profile/",
        json={"full_name": "T", "skills": ["react"], "desired_roles": ["react"]},
    )
    job_id = client.post(
        "/api/jobs/",
        json={
            "title": "Senior React Engineer",
            "company": "Acme",
            "source": "manual",
            "description": "React and TypeScript.",
        },
    ).json()["id"]

    response = client.post(f"/api/matching/score/{job_id}")
    assert response.status_code == 200

    response = client.get("/api/jobs/")
    assert response.status_code == 200
    rows = response.json()
    assert len(rows) == 1
    assert isinstance(rows[0]["match_evidence"], list)
    assert rows[0]["match_evidence"]


def test_bulk_score_rejects_empty_selection(client):
    """An empty id list must score nothing, not fall back to scoring everything."""
    client.post(
        "/api/profile/",
        json={"full_name": "T", "skills": ["react"], "desired_roles": ["react"]},
    )
    for title in ("React Engineer", "Backend Engineer", "Data Engineer"):
        client.post("/api/jobs/", json={"title": title, "company": "Acme", "source": "manual"})

    response = client.post("/api/discovery/score", json={"job_ids": []})
    assert response.status_code == 200
    assert response.json()["scored"] == 0


def test_bulk_score_scores_only_requested_ids(client):
    a = client.post("/api/jobs/", json={"title": "React A", "company": "Acme", "source": "manual"}).json()["id"]
    client.post("/api/jobs/", json={"title": "React B", "company": "Acme", "source": "manual"})
    client.post(
        "/api/profile/",
        json={"full_name": "T", "skills": ["react"], "desired_roles": ["react"]},
    )

    response = client.post("/api/discovery/score", json={"job_ids": [a]})
    assert response.status_code == 200
    assert response.json()["scored"] == 1


def test_bulk_score_requires_a_profile(client):
    response = client.post("/api/discovery/score", json={"unscored_only": True})
    assert response.status_code == 400


def test_v2_sources_endpoint(client):
    from app.database import get_db
    from app.models import JobSource
    db = next(get_db())
    for adapter, name in [("adzuna", "Adzuna"), ("remotive", "Remotive"), ("jsearch", "JSearch"), ("usajobs", "USAJOBS")]:
        db.add(JobSource(id=f"test-{adapter}", source_name=f"Test {name}", adapter=adapter, enabled=True))
    db.commit()
    db.close()

    response = client.get("/api/discovery/v2/sources")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    adapters = {s["adapter"] for s in data}
    assert "adzuna" in adapters
    assert "remotive" in adapters
    assert "jsearch" in adapters
    assert "usajobs" in adapters


def test_adzuna_skips_without_credentials(client):
    from app.services.multi_discovery import _discover_adzuna
    source = {
        "source_name": "Adzuna Test",
        "adapter": "adzuna",
        "country": "USA",
        "config": {"queries": [{"search_term": "test", "location": "NYC"}], "results_wanted": 5},
    }
    result = _discover_adzuna(source)
    assert result == []


def test_jsearch_skips_without_api_key(client):
    from app.services.multi_discovery import _discover_jsearch
    source = {
        "source_name": "JSearch Test",
        "adapter": "jsearch",
        "config": {"queries": [{"search_term": "test", "location": "NYC"}], "results_wanted": 5},
    }
    result = _discover_jsearch(source)
    assert result == []


def test_run_discovery_with_new_adapter(client):
    response = client.post(
        "/api/discovery/v2/run",
        json={
            "sources": [
                {
                    "id": "api-adzuna-test",
                    "source_name": "Adzuna Test",
                    "adapter": "adzuna",
                    "country": "USA",
                    "config": {"queries": [{"search_term": "test", "location": "NYC"}], "results_wanted": 5},
                }
            ]
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "sources" in data
    assert data["sources"][0]["status"] == "success"


def test_remoteok_adapter_handles_no_network(client):
    from app.services.multi_discovery import _discover_remoteok
    source = {
        "source_name": "RemoteOK Test",
        "adapter": "remoteok",
        "config": {"queries": [{"search_term": "test"}], "results_wanted": 3},
    }
    result = _discover_remoteok(source)
    assert isinstance(result, list)


def test_himalayas_adapter_handles_no_network(client):
    from app.services.multi_discovery import _discover_himalayas
    source = {
        "source_name": "Himalayas Test",
        "adapter": "himalayas",
        "config": {"queries": [{"search_term": "test"}], "results_wanted": 3},
    }
    result = _discover_himalayas(source)
    assert isinstance(result, list)


def test_all_new_adapters_routed(client):
    from app.services.multi_discovery import _discover_adzuna, _discover_remotive, _discover_jsearch, _discover_usajobs, _discover_remoteok, _discover_himalayas
    adapters = [_discover_adzuna, _discover_remotive, _discover_jsearch, _discover_usajobs, _discover_remoteok, _discover_himalayas]
    for adapter_fn in adapters:
        result = adapter_fn({"source_name": "test", "adapter": "test", "config": {"queries": [{"search_term": "x"}]}})
        assert isinstance(result, list)

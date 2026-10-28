#!/usr/bin/env python3
"""
Multi-source job discovery worker.

Uses JobSpy for LinkedIn/Indeed/Naukri/Glassdoor and custom adapters for ATS boards.
Runs queries in parallel, normalizes data, aggressively deduplicates, and stores results.
"""
import concurrent.futures
import hashlib
import re
import uuid
from datetime import datetime
from html import unescape
from typing import Any

import feedparser
import pandas as pd
import requests

from app.config import settings
from app.database import SessionLocal
from app.models import (
    Job,
    JobSource,
    JobSourceMapping,
    Profile,
    SourceRun,
)
from app.services.matching import score_job_against_profile

# --------------- normalization helpers ---------------

def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    text = unescape(text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _normalize_url(url: str | None) -> str:
    if not url:
        return ""
    url = url.strip()
    url = re.sub(r"[?&]utm_[^&]*", "", url)
    url = re.sub(r"[?&]gh_src=[^&]*", "", url)
    url = re.sub(r"[?&]ref=[^&]*", "", url)
    url = re.sub(r"[?&]source=[^&]*", "", url)
    url = url.rstrip("?&")
    url = re.sub(r"//+", "//", url)
    return url.lower().rstrip("/")


def _fingerprint(title: str, company: str, location: str, description: str) -> str:
    """Deterministic fingerprint for dedup Level 3/4."""
    norm = " | ".join([
        (title or "").lower().strip(),
        (company or "").lower().strip(),
        (location or "").lower().strip(),
        (description or "")[:500].lower().strip(),
    ])
    return hashlib.sha256(norm.encode()).hexdigest()


# --------------- adapter helpers ---------------

def _discover_jobspy(source: dict) -> list[dict]:
    """Run JobSpy for LinkedIn/Indeed/Naukri/Glassdoor/ZipRecruiter/Google/Bayt/BDJobs."""
    queries = source.get("config", {}).get("queries", [])
    if not queries:
        return []

    adapter = source.get("adapter", "").lower()
    site_map = {
        "linkedin": ["linkedin"],
        "indeed": ["indeed"],
        "naukri": ["naukri"],
        "glassdoor": ["glassdoor"],
        "zip_recruiter": ["zip_recruiter"],
        "ziprecruiter": ["zip_recruiter"],
        "google": ["google"],
        "bayt": ["bayt"],
        "bdjobs": ["bdjobs"],
    }
    sites = site_map.get(adapter)
    if not sites:
        sites = ["indeed", "linkedin", "naukri", "glassdoor", "zip_recruiter", "google", "bayt", "bdjobs"]

    results = []
    for q in queries:
        search_term = q.get("search_term")
        location = q.get("location", "India")
        if not search_term:
            continue
        try:
            df = _jobspy_scrape(sites, search_term, location, source)
            if df is not None and len(df) > 0:
                for record in df.to_dict("records"):
                    norm = {
                        "source_job_id": str(record.get("id") or record.get("job_url") or ""),
                        "title": _clean_text(record.get("title") or ""),
                        "company": _clean_text(record.get("company") or record.get("company_name") or source.get("source_name", "")),
                        "location": _clean_text(record.get("location") or ""),
                        "remote": bool(record.get("is_remote") or _is_remote(_clean_text(record.get("location") or ""), record.get("title") or "")),
                        "description": _clean_text(record.get("description") or "")[:6000],
                        "url": _normalize_url(record.get("job_url") or record.get("job_url_direct") or ""),
                        "salary_min": record.get("min_amount"),
                        "salary_max": record.get("max_amount"),
                        "date_posted": _safe_parse_date(record.get("date_posted")),
                        "job_type": record.get("job_type"),
                        "skills": _clean_text(record.get("skills") or "") or None,
                        "source_site": record.get("site") or adapter,
                    }
                    results.append(norm)
        except Exception as exc:
            print(f"[jobspy] {source['source_name']} query failed: {search_term} / {location}: {exc}")
    return results


def _jobspy_scrape(sites: list[str], search_term: str, location: str, source: dict) -> pd.DataFrame | None:
    from jobspy import scrape_jobs
    config = source.get("config", {})
    results_wanted = config.get("results_wanted", 20)
    hours_old = config.get("hours_old", 72)
    country_indeed = "india" if "indeed" in sites else "usa"
    google_search_term = config.get("google_search_term") or f"{search_term} jobs in {location}"
    return scrape_jobs(
        site_name=sites,
        search_term=search_term,
        location=location,
        results_wanted=results_wanted,
        country_indeed=country_indeed,
        hours_old=hours_old,
        google_search_term=google_search_term,
        verbose=False,
    )


def _discover_ats(source: dict) -> list[dict]:
    """Greenhouse / Lever / Ashby public board."""
    url = source.get("base_url") or source.get("url")
    if not url:
        return []
    kind = source.get("adapter", "").lower() or source.get("kind", "").lower()
    try:
        resp = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code != 200:
            return []
        data = resp.json()
    except Exception as exc:
        print(f"[ats] {source['source_name']} fetch failed: {exc}")
        return []

    items: list[dict] = []
    if kind == "greenhouse":
        for job in data.get("jobs", []):
            loc = _clean_text(job.get("location") or "").strip()
            items.append({
                "source_job_id": str(job.get("id")),
                "title": _clean_text(job.get("title")),
                "company": _clean_text(job.get("company_name") or source["source_name"]),
                "location": loc,
                "remote": _is_remote(loc, job.get("title")),
                "description": _clean_text(job.get("content") or "")[:6000],
                "url": _normalize_url(job.get("absolute_url") or ""),
                "salary_min": job.get("salary_min"),
                "salary_max": job.get("salary_max"),
                "date_posted": job.get("updated_at") or job.get("created_at"),
                "job_type": None,
                "skills": None,
                "source_site": "greenhouse",
            })
    elif kind == "lever":
        for job in data if isinstance(data, list) else []:
            loc = _clean_text(job.get("categories", {}).get("location") or "").strip()
            items.append({
                "source_job_id": str(job.get("id")),
                "title": _clean_text(job.get("text")),
                "company": _clean_text(job.get("company") or source["source_name"]),
                "location": loc,
                "remote": _is_remote(loc, job.get("text")),
                "description": _clean_text(job.get("descriptionPlain") or job.get("description", "") or "")[:6000],
                "url": _normalize_url(job.get("hostedUrl") or ""),
                "salary_min": None,
                "salary_max": None,
                "date_posted": datetime.fromtimestamp(job["createdAt"] / 1000).isoformat() if job.get("createdAt") else None,
                "job_type": job.get("categories", {}).get("commitment"),
                "skills": None,
                "source_site": "lever",
            })
    elif kind == "ashby":
        for job in data.get("jobPostings", []):
            loc = _clean_text(job.get("locationName") or "").strip()
            items.append({
                "source_job_id": str(job.get("id")),
                "title": _clean_text(job.get("title")),
                "company": _clean_text(job.get("companyName") or source["source_name"]),
                "location": loc,
                "remote": bool(job.get("isRemote")),
                "description": _clean_html_to_text(job.get("jobDescription") or "")[:6000],
                "url": _normalize_url(f"https://jobs.ashbyhq.com/{source.get('base_url','').split('/')[-1]}/{job.get('id')}"),
                "salary_min": None,
                "salary_max": None,
                "date_posted": job.get("publishedDate"),
                "job_type": job.get("employmentType"),
                "skills": None,
                "source_site": "ashby",
            })
    return items


def _discover_rss(source: dict) -> list[dict]:
    """Parse RSS/Atom feeds for job listings."""
    feed_urls = source.get("config", {}).get("feed_urls", [])
    if not feed_urls:
        return []

    items: list[dict] = []
    for feed_url in feed_urls:
        try:
            feed = feedparser.parse(feed_url)
            source_name = source.get("source_name", "RSS Feed")
            for entry in feed.entries:
                title = _clean_text(entry.get("title", ""))
                link = _normalize_url(entry.get("link", ""))
                description = _clean_text(entry.get("description", "") or entry.get("summary", ""))[:6000]
                published = entry.get("published") or entry.get("updated")
                date_posted = _safe_parse_date(published)
                items.append({
                    "source_job_id": link or title,
                    "title": title,
                    "company": source_name,
                    "location": "",
                    "remote": _is_remote(description, title),
                    "description": description,
                    "url": link,
                    "salary_min": None,
                    "salary_max": None,
                    "date_posted": date_posted,
                    "job_type": None,
                    "skills": None,
                    "source_site": "rss",
                })
        except Exception as exc:
            print(f"[rss] {source['source_name']} feed failed: {feed_url}: {exc}")
    return items


def _discover_remoteok(source: dict) -> list[dict]:
    """RemoteOK API — free JSON feed, no auth, attribution required.

    https://remoteok.com/api
    """
    results: list[dict] = []
    headers = {
        "User-Agent": settings.user_agent,
        "Accept": "application/json",
    }
    try:
        resp = requests.get("https://remoteok.com/api", headers=headers, timeout=30)
        if resp.status_code != 200:
            print(f"[remoteok] HTTP {resp.status_code}")
            return []
        data = resp.json()
        if not isinstance(data, list):
            return []
        queries = source.get("config", {}).get("queries", [])
        keywords = [q.get("search_term", "").lower() for q in queries if q.get("search_term")]

        for job in data:
            title = _clean_text(job.get("title") or "")
            if not title:
                continue
            if keywords:
                combined = f"{title} {job.get('description', '')}".lower()
                if not any(kw in combined for kw in keywords if kw):
                    continue
            loc = _clean_text(job.get("location") or "")
            results.append({
                "source_job_id": str(job.get("id") or job.get("url") or ""),
                "title": title,
                "company": _clean_text(job.get("company") or ""),
                "location": loc,
                "remote": True,
                "description": _clean_text(job.get("description") or "")[:6000],
                "url": _normalize_url(job.get("url") or ""),
                "salary_min": job.get("salary"),
                "salary_max": job.get("salary_max"),
                "date_posted": _safe_parse_date(job.get("date") or job.get("posted")),
                "job_type": job.get("contract"),
                "skills": ", ".join(job.get("tags", [])),
                "source_site": "remoteok",
            })
    except Exception as exc:
        print(f"[remoteok] {source['source_name']} fetch failed: {exc}")
    return results


def _discover_himalayas(source: dict) -> list[dict]:
    """Himalayas API — remote+on-site jobs, no auth.

    https://himalayas.app/jobs/rss  (API docs: https://himalayas.app/api)
    """
    results: list[dict] = []
    headers = {"User-Agent": settings.user_agent}
    queries = source.get("config", {}).get("queries", [])
    keywords = [q.get("search_term", "").lower() for q in queries if q.get("search_term")]

    try:
        resp = requests.get("https://himalayas.app/api/v1/jobs?limit=50", headers=headers, timeout=30)
        if resp.status_code != 200:
            print(f"[himalayas] HTTP {resp.status_code}")
            return []
        data = resp.json()
        jobs = data.get("jobs", []) if isinstance(data, dict) else data
        for job in jobs:
            title = _clean_text(job.get("title") or job.get("job_title") or "")
            if not title:
                continue
            if keywords:
                combined = f"{title} {job.get('description', '')}".lower()
                if not any(kw in combined for kw in keywords if kw):
                    continue
            loc = _clean_text(job.get("location") or job.get("location_name") or "")
            results.append({
                "source_job_id": str(job.get("id") or job.get("job_hash") or ""),
                "title": title,
                "company": _clean_text(job.get("company") or job.get("company_name") or ""),
                "location": loc,
                "remote": bool(job.get("is_remote") or job.get("remote") or _is_remote(loc, title)),
                "description": _clean_text(job.get("description") or job.get("job_description") or "")[:6000],
                "url": _normalize_url(job.get("url") or job.get("job_url") or ""),
                "salary_min": job.get("salary_min") or job.get("min_salary"),
                "salary_max": job.get("salary_max") or job.get("max_salary"),
                "date_posted": _safe_parse_date(job.get("published_at") or job.get("created_at")),
                "job_type": job.get("job_type") or job.get("employment_type"),
                "skills": None,
                "source_site": "himalayas",
            })
    except Exception as exc:
        print(f"[himalayas] {source['source_name']} fetch failed: {exc}")
    return results


def _discover_adzuna(source: dict) -> list[dict]:
    """Adzuna Job Board API — free tier 250 req/day, global coverage.

    Requires ADZUNA_APP_ID and ADZUNA_APP_KEY in config (.env).
    https://developer.adzuna.com/overview
    """
    if not settings.adzuna_app_id or not settings.adzuna_app_key:
        print("[adzuna] No API credentials configured — skipping")
        return []

    queries = source.get("config", {}).get("queries", [])
    if not queries:
        return []

    country = source.get("country", "India")
    country_map = {
        "usa": "us", "united states": "us", "india": "in", "uk": "gb",
        "united kingdom": "gb", "canada": "ca", "australia": "au",
        "germany": "de", "france": "fr", "singapore": "sg",
    }
    country_code = country_map.get(country.lower(), "in")

    results: list[dict] = []
    results_wanted = source.get("config", {}).get("results_wanted", 20)
    headers = {"User-Agent": settings.user_agent}

    for q in queries:
        search_term = q.get("search_term")
        location = q.get("location", "")
        if not search_term:
            continue
        try:
            url = f"https://api.adzuna.com/v1/api/jobs/{country_code}/search/1"
            params = {
                "app_id": settings.adzuna_app_id,
                "app_key": settings.adzuna_app_key,
                "what": search_term,
                "where": location,
                "results_per_page": results_wanted,
                "max_days_old": source.get("config", {}).get("hours_old", 72) // 24,
            }
            resp = requests.get(url, params=params, headers=headers, timeout=30)
            if resp.status_code != 200:
                print(f"[adzuna] {search_term} / {location}: HTTP {resp.status_code}")
                continue
            data = resp.json()
            for job in data.get("results", []):
                loc_parts = []
                for k in ("area", "region", "country"):
                    v = job.get("location", {}).get(k)
                    if v:
                        if isinstance(v, list):
                            loc_parts.extend(str(x) for x in v)
                        else:
                            loc_parts.append(str(v))
                location_str = ", ".join(dict.fromkeys(loc_parts)) or location

                results.append({
                    "source_job_id": str(job.get("id") or job.get("redirect_url", "")),
                    "title": _clean_text(job.get("title") or ""),
                    "company": _clean_text(job.get("company", {}).get("display_name") or ""),
                    "location": location_str,
                    "remote": _is_remote(location_str, job.get("title")),
                    "description": _clean_text(job.get("description") or "")[:6000],
                    "url": _normalize_url(job.get("redirect_url") or ""),
                    "salary_min": job.get("salary_min"),
                    "salary_max": job.get("salary_max"),
                    "date_posted": _safe_parse_date(job.get("created")) or _safe_parse_date(job.get("updated")),
                    "job_type": None,
                    "skills": None,
                    "source_site": "adzuna",
                })
        except Exception as exc:
            print(f"[adzuna] {source['source_name']} query failed: {search_term} / {location}: {exc}")
    return results


def _discover_remotive(source: dict) -> list[dict]:
    """Remotive Remote Jobs API — free, no auth, requires attribution.

    https://remotive.com/remote-jobs/api
    """
    queries = source.get("config", {}).get("queries", [])
    if not queries:
        feed_urls = source.get("config", {}).get("feed_urls", [])
        if feed_urls:
            return _discover_remotive_feed(feed_urls, source)
        return []

    results: list[dict] = []
    base_url = "https://api.remotive.com/v1/jobs"
    headers = {"User-Agent": settings.user_agent}

    for q in queries:
        search_term = q.get("search_term", "")
        params = {"page": 1}
        try:
            resp = requests.get(base_url, params=params, headers=headers, timeout=30)
            if resp.status_code != 200:
                print(f"[remotive] HTTP {resp.status_code}")
                continue
            data = resp.json()
            for job in data.get("jobs", []):
                title = _clean_text(job.get("title") or "")
                if search_term and search_term.lower() not in title.lower() and search_term.lower() not in _clean_text(job.get("description") or "").lower():
                    continue
                loc = _clean_text(job.get("candidate_required_location") or "")
                results.append({
                    "source_job_id": str(job.get("id") or job.get("url", "")),
                    "title": title,
                    "company": _clean_text(job.get("company_name") or ""),
                    "location": loc,
                    "remote": True,
                    "description": _clean_text(job.get("description") or "")[:6000],
                    "url": _normalize_url(job.get("url") or ""),
                    "salary_min": None,
                    "salary_max": None,
                    "date_posted": _safe_parse_date(job.get("date_posted")),
                    "job_type": None,
                    "skills": job.get("tags"),
                    "source_site": "remotive",
                })
        except Exception as exc:
            print(f"[remotive] {source['source_name']} query failed: {exc}")
    return results


def _discover_remotive_feed(feed_urls: list[str], source: dict) -> list[dict]:
    """Fallback: parse Remotive RSS feeds."""
    items: list[dict] = []
    headers = {"User-Agent": settings.user_agent}
    for feed_url in feed_urls:
        try:
            resp = requests.get(feed_url, headers=headers, timeout=30)
            if resp.status_code != 200:
                continue
            feed = feedparser.parse(resp.content)
            for entry in feed.entries:
                title = _clean_text(entry.get("title", ""))
                link = _normalize_url(entry.get("link", ""))
                desc = _clean_text(entry.get("description", "") or entry.get("summary", ""))[:6000]
                items.append({
                    "source_job_id": link or title,
                    "title": title,
                    "company": source.get("source_name", "Remotive"),
                    "location": "",
                    "remote": True,
                    "description": desc,
                    "url": link,
                    "salary_min": None,
                    "salary_max": None,
                    "date_posted": _safe_parse_date(entry.get("published") or entry.get("updated")),
                    "job_type": None,
                    "skills": None,
                    "source_site": "remotive-rss",
                })
        except Exception as exc:
            print(f"[remotive-rss] feed failed: {feed_url}: {exc}")
    return items


def _discover_jsearch(source: dict) -> list[dict]:
    """JSearch (SerpApi/RapidAPI) — job search aggregation API.

    Free tier: 50 requests/month on RapidAPI. Requires JSEARCH_API_KEY.
    """
    if not settings.jsearch_api_key:
        print("[jsearch] No API key configured — skipping")
        return []

    queries = source.get("config", {}).get("queries", [])
    if not queries:
        return []

    results: list[dict] = []
    headers = {
        "X-RapidAPI-Key": settings.jsearch_api_key,
        "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
        "User-Agent": settings.user_agent,
    }

    for q in queries:
        search_term = q.get("search_term")
        location = q.get("location", "")
        if not search_term:
            continue
        query = f"{search_term} {location}".strip()
        params = {
            "query": query,
            "page": "1",
            "num_results": str(source.get("config", {}).get("results_wanted", 20)),
            "date_posted": "week",
            "remote_jobs_only": "false",
        }
        try:
            resp = requests.get("https://jsearch.p.rapidapi.com/search", params=params, headers=headers, timeout=30)
            if resp.status_code != 200:
                print(f"[jsearch] {query}: HTTP {resp.status_code}")
                continue
            data = resp.json()
            for job in data.get("data", []) or data.get("jobs", []):
                loc = _clean_text(job.get("job_location") or job.get("location") or "")
                results.append({
                    "source_job_id": str(job.get("job_id") or job.get("job_apply_link", "")),
                    "title": _clean_text(job.get("job_title") or ""),
                    "company": _clean_text(job.get("employer_name") or job.get("company_name") or ""),
                    "location": loc,
                    "remote": bool(job.get("job_is_remote")) or _is_remote(loc, ""),
                    "description": _clean_text(job.get("job_description") or "")[:6000],
                    "url": _normalize_url(job.get("job_apply_link") or ""),
                    "salary_min": job.get("job_min_salary"),
                    "salary_max": job.get("job_max_salary"),
                    "date_posted": _safe_parse_date(job.get("job_posting_date")),
                    "job_type": job.get("job_employment_type"),
                    "skills": None,
                    "source_site": "jsearch",
                })
        except Exception as exc:
            print(f"[jsearch] {source['source_name']} query failed: {search_term}: {exc}")
    return results


def _discover_usajobs(source: dict) -> list[dict]:
    """USAJOBS API — US federal jobs, no auth required (API key recommended).

    https://www.usajobs.gov/Developer/api/docs/
    """
    queries = source.get("config", {}).get("queries", [])
    if not queries:
        return []

    results: list[dict] = []
    headers = {
        "User-Agent": settings.user_agent,
        "Authorization-Type": "google",
    }
    if settings.usajobs_api_key:
        headers["Authorization"] = f"Bearer {settings.usajobs_api_key}"

    api_url = "https://jobs.gov/api/search"

    for q in queries:
        keyword = q.get("search_term", "")
        location = q.get("location", "")
        if not keyword:
            continue
        params = {
            "Keyword": keyword,
            "Location": location or "United States",
            "ResultsPerPage": source.get("config", {}).get("results_wanted", 20),
            "Page": 1,
        }
        try:
            resp = requests.get(api_url, params=params, headers=headers, timeout=30)
            if resp.status_code != 200:
                print(f"[usajobs] {keyword}: HTTP {resp.status_code}")
                continue
            data = resp.json()
            search_results = data.get("SearchResult", {}).get("SearchResultItems", [])
            for item in search_results:
                job = item.get("MatchedObjectDescriptor", {})
                loc = _clean_text(job.get("positionLocations", {}).get("Location", [{}])[0].get("City", "") or job.get("location", ""))
                if not loc:
                    loc = _clean_text(job.get("location", ""))
                results.append({
                    "source_job_id": str(job.get("PositionID") or job.get("PositionURI", "")),
                    "title": _clean_text(job.get("PositionTitle") or ""),
                    "company": _clean_text(job.get("OrganizationName") or "US Federal Government"),
                    "location": loc,
                    "remote": _is_remote(loc, job.get("PositionTitle", "")),
                    "description": _clean_text(job.get("Description") or "")[:6000],
                    "url": _normalize_url(job.get("PositionURI") or ""),
                    "salary_min": None,
                    "salary_max": None,
                    "date_posted": _safe_parse_date(job.get("datePosted")),
                    "job_type": job.get("timeTypeDescription") or job.get("jobCategory", [{}])[0].get("Text", "") if isinstance(job.get("jobCategory"), list) else None,
                    "skills": None,
                    "source_site": "usajobs",
                })
        except Exception as exc:
            print(f"[usajobs] {source['source_name']} query failed: {keyword}: {exc}")
    return results


def _discover_remotive_feed_old(source: dict) -> list[dict]:
    """Parse general RSS/Atom feeds (fallback)."""
    return _discover_rss(source)


def _discover_jobscraper(source: dict) -> list[dict]:
    """python-job-scraper alternative for Indian platforms: Internshala, Shine, Apna, Naukri, Foundit.

    Uses its own scrape_jobs API. Optional lightweight extension of JobSpy.
    https://github.com/seeedstack/job-scraper
    """
    queries = source.get("config", {}).get("queries", [])
    adapter = source.get("adapter", "jobscraper")
    site_map = {
        "internshala": ["internshala"],
        "shine": ["shine"],
        "apna": ["apna"],
        "naukri": ["naukri"],
        "foundit": ["foundit"],
        "indeed": ["indeed"],
        "glassdoor": ["glassdoor"],
        "linkedin": ["linkedin"],
        "upwork": ["upwork"],
    }
    sites = site_map.get(adapter, ["indeed", "glassdoor", "linkedin"])

    results = []
    for q in queries:
        search_term = q.get("search_term")
        location = q.get("location", "India")
        if not search_term:
            continue
        try:
            from jobscraper import scrape_jobs as js_scrape_jobs
            df = js_scrape_jobs(
                site_name=sites,
                search_term=search_term,
                location=location,
                results_wanted=source.get("config", {}).get("results_wanted", 20),
                hours_old=source.get("config", {}).get("hours_old", 48),
            )
            if df is not None and len(df) > 0:
                for record in df.to_dict("records"):
                    norm = {
                        "source_job_id": str(record.get("id") or record.get("job_url") or ""),
                        "title": _clean_text(record.get("title") or ""),
                        "company": _clean_text(record.get("company") or record.get("company_name") or source.get("source_name", "")),
                        "location": _clean_text(record.get("location") or ""),
                        "remote": bool(record.get("is_remote")) or _is_remote(_clean_text(record.get("location") or ""), record.get("title") or ""),
                        "description": _clean_text(record.get("description") or "")[:6000],
                        "url": _normalize_url(record.get("job_url") or record.get("job_url_direct") or ""),
                        "salary_min": record.get("min_amount") or record.get("salary_min"),
                        "salary_max": record.get("max_amount") or record.get("salary_max"),
                        "date_posted": _safe_parse_date(record.get("date_posted")),
                        "job_type": record.get("job_type"),
                        "skills": _clean_text(record.get("skills") or "") or None,
                        "source_site": record.get("site") or adapter,
                    }
                    results.append(norm)
        except ImportError:
            print("[jobscraper] python-job-scraper not installed — skipping")
            break
        except Exception as exc:
            print(f"[jobscraper] {source['source_name']} query failed: {search_term} / {location}: {exc}")
    return results


def _clean_html_to_text(html: str) -> str:
    return _clean_text(html)


def _is_remote(location: str, title: str = "") -> bool:
    text = f"{location} {title}".lower()
    return any(token in text for token in ["remote", "anywhere", "wfh", "work from home", "distributed"])


def _safe_parse_date(value: Any) -> str | None:
    if not value:
        return None
    if isinstance(value, str):
        # ISO format
        m = re.match(r"(\d{4}-\d{2}-\d{2})", value)
        if m:
            return m.group(1)
    return None


# --------------- core discovery ---------------

def run_source(source: dict) -> dict:
    """Execute one source and return stats. Each call creates its own DB session."""
    source_id = source.get("id") or source.get("company", "unknown").lower().replace(" ", "-").replace("/", "-")[:50]
    source_name = source.get("source_name", source.get("company", "unknown"))
    adapter = source.get("adapter", "").lower() or source.get("kind", "").lower()
    started = datetime.utcnow()

    db = SessionLocal()
    try:
        # Upsert source record
        db_source = db.query(JobSource).filter(JobSource.id == source_id).first()
        if not db_source:
            db_source = JobSource(id=source_id, source_name=source_name)
            db.add(db_source)
            db.commit()
            db.refresh(db_source)

        run = SourceRun(
            id=uuid.uuid4().hex,
            source_id=source_id,
            started_at=started,
            status="running",
            queries_run=source.get("config", {}).get("queries", []),
        )
        db.add(run)
        db.commit()

        try:
            if adapter in ("greenhouse", "lever", "ashby"):
                items = _discover_ats(source)
            elif adapter in ("rss",):
                items = _discover_rss(source)
            elif adapter in ("adzuna",):
                items = _discover_adzuna(source)
            elif adapter in ("remotive",):
                items = _discover_remotive(source)
            elif adapter in ("jsearch",):
                items = _discover_jsearch(source)
            elif adapter in ("usajobs",):
                items = _discover_usajobs(source)
            elif adapter in ("remoteok",):
                items = _discover_remoteok(source)
            elif adapter in ("himalayas",):
                items = _discover_himalayas(source)
            elif adapter in ("jobscraper",):
                items = _discover_jobscraper(source)
            elif adapter in ("jobspy", "linkedin", "indeed", "naukri", "glassdoor", "zip_recruiter", "google", "bayt", "bdjobs", "ziprecruiter"):
                items = _discover_jobspy(source)
            else:
                items = []

            jobs_found = len(items)
            new_jobs = 0
            duplicates = 0
            failed = 0

            profile = db.query(Profile).first()

            for item in items:
                try:
                    url = _normalize_url(item.get("url", ""))
                    if not url and not item.get("source_job_id"):
                        failed += 1
                        continue

                    existing = None
                    if url:
                        existing = db.query(Job).filter(Job.url == url).first()

                    if not existing:
                        existing = db.query(Job).filter(
                            Job.title == item.get("title"),
                            Job.company == item.get("company"),
                        ).first()

                    if existing:
                        duplicates += 1
                        existing_mapping = db.query(JobSourceMapping).filter(
                            JobSourceMapping.job_id == existing.id,
                            JobSourceMapping.source_id == source_id,
                        ).first()
                        if not existing_mapping:
                            mapping = JobSourceMapping(
                                id=uuid.uuid4().hex,
                                job_id=existing.id,
                                source_id=source_id,
                                source_job_id=item.get("source_job_id"),
                                source_url=url,
                            )
                            db.add(mapping)
                        continue

                    job = Job(
                        id=uuid.uuid4().hex,
                        title=item.get("title") or "Untitled",
                        company=item.get("company"),
                        location=item.get("location"),
                        remote=item.get("remote"),
                        salary_min=item.get("salary_min"),
                        salary_max=item.get("salary_max"),
                        description=item.get("description"),
                        url=url,
                        source=f"{source.get('adapter', '')}:{source_name}",
                        status="discovered",
                    )
                    db.add(job)
                    db.flush()

                    mapping = JobSourceMapping(
                        id=uuid.uuid4().hex,
                        job_id=job.id,
                        source_id=source_id,
                        source_job_id=item.get("source_job_id"),
                        source_url=url,
                    )
                    db.add(mapping)

                    if profile:
                        try:
                            result = score_job_against_profile(profile, job)
                            job.match_score = result.score
                            job.match_evidence = result.evidence
                        except Exception:
                            pass

                    new_jobs += 1

                except Exception as exc:
                    failed += 1
                    print(f"[run_source] item error: {exc}")

            db.commit()

            db_source.last_run = datetime.utcnow()
            db_source.last_success = datetime.utcnow()
            db_source.jobs_found += jobs_found
            db_source.new_jobs += new_jobs
            db_source.duplicates += duplicates
            db_source.failed_jobs += failed
            db_source.health_status = "HEALTHY"
            db_source.error_message = None

            run.finished_at = datetime.utcnow()
            run.duration_seconds = int((run.finished_at - started).total_seconds())
            run.jobs_found = jobs_found
            run.new_jobs = new_jobs
            run.duplicates = duplicates
            run.failed_jobs = failed
            run.status = "success"
            db.commit()

            return {
                "source": source_name,
                "jobs_found": jobs_found,
                "new_jobs": new_jobs,
                "duplicates": duplicates,
                "failed": failed,
                "status": "success",
            }

        except Exception as exc:
            db_source.last_failure = datetime.utcnow()
            db_source.health_status = "BLOCKED"
            db_source.error_message = str(exc)[:500]
            run.finished_at = datetime.utcnow()
            run.duration_seconds = int((run.finished_at - started).total_seconds())
            run.status = "failed"
            run.error_message = str(exc)[:500]
            db.commit()
            return {
                "source": source_name,
                "jobs_found": 0,
                "new_jobs": 0,
                "duplicates": 0,
                "failed": 0,
                "status": "failed",
                "error": str(exc)[:100],
            }
    finally:
        db.close()


def discover(sources: list[dict], max_workers: int = 4) -> dict:
    """Run multiple sources in parallel with deduplication."""
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(run_source, s): s for s in sources}
        for future in concurrent.futures.as_completed(futures):
            try:
                res = future.result()
                results.append(res)
            except Exception as exc:
                s = futures[future]
                results.append({
                    "source": s.get("source_name", s.get("company", "unknown")),
                    "status": "failed",
                    "error": str(exc)[:100],
                })
    total = sum(r.get("jobs_found", 0) for r in results)
    new = sum(r.get("new_jobs", 0) for r in results)
    dups = sum(r.get("duplicates", 0) for r in results)
    failed = sum(r.get("failed", 0) for r in results)
    return {
        "imported": new,
        "duplicates": dups,
        "failed": failed,
        "total_found": total,
        "sources": results,
    }


if __name__ == "__main__":
    # Quick test with NSita queries
    db = SessionLocal()
    try:
        sources = db.query(JobSource).filter(JobSource.enabled == True).all()
        print(f"Testing with {len(sources)} enabled sources")
        for s in sources[:3]:
            print(f"  - {s.source_name}: {s.adapter}")
            if s.adapter == "jobspy":
                print(f"    queries: {s.config.get('queries', [])}")
    finally:
        db.close()

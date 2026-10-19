# Job Hunter OS — Integration Research

Research completed: 2026-10-03
Scope: select legitimate, maintainable integrations for local-first job automation.

---

## 1. n8n Community Edition

**Docs:** https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.httprequest
**Webhook:** https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.webhook

**Findings:**
- **Free / Commercial:** Community Edition is self-hosted, free, open-source (fair-code).
- **Auth:** Webhooks support None, Basic, Header, JWT. Production webhooks require publishing the workflow.
- **Rate limits:** No hard-coded rate limit on webhook ingestion, but max payload is 16MB by default (configurable via `N8N_PAYLOAD_SIZE_MAX`).
- **India:** Works locally; no geo restriction on self-hosted instances.
- **Commercial use:** Fair-code (n8n License); can be used commercially, but SaaS-hosting n8n as a service requires a commercial license.
- **Automated submission:** n8n is a workflow orchestrator only. It does not itself submit job applications; it can call our backend API or a permitted ATS API.
- **Alternatives:** Huginn (Ruby), Node-RED (JS), Temporal (Python/Go). n8n is the best fit because of its HTTP Request node, webhook triggers, and visual workflow editor.

**Decision:** Use n8n CE for scheduled discovery, matching, and notification workflows. Keep the core app functional without n8n.

---

## 2. Ollama — Local AI

**Docs:** https://docs.ollama.com/capabilities/structured-outputs
**API:** https://github.com/ollama/ollama/blob/97323d1c/docs/api.md

**Findings:**
- **Free:** 100% free, local, open-source (MIT).
- **Auth:** None for localhost. Remote access can be locked behind `OLLAMA_ORIGINS`.
- **Rate limits:** None locally. Throughput depends on GPU/CPU.
- **India:** Works locally. No geo restriction.
- **Commercial use:** MIT license. Permitted.
- **Structured JSON:** Supported via `format` parameter (JSON schema or `"json"`). Works with `llama3.1`, `llama3.2`, `mistral`, `gemma2`, `phi3`, etc. Cloud does NOT support structured outputs; local only.
- **Model size:** `llama3.1:8b` (~4.7GB VRAM) is a good balance for a laptop. `phi3:mini` (~2.3GB) for low-resource machines.

**Decision:** Ollama is the default AI provider. Support OpenAI-compatible API as an optional external provider with explicit user consent.

---

## 3. Greenhouse Job Board API

**Docs:** https://developers.greenhouse.io/job-board.html
**GitHub:** https://github.com/grnhse/greenhouse-api-docs

**Findings:**
- **Free:** Public GET endpoints are completely free and unauthenticated.
- **Auth:** GET requires no auth. POST (application submission) requires Base64-encoded API key.
- **Rate limits:** No published rate limit for GETs. Reasonable polling (every 6h) is safe.
- **India:** No geo restriction.
- **Commercial use:** Permitted. Greenhouse encourages building custom career pages.
- **Automated submission:** Allowed only with the company's API key (for applying to *their* jobs, not as a candidate). **Candidate-side automated submission is NOT supported.** The API docs say: "we would encourage customers to make use of the Embedded Job Application... Building your own form can introduce a number of challenges."
- **Fields:** `?content=true` returns full description. `?questions=true` returns application form fields.

**Decision:** Use Greenhouse for job discovery (GET) and form inspection (GET with `?questions=true`). Do NOT auto-submit via Greenhouse API. Use browser automation for assisted/manual submission only.

---

## 4. Lever Postings API

**Docs:** https://github.com/lever/postings-api
**OpenAPI:** https://raw.githubusercontent.com/api-evangelist/lever-co/refs/heads/main/openapi/lever-co-postings-api-openapi.yml

**Findings:**
- **Free:** Public GET endpoints are free and unauthenticated.
- **Auth:** GET requires no auth. POST (application creation) requires a Super Admin API key.
- **Rate limits:** POST is rate-limited to 2 req/s per account. GET has no published limit.
- **India:** No geo restriction.
- **Commercial use:** Permitted.
- **Automated submission:** Requires company-side API key. **Not available for candidate-side automation.**
- **Fields:** JSON mode supports `?mode=json` or `Accept: application/json`. Filter by `location`, `commitment`, `team`, `department`, `level`.

**Decision:** Use Lever for job discovery and form field inspection. Do not auto-submit.

---

## 5. RSS Job Feeds

**Sources verified working:**
| Feed | URL | License |
|------|-----|---------|
| We Work Remotely (all) | `https://weworkremotely.com/remote-jobs.rss` | Free, attribution requested |
| We Work Remotely (programming) | `https://weworkremotely.com/categories/remote-programming-jobs.rss` | Free |
| Remotive | `https://remotive.com/remote-jobs/feed` | Free |
| Himalayas | `https://himalayas.app/jobs/rss` | Free |
| Jobicy | `https://jobicy.com/jobs/feed` | Free, 7-day window |
| Hacker News Who is Hiring | `https://hnrss.org/whoishiring/jobs` | Free |
| WordPress Jobs | `https://jobs.wordpress.net/feed/` | Free |

**Findings:**
- **Free:** All free, no authentication required.
- **Rate limits:** Poll no more than once per hour for Jobicy. Others are more generous but respect ` crawl-delay`.
- **India:** No geo restriction.
- **Commercial use:** Permitted for personal/internal use. Check individual terms if redistributing.
- **Automated submission:** Not applicable; these are listing feeds only.

**Decision:** Include We Work Remotely, Remotive, Himalayas, and Jobicy as default RSS sources.

---

## 6. Playwright Browser Automation

**Docs:** https://playwright.dev/python/docs/intro

**Findings:**
- **Free:** Open-source (Apache 2.0).
- **Auth:** N/A.
- **Rate limits:** N/A for local execution.
- **India:** Works locally.
- **Commercial use:** Permitted.
- **CAPTCHA:** Playwright cannot bypass CAPTCHA. Sites that require CAPTCHA after form fill must fall back to manual.
- **Anti-bot:** Playwright is detectable. `stealth` plugins exist but are not officially supported. Use only on permitted sites.

**Decision:** Use Playwright for assisted form filling on supported sites. Implement site-specific adapters. Never bypass CAPTCHA or auth walls.

---

## 7. Google Sheets / Gmail

**Docs:** https://developers.google.com/workspace
**Gmail API:** https://developers.google.com/gmail/api
**Sheets API:** https://developers.google.com/sheets/api

**Findings:**
- **Free:** Both have free tiers (500MB Sheets, Gmail with Google account).
- **Auth:** OAuth 2.0 required. Complex setup.
- **India:** Supported.
- **Commercial use:** Permitted under Google Workspace terms.
- **Automation:** Permitted for personal use. Bulk unsolicited email violates ToS.

**Decision:** Defer Gmail/Sheets integration to P2. Use local SQLite for primary storage. If added later, require explicit OAuth consent.

---

## 8. Resume Parsing

**Candidates evaluated:**
| Library | License | Formats | OCR | Notes |
|---------|---------|---------|-----|-------|
| `pdfplumber` | MIT | PDF | No | Text-based PDFs only. Fast, lightweight. |
| `pymupdf` (fitz) | AGPL | PDF, images | Yes (Tesseract) | AGPL may be restrictive for some use cases. |
| `ai-resume-parser` | MIT | PDF, DOCX, TXT, images | Yes (Tesseract) | Requires LLM API key (OpenAI/Anthropic/Ollama). Good for structured extraction but heavy. |
| `resumeminer` | MIT | PDF | No | Regex-based. Lightweight but lower accuracy. |
| `leverparser` | MIT | PDF, DOCX, TXT | No | Designed for Lever ATS compatibility. 95%+ contact info accuracy. |
| `python-docx` | MIT | DOCX | N/A | Read/create DOCX. Not a parser. |

**Decision:**
- **Parsing:** `pdfplumber` for PDF text extraction + regex heuristics for contact/skills/experience. Add `python-docx` for DOCX.
- **DOCX generation:** `python-docx` (create tailored resumes).
- **PDF generation:** `reportlab` or `weasyprint` for PDF export. Start with `python-docx` output; add PDF later if needed.

---

## 9. Document Generation

**Libraries:**
| Library | License | Notes |
|---------|---------|-------|
| `python-docx` | MIT | Create/edit DOCX. Industry standard. |
| `reportlab` | BSD | PDF generation. Mature. |
| `weasyprint` | MIT | HTML → PDF. Easier templating. |
| `pypandoc` | MIT | Pandoc wrapper. Broad format support. |

**Decision:** Use `python-docx` for DOCX generation. Add `reportlab` for PDF export in a later iteration.

---

## 10. Platform Automation Policies

| Platform | Automated Discovery | Automated Application | API Available | Policy Notes |
|----------|---------------------|----------------------|---------------|--------------|
| Greenhouse | ✅ Public GET | ❌ Candidate-side not supported | ✅ Job Board API | Use for discovery + form inspection only |
| Lever | ✅ Public GET | ❌ Candidate-side not supported | ✅ Postings API | Use for discovery + form inspection only |
| LinkedIn | ❌ ToS prohibits scraping | ❌ Prohibited | ✅ Some (but restricted) | Use manual/assisted mode only |
| Indeed | ❌ Blocks automation | ❌ Prohibited | ❌ No public API | Use manual/assisted mode only |
| Naukri | ❌ Blocks automation | ❌ Unknown | ❌ No public API | Use manual/assisted mode only |
| Workday | ❌ Anti-bot strong | ❌ Not supported | ❌ No public API | Use manual/assisted mode only |

---

## 11. Job Scraping Libraries & Aggregation APIs (JobSpy Alternatives)

### python-jobspy (JobSpy)

- **Repo:** https://github.com/speedyapply/JobSpy
- **License:** MIT
- **Stars:** 1.5k+ / 800+ forks
- **Sources:** LinkedIn, Indeed, Glassdoor, Google, ZipRecruiter, Bayt, Naukri, BDJobs
- **Auth:** None (proxies optional for bypassing blocks)
- **Free:** Yes, completely free and open-source
- **Integration status:** Already integrated as `JobSpy` adapter in `multi_discovery.py`
- **Rate limits:** LinkedIn ~10 pages per IP; Indeed no rate limit; Glassdoor ~30 req/IP
- **Risk:** Scraping job boards may violate ToS; use with proxies and delays

### python-job-scraper (seeedstack)

- **Repo:** https://github.com/seeedstack/job-scraper
- **License:** MIT
- **Released:** April 2026 (actively maintained)
- **Sources:** Indeed, Glassdoor, LinkedIn, Naukri, Foundit, Shine, Internshala, Upwork, Apna
- **Auth:** None (cookie-based for richer LinkedIn data)
- **Free:** Yes
- **Python:** Requires 3.13+
- **Integration status:** Added as optional `jobscraper` adapter; gracefully degrades if not installed

### Adzuna API

- **Docs:** https://developer.adzuna.com/overview
- **License:** Free commercial API
- **Auth:** Free registration for app_id + app_key
- **Free tier:** 250 requests/day
- **Coverage:** Global (US, UK, India, Germany, Singapore, etc.)
- **Integration status:** Integrated as `adzuna` adapter
- **Rate limits:** No explicit limit; 250 req/day on free tier

### JSearch (RapidAPI)

- **Docs:** https://rapidapi.com/jsearch-api-api/
- **License:** Freemium via RapidAPI
- **Auth:** API key via RapidAPI
- **Free tier:** 50 requests/month
- **Sources:** Google, LinkedIn, Indeed, Glassdoor, ZipRecruiter, and more
- **Integration status:** Integrated as `jsearch` adapter
- **Rate limits:** Free tier = 50 req/month; paid tiers available

### Remotive API

- **Docs:** https://remotive.com/remote-jobs/api
- **License:** Free, requires attribution
- **Auth:** None required (optional premium API key)
- **Coverage:** Remote-only jobs globally
- **Integration status:** Integrated as `remotive` adapter (API + RSS fallback)
- **Rate limits:** 6-hour cache recommended; requires attribution link
- **Terms:** Do not submit to third-party job sites; link back to Remotive

### USAJOBS API

- **Docs:** https://www.usajobs.gov/developers/
- **License:** Free, US federal government
- **Auth:** No auth required (API key recommended for higher limits)
- **Coverage:** US federal jobs only
- **Integration status:** Integrated as `usajobs` adapter
- **Rate limits:** 20,000 requests/day without key; 100,000 with key

### Decision Matrix

| Tool | Free | Auth Required | Global | India Support | Scraping | Legitimate |
|------|------|---------------|--------|---------------|----------|------------|
| JobSpy | ✅ | ❌ | ✅ | ✅ | ✅ | ⚠️ ToS risk |
| python-job-scraper | ✅ | ❌ | ✅ | ✅ (Apna, Shine, Internshala) | ✅ | ⚠️ ToS risk |
| Adzuna API | ✅ | ✅ (free) | ✅ | ✅ | ❌ | ✅ |
| JSearch API | ✅ tier | ✅ | ✅ | ✅ | ❌ | ✅ |
| Remotive API | ✅ | ❌ | ✅ (remote) | ✅ | ❌ | ✅ |
| RemoteOK API | ✅ | ❌ | ✅ (remote) | ✅ | ❌ | ✅ |
| Himalayas API | ✅ | ❌ | ✅ (remote) | ✅ | ❌ | ✅ |
| USAJOBS API | ✅ | ❌ (recommended) | ❌ (US only) | ❌ | ❌ | ✅ |

**Recommendation:** Use JobSpy as the primary scraper for major boards, supplemented by Adzuna and JSearch APIs as lower-risk alternatives. Remotive API covers remote-only. USAJOBS covers US federal roles. **RemoteOK API** and **Himalayas API** added as additional free no-auth sources. All are optional — the app works with any subset.

**Decision:** Auto-apply engine supports:
1. **Manual mode** — all platforms (find, match, prepare, user submits).
2. **Approval mode** — fill form via Playwright, user reviews, user submits.
3. **Autonomous mode** — only on platforms with explicit, documented, permitted APIs AND where the user has their own API key. Currently this means **no platform supports full autonomous candidate-side submission via API**. Autonomous mode falls back to assisted Playwright on permitted sites.

---

## Selected Technology Stack

| Component | Choice | Reason |
|-----------|--------|--------|
| Backend | FastAPI + SQLAlchemy + SQLite | Existing, working, local-first |
| Frontend | React + TypeScript + Tailwind + Zustand | Existing, polished |
| AI | Ollama (local) + optional OpenAI-compatible | Free, private, structured output |
| Job discovery | Greenhouse GET, Lever GET, RSS (WWR, Remotive, Himalayas, Jobicy), Adzuna API, JSearch API, USAJOBS API | Free, legitimate, no auth or free-tier APIs |
| Resume parsing | pdfplumber + python-docx + regex | Free, lightweight, no LLM dependency |
| Document generation | python-docx + reportlab | Free, standard |
| Browser automation | Playwright | Industry standard, site adapters |
| Workflows | n8n CE | Visual, local, free |
| Testing | pytest + CDP e2e harness | Existing, verified |

---

## Known Limitations

1. **No automated candidate submission via API** — Greenhouse and Lever only allow company-side application submission via API. Candidate-side automation requires browser interaction.
2. **CAPTCHA** — Playwright cannot bypass CAPTCHA. Sites that trigger CAPTCHA after form interaction require manual completion.
3. **LinkedIn/Indeed/Naukri/Workday** — No legitimate automated discovery or application method available.
4. **Ollama structured output** — Only works with local models. Cloud models (Ollama Cloud, OpenAI) do not support `format` parameter.
5. **Job data freshness** — RSS feeds and public APIs may have 3-7 day delays. Real-time discovery requires company-specific APIs.

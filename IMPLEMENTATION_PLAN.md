# Job Hunter OS — Implementation Plan

Audit completed: 2026-10-03
Repository: `/Users/macbook/Desktop/SUMIT/job-hunter-os`

---

## Current State

### Working
- Frontend: 8 pages, polished dark UI, 36/36 interaction checks passing
- Backend: FastAPI + SQLAlchemy + SQLite, 46 tests green
- Database: `Profile`, `Resume`, `Job`, `Application`, `AgentLog`, `WorkflowConfig` models
- Job discovery: Greenhouse, Lever, Ashby, RSS, JSON adapters — 1944 jobs discovered live
- AI matching: Token-based weighted scoring with relevance gate
- Application prep: Cover letters and follow-up messages
- E2E: CDP-based test harness, 25/25 checks

### Missing / Incomplete
- No `AutoApplySettings` model or endpoints
- No `TailoredResume` or `CoverLetterVersion` models
- No `ApplicationAttempt` or approval queue
- No Ollama integration (service + endpoints)
- No resume parsing (pdfplumber/python-docx not wired)
- No CV/cover letter generation endpoints
- No Playwright browser automation
- No n8n workflow JSON files
- Frontend `Apply` page is legacy; no Auto Apply dashboard
- Some frontend pages use mock data as fallback but are not connected to real APIs

---

## Phase 1: Foundation (P0 — Must Work First)

### 1.1 Database Models
Add tables:
- `auto_apply_settings` — user's auto-apply configuration (enabled, min_score, max_per_day, sources, mode, emergency_stop)
- `tailored_resumes` — per-job resume versions with original + generated content
- `cover_letter_versions` — per-job cover letter versions
- `application_attempts` — every execution (found → matched → prepared → filled → submitted/result)
- `form_answers` — reusable answers to screening questions
- `approval_records` — approval queue entries with approver + decision
- `browser_logs` — Playwright execution logs per attempt

### 1.2 Ollama Service
- `backend/app/services/ollama.py`:
  - `check_connection()` — GET `http://localhost:11434/api/tags`
  - `list_models()` — return available models
  - `chat(model, messages, format?)` — structured JSON output via `format` param
  - `generate(model, prompt, format?)` — for single-turn tasks
  - Timeout handling (default 120s), graceful degradation

### 1.3 Resume Parsing Service
- `backend/app/services/resume_parser.py`:
  - `parse_pdf(file_path)` — pdfplumber text extraction
  - `parse_docx(file_path)` — python-docx text extraction
  - `extract_fields(text)` — regex-based: name, email, phone, skills, experience, education
  - Return structured dict; never overwrite original file

### 1.4 Document Generation Service
- `backend/app/services/documents.py`:
  - `generate_resume_docx(base_resume, job_description, profile)` — python-docx
  - `generate_cover_letter_docx(profile, job, match_result)` — python-docx
  - `docx_to_bytes(doc)` — serialize for download
  - Store generated files in `UPLOAD_DIR/`

### 1.5 AI Integration Endpoints
- `POST /api/ai/test-connection` — verify Ollama is reachable
- `GET /api/ai/models` — list available models
- `POST /api/ai/match-job` — score a job against profile (structured JSON)
- `POST /api/ai/analyze-resume` — extract fields from uploaded resume
- `POST /api/ai/generate-cover-letter` — generate tailored letter
- `POST /api/ai/generate-resume` — generate tailored resume suggestions

---

## Phase 2: Auto-Apply Engine (P0)

### 2.1 Backend
- `AutoApplySettings` CRUD endpoints
- `ApplicationAttempt` creation and status tracking
- `ApprovalRecord` queue endpoints (list, approve, reject)
- `POST /api/auto-apply/start` — begin execution loop
- `POST /api/auto-apply/stop` — emergency stop
- `GET /api/auto-apply/status` — current execution state
- `GET /api/auto-apply/history` — past attempts

### 2.2 Browser Automation (Playwright)
- `backend/app/services/browser.py`:
  - `launch_browser(headless=True)` — Playwright Chromium
  - `fill_greenhouse_form(job, profile, resume_path)` — site adapter
  - `fill_lever_form(job, profile, resume_path)` — site adapter
  - `detect_form_fields(url)` — inspect application form
  - `submit_application(url, data)` — ONLY in approval/autonomous mode with explicit config
  - `close_browser()` — cleanup

### 2.3 Frontend
- `/auto-apply` page:
  - Enable/disable toggle
  - Start/Pause/Emergency stop buttons
  - Min match score, max per day, preferred titles/locations/salary
  - CV selection dropdown
  - Cover letter toggle
  - Mode selector: Manual / Approval Required / Autonomous
  - Live execution timeline (job found → matched → prepared → filled → result)
  - Application history table
  - Approval queue with Approve/Reject buttons

---

## Phase 3: Application Tracking (P0)

### 3.1 Extend Existing Models
- Add `application_attempts` FK to `Application`
- Add `approval_status` to `Application` (pending / approved / rejected)
- Add `submission_confirmed` boolean to `Application`

### 3.2 Endpoints
- `PATCH /api/applications/{id}/status` — update stage with history
- `POST /api/applications/{id}/approve` — approve for submission
- `POST /api/applications/{id}/reject` — reject application
- `GET /api/applications/history/{id}` — full timeline

---

## Phase 4: n8n Integration (P1)

### 4.1 Workflow JSON Files
Create importable workflows:
- `n8n/workflows/scheduled-discovery.json`
- `n8n/workflows/job-matching.json`
- `n8n/workflows/cover-letter-generation.json`
- `n8n/workflows/approval-notification.json`
- `n8n/workflows/follow-up-reminders.json`
- `n8n/workflows/daily-summary.json`

### 4.2 Webhook Endpoints
- `POST /api/n8n/webhook/discovery` — receive new jobs from n8n
- `POST /api/n8n/webhook/matching` — receive match results
- `POST /api/n8n/webhook/approval` — approval notification callback

### 4.3 Connectivity
- Test n8n connection from frontend
- Show n8n status in system health
- Graceful degradation when n8n is offline

---

## Phase 5: Frontend Connectivity (P0)

### 5.1 Real API Integration
- Connect Overview dashboard to `/api/dashboard/summary` and `/api/jobs/`
- Connect Discover Jobs to real search/filter/sort
- Connect Applications to real CRUD
- Connect Resume Studio to upload + parse + generate
- Connect Settings to profile save + AI config
- Remove all mock data fallbacks that pretend to be live data

### 5.2 Auto Apply Page
- Build `/auto-apply` route and page
- Wire all controls to new backend endpoints
- Live status polling every 5s during execution

---

## Phase 6: Testing (P0-P1)

### 6.1 Backend Tests
- Resume parsing tests (sample PDF/DOCX)
- Ollama service tests (mock HTTP)
- AI output validation tests
- Auto-apply execution state machine tests
- Duplicate prevention tests
- Approval workflow tests

### 6.2 Frontend Tests
- TypeScript checks (already clean)
- Production build verification
- E2E: auto-apply page controls
- E2E: approval queue flow

### 6.3 Integration Tests
- End-to-end: upload resume → parse → match job → generate cover letter → prepare application
- End-to-end: discovery → match → auto-apply execution → approval → status update

---

## Phase 7: Deployment (P1)

### 7.1 Docker Compose
- Add Ollama service
- Add n8n service (already present, verify config)
- Persistent volumes for data, n8n, Ollama models
- Health checks for all services
- Startup order: PostgreSQL (if added) → backend → n8n → Ollama

### 7.2 Environment
- `.env.example` with all required vars
- `docker-compose.yml` with all services
- `docker-compose.dev.yml` for development with hot reload

### 7.3 Documentation
- README: setup, prerequisites, startup commands
- LIMITATIONS.md: what works, what requires credentials, what is manual-only
- N8N_SETUP.md: workflow import instructions

---

## Execution Order

1. **Models + migrations** (enables all subsequent features)
2. **Ollama service** (required for AI features)
3. **Resume parsing** (required for CV generation)
4. **Document generation** (required for cover letters + tailored CVs)
5. **AI endpoints** (required for matching + generation)
6. **Auto-apply backend** (settings + execution)
7. **Auto-apply frontend** (user interface)
8. **Application tracking extensions** (approval queue)
9. **n8n workflows** (automation)
10. **Frontend connectivity** (replace mocks with real APIs)
11. **Tests** (verify everything)
12. **Deployment** (Docker + docs)

---

## Acceptance Criteria

### P0 (MVP)
- [ ] Backend starts, database initializes with new tables
- [ ] Profile save/load works
- [ ] Resume upload → parse → structured fields stored
- [ ] At least one job source returns real jobs (Greenhouse or RSS)
- [ ] Jobs appear in frontend Discover page
- [ ] AI matching returns structured JSON with score + evidence
- [ ] Cover letter generation produces text from profile + job
- [ ] Application tracking works (create, update stage, history)
- [ ] Approval queue prevents accidental submission
- [ ] Auto-apply page has working enable/disable/stop controls
- [ ] Emergency stop immediately halts execution
- [ ] All existing tests pass (46+)
- [ ] Frontend build clean

### P1
- [ ] n8n workflows importable and functional
- [ ] Scheduled discovery runs without manual trigger
- [ ] DOCX export works for resumes and cover letters
- [ ] Email monitoring works (if credentials provided)
- [ ] Analytics shows real database data

### P2
- [ ] Browser automation fills forms on supported sites
- [ ] More job sources integrated
- [ ] PDF resume generation
- [ ] Google Sheets export
- [ ] Advanced analytics

---

## Completed: Auto-Apply Pipeline + Additional Job Sources

**Status:** All P0 criteria met. Pipeline is functional and tested.

### What was built

1. **Additional job discovery sources** (beyond existing JobSpy + RSS + ATS):
   - Adzuna API adapter (free tier, global)
   - Remotive API adapter (free, remote-only, attribution required)
   - JSearch API adapter (RapidAPI free tier)
   - USAJOBS API adapter (free, US federal)
   - python-job-scraper adapter (optional, for Indian platforms)

2. **Full auto-apply workflow** (`app/services/auto_apply_workflow.py`):
   - `run_discovery_step()` — discovers jobs from all 26 configured sources
   - `run_matching_step()` — scores jobs against profile using deterministic matching
   - `run_preparation_step()` — generates cover letter + form answers, creates approval records
   - `run_auto_apply_pipeline()` — chains all stages in a background thread
   - `get_pending_approvals()` — returns approval queue with full application context
   - `process_approval()` — processes approve/reject decisions

3. **New API endpoints**:
   - `GET /api/auto-apply/queue` — pending approvals with job title, company, match score
   - `POST /api/auto-apply/approvals/{id}/process` — approve/reject with notes
   - `GET /api/auto-apply/stats` — engine stats summary
   - Background thread execution on `POST /api/auto-apply/start`

4. **Frontend updates** (`AutoApply.tsx`):
   - Uses new `/queue` endpoint for richer approval queue (job title, company, match score)
   - Uses `/stats` endpoint for status display
   - Uses `/approvals/{id}/process` for approval decisions
   - Full TypeScript types for `QueuedApproval` and `AutoApplyStats`

5. **Database fix**: `approval_records.attempt_id` made nullable for workflow-driven creation

6. **Tests**: 4 new tests added (16 total, all passing)

### How it works

```
User enables auto-apply → /api/auto-apply/start
  ↓
Background thread: run_auto_apply_pipeline()
  ├─ Stage 1: Discovery (JobSpy + Adzuna + Remotive + JSearch + USAJOBS + RSS + ATS)
  ├─ Stage 2: Matching (score against profile, filter by min_score)
  ├─ Stage 3: Preparation (generate cover letter + form answers)
  └─ Stage 4: Approval queue (pending records for user review)
  
User visits /auto-apply → sees approval queue
  → Approve → status becomes "awaiting_approval" (user submits manually)
  → Reject → status becomes "rejected"
  
In autonomous mode: approved → Playwright submits on supported ATS
```

### Limitations
- In sandbox/no-network: discovery returns 0 jobs (expected)
- With API credentials configured: Adzuna, JSearch, USAJOBS will return real jobs
- Playwright submission is implemented but only used in autonomous mode
- CAPTCHA and login-walled sites require manual completion

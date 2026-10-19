# Job Hunter OS — Implementation Plan

## Overview
Build a local-first, multi-agent job application platform named **Job Hunter OS**.
New project root: `/Users/macbook/Desktop/SUMIT/job-hunter-os/`

## Architecture
- **Frontend**: React 18 + TypeScript + Vite 5 + Tailwind CSS 3 + Lucide React
- **Backend**: FastAPI + SQLAlchemy 2.0 + Alembic + SQLite
- **AI**: Ollama (local, default) + optional OpenAI-compatible endpoint
- **Automation**: n8n Community Edition via Docker Compose
- **Browser**: Playwright for permitted automation only
- **Deployment**: Docker Compose (app + n8n + Ollama optional)
- **Secrets**: Environment variables only, never hardcoded

## Directory Layout
```
job-hunter-os/
  backend/
    app/
      __init__.py
      main.py
      config.py
      database.py
      models/
        user.py
        profile.py
        resume.py
        job.py
        application.py
        workflow.py
        agent_log.py
      schemas/
      routers/
      services/
        ai.py
        matching.py
        parsing.py
        n8n.py
        email.py
      workers/
    alembic/
    tests/
    requirements.txt
    .env.example
  frontend/
    src/
      components/
        layout/
        ui/
      pages/
      hooks/
      services/
      types/
    package.json
    tsconfig.json
    vite.config.ts
    tailwind.config.js
    postcss.config.js
    index.html
  n8n/
    workflows/
    docker-compose.yml
  docker-compose.yml
  .env.example
  README.md
  AGENTS.md
```

## Implementation Phases (MVP)

### Phase 1 — Scaffold & Core
- Create directory structure
- Backend: FastAPI app with CORS, health endpoint, structured logging
- Frontend: Vite + React + TS + Tailwind scaffold
- Docker Compose: app service + n8n service

### Phase 2 — Database & Models
- Normalized SQLite schema via SQLAlchemy 2.0
- Models: User, Profile, Resume, Job, Application, AgentLog, WorkflowConfig
- Alembic migrations
- Seed logic (idempotent) for empty states

### Phase 3 — Core API
- REST endpoints for all CRUD operations
- File upload (PDF/DOCX) with size/type validation
- Pagination, filtering, search
- Error handling + validation

### Phase 4 — Frontend Shell
- Auth-lite (local-only, single user)
- Collapsible sidebar with 8 sections
- Layout components: Sidebar, TopBar, Card, Table, Kanban, Modal, Badge
- Dark theme: graphite + green accent

### Phase 5 — Dashboard
- Real counts from DB (jobs discovered, matching, prepared, submitted, interviews, response rate)
- Recent activity, upcoming follow-ups, agent status
- Charts: daily/weekly trends (no hardcoded stats)

### Phase 6 — Profile Wizard
- Multi-step setup capturing all required fields
- Editable profile with save
- Location, salary, remote preference, skills, etc.

### Phase 7 — Resume Studio
- Upload PDF/DOCX
- Parse with python-docx + pdfplumber
- Editable sections
- Multiple versions
- Factuality safeguard: never invent data

### Phase 8 — Job Discovery
- Pluggable source adapters (LinkedJob, Indeed public pages, RSS, Greenhouse, Lever, career pages)
- CSV import + URL import
- Deduplication
- Search + filters + sort
- Job cards + detail view

### Phase 9 — AI Matching
- Configurable weighted scoring (skills, experience, location, salary, role relevance)
- Explainable match scores with evidence
- User override support
- Local Ollama integration + optional OpenAI

### Phase 10 — Application Tracker
- Kanban + table view
- Stages: Discovered → Shortlisted → Preparing → Awaiting approval → Submitted → Assessment → Interview → Offer → Rejected → Withdrawn
- History, notes, follow-ups
- Bulk actions, CSV export

### Phase 11 — n8n & Agents
- Webhook endpoints between app and n8n
- Docker Compose with n8n
- Importable workflow JSONs for scheduled discovery, dedup, matching, resume prep, approvals, email, follow-ups, daily summary
- Agent execution logs + status + retry

### Phase 12 — Polish & Deploy
- Ollama + OpenAI config in Settings
- Email integration (IMAP/Gmail, user-authorized)
- Analytics charts
- Tests (pytest + vitest for key flows)
- README with Docker startup, troubleshooting, backup
- Verify build + lint + main journeys

## Constraints
- Local-first by default
- No brute-forcing or bypassing protections
- Human approval required before submission by default
- Never invent qualifications or experience
- Respect TOS of target sites
- Use env vars for secrets

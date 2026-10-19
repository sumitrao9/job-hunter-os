# Job Hunter OS

Local-first job application tracker with AI matching, resume studio, and optional n8n automation.
Built for ease of use: clean UI, guided profile setup, real tracking, no fake buttons.

## Quick start

### Backend only
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend only
```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 and the backend at http://localhost:8000.

### Docker Compose
```bash
docker compose up --build
```

App UI: http://localhost:5173
Backend API: http://localhost:8000
n8n: http://localhost:5678

## Notes
- This app stores data locally. No accounts, no cloud sync by default.
- Job discovery uses permitted sources only.
- Human approval is required before submitting applications.

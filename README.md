# Mahara Match

Mahara Match is a fresh-start project for helping Tunisian job seekers make
their skills visible and explore work and training pathways. The product
requirements and implementation order are tracked in `TASKS.md`.

## Current status

The first implementation milestone is underway: a French-first, responsive
React app shell with design tokens, reusable UI basics, light/dark themes, and
honest empty states. The FastAPI service currently provides a process-liveness
endpoint only. Authentication, PostgreSQL persistence, matching, and the other
product features are not implemented yet.

## Requirements

- Node.js 22.12+ (or 24+)
- Python 3.11+

## Run locally

Install and start the frontend:

```powershell
npm install
npm run dev
```

In another terminal, install and start the API:

```powershell
python -m pip install -r backend/requirements.txt
python -m uvicorn app.main:app --app-dir backend --reload
```

The API liveness endpoint is `http://127.0.0.1:8000/health/live`; it checks
that the process responds, not database readiness.

## Checks

```powershell
npm test
npm run build
python -m pytest
```

See `docs/AUDIT.md` for the fresh-project baseline and `TASKS.md` for current
progress and the next implementation steps.

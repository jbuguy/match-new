# Mahara Match

Mahara Match is a fresh-start project for helping Tunisian job seekers make
their skills visible and explore work and training pathways. The product
requirements and implementation order are tracked in `TASKS.md`.

## Current status

The French-first responsive app shell is in place. Task 1 provides
PostgreSQL-backed roles, JWT sign-in, organisation membership, demo accounts,
role-specific navigation, and an append-only audit log. Candidate registration,
full profile onboarding with a Derja-capable local assistant, candidate skill
matching, employer job offers, and role-specific guided assistants are also
available. Candidates can also chat about careers in Derja, Arabic, or French
and return to their saved assistant conversations. Their career roadmaps
prioritize missing skills requested by published offers and save candidate-owned
step progress. Applications and courses remain unavailable rather than
simulated.

## Requirements

- Node.js 22.12+ (or 24+)
- Python 3.11+
- PostgreSQL

## Run locally

Create a local PostgreSQL database named `mahara_match`, then copy
`.env.example` to `.env`. Replace `JWT_SECRET_KEY` with a random value of at
least 32 characters. To seed demo accounts, set `MAHARA_ENABLE_DEMO_USERS=true`
and set `MAHARA_DEMO_PASSWORD` to a local-only password of at least 12
characters. Set `DATABASE_URL` to match your local PostgreSQL connection.
Demo accounts must never be seeded in production.

Install the backend dependencies, apply the migration, and seed the fake demo
accounts:

```powershell
python -m pip install -r backend/requirements.txt
python -m alembic -c backend/alembic.ini upgrade head
$env:PYTHONPATH = "backend"
python -m app.seed_demo_users
```

Demo account emails:

- `candidate@demo.maharamatch.test`
- `employer@demo.maharamatch.test`
- `ministry@demo.maharamatch.test`
- `provider@demo.maharamatch.test`
- `operator@demo.maharamatch.test`

Each account uses the password configured in `MAHARA_DEMO_PASSWORD`. The seed
command is repeatable and will not reset passwords for existing accounts.

Install and start the frontend:

```powershell
npm install
npm run dev
```

In another terminal, start the API:

```powershell
python -m uvicorn app.main:app --app-dir backend --reload
```

The API liveness endpoint is `http://127.0.0.1:8000/health/live`; it checks
that the process responds, not database readiness. Candidate registration is
at `POST /auth/register`, sign-in is at `POST /auth/login`, and `GET /auth/me`
returns the authenticated user's server-side role. Set `VITE_API_BASE_URL`
when the API is not at `http://127.0.0.1:8000`. Candidates can read and update
their full profile at `/candidate/profile`, chat with the profile assistant at
`POST /candidate/assistant/chat`, transcribe voice at
`POST /candidate/assistant/transcriptions`, and request spoken replies at
`POST /candidate/assistant/speech`. Career assistant sessions can be listed,
created, read, and deleted at `/candidate/assistant/sessions`; send a message
to a session at `POST /candidate/assistant/sessions/{session_id}/messages`.
Candidates can read offer matches at `GET /candidate/matches`. Employers can
publish offers at `POST /employer/offers` and list their own offers at
`GET /employer/offers`.
The match score is the percentage of an offer's required skills listed on the
candidate profile; it is informational and does not predict hiring outcomes.

### Local assistant services

The backend sends chat requests to the OpenAI-compatible
`/v1/chat/completions` endpoint under `MAHARA_LLM_BASE_URL`. The example
configuration targets a local service on port 1234; set the model name and
optional API key to match your local server. Voice input uses the
OpenAI-compatible `/v1/audio/transcriptions` endpoint under
`MAHARA_WHISPER_BASE_URL`; configure a Derja-capable Whisper model where
available, or standard multilingual Whisper. Spoken replies use the
OpenAI-compatible `/v1/audio/speech` endpoint under `MAHARA_TTS_BASE_URL`.
Whisper and TTS can run as separate local services. Their API keys are optional
and must remain in the backend environment, never in the frontend.

Text chat and manual profile editing remain available if voice services are
not configured. The candidate reviews and edits assistant suggestions before
saving them. Conversation context exists only while the profile page is open;
the profile assistant does not persist its transcript or raw audio. The career
assistant stores conversation text in candidate-owned server sessions until
the candidate deletes each session. Assistant service requests are sent to
the configured backend services for processing; keep those service URLs on
trusted local infrastructure.

### Development data and labour-market sources

Generate repeatable, clearly labelled synthetic Tunisian job offers:

```powershell
$env:PYTHONPATH = "backend"
python -m app.synthetic_data --seed 2026 --count 100 `
  --output backend/data/generated/synthetic_job_offers.jsonl
```

The seed and count determine the exact JSONL contents. Every generated record
is marked `is_synthetic: true` and `source: "synthetic"`; these offers are for
development and must never be presented as real vacancies.

Collect the configured public data sources:

```powershell
$env:PYTHONPATH = "backend"
python -m app.data_pipeline --output-dir backend/data/open
```

The collector currently retrieves:

- Eurostat annual unemployment rates for France (ages 15–74, total), from the
  official JSON API. It saves the source response and a normalized period/value
  series.
- France Travail's BMO dataset catalogue from data.gouv.fr. It saves dataset
  metadata, downloads the latest year-labelled XLSX resource, and normalizes
  occupation, region, department, employment-area, planned recruitment,
  difficult recruitment, and seasonal recruitment fields. BMO rows are
  aggregate estimates, not individual job advertisements.

Each run writes raw responses, normalized JSONL records, and a `manifest.json`
with retrieval time, source page, provider, licence, record count, and raw
SHA-256 checksums. A failed or invalid source is recorded in the manifest and
causes a non-zero exit; other configured sources are still attempted. Output
under `backend/data/` is local and git-ignored. Check the upstream licence,
availability, definitions, and revision notes before using or redistributing
any collected data. Statistical trends are context, not individual hiring
predictions.

Labour-market indicators do not require copying legal texts. The collector
does not scrape or redistribute legislation; if a later feature needs a legal
reference, link to the current official Légifrance text and verify its
applicability and update date rather than treating it as career advice.

## Roles and privacy

| Role | Access |
| --- | --- |
| Candidate | Own full profile, offer matches, roadmap progress, and deletable assistant sessions; future consents and applications |
| Employer | Offers created by the signed-in employer; future applications and permitted applicant access |
| Ministry admin | Referentials, suggestion review, dataset imports, logged exports, and aggregate indicators |
| Training provider | Its organisation's course catalogue and validated skills |
| Operator | Service configuration/status and audit metadata, never personal records |

Every protected request verifies its JWT role against the current database user.
The liveness endpoint is intentionally public. Candidate and organisation
ownership guards are available for the domain routes as they are added. The
current operator audit view omits email, user IDs, resource IDs, and event
details. Admin actions and sensitive reads should use
`record_admin_action` and `record_sensitive_read` after authorization checks;
profile changes, registration, and assistant service requests are audited
without recording profile values, message content, or audio. Career chat
messages are persisted only in sessions owned by the candidate and are
excluded from audit details. Role-specific guidance remains curated in the
frontend; candidate assistants use only the backend-configured model and voice
services.

## Checks

```powershell
npm test
npm run build
python -m pytest
python -m alembic -c backend/alembic.ini upgrade head --sql
```

See `docs/AUDIT.md` for the fresh-project baseline and `TASKS.md` for current
progress and the next implementation steps.

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
step progress. Candidates can prepare for interviews using employer-published
offer requirements and clearly labeled general behavioral and communication
prompts, and complete saved, role-linked technical assessments with
deterministic knowledge scoring and structured feedback for text responses.
They can also record technical or behavioral answers in the browser, review and
edit Whisper transcripts before submitting them, or use manual text entry.
Candidate code submissions are never executed. Candidates can also review a
lightweight communication coach that analyzes a draft answer for structure,
concrete examples, and result clarity and surfaces micro-exercises to improve
it. The interview-prep workspace now also shows a progress report summarizing
completed questions, score averages, and recommendations for the next round of
practice. Candidates can apply to offers and enroll in published formations.
Employers can review applications and record hiring outcomes.
Training providers can manage courses and follow enrollments and completions.
The ministry administration dashboard reports filtered platform activity and
aggregate outcomes without exposing candidate-level records.

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

To reset the local development database without dropping the schema or migration
history, use the explicit opt-in reset script:

```powershell
$env:PYTHONPATH = "backend"
$env:DATABASE_URL = "postgresql+psycopg://postgres:password@localhost:5432/mahara_match"
python -m scripts.reset_demo_database --confirm
```

To rebuild a realistic demo dataset with stable candidate and employer records,
matching offers, and published training content:

```powershell
$env:PYTHONPATH = "backend"
python -m scripts.seed_demo_data
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
their full profile at `/candidate/profile`, upload a CV for AI-assisted
profile extraction at `POST /candidate/profile/cv`, review and edit the
extracted values before saving, chat with the profile assistant at
`POST /candidate/assistant/chat`, transcribe voice at
`POST /candidate/assistant/transcriptions`, and request spoken replies at
`POST /candidate/assistant/speech`. Career assistant sessions can be listed,
created, read, and deleted at `/candidate/assistant/sessions`; send a message
to a session at `POST /candidate/assistant/sessions/{session_id}/messages`.
Candidates can read offer matches at `GET /candidate/matches` and list
interview-preparation targets at `GET /candidate/interview-prep/roles`. Read an
offer-based competency profile at`GET /candidate/interview-prep/profiles/{offer_id}`. Requirements come from
that employer offer; generic behavioral prompts are suggestions and do not
assert employer requirements. Start a technical assessment for an offer skill
with `POST /candidate/interview-prep/assessments`, read the candidate-owned
session at `GET /candidate/interview-prep/assessments/{assessment_id}`, and
submit answers at
`POST /candidate/interview-prep/assessments/{assessment_id}/answers`. Objective
Python and SQL knowledge questions are scored deterministically; open answers
are evaluated by the configured local assistant and saved with criterion
scores and feedback. Text exercises are not executed. Open-answer assessment
requires `MAHARA_LLM_BASE_URL` to be configured. Start a behavioral and
situational assessment for a supported general competency at
`POST /candidate/interview-prep/behavioral-assessments`, read the
candidate-owned session at
`GET /candidate/interview-prep/behavioral-assessments/{assessment_id}`, and
submit a text answer at
`POST /candidate/interview-prep/behavioral-assessments/{assessment_id}/answers`.
Behavioral feedback includes structured Situation, Task, Action, and Result
scores; situational responses are evaluated without claiming to measure
personality. These are general coaching suggestions, not employer requirements.
Candidates can upload an interview answer for transcription at
`POST /candidate/interview-prep/{assessment_type}-assessments/{assessment_id}/questions/{question_id}/transcription`
and poll its status at
`GET /candidate/interview-prep/transcriptions/{transcription_id}`. Uploads
require an `audio/*` media type and are limited to 20 MB. The backend processes
audio asynchronously through the configured Whisper service, stores the
transcript and job status, and does not retain raw audio. Transcripts are
suggestions: candidates can edit them, and they are not submitted until the
candidate uses the normal assessment answer form. Manual text entry remains
available when browser recording or the transcription service is unavailable.
The `{assessment_type}` path value is `technical` or `behavioral`. Jobs use
FastAPI's in-process background tasks, so a process restart before processing
finishes can leave a job queued; the candidate can retry the recording.
Employers can publish offers at `POST /employer/offers` and list their own
offers at `GET /employer/offers`.
Candidates submit and view applications at
`POST /candidate/applications/{offer_id}` and `GET /candidate/applications`;
employers review their offer applications at `GET /employer/applications` and
update status at `PUT /employer/applications/{application_id}/status`.
Training providers list, create, and update their own courses at
`GET|POST /training/courses` and `PUT /training/courses/{course_id}`. Course
metadata includes title, summary, skills, delivery mode, location, dates,
duration, capacity, optional price in TND, and draft/published/archived status.
Providers review participants at
`GET /training/courses/{course_id}/enrollments` and record completion or
withdrawal at `PUT /training/enrollments/{enrollment_id}/status`. Candidates
browse published courses at `GET /candidate/courses`, enroll at
`POST /candidate/courses/{course_id}/enroll`, and view their enrollments at
`GET /candidate/enrollments`. Ministry administrators read date-filterable
aggregate indicators at `GET /admin/indicators?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD`.
The reported hiring rate is hired applications divided by closed applications
(hired or rejected); it represents employer-reported outcomes, not an
independently verified employment measure. Application records and provider
rosters are role-scoped, sensitive profile reads are audited, and the admin
indicators endpoint returns aggregate data only.
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

- World Bank World Development Indicators for Tunisia: annual total
  unemployment, youth unemployment (ages 15–24), and employment-to-population
  ratio. The unemployment series are modelled ILO estimates; the manifest
  records each indicator's provider, source URL, licence note, retrieval time,
  and checksum.
- Tunisia's [National Open Data Catalogue](https://catalog.data.gov.tn) exposes
  an open `cc-by` list of vocational specialties dated 2017 and a national
  open-licence agricultural investment series counting jobs created through
  2022. The specialty list is a historical taxonomy, not evidence that a
  course is currently available. The agricultural series measures jobs
  attributed to investment projects; it is not total employment or vacancies.
- INS Statistiques publishes Tunisia employment-related statistical pages
  (including its [employment statistics index](https://ins.tn/statistiques/emploi)).
  The employment landing page links to employment/unemployment topics; in this
  source check the linked topic pages did not expose a documented bulk API or
  machine-readable labour-market series suitable for automatic ingestion.
  ANETI's [official site](https://www.emploi.nat.tn/fo/Fr/global.php) exposes
  live job-search services, but no public bulk endpoint or reuse terms for
  vacancy collection were verified. Reuse terms for programmatic collection
  from either site were not confirmed. Do not scrape either source or present
  live listings as a trend dataset until an authorised, documented feed and
  its terms are confirmed. The older employment-office directory contains
  staff contact details and is deliberately excluded. Textile employment files
  are also excluded until their custom catalogue licence is verified.
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
any collected data. Tunisia observations and France observations remain
separately labelled. French data can provide comparative context about
cross-border or European trends, but it is not evidence of Tunisian demand and
must not be presented as a substitute for Tunisia-specific sources.
Statistical trends are context, not individual hiring predictions.

### Assistant knowledge and retrieval

The assistant remains a general-purpose LM Studio chat. Retrieval is an
optional layer for labour-market, skill, career, and job-search questions;
ordinary general questions do not depend on the knowledge tables or embedding
service. PostgreSQL uses pgvector for cosine similarity and a `simple`
full-text index for keyword matching. Text, Markdown, and PDF ingestion keeps
source, dates, country, language, category, skill/occupation metadata, and a
content checksum; repeated ingestion of unchanged content does not duplicate
chunks.

The Compose stack uses the `pgvector/pgvector:pg17-trixie` PostgreSQL image,
matching the Debian 13 base used by the original Postgres image, and has an
optional CPU embedding service using
`sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (384 dimensions).
The pgvector column is fixed at 384 dimensions; changing embedding models
requires a corresponding schema migration.
Set the embedding values shown in `.env.example`; start both services with
`docker compose --profile rag up -d`. The model is multilingual, including
French and Arabic; Tunisian Derja quality should be evaluated on representative
queries. Its 128-token input limit is why the example uses 350-character
chunks. The endpoint must implement the OpenAI-compatible `/v1/embeddings`
request. With no embedding endpoint, document ingestion and retrieval use
keyword search only. An embedding service failure is logged and also falls
back to keyword search; it must not block a general assistant response.
Configure the chunk, retrieval, timeout, similarity, and hybrid-weight
settings in `.env.example`.

Apply the migration after installing requirements. PostgreSQL must permit
`CREATE EXTENSION vector` and provide pgvector. Use the `app.knowledge_base`
service functions to ingest or remove documents programmatically. To load the
approved, collected annual Tunisia and France unemployment series:

```powershell
$env:PYTHONPATH = "backend"
python -m app.ingest_labour_data --data-dir backend/data/open
```

The importer loads only the reviewed annual series and the historical
specialty list. It keeps country, provider, source URL, update date, year
range, methodology, licence, and source vintage in document metadata.
The France Travail BMO workbook is collected separately but not yet imported:
it is a single-year set of regional recruitment intentions, not a time series
or evidence of Tunisian demand, and needs a deliberate aggregation strategy
before retrieval.

Only ingest data whose source and reuse terms have been reviewed. The current
Tunisia series are national macro indicators, not occupation-level vacancy or
skill-demand data. French observations are retained as a distinct country and
must not be represented as evidence of Tunisia-specific demand. The platform
now has a provider-managed course catalogue and candidate enrollment records;
the assistant's retrieval context does not yet query those records, so consult
the candidate catalogue for current course availability rather than relying on
assistant retrieval or historical specialty data. The structured platform
contains candidate skills and employer-created job offers, but no authoritative
occupation-skill taxonomy.

Labour-market indicators do not require copying legal texts. The collector
does not scrape or redistribute legislation; if a later feature needs a legal
reference, link to the current official Légifrance text and verify its
applicability and update date rather than treating it as career advice.

## Roles and privacy

| Role | Access |
| --- | --- |
| Candidate | Own profile, offer matches, roadmap progress, assistant sessions, job applications, and course enrollments; browse published courses |
| Employer | Offers created by the signed-in employer and applicants to those offers; manage application outcomes |
| Ministry admin | Referentials, suggestion review, dataset imports, logged exports, and aggregate indicators without candidate-level records |
| Training provider | Courses created by the signed-in provider; view and update enrollments for those courses |
| Operator | Service configuration/status and audit metadata, never personal records |

Every protected request verifies its JWT role against the current database user.
The liveness endpoint is intentionally public. Candidate and organisation
ownership checks are enforced at each marketplace route. The
current operator audit view omits email, user IDs, resource IDs, and event
details. Admin actions and sensitive reads should use
`record_admin_action` and `record_sensitive_read` after authorization checks;
employer applicant access and provider enrollee access are scoped to their
offers/courses and audited. Hiring outcomes are explicitly reported by
employers; the dashboard rate is hires divided by closed applications, not an
independently verified employment measure. Administration indicators contain
aggregates only.
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

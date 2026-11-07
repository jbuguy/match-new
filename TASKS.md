# Mahara Match — Task Tracker

Progress ledger for the Mahara Match build brief. Update this file as milestones
are implemented and verified; do not mark a task complete before its acceptance
checks pass.

Status: `[ ]` todo · `[/]` in progress · `[x]` completed · `[!]` blocked

## Current focus

- [/] Task 12 — Persistent assistant surfaces.
  - [x] Reuse user-owned assistant sessions for floating and full-page chat;
    keep the selected conversation across app navigation.
  - [x] Add a responsive authenticated floating chat for every role, with
    conversation creation, loading/error states, and a link to the workspace.
  - [x] Add workspace conversation search, rename, and owner-scoped API access.
  - [x] Allow PATCH through CORS preflight and verify API session access,
    rename ownership, preflight, and frontend production build.
  - [ ] Verify the full assistant navigation flow at desktop and mobile sizes.
- [x] Task 0 — Fresh-project baseline audit (`docs/AUDIT.md`).
- [x] Task 6, part 1 — Design tokens, shared components, and responsive app
  shell.
  - [x] Choose the brief's stack: React/Vite/TypeScript, FastAPI, PostgreSQL.
  - [x] Implement design tokens, light/dark theme switching, and reusable
    buttons, cards, badges, chips, avatars, form inputs and selects, tabs,
    modal, drawer, toast, stepper, progress, skeleton, empty state, data table,
    and chart frame.
  - [x] Implement candidate app shell and French-first empty states.
  - [x] Verify app navigation and no horizontal overflow at 360 px and
    1280 px; verify theme toggle.
  - [x] Test component keyboard behavior, modal focus trapping, and accessible
    labels/announcements.
- [x] Task 1 — Roles, access control, demo users, and audit log.
  - [x] Define five app-specific roles and server-side permission boundaries.
  - [x] Add PostgreSQL users, organisations, memberships, and migration.
  - [x] Add password-hashed demo users and JWT login/current-user endpoints.
  - [x] Add role and ownership/organisation membership guards.
  - [x] Add append-only audit events and an operator view without personal data.
  - [x] Add role-specific login, dashboard, and navigation in the frontend.
  - [x] Test all roles on the current protected routes, login, ownership,
    migration append-only behavior, and frontend role navigation.
- [x] Task 7 — Candidate skill matching, employer offers, and role-specific
  assistant guidance.
  - [x] Save candidate skills and calculate deterministic skill-overlap scores
    for published job offers.
  - [x] Let employers publish offers and list only offers they created.
  - [x] Add role-restricted assistant guidance for candidates and employers.
  - [x] Test matching, role boundaries, persistence migration, offer creation,
    and both assistant experiences.
- [x] Task 8 — Candidate registration, onboarding, and reusable profile
  assistant.
  - [x] Add candidate-only registration and persist contact, location,
    education, experience, and skill profile fields.
  - [x] Add a Derja-capable local LLM chat adapter with candidate-reviewed
    profile suggestions and a manual profile editor.
  - [x] Add local Whisper transcription and server-side TTS adapters with
    explicit unavailable-service and text fallbacks.
  - [x] Reuse the assistant for profile updates after onboarding; audit service
    requests without storing profile values, chat messages, or raw audio.
  - [x] Test registration, profile persistence, role boundaries, voice-service
    contracts, confirmation-before-save, migrations, and UI onboarding.
- [/] Task 2 — Derja chatbot, manual fallback, and session history.
  - [x] Add a Derja-capable career chat with a direct route to manual profile
    editing when the assistant is unavailable.
  - [x] Persist candidate-owned chat sessions with list, reopen, and delete
    controls; keep transcripts out of audit event details.
  - [ ] Re-run API session, ownership, deletion, and migration checks after
    the final invalid-response guard was added.
- [x] Task 10 — Hybrid RAG assistant and Tunisian labour-market intelligence.
  - [x] Audit the assistant, LM Studio client, database models, profile/job
    records, and conversation history; retain the existing general-purpose
    assistant as the primary reasoning engine.
  - [x] Extend public-data collection with sourced Tunisia labour-market
    indicators while keeping French observations separate and comparative.
  - [x] Inventory authoritative Tunisian sources, available application data,
    source licences, recency, and gaps before adding claims or records.
  - [x] Design a multilingual document ingestion and PostgreSQL/pgvector
    retrieval foundation with keyword search, metadata, source citations, and
    graceful fallback.
  - [x] Add conditional retrieval and structured application-data queries
    without requiring RAG for general questions.
  - [x] Add migration, configuration, ingestion documentation, and tests for
    retrieval, routing, relevance, failures, and provenance.
  - [x] Apply the migration and ingest the collected records on an authorized
    PostgreSQL/pgvector database; verify live vector and full-text queries with
    the configured multilingual embedding service.
- [x] Task 11 — Administration and training-provider dashboards.
  - [x] Add persisted job applications and employer-reported hiring outcomes
    with candidate/employer role boundaries.
  - [x] Add provider-owned course metadata, candidate enrollment, provider
    roster, and completion tracking.
  - [x] Add filtered aggregate administration indicators for activity, skills,
    applications, hiring outcomes, and training.
  - [x] Add role-specific administration and provider dashboards plus
    candidate/employer supporting screens.
  - [x] Re-run API (89), migration, frontend UI (32), and production build
    checks after final dashboard changes.
- [x] Task 4 — Deterministic career roadmap engine and screens.
  - [x] Generate prioritized steps from missing skills in published offers and
    the candidate’s saved skills.
  - [x] Persist candidate-owned step completion and display roadmap progress.
  - [x] Test deterministic ordering, role boundaries, persistence, screens,
    and database migration.

## Build order

- [x] Task 1 — Roles, access control, demo users, and audit log.
- [x] Task 7 — Candidate skill matching, employer offers, and role-specific
  assistant guidance.
- [x] Task 8 — Candidate registration, onboarding, and reusable profile
  assistant.
- [x] Task 5 — Reproducible synthetic data generator.
  - [x] Generate deterministic, explicitly labelled synthetic Tunisian job
    offers from a seed and write JSONL fixtures.
- [x] Task 3 — Authorised data collection and ingestion pipeline.
  - [x] Collect France unemployment time series from the public Eurostat API
    and France Travail BMO metadata and the latest occupation/area estimates.
  - [x] Save raw snapshots, normalized records, source/licence metadata, and
    checksums; report source failures explicitly.
- [/] Task 2 — Derja chatbot, manual fallback, and session history.
- [x] Task 10 — Hybrid RAG assistant and Tunisian labour-market intelligence.
- [x] Task 4 — Deterministic career roadmap engine and screens.
  - [x] Build roadmap steps from profile skill gaps in published job offers,
    prioritizing skills requested by more offers.
  - [x] Add candidate progress tracking and a responsive roadmap screen.
  - [x] Add role-restricted API, persistence migration, and regression tests.
- [/] Task 9 — Interview preparation and hard/soft skills review.
  - [x] Phase 0 — Inspect architecture and identify reusable profile, offer,
    permission, assistant, training, and frontend components.
  - [x] Phase 1 — Add a competency catalog, proficiency scale, candidate skill
    comparison, offer-based role profiles, and clearly labeled behavioral and
    communication suggestions.
  - [x] Phase 2 — Generate knowledge, practical, and scenario questions from
    offer skills; persist candidate-owned sessions, answers, and evaluations.
    Score objective Python/SQL questions deterministically, validate structured
    local-assistant feedback for open answers, and keep code execution disabled.
  - [x] Phase 3 — Add saved behavioral and situational assessment sessions
    for the supported soft-skill catalog, accept candidate-owned text answers,
    and provide structured STAR evaluation and improvement feedback without
    inferring personality or penalizing non-professional experience.
  - [x] Phase 4 — Capture technical and behavioral interview answers in the
    browser, asynchronously transcribe them, and let candidates review/edit
    transcripts before submission. Persist job status and transcript only;
    validate ownership and audio type/size, and never retain raw audio.
    Verify recorder/upload/review UI, API ownership and failure states,
    migration, backend suite (111), frontend suite, and production build.
  - [x] Phase 5 — Analyze communication signals and provide exercises.
    Draft interview responses are scored for structure, concrete examples,
    and result clarity; the UI surfaces a short communication coach and a
    set of practice exercises. Validate with the interview-prep frontend
    suite and the production build.
  - [x] Phase 6 — Orchestrate adaptive mock interviews.
  - [ ] Phase 7 — Integrate candidate CV evidence.
  - [ ] Phase 8 — Recommend matching training courses.
  - [x] Phase 9 — Add reports and progress tracking.
    Summarize completed technical and behavioral responses into a simple
    interview-prep report with question counts, score averages, and a
    progress bar, plus coaching recommendations for the next practice round.
  - [ ] Phase 10 — Complete end-to-end integration, validation, and
    optimization.
- [x] Task 11 — Administration and training-provider dashboards.
- [ ] Task 6, part 2 — Polish the remaining screens in the brief's order.

## Project baseline / guardrails

- The project started with no application source, routes, models, migrations,
  or tests; see `docs/AUDIT.md`.
- The brief's stack is the project baseline. No pre-existing behavior is being
  replaced.
- Features not implemented are unavailable; the initial UI uses empty states
  rather than simulated platform data.
- Latest checks: frontend production build passed; frontend tests passed
  (including interview recording and transcript review); full API test suite
  passed (111), including marketplace role/ownership, SQLite migrations through
  revision 0010, behavioral and technical assessment persistence and scoring,
  interview transcription job ownership/failure states, roadmap, permissions,
  and assistant retrieval/routing. The new migration through revision 0010 passed
  SQLite integration checks
  and PostgreSQL static SQL generation. PostgreSQL 17 with pgvector was
  migrated through revision 0006; six approved Tunisia/France documents and
  361 384-dimensional chunks were ingested. Live PostgreSQL vector,
  full-text-only, country-filtered, French, and Arabic retrieval checks passed
  against the local multilingual embedding service.
- PostgreSQL-backed authentication and role infrastructure are implemented.
  Candidate profiles and employer job offers are persisted; the match score
  is deterministic required-skill overlap. Candidate profile assistance uses
  configured local model services without persisted history; career assistant
  conversations are persisted in candidate-owned sessions. Career roadmaps
  are deterministic skill-gap plans based on published offers, with
  candidate-owned progress. Job applications and provider courses,
  enrollments, and completions are persisted; the administration dashboard
  reports aggregate data and explicitly employer-reported hiring outcomes.
- API liveness is process-only; it intentionally does not imply database
  readiness.
- Live PostgreSQL authentication was rejected by the current local connection
  settings, so the migration and demo seed were not exercised against that
  server; see the migration SQL and SQLite integration checks above.
- GitHub PR is not yet possible: this local git repository has no commits or
  remote. User requested PR and merge; destination remote/base branch are
  required before publication.
- Continue from this file and the audit. Review only files relevant to the
  current milestone; update the ledger after verification.

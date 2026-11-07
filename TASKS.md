# Mahara Match — Task Tracker

Progress ledger for the Mahara Match build brief. Update this file as milestones
are implemented and verified; do not mark a task complete before its acceptance
checks pass.

Status: `[ ]` todo · `[/]` in progress · `[x]` completed · `[!]` blocked

## Current focus

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
- [x] Task 4 — Deterministic career roadmap engine and screens.
  - [x] Build roadmap steps from profile skill gaps in published job offers,
    prioritizing skills requested by more offers.
  - [x] Add candidate progress tracking and a responsive roadmap screen.
  - [x] Add role-restricted API, persistence migration, and regression tests.
- [ ] Task 9 — Interview preparation and hard/soft skills review.
  - [ ] Help candidates review role-relevant hard skills and soft skills
    before interviews.
- [ ] Task 6, part 2 — Polish the remaining screens in the brief's order.

## Project baseline / guardrails

- The project started with no application source, routes, models, migrations,
  or tests; see `docs/AUDIT.md`.
- The brief's stack is the project baseline. No pre-existing behavior is being
  replaced.
- Features not implemented are unavailable; the initial UI uses empty states
  rather than simulated platform data.
- Latest checks: frontend production build passed; frontend tests passed
  (29); full API test suite passed (59), including roadmap, permissions, and
  SQLite migration checks. PostgreSQL-backed verification remains unavailable
  with the current local connection settings.
- PostgreSQL-backed authentication and role infrastructure are implemented.
  Candidate profiles and employer job offers are persisted; the match score
  is deterministic required-skill overlap. Candidate profile assistance uses
  configured local model services without persisted history; career assistant
  conversations are persisted in candidate-owned sessions. Career roadmaps
  are deterministic skill-gap plans based on published offers, with
  candidate-owned progress. Applications and courses remain unavailable.
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

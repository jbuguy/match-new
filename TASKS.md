# Mahara Match — Task Tracker

Progress ledger for the Mahara Match build brief. Update this file as milestones
are implemented and verified; do not mark a task complete before its acceptance
checks pass.

Status: `[ ]` todo · `[/]` in progress · `[x]` completed · `[!]` blocked

## Current focus

- [x] Task 0 — Fresh-project baseline audit (`docs/AUDIT.md`).
- [/] Task 6, part 1 — Design tokens, shared components, and responsive app
  shell.
  - [x] Choose the brief's stack: React/Vite/TypeScript, FastAPI, PostgreSQL.
  - [x] Implement design tokens, light/dark theme switching, and reusable
    Button, Card, Badge, and ProgressBar primitives.
  - [x] Implement candidate app shell and French-first empty states.
  - [x] Verify app navigation and no horizontal overflow at 360 px and
    1280 px; verify theme toggle.
  - [ ] Complete the full shared component catalog from the brief.

## Build order

- [ ] Task 1 — Roles, access control, demo users, and audit log.
- [ ] Task 5 — Reproducible synthetic data generator.
- [ ] Task 3 — Authorised data collection and ingestion pipeline.
- [ ] Task 2 — Derja chatbot, manual fallback, and session history.
- [ ] Task 4 — Deterministic career roadmap engine and screens.
- [ ] Task 6, part 2 — Polish the remaining screens in the brief's order.

## Project baseline / guardrails

- The project started with no application source, routes, models, migrations,
  or tests; see `docs/AUDIT.md`.
- The brief's stack is the project baseline. No pre-existing behavior is being
  replaced.
- Features not implemented are unavailable; the initial UI uses empty states
  rather than simulated platform data.
- Latest checks: frontend build passed; frontend tests passed (3); API tests
  passed (1); `npm audit` reported zero vulnerabilities.
- No PostgreSQL integration, authentication, matching, or product data exists
  yet. API liveness is process-only.
- Continue from this file and the audit. Review only files relevant to the
  current milestone; update the ledger after verification.

# Mahara Match — Repository Audit

**Date:** 2026-11-06  
**Scope:** Fresh project baseline in this workspace; no application code existed
before this implementation began.

## Baseline

This is a new application, not an audit of an existing product. The initial
workspace contained only the build brief's task tracker and an empty `docs`
directory. There were no routes, models, migrations, auth implementation,
matching logic, UI, seeds, or tests to preserve or report as existing.

The build brief specifies a React/Vite frontend, FastAPI backend, and
PostgreSQL. The initial implementation is establishing those boundaries; the
backend currently exposes only liveness and does not yet connect to a database.

| Area | Initial status | Current files |
|---|---|---|
| Auth, profiles, offers, matching, applications, formation, ministry routes | Missing | None |
| API liveness | Implemented; process status only, no database readiness check | `backend/app/main.py` |
| Models and database migrations | Missing | None |
| Authentication, roles, and ownership checks | Missing | None |
| Chat, LLM client, speech-to-text, prompts | Missing | None |
| Matching weights (50/20/15/15) and tests | Missing | None |
| Skill/occupation referentials and skill relations | Missing | None |
| Seeds, ingestion, workers, scheduled jobs | Missing | None |
| UI framework and styling | Started: React, Vite, TypeScript, responsive CSS tokens, light/dark mode, reusable primitives | `src/`, `package.json`, `vite.config.ts` |
| API framework | Started: FastAPI liveness endpoint | `backend/app/main.py` |
| Test suite and baseline | No pre-existing suite; initial checks added with implementation | `src/App.test.tsx`, `backend/tests/` |

## Build brief status

“Partial” means work has started but the task's acceptance criteria are not
complete. No feature beyond the explicitly implemented app-shell and liveness
scaffolds should be treated as available.

| Task | Status | Files |
|---|---|---|
| Task 0 — Repository audit | Complete for the clean-start baseline | `docs/AUDIT.md` |
| Task 1 — Roles and access control | Missing | None |
| Task 2 — Derja chatbot | Missing | None |
| Task 3 — Data collection pipeline | Missing | None |
| Task 4 — Career roadmap engine | Missing | None |
| Task 5 — Synthetic data generation | Missing | None |
| Task 6 — Design system and UI | Partial: part 1 in progress | `src/`, `index.html` |

## Test baseline

There was no pre-existing code or test suite to run. The initial implementation
checks passed: frontend build; 12 frontend tests; 1 API test; and `npm audit`
with zero reported vulnerabilities. No database or product-feature tests
exist yet.

## Next steps

Finish Task 6 part 1, then continue in the brief's order: roles/access control,
synthetic data, authorised ingestion, chatbot, roadmap engine, and remaining UI
polish. Update this audit and `TASKS.md` as each milestone is verified.

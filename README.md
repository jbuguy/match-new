# Mahara Match

Mahara Match is a fresh-start project for helping Tunisian job seekers make
their skills visible and explore work and training pathways. The product
requirements and implementation order are tracked in `TASKS.md`.

## Current status

The French-first responsive app shell is in place, and Task 1 now provides
PostgreSQL-backed roles, JWT sign-in, organisation membership, demo accounts,
role-specific navigation, and an append-only audit log. Product data routes
(profiles, offers, applications, courses, matching, chat, and roadmaps) are not
implemented yet; their data remains unavailable rather than simulated.

## Requirements

- Node.js 22.12+ (or 24+)
- Python 3.11+
- PostgreSQL

## Run locally

Create a local PostgreSQL database named `mahara_match`, then copy
`.env.example` to `.env`. Replace `JWT_SECRET_KEY` with a random value of at
least 32 characters. To seed demo accounts, set `MAHARA_ENABLE_DEMO_USERS=true`
and set `MAHARA_DEMO_PASSWORD` to a local-only password of at least 12
characters. Demo accounts must never be seeded in production.

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
that the process responds, not database readiness. Sign-in is at
`POST /auth/login`; `GET /auth/me` returns the authenticated user's server-side
role. Set `VITE_API_BASE_URL` when the API is not at `http://127.0.0.1:8000`.

## Roles and privacy

| Role | Access |
| --- | --- |
| Candidate | Own profile, consents, matches, applications, roadmap, and chat data |
| Employer | Offers and applications for member organisations; applicant data only through an application |
| Ministry admin | Referentials, suggestion review, dataset imports, logged exports, and aggregate indicators |
| Training provider | Its organisation's course catalogue and validated skills |
| Operator | Service configuration/status and audit metadata, never personal records |

Every protected request verifies its JWT role against the current database user.
The liveness endpoint is intentionally public. Candidate and organisation
ownership guards are available for the domain routes as they are added. The
current operator audit view omits email, user IDs, resource IDs, and event
details. Admin actions and sensitive reads should use
`record_admin_action` and `record_sensitive_read` after authorization checks;
there are not yet any domain routes that perform those reads or actions.

## Checks

```powershell
npm test
npm run build
python -m pytest
python -m alembic -c backend/alembic.ini upgrade head --sql
```

See `docs/AUDIT.md` for the fresh-project baseline and `TASKS.md` for current
progress and the next implementation steps.

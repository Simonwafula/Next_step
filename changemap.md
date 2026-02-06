# Change Map

Purpose: Track human-readable changes and outcomes before pushing to git.

## Template
- Date:
- Change summary:
- Outcome:
- Affected areas:
- Tests:
- Follow-ups:

## 2026-02-06 (T-800 comprehensive audit hardening)
- Change summary:
  - Repo hygiene: stopped tracking `backend/venv3.11/` and a stray SQLite journal; expanded `.gitignore` to cover virtualenv variants, SQLite journal/WAL/SHM, and `artifacts/`.
  - Backend correctness/security: removed unsafe embedding parsing (`eval`) by introducing a safe `parse_embedding()` helper; ensured embeddings are persisted as JSON strings; fixed `DataProcessingService` to match the actual `JobPost` schema (use `first_seen/last_seen/description_raw`, derive “active” from recency).
  - Frontend security: added `frontend/js/sanitize.js` and escaped/sanitized user- and API-provided strings before rendering via `innerHTML` (mitigates XSS on index/admin/dashboard pages).
  - Backend consistency: replaced SQLAlchemy boolean comparisons (`== True/False`) with `.is_(True/False)`; added targeted `# ruff: noqa: E402` where scripts/tests intentionally mutate `sys.path`/env pre-import; added missing `asyncio` import.
  - Code quality: made the backend `ruff`-clean and applied `ruff format` repo-wide under `backend/`.
- Outcome:
  - `ruff check backend` passes and formatting is consistent.
  - Reduced RCE risk surface (no `eval` on DB data) and prevented runtime crashes in background processing due to stale schema assumptions.
  - Tests remain green.
- Affected areas: `.gitignore`, `backend/app/ml/embeddings.py`, `backend/app/services/search.py`, `backend/app/services/deduplication_service.py`, `backend/app/services/data_processing_service.py`, `backend/app/tasks/processing_tasks.py`, multiple API/services scripts under `backend/`.
- Tests:
  - `backend/venv3.11/bin/ruff check backend` (pass)
  - `backend/venv3.11/bin/ruff format backend` (pass)
  - `backend/venv3.11/bin/pytest` (pass; 11 passed, 12 skipped)
- Follow-ups:
  - Add a documented dev bootstrap (`python -m venv backend/venv3.11 && pip install -r backend/requirements.txt`) and consider a `requirements-dev.txt` for `ruff`.
  - Tighten/realize the skipped async tests (add markers or convert to sync), and make “script-like” tests assert meaningful outcomes (remove `return` values to avoid future pytest errors).
  - Add Twilio webhook signature validation + request auth and consider strict CORS/CSRF posture for auth endpoints.

## 2026-02-06 (T-800 improvement proposals implemented)
- Change summary:
  - Dev tooling: added `backend/requirements-dev.txt` (pins `ruff`) and updated `AGENTS.md` to install dev tooling from that file.
  - Twilio webhook hardening: added Twilio signature validation (`X-Twilio-Signature`), request size guard (413 on oversized payloads), and per-endpoint rate limiting for `/whatsapp/webhook` with proxy-aware URL reconstruction (`TWILIO_WEBHOOK_URL`, `x-forwarded-*`).
  - Auth hardening (browser clients): auth routes now set httpOnly cookies (access + refresh) and backend auth dependencies accept either Bearer tokens or cookies; logout now clears cookies without requiring a valid session.
  - Embeddings migration: introduced `job_post.embedding_vector` (portable `VectorString` type), dual-read in search/dedupe, dual-write/backfill in embedding updater, and Postgres startup schema ensures (pgvector extension, add column if missing, optional ANN index via `PGVECTOR_CREATE_INDEX=true`).
  - Test normalization: moved runnable smoke scripts out of pytest collection (`backend/scripts/`) and added deterministic tests under `backend/tests/`.
- Outcome:
  - `pytest` no longer reports skipped async coroutine tests or return-value warnings; new tests provide real coverage for the hardened auth/webhook paths.
  - Postgres deployments can transition toward pgvector with backward-compatible dual storage and an opt-in index build.
- Affected areas:
  - `AGENTS.md`, `backend/requirements-dev.txt`
  - `backend/app/core/config.py`, `backend/app/main.py`
  - `backend/app/api/auth_routes.py`, `backend/app/services/auth_service.py`
  - `backend/app/webhooks/whatsapp.py`
  - `backend/app/db/database.py`, `backend/app/db/models.py`, `backend/app/db/types.py`
  - `backend/app/services/search.py`, `backend/app/services/deduplication_service.py`
  - `backend/app/tasks/processing_tasks.py`
  - `backend/tests/`, `backend/scripts/`
- Tests:
  - `backend/venv3.11/bin/ruff check backend` (pass)
  - `backend/venv3.11/bin/ruff format backend --check` (pass)
  - `backend/venv3.11/bin/pytest` (pass; 7 passed)
- Follow-ups:
  - Consider adding CSRF protection if cookie auth is used cross-site (e.g., `SameSite=None` + `allow_credentials=True`).
  - If/when Alembic is standardized in this repo, add a proper migration for `embedding_vector` and pgvector index creation.

## 2026-01-19 (local sqlite path)
- Change summary: Switched local SQLite storage to `backend/var/nextstep.sqlite` and ensured the dev script prepares the directory; updated local env and docs to match.
- Outcome: Local dev avoids the corrupted `test_db.sqlite` and boots with a clean DB path.
- Affected areas: `.env`, `.env.example`, `scripts/dev-start.sh`, `AGENTS.md`, `backend/var/`.
- Tests: Not run.
- Follow-ups: Move or delete the old `backend/test_db.sqlite` if it still exists.

## 2026-01-19 (env quoting)
- Change summary: Quoted `.env` values that contain spaces so the dev script can `source` the file safely.
- Outcome: `scripts/dev-start.sh` no longer fails on `PROJECT_NAME` or `DESCRIPTION`.
- Affected areas: `.env`, `.env.example`.
- Tests: Not run.
- Follow-ups: Re-run `./scripts/dev-start.sh`.

## 2026-01-18
- Change summary: Added auth flows (email/password, Google OAuth, reset), introduced a search-first frontend with account UI, and wired government ingestion + monitoring. Cleaned extra virtual environments and consolidated documentation into `docs/` with new `features.md`, `userjourney.md`, and `changemap.md`.
- Outcome: Users can sign up/sign in, recover passwords, search for roles, and view profile/saved roles; ingestion pipeline can populate data; docs are centralized and easier to navigate.
- Affected areas: `backend/app/api`, `backend/app/services`, `frontend/`, `backend/app/ingestion/`, `docs/`, repo root.
- Tests: Not run.
- Follow-ups: Verify OAuth creds, SMTP config, and run ingestion against live sources.

## 2026-01-18 (dev start)
- Change summary: Added a helper script to start backend + frontend locally with the `.env` file.
- Outcome: Developers can boot the app with one command for local browser testing.
- Affected areas: `scripts/dev-start.sh`.
- Tests: Not run.
- Follow-ups: None.

## 2026-01-18 (auth UX)
- Change summary: Fixed auth UI visibility and added token validation on load to prevent mixed signed-in/out states.
- Outcome: Sign-in and sign-out are mutually exclusive, and invalid tokens reset the session before showing profile.
- Affected areas: `frontend/js/main.js`, `frontend/styles/main.css`.
- Tests: Not run.
- Follow-ups: None.

## 2026-01-18 (auth backend)
- Change summary: Reworked the database session wrapper to support both sync API usage and async test helpers.
- Outcome: Registration and login use sync sessions correctly while async tests can still `await` DB calls.
- Affected areas: `backend/app/db/database.py`.
- Tests: Not run.
- Follow-ups: Retest signup and login locally.

## 2026-01-18 (dashboards)
- Change summary: Added admin KPI endpoints with access control plus new admin/user dashboard pages and navigation links.
- Outcome: Admins can view KPIs, sources, and recent activity; users have a dedicated dashboard with paid/free sections.
- Affected areas: `backend/app/api/admin_routes.py`, `backend/app/services/auth_service.py`, `backend/app/api/auth_routes.py`, `frontend/admin.html`, `frontend/dashboard.html`, `frontend/js/admin.js`, `frontend/js/dashboard-ui.js`, `frontend/index.html`, `frontend/js/main.js`, `frontend/styles/main.css`, `features.md`, `.env`, `.env.example`.
- Tests: Not run.
- Follow-ups: Set `ADMIN_EMAILS` and verify admin access locally.

## 2026-01-18 (bcrypt pin)
- Change summary: Pinned bcrypt to a compatible version for passlib.
- Outcome: Registration/login should work without bcrypt version errors.
- Affected areas: `backend/requirements.txt`.
- Tests: Not run.
- Follow-ups: Reinstall backend requirements in the venv.

## 2026-01-18 (auth response)
- Change summary: Made phone fields optional in auth response models.
- Outcome: Registration succeeds when phone fields are null.
- Affected areas: `backend/app/api/auth_routes.py`.
- Tests: Local register flow verified via script.
- Follow-ups: None.

## 2026-01-18 (auth redirect)
- Change summary: Added post-auth redirects to user dashboard or admin console.
- Outcome: Email/password and Google sign-in now navigate to the correct dashboard automatically.
- Affected areas: `frontend/js/main.js`, `frontend/auth-callback.html`.
- Tests: Not run.
- Follow-ups: Confirm redirects on sign-in and Google OAuth.

## 2026-01-18 (dashboard gate)
- Change summary: Added clearer login links and host-mismatch messaging for dashboard/admin gates; bound frontend server to 127.0.0.1 in dev script.
- Outcome: Sessions persist across navigation and gate explains when the host origin is wrong.
- Affected areas: `scripts/dev-start.sh`, `frontend/dashboard.html`, `frontend/admin.html`, `frontend/js/dashboard-ui.js`, `frontend/js/admin.js`.
- Tests: Not run.
- Follow-ups: Use `http://127.0.0.1:5173` during local dev.

## 2026-01-18 (dashboard auth diagnostics)
- Change summary: Improved dashboard/admin gate messaging for missing session, expired token, or API offline.
- Outcome: Login issues are clearer and indicate the next fix step.
- Affected areas: `frontend/js/dashboard-ui.js`, `frontend/js/admin.js`.
- Tests: Not run.
- Follow-ups: None.

## 2026-01-18 (signed-in badge)
- Change summary: Added explicit "Signed in as" labels in dashboard and admin headers.
- Outcome: Users can confirm the active session at a glance.
- Affected areas: `frontend/js/dashboard-ui.js`, `frontend/js/admin.js`.
- Tests: Not run.
- Follow-ups: None.

## 2026-01-18 (jwt sub fix)
- Change summary: Stored JWT `sub` as string and parsed it back to int on lookup.
- Outcome: `/auth/me` succeeds after login, fixing dashboard gate loops.
- Affected areas: `backend/app/services/auth_service.py`, `backend/app/api/auth_routes.py`.
- Tests: Manual login check pending.

## 2026-01-18 (dashboard sign out)
- Change summary: Added sign-out buttons to user and admin dashboards.
- Outcome: Users can clear sessions directly from dashboards.
- Affected areas: `frontend/dashboard.html`, `frontend/admin.html`, `frontend/js/dashboard-ui.js`, `frontend/js/admin.js`.
- Tests: Not run.
- Follow-ups: None.

## 2026-01-18 (admin gate fix)
- Change summary: Prevented admin gate overlay when admin session is valid but data fetch fails.
- Outcome: Admins stay in the dashboard and see a status error instead of being blocked.
- Affected areas: `frontend/js/admin.js`.
- Tests: Not run.
- Follow-ups: Verify admin data loads after backend restarts.

## 2026-01-18 (gov scraper enhancements)
- Change summary: Improved government scraper link detection, added PDF text extraction, and fallback capture for list pages.
- Outcome: More sources yield ingestible postings for insights.
- Affected areas: `backend/app/ingestion/connectors/gov_careers.py`, `backend/requirements.txt`.
- Tests: Not run.
- Follow-ups: Install updated requirements and run `/api/admin/ingest/government`.

## 2026-01-18 (source cleanup tool)
- Change summary: Added a script to remove government sources returning 404/410.
- Outcome: Easy cleanup pass for stale URLs before ingestion runs.
- Affected areas: `scripts/clean_government_sources.py`.
- Tests: Not run.
- Follow-ups: Run the script locally with network access.

## 2026-01-18 (personalized recommendations)
- Change summary: Expanded recommendation scoring with keyword, location, and recency signals and removed stale recs before storing.
- Outcome: Recommendations align better with user skills/search history and prioritize recent postings.
- Affected areas: `backend/app/services/ai_service.py`, `backend/app/services/personalized_recommendations.py`.
- Tests: Not run.
- Follow-ups: Trigger `/api/users/recommendations` and review match quality.

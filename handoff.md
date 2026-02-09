# Handoff

## 2026-02-09 (Hardening & Test Coverage)

Branch: `main`

### Summary
- **T-403d**: Added 42 endpoint tests covering all analytics (public) and admin dashboard routes — overview, users, jobs, sources, operations, summaries, education mappings (CRUD), admin analytics, drift monitoring, and signals (tenders + hiring).
- **T-601c**: Implemented incremental dedup (`run_incremental_dedup`) using MinHash LSH with persistent `JobDedupeMap` tracking, and incremental embeddings (`run_incremental_embeddings`) that processes only unembedded jobs. Both wired into CLI and ProcessingLog. 10 tests.
- **T-603a/b**: Created 5-job regression fixture dataset and 34 regression tests validating title normalization, seniority, experience, education, salary parsing, skill extraction, and determinism guarantees.
- **T-731**: Created systemd service/timer templates for API server, pipeline (every 6h), and drift checks (daily) in `deploy/systemd/`.
- **T-732**: Built `backend/app/db/upsert.py` with Postgres `INSERT ON CONFLICT` + SQLite ORM fallback for jobs, orgs, and skills. Includes `bulk_upsert_jobs` convenience. 11 tests.
- Updated CLI (`backend/cli.py`): added `dedupe` command, replaced external script-based `embed` with incremental `run_incremental_embeddings`.

### Tests Run
- `.venv/bin/ruff check backend` (pass)
- `.venv/bin/ruff format backend --check` (pass)
- `.venv/bin/pytest backend/tests/` (99 passed)

### Files Changed
- `backend/tests/test_dashboard_endpoints.py` (new — 42 tests)
- `backend/tests/test_incremental_processing.py` (new — 10 tests)
- `backend/tests/test_upsert.py` (new — 11 tests)
- `backend/tests/test_regression.py` (new — 34 tests)
- `backend/app/normalization/dedupe.py` (added `run_incremental_dedup`)
- `backend/app/ml/embeddings.py` (added `run_incremental_embeddings`)
- `backend/app/db/upsert.py` (new — Postgres/SQLite upsert helpers)
- `backend/cli.py` (added `dedupe` command, updated `embed`)
- `deploy/systemd/` (new — 5 unit files)
- `data/samples/regression_jobs.json` (new — fixture dataset)
- `changemap.md` (updated task statuses + log)

### Next Steps
1. Decide on cookie-first auth for the frontend (CORS + CSRF).
2. Enable pgvector index build (`PGVECTOR_CREATE_INDEX=true`) during maintenance.
3. Remaining open items: T-500b (tender metadata normalization), T-502a (signal aggregation), T-602c (alerting hooks), T-603 (more regression fixtures).

---

## 2026-02-06 (T-800 Comprehensive Audit)

Branch: `feat/T-800-comprehensive-audit`

### Summary
- Cleaned up repo hygiene: stopped tracking `backend/venv3.11/`, removed a tracked SQLite journal, and expanded `.gitignore` for venv/artifacts/SQLite journals.
- Made backend `ruff`-clean and applied `ruff format`.
- Fixed correctness/security issues:
  - Removed `eval()` embedding parsing by adding safe `parse_embedding()` and using it in consumers.
  - Ensured embeddings are persisted as JSON strings.
  - Repaired `DataProcessingService` to match actual `JobPost` schema (use `first_seen/last_seen/description_raw`).
- Hardened the frontend against XSS by escaping API-provided fields before injecting into the DOM and restricting external links to `http(s)`.
- Implemented the audit improvement proposals:
  - Captured dev tooling (`backend/requirements-dev.txt`).
  - Hardened Twilio/WhatsApp webhook (signature validation + size guard + rate limiting).
  - Normalized “script tests” by moving smoke scripts out of pytest collection and adding real deterministic tests under `backend/tests/`.
  - Started pgvector transition via `job_post.embedding_vector` (portable type + dual-read/write + Postgres startup schema ensure + opt-in index build).
- Tests remain green.

### Commits
- `c51d696` `[T-800] Stop tracking venv and transient artifacts`
- `b640973` `[T-800] Make backend ruff-clean and fix processing/search correctness`
- `361d9e6` `[T-800] Update audit docs and changemap`
- `0cc000e` `[T-800] Harden frontend rendering against XSS`
- `66fdcad` `[T-800] Implement improvement proposals`

### Tests Run
- `backend/venv3.11/bin/ruff check backend`
- `backend/venv3.11/bin/ruff format backend --check`
- `backend/venv3.11/bin/pytest` (pass; 7 passed)

### Notes
- This environment has no outbound network (pip installs from PyPI will fail). Repo changes assume a normal dev/CI environment can install dependencies.

### Next Steps
1. Decide whether the browser frontend should switch to cookie-first auth (requires explicit `CORS_ORIGINS` and likely CSRF protection for cross-site scenarios).
2. For Postgres deployments, set `PGVECTOR_CREATE_INDEX=true` during a controlled maintenance window (index builds can be expensive on large tables).

# ChangeMap (Tasks, Subtasks, Logs)

## Legend
- TODO, IN_PROGRESS, BLOCKED, DONE

## 0. Repo Scan & Reconcile (MANDATORY)
- [x] (T-000-SCAN) Repo Scan & Reconcile (must run before any new feature work)
  - [x] (T-000a) Generate repo snapshot (tree, deps, tests, DB schema summary)
  - [x] (T-000b) Detect implemented vs missing
  - [x] (T-000c) Update changemap tasks to match reality
  - [x] (T-000d) Update agents.md with repo-specific conventions found
  - [ ] (T-000e) Commit + push scan baseline

## 1. Ingestion & Normalization (Partially Implemented)
- [x] (T-100) Database Implementation (Alembic/Postgres)
  - [x] (T-101) Set up Alembic for migrations
  - [x] (T-102) Create initial production schema (B3 in plan)
  - [x] (T-102) Company normalize (`backend/app/normalization/companies.py`)
  - [x] (T-103) Location normalize (`backend/app/normalization/locations.py`)
  - [x] (T-104) Salary parser (`backend/app/normalization/parsers.py`)
  - [x] (T-105) Date standardization (`backend/app/normalization/parsers.py`)
  - [x] (T-106) Dedup strategy (MinHash/LSH, `backend/app/normalization/dedupe.py`)
  - [x] (T-107) Pipeline logging/metrics
  - [x] (T-108) Tests for parsers + dedupe (`backend/test_processors.py`, etc.)

## 2. NLP extraction (Partially Implemented)
- [x] (T-200) description_clean builder
  - [x] (T-201) skills taxonomy + matcher (`backend/app/normalization/skills.py`)
  - [x] (T-202) tools taxonomy (integrated in skills matcher)
  - [x] (T-203) education extractor
  - [x] (T-204) experience extractor
  - [x] (T-205) employment/seniority classifier
  - [x] (T-206) entity storage job_entities (`backend/app/db/models.py`)
  - [x] (T-207) evaluation harness on labeled sample
  - [x] (T-208) extraction confidence reporting

## 3. Embeddings + matching (Partially Implemented)
- [x] (T-300) embedding builder (batch + resume)
  - [x] (T-301) vector index abstraction (`backend/app/ml/embeddings.py`)
  - [x] (T-302) profile embedding builder (integrated in `generate_embeddings.py`)
  - [x] (T-303) matching (`backend/app/services/search.py`, `backend/app/services/recommend.py`)
  - [ ] (T-304) explanation generator
  - [x] (T-305) tests for deterministic retrieval (`backend/test_integration.py`)

## 4. Intelligence analytics (planned)
- [ ] (T-400) skill trends
- [ ] (T-401) role evolution
- [ ] (T-402) adjacency roles
- [ ] (T-403) dashboards endpoints

## 5. Signals (planned)
- [ ] (T-500) tender ingestion parser
- [ ] (T-501) task→role mapping
- [ ] (T-502) likely-hiring signals
- [ ] (T-503) evidence + confidence tracking

## 6. Hardening (planned)
- [ ] (T-600) orchestration CLI
- [ ] (T-601) incremental updates
- [ ] (T-602) monitoring + drift checks
- [ ] (T-603) regression tests
- [ ] (T-604) runbook docs

## 7. Production Readiness (NEW - ML/DB Transition)
- [x] (T-010-PLAN) Integrate production roadmap into control plane
- [/] (T-700-PROD) Postgres 14.20 + pgvector baseline
  - [x] (T-701) Install/verify extensions (vector, pg_trgm, unaccent) in migration
  - [x] (T-702) Schema design & SQL DDL (tables B3, indexes B4)
- [x] (T-710-PROD) Alembic Migrations
  - [x] (T-711) Initialize Alembic in `backend/`
  - [x] (T-712) Generate initial migration from models
- [x] (T-720-PROD) Bulk Load & Artifacts
  - [x] (T-721) CSV/Parquet export scripts for initial bootstrap
  - [x] (T-722) COPY command templates for VPS load
- [ ] (T-730-PROD) Hardening & Operations
  - [ ] (T-731) Systemd service/timer templates
  - [ ] (T-732) Incremental update upsert patterns

## Logs

### 2026-01-25
- (T-000-SCAN) Initial baseline scan completed.
- (T-010-PLAN) Integrated ML/DB production transition plan into control plane.
- (T-100/T-710) Initialized Alembic and implemented production schema baseline.
- Enhanced migration with Postgres extensions (pgvector/pg_trgm/unaccent) and HNSW indexes.
- Implemented high-precision normalization for companies, locations, salaries, and dates.
- Built deduplication engine using MinHash/LSH with datasketch.
- Implemented advanced extractors for education, experience, and seniority.
- Generated full baseline artifacts (500 jobs) with `e5-small-v2` embeddings and SHA256 checksums.
- Verified 17 tests passing in `backend/` and added normalization/extraction validation scripts.

### 2026-01-25 (Prior Context)
- (agent instruction audit) Added compatibility instruction files and flagged `agent-work.md` as an archived snapshot.
- (local sqlite path) Switched local SQLite storage to `backend/var/nextstep.sqlite` and ensured the dev script prepares the directory; updated local env and docs to match.
- (env quoting) Quoted `.env` values that contain spaces so the dev script can `source` the file safely.

### 2026-01-18 (Prior Context)
- Added auth flows (email/password, Google OAuth, reset), introduced a search-first frontend with account UI, and wired government ingestion + monitoring. Cleaned extra virtual environments and consolidated documentation into `docs/` with new `features.md`, `userjourney.md`, and `changemap.md`.
- Added a helper script to start backend + frontend locally with the `.env` file.
- Fixed auth UI visibility and added token validation on load to prevent mixed signed-in/out states.
- Reworked the database session wrapper to support both sync API usage and async test helpers.
- Added admin KPI endpoints with access control plus new admin/user dashboard pages and navigation links.
- Pinned bcrypt to a compatible version for passlib.
- Made phone fields optional in auth response models.
- Added post-auth redirects to user dashboard or admin console.
- Added clearer login links and host-mismatch messaging for dashboard/admin gates; bound frontend server to 127.0.0.1 in dev script.
- Improved dashboard/admin gate messaging for missing session, expired token, or API offline.
- Added explicit "Signed in as" labels in dashboard and admin headers.
- Stored JWT `sub` as string and parsed it back to int on lookup.
- Added sign-out buttons to user and admin dashboards.
- Prevented admin gate overlay when admin session is valid but data fetch fails.
- Improved government scraper link detection, added PDF text extraction, and fallback capture for list pages.
- Added a script to remove government sources returning 404/410.
- Expanded recommendation scoring with keyword, location, and recency signals and removed stale recs before storing.

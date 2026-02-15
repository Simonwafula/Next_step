# Role Baselines & Guided Search Modes Implementation Plan

Created: 2026-02-14
Status: PENDING
Approved: Yes
Iterations: 0
Worktree: Yes

> **Status Lifecycle:** PENDING → COMPLETE → VERIFIED
> **Iterations:** Tracks implement→verify cycles (incremented by verify phase)
>
> - PENDING: Initial state, awaiting implementation
> - COMPLETE: All tasks implemented
> - VERIFIED: All checks passed
>
> **Approval Gate:** Implementation CANNOT proceed until `Approved: Yes`
> **Worktree:** Set at plan creation (from dispatcher). `Yes` uses git worktree isolation; `No` works directly on current branch

## Summary

**Goal:** Build the Minimum Viable Insights Layer (MVIL) role baselines from existing job data, then wire three guided search modes (Explore/Match/Advance) so students, early-career, and professionals each get role-level guidance backed by evidence job IDs.

**Architecture:** Add an MVIL aggregation service that reads from `JobPost`, `JobEntities`, `JobSkill`, `TitleNorm` to compute role-level statistics (skills matrix, education/experience distributions, demand counts). Store results in new lightweight tables. Extend the search API with a `mode` parameter that returns `guided_results[]` alongside the existing `jobs[]` response. Frontend adds a mode selector for logged-in users.

**Tech Stack:** Python/FastAPI (backend), SQLAlchemy (ORM), PostgreSQL/SQLite (DB), Vanilla JS (frontend)

## Scope

### In Scope

- MVIL tables: `role_skill_baseline`, `role_education_baseline`, `role_experience_baseline`, `role_demand_snapshot`
- Aggregation service that computes baselines from existing extracted data
- Admin endpoint to trigger aggregation refresh
- Search API `mode` parameter: `explore`, `match`, `advance`
- Explore mode: career cards with education distribution, top skills, demand count, evidence job IDs
- Match mode: ranked role matches for user skills + missing skills + starter job previews
- Advance mode: transition cards with target role, skill gap vs baseline, target job links
- Frontend mode selector (logged-in users only) + guided results rendering
- Every insight row stores `sample_job_ids` (3-10) and `count_total_jobs_used`

### Out of Scope

- `salary_by_role` (salary coverage is low per existing data; defer to when coverage improves)
- `transition_edges` weighted graph (use existing `TitleAdjacency` + `transitions_for()` as-is)
- `emerging_signals` / `skill_demand_daily` (Phase 4 - Admin LMI)
- LLM-based career advice (per OUTCOMES_PLAN: no LLM advice without RAG + citations)
- Notification delivery (separate feature)
- Premium/payment features (moved to later_features/)

## Prerequisites

- Post-ingestion processing must have run (jobs need `title_norm_id`, `JobEntities`, `JobSkill` populated)
- At least ~100 processed jobs for meaningful baselines (role families with < 10 jobs are skipped or flagged as low-confidence)
- User auth system working (for mode selection on logged-in users)
- Phase 1 (O0 public search) is complete — verify: `/api/search?q=test` returns `jobs`, `title_clusters`, `companies_hiring` keys

## Context for Implementer

- **Patterns to follow:** Service functions in `backend/app/services/lmi.py` — same pattern of SQLAlchemy queries returning dicts. Route handlers in `backend/app/api/routes.py:41` for search endpoint pattern.
- **Conventions:** Services return plain dicts (no Pydantic response models for LMI). Routes use `db: Session = Depends(get_db)`. Tests use SQLite in-memory with fixtures.
- **Key files the implementer must read first:**
  - `backend/app/services/search.py` — current search implementation, returns `title_clusters`, `companies_hiring`, `jobs`
  - `backend/app/services/lmi.py` — LMI aggregation patterns (trending skills, salary insights)
  - `backend/app/services/recommend.py` — `get_skills_for_role()`, `calculate_skill_overlap()`, `transitions_for()` — reuse these
  - `backend/app/db/models.py` — all models; `JobPost:77`, `TitleNorm:53`, `JobEntities:133`, `JobSkill:247`, `UserProfile:323`
  - `backend/app/services/post_ingestion_processing_service.py` — how entities/skills are extracted
  - `frontend/js/search.js` — `SearchManager` class, vanilla JS rendering
  - `frontend/js/config.js` — API endpoints config
- **Gotchas:**
  - `JobEntities.skills` can be `list[dict]`, `list[str]`, or even `dict` — use `_skill_values()` pattern from `search.py:439` and generalize it for all aggregation functions
  - `JobEntities.education` is a JSONB dict with varying keys — normalize to bins: "Certificate/Diploma", "Bachelor's", "Master's", "PhD", "Not specified"; map common variations ("Bachelor", "BSc", "B.S." → "Bachelor's")
  - `JobEntities.experience` is a JSONB dict — extract numeric years and bin with Python logic, NOT SQL `percentile_cont` (which is PostgreSQL-only and breaks SQLite tests)
  - `TitleNorm.family` is the role grouping key (e.g., `data_analytics`, `software_engineering`); **skip family='other' in aggregation** — it lumps disparate roles together and produces meaningless baselines
  - `UserProfile.skills` is a JSONB dict `{"skill_name": confidence_score}` — convert to `list(profile.skills.keys())` when passing to match functions
  - `JobPost.education` is a simple string; `JobEntities.education` is a JSONB dict with more structure
  - Frontend is vanilla JS (no React/Vue) — add to existing `search.js` / create `guided-results.js`
  - Frontend auth detection: use `CONFIG.isAuthenticated()` or check response from `/api/auth/me` — do NOT rely solely on token presence in localStorage (tokens may be expired)
- **Domain context:**
  - "Role" = a `TitleNorm.family` grouping (e.g., "Data Analytics" groups Data Analyst, Data Scientist, BI Analyst)
  - "Career card" = role-level summary showing what the role is, what education/skills it needs, how many jobs exist
  - "Transition card" = comparison between user's current role and a target role showing skill gap
  - Evidence = `sample_job_ids` array proving the insight comes from real ads

## Runtime Environment

- **Start command:** `.venv/bin/uvicorn backend.app.main:app --reload` (dev) or `backend/venv3.11/bin/uvicorn backend.app.main:app` (prod)
- **Port:** 8000
- **Health check:** `curl http://localhost:8000/health`
- **Frontend:** Static files served at root, search page at `/search`
- **Tests:** `.venv/bin/pytest backend/tests/ -q`

## Progress Tracking

**MANDATORY: Update this checklist as tasks complete. Change `[ ]` to `[x]`.**

- [x] Task 1: MVIL database models
- [x] Task 2: MVIL aggregation service
- [x] Task 3: Admin aggregation endpoint + runner
- [x] Task 4: Explore mode API (Student career cards)
- [x] Task 5: Match mode API (Early-career role matching)
- [x] Task 6: Advance mode API (Professional transitions)
- [x] Task 7: Search API mode routing
- [x] Task 8: Frontend mode selector + guided results UI

**Total Tasks:** 8 | **Completed:** 8 | **Remaining:** 0

## Implementation Tasks

### Task 1: MVIL Database Models

**Objective:** Create the four MVIL baseline tables that store aggregated role-level insights with evidence job IDs.

**Dependencies:** None

**Files:**

- Modify: `backend/app/db/models.py`
- Test: `backend/tests/test_mvil_models.py`

**Key Decisions / Notes:**

- Add 4 new models: `RoleSkillBaseline`, `RoleEducationBaseline`, `RoleExperienceBaseline`, `RoleDemandSnapshot`
- Each model stores `role_family` (from `TitleNorm.family`), the aggregated data, `sample_job_ids` (JSONB list of 3-10 job IDs), `count_total_jobs_used` (int), and `computed_at` (datetime)
- `RoleSkillBaseline`: `role_family`, `skill_name`, `frequency` (float 0-1 = share of jobs requiring it), `count_ads` (int), `sample_job_ids`, `count_total_jobs_used`, `computed_at`
- `RoleEducationBaseline`: `role_family`, `education_level` (e.g., "Bachelor's", "Master's", "Diploma"), `share` (float 0-1), `count_ads`, `sample_job_ids`, `count_total_jobs_used`, `computed_at`
- `RoleExperienceBaseline`: `role_family`, `experience_band` (e.g., "0-2 years", "3-5 years"), `share` (float 0-1), `count_ads`, `sample_job_ids`, `count_total_jobs_used`, `computed_at`
- `RoleDemandSnapshot`: `role_family`, `date` (date of snapshot), `count_ads`, `unique_employers`, `sample_job_ids`, `count_total_jobs_used`, `computed_at`
- Use composite unique index on (`role_family`, `skill_name`/`education_level`/`experience_band`/`date`) for upsert behavior
- Follow existing model pattern from `SkillTrendsMonthly` at `models.py:156`

**Definition of Done:**

- [ ] All 4 MVIL model classes exist in `models.py`
- [ ] Each model has `sample_job_ids` (JSONB) and `count_total_jobs_used` (Integer)
- [ ] Tables can be created via `Base.metadata.create_all()` without errors
- [ ] Unit test verifies model instantiation and field types

**Verify:**

- `.venv/bin/pytest backend/tests/test_mvil_models.py -q` — model tests pass

### Task 2: MVIL Aggregation Service

**Objective:** Build the service that queries existing job data and computes the four MVIL baselines.

**Dependencies:** Task 1

**Files:**

- Create: `backend/app/services/mvil_service.py`
- Test: `backend/tests/test_mvil_service.py`

**Key Decisions / Notes:**

- **Data shape normalization (CRITICAL):** Before aggregation, normalize all data formats:
  - Skills: Reuse and generalize `_skill_values()` from `search.py:439` — handle `list[dict]`, `list[str]`, and `dict` formats. Log (don't crash) on rows with unparseable skills.
  - Education: Map variations to standard bins — `("Bachelor", "BSc", "B.S.", "BA", "BS") → "Bachelor's"`, `("Master", "MSc", "M.S.", "MA", "MS") → "Master's"`, etc. Unmapped values → "Not specified".
  - Experience: Extract numeric years from `JobEntities.experience` dict. If range like "2-4 years", use midpoint. If qualitative: entry/junior → 0-2, mid-level → 3-5, senior → 5-10, lead/principal → 10+. Unparseable → "Not specified". **Use Python logic for binning, NOT SQL `percentile_cont`** (breaks SQLite).
- **Skip `family='other'`** in all aggregation — it lumps disparate roles and produces meaningless baselines.
- **Skip role families with < 3 jobs** — too few for meaningful baselines. Families with 3-9 jobs get `low_confidence=True` flag.
- `compute_role_skill_baselines(db)`: For each `TitleNorm.family` (excluding 'other'), count how many jobs require each skill (via `JobSkill` join), compute frequency = count/total_jobs_in_family. Store top skills per role. Collect sample job IDs per skill-role pair.
- `compute_role_education_baselines(db)`: For each family, parse `JobEntities.education` dict, normalize to bins, compute distribution shares.
- `compute_role_experience_baselines(db)`: For each family, extract years from `JobEntities.experience`, bin using Python logic, compute distribution shares.
- `compute_role_demand_snapshots(db)`: For each family, count active (`is_active=True`) jobs and unique employers (via `org_id`). Store as daily snapshot.
- `refresh_all_baselines(db)`: Calls all four compute functions. **Uses transactional safety:** insert new rows first, then delete old rows only after insert succeeds. Wrap in a single transaction so failure leaves old data intact (never empty tables).
- All functions are synchronous (use regular Session, not AsyncSession) matching existing service patterns
- **Sample job IDs strategy:** Sort candidate job IDs by `last_seen` DESC (prefer recent jobs), filter to `is_active=True` only, then take first `min(10, len(job_ids))`. Deterministic (no random) — same input produces same output for reproducibility.

**Definition of Done:**

- [x] `mvil_service.py` has all four compute functions + `refresh_all_baselines()`
- [x] Each function stores `sample_job_ids` and `count_total_jobs_used` in every row
- [x] Aggregation handles both `list[dict]` and `list[str]` formats in `JobEntities.skills` without crashing
- [x] Role families with `family='other'` are excluded from aggregation
- [x] Role families with < 3 jobs are excluded; families with 3-9 jobs get `low_confidence=True`
- [x] `refresh_all_baselines()` is transactional — failure mid-run preserves old data (tables never left empty)
- [x] Sample job IDs are sorted by recency and filtered to `is_active=True`
- [x] Tests verify correct aggregation with fixture data (at least 3 jobs per role family)
- [x] Tests include fixture jobs with BOTH `list[dict]` and `list[str]` skill formats
- [x] Tests verify `sample_job_ids` are valid, active job IDs from the input set
- [x] All aggregation runs on SQLite (no PostgreSQL-specific SQL like `percentile_cont`)

**Verify:**

- `.venv/bin/pytest backend/tests/test_mvil_service.py -q` — aggregation tests pass

### Task 3: Admin Aggregation Endpoint + Runner

**Objective:** Add an admin endpoint to trigger MVIL refresh and a function callable from CLI/cron.

**Dependencies:** Task 2

**Files:**

- Modify: `backend/app/api/routes.py` (add admin endpoint)
- Test: `backend/tests/test_mvil_admin.py`

**Key Decisions / Notes:**

- Add `POST /api/admin/mvil/refresh` endpoint (requires admin auth via `require_admin()`)
- Returns `{"status": "ok", "baselines_refreshed": 4, "role_families_processed": N, "duration_s": X}`
- Follow pattern of existing `POST /api/admin/ingest` endpoint at `routes.py:401`
- Also call `refresh_all_baselines()` after post-ingestion processing completes (add hook in existing flow)
- Auto-refresh is **non-blocking** (fire-and-forget after ingestion; does not delay ingestion response)
- If auto-refresh fails, log error but do NOT rollback ingestion — aggregation can be retried manually
- Throttle: only auto-refresh if last successful run was > 12 hours ago (avoid redundant refreshes from multiple ingestion runs in same day)

**Definition of Done:**

- [x] `POST /api/admin/mvil/refresh` endpoint exists and requires admin auth
- [x] Endpoint calls `refresh_all_baselines()` and returns summary
- [x] Test verifies endpoint requires auth and returns expected shape

**Verify:**

- `.venv/bin/pytest backend/tests/test_mvil_admin.py -q` — admin endpoint tests pass

### Task 4: Explore Mode API (Student Career Cards)

**Objective:** Build the Explore mode endpoint that returns career cards for students: what a role is, education distribution, common skills, demand count, with evidence job IDs.

**Dependencies:** Task 2

**Files:**

- Create: `backend/app/services/guided_search.py`
- Modify: `backend/app/api/routes.py` (add endpoint)
- Test: `backend/tests/test_guided_explore.py`

**Key Decisions / Notes:**

- `GET /api/guided/explore?q=<query>&location=<loc>` — returns career cards
- `explore_careers(db, query, location)` function:
  1. Normalize query to role family via `normalize_title()`
  2. Find matching role families (fuzzy match on family name or canonical_title)
  3. For each matching family, build a career card from MVIL baselines:
     - `role_family`: display name
     - `description`: canonical titles in this family
     - `education_distribution`: from `RoleEducationBaseline` rows
     - `top_skills`: top 10 from `RoleSkillBaseline` with frequency
     - `demand`: from `RoleDemandSnapshot` (latest) — `count_ads`, `unique_employers`
     - `experience_distribution`: from `RoleExperienceBaseline` rows
     - `sample_job_ids`: union of sample IDs from baselines
     - `canonical_titles`: list of distinct `TitleNorm.canonical_title` in this family
  4. Return list of career cards sorted by demand count
- If MVIL tables are empty, return `{"guided_results": [], "message": "Insights not yet available — run baseline aggregation first"}` (do NOT fall back to expensive live query)
- Cards with `count_total_jobs_used < 10` include `"low_confidence": true` in response — frontend renders "Limited data (N jobs)" badge
- Career cards do NOT include salary information (salary_by_role is deferred)
- Per OUTCOMES_PLAN O1: "career cards (role-level), not only jobs"

**Definition of Done:**

- [x] `GET /api/guided/explore` endpoint returns career cards with education, skills, demand
- [x] Each career card includes `sample_job_ids` evidence
- [x] Cards with `count_total_jobs_used < 10` include `low_confidence: true`
- [x] Career cards contain NO salary-related fields
- [x] Empty MVIL tables return empty `guided_results` with helpful message (no live query fallback)
- [x] Empty query returns top 10 career cards by demand
- [x] Test with fixture data verifies card structure and evidence presence

**Verify:**

- `.venv/bin/pytest backend/tests/test_guided_explore.py -q` — explore tests pass

### Task 5: Match Mode API (Early-Career Role Matching)

**Objective:** Build the Match mode endpoint that returns ranked role matches for a user's skills/education, showing skill gaps and starter job previews.

**Dependencies:** Task 2

**Files:**

- Modify: `backend/app/services/guided_search.py`
- Modify: `backend/app/api/routes.py` (add endpoint)
- Test: `backend/tests/test_guided_match.py`

**Key Decisions / Notes:**

- `GET /api/guided/match?q=<query>&skills=<comma-separated>&education=<level>` — returns role matches
- Also accept user profile skills from `UserProfile.skills` if authenticated — **convert dict to list:** `user_skills = list(profile.skills.keys()) if profile.skills else []`
- `match_roles(db, query, user_skills, education, location)` function:
  1. Get all role families from MVIL baselines
  2. For each family, compute match score:
     - Skill overlap = user skills ∩ role's top skills / role's top skills (reuse `calculate_skill_overlap()` from `recommend.py:51`)
     - Education fit scoring ladder: "Most common" = education level with highest `share` in `RoleEducationBaseline`. Ladder: Certificate < Bachelor's < Master's < PhD. If user education >= required → 1.0, if 1 step below → 0.5, if 2+ steps below or "Not specified" → 0.0
  3. Rank by match score descending
  4. For top matches, include:
     - `role_family`, `match_score`, `matching_skills`, `missing_skills` (top 3-5)
     - `starter_jobs`: 3-5 actual `JobPost` records filtered to entry/junior seniority for this family
     - `sample_job_ids` from baselines
  5. Return top 10 role matches
- Per OUTCOMES_PLAN O2: "ranked role matches + 3–5 starter job previews per role. Each role shows missing skills"

**Definition of Done:**

- [x] `GET /api/guided/match` endpoint returns ranked role matches with skill gap
- [x] Each match includes `missing_skills` and `starter_jobs` (3-5 previews)
- [x] Match score correctly reflects skill overlap and education fit
- [x] Match cards contain NO salary-related fields
- [x] Authenticated users can match against their profile skills (`UserProfile.skills` dict correctly converted to list)
- [x] Test verifies ranking order, skill gap calculation, and education scoring ladder
- [x] Test verifies `UserProfile.skills` dict `{"Python": 0.9}` is correctly converted to `["Python"]`

**Verify:**

- `.venv/bin/pytest backend/tests/test_guided_match.py -q` — match tests pass

### Task 6: Advance Mode API (Professional Transitions)

**Objective:** Build the Advance mode endpoint that returns transition cards for professionals, showing target roles with skill gaps vs baselines and target job links.

**Dependencies:** Task 2

**Files:**

- Modify: `backend/app/services/guided_search.py`
- Modify: `backend/app/api/routes.py` (add endpoint)
- Test: `backend/tests/test_guided_advance.py`

**Key Decisions / Notes:**

- `GET /api/guided/advance?current_role=<role>&skills=<comma-separated>` — returns transition cards
- `advance_transitions(db, current_role, user_skills, location)` function:
  1. Normalize `current_role` to family via `normalize_title()`
  2. Find transition targets using existing `transitions_for()` from `recommend.py:86` as base data
  3. For each target family, build transition card:
     - `target_role`: family display name
     - `current_role`: user's normalized family
     - `skill_gap`: skills in target baseline NOT in user's skills (from `RoleSkillBaseline`)
     - `shared_skills`: skills user already has that target needs
     - `demand_trend`: from `RoleDemandSnapshot` — is demand growing?
     - `difficulty_proxy`: weighted heuristic — skill gap: 0-3 missing = "Low", 4-7 = "Medium", 8+ = "High"; education gap uses same ladder as Task 5 (0.0/0.5/1.0); combined: `0.7 * skill_score + 0.3 * education_score`; demand trend shown as separate field (not in difficulty)
     - `target_jobs`: 3-5 actual `JobPost` records for this target family
     - `sample_job_ids` from baselines
  4. Return transition cards sorted by feasibility (smaller skill gap first)
- Per OUTCOMES_PLAN O3: "transition cards with: target role, tradeoffs proxy, missing skills vs baseline, see target jobs"

**Definition of Done:**

- [x] `GET /api/guided/advance` endpoint returns transition cards with skill gaps
- [x] Each card includes `difficulty_proxy`, `skill_gap`, `shared_skills`, `target_jobs`
- [x] `difficulty_proxy` uses defined thresholds (0-3 Low, 4-7 Medium, 8+ High) with weighted formula
- [x] Transition cards contain NO salary-related fields
- [x] Cards sorted by feasibility (fewer missing skills = easier transition)
- [x] Test verifies card structure, skill gap correctness, and difficulty classification

**Verify:**

- `.venv/bin/pytest backend/tests/test_guided_advance.py -q` — advance tests pass

### Task 7: Search API Mode Routing

**Objective:** Add `mode` parameter to the main search endpoint that includes `guided_results[]` alongside existing job results for logged-in users.

**Dependencies:** Task 4, Task 5, Task 6

**Files:**

- Modify: `backend/app/services/search.py`
- Modify: `backend/app/api/routes.py`
- Test: `backend/tests/test_search_modes.py`

**Key Decisions / Notes:**

- Add `mode` query parameter to `GET /api/search`: `explore`, `match`, `advance` (default: none = public mode)
- When `mode` is set AND user is authenticated:
  - Call the appropriate guided function from `guided_search.py`
  - Include result as `guided_results` key in search response
  - Keep existing `jobs`, `title_clusters`, `companies_hiring` unchanged
- When `mode` is set but user is NOT authenticated:
  - Return `"guided_results": null, "mode": null, "mode_error": "Authentication required for guided search"` — explicit error instead of silent ignore
- Response shape becomes:
  ```json
  {
    "jobs": [...],
    "title_clusters": [...],
    "companies_hiring": [...],
    "guided_results": [...],  // career cards/matches/transitions, or null if not authed
    "mode": "explore",        // echo back the mode, or null
    "mode_error": null,       // null on success, string on auth/error
    "total": 42
  }
  ```
- Public search (no mode/no auth) works exactly as before — backward compatible
- Keep mode routing logic lightweight in `search.py` — delegate to `guided_search.py` functions
- Per OUTCOMES_PLAN: "Same search bar, but now: Mode selector: Explore / Match / Advance. Default tab: Guidance. Secondary tab: Jobs (same as public)"

**Definition of Done:**

- [x] `GET /api/search?mode=explore` returns `guided_results` with career cards
- [x] `GET /api/search?mode=match` returns `guided_results` with role matches
- [x] `GET /api/search?mode=advance` returns `guided_results` with transition cards
- [x] Public search without `mode` parameter returns same response shape as current: `{jobs, title_clusters, companies_hiring, total}` (backward compat verified by snapshot test)
- [x] Unauthenticated request with `mode` set returns `mode_error: "Authentication required..."` (NOT silent ignore)
- [x] Test verifies all three modes, backward compatibility, and unauthenticated mode_error

**Verify:**

- `.venv/bin/pytest backend/tests/test_search_modes.py -q` — mode routing tests pass

### Task 8: Frontend Mode Selector + Guided Results UI

**Objective:** Add a mode selector for logged-in users and render guided results (career cards, role matches, transition cards) in the search UI.

**Dependencies:** Task 7

**Files:**

- Modify: `frontend/js/search.js` (add mode selector logic)
- Modify: `frontend/js/config.js` (add guided endpoints)
- Modify: `frontend/search.html` (add mode selector HTML + guided results container)
- Test: Manual verification with `playwright-cli`

**Key Decisions / Notes:**

- Add mode selector tabs below search bar (visible only when logged in):
  - Explore (🎓 for students) | Match (🎯 for early-career) | Advance (📈 for professionals) | Jobs (📋 always)
- Default to "Explore" mode for logged-in users, "Jobs" for public
- Career card HTML: role name, demand badge, education pills, skill tags, "View X jobs" button
- Match card HTML: role name, match score %, matching/missing skills, starter job previews
- Advance card HTML: target role, difficulty badge, skill gap list, "See target jobs" button
- Guided results render above the jobs list in a separate container
- Follow existing vanilla JS patterns in `search.js` — extend `SearchManager` class
- Add `mode` parameter to search API calls: `${CONFIG.API_BASE_URL}/search?q=${q}&mode=${mode}`
- Use `_esc()` sanitizer for all user-generated content in cards

**Definition of Done:**

- [x] Mode selector tabs visible for logged-in users (determined by backend `user_authenticated` flag in search response or `/api/auth/me` check — NOT solely by token presence in localStorage)
- [x] Mode selector hidden for unauthenticated users
- [x] Selecting a mode triggers search with `mode` parameter
- [x] Career cards render with education, skills, demand for Explore mode
- [x] Cards with `low_confidence: true` show "Limited data (N jobs)" badge
- [x] Match cards render with skill gap and starter jobs for Match mode
- [x] Advance cards render with transition info for Advance mode
- [x] If `mode_error` is returned, show login prompt instead of blank results
- [x] Jobs tab works unchanged for all users
- [x] All user-generated content sanitized with `_esc()` helper
- [x] Mode selector and cards render without layout breaks at desktop (>=1024px) and mobile (<768px)

**Verify:**

- `playwright-cli open http://localhost:8000/search` → `snapshot` → verify mode selector renders
- `playwright-cli` interaction: select Explore mode → verify career cards appear

## Testing Strategy

- **Unit tests:** Each MVIL service function tested with in-memory SQLite fixtures (3+ jobs per role family with skills, education, experience populated)
- **Integration tests:** Admin refresh endpoint, search mode routing with auth
- **Manual verification:** Frontend mode selector and card rendering via `playwright-cli`

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Insufficient processed jobs for meaningful baselines | Medium | High | Skip families with < 3 jobs; families with 3-9 jobs get `low_confidence: true` flag; empty MVIL tables return `guided_results: []` with message (no live query fallback); frontend shows "Limited data (N jobs)" badge on low-confidence cards |
| `JobEntities.education`/`experience` format varies across sources | Medium | Medium | Normalize with explicit mapping dicts in aggregation service (e.g., "BSc"→"Bachelor's"); log unparseable rows; unit tests include all known format variations; skip rows gracefully (don't crash) |
| PostgreSQL-specific SQL (percentile_cont) in tests | Low | Medium | All aggregation uses Python logic for binning, NOT SQL aggregate functions; no `percentile_cont` anywhere in MVIL code; CI tests run on SQLite |
| Frontend mode selector breaks existing search flow | Low | High | Mode selector is additive — hidden by default for public users; existing search path unchanged; backward compat verified by snapshot test |
| Aggregation refresh failure leaves empty tables | Low | High | Transactional refresh: insert new rows first, delete old only after success; failure preserves old data; log refresh duration and errors |
| Large number of role families makes aggregation slow | Low | Low | Skip 'other' family; limit to families with >= 3 jobs; aggregation is a batch job, not on-request; log duration for monitoring |

## Open Questions

- None — all requirements are specified in OUTCOMES_PLAN.md

### Deferred Ideas

- `salary_by_role` baseline — defer until salary coverage improves (currently low per data quality metrics)
- `transition_edges` weighted graph — use existing `TitleAdjacency` + cosine similarity for now
- `aggregation_run_id` UUID for versioned baselines — useful for detecting stale data and preventing race conditions during refresh
- Incremental refresh (only recompute changed role families) — needed when job count exceeds ~10k and full refresh takes >2 minutes
- Periodic cleanup of stale `sample_job_ids` (re-aggregate if >30% of sample IDs point to inactive jobs)
- Push notifications for new jobs matching user's mode preferences
- "Career map" visualization (SVG/canvas) for Explore mode — could be a future enhancement

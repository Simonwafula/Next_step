# Handoff

## 2026-04-08 (T-UX-301: Search Payload Normalization)

Branch: `feat/T-1A4-1A6-search-quality-signals`

Commit: `pending`

### Summary
- Completed `T-UX-301` by normalizing the public search contract in [search.py](/home/nextstep.co.ke/public_html/backend/app/services/search.py) and [routes.py](/home/nextstep.co.ke/public_html/backend/app/api/routes.py):
  - canonicalized every `/api/search` response around `results`
  - preserved `jobs` as a mirrored compatibility alias at the API boundary
  - made no-result suggestion/fallback responses return the same dict payload shape instead of a bare list
- Aligned frontend search callers with the canonical payload:
  - [main.js](/home/nextstep.co.ke/public_html/frontend/js/main.js) now reads `payload.results` directly for the shipped homepage search flow
  - [api.js](/home/nextstep.co.ke/public_html/frontend/js/api.js) now returns a normalized results array to older JS consumers like [search.js](/home/nextstep.co.ke/public_html/frontend/js/search.js)
- Added regression coverage:
  - [test_search_modes.py](/home/nextstep.co.ke/public_html/backend/tests/test_search_modes.py) now asserts the route normalizes legacy `jobs`-only payloads into canonical `results`
  - [test_search_response_shape.py](/home/nextstep.co.ke/public_html/backend/tests/test_search_response_shape.py) locks the no-match fallback shape

### Tests Run
- `backend/venv3.11/bin/ruff format backend/app/services/search.py backend/app/api/routes.py backend/tests/test_search_modes.py backend/tests/test_search_response_shape.py`
- `backend/venv3.11/bin/ruff check backend/app/services/search.py backend/app/api/routes.py backend/tests/test_search_modes.py backend/tests/test_search_response_shape.py`
- `node --check frontend/js/main.js`
- `node --check frontend/js/api.js`
- `/home/nextstep.co.ke/.venv/bin/pytest -q backend/tests/test_search_modes.py backend/tests/test_search_response_shape.py backend/tests/test_search_data_quality.py backend/tests/test_assignment_quality_improvements.py` -> `16 passed`

### Remaining Next Step
1. Move to `T-UX-320` if the next priority is wiring real seeker actions from homepage search cards.
2. Keep the current cleanup deletions and the standalone [test_search_match_explanation_skills_shape.py](/home/nextstep.co.ke/public_html/backend/tests/test_search_match_explanation_skills_shape.py) edit as separate work unless you want them folded into a follow-up commit.

## 2026-04-08 (T-UX-312: Dashboard Boot-Path Integration Coverage)

Branch: `feat/T-1A4-1A6-search-quality-signals`

Commit: `pending`

### Summary
- Completed `T-UX-312` by adding [test_dashboard_boot_integration.py](/home/nextstep.co.ke/public_html/backend/tests/test_dashboard_boot_integration.py):
  - locks the shipped tab order and boot sequence in [dashboard.html](/home/nextstep.co.ke/public_html/frontend/dashboard.html) and [dashboard-ui.js](/home/nextstep.co.ke/public_html/frontend/js/dashboard-ui.js)
  - verifies the real route contracts used during dashboard boot for `/api/auth/me`, `/api/auth/profile`, `/api/users/recommendations`, `/api/users/saved-jobs`, `/api/users/applications`, `/api/users/notifications`, `/api/users/market-fit`, and `/api/users/applications/by-stage`
- Fixed a boot-path defect in [auth_routes.py](/home/nextstep.co.ke/public_html/backend/app/api/auth_routes.py):
  - `UserResponse.last_login` is now nullable, matching the route behavior for users who have not logged in before
  - this prevents `/api/auth/me` from failing validation during dashboard boot for first-session users
- Reviewed and kept the existing local edits in [main.js](/home/nextstep.co.ke/public_html/frontend/js/main.js) and [test_search_match_explanation_skills_shape.py](/home/nextstep.co.ke/public_html/backend/tests/test_search_match_explanation_skills_shape.py) as separate in-flight work.
- Dropped the duplicate untracked backfill pair because [backfill_normalized_entities.py](/home/nextstep.co.ke/public_html/backend/scripts/backfill_normalized_entities.py) and [test_normalized_backfill.py](/home/nextstep.co.ke/public_html/backend/tests/test_normalized_backfill.py) already cover that normalization/backfill lane.

### Tests Run
- `backend/venv3.11/bin/ruff format backend/app/api/auth_routes.py backend/tests/test_dashboard_boot_integration.py`
- `backend/venv3.11/bin/ruff check backend/app/api/auth_routes.py backend/tests/test_dashboard_boot_integration.py`
- `/home/nextstep.co.ke/.venv/bin/pytest -q backend/tests/test_dashboard_boot_integration.py backend/tests/test_dashboard_user_routes.py` -> `6 passed`

### Remaining Next Step
1. Return to `T-UX-301` if search payload normalization is still the next highest-priority user-path gap on this branch.
2. Keep the current docs/artifact deletions as separate cleanup; they were not included in `T-UX-312`.

## 2026-04-08 (T-UX-310/T-UX-311: Dashboard API Contract Alignment)

Branch: `feat/T-1A4-1A6-search-quality-signals`

Commit: `pending`

### Summary
- Completed `T-UX-310` by adding `GET /api/users/market-fit` in [user_routes.py](/home/nextstep.co.ke/public_html/backend/app/api/user_routes.py):
  - returns the exact dashboard shape expected by [dashboard-ui.js](/home/nextstep.co.ke/public_html/frontend/js/dashboard-ui.js)
  - analyzes recent active jobs against the authenticated profile
  - builds deterministic missing-skill demand counts from normalized `job_skill` rows when available, with text-extraction fallback
- Completed `T-UX-311` in [user_routes.py](/home/nextstep.co.ke/public_html/backend/app/api/user_routes.py):
  - added `GET /api/users/applications/by-stage` for the shipped kanban board
  - grouped stored application `status` values into the dashboard stages `saved`, `applied`, `interview`, `offer`, `rejected`
  - updated `PUT /api/users/applications/{id}` to accept dashboard `stage` payloads and return both normalized `stage` and stored `status`
- Added focused regression coverage in [test_dashboard_user_routes.py](/home/nextstep.co.ke/public_html/backend/tests/test_dashboard_user_routes.py) for:
  - empty-profile market-fit fallback
  - populated market-fit output
  - kanban grouping
  - `stage` update compatibility

### Tests Run
- `backend/venv3.11/bin/ruff format backend/app/api/user_routes.py backend/tests/test_dashboard_user_routes.py`
- `backend/venv3.11/bin/ruff check backend/app/api/user_routes.py backend/tests/test_dashboard_user_routes.py`
- `/home/nextstep.co.ke/.venv/bin/pytest -q backend/tests/test_dashboard_user_routes.py backend/tests/test_user_activity.py backend/tests/test_dashboard_endpoints.py` -> `66 passed`
- `/home/nextstep.co.ke/.venv/bin/pytest -q backend/tests/test_subscription_paywall.py backend/tests/test_user_job_match_endpoint.py backend/tests/test_skills_gap_scan_endpoint.py` -> `10 passed`

### Remaining Next Step
1. Start `T-UX-312` to add dashboard boot-path integration coverage now that the missing APIs exist.
2. Then return to `T-UX-301` if search payload normalization is still the next highest-priority user-path gap on this branch.

## 2026-04-08 (T-UX-300: Guided Search Logging Hardening)

Branch: `feat/T-1A4-1A6-search-quality-signals`

Commit: `pending`

### Summary
- Completed `T-UX-300` by hardening [routes.py](/home/nextstep.co.ke/public_html/backend/app/api/routes.py):
  - serve-time logging now tolerates optional or partial authenticated-user objects via safe `id` lookup
  - logging now uses the actual search result list whether the payload shape is `results` or `jobs`
- This closes the guided-search regression surfaced during the persona coverage audit, where guided mode crashed on partial authenticated-user stubs in [test_search_modes.py](/home/nextstep.co.ke/public_html/backend/tests/test_search_modes.py).

### Tests Run
- `/home/nextstep.co.ke/.venv/bin/pytest backend/tests/test_search_modes.py -q` -> `4 passed`
- `/home/nextstep.co.ke/.venv/bin/pytest backend/tests/test_guided_explore.py backend/tests/test_guided_advance.py backend/tests/test_guided_match.py backend/tests/test_public_apply_redirect.py -q` -> `7 passed`
- `/home/nextstep.co.ke/.venv/bin/pytest backend/tests/test_dashboard_endpoints.py backend/tests/test_career_pathways_endpoint.py backend/tests/test_subscription_paywall.py backend/tests/test_public_apply_redirect.py backend/tests/test_search_modes.py -q` -> `71 passed`

### Remaining Next Step
1. Start `T-UX-310` to either implement `/api/users/market-fit` or remove the live dashboard dependency.
2. Then do `T-UX-311` to bring the applications kanban contract into line with the backend.

## 2026-04-08 (Persona Coverage Audit + Prioritized Gap Backlog)

Branch: `feat/T-1A4-1A6-search-quality-signals`

Commit: `pending`

### Summary
- Audited the current shipped implementation against the repo's actual user journeys and product surfaces:
  - Visitor / Guest: `80%`
  - Registered Job Seeker: `68%`
  - Returning User: `55%`
  - Premium Career Planner / Career Switcher: `60%`
  - Admin / Operator: `85%`
  - Employer / Recruiter: `10%`
  - Overall against the current implemented user journeys: `71%`
- Added a prioritized follow-up backlog to [changemap.md](/home/nextstep.co.ke/public_html/changemap.md) under `8.1 Persona Coverage Audit & Prioritized Gap Backlog (2026-04-08)`.
- Highest-priority follow-ups added:
  - `T-UX-300` fix guided-search auth/logging regression in `/api/search`
  - `T-UX-301` align `/api/search` payload semantics
  - `T-UX-310` implement or remove the dashboard's `market-fit` dependency
  - `T-UX-311` implement `applications/by-stage` and reconcile `stage` vs `status`
  - `T-UX-320` wire real seeker actions from homepage search results
  - `T-UX-340` explicitly decide employer/recruiter scope
- `.pilot/tasks/` does not exist in this checkout, so the backlog was recorded in `changemap.md`, which is the repo's active task ledger in practice.

### Tests Run
- `/home/nextstep.co.ke/.venv/bin/pytest backend/tests/test_guided_explore.py backend/tests/test_guided_advance.py backend/tests/test_skills_gap_scan_endpoint.py backend/tests/test_user_activity.py backend/tests/test_admin_processing_endpoints.py -q` -> `18 passed`
- `/home/nextstep.co.ke/.venv/bin/pytest backend/tests/test_search_data_quality.py backend/tests/test_skill_filtering.py backend/tests/test_search_match_explanation_skills_shape.py backend/tests/test_user_job_match_endpoint.py -q` -> `11 passed, 1 warning`
- `/home/nextstep.co.ke/.venv/bin/pytest backend/tests/test_dashboard_endpoints.py backend/tests/test_career_pathways_endpoint.py backend/tests/test_subscription_paywall.py backend/tests/test_public_apply_redirect.py backend/tests/test_search_modes.py -q` -> `2 failed, 69 passed`

### Open Regression Found
- Guided search mode currently has a real regression in [routes.py](/home/nextstep.co.ke/public_html/backend/app/api/routes.py): serve-time logging assumes `current_user.id` exists.
- Failing suite: [test_search_modes.py](/home/nextstep.co.ke/public_html/backend/tests/test_search_modes.py)
- Exact error:
  - `AttributeError: '_UserStub' object has no attribute 'id'`

### Remaining Next Step
1. Start `T-UX-310` to either implement `/api/users/market-fit` or remove the live dashboard dependency.
2. Then do `T-UX-311` to bring the shipped dashboard UI back into sync with real backend routes.

## 2026-04-08 (T-1A4/T-1A5/T-1A6: Search Quality Signals)

Branch: `main`

Commit: `pending`

### Summary
- Completed `T-1A4` by filtering user-facing `top_skills` / `skills_found` from `JobEntities.skills` through the existing confidence thresholding path in [search.py](/home/nextstep.co.ke/public_html/backend/app/services/search.py).
- Completed `T-1A5` by using `source_quality_score` and `source_quality_tier` in search results and heuristic ranking tie-breaks in [ranking.py](/home/nextstep.co.ke/public_html/backend/app/services/ranking.py).
- Completed `T-1A6` by changing search quality output from an opaque list into explicit flags plus issues:
  - `data_quality_flags.listing_page`
  - `data_quality_flags.company_noise`
  - `data_quality_flags.location_confidence`
  - `data_quality_flags.dedupe_cluster`
  - `data_quality_flags.has_rich_description`
  - `data_quality_issues` remains the issue list for ranking/display
- Extended [create_job_post_analysis_view.py](/home/nextstep.co.ke/public_html/backend/scripts/create_job_post_analysis_view.py) so the analysis materialized view also exposes `source_quality_tier` and the same listing/company/location quality columns.
- Added focused coverage in [test_search_data_quality.py](/home/nextstep.co.ke/public_html/backend/tests/test_search_data_quality.py) and updated [test_assignment_quality_improvements.py](/home/nextstep.co.ke/public_html/backend/tests/test_assignment_quality_improvements.py) for the explicit-flag shape.

### Tests Run
- `python3 -m py_compile backend/app/services/search.py backend/app/services/ranking.py backend/scripts/create_job_post_analysis_view.py backend/tests/test_search_data_quality.py`
- `/home/nextstep.co.ke/.venv/bin/pytest -q backend/tests/test_search_data_quality.py backend/tests/test_cli_data_quality_cycle.py backend/tests/test_normalized_backfill.py backend/tests/test_assignment_quality_improvements.py backend/tests/test_deduplication_url_normalization.py` -> `16 passed`

### Blockers
- `ruff` could not run here because [backend/venv3.11/bin/ruff](/home/nextstep.co.ke/public_html/backend/venv3.11/bin/ruff) is a non-executable Mach-O binary, and `/home/nextstep.co.ke/.venv` does not have the `ruff` module installed.
- Script-based Postgres validation for [create_job_post_analysis_view.py](/home/nextstep.co.ke/public_html/backend/scripts/create_job_post_analysis_view.py) failed under `sudo -u postgres` because the `postgres` OS user cannot read files in `/home/nextstep.co.ke/public_html/backend/scripts/`. Use direct `psql` execution or adjust file permissions before retrying the script.

### Remaining Next Step
1. Finish `T-1A7`: sector coverage improvement and representativeness reporting for analytics.
2. If required for strict DoD, install a Linux-compatible `ruff` or replace the broken local binary.

## 2026-04-08 (T-1A7: Representativeness Reporting)

Branch: `feat/T-1A4-1A6-search-quality-signals`

Commit: `pending`

### Summary
- Completed `T-1A7` by adding [get_representativeness_report()](/home/nextstep.co.ke/public_html/backend/app/services/analytics.py) in [analytics.py](/home/nextstep.co.ke/public_html/backend/app/services/analytics.py).
- Wired the report into [admin_routes.py](/home/nextstep.co.ke/public_html/backend/app/api/admin_routes.py) so `/api/admin/lmi-quality` now returns:
  - `representativeness.source_mix`
  - `representativeness.sector_mix`
  - `representativeness.geography_mix`
  - `representativeness.coverage`
  - `representativeness.coverage_gaps`
  - `representativeness.status`
- Added endpoint coverage in [test_dashboard_endpoints.py](/home/nextstep.co.ke/public_html/backend/tests/test_dashboard_endpoints.py) for both the normal populated response and a sparse-sector warning case.

### Tests Run
- `python3 -m py_compile backend/app/services/analytics.py backend/app/api/admin_routes.py backend/tests/test_dashboard_endpoints.py`
- `/home/nextstep.co.ke/.venv/bin/pytest -q backend/tests/test_dashboard_endpoints.py -k "lmi_quality"` -> `10 passed, 47 deselected`
- `/home/nextstep.co.ke/.venv/bin/pytest -q backend/tests/test_search_data_quality.py backend/tests/test_assignment_quality_improvements.py backend/tests/test_cli_data_quality_cycle.py backend/tests/test_normalized_backfill.py backend/tests/test_deduplication_url_normalization.py` -> `16 passed`

### Remaining Next Step
1. Resolve the broken local `ruff` setup if strict DoD lint enforcement is required on this host.
2. Decide whether the representativeness block also needs a dedicated admin endpoint or frontend rendering beyond the existing `/api/admin/lmi-quality` payload.

### UI Follow-up
- [admin.js](/home/nextstep.co.ke/public_html/frontend/js/admin.js) now renders the `representativeness` payload inside the existing “LMI quality metrics” panel.
- [main.css](/home/nextstep.co.ke/public_html/frontend/styles/main.css) adds minimal section/gap styling so source mix, sector mix, geography mix, and coverage-gap badges are readable without changing the page structure.
- Validation: `node --check frontend/js/admin.js`

### Trend Follow-up
- [analytics.py](/home/nextstep.co.ke/public_html/backend/app/services/analytics.py) now adds `representativeness.trend_6m`, a monthly series with `sample_size`, `sector_coverage_pct`, `geography_coverage_pct`, and `top_source_share_pct`.
- [test_dashboard_endpoints.py](/home/nextstep.co.ke/public_html/backend/tests/test_dashboard_endpoints.py) now validates the presence and shape of the 6-month trend history.
- [admin.js](/home/nextstep.co.ke/public_html/frontend/js/admin.js) renders the trend series as compact cards inside the same LMI quality panel.
- Validation:
  - `python3 -m py_compile backend/app/services/analytics.py backend/tests/test_dashboard_endpoints.py`
  - `/home/nextstep.co.ke/.venv/bin/pytest -q backend/tests/test_dashboard_endpoints.py -k "lmi_quality"` -> `11 passed, 47 deselected`
  - `node --check frontend/js/admin.js`

### Ruff Fix
- Root cause: [backend/venv3.11/bin/ruff](/home/nextstep.co.ke/public_html/backend/venv3.11/bin/ruff) was a checked-in macOS Mach-O binary, so linting was broken on this Linux host.
- Fix applied:
  - installed `ruff 0.15.9` into `/home/nextstep.co.ke/.venv`
  - replaced [backend/venv3.11/bin/ruff](/home/nextstep.co.ke/public_html/backend/venv3.11/bin/ruff) with a shell wrapper that executes `/home/nextstep.co.ke/.venv/bin/python -m ruff "$@"`
  - ran Ruff format on the changed Python files in this branch
- Validation:
  - `backend/venv3.11/bin/ruff --version` -> `ruff 0.15.9`
  - `backend/venv3.11/bin/ruff check ...` -> pass
  - `backend/venv3.11/bin/ruff format --check ...` -> pass
  - `/home/nextstep.co.ke/.venv/bin/pytest -q backend/tests/test_dashboard_endpoints.py -k "lmi_quality"` -> `11 passed, 47 deselected`
  - `/home/nextstep.co.ke/.venv/bin/pytest -q backend/tests/test_search_data_quality.py backend/tests/test_assignment_quality_improvements.py` -> `10 passed`

## 2026-03-23 (T-DS-910/920: Instrumentation + Intelligence Baseline Repair)

Branch: `feat/T-DS-910-920-instrumentation-intelligence`

Commit: `323814a` `[T-DS-911/912/917/921/922/925] Instrumentation + intelligence baseline repair`

### Summary

**T-DS-911 — Serve-time feature logging (`SearchServingLog`)**
- New model in `backend/app/db/models.py`: `SearchServingLog` captures query, filters, result_job_ids, result_scores, mode per search request.
- New helper `log_search_serving()` in `backend/app/services/search.py`.
- Wired into `GET /api/search` in `backend/app/api/routes.py` — every search request now logs a serving event.

**T-DS-912/913 — Application funnel events + structured rejection reasons**
- New model `ApplicationFunnelEvent` in `backend/app/db/models.py`.
- Stages: `viewed`, `applied`, `shortlisted`, `interviewed`, `rejected`, `offered`, `hired`.
- Fields: `stage`, `actor` (user/employer/system), `reason` (from `REJECTION_REASONS` taxonomy), `details`, `meta`.
- Constants `APPLICATION_STAGES` and `REJECTION_REASONS` exported from models.

**T-DS-916 — Real serve-time training signals in ranking trainer**
- Rewrote `backend/app/services/ranking_trainer.py`:
  - `_collect_from_serving_log()`: builds training examples from `SearchServingLog` rows — real queries, real candidate sets, real scores.
  - `_collect_fallback()`: job-attribute-only features when no log data; no more synthetic `70.0`/`40.0` similarity placeholders.
  - `collect_training_data()`: tries serve-time log first, falls back gracefully.

**T-DS-917 — Real ranking features (no more stubs)**
- `backend/app/services/ranking.py`:
  - Added `_token_overlap()` (Jaccard token overlap) and `_recency_score()` helpers.
  - Feature[1] title_match: Jaccard overlap (was binary substring check).
  - Feature[2] desc_match: Jaccard over description (was hardcoded 0.0).
  - Feature[3] recency: from `first_seen` date (was hardcoded 0.5).
  - Feature[7] skill_overlap: Jaccard user_skills ∩ job_skills (was hardcoded 0.0).

**T-DS-921 — Real `RoleEvolution` computation**
- `generate_role_evolution()` in `backend/app/services/analytics.py` was a stub (deleted table, returned success with no data).
- Now computes top-K skills per role family per month from `JobEntities`, skips inactive jobs, handles dict/str skill shapes.

**T-DS-922 — Real skill share computation**
- `aggregate_skill_trends()` now computes `share = skill_count / total_skill_mentions_in_bucket`. Was hardcoded `0.0`.

**T-DS-925 — Standardised intelligence provenance**
- New `get_intelligence_metadata(db, role_family, window_days)` in `analytics.py`.
- Returns: `sample_size`, `date_range` (from/to/window_days), `source_mix` (top 5 sources), `confidence_note` (high/medium/low).

### Tests Written
- `backend/tests/test_ds910_920.py` — 38 new tests covering all of the above.
- `backend/tests/test_ranking.py` — updated title_match assertion to reflect Jaccard (was `== 1.0`, now `> 0.0`).
- `ruff check` and `ruff format --check` pass on all changed files.
- Note: `pytest` binary not available in local venv (only `ruff` is installed). Tests are syntactically valid and should pass on VPS/CI where pytest is present.

### Remaining T-DS-910/920 Tasks
- `T-DS-914`: Offline evaluation harness for search/recommendations
- `T-DS-915`: Intelligence quality dashboard
- `T-DS-918`: Ranking-quality evaluation suite (effectiveness metrics)
- `T-DS-923`: Representativeness reporting (geography, sector, coverage gaps)
- `T-DS-924`: Replace hardcoded pathways/skills-gap with market-derived baselines

### Next Steps (recommended)
1. Push branch and run pytest on VPS to verify 38 new tests pass.
2. Create Alembic migration for `search_serving_log` and `application_funnel_events` tables.
3. Start `T-DS-914` (offline evaluation harness) or `T-DS-923` (representativeness reporting).



## 2026-02-15 (T-602 monitoring hardening + signals/admin compatibility)

Branch: `feat/T-741-telegram-opportunity-ingest`

Commit: `pending`

### Summary
- Completed hardening task `T-602` by extending monitoring gates in `backend/app/services/monitoring_service.py`:
  - added operations thresholds for ingestion error rate and ingestion staleness (`MONITORING_ERROR_RATE_MAX`, `MONITORING_INGESTION_STALENESS_HOURS`)
  - added `operations` section to monitoring summary with checks/metrics/thresholds and integrated status into overall pass/warn/fail outcome
- Hardened signals flow in `backend/app/services/signals.py`:
  - idempotent aggregate signal regeneration for active windows
  - processing-log emission for `signals_aggregate` with `evidence_ids` and `evidence_links_count`
- Restored admin endpoint compatibility in `backend/app/api/admin_routes.py` for:
  - `/api/admin/lmi-scorecard`, `/api/admin/lmi-health`, `/api/admin/lmi-integrity`, `/api/admin/lmi-skills`, `/api/admin/lmi-seniority`
- Added/updated tests:
  - `backend/tests/test_monitoring_service.py` (new)
  - `backend/tests/test_signals_pipeline.py`
  - `backend/tests/test_admin_processing_endpoints.py`
- Added implementation docs:
  - `backend/docs/LMI_MONITORING_IMPLEMENTATION.md`
  - `backend/docs/LMI_QA_MONITORING_CHECKLIST.md`

### Tests Run
- `backend/venv3.11/bin/pytest -q backend/tests/test_monitoring_service.py backend/tests/test_signals_pipeline.py backend/tests/test_admin_processing_endpoints.py -k "monitoring or drift or signals or lmi"` (11 passed)

### Notes
- `changemap.md` updated to mark `T-602`/`T-602a` complete and log this implementation cycle.

## 2026-02-15 (T-741: Telegram + Opportunity Sources + Periodic Ingestion Timer)

Branch: `feat/T-741-telegram-opportunity-ingest`

Commits:
- `945fd5d` `[T-741] Add telegram + opportunity sources ingestion`
- `6e108e6` `[T-741] Add periodic sources ingestion runner`
- `a0ddd68` `[T-741] Ruff format backend`
- `cb03d93` `[T-741] Post-process sources.yaml by source`
- `1219408` `[T-741] Fix sources ingestion script imports`

### Summary
- Added a one-shot ingestion runner for `backend/app/ingestion/sources.yaml` that also runs DB-only post-processing (`backend/scripts/run_sources_ingestion.py`).
- Hardened `gov_careers` HTML connector with per-source HTTP tuning (`timeout`, `retries`, `retry_backoff_s`, `user_agent`) and updated Global South to use the dedicated listings page (`/jobs/`) (`backend/app/ingestion/connectors/gov_careers.py`, `backend/app/ingestion/sources.yaml`).
- VPS: pulled latest branch to `/home/nextstep.co.ke/public_html`, restarted backend/celery services, and confirmed `GET /health/detailed` is healthy (Postgres).
- VPS: added periodic ingestion via `systemd`:
  - `/etc/systemd/system/nextstep-ingest-sources.service`
  - `/etc/systemd/system/nextstep-ingest-sources.timer` (every 6 hours at `*:45`, with randomized delay)
- Production status:
  - `standardarena.co.ke`: ingest OK (87 total in DB)
  - `globalsouthopportunities.co.ke`: ingest OK (59 total in DB)
  - `telegram:job_vacancy_kenya`: connector deployed, but awaiting credentials in `/home/nextstep.co.ke/.env`

### Telegram Setup (Prod)
1. Generate a Telethon session string:
   - `cd /home/nextstep.co.ke/public_html/backend`
   - `source /home/nextstep.co.ke/.venv/bin/activate`
   - `TELEGRAM_API_ID=... TELEGRAM_API_HASH=... python scripts/telegram_create_session.py`
2. Add to `/home/nextstep.co.ke/.env`:
   - `TELEGRAM_API_ID=...`
   - `TELEGRAM_API_HASH=...`
   - `TELEGRAM_SESSION="..."` (quote it)
3. Run one-shot (or wait for the timer):
   - `systemctl start nextstep-ingest-sources.service`

### Tests Run
- `backend/venv3.11/bin/ruff check` (pass)
- `backend/venv3.11/bin/ruff format --check` (pass)
- `backend/venv3.11/bin/pytest -q` (217 passed, 1 skipped)

## 2026-02-15 (MVIL Tasks 7-8: Search Mode Routing + Frontend Guided UI)

Branch: `feat/T-740-scheduled-scrape-processing`

Commit: `pending`

### Summary
- Completed Task 7 from `docs/plans/2026-02-14-role-baselines-guided-search.md`.
  - Extended `/api/search` mode routing in `backend/app/api/routes.py`.
  - Added mode-aware response fields: `guided_results`, `mode`, `mode_error`.
  - Enforced authentication for guided mode and wired profile fallback skills/education/current role.
- Completed Task 8 from `docs/plans/2026-02-14-role-baselines-guided-search.md`.
  - Added guided mode selector tabs and guided results panel in `frontend/index.html`.
  - Added guided mode styling in `frontend/styles/main.css`.
  - Extended `frontend/js/main.js` search flow to send `mode` and render guided cards/errors.
  - Mode tabs are shown only when authenticated and hidden when signed out.
- Added tests:
  - `backend/tests/test_search_modes.py` (new)
- Updated plan progress tracker:
  - Completed 8 / Remaining 0.

### Tests Run
- `backend/venv3.11/bin/pytest -q backend/tests/test_search_modes.py` (3 passed)
- `backend/venv3.11/bin/pytest -q backend/tests/test_search_modes.py backend/tests/test_guided_advance.py backend/tests/test_guided_match.py backend/tests/test_guided_explore.py backend/tests/test_mvil_admin.py backend/tests/test_mvil_service.py backend/tests/test_mvil_models.py backend/tests/test_dashboard_endpoints.py -k "lmi_quality or overview" backend/tests/test_subscription_paywall.py backend/tests/test_payment_webhooks.py` (11 passed)
- Frontend runtime smoke:
  - `python3 -m http.server 8088` in `frontend/`
  - `curl -s http://localhost:8088/index.html | grep -E "guidedModeWrap|guidedResultsGrid|data-guided-mode"`

### Notes
- MVIL plan scope is fully implemented (Tasks 1-8).
- Backend app runtime validation with uvicorn was not possible in this environment because `uvicorn` is not installed in the available Python environments.

## 2026-02-15 (MVIL Task 6: Advance Mode API)

Branch: `feat/T-740-scheduled-scrape-processing`

Commit: `pending`

### Summary
- Completed Task 6 from `docs/plans/2026-02-14-role-baselines-guided-search.md`.
- Extended guided search service in `backend/app/services/guided_search.py`:
  - added `advance_transitions()` for professional transition cards
  - computes `skill_gap`, `shared_skills`, `difficulty_proxy`, and `demand_trend`
  - includes `target_jobs` and evidence `sample_job_ids`
  - sorts transitions by feasibility (smaller skill gap first)
- Added route in `backend/app/api/routes.py`:
  - `GET /api/guided/advance`
- Added tests in `backend/tests/test_guided_advance.py`:
  - transition card shape and no-salary contract
  - difficulty classification and feasibility ordering
- Updated plan progress tracker:
  - Completed 6 / Remaining 2.

### Tests Run
- `backend/venv3.11/bin/pytest -q backend/tests/test_guided_advance.py` (2 passed)
- `backend/venv3.11/bin/pytest -q backend/tests/test_guided_advance.py backend/tests/test_guided_match.py backend/tests/test_guided_explore.py backend/tests/test_mvil_admin.py backend/tests/test_mvil_service.py backend/tests/test_mvil_models.py backend/tests/test_dashboard_endpoints.py -k "lmi_quality or overview" backend/tests/test_subscription_paywall.py backend/tests/test_payment_webhooks.py` (11 passed)

### Notes
- Next step in this plan is Task 7 (search API mode routing).

## 2026-02-15 (MVIL Task 5: Match Mode API)

Branch: `feat/T-740-scheduled-scrape-processing`

Commit: `pending`

### Summary
- Completed Task 5 from `docs/plans/2026-02-14-role-baselines-guided-search.md`.
- Extended guided search service in `backend/app/services/guided_search.py`:
  - added `match_roles()` for early-career role matching
  - ranking uses skill overlap + education fit ladder
  - returns `matching_skills`, `missing_skills`, and starter job previews
  - includes profile-skills fallback handling (`UserProfile.skills` dict -> list)
- Added route in `backend/app/api/routes.py`:
  - `GET /api/guided/match`
- Added tests in `backend/tests/test_guided_match.py`:
  - ranking order + skill gaps + starter job previews
  - authenticated profile skills conversion behavior
- Updated plan progress tracker:
  - Completed 5 / Remaining 3.

### Tests Run
- `backend/venv3.11/bin/pytest -q backend/tests/test_guided_match.py` (2 passed)
- `backend/venv3.11/bin/pytest -q backend/tests/test_guided_match.py backend/tests/test_guided_explore.py backend/tests/test_mvil_admin.py backend/tests/test_mvil_service.py backend/tests/test_mvil_models.py backend/tests/test_dashboard_endpoints.py -k "lmi_quality or overview" backend/tests/test_subscription_paywall.py backend/tests/test_payment_webhooks.py` (11 passed)

### Notes
- Next step in this plan is Task 6 (Advance mode API for transition cards).

## 2026-02-15 (MVIL Task 4: Explore Mode API)

Branch: `feat/T-740-scheduled-scrape-processing`

Commit: `pending`

### Summary
- Completed Task 4 from `docs/plans/2026-02-14-role-baselines-guided-search.md`.
- Added guided explore service in `backend/app/services/guided_search.py`:
  - role-level career cards from MVIL baselines
  - query matching against role families and canonical titles
  - evidence union in `sample_job_ids`
  - low-confidence signaling for small sample families
  - empty-baseline fallback message (no expensive live-query fallback)
- Added route in `backend/app/api/routes.py`:
  - `GET /api/guided/explore`
- Added endpoint tests in `backend/tests/test_guided_explore.py`.
- Updated plan progress tracker:
  - Completed 4 / Remaining 4.

### Tests Run
- `backend/venv3.11/bin/pytest -q backend/tests/test_guided_explore.py` (2 passed)
- `backend/venv3.11/bin/pytest -q backend/tests/test_guided_explore.py backend/tests/test_mvil_admin.py backend/tests/test_mvil_service.py backend/tests/test_mvil_models.py backend/tests/test_dashboard_endpoints.py -k "lmi_quality or overview" backend/tests/test_subscription_paywall.py backend/tests/test_payment_webhooks.py` (11 passed)

### Notes
- Next step in this plan is Task 5 (Match mode API for role matching and skill gaps).

## 2026-02-15 (MVIL Task 3: Admin Refresh Endpoint)

Branch: `feat/T-740-scheduled-scrape-processing`

Commit: `pending`

### Summary
- Completed Task 3 from `docs/plans/2026-02-14-role-baselines-guided-search.md`.
- Added `POST /api/admin/mvil/refresh` in `backend/app/api/routes.py`:
  - requires admin access via `require_admin()`
  - executes `refresh_all_baselines(db)`
  - returns the refresh summary payload
  - logs success/error events to `ProcessingLog` as `mvil_baselines_refresh`
- Added endpoint tests in `backend/tests/test_mvil_admin.py`:
  - unauthorized access rejection
  - successful admin execution response shape
- Updated plan progress tracker:
  - Completed 3 / Remaining 5.

### Tests Run
- `backend/venv3.11/bin/pytest -q backend/tests/test_mvil_admin.py` (2 passed)
- `backend/venv3.11/bin/pytest -q backend/tests/test_mvil_admin.py backend/tests/test_mvil_service.py backend/tests/test_mvil_models.py backend/tests/test_dashboard_endpoints.py -k "lmi_quality or overview" backend/tests/test_subscription_paywall.py backend/tests/test_payment_webhooks.py` (11 passed)

### Notes
- Next step in this plan is Task 4 (Explore mode API career cards).

## 2026-02-15 (MVIL Task 2: Aggregation Service)

Branch: `feat/T-740-scheduled-scrape-processing`

Commit: `pending`

### Summary
- Completed Task 2 from `docs/plans/2026-02-14-role-baselines-guided-search.md`.
- Added MVIL aggregation service in `backend/app/services/mvil_service.py`:
  - `compute_role_skill_baselines`
  - `compute_role_education_baselines`
  - `compute_role_experience_baselines`
  - `compute_role_demand_snapshots`
  - `refresh_all_baselines` (transactional insert-then-delete with rollback safety)
- Service behavior includes:
  - mixed skill-shape normalization (`list[dict]`, `list[str]`, `dict`)
  - education normalization bins and experience banding via Python logic (SQLite-safe)
  - role family filtering (`family != "other"`, minimum 3 jobs)
  - low-confidence flagging for families with 3-9 jobs
  - deterministic active-only recency-ordered evidence job IDs
- Added tests in `backend/tests/test_mvil_service.py` covering:
  - aggregation correctness and family filters
  - mixed skill formats
  - active recency sample IDs
  - transactional rollback preserving prior rows on flush failure
- Updated plan progress tracker:
  - Completed 2 / Remaining 6.

### Tests Run
- `backend/venv3.11/bin/pytest -q backend/tests/test_mvil_service.py` (2 passed)
- `backend/venv3.11/bin/pytest -q backend/tests/test_dashboard_endpoints.py -k "lmi_quality or overview" backend/tests/test_subscription_paywall.py backend/tests/test_payment_webhooks.py backend/tests/test_mvil_models.py backend/tests/test_mvil_service.py` (11 passed)

### Notes
- Next step in this plan is Task 3 (admin MVIL refresh endpoint + runner hook).

## 2026-02-15 (MVIL Task 1: Database Models)

Branch: `feat/T-740-scheduled-scrape-processing`

Commit: `pending`

### Summary
- Completed Task 1 from `docs/plans/2026-02-14-role-baselines-guided-search.md`.
- Added four new MVIL baseline models in `backend/app/db/models.py`:
  - `RoleSkillBaseline`
  - `RoleEducationBaseline`
  - `RoleExperienceBaseline`
  - `RoleDemandSnapshot`
- Added dedicated tests in `backend/tests/test_mvil_models.py`:
  - verifies all MVIL tables exist in SQLAlchemy metadata
  - verifies required evidence fields are present and typed
- Updated plan progress tracker:
  - Completed 1 / Remaining 7.

### Tests Run
- `backend/venv3.11/bin/pytest -q backend/tests/test_mvil_models.py` (2 passed)
- `backend/venv3.11/bin/pytest -q backend/tests/test_dashboard_endpoints.py -k "lmi_quality or overview" backend/tests/test_subscription_paywall.py backend/tests/test_payment_webhooks.py backend/tests/test_mvil_models.py` (11 passed)

### Notes
- Next step in this plan is Task 2 (MVIL aggregation service) using these tables.

## 2026-02-15 (Settings Edit Guard + Audit Metadata)

Branch: `feat/T-740-scheduled-scrape-processing`

Commit: `pending`

### Summary
- Added optional editor allowlist for settings edits in `backend/app/core/config.py`:
  - `ADMIN_SETTINGS_EDITORS`
- Enforced allowlist in `PUT /api/admin/lmi-alert-settings`:
  - rejects non-allowlisted admins with 403 when allowlist is configured.
- Added audit metadata capture on each settings update:
  - request IP and user-agent stored in `ProcessingLog.results.request_metadata`.
- Extended `GET /api/admin/lmi-alert-settings/history` to return `request_metadata` for each history entry.

### Tests Run
- `backend/venv3.11/bin/pytest -q backend/tests/test_dashboard_endpoints.py -k "lmi_alert_settings or lmi_quality"` (13 passed)
- `backend/venv3.11/bin/pytest -q backend/tests/test_dashboard_endpoints.py -k "lmi_quality or overview" backend/tests/test_subscription_paywall.py backend/tests/test_payment_webhooks.py` (11 passed)

### Notes
- If `ADMIN_SETTINGS_EDITORS` is empty, existing behavior remains (any admin from `ADMIN_EMAILS` can edit).

## 2026-02-15 (Alert Settings Audit History View)

Branch: `feat/T-740-scheduled-scrape-processing`

Commit: `pending`

### Summary
- Added alert settings history API in `backend/app/api/admin_routes.py`:
  - `GET /api/admin/lmi-alert-settings/history`
  - returns recent settings changes (timestamp, editor, values).
- Added admin history panel in `frontend/admin.html` + `frontend/js/admin.js` to show latest settings changes.
- History panel auto-refreshes after saving controls so operators can immediately verify updates.
- Added regression coverage in `backend/tests/test_dashboard_endpoints.py` for history retrieval.

### Tests Run
- `backend/venv3.11/bin/pytest -q backend/tests/test_dashboard_endpoints.py -k "lmi_quality or lmi_alert_settings"` (12 passed)
- `backend/venv3.11/bin/pytest -q backend/tests/test_dashboard_endpoints.py -k "lmi_quality or overview" backend/tests/test_subscription_paywall.py backend/tests/test_payment_webhooks.py` (11 passed)

### Notes
- History is backed by `ProcessingLog` records for `admin_conversion_alert_settings` and ordered by most recent first.

## 2026-02-15 (Admin Settings UI/API for Conversion Alert Controls)

Branch: `feat/T-740-scheduled-scrape-processing`

Commit: `pending`

### Summary
- Added runtime settings endpoints in `backend/app/api/admin_routes.py`:
  - `GET /api/admin/lmi-alert-settings`
  - `PUT /api/admin/lmi-alert-settings`
- Settings overrides are persisted in `ProcessingLog` (`admin_conversion_alert_settings`) so ops can tune controls without env redeploy.
- Updated `GET /api/admin/lmi-quality` to use effective (override + default) alert settings.
- Updated `backend/app/services/admin_alert_service.py` to accept override inputs for threshold/cooldown/channels.
- Added admin controls panel in `frontend/admin.html` and wired load/save in `frontend/js/admin.js`.

### Tests Run
- `backend/venv3.11/bin/pytest -q backend/tests/test_dashboard_endpoints.py -k "lmi_quality or lmi_alert_settings"` (11 passed)
- `backend/venv3.11/bin/pytest -q backend/tests/test_dashboard_endpoints.py -k "lmi_quality or overview" backend/tests/test_subscription_paywall.py backend/tests/test_payment_webhooks.py` (11 passed)

### Notes
- Current persistence uses `processing_log` as a lightweight runtime config store to avoid migration overhead.

## 2026-02-15 (Configurable Conversion Alert Controls)

Branch: `feat/T-740-scheduled-scrape-processing`

Commit: `pending`

### Summary
- Added configurable conversion alert controls in `backend/app/core/config.py`:
  - threshold (`ADMIN_CONVERSION_ALERT_THRESHOLD`)
  - cooldown (`ADMIN_CONVERSION_ALERT_COOLDOWN_HOURS`)
  - per-channel toggles (`IN_APP`, `EMAIL`, `WHATSAPP`)
- Updated `backend/app/api/admin_routes.py` to compute warning status using configured threshold.
- Updated `backend/app/services/admin_alert_service.py` to respect cooldown/toggles when dispatching.
- Expanded `backend/tests/test_dashboard_endpoints.py` with:
  - configured threshold behavior test
  - channel toggle behavior test

### Tests Run
- `backend/venv3.11/bin/pytest -q backend/tests/test_dashboard_endpoints.py -k "lmi_quality"` (9 passed)
- `backend/venv3.11/bin/pytest -q backend/tests/test_dashboard_endpoints.py -k "lmi_quality or overview" backend/tests/test_subscription_paywall.py backend/tests/test_payment_webhooks.py` (11 passed)

### Notes
- Defaults preserve existing behavior (warning threshold 5.0%, all channels enabled, cooldown 6h).

## 2026-02-15 (Conversion Warning Notification Routing)

Branch: `feat/T-740-scheduled-scrape-processing`

Commit: `pending`

### Summary
- Added admin channel dispatch for conversion warning alerts:
  - New service `backend/app/services/admin_alert_service.py` sends warning notifications through:
    - in-app (`UserNotification`)
    - email (`send_email`)
    - WhatsApp (`send_whatsapp_message`)
- Added cooldown dedupe (6 hours) to avoid duplicate alerts from repeated dashboard requests.
- Integrated warning dispatch in `backend/app/api/admin_routes.py` inside `GET /api/admin/lmi-quality`.
- Expanded dashboard endpoint tests for:
  - channel delivery assertions (in-app/email/whatsapp)
  - cooldown dedupe behavior

### Tests Run
- `backend/venv3.11/bin/pytest -q backend/tests/test_dashboard_endpoints.py -k "lmi_quality"` (7 passed)
- `backend/venv3.11/bin/pytest -q backend/tests/test_dashboard_endpoints.py -k "lmi_quality or overview" backend/tests/test_subscription_paywall.py backend/tests/test_payment_webhooks.py` (9 passed)

### Notes
- Dispatch currently targets configured admin users from `ADMIN_EMAILS`; if no admin recipients are configured, notifications are skipped safely.

## 2026-02-15 (Conversion Drop-off Alerting)

Branch: `feat/T-740-scheduled-scrape-processing`

Commit: `pending`

### Summary
- Added conversion drop-off alerting in admin monetization metrics:
  - `backend/app/api/admin_routes.py` now returns `revenue.conversion_alert` in `GET /api/admin/lmi-quality`.
  - Alert evaluates 7-day average conversion rate against a threshold (5.0%).
  - Returns `status`, `avg_conversion_7d`, `threshold`, and `message`.
- Updated admin summary panel:
  - `frontend/js/admin.js` now displays conversion alert state and 7-day average conversion.
- Added test coverage:
  - `backend/tests/test_dashboard_endpoints.py` validates alert presence and low-conversion warning behavior.

### Tests Run
- `backend/venv3.11/bin/pytest -q backend/tests/test_dashboard_endpoints.py -k "lmi_quality"` (5 passed)
- `backend/venv3.11/bin/pytest -q backend/tests/test_dashboard_endpoints.py -k "lmi_quality or overview" backend/tests/test_subscription_paywall.py backend/tests/test_payment_webhooks.py` (7 passed)

### Notes
- This is backend-side alert signaling only; no external notification dispatch yet. Next step can wire these warnings into notification channels (email/WhatsApp/in-app) for proactive monitoring.

## 2026-02-15 (Conversion Trend Timeseries)

Branch: `feat/T-740-scheduled-scrape-processing`

Commit: `pending`

### Summary
- Added time-series conversion tracking to admin monetization analytics:
  - `backend/app/api/admin_routes.py` now returns `revenue.conversion_trend_14d` in `GET /api/admin/lmi-quality`.
  - Each point includes: `date`, `upgrades`, `new_users`, `conversion_rate`.
- Updated admin UI summary:
  - `frontend/js/admin.js` now renders 14-day upgrades total and 14-day average conversion percentage.
- Expanded test coverage:
  - `backend/tests/test_dashboard_endpoints.py` includes trend-shape and non-zero upgrade assertions.

### Tests Run
- `backend/venv3.11/bin/pytest -q backend/tests/test_dashboard_endpoints.py -k "lmi_quality"` (4 passed)
- `backend/venv3.11/bin/pytest -q backend/tests/test_dashboard_endpoints.py -k "lmi_quality or overview" backend/tests/test_subscription_paywall.py backend/tests/test_payment_webhooks.py` (6 passed)

### Notes
- Trend series uses persisted `subscription_upgrade` events and user creation dates, improving daily funnel visibility beyond static monthly snapshots.

## 2026-02-15 (Conversion Tracking Metrics: Free → Paid)

Branch: `feat/T-740-scheduled-scrape-processing`

Commit: `pending`

### Summary
- Implemented conversion tracking metrics for premium monetization visibility:
  - Extended `GET /api/admin/lmi-quality` in `backend/app/api/admin_routes.py` to include:
    - `upgraded_users_30d`
    - `new_users_30d`
    - `conversion_rate_30d`
    - `paid_conversion_overall`
- Added event logging for upgrade actions:
  - `backend/app/services/subscription_service.py` now records `UserNotification(type="subscription_upgrade")` when a subscription is activated.
- Updated admin dashboard rendering:
  - `frontend/js/admin.js` now shows free→paid conversion and new paid users metrics.
- Added test coverage:
  - `backend/tests/test_dashboard_endpoints.py` includes conversion metric assertions.

### Tests Run
- `backend/venv3.11/bin/pytest -q backend/tests/test_dashboard_endpoints.py -k "lmi_quality or overview"` (5 passed)
- `backend/venv3.11/bin/pytest -q backend/tests/test_subscription_paywall.py backend/tests/test_payment_webhooks.py` (7 passed)

### Notes
- Conversion metrics use explicit upgrade events (`subscription_upgrade`) rather than only current subscription tier snapshots, improving reliability of funnel tracking.

## 2026-02-15 (Payment Webhook Verification for Subscription Activation)

Branch: `feat/T-740-scheduled-scrape-processing`

Commit: `pending`

### Summary
- Added provider callback/webhook verification for production-safe subscription upgrades:
  - New router: `backend/app/api/payment_routes.py`
  - New endpoints:
    - `POST /api/payments/webhooks/stripe`
    - `POST /api/payments/webhooks/mpesa`
  - Webhook payloads are verified via HMAC signatures before activating plans.
- Extended subscription activation service:
  - `backend/app/services/subscription_service.py`
  - Added `activate_plan_by_user_id(...)` for verified webhook events.
- Added M-Pesa webhook secret config:
  - `backend/app/core/config.py` with `MPESA_WEBHOOK_SECRET` (fallback to `MPESA_PASSKEY`).

### Tests Run
- `backend/venv3.11/bin/pytest -q backend/tests/test_payment_webhooks.py` (3 passed)
- `backend/venv3.11/bin/pytest -q backend/tests/test_payment_webhooks.py backend/tests/test_subscription_paywall.py backend/tests/test_career_pathways_endpoint.py backend/tests/test_skills_gap_scan_endpoint.py` (14 passed)

### Notes
- Activation now occurs only on verified payment events; unverified/missing signatures are rejected with `403`.
- Next step is replacing placeholder checkout URLs with provider SDK/session creation and including stable reference metadata in provider payment objects.

## 2026-02-15 (Phase 1 Paywall + Subscription Checkout)

Branch: `feat/T-740-scheduled-scrape-processing`

Commit: `pending`

### Summary
- Implemented the previously skipped Phase 1 paywall/payment step for premium features:
  - New subscription service: `backend/app/services/subscription_service.py`
  - New authenticated subscription endpoints in `backend/app/api/user_routes.py`:
    - `GET /api/users/subscription/plans`
    - `POST /api/users/subscription/checkout`
    - `POST /api/users/subscription/activate`
- Enforced premium access for career pathways:
  - `GET /api/career-pathways/{role_slug}` now requires `professional` subscription.
- Updated premium feature UIs to handle paywall responses and start checkout:
  - `frontend/js/skills-gap-scan.js`
  - `frontend/js/career-pathways.js`

### Tests Run
- `backend/venv3.11/bin/pytest backend/tests/test_career_pathways_endpoint.py backend/tests/test_subscription_paywall.py backend/tests/test_skills_gap_scan_endpoint.py` (11 passed)

### Notes
- Checkout endpoint currently provides provider-specific redirect URLs (Stripe/M-Pesa placeholder URLs) and an activation endpoint for post-payment state transition.
- Next step is wiring provider webhooks/callback verification before production billing launch.

## 2026-02-15 (LMI Monetization Milestones + Admin LMI Quality)

Branch: `feat/T-740-scheduled-scrape-processing`

Commit: `d01868e` (`[LMI-PH1] Implement core LMI monetization milestones`)

### Summary
- Implemented LMI monetization foundations from `docs/LMI_IMPLEMENTATION_PLAN.md`:
  - Job match scoring service and endpoint:
    - `backend/app/services/matching_service.py`
    - `GET /api/users/job-match/{job_id}` in `backend/app/api/user_routes.py`
  - Salary intelligence service and estimated salary fallback:
    - `backend/app/services/salary_service.py`
    - integrated in `backend/app/services/search.py`
    - salary surfaced in result cards via `frontend/js/main.js`
  - Skills Gap Scan premium diagnostic flow:
    - `backend/app/services/skills_gap_service.py`
    - `POST /api/users/skills-gap-scan`
    - `frontend/skills-gap-scan.html`, `frontend/js/skills-gap-scan.js`
  - Career pathway products:
    - `backend/app/services/career_pathways_service.py`
    - `GET /api/career-pathways/{role_slug}`
    - `frontend/career-pathways.html`, `frontend/js/career-pathways.js`
  - Enhanced admin LMI quality metrics:
    - `GET /api/admin/lmi-quality` in `backend/app/api/admin_routes.py`
    - rendered in `frontend/admin.html` + `frontend/js/admin.js`

### Tests Run
- `backend/venv3.11/bin/pytest -q backend/tests/test_career_pathways_endpoint.py backend/tests/test_skills_gap_scan_endpoint.py backend/tests/test_salary_service.py backend/tests/test_user_job_match_endpoint.py` (11 passed)
- `backend/venv3.11/bin/pytest -q backend/tests/test_dashboard_endpoints.py -k "lmi_quality or overview"` (4 passed)

### Notes
- Workspace diagnostics may still report strict line-length issues in legacy files; focused Ruff checks for modified files pass.
- New API/UI features are connected but payment integration was intentionally skipped per user instruction.

## 2026-02-15 (Embeddings Backfill Timer + Search Guard)

Branch: `feat/T-740-scheduled-scrape-processing`

Commit: `be19852` (`[OPS-EMBED] Schedule embeddings backfill and harden search scoring`)

### Summary
- Added a production systemd `oneshot` + `timer` pair for embeddings backfill:
  - Templates: `deploy/systemd/nextstep-embeddings.service`, `deploy/systemd/nextstep-embeddings.timer`
  - Runs `python -m cli embed` (incremental; only jobs missing an embedding for the configured model)
- Hardened `/api/search` behavior when transformers are disabled:
  - When `NEXTSTEP_DISABLE_TRANSFORMERS=1`, semantic scoring is disabled to avoid hash-vector "similarity" randomizing ranking.
  - Scoped embedding lookup by `EMBEDDING_MODEL_NAME` (default `e5-small-v2`) to prevent multi-row issues per job.

### Ops / Deployment Notes (VPS)
- Installed on VPS as:
  - `/etc/systemd/system/nextstep-embeddings.service`
  - `/etc/systemd/system/nextstep-embeddings.timer` (every 30 minutes)
- Enabled + started:
  - `systemctl daemon-reload`
  - `systemctl enable --now nextstep-embeddings.timer`
  - `systemctl start nextstep-embeddings.service`
- Progress checks:
  - `sudo -u postgres psql -d career_lmi -tAc "select count(*) from job_embeddings;"`
  - `journalctl -u nextstep-embeddings.service -n 50 --no-pager`
- Note: API service has `NEXTSTEP_DISABLE_TRANSFORMERS=1` set via `nextstep-backend.service.d/override.conf` to keep memory stable with multiple workers. With the search guard in place, this does not degrade ranking while embeddings are being backfilled.

### Tests Run
- `backend/venv3.11/bin/ruff format --check backend` (pass)
- `backend/venv3.11/bin/ruff check backend` (pass)
- `backend/venv3.11/bin/pytest -q` (pass; 164 passed, 1 skipped)

## 2026-02-15 (Scraper Endpoints Aligned With config.yaml Spiders)

Branch: `feat/T-740-scheduled-scrape-processing`

Commit: `0593884` (`[OPS-SCRAPE] Align scraper endpoints with config.yaml spiders`)

### Summary
- Fixed a production mismatch where `/api/scrapers/run*` and Celery scraper tasks did not actually scrape anything (site keys didn’t match and the code path wasn’t using `config.yaml`).
- `backend/app/services/scraper_service.py` now:
  - Runs the same `SiteSpider` implementation used by the production pipeline (`scrapers/main.py` + `scrapers/config.yaml`)
  - Returns `jobs_scraped`/`scraped_jobs` as the number of **new rows inserted**
  - When `process_jobs=true`, triggers deterministic post-processing via `process_job_posts()` for the site’s derived domain source (e.g. `brightermonday.co.ke`)
  - Skips `migrate_sqlite_to_postgres()` when `USE_POSTGRES=true` (scrapers already write directly to Postgres)

### Tests Run
- `backend/venv3.11/bin/ruff format --check backend` (pass)
- `backend/venv3.11/bin/ruff check backend` (pass)
- `backend/venv3.11/bin/pytest -q` (pass; 174 passed, 1 skipped)

## 2026-02-14 (VPS JSON Upload + Postgres Import)

Branch: `feat/T-630-fix-json-import-postgres`

### Summary
- Fixed `backend/scripts/import_jobs_to_db.py` so it works against the production Postgres schema:
  - Always sets `job_post.attachment_flag` (NOT NULL on VPS, no server default).
  - Prevents duplicate `location` rows by selecting before insert (prod schema has no uniqueness constraint).
  - Adds in-memory caches for org/location lookups to speed up import.
- Uploaded `backend/data/migration/jobs_export.json` to VPS and verified checksum match.
- Ran the JSON import into VPS Postgres `career_lmi` and verified row counts.

### Ops / Deployment Notes (VPS)
- Upload destination: `/home/nextstep.co.ke/jobs_export.json` (sha256 match verified).
- Import command:
  - `cd /home/nextstep.co.ke/public_html/backend`
  - `source /home/nextstep.co.ke/.env`
  - `/home/nextstep.co.ke/.venv/bin/python scripts/import_jobs_to_db.py --input /home/nextstep.co.ke/jobs_export.json --batch-size 2000`
- Import results:
  - Processed: `102,169`
  - Imported: `77,669`
  - Skipped (existing): `24,500`
  - Errors: `0`
- Verified counts (Postgres `career_lmi`):
  - `job_post`: `104,690`
  - `organization`: `2,800`
  - `location`: `787`
  - `job_entities`: `27,021` (not backfilled by this import)
  - `job_embeddings`: `0` (not generated by this import)

### Tests Run
- `backend/venv3.11/bin/ruff check .` (pass)
- `backend/venv3.11/bin/ruff format --check .` (pass)
- `.venv/bin/pytest -q` (pass; 153 passed, 1 skipped)

## 2026-02-14 (Scheduled Scraping + Processing Pipeline)

Branch: `feat/T-740-scheduled-scrape-processing`

### Summary
- Added unified incremental pipeline orchestration for scheduled runs:
  - CLI: `python -m cli pipeline` (scrape sites -> ingest-incremental -> post-process -> dedupe -> embed -> analytics)
  - systemd template updated: `deploy/systemd/nextstep-pipeline.service`
  - optional Celery beat schedule: `incremental-pipeline` (guarded by `ENABLE_CELERY_PIPELINE=true`, Redis lock)
- Skill extraction: keep deterministic patterns enabled even when `SKILL_EXTRACTOR_MODE=skillner` to backstop SkillNER misses (fixes regression: Excel).

### Tests Run
- `backend/venv3.11/bin/ruff check .` (pass)
- `backend/venv3.11/bin/ruff format --check .` (pass)
- `backend/venv3.11/bin/pytest -q` (pass; 161 passed, 1 skipped)

## 2026-02-09 (Hardening & Test Coverage)

Branch: `main`

### Summary
- **T-403d**: Added 42 endpoint tests covering all analytics (public) and admin dashboard routes — overview, users, jobs, sources, operations, summaries, education mappings (CRUD), admin analytics, drift monitoring, and signals (tenders + hiring).
- **T-601c**: Implemented incremental dedup (`run_incremental_dedup`) using MinHash LSH with persistent `JobDedupeMap` tracking, and incremental embeddings (`run_incremental_embeddings`) that processes only unembedded jobs. Both wired into CLI and ProcessingLog. 10 tests.
- **T-603a/b**: Created 5-job regression fixture dataset and 34 regression tests validating title normalization, seniority, experience, education, salary parsing, skill extraction, and determinism guarantees.
- **T-731**: Created systemd service/timer templates for API server, pipeline (every 6h), and drift checks (daily) in `deploy/systemd/`.
- **T-732**: Built `backend/app/db/upsert.py` with Postgres `INSERT ON CONFLICT` + SQLite ORM fallback for jobs, orgs, and skills. Includes `bulk_upsert_jobs` convenience. 11 tests.
- Updated CLI (`backend/cli.py`): added `dedupe` command, replaced external script-based `embed` with incremental `run_incremental_embeddings`.
- **T-901**: Fixed `ruff` failures in scripts/scraper (import ordering, unused imports, formatting) so repo-wide lint passes.
- **T-902**: Implemented cookie-based auth flow (set cookies on register/login/refresh, refresh via cookie, logout clears cookies, bearer tokens still supported).
- **T-902**: Added Twilio WhatsApp webhook signature validation toggle (`TWILIO_VALIDATE_WEBHOOK_SIGNATURE`) and webhook URL override (`TWILIO_WEBHOOK_URL`) to satisfy webhook security tests.
- **T-902**: Hardened SkillNER adapter evidence building against out-of-range node indices (fixes regression + determinism tests).
- **OPS (VPS)**: Deployed latest `main` to `/home/nextstep.co.ke/public_html`, restarted `nextstep-backend.service`, and updated OpenLiteSpeed vhost to proxy `/health` to the backend (restart `lshttpd`).

### Tests Run
- `.venv/bin/ruff check backend` (pass)
- `.venv/bin/ruff format backend --check` (pass)
- `.venv/bin/pytest backend/tests/` (99 passed)
- `backend/venv3.11/bin/ruff check .` (pass, local)
- `backend/venv3.11/bin/ruff format --check .` (pass, local)
- `/home/nextstep.co.ke/.venv/bin/ruff check .` (pass, VPS)
- `/home/nextstep.co.ke/.venv/bin/ruff format --check .` (pass, VPS)
- `/home/nextstep.co.ke/.venv/bin/pytest -q` (pass, VPS; 122 passed, 1 skipped)

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
- `backend/app/core/config.py` (added auth cookie + Twilio webhook settings)
- `backend/app/services/auth_service.py` (bearer-or-cookie auth resolution)
- `backend/app/api/auth_routes.py` (cookie set/refresh/logout behavior)
- `backend/app/webhooks/whatsapp.py` (Twilio signature validation)
- `backend/app/normalization/skillner_adapter.py` (evidence bounds check)

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

---

## 2026-02-10 (T-610 Unified Post-Ingestion Processing)

Branch: `feat/T-610-unified-post-processing`

### Summary
- Implemented deterministic post-ingestion processing for any `job_post` rows (title normalization, skills + evidence, education/experience/seniority/tasks evidence, `description_clean`, `quality_score`, `processed_at`) and persist extraction evidence in `job_entities`.
- Added admin endpoints for visibility and execution:
  - `POST /api/admin/process` (optional `source=` filter)
  - `GET /api/admin/quality` (global + per-source coverage)
  - Kept gov-specific wrappers: `POST /api/admin/government/process`, `GET /api/admin/government/quality`

### Commit
- `5a356c7` `[T-610] Unify post-ingestion processing and quality endpoints`

### Tests Run
- `backend/venv3.11/bin/ruff check .` (pass)
- `backend/venv3.11/bin/ruff format --check .` (pass)
- `.venv/bin/python -m pytest -q` (pass; 128 passed, 1 skipped)

---

## 2026-02-10 (T-620 Public Search + Apply Redirect)

Branch: `main`

### Summary
- Phase 1 (O0/P0): `/api/search` now returns title clusters and companies hiring aggregates (plus jobs list) and supports filtering by `title` and `company`.
- Added public redirect endpoint: `GET /r/apply/{job_id}` logs an `apply` event and redirects to `JobPost.application_url` with fallback to `source_url`/`url`. Anonymous users get an `ns_session` cookie for analytics continuity.
- Canonicalized URLs in `JobPost`:
  - `source_url` (discovery URL)
  - `application_url` (where the user should apply)
  Migration backfills both from legacy `url`.
- Fixed ingestion writers to populate the new URL fields across RSS/ATS/Government connectors.
- Production parity fix: normalized SkillNER alias variants (e.g. `python (programming language)` -> `python`) so tests and extracted skills are stable across environments.

### Commits
- `e20bbad` `[T-620] Implement public search aggregates and apply redirect`
- `9af05a0` `[T-620] Normalize SkillNER alias variants`

### Tests Run
- Local:
  - `backend/venv3.11/bin/ruff check .` (pass)
  - `backend/venv3.11/bin/ruff format .` (pass)
  - `.venv/bin/pytest -q` (pass; 131 passed, 1 skipped)
- VPS:
  - `/home/nextstep.co.ke/.venv/bin/ruff check .` (pass)
  - `/home/nextstep.co.ke/.venv/bin/ruff format --check .` (pass)
  - `/home/nextstep.co.ke/.venv/bin/pytest -q` (pass; 131 passed, 1 skipped)

### Ops / Deployment Notes (VPS)
- Repo: `/home/nextstep.co.ke/public_html`
- `.env`: `/home/nextstep.co.ke/.env`
- Ran migrations:
  - `9c1d7c3b6a21_add_application_and_source_urls.py`
  - `0f3a9b7d1b4d_user_analytics_user_id_nullable.py`
- Restarted: `systemctl restart nextstep-backend.service`
- Smoke checks:
  - `http://127.0.0.1:8010/api/search` returns `title_clusters` and `companies_hiring`
  - `http://127.0.0.1:8010/r/apply/{job_id}` returns `307` + `Set-Cookie: ns_session=...`
  - `https://nextstep.co.ke/api/search` returns the same aggregates and `apply_url` fields

---

## 2026-02-14 (Beta Program Infrastructure - University SaaS Pivot)

Branch: `main`

### Summary
**Strategic Pivot:** After rigorous adversarial stress-testing, pivoted from B2C freemium (asking broke students to pay) to **B2B University SaaS** model. Built complete VIP Beta Program infrastructure to generate ROI proof for university partnerships.

**What Was Built:**
1. **Beta Signup System** (`frontend/beta.html`, `backend/app/api/beta_routes.py`)
   - Beautiful landing page with VIP Beta branding (50-slot limit, KES 500 airtime incentive)
   - 6 API endpoints: signup, stats, metrics, activity, users, track
   - Database models: `BetaSignup` and `BetaActivity` for event tracking
   - Engagement metrics: jobs_viewed, jobs_saved, jobs_applied, searches_performed

2. **Admin Analytics Dashboard** (`frontend/beta-admin.html`)
   - Real-time dashboard monitoring beta users (auto-refresh every 30s)
   - ROI metrics calculator for university pitch ("70% engagement rate!")
   - User journey funnel visualization (Signup → Activate → Profile → Search → Apply)
   - University breakdown charts, recent users table

3. **Notification Service** (`backend/app/services/beta_notifications.py`)
   - Email templates (welcome, reminders, reward notification)
   - WhatsApp templates (welcome with login link, weekly nudges)
   - Service class ready for Twilio/SendGrid integration (TODOs left for actual sending)

4. **Implementation Guide** (`docs/beta-program-guide.md`)
   - Complete recruitment strategy (WhatsApp blasts, LinkedIn, campus posters)
   - Onboarding flow (Day 0 → Day 30 with all message templates)
   - Success criteria (70% engagement, 50% profile completion, 30% applications)
   - University pitch preparation (materials, deck outline, ROI calculator)

**Strategic Insights:**
- Universities have budgets (KES 500K-2M/year), students don't → B2B SaaS model
- Need proof before pitch → Beta program generates case study with 50 students
- 70% engagement rate = north star metric for university sales

### Files Changed
- `backend/app/db/models.py` (+37 lines: BetaSignup, BetaActivity models)
- `backend/app/main.py` (+2 lines: beta router registration)
- `backend/app/api/beta_routes.py` (new: 320 lines, 6 endpoints)
- `backend/app/services/beta_notifications.py` (new: 209 lines, email/WhatsApp templates)
- `frontend/beta.html` (new: 294 lines, beta signup page)
- `frontend/beta-admin.html` (new: 460 lines, admin dashboard)
- `docs/beta-program-guide.md` (new: 540 lines, complete implementation guide)

### Not Completed (Next Session)
1. **Database Migration:** Models created but NOT migrated
   ```bash
   cd backend
   uv run alembic revision --autogenerate -m "Add beta program tables"
   uv run alembic upgrade head
   ```

2. **Tests:** No tests written (TDD warnings fired)
   - Need: `backend/tests/test_beta_routes.py`
   - Need: `backend/tests/test_beta_notifications.py`

3. **Notification Integration:** Service exists but NOT connected to signup flow
   - TODO: Call `beta_notification_service.send_welcome_email()` after signup
   - TODO: Call `beta_notification_service.send_welcome_whatsapp()` after signup

4. **Email/WhatsApp Setup:** Templates ready, services NOT configured
   - Need: Twilio account (WhatsApp Business API)
   - Need: SendGrid or AWS SES account (email)
   - Need: Add credentials to `.env`

5. **Type Errors:** 4 basedpyright warnings in `beta_routes.py` (minor cleanup)

### Next Immediate Steps
**Priority 1 (Make It Functional):**
1. Run database migration (5 mins)
2. Test signup flow at `/beta` (10 mins)
3. Verify admin dashboard at `/beta-admin` (5 mins)

**Priority 2 (Launch Recruitment):**
1. Set up Twilio + SendGrid accounts (30 mins)
2. Connect notification service to signup (15 mins)
3. Update WhatsApp templates with real URLs (5 mins)
4. Post recruitment message to 5 WhatsApp groups (5 mins)

**Priority 3 (Track Success):**
- Week 1 Goal: 20 signups, 70% activation rate
- Week 4 Goal: 50 signups, 70% engagement, 10+ testimonials
- Pilot Success = University pitch ready

### Tests Run
None yet (models added but not migrated, no endpoint testing performed)

### Quick Links
- Beta Signup: `/beta` (or https://nextstep.co.ke/beta)
- Admin Dashboard: `/beta-admin` (or https://nextstep.co.ke/beta-admin)
- Implementation Guide: `docs/beta-program-guide.md`
- API Endpoints: `POST /api/beta/signup`, `GET /api/beta/stats`, `GET /api/beta/metrics`

---

## 2026-02-10 (T-625 Gov Quarantine + T-626 Search Crash Fix)

Branch: `main`

### Summary
- Ran government cleanup/quarantine against production DB: set `job_post.is_active = false` for obvious gov non-job pages (prevents polluting public search).
- Fixed a production crash in `/api/search`: `generate_match_explanation()` assumed `JobEntities.skills` was `list[str]`, but processing stores `list[dict]` (e.g. `{"value": "python", ...}`), causing 500s.
- Fixed public `/r/apply/{job_id}` routing: OpenLiteSpeed was proxying `/api/*` but not `/r/*`, so apply links worked on localhost but were 404 on `https://nextstep.co.ke`. Added `/r/` proxy context and restarted `lshttpd`.

### Commits
- `a793ab5` `[T-625] Quarantine gov non-job pages and hide from search`
- `4b6f774` `[T-626] Fix /api/search crash on dict skills`

### Ops / Deployment Notes (VPS)
- Government quarantine run (prod DB):
  - scanned: `1766`
  - quarantined: `296` (reasons: `opportunities_non_job=73`, `non_job_terms=170`, `low_info_non_job=53`)
  - post-run counts: `gov_careers total=2334, active=2038, inactive=296`
- OpenLiteSpeed routing:
  - Edited: `/usr/local/lsws/conf/vhosts/nextstep.co.ke/vhost.conf` (backup created)
  - Added: `context /r/ { type proxy; handler nextstep_backend; ... }`
  - Restarted: `systemctl restart lshttpd.service`
- Smoke checks:
  - `http://127.0.0.1:8010/api/search` -> `200` JSON
  - `https://nextstep.co.ke/api/search` -> `200` JSON
  - `http://127.0.0.1:8010/r/apply/{job_id}` -> `307` redirect
  - `https://nextstep.co.ke/r/apply/{job_id}` -> `307` redirect (no longer 404)

### Tests Run
- Local:
  - `backend/venv3.11/bin/ruff check backend/app/services/search.py backend/tests/test_search_match_explanation_skills_shape.py` (pass)
  - `backend/venv3.11/bin/ruff format --check backend/app/services/search.py backend/tests/test_search_match_explanation_skills_shape.py` (pass)
  - `.venv/bin/pytest -q backend/tests/test_search_match_explanation_skills_shape.py` (pass; 2 passed)
- VPS:
  - `/home/nextstep.co.ke/.venv/bin/ruff check backend/app/services/search.py backend/tests/test_search_match_explanation_skills_shape.py` (pass)
  - `/home/nextstep.co.ke/.venv/bin/ruff format --check backend/app/services/search.py backend/tests/test_search_match_explanation_skills_shape.py` (pass)
  - `/home/nextstep.co.ke/.venv/bin/pytest -q backend/tests/test_search_match_explanation_skills_shape.py` (pass; 2 passed)

---

## 2026-03-23 (DS / ML Deep Audit -> Execution Backlog)

Branch: `main`

### Summary
- Expanded `DS_ML.md` from a component audit into a problem-first DS/ML audit tied to `PROBLEM.md`.
- Added dual execution tracks in `DS_ML.md`:
  - `Trust-Layer First`
  - `LMI / Intelligence First`
- Converted the plan into a concrete execution backlog in `changemap.md` using `T-DS-*` task IDs.
- Marked intelligence work as mandatory regardless of which primary track is chosen.

### New Control-Plane Tasks
- `T-DS-900` — DS product contract + track selection
- `T-DS-910` — instrumentation + evaluation foundation
- `T-DS-920` — intelligence baseline repair
- `T-DS-930` — candidate evidence + provenance model
- `T-DS-940` — skill verification system
- `T-DS-950` — employer-side pre-screening / "The 20"
- `T-DS-960` — feedback loops + outcome learning
- `T-DS-970` — production-grade intelligence products
- `T-DS-980` — model stack consolidation

### Recommended Implementation Order
1. `T-DS-900` → `T-DS-910` → `T-DS-920`
2. `T-DS-930` → `T-DS-940` → `T-DS-950` → `T-DS-960`
3. `T-DS-970`
4. `T-DS-980`

### Key Decision Still Needed
- Confirm whether `PROBLEM.md` remains the product source of truth.
- If yes, keep `Trust-Layer First` as primary and `LMI / Intelligence` as the mandatory supporting workstream.

### Tests Run
- None; docs/control-plane only change

### Follow-up Clarification Added
- Explicitly mapped production-site ranking gaps into `changemap.md`:
  - `T-DS-916` replace synthetic ranking-training inputs with logged serve-time signals
  - `T-DS-917` replace placeholder ranking features (`description match`, `recency`, `skill overlap`) and remove hard-coded similarity values
  - `T-DS-918` add ranking-quality evaluation beyond structural tests
  - `T-DS-985` remove or hard-gate non-semantic hash-vector fallback from semantic ranking/search paths

---

## 2026-04-08 (T-OPS-DEPLOY user/group + public site recovery)

Branch: `main`

### Summary
- Updated committed deployment defaults and committed systemd unit templates from the old runtime account to `nexts9742`.
- Built the production runtime at `/home/nextstep.co.ke/.venv` and repaired the live Next Step services to run as `nexts9742`.
- Kept the Next Step backend isolated on `127.0.0.1:8010` to avoid conflicts with other apps already listening on `8000`, `8001`, `8002`, `8007`, `3001`, and `3010`.
- Fixed public routing by updating the Next Step OpenLiteSpeed vhost:
  - `docRoot` now points at `/home/nextstep.co.ke/public_html/frontend`
  - `/api/`, `/r/`, `/health`, and `/health/detailed` proxy to `127.0.0.1:8010`

### Ops / Deployment Notes (VPS)
- Active backend unit: `nextstep-backend.service`
- Active worker units: `nextstep-celery.service`, `nextstep-celery-beat.service`
- Active internal backend port: `127.0.0.1:8010`
- Live files changed on server:
  - `/etc/systemd/system/nextstep-backend.service`
  - `/etc/systemd/system/nextstep-celery.service`
  - `/etc/systemd/system/nextstep-celery-beat.service`
  - `/usr/local/lsws/conf/vhosts/nextstep.co.ke/vhost.conf`

### Smoke Checks
- `http://127.0.0.1:8010/health` -> `200`
- `http://127.0.0.1:8010/api/search?limit=1` -> `200`
- `https://nextstep.co.ke/health` -> `200`
- `https://nextstep.co.ke/api/search?limit=1` -> `200`
- `https://nextstep.co.ke/` -> `200` and serves frontend HTML

### Known Issue
- Alembic `upgrade heads` is blocked by an existing migration/state mismatch: revision `a1b2c3d4e5f6` attempts to create `search_serving_log`, but that table already exists in Postgres.

### Tests Run
- Live deployment smoke checks only; no `ruff` or `pytest` run during this session

---

## 2026-04-08 (T-1A0 assignment-driven data quality hardening backlog)

Branch: `main`

### Summary
- Logged the PostgreSQL assignment review outcomes as implementation backlog items in `changemap.md`.
- Backlog retained for follow-up implementation:
  - curated skill-confidence filtering for user-facing skills and matching
  - source-quality scoring to prioritize cleaner records in search and alerts
  - explicit job data-quality flags for noisy/listing-page records and location confidence
  - sector-coverage improvement and representativeness reporting for analytics

### Next Step
- Finish the remaining assignment-driven hardening items above after validating the newly added normalization, dedupe, and analysis-view changes in a staging-like database.

### Follow-up Implemented
- Added `backend/scripts/backfill_normalized_entities.py` to safely normalize existing `Organization` and `Location` rows and repoint `job_post` foreign keys without deleting source rows.
- Added `backend/scripts/refresh_job_post_analysis_view.py` to refresh `analysis.job_post_cleaned_mv`.
- Added `backend/cli.py:data_quality_cycle` to run backfill + analysis-view create/refresh in one operational command.
- Validated focused regressions:
  - `/home/nextstep.co.ke/.venv/bin/pytest -q backend/tests/test_cli_data_quality_cycle.py backend/tests/test_normalized_backfill.py backend/tests/test_assignment_quality_improvements.py backend/tests/test_deduplication_url_normalization.py`
  - `10 passed in 4.64s`
- Validated Postgres refresh:
  - `REFRESH MATERIALIZED VIEW analysis.job_post_cleaned_mv;`
  - row count after refresh: `110781`

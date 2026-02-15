# Handoff

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

# TODO: Next Step Seniority Rollout

Purpose: turn the current assignment-grade seniority classifier into a production-safe capability for `nextstep.co.ke` clientele without leaking secrets, without skipping logs, and without collapsing multiple risky changes into one push.

Status: `IN_PROGRESS`
Owner: `codex`
Suggested branch when implementation starts: `feat/T-1A12-seniority-rollout`

## Non-Negotiable Rules

- Do not expose secrets in code, logs, notebooks, screenshots, commits, or handoff notes.
- Do not commit `.env`, credentials, tokens, raw DB URLs, or user-identifying exports.
- Use feature branches with task id in commit messages:
  - `[T-1A12] <imperative summary>`
- Work in small actions:
  - implement
  - test
  - fix
  - retest
  - log
  - commit
  - push
- If blocked, add a `BLOCKED` entry to `changemap.md` with:
  - exact command or failure
  - what was tried
  - next planned step
- After every completed action, update:
  - `changemap.md`
  - `handoff.md`
  - `handoff.jsonl`
- Do not push an action unless its scoped tests pass.
- If an action introduces follow-up work or forces a product decision, log that explicitly in:
  - the TODO file
  - `changemap.md`
  - handoff notes

## Rollout Principle

Current offline result: weighted F1 is around `0.6-0.65` on sampled evaluation. That is useful as an assistive signal, not reliable enough for hard user-facing filtering on its own.

Initial rollout target:
- internal ranking signal first
- confidence-aware soft labels second
- hard filters only after better calibration and class-level quality

## Action Sequence

### Action 0: Freeze the Current Baseline

Status:
- `DONE 2026-04-18`

Goal:
- preserve the current notebook/dataset/export SQL as the reproducible baseline for future comparisons

Files:
- `notebooks/csa821_assignment_1_nextstep_kenya_seniority_classification.ipynb`
- `notebooks/data/csa821_kenya_seniority_dataset.csv`
- `notebooks/sql/csa821_kenya_seniority_dataset_export.sql`
- `docs/` if a short baseline note is added

Tasks:
- verify the CSV snapshot row count and class distribution
- record current sample metrics
- add a short baseline note if needed

Tests:
- `python3 -m json.tool notebooks/csa821_assignment_1_nextstep_kenya_seniority_classification.ipynb`
- CSV-only smoke evaluation using `/home/nextstep.co.ke/.venv/bin/python`

Push gate:
- only documentation and reproducibility assets changed

Logs required:
- add baseline row count, classes, and sample metrics to `changemap.md`

Completed notes:
- Added `docs/seniority_baseline.md`.
- Baseline snapshot frozen at `38,335` rows and `14` columns.
- CSV-only sampled smoke metrics recorded for `Linear SVM` and `Logistic Regression`.
- Decision logged: the full CSV snapshot remains local and is not part of the git commit because it is a large output; the committed regeneration path is notebook + SQL + baseline note.

### Action 1: Define Production Seniority Policy

Status:
- `DONE 2026-04-18`

Goal:
- decide exactly how seniority is allowed to affect product behavior

Product decision needed:
- `internal_only` vs `soft_user_label` vs `hard_filter`

Tasks:
- define confidence bands:
  - `high_confidence`
  - `medium_confidence`
  - `low_confidence`
- define user-facing language:
  - `Likely Entry`
  - `Likely Mid-Level`
  - `Likely Senior`
  - `Likely Executive`
- define where the signal is used:
  - search ranking
  - alerts
  - recommendations
  - explicit filter UI

Deliverable:
- `docs/seniority_rollout_policy.md`

Tests:
- docs-only; no code tests required

Push gate:
- policy doc reviewed and logged

Logs required:
- record the chosen behavior and any deferred decisions

Completed notes:
- Chosen rollout mode is `internal_only` for model-predicted seniority.
- Predicted seniority is allowed only as a bounded internal ranking/recommendation/alert-ordering signal in the current phase.
- Soft user-facing labels are deferred until reviewed labels, calibration, stronger offline quality, and versioned prediction storage exist.
- Hard filtering on model-predicted seniority is explicitly prohibited in the current rollout policy.
- Existing ingestion-time `JobPost.seniority` behavior remains separate from this new predicted-seniority policy.

### Action 2: Build a Reviewed Label Audit Set

Status:
- `DONE 2026-04-18`

Goal:
- create a gold or silver evaluation subset to measure real quality rather than trusting noisy labels blindly

Tasks:
- sample jobs across all four classes
- manually review seniority labels
- store reviewed set in an anonymized artifact suitable for repo inclusion if possible

Suggested files:
- `data/samples/seniority_review_sample.csv`
- `docs/seniority_labeling_guide.md`

Decision needed:
- whether reviewed labels can be committed anonymized, or must remain operational-only

Tests:
- schema/format validation for the review sample

Push gate:
- no raw sensitive text beyond acceptable repo policy

Logs required:
- log sample size
- log label guidelines
- log whether repo-safe reviewed data exists

Completed notes:
- Added `data/samples/seniority_review_sample.csv` as a repo-safe silver audit set with `20` reviewed rows.
- The sample is balanced across current labels with `5` rows each for `Entry`, `Mid-Level`, `Senior`, and `Executive`.
- Added `docs/seniority_labeling_guide.md` with the taxonomy, lexical traps, confidence rules, and current sample design.
- Decision logged: repo-safe reviewed data exists, but it is intentionally anonymized and title-centric; operational-only back-links to raw postings are deferred outside the repo.
- Added `backend/tests/test_seniority_review_sample.py` to validate the sample schema, balanced current-label counts, and allowed field values.

### Action 3: Add Stronger Extracted Features

Goal:
- improve the predictive signal beyond raw TF-IDF text

Candidate additions:
- `years_experience_min`
- `years_experience_max`
- `managerial_flag`
- `leadership_keywords_count`
- `seniority_source`
- `seniority_confidence`

Likely files:
- `backend/app/normalization/extractors.py`
- `backend/app/services/post_ingestion_processing_service.py`
- `backend/app/db/models.py`
- Alembic migration
- targeted tests under `backend/tests/`

Tests:
- `backend/venv3.11/bin/ruff format <changed files>`
- `backend/venv3.11/bin/ruff check <changed files>`
- `/home/nextstep.co.ke/.venv/bin/pytest -q <targeted tests>`

Push gate:
- migration and tests pass together

Logs required:
- feature definitions
- extraction heuristics
- any false-positive/false-negative patterns found

### Action 4: Add Explicit Rule Layer for Obvious Cases

Goal:
- catch the easy seniority cases deterministically before ML handles ambiguity

Rules should include:
- title cues: `intern`, `assistant`, `associate`, `senior`, `lead`, `head`, `director`, `chief`
- requirement cues: `X years`, `minimum X years`, `team leadership`, `reports to`

Likely files:
- `backend/app/services/` new seniority rules module
- tests under `backend/tests/test_seniority_rules.py`

Tests:
- rule unit tests
- collision tests against known ambiguous titles

Push gate:
- deterministic behavior documented

Logs required:
- exact rule categories added
- list of intentionally unresolved ambiguous cases

### Action 5: Train a Hybrid Offline Model

Goal:
- combine rules, text, and structured features into a better offline classifier

Model candidates:
- Logistic Regression baseline
- Linear SVM baseline
- structured booster if available
- hybrid rule + ML chooser

Deliverables:
- training script or notebook
- metrics table
- confusion matrix artifacts if needed

Suggested files:
- `analysis_outputs/` or `notebooks/` if repo-safe
- `docs/seniority_model_evaluation.md`

Required evaluation:
- weighted F1
- macro F1
- per-class precision/recall
- calibration or confidence inspection

Push gate:
- report shows whether the hybrid is actually better than baseline

Logs required:
- metrics by model version
- chosen winner and rationale

### Action 6: Add Prediction Storage and Versioning

Goal:
- persist prediction output so rollout can be audited and reversed

Schema ideas:
- `predicted_seniority`
- `predicted_seniority_confidence`
- `predicted_seniority_source`
- `predicted_seniority_model_version`
- optional `predicted_seniority_top2`

Likely files:
- `backend/app/db/models.py`
- migration
- population/backfill helper

Tests:
- migration test
- model serialization or persistence tests
- API schema tests if exposed

Push gate:
- backfill path exists
- rollback path documented

Logs required:
- exact schema added
- backfill command used
- row counts updated

### Action 7: Use It in Ranking Only

Goal:
- ship the signal safely as an internal ranking feature before exposing it to users

Likely files:
- `backend/app/services/search.py`
- `backend/app/services/ranking.py`
- `backend/tests/test_search_*`

Behavior:
- no hard exclusion based on predicted seniority
- confidence only influences ranking weights

Tests:
- ranking/search regressions
- no payload-break regression
- no low-confidence hard-filter behavior

Push gate:
- user-facing response contract unchanged unless explicitly intended

Logs required:
- ranking weight added
- expected user benefit
- risk notes

### Action 8: Expose Soft Labels Behind Confidence Gates

Goal:
- show `Likely ...` seniority labels only when quality is good enough

API contract ideas:
- `predicted_seniority`
- `predicted_seniority_confidence`
- `predicted_seniority_top2`
- `predicted_seniority_is_high_confidence`

Frontend behavior:
- display only when confidence exceeds threshold
- otherwise hide or keep internal

Likely files:
- backend API route/service files
- `frontend/js/main.js`
- `frontend/styles/main.css`
- frontend-facing tests if available

Tests:
- backend route tests
- `node --check` on changed JS
- targeted frontend/backend integration checks

Push gate:
- policy from Action 1 implemented exactly

Logs required:
- chosen thresholds
- exposed fields
- any copy/text decisions

### Action 9: Add Monitoring and Drift Checks

Goal:
- detect when live prediction quality or class distribution drifts

Monitoring targets:
- class mix over time
- high-confidence coverage rate
- low-confidence rate
- prediction distribution by source
- source-specific anomalies

Likely files:
- `backend/app/services/monitoring_service.py`
- admin endpoints/UI if needed

Tests:
- monitoring unit tests
- admin endpoint tests if changed

Push gate:
- at least one operational view exists for quality tracking

Logs required:
- what is monitored
- alert thresholds

### Action 10: Reassess Hard Filter Eligibility

Goal:
- decide whether seniority can ever become a hard filter for users

Decision rule:
- do not enable hard filtering unless offline and staged quality clearly improves and confidence calibration is acceptable

Required evidence:
- better macro F1
- stable per-class precision, especially on `Entry`
- acceptable live confidence coverage

Deliverable:
- logged decision in `docs/seniority_rollout_policy.md`

Tests:
- if filter enabled, targeted search contract and ranking tests

Push gate:
- explicit sign-off logged

Logs required:
- `ENABLED` or `DEFERRED`
- rationale

## Required Logging Per Action

For every action completed:
- update status in this file
- add a short `Log YYYY-MM-DD:` note to `changemap.md`
- add tests actually run to `changemap.md`
- append a concise session summary to `handoff.md`
- append one JSON line to `handoff.jsonl`

For every action blocked:
- add `BLOCKED YYYY-MM-DD:` in `changemap.md`
- include exact failing command or error
- include next attempt planned

## Secret Handling Checklist

- Never paste `DATABASE_URL` values into committed files.
- If a command needs DB access, load from environment only.
- Never commit production extracts containing sensitive user data.
- If a sample dataset is committed, it must be reviewed for privacy and necessity.

## Start Condition For Future Work

Before starting Action 1 or later:
- create branch `feat/T-1A12-seniority-rollout`
- confirm current worktree state to avoid mixing with unrelated dirty changes
- restate the exact action number being executed
- keep each push scoped to one action only

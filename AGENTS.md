# Agents Operating Manual (Next Step)

## Mission
Build Next Step: job matching + labor market intelligence from jobs.sqlite3.

## Ralph Wiggum Loop Rules
- Work iteratively: implement → test → fix → retest → document → commit → push.
- Never stop after one pass.
- If blocked, write a BLOCKED entry to changemap.md with exact error + what you tried + next plan.

## Definition of Done (for every task)
- ruff check passes
- ruff format passes
- pytest passes
- docs updated when relevant
- changemap.md updated with status change + logs + tests run
- handoff.md and handoff.jsonl updated at session end
- commit with task id in message
- pushed to GitHub

## Branching & Commits
- Use feature branches: feat/<task-id>-short-name
- Commit message format:
  [<task-id>] <imperative summary>
- Push after each DONE task/feature.

## Repo Conventions (Discovered)
- `backend/`: FastAPI service, SQLAlchemy models, ingestion jobs.
- `frontend/`: static UI (HTML/JS/CSS).
- `dbt/`: analytics models.
- **Production Plan**: See [docs/ml-db-production-plan.md](file:///Users/hp/Library/CloudStorage/OneDrive-Personal/Codes/Next_step/docs/ml-db-production-plan.md) for ML/DB transition and VPS deployment rules.
- Default jobs DB: `jobs.sqlite3` (root, 1.2GB) or `backend/jobs.sqlite3` (sample/dev).
- App DB: `backend/var/nextstep.sqlite`.
- Virtual Env: `backend/venv3.11`.
- Tool paths:
  - `backend/venv3.11/bin/ruff`
  - `backend/venv3.11/bin/pytest`
- Skill extraction:
  - SkillNER data: `backend/app/normalization/skillner_data/`
  - Mapping file: `backend/app/normalization/skill_mapping.json`
  - Education mapping: `backend/app/normalization/education_mapping.json`
  - Config: `SKILL_EXTRACTOR_MODE` and `SKILLNER_DATA_DIR`

## Code Quality
- Small functions, typed interfaces where possible.
- Add tests for each parser/extractor/pipeline stage.
- Prefer deterministic, auditable extraction.
- Every extractor must return: value, confidence, evidence span/snippet.

## Data Handling
- Do not commit jobs.sqlite3 or large outputs.
- Commit only anonymized samples in data/samples/.

## Logging
- Pipelines must log: rows in/out, duplicates removed, confidence stats, runtime.
- Logs must be reproducible and deterministic.

## Safety / Privacy
- Scraped text may contain sensitive info.
- Redact personal data before committing samples.

# Agents Operating Manual (Next Step)

## Mission
Build Next Step: job matching + labor market intelligence from `jobs.sqlite3`.

## Workflow (Ralph Wiggum Loop)
- Work iteratively: implement -> test -> fix -> retest -> document -> commit -> push.
- If blocked, add a `BLOCKED` entry to `changemap.md` with the exact error, what you tried, and the next plan.

## Definition Of Done (For Every Task)
- `backend/venv3.11/bin/ruff check backend` passes
- `backend/venv3.11/bin/ruff format backend --check` passes
- `backend/venv3.11/bin/pytest` passes
- docs updated when relevant
- `changemap.md` updated (status + logs + tests run)
- `handoff.md` and `handoff.jsonl` updated at session end
- commit with task id in message
- pushed to GitHub

## Branching & Commits
- Feature branches: `feat/<task-id>-short-name`
- Commit message format: `[<task-id>] <imperative summary>`

## Repo Conventions (Discovered)
- `backend/`: FastAPI service, SQLAlchemy models, ingestion jobs, processing pipelines.
- `frontend/`: static UI (HTML/JS/CSS).
- `dbt/`: analytics models.
- Default jobs DB: `jobs.sqlite3` (root) or `backend/jobs.sqlite3` (sample/dev).
- App DB: `backend/var/nextstep.sqlite`.

## Dev Environment
- Virtual env path: `backend/venv3.11` (not committed to git).
- Create venv (example):
  - `python3.11 -m venv backend/venv3.11`
  - `backend/venv3.11/bin/pip install -r backend/requirements.txt`
  - `backend/venv3.11/bin/pip install -r backend/requirements-dev.txt`
- Tool paths:
  - `backend/venv3.11/bin/ruff`
  - `backend/venv3.11/bin/pytest`

## Code Quality
- Prefer small functions and typed interfaces where practical.
- Prefer deterministic, auditable extraction and processing.
- Every extractor should return: `value`, `confidence`, and `evidence` (span/snippet).

## Data Handling / Privacy
- Do not commit large DBs or outputs (`*.sqlite3`, `jobs.sqlite3`, `artifacts/`).
- Scraped text may contain sensitive info; redact personal data before committing samples.

## Security
- Keep secrets in `.env` only; never commit credentials/tokens.
- Treat DB contents as untrusted: avoid `eval` and other unsafe parsing patterns.

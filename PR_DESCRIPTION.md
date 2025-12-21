PR: Prepare async DB support, embedding fallback, and requirements updates

Summary
-------
This branch collects recent, tested changes that:  
- Add optional async SQLAlchemy engine support and a safer sync->async session shim in `app/db/database.py`.  
- Fix the insight-generation await/NoneType bug (flow fixes in automated workflow helpers).  
- Replace the temporary `sentence_transformers` stub with a lazy-loading real model path and an internal deterministic hash-based fallback in `app/services/ai_service.py` and `app/ml/embeddings.py`.  
- Relax the `torch` pin in `backend/requirements.txt` to `>=2.2.2,<2.4.0` and add notes about using a Python 3.11 venv for real-model runs.

Changed files (high-impact)
- `app/db/database.py` — optional async engine + sqlite auto-create + session shim
- `app/db/models.py` — JSONB -> JSON fallback for SQLite; added `ProcessingLog`
- `app/services/ai_service.py` — lazy-load `SentenceTransformer` with fallback
- `app/ml/embeddings.py` — deterministic fallback embedder + helpers
- `backend/requirements.txt` — relaxed `torch` pin

How to run tests (lightweight, quick)
1. Create and activate the lightweight venv (if not already):

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt
```

2. Set sqlite test DB and run tests:

```bash
export DATABASE_URL=sqlite:///./test_db.sqlite
pytest backend/test_automated_workflow.py -q
```

How to enable real sentence-transformers embeddings (optional, heavier)
1. Create Python 3.11 venv and install heavy ML deps (already validated locally):

```bash
python3.11 -m venv venv3.11
source venv3.11/bin/activate
pip install -r backend/requirements.txt
```

2. After activation, the service will lazily load `SentenceTransformer('all-MiniLM-L6-v2')`. If unavailable, it falls back to the deterministic hash embedder.

Migration notes / followups for PR
- Full conversion of all DB callers to `AsyncSession` is recommended (not yet completed). See `DEPLOYMENT.md` for a suggested migration plan.  
- CI: add a two-job matrix (fast: SQLite + fallback; integration: Postgres+Redis+real-ML on Python 3.11).

Contact / Testing notes
- I ran the automated workflow tests locally with `DATABASE_URL=sqlite:///./test_db.sqlite` and validated sentence-transformers loading in a Python 3.11 venv after downgrading `numpy` to `1.26.4` in that venv.

Next steps I can do on this branch
- Create branch `feature/async-db-embeddings-fallback`, commit the changes, run full `pytest -q` and push & open a PR draft.

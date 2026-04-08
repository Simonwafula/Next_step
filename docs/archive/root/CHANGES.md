Changelog — recent test-enabling and async/embedding changes

Summary of changes
- Added optional async SQLAlchemy support and a sync->async session shim to allow current callers to `await` without breaking tests. See `app/db/database.py`.
- Added JSON fallback for SQLite and `ProcessingLog` model entries in `app/db/models.py`.
- Replaced temporary ML stubs with a lazy-loading path to `sentence-transformers` and a deterministic fallback embedder in `app/services/ai_service.py` and `app/ml/embeddings.py`.
- Relaxed `torch` pin in `backend/requirements.txt` (`>=2.2.2,<2.4.0`) and validated installation in a Python 3.11 venv.

Notes
- Tests were validated locally using `DATABASE_URL=sqlite:///./test_db.sqlite` (file DB) and `pytest backend/test_automated_workflow.py` completed successfully.
- Real-ML mode requires Python 3.11 and the heavier wheel installs; local validation used `venv3.11` and `numpy==1.26.4` to avoid runtime incompatibilities.

Recommended follow-ups
- Migrate DB callers to native `AsyncSession` across the codebase.
- Add CI job matrix for light vs integration tests.

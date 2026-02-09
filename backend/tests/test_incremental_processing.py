"""Tests for incremental dedup and embeddings refresh (T-601c)."""

import json

from app.db.models import JobDedupeMap, JobEmbedding, JobPost
from app.ml.embeddings import run_incremental_embeddings
from app.normalization.dedupe import run_incremental_dedup


def _add_job(db, job_id_hint, text, source="test"):
    """Helper to insert a JobPost with a description."""
    job = JobPost(
        source=source,
        url=f"https://example.com/job/{job_id_hint}",
        url_hash=f"hash-{job_id_hint}",
        title_raw=f"Job {job_id_hint}",
        description_raw=text,
    )
    db.add(job)
    db.flush()
    return job


# ---------------------------------------------------------------------------
# Incremental Dedup
# ---------------------------------------------------------------------------


class TestIncrementalDedup:
    def test_no_jobs_returns_zero(self, db_session_factory):
        db = db_session_factory()
        result = run_incremental_dedup(db)
        assert result["status"] == "success"
        assert result["processed"] == 0
        assert result["duplicates_found"] == 0
        db.close()

    def test_new_unique_jobs_get_self_mapped(self, db_session_factory):
        db = db_session_factory()
        _add_job(db, 1, "Build scalable microservices with Python and FastAPI")
        _add_job(db, 2, "Design marketing campaigns for consumer products")
        db.commit()

        result = run_incremental_dedup(db)
        assert result["processed"] == 2

        maps = db.query(JobDedupeMap).all()
        assert len(maps) == 2
        # Unique jobs map to themselves
        for m in maps:
            assert m.job_id == m.canonical_job_id
            assert m.similarity_score == 1.0
        db.close()

    def test_duplicate_detected(self, db_session_factory):
        db = db_session_factory()
        text = "We are looking for a senior software engineer to build REST APIs using Python Flask. Must have 5 years experience with cloud infrastructure."
        _add_job(db, 1, text)
        _add_job(db, 2, text)  # exact duplicate
        db.commit()

        result = run_incremental_dedup(db)
        assert result["processed"] == 2
        assert result["duplicates_found"] >= 1

        # One of them should point to the other
        dupe_maps = (
            db.query(JobDedupeMap)
            .filter(JobDedupeMap.job_id != JobDedupeMap.canonical_job_id)
            .all()
        )
        assert len(dupe_maps) >= 1
        db.close()

    def test_incremental_skips_already_processed(self, db_session_factory):
        db = db_session_factory()
        _add_job(db, 1, "Unique job about data science and machine learning")
        db.commit()

        # First run processes the job
        result1 = run_incremental_dedup(db)
        assert result1["processed"] == 1

        # Second run finds nothing new
        result2 = run_incremental_dedup(db)
        assert result2["processed"] == 0
        db.close()

    def test_incremental_processes_only_new(self, db_session_factory):
        db = db_session_factory()
        _add_job(db, 1, "Frontend developer React TypeScript position")
        db.commit()
        run_incremental_dedup(db)

        # Add a new job
        _add_job(db, 2, "Backend developer Python Django position")
        db.commit()

        result = run_incremental_dedup(db)
        assert result["processed"] == 1
        assert result["baseline_size"] == 1
        db.close()


# ---------------------------------------------------------------------------
# Incremental Embeddings
# ---------------------------------------------------------------------------


class TestIncrementalEmbeddings:
    def test_no_jobs_returns_zero(self, db_session_factory):
        db = db_session_factory()
        result = run_incremental_embeddings(db)
        assert result["status"] == "success"
        assert result["processed"] == 0
        db.close()

    def test_embeds_new_jobs(self, db_session_factory):
        db = db_session_factory()
        _add_job(db, 1, "Software engineering role building APIs")
        _add_job(db, 2, "Marketing manager for growth team")
        db.commit()

        result = run_incremental_embeddings(db)
        assert result["processed"] == 2
        assert result["model"] == "e5-small-v2"

        embeddings = db.query(JobEmbedding).all()
        assert len(embeddings) == 2
        for emb in embeddings:
            assert emb.model_name == "e5-small-v2"
            vec = (
                json.loads(emb.vector_json)
                if isinstance(emb.vector_json, str)
                else emb.vector_json
            )
            assert isinstance(vec, list)
            assert len(vec) > 0
        db.close()

    def test_incremental_skips_already_embedded(self, db_session_factory):
        db = db_session_factory()
        _add_job(db, 1, "Data analyst role with SQL and Python")
        db.commit()

        result1 = run_incremental_embeddings(db)
        assert result1["processed"] == 1

        result2 = run_incremental_embeddings(db)
        assert result2["processed"] == 0
        db.close()

    def test_incremental_processes_only_new(self, db_session_factory):
        db = db_session_factory()
        _add_job(db, 1, "DevOps engineer managing CI/CD pipelines")
        db.commit()
        run_incremental_embeddings(db)

        _add_job(db, 2, "Product manager for SaaS platform")
        db.commit()

        result = run_incremental_embeddings(db)
        assert result["processed"] == 1

        total_embeddings = db.query(JobEmbedding).count()
        assert total_embeddings == 2
        db.close()

    def test_skips_null_descriptions(self, db_session_factory):
        db = db_session_factory()
        job = JobPost(
            source="test",
            url="https://example.com/job/no-desc",
            url_hash="hash-no-desc",
            title_raw="No Description Job",
            description_raw=None,
        )
        db.add(job)
        db.commit()

        result = run_incremental_embeddings(db)
        assert result["processed"] == 0
        db.close()

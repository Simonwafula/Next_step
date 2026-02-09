"""Tests for upsert helpers (T-732)."""

from app.db.models import JobPost, Organization, Skill
from app.db.upsert import (
    bulk_upsert_jobs,
    upsert_job_post,
    upsert_organization,
    upsert_skill,
)


class TestUpsertJobPost:
    def test_insert_new(self, db_session_factory):
        db = db_session_factory()
        job_id = upsert_job_post(
            db,
            {
                "source": "test",
                "url": "https://example.com/1",
                "url_hash": "h1",
                "title_raw": "Dev",
                "description_raw": "Build things",
            },
        )
        assert job_id is not None
        assert db.query(JobPost).count() == 1
        db.close()

    def test_update_existing_enriches(self, db_session_factory):
        db = db_session_factory()
        upsert_job_post(
            db,
            {
                "source": "test",
                "url": "https://example.com/1",
                "url_hash": "h1",
                "title_raw": "Dev",
            },
        )
        job_id = upsert_job_post(
            db,
            {
                "source": "test",
                "url": "https://example.com/1",
                "url_hash": "h1",
                "title_raw": "Dev",
                "salary_min": 50000,
            },
        )
        assert db.query(JobPost).count() == 1
        job = db.get(JobPost, job_id)
        assert job.salary_min == 50000
        db.close()

    def test_does_not_overwrite_existing_fields(self, db_session_factory):
        db = db_session_factory()
        upsert_job_post(
            db,
            {
                "source": "test",
                "url": "https://example.com/1",
                "url_hash": "h1",
                "title_raw": "Dev",
                "salary_min": 80000,
            },
        )
        upsert_job_post(
            db,
            {
                "source": "test",
                "url": "https://example.com/1",
                "url_hash": "h1",
                "title_raw": "Dev",
                "salary_min": 50000,
            },
        )
        job = db.query(JobPost).first()
        # Original salary_min should be kept (COALESCE prefers existing)
        assert job.salary_min == 80000
        db.close()


class TestUpsertOrganization:
    def test_insert_new(self, db_session_factory):
        db = db_session_factory()
        org_id = upsert_organization(db, "Acme Corp", sector="tech")
        assert org_id is not None
        assert db.query(Organization).count() == 1
        db.close()

    def test_returns_existing(self, db_session_factory):
        db = db_session_factory()
        id1 = upsert_organization(db, "Acme Corp")
        id2 = upsert_organization(db, "Acme Corp")
        assert id1 == id2
        assert db.query(Organization).count() == 1
        db.close()

    def test_empty_name_returns_none(self, db_session_factory):
        db = db_session_factory()
        assert upsert_organization(db, "") is None
        db.close()


class TestUpsertSkill:
    def test_insert_new(self, db_session_factory):
        db = db_session_factory()
        skill_id = upsert_skill(db, "Python")
        assert skill_id is not None
        assert db.query(Skill).count() == 1
        db.close()

    def test_returns_existing(self, db_session_factory):
        db = db_session_factory()
        id1 = upsert_skill(db, "Python")
        id2 = upsert_skill(db, "Python")
        assert id1 == id2
        db.close()

    def test_empty_name_returns_none(self, db_session_factory):
        db = db_session_factory()
        assert upsert_skill(db, "") is None
        db.close()


class TestBulkUpsertJobs:
    def test_bulk_insert(self, db_session_factory):
        db = db_session_factory()
        jobs = [
            {
                "source": "test",
                "url": f"https://example.com/{i}",
                "url_hash": f"h{i}",
                "title_raw": f"Job {i}",
            }
            for i in range(5)
        ]
        result = bulk_upsert_jobs(db, jobs)
        assert result["inserted"] == 5
        assert result["updated"] == 0
        assert result["errors"] == 0
        assert db.query(JobPost).count() == 5
        db.close()

    def test_bulk_mixed(self, db_session_factory):
        db = db_session_factory()
        upsert_job_post(
            db,
            {
                "source": "test",
                "url": "https://example.com/0",
                "url_hash": "h0",
                "title_raw": "Existing",
            },
        )
        jobs = [
            {
                "source": "test",
                "url": "https://example.com/0",
                "url_hash": "h0",
                "title_raw": "Existing",
            },
            {
                "source": "test",
                "url": "https://example.com/1",
                "url_hash": "h1",
                "title_raw": "New",
            },
        ]
        result = bulk_upsert_jobs(db, jobs)
        assert result["inserted"] == 1
        assert result["updated"] == 1
        assert db.query(JobPost).count() == 2
        db.close()

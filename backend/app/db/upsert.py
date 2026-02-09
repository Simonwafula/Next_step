"""Postgres-friendly upsert helpers for incremental bulk loads (T-732).

These functions use ``INSERT … ON CONFLICT`` to efficiently merge new data
into existing tables without round-tripping each row through Python.

For SQLite (dev/test) environments the helpers fall back to SQLAlchemy ORM
merge patterns so the same call-sites work everywhere.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from .models import JobPost, Organization, Skill

logger = logging.getLogger(__name__)


def _is_postgres(db: Session) -> bool:
    return db.bind.dialect.name == "postgresql" if db.bind else False


# ---------------------------------------------------------------------------
# Job post upsert (by url_hash)
# ---------------------------------------------------------------------------


def upsert_job_post(db: Session, data: dict[str, Any]) -> int | None:
    """Insert a job post or update ``last_seen`` + enrich empty fields.

    *data* must contain at least ``url``, ``url_hash``, ``source``.
    Returns the ``job_post.id`` on success, ``None`` on error.
    """
    now = datetime.utcnow()
    data.setdefault("first_seen", now)
    data.setdefault("last_seen", now)

    if _is_postgres(db):
        return _pg_upsert_job_post(db, data)
    return _orm_upsert_job_post(db, data)


def _pg_upsert_job_post(db: Session, data: dict[str, Any]) -> int | None:
    cols = [
        "source",
        "url",
        "url_hash",
        "title_raw",
        "org_id",
        "location_id",
        "title_norm_id",
        "tenure",
        "salary_min",
        "salary_max",
        "currency",
        "seniority",
        "description_raw",
        "requirements_raw",
        "education",
        "first_seen",
        "last_seen",
    ]
    present = {c: data[c] for c in cols if c in data}
    col_names = ", ".join(present.keys())
    placeholders = ", ".join(f":{c}" for c in present.keys())
    update_set = ", ".join(
        f"{c} = COALESCE(EXCLUDED.{c}, job_post.{c})"
        for c in present.keys()
        if c not in ("url", "url_hash", "source", "first_seen")
    )
    update_set += ", last_seen = EXCLUDED.last_seen"

    sql = text(
        f"INSERT INTO job_post ({col_names}) VALUES ({placeholders}) "
        f"ON CONFLICT (url_hash) DO UPDATE SET {update_set} "
        "RETURNING id"
    )
    result = db.execute(sql, present)
    row = result.fetchone()
    db.commit()
    return row[0] if row else None


def _orm_upsert_job_post(db: Session, data: dict[str, Any]) -> int | None:
    existing = (
        db.query(JobPost).filter(JobPost.url_hash == data.get("url_hash")).first()
    )
    if existing:
        existing.last_seen = data.get("last_seen", datetime.utcnow())
        for field in (
            "org_id",
            "location_id",
            "title_norm_id",
            "tenure",
            "salary_min",
            "salary_max",
            "currency",
            "seniority",
            "description_raw",
            "requirements_raw",
            "education",
        ):
            if data.get(field) and not getattr(existing, field, None):
                setattr(existing, field, data[field])
        db.commit()
        return existing.id

    job = JobPost(**{k: v for k, v in data.items() if hasattr(JobPost, k)})
    db.add(job)
    db.commit()
    db.refresh(job)
    return job.id


# ---------------------------------------------------------------------------
# Organization upsert (by name)
# ---------------------------------------------------------------------------


def upsert_organization(db: Session, name: str, **extras: Any) -> int | None:
    if not name:
        return None
    if _is_postgres(db):
        return _pg_upsert_org(db, name, extras)
    return _orm_upsert_org(db, name, extras)


def _pg_upsert_org(db: Session, name: str, extras: dict) -> int | None:
    sql = text(
        "INSERT INTO organization (name, sector, ats, verified) "
        "VALUES (:name, :sector, :ats, :verified) "
        "ON CONFLICT (name) DO UPDATE SET "
        "  sector = COALESCE(EXCLUDED.sector, organization.sector), "
        "  ats = COALESCE(EXCLUDED.ats, organization.ats) "
        "RETURNING id"
    )
    result = db.execute(
        sql,
        {
            "name": name,
            "sector": extras.get("sector"),
            "ats": extras.get("ats"),
            "verified": extras.get("verified", False),
        },
    )
    row = result.fetchone()
    db.commit()
    return row[0] if row else None


def _orm_upsert_org(db: Session, name: str, extras: dict) -> int | None:
    org = db.query(Organization).filter(Organization.name == name).first()
    if org:
        for k, v in extras.items():
            if v and not getattr(org, k, None):
                setattr(org, k, v)
        db.commit()
        return org.id
    org = Organization(name=name, **extras)
    db.add(org)
    db.commit()
    db.refresh(org)
    return org.id


# ---------------------------------------------------------------------------
# Skill upsert (by name)
# ---------------------------------------------------------------------------


def upsert_skill(db: Session, name: str) -> int | None:
    if not name:
        return None
    if _is_postgres(db):
        result = db.execute(
            text(
                "INSERT INTO skill (name) VALUES (:name) "
                "ON CONFLICT (name) DO NOTHING "
                "RETURNING id"
            ),
            {"name": name},
        )
        row = result.fetchone()
        if row:
            db.commit()
            return row[0]
        # Already exists
        row = db.execute(
            text("SELECT id FROM skill WHERE name = :name"), {"name": name}
        ).fetchone()
        return row[0] if row else None

    existing = db.query(Skill).filter(Skill.name == name).first()
    if existing:
        return existing.id
    skill = Skill(name=name)
    db.add(skill)
    db.commit()
    db.refresh(skill)
    return skill.id


# ---------------------------------------------------------------------------
# Bulk upsert convenience
# ---------------------------------------------------------------------------


def bulk_upsert_jobs(db: Session, jobs: list[dict[str, Any]]) -> dict:
    """Upsert a list of job dicts. Returns summary counts."""
    inserted = 0
    updated = 0
    errors = 0
    for job_data in jobs:
        try:
            existing = (
                db.query(JobPost)
                .filter(JobPost.url_hash == job_data.get("url_hash"))
                .first()
            )
            result_id = upsert_job_post(db, job_data)
            if result_id:
                if existing:
                    updated += 1
                else:
                    inserted += 1
        except Exception:
            logger.exception("Failed to upsert job: %s", job_data.get("url"))
            db.rollback()
            errors += 1
    return {"inserted": inserted, "updated": updated, "errors": errors}

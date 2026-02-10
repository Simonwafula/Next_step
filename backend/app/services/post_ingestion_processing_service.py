from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import Any, Dict

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from ..db.models import JobEntities, JobPost, JobSkill, TitleNorm
from ..db.upsert import upsert_skill
from ..normalization.extractors import (
    classify_seniority_detailed,
    extract_education_detailed,
    extract_experience_years_detailed,
    extract_task_statements,
)
from ..normalization.skills import extract_skills_detailed
from ..normalization.titles import normalize_title


def _clean_text(text: str | None) -> str | None:
    if not text:
        return None
    cleaned = " ".join(str(text).split()).strip()
    return cleaned or None


def _is_generic_title(title: str | None) -> bool:
    if not title:
        return True
    t = title.strip().lower()
    if not t:
        return True
    return t in {
        "job posting",
        "career opportunity",
        "vacancies",
        "vacancy",
        "careers",
        "jobs",
        "job",
        "opportunities",
    }


def _quality_score(
    *,
    title: str | None,
    description: str | None,
    org_id: int | None,
    salary_min: float | None,
    salary_max: float | None,
    skills_count: int,
) -> float:
    """Deterministic quality score in [0, 1] for monitoring."""
    score = 0.0

    if title and not _is_generic_title(title):
        score += 0.25

    if description:
        score += min(len(description) / 800.0, 1.0) * 0.35

    if skills_count >= 5:
        score += 0.2
    elif skills_count >= 2:
        score += 0.12
    elif skills_count >= 1:
        score += 0.07

    if org_id is not None:
        score += 0.1

    if salary_min is not None or salary_max is not None:
        score += 0.1

    return round(min(max(score, 0.0), 1.0), 4)


def _get_or_create_title_norm(
    db: Session, family: str, canonical_title: str
) -> int | None:
    if not family or not canonical_title:
        return None
    existing = (
        db.query(TitleNorm)
        .filter(
            TitleNorm.family == family,
            TitleNorm.canonical_title == canonical_title,
        )
        .one_or_none()
    )
    if existing:
        return existing.id
    tn = TitleNorm(family=family, canonical_title=canonical_title, aliases={})
    db.add(tn)
    db.flush()
    return tn.id


def _upsert_job_entities(db: Session, job_id: int, payload: Dict[str, Any]) -> None:
    existing = db.query(JobEntities).filter(JobEntities.job_id == job_id).one_or_none()
    if existing:
        existing.entities = payload
        existing.skills = payload.get("skills", []) or []
        existing.education = payload.get("education", {}) or {}
        existing.experience = payload.get("experience", {}) or {}
        db.add(existing)
        return

    je = JobEntities(
        job_id=job_id,
        entities=payload,
        skills=payload.get("skills", []) or [],
        tools=[],
        education=payload.get("education", {}) or {},
        experience=payload.get("experience", {}) or {},
    )
    db.add(je)


def process_job_posts(
    db: Session,
    *,
    source: str | None = None,
    limit: int = 500,
    only_unprocessed: bool = True,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Post-ingestion processing for any `job_post` rows.

    Does not fetch remote content; it only processes what's already in DB.
    This makes it safe and deterministic and gives clear visibility into
    which sources are failing to provide enough text for extraction.
    """
    started_at = datetime.utcnow()

    q = db.query(JobPost)
    if source:
        q = q.filter(JobPost.source == source)
    if only_unprocessed:
        q = q.filter(JobPost.processed_at.is_(None))

    jobs = q.order_by(JobPost.first_seen.desc()).limit(limit).all()

    processed = 0
    title_normed = 0
    skills_upserted = 0
    jobskills_created = 0
    quality_scores: list[float] = []
    reasons = Counter()

    # Cache Skill.name -> id during a run to avoid repeated lookups.
    skill_cache: dict[str, int] = {}

    now = datetime.utcnow()
    for job in jobs:
        title_raw = _clean_text(job.title_raw) or job.title_raw
        desc_raw = _clean_text(job.description_raw)

        family, canonical = normalize_title(title_raw or "")
        tn_id = _get_or_create_title_norm(db, family, canonical)
        if tn_id and job.title_norm_id != tn_id:
            job.title_norm_id = tn_id
            title_normed += 1

        skills_detailed = extract_skills_detailed(desc_raw or "")
        skills_sorted = sorted(
            skills_detailed.values(),
            key=lambda x: x.get("confidence", 0.0),
            reverse=True,
        )

        edu_d = extract_education_detailed(desc_raw or "")
        exp_d = extract_experience_years_detailed(desc_raw or "")
        seniority_d = classify_seniority_detailed(
            title_raw or "", exp_d["value"] if exp_d else None
        )
        tasks_d = extract_task_statements(job.description_raw or "")

        existing_skill_ids = set()
        if job.id:
            existing_skill_ids = {
                row[0]
                for row in db.execute(
                    select(JobSkill.skill_id).where(JobSkill.job_post_id == job.id)
                ).all()
            }

        for sd in skills_sorted:
            name = str(sd.get("value") or "").strip()
            if not name:
                continue
            if name in skill_cache:
                sid = skill_cache[name]
            else:
                sid = upsert_skill(db, name)
                if sid:
                    skill_cache[name] = sid
                    skills_upserted += 1

            if not sid or sid in existing_skill_ids:
                continue

            js = JobSkill(
                job_post_id=job.id,
                skill_id=sid,
                confidence=float(sd.get("confidence") or 0.5),
            )
            db.add(js)
            existing_skill_ids.add(sid)
            jobskills_created += 1

        job.description_clean = desc_raw
        if edu_d and edu_d.get("value"):
            job.education = str(edu_d["value"])
        if seniority_d and seniority_d.get("value"):
            job.seniority = str(seniority_d["value"])

        qscore = _quality_score(
            title=title_raw,
            description=desc_raw,
            org_id=job.org_id,
            salary_min=job.salary_min,
            salary_max=job.salary_max,
            skills_count=len(skills_sorted),
        )
        job.quality_score = qscore
        quality_scores.append(qscore)

        if not desc_raw:
            reasons["missing_description"] += 1
        if _is_generic_title(title_raw):
            reasons["generic_title"] += 1
        if len(skills_sorted) == 0:
            reasons["no_skills"] += 1

        entities_payload: Dict[str, Any] = {
            "skills": skills_sorted[:50],
            "education": edu_d or {},
            "experience": exp_d or {},
            "seniority": seniority_d or {},
            "tasks": tasks_d[:30],
            "processed_at": now.isoformat(),
            "source": "post_ingestion_processing_service",
        }
        _upsert_job_entities(db, job.id, entities_payload)

        job.processed_at = now
        db.add(job)
        processed += 1

    duration_s = (datetime.utcnow() - started_at).total_seconds()
    result = {
        "status": "success",
        "source": source,
        "processed": processed,
        "limit": limit,
        "only_unprocessed": only_unprocessed,
        "dry_run": dry_run,
        "title_norm_updated": title_normed,
        "skills_upserted": skills_upserted,
        "job_skills_created": jobskills_created,
        "quality": {
            "avg": round(sum(quality_scores) / len(quality_scores), 4)
            if quality_scores
            else 0.0,
            "min": min(quality_scores) if quality_scores else 0.0,
            "max": max(quality_scores) if quality_scores else 0.0,
        },
        "flags": dict(reasons),
        "duration_seconds": round(duration_s, 2),
    }

    if dry_run:
        db.rollback()
        return result

    db.commit()
    return result


def quality_snapshot(db: Session) -> Dict[str, Any]:
    """Coverage snapshot across all sources + per-source breakdown."""
    total = db.execute(select(func.count(JobPost.id))).scalar() or 0
    processed = (
        db.execute(
            select(func.count(JobPost.id)).where(JobPost.processed_at.is_not(None))
        ).scalar()
        or 0
    )
    with_desc = (
        db.execute(
            select(func.count(JobPost.id)).where(JobPost.description_raw.is_not(None))
        ).scalar()
        or 0
    )
    with_quality = (
        db.execute(
            select(func.count(JobPost.id)).where(JobPost.quality_score.is_not(None))
        ).scalar()
        or 0
    )
    with_entities = db.execute(select(func.count(JobEntities.id))).scalar() or 0

    rows = db.execute(
        select(
            JobPost.source,
            func.count(JobPost.id),
            func.sum(case((JobPost.processed_at.is_not(None), 1), else_=0)),
            func.sum(case((JobPost.description_raw.is_not(None), 1), else_=0)),
            func.sum(case((JobPost.quality_score.is_not(None), 1), else_=0)),
        ).group_by(JobPost.source)
    ).all()

    by_source = []
    for source, c_total, c_processed, c_desc, c_quality in rows:
        c_total = int(c_total or 0)
        c_processed = int(c_processed or 0)
        c_desc = int(c_desc or 0)
        c_quality = int(c_quality or 0)
        by_source.append(
            {
                "source": source,
                "total": c_total,
                "processed": c_processed,
                "coverage": {
                    "description_raw": round(c_desc / c_total * 100, 1)
                    if c_total
                    else 0,
                    "quality_score": round(c_quality / c_total * 100, 1)
                    if c_total
                    else 0,
                    "processed_at": round(c_processed / c_total * 100, 1)
                    if c_total
                    else 0,
                },
            }
        )

    by_source.sort(key=lambda x: x["total"], reverse=True)

    return {
        "totals": {
            "jobs": total,
            "processed": processed,
        },
        "coverage": {
            "description_raw": {
                "count": with_desc,
                "percentage": round(with_desc / total * 100, 1) if total else 0,
            },
            "quality_score": {
                "count": with_quality,
                "percentage": round(with_quality / total * 100, 1) if total else 0,
            },
            "job_entities": {
                "count": with_entities,
                "percentage": round(with_entities / total * 100, 1) if total else 0,
            },
            "processed_at": {
                "count": processed,
                "percentage": round(processed / total * 100, 1) if total else 0,
            },
        },
        "by_source": by_source,
    }

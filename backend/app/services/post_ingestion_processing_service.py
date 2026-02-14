from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import Any, Dict

from sqlalchemy import select
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
from .processing_quality import calculate_quality_score, is_generic_title


def _clean_text(text: str | None) -> str | None:
    if not text:
        return None
    cleaned = " ".join(str(text).split()).strip()
    return cleaned or None


def _get_or_create_title_norm(
    db: Session, family: str, canonical_title: str
) -> int | None:
    if not family or not canonical_title:
        return None
    # TitleNorm columns are constrained (String(120)); clamp to avoid runtime
    # failures when upstream sources produce very long titles/snippets.
    family = str(family)[:120]
    canonical_title = str(canonical_title)[:120]
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


def _upsert_job_entities(
    db: Session,
    job_id: int,
    payload: Dict[str, Any],
) -> None:
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

        qscore = calculate_quality_score(
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
        if is_generic_title(title_raw):
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

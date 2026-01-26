from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import select, func, desc
from sqlalchemy.orm import Session

from ..db.models import (
    JobPost,
    Organization,
    TitleNorm,
    TenderNotice,
    SignalEvidence,
    TaskRoleMapping,
    HiringSignal,
)
from ..normalization.extractors import extract_task_statements


TASK_ROLE_KEYWORDS = {
    "data_analytics": [
        "analyze",
        "analysis",
        "dashboard",
        "reporting",
        "sql",
        "metrics",
    ],
    "software_engineering": [
        "build",
        "develop",
        "deploy",
        "api",
        "backend",
        "frontend",
    ],
    "project_management": ["plan", "coordinate", "deliver", "timeline", "stakeholder"],
    "sales": ["prospect", "pipeline", "deal", "quota", "crm"],
    "marketing": ["campaign", "content", "brand", "social", "growth"],
    "finance": ["budget", "forecast", "audit", "reconcile", "ledger"],
}


def _map_task_to_role(task_text: str) -> tuple[str | None, float]:
    text = (task_text or "").lower()
    for role_family, keywords in TASK_ROLE_KEYWORDS.items():
        matches = sum(1 for keyword in keywords if keyword in text)
        if matches:
            confidence = min(0.9, 0.3 + (matches / max(len(keywords), 1)))
            return role_family, round(confidence, 2)
    return None, 0.0


def build_task_role_mappings(db: Session, limit: int = 200) -> dict:
    jobs = (
        db.execute(
            select(JobPost)
            .where(JobPost.description_raw.is_not(None))
            .order_by(desc(JobPost.first_seen))
            .limit(limit)
        )
        .scalars()
        .all()
    )
    created = 0
    for job in jobs:
        tasks = extract_task_statements(job.description_raw or "")
        for task in tasks:
            role_family, confidence = _map_task_to_role(task["value"])
            if not role_family:
                continue
            evidence = SignalEvidence(
                evidence_type="task_statement",
                source="job_post",
                source_url=job.url,
                snippet=task["evidence"],
                confidence=task["confidence"],
                meta_json={"job_id": job.id},
            )
            db.add(evidence)
            db.flush()
            mapping = TaskRoleMapping(
                task_text=task["value"],
                role_family=role_family,
                confidence=min(task["confidence"], confidence),
                evidence_id=evidence.id,
            )
            db.add(mapping)
            created += 1
    db.commit()
    return {"status": "success", "created": created}


def list_tenders(db: Session, limit: int = 50, offset: int = 0) -> dict:
    stmt = (
        select(TenderNotice)
        .order_by(desc(TenderNotice.published_at))
        .offset(offset)
        .limit(limit)
    )
    rows = db.execute(stmt).scalars().all()
    return {
        "tenders": [
            {
                "id": row.id,
                "title": row.title,
                "organization": row.organization,
                "category": row.category,
                "location": row.location,
                "published_at": row.published_at.isoformat()
                if row.published_at
                else None,
                "closing_at": row.closing_at.isoformat() if row.closing_at else None,
                "url": row.url,
            }
            for row in rows
        ],
        "total": len(rows),
    }


def generate_hiring_signals(db: Session, days: int = 30, limit: int = 50) -> dict:
    since = datetime.utcnow() - timedelta(days=max(days, 1))
    stmt = (
        select(
            TitleNorm.family, Organization.id, Organization.name, func.count(JobPost.id)
        )
        .join(JobPost, JobPost.org_id == Organization.id)
        .join(TitleNorm, JobPost.title_norm_id == TitleNorm.id)
        .where(JobPost.first_seen >= since)
        .group_by(TitleNorm.family, Organization.id, Organization.name)
        .order_by(desc(func.count(JobPost.id)))
        .limit(limit)
    )
    rows = db.execute(stmt).all()
    created = 0
    for role_family, org_id, org_name, count in rows:
        signal = HiringSignal(
            signal_type="posting_velocity",
            role_family=role_family,
            org_id=org_id,
            score=float(count),
            window_start=since,
            window_end=datetime.utcnow(),
            meta_json={"org_name": org_name},
        )
        db.add(signal)
        created += 1
    db.commit()
    return {"status": "success", "created": created}


def list_hiring_signals(db: Session, limit: int = 50) -> dict:
    stmt = select(HiringSignal).order_by(desc(HiringSignal.created_at)).limit(limit)
    rows = db.execute(stmt).scalars().all()
    return {
        "signals": [
            {
                "id": row.id,
                "signal_type": row.signal_type,
                "role_family": row.role_family,
                "org_id": row.org_id,
                "score": row.score,
                "window_start": row.window_start.isoformat()
                if row.window_start
                else None,
                "window_end": row.window_end.isoformat() if row.window_end else None,
                "metadata": row.meta_json or {},
            }
            for row in rows
        ],
        "total": len(rows),
    }

from __future__ import annotations

from datetime import datetime, timedelta
import os

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
from .processing_log_service import log_processing_event


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
    "project_management": [
        "plan",
        "coordinate",
        "deliver",
        "timeline",
        "stakeholder",
    ],
    "sales": ["prospect", "pipeline", "deal", "quota", "crm"],
    "marketing": ["campaign", "content", "brand", "social", "growth"],
    "finance": ["budget", "forecast", "audit", "reconcile", "ledger"],
}


TENDER_CATEGORY_KEYWORDS = {
    "it": ["it", "ict", "software", "hardware", "technology"],
    "construction": ["construction", "building", "civil", "renovation"],
    "consulting": ["consulting", "advisory", "consultant"],
    "supplies": ["supply", "supplies", "procurement", "stationery"],
    "services": ["services", "service"],
}

TENDER_LOCATIONS = [
    "nairobi",
    "mombasa",
    "kisumu",
    "nakuru",
    "eldoret",
    "thika",
]

ORG_HINTS = (
    "county",
    "ministry",
    "department",
    "authority",
    "commission",
    "agency",
    "university",
)


def _map_task_to_role(task_text: str) -> tuple[str | None, float]:
    text = (task_text or "").lower()
    for role_family, keywords in TASK_ROLE_KEYWORDS.items():
        matches = sum(1 for keyword in keywords if keyword in text)
        if matches:
            confidence = min(0.9, 0.3 + (matches / max(len(keywords), 1)))
            return role_family, round(confidence, 2)
    return None, 0.0


def _clean_text(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = " ".join(str(value).split()).strip()
    return cleaned or None


def _canonical_category(value: str | None, context: str) -> str | None:
    combined = f"{value or ''} {context}".lower()
    for category, keywords in TENDER_CATEGORY_KEYWORDS.items():
        if any(keyword in combined for keyword in keywords):
            return category
    return _clean_text(value).lower() if value else None


def _extract_location(context: str) -> str | None:
    lowered = context.lower()
    for loc in TENDER_LOCATIONS:
        if loc in lowered:
            return loc.title()
    return None


def _extract_org_from_title(title: str | None) -> str | None:
    if not title:
        return None
    title = _clean_text(title)
    if not title:
        return None
    for sep in (" - ", ":"):
        if sep in title:
            candidate = title.split(sep, 1)[0].strip()
            lowered = candidate.lower()
            if any(hint in lowered for hint in ORG_HINTS):
                return candidate
    return None


def normalize_tender_metadata(db: Session, limit: int = 200) -> dict:
    notices = (
        db.execute(
            select(TenderNotice)
            .where(
                (TenderNotice.organization.is_(None))
                | (TenderNotice.category.is_(None))
                | (TenderNotice.location.is_(None))
            )
            .order_by(desc(TenderNotice.created_at))
            .limit(limit)
        )
        .scalars()
        .all()
    )

    updated = 0
    for notice in notices:
        context = " ".join(
            [
                notice.title or "",
                notice.description_raw or "",
            ]
        ).strip()
        meta = notice.meta_json or {}

        organization = (
            notice.organization or meta.get("org") or meta.get("organization")
        )
        organization = _clean_text(organization)
        if not organization:
            organization = _extract_org_from_title(notice.title)

        category = _canonical_category(
            notice.category or meta.get("category"),
            context,
        )
        location = notice.location or meta.get("location")
        location = _clean_text(location)
        if not location:
            location = _extract_location(context)

        if organization:
            notice.organization = organization
        if category:
            notice.category = category
        if location:
            notice.location = location

        meta.setdefault("normalized", {})
        meta["normalized"].update(
            {
                "organization": notice.organization,
                "category": notice.category,
                "location": notice.location,
            }
        )
        notice.meta_json = meta
        db.add(notice)
        updated += 1

    if updated:
        db.commit()
    return {"status": "success", "updated": updated}


def _create_evidence(
    db: Session,
    *,
    evidence_type: str,
    source: str,
    source_url: str | None,
    snippet: str | None,
    confidence: float,
    meta_json: dict,
) -> int:
    evidence = SignalEvidence(
        evidence_type=evidence_type,
        source=source,
        source_url=source_url,
        snippet=snippet,
        confidence=confidence,
        meta_json=meta_json,
    )
    db.add(evidence)
    db.flush()
    return evidence.id


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
                "closing_at": (
                    row.closing_at.isoformat() if row.closing_at else None
                ),
                "url": row.url,
            }
            for row in rows
        ],
        "total": len(rows),
    }


def generate_hiring_signals(
    db: Session,
    days: int = 30,
    limit: int = 50,
) -> dict:
    since = datetime.utcnow() - timedelta(days=max(days, 1))
    stmt = (
        select(
            TitleNorm.family,
            Organization.id,
            Organization.name,
            func.count(JobPost.id),
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
        job_ids = [
            job_id
            for (job_id,) in db.execute(
                select(JobPost.id)
                .join(TitleNorm, JobPost.title_norm_id == TitleNorm.id)
                .where(JobPost.org_id == org_id)
                .where(TitleNorm.family == role_family)
                .where(JobPost.first_seen >= since)
                .limit(5)
            ).all()
        ]
        evidence_id = _create_evidence(
            db,
            evidence_type="posting_velocity",
            source="job_post",
            source_url=None,
            snippet="recent job postings",
            confidence=0.6,
            meta_json={"job_ids": job_ids, "org_name": org_name},
        )
        signal = HiringSignal(
            signal_type="posting_velocity",
            role_family=role_family,
            org_id=org_id,
            score=float(count),
            window_start=since,
            window_end=datetime.utcnow(),
            evidence_ids=[evidence_id],
            meta_json={"org_name": org_name},
        )
        db.add(signal)
        created += 1
    db.commit()
    return {"status": "success", "created": created}


def list_hiring_signals(db: Session, limit: int = 50) -> dict:
    stmt = (
        select(HiringSignal)
        .order_by(desc(HiringSignal.created_at))
        .limit(limit)
    )
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
                "window_end": (
                    row.window_end.isoformat() if row.window_end else None
                ),
                "evidence_ids": row.evidence_ids or [],
                "metadata": row.meta_json or {},
            }
            for row in rows
        ],
        "total": len(rows),
    }


def _generate_repost_intensity_signals(
    db: Session,
    *,
    since: datetime,
    limit: int,
) -> int:
    min_repost = int(os.getenv("SIGNAL_REPOST_MIN", "2"))
    stmt = (
        select(
            TitleNorm.family,
            Organization.id,
            Organization.name,
            func.avg(JobPost.repost_count),
        )
        .join(JobPost, JobPost.org_id == Organization.id)
        .join(TitleNorm, JobPost.title_norm_id == TitleNorm.id)
        .where(JobPost.first_seen >= since)
        .where(JobPost.repost_count >= min_repost)
        .group_by(TitleNorm.family, Organization.id, Organization.name)
        .order_by(desc(func.avg(JobPost.repost_count)))
        .limit(limit)
    )
    rows = db.execute(stmt).all()
    created = 0
    for role_family, org_id, org_name, avg_repost in rows:
        job_ids = [
            job_id
            for (job_id,) in db.execute(
                select(JobPost.id)
                .join(TitleNorm, JobPost.title_norm_id == TitleNorm.id)
                .where(JobPost.org_id == org_id)
                .where(TitleNorm.family == role_family)
                .where(JobPost.first_seen >= since)
                .where(JobPost.repost_count >= min_repost)
                .limit(5)
            ).all()
        ]
        evidence_id = _create_evidence(
            db,
            evidence_type="repost_intensity",
            source="job_post",
            source_url=None,
            snippet="repost activity",
            confidence=0.55,
            meta_json={"job_ids": job_ids, "org_name": org_name},
        )
        signal = HiringSignal(
            signal_type="repost_intensity",
            role_family=role_family,
            org_id=org_id,
            score=float(avg_repost or 0),
            window_start=since,
            window_end=datetime.utcnow(),
            evidence_ids=[evidence_id],
            meta_json={"org_name": org_name},
        )
        db.add(signal)
        created += 1
    return created


def _generate_org_activity_signals(
    db: Session,
    *,
    since: datetime,
    limit: int,
) -> int:
    min_roles = int(os.getenv("SIGNAL_ORG_MIN_ROLES", "2"))
    stmt = (
        select(
            Organization.id,
            Organization.name,
            func.count(func.distinct(TitleNorm.family)),
        )
        .join(JobPost, JobPost.org_id == Organization.id)
        .join(TitleNorm, JobPost.title_norm_id == TitleNorm.id)
        .where(JobPost.first_seen >= since)
        .group_by(Organization.id, Organization.name)
        .order_by(desc(func.count(func.distinct(TitleNorm.family))))
        .limit(limit)
    )
    rows = db.execute(stmt).all()
    created = 0
    for org_id, org_name, role_count in rows:
        if role_count < min_roles:
            continue
        role_families = [
            family
            for (family,) in db.execute(
                select(func.distinct(TitleNorm.family))
                .join(JobPost, JobPost.title_norm_id == TitleNorm.id)
                .where(JobPost.org_id == org_id)
                .where(JobPost.first_seen >= since)
                .limit(10)
            ).all()
        ]
        evidence_id = _create_evidence(
            db,
            evidence_type="org_activity",
            source="job_post",
            source_url=None,
            snippet="org role diversity",
            confidence=0.6,
            meta_json={"role_families": role_families, "org_name": org_name},
        )
        signal = HiringSignal(
            signal_type="org_activity",
            role_family=None,
            org_id=org_id,
            score=float(role_count),
            window_start=since,
            window_end=datetime.utcnow(),
            evidence_ids=[evidence_id],
            meta_json={"org_name": org_name},
        )
        db.add(signal)
        created += 1
    return created


def _clear_existing_aggregate_signals(db: Session, since: datetime) -> None:
    signal_types = ("posting_velocity", "repost_intensity", "org_activity")
    db.query(HiringSignal).filter(
        HiringSignal.signal_type.in_(signal_types),
        HiringSignal.window_end.is_not(None),
        HiringSignal.window_end >= since,
    ).delete(synchronize_session=False)
    db.flush()


def generate_signal_aggregates(
    db: Session,
    *,
    days: int = 30,
    limit: int = 50,
) -> dict:
    latest_evidence_id = db.execute(
        select(func.max(SignalEvidence.id))
    ).scalar()
    baseline_evidence_id = int(latest_evidence_id or 0)

    since = datetime.utcnow() - timedelta(days=max(days, 1))
    _clear_existing_aggregate_signals(db, since)

    created_by_type = {
        "posting_velocity": 0,
        "repost_intensity": 0,
        "org_activity": 0,
    }

    created_by_type["posting_velocity"] = generate_hiring_signals(
        db,
        days=days,
        limit=limit,
    )["created"]
    created_by_type["repost_intensity"] = _generate_repost_intensity_signals(
        db,
        since=since,
        limit=limit,
    )
    created_by_type["org_activity"] = _generate_org_activity_signals(
        db,
        since=since,
        limit=limit,
    )

    db.commit()

    evidence_ids = [
        evidence_id
        for (evidence_id,) in db.execute(
            select(SignalEvidence.id)
            .where(SignalEvidence.id > baseline_evidence_id)
            .order_by(SignalEvidence.id.asc())
        ).all()
    ]

    response = {
        "status": "success",
        "created_by_type": created_by_type,
        "created_total": sum(created_by_type.values()),
    }

    log_processing_event(
        db,
        process_type="signals_aggregate",
        status="success",
        message="Generated hiring signals with evidence links",
        details={
            "days": days,
            "limit": limit,
            "created_by_type": created_by_type,
            "created_total": response["created_total"],
            "evidence_ids": evidence_ids,
            "evidence_links_count": len(evidence_ids),
        },
    )

    return response

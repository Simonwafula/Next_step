from __future__ import annotations

import os
from typing import Any, Dict

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from ..db.models import JobEntities, JobPost


def is_generic_title(title: str | None) -> bool:
    if not title:
        return True
    lowered = title.strip().lower()
    if not lowered:
        return True
    return lowered in {
        "job posting",
        "career opportunity",
        "vacancies",
        "vacancy",
        "careers",
        "jobs",
        "job",
        "opportunities",
    }


def calculate_quality_score(
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

    if title and not is_generic_title(title):
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


def _read_gate_thresholds() -> Dict[str, float]:
    return {
        "description_raw": float(os.getenv("QUALITY_GATE_DESCRIPTION_PCT", "50")),
        "job_entities": float(os.getenv("QUALITY_GATE_ENTITIES_PCT", "40")),
        "processed_at": float(os.getenv("QUALITY_GATE_PROCESSED_PCT", "50")),
        "quality_score": float(os.getenv("QUALITY_GATE_QUALITY_SCORE_PCT", "50")),
    }


def evaluate_quality_gates(
    snapshot: Dict[str, Any],
    thresholds: Dict[str, float] | None = None,
) -> Dict[str, Any]:
    checks: Dict[str, Any] = {}
    coverage = snapshot.get("coverage", {})
    thresholds = thresholds or _read_gate_thresholds()

    for key, required in thresholds.items():
        actual = float(coverage.get(key, {}).get("percentage", 0) or 0)
        status = "pass" if actual >= required else "fail"
        checks[key] = {
            "status": status,
            "required": required,
            "actual": actual,
        }

    overall_status = (
        "pass"
        if all(check["status"] == "pass" for check in checks.values())
        else "fail"
    )

    return {
        "overall_status": overall_status,
        "checks": checks,
    }


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
            select(func.count(JobPost.id)).where(
                func.length(func.trim(JobPost.description_raw)) > 0
            )
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
            func.sum(
                case(
                    (func.length(func.trim(JobPost.description_raw)) > 0, 1),
                    else_=0,
                )
            ),
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

    snapshot = {
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

    snapshot["gates"] = evaluate_quality_gates(snapshot)
    return snapshot

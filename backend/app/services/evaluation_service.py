"""Offline evaluation services for search, ranking, recommendations, and intelligence quality.

Implements:
- T-DS-914: offline evaluation harness for search + recommendations
- T-DS-915: intelligence quality dashboard
- T-DS-918: ranking-quality evaluation suite over held-out sessions
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from math import log2
from typing import Any

from sqlalchemy import case, desc, func, select
from sqlalchemy.orm import Session

from ..db.models import (
    JobApplication,
    RoleDemandSnapshot,
    RoleSkillBaseline,
    SavedJob,
    SearchServingLog,
    UserAnalytics,
    UserJobRecommendation,
)
from .analytics import get_intelligence_metadata
from .intelligence_products import get_baseline_health


@dataclass
class RankedExample:
    key: str
    ranked_ids: list[int]
    relevant_ids: set[int]
    timestamp: datetime


def _safe_div(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return numerator / denominator


def _precision_at_k(ranked_ids: list[int], relevant_ids: set[int], k: int) -> float:
    if k <= 0:
        return 0.0
    top_k = ranked_ids[:k]
    if not top_k:
        return 0.0
    hits = sum(1 for job_id in top_k if job_id in relevant_ids)
    return hits / float(k)


def _hit_rate_at_k(ranked_ids: list[int], relevant_ids: set[int], k: int) -> float:
    top_k = ranked_ids[:k]
    return 1.0 if any(job_id in relevant_ids for job_id in top_k) else 0.0


def _mrr_at_k(ranked_ids: list[int], relevant_ids: set[int], k: int) -> float:
    for idx, job_id in enumerate(ranked_ids[:k], start=1):
        if job_id in relevant_ids:
            return 1.0 / float(idx)
    return 0.0


def _dcg_at_k(ranked_ids: list[int], relevant_ids: set[int], k: int) -> float:
    dcg = 0.0
    for idx, job_id in enumerate(ranked_ids[:k], start=1):
        if job_id in relevant_ids:
            dcg += 1.0 / log2(idx + 1)
    return dcg


def _ndcg_at_k(ranked_ids: list[int], relevant_ids: set[int], k: int) -> float:
    if not relevant_ids or k <= 0:
        return 0.0
    dcg = _dcg_at_k(ranked_ids, relevant_ids, k)
    ideal_hits = min(len(relevant_ids), k)
    ideal_dcg = sum(1.0 / log2(idx + 1) for idx in range(1, ideal_hits + 1))
    return _safe_div(dcg, ideal_dcg)


def _summarise_examples(examples: list[RankedExample], k: int) -> dict[str, Any]:
    if not examples:
        return {
            "evaluated_examples": 0,
            "precision_at_k": 0.0,
            "hit_rate_at_k": 0.0,
            "mrr_at_k": 0.0,
            "ndcg_at_k": 0.0,
            "avg_relevant_per_example": 0.0,
            "avg_relevant_returned_at_k": 0.0,
        }

    precision_scores: list[float] = []
    hit_scores: list[float] = []
    mrr_scores: list[float] = []
    ndcg_scores: list[float] = []
    relevant_counts: list[int] = []
    returned_counts: list[int] = []

    for example in examples:
        precision_scores.append(
            _precision_at_k(example.ranked_ids, example.relevant_ids, k)
        )
        hit_scores.append(_hit_rate_at_k(example.ranked_ids, example.relevant_ids, k))
        mrr_scores.append(_mrr_at_k(example.ranked_ids, example.relevant_ids, k))
        ndcg_scores.append(_ndcg_at_k(example.ranked_ids, example.relevant_ids, k))
        relevant_counts.append(len(example.relevant_ids))
        returned_counts.append(
            sum(
                1 for job_id in example.ranked_ids[:k] if job_id in example.relevant_ids
            )
        )

    count = len(examples)
    return {
        "evaluated_examples": count,
        "precision_at_k": round(sum(precision_scores) / count, 4),
        "hit_rate_at_k": round(sum(hit_scores) / count, 4),
        "mrr_at_k": round(sum(mrr_scores) / count, 4),
        "ndcg_at_k": round(sum(ndcg_scores) / count, 4),
        "avg_relevant_per_example": round(sum(relevant_counts) / count, 3),
        "avg_relevant_returned_at_k": round(sum(returned_counts) / count, 3),
    }


def _build_search_examples(
    db: Session, days_back: int
) -> tuple[list[RankedExample], int]:
    cutoff = datetime.utcnow() - timedelta(days=days_back)
    logs = (
        db.execute(
            select(SearchServingLog)
            .where(SearchServingLog.served_at >= cutoff)
            .where(SearchServingLog.session_id.is_not(None))
            .order_by(SearchServingLog.served_at.asc())
        )
        .scalars()
        .all()
    )

    apply_events = (
        db.execute(
            select(UserAnalytics)
            .where(UserAnalytics.event_type == "apply")
            .where(UserAnalytics.timestamp >= cutoff)
            .where(UserAnalytics.session_id.is_not(None))
            .order_by(UserAnalytics.timestamp.asc())
        )
        .scalars()
        .all()
    )

    relevant_by_session: dict[str, set[int]] = defaultdict(set)
    for event in apply_events:
        job_id = (event.event_data or {}).get("job_id")
        if event.session_id and job_id:
            relevant_by_session[event.session_id].add(int(job_id))

    examples: list[RankedExample] = []
    for log_row in logs:
        session_id = log_row.session_id
        if not session_id:
            continue
        ranked_ids = [int(job_id) for job_id in (log_row.result_job_ids or [])]
        if not ranked_ids:
            continue
        relevant_ids = relevant_by_session.get(session_id, set())
        if not relevant_ids:
            continue
        examples.append(
            RankedExample(
                key=f"search:{log_row.id}",
                ranked_ids=ranked_ids,
                relevant_ids=set(relevant_ids),
                timestamp=log_row.served_at,
            )
        )

    return examples, len(logs)


def evaluate_search_offline(
    db: Session,
    days_back: int = 30,
    k: int = 10,
) -> dict[str, Any]:
    """T-DS-914: Offline evaluation harness for search effectiveness."""
    examples, total_logs = _build_search_examples(db, days_back=days_back)
    metrics = _summarise_examples(examples, k)
    return {
        "task": "search_offline_evaluation",
        "window_days": days_back,
        "k": k,
        "total_logged_searches": total_logs,
        "searches_with_positive_feedback": len(examples),
        "feedback_coverage_pct": round(_safe_div(len(examples), total_logs) * 100, 1)
        if total_logs
        else 0.0,
        "metrics": metrics,
    }


def _build_recommendation_examples(
    db: Session, days_back: int
) -> tuple[list[RankedExample], dict[str, Any]]:
    cutoff = datetime.utcnow() - timedelta(days=days_back)
    rec_rows = (
        db.execute(
            select(UserJobRecommendation)
            .where(UserJobRecommendation.recommended_at >= cutoff)
            .order_by(
                UserJobRecommendation.user_id.asc(),
                UserJobRecommendation.match_score.desc(),
            )
        )
        .scalars()
        .all()
    )

    application_rows = (
        db.execute(
            select(JobApplication)
            .where(JobApplication.applied_at >= cutoff)
            .order_by(JobApplication.applied_at.asc())
        )
        .scalars()
        .all()
    )
    saved_rows = (
        db.execute(
            select(SavedJob)
            .where(SavedJob.saved_at >= cutoff)
            .order_by(SavedJob.saved_at.asc())
        )
        .scalars()
        .all()
    )

    first_apply_at: dict[tuple[int, int], datetime] = {}
    for row in application_rows:
        key = (row.user_id, row.job_post_id)
        if key not in first_apply_at or row.applied_at < first_apply_at[key]:
            first_apply_at[key] = row.applied_at

    first_saved_at: dict[tuple[int, int], datetime] = {}
    for row in saved_rows:
        key = (row.user_id, row.job_post_id)
        if key not in first_saved_at or row.saved_at < first_saved_at[key]:
            first_saved_at[key] = row.saved_at

    grouped: dict[int, list[UserJobRecommendation]] = defaultdict(list)
    for row in rec_rows:
        grouped[row.user_id].append(row)

    examples: list[RankedExample] = []
    clicked_total = 0
    applied_total = 0
    saved_total = 0

    for user_id, user_rows in grouped.items():
        ranked_ids: list[int] = []
        relevant_ids: set[int] = set()
        first_timestamp = min(row.recommended_at for row in user_rows)

        for row in user_rows:
            ranked_ids.append(int(row.job_post_id))
            key = (user_id, row.job_post_id)
            clicked = bool(row.clicked)
            applied = (
                key in first_apply_at and first_apply_at[key] >= row.recommended_at
            )
            saved = key in first_saved_at and first_saved_at[key] >= row.recommended_at

            if clicked:
                clicked_total += 1
            if applied:
                applied_total += 1
            if saved:
                saved_total += 1

            if clicked or applied or saved:
                relevant_ids.add(int(row.job_post_id))

        if relevant_ids:
            examples.append(
                RankedExample(
                    key=f"recommendations:{user_id}",
                    ranked_ids=ranked_ids,
                    relevant_ids=relevant_ids,
                    timestamp=first_timestamp,
                )
            )

    summary = {
        "recommendations_total": len(rec_rows),
        "users_with_recommendations": len(grouped),
        "users_with_positive_feedback": len(examples),
        "click_rate_pct": round(_safe_div(clicked_total, len(rec_rows)) * 100, 1)
        if rec_rows
        else 0.0,
        "apply_rate_pct": round(_safe_div(applied_total, len(rec_rows)) * 100, 1)
        if rec_rows
        else 0.0,
        "save_rate_pct": round(_safe_div(saved_total, len(rec_rows)) * 100, 1)
        if rec_rows
        else 0.0,
    }
    return examples, summary


def evaluate_recommendations_offline(
    db: Session,
    days_back: int = 30,
    k: int = 10,
) -> dict[str, Any]:
    """T-DS-914: Offline evaluation harness for stored recommendations."""
    examples, summary = _build_recommendation_examples(db, days_back=days_back)
    return {
        "task": "recommendation_offline_evaluation",
        "window_days": days_back,
        "k": k,
        **summary,
        "metrics": _summarise_examples(examples, k),
    }


def evaluate_ranking_quality(
    db: Session,
    days_back: int = 30,
    k: int = 10,
    holdout_fraction: float = 0.2,
) -> dict[str, Any]:
    """T-DS-918: Held-out ranking effectiveness metrics over logged sessions."""
    examples, total_logs = _build_search_examples(db, days_back=days_back)
    ordered = sorted(examples, key=lambda item: item.timestamp)

    holdout_size = 0
    holdout_examples: list[RankedExample] = []
    calibration_examples: list[RankedExample] = ordered
    if ordered:
        holdout_size = max(1, int(round(len(ordered) * holdout_fraction)))
        holdout_size = min(holdout_size, len(ordered))
        calibration_examples = ordered[:-holdout_size] or ordered[:0]
        holdout_examples = ordered[-holdout_size:]

    return {
        "task": "ranking_quality_evaluation",
        "window_days": days_back,
        "k": k,
        "holdout_fraction": holdout_fraction,
        "total_logged_searches": total_logs,
        "searches_with_positive_feedback": len(ordered),
        "calibration_examples": len(calibration_examples),
        "holdout_examples": len(holdout_examples),
        "metrics": {
            "overall": _summarise_examples(ordered, k),
            "holdout": _summarise_examples(holdout_examples, k),
        },
    }


def build_intelligence_quality_dashboard(
    db: Session,
    window_days: int = 180,
    top_role_families: int = 10,
) -> dict[str, Any]:
    """T-DS-915: Intelligence quality dashboard for stability and representativeness."""
    baseline_health = get_baseline_health(db)
    metadata = get_intelligence_metadata(db, window_days=window_days)

    role_rows = db.execute(
        select(
            RoleDemandSnapshot.role_family,
            RoleDemandSnapshot.demand_count,
            RoleDemandSnapshot.count_total_jobs_used,
            RoleDemandSnapshot.low_confidence,
            func.count(RoleSkillBaseline.id).label("skill_rows"),
            func.sum(
                case(
                    (RoleSkillBaseline.low_confidence.is_(True), 1),
                    else_=0,
                )
            ).label("low_skill_rows"),
        )
        .select_from(RoleDemandSnapshot)
        .join(
            RoleSkillBaseline,
            RoleSkillBaseline.role_family == RoleDemandSnapshot.role_family,
            isouter=True,
        )
        .group_by(
            RoleDemandSnapshot.role_family,
            RoleDemandSnapshot.demand_count,
            RoleDemandSnapshot.count_total_jobs_used,
            RoleDemandSnapshot.low_confidence,
        )
        .order_by(desc(RoleDemandSnapshot.demand_count))
        .limit(top_role_families)
    ).all()

    role_family_quality = []
    for row in role_rows:
        sample_size = row.count_total_jobs_used or 0
        if sample_size >= 100:
            confidence_tier = "high"
        elif sample_size >= 30:
            confidence_tier = "medium"
        else:
            confidence_tier = "low"
        skill_rows = row.skill_rows or 0
        low_skill_rows = row.low_skill_rows or 0
        role_family_quality.append(
            {
                "role_family": row.role_family,
                "demand_count": row.demand_count,
                "sample_size": sample_size,
                "low_confidence": bool(row.low_confidence),
                "confidence_tier": confidence_tier,
                "low_confidence_skill_pct": round(
                    _safe_div(low_skill_rows, skill_rows) * 100, 1
                )
                if skill_rows
                else 0.0,
            }
        )

    stale_tables = [
        table_name
        for table_name, info in baseline_health["tables"].items()
        if info.get("stale")
    ]

    return {
        "task": "intelligence_quality_dashboard",
        "window_days": window_days,
        "summary": {
            "overall_status": baseline_health["overall_status"],
            "sample_size": metadata["sample_size"],
            "confidence_note": metadata["confidence_note"],
            "source_count": len(metadata["source_mix"]),
            "coverage_gap_count": len(metadata["coverage_gaps"]),
            "stale_table_count": len(stale_tables),
        },
        "baseline_health": baseline_health,
        "market_metadata": metadata,
        "role_family_quality": role_family_quality,
        "warnings": baseline_health["recommendations"],
    }

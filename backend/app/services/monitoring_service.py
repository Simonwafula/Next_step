from __future__ import annotations

from datetime import datetime, timedelta
import os
from typing import Any, Dict

from sqlalchemy import select
from sqlalchemy.orm import Session

from .analytics import run_drift_checks
from ..db.models import ProcessingLog
from .processing_quality import quality_snapshot


def _read_drift_thresholds() -> Dict[str, float]:
    return {
        "skill_drift_max": float(os.getenv("DRIFT_SKILL_MAX", "0.7")),
        "title_drift_max": float(os.getenv("DRIFT_TITLE_MAX", "0.7")),
        "salary_delta_max": float(os.getenv("DRIFT_SALARY_MAX", "0.5")),
    }


def _read_operations_thresholds() -> Dict[str, float]:
    return {
        "error_rate_max": float(os.getenv("MONITORING_ERROR_RATE_MAX", "20")),
        "ingestion_staleness_hours_max": float(
            os.getenv("MONITORING_INGESTION_STALENESS_HOURS", "48")
        ),
    }


def _evaluate_operations_checks(
    db: Session,
    *,
    recent_days: int,
    thresholds: Dict[str, float],
) -> Dict[str, Any]:
    since = datetime.utcnow() - timedelta(days=max(recent_days, 1))
    ingestion_types = [
        "ingestion",
        "ingest_all",
        "ingest_government",
        "daily_workflow",
    ]

    recent_logs = (
        db.execute(
            select(ProcessingLog)
            .where(ProcessingLog.process_type.in_(ingestion_types))
            .where(ProcessingLog.processed_at >= since)
            .order_by(ProcessingLog.processed_at.desc())
        )
        .scalars()
        .all()
    )

    total_runs = len(recent_logs)
    error_runs = sum(
        1
        for log in recent_logs
        if ((log.results or {}).get("status") or "").lower() == "error"
    )

    error_rate_pct = (error_runs / total_runs * 100.0) if total_runs else None
    if error_rate_pct is None:
        error_rate_check = {
            "status": "unknown",
            "reason": "insufficient_data",
            "actual": None,
            "threshold": thresholds["error_rate_max"],
        }
    else:
        error_rate_check = {
            "status": "pass"
            if error_rate_pct <= thresholds["error_rate_max"]
            else "fail",
            "actual": round(error_rate_pct, 2),
            "threshold": thresholds["error_rate_max"],
        }

    latest_ingestion = (
        db.execute(
            select(ProcessingLog)
            .where(ProcessingLog.process_type.in_(ingestion_types))
            .order_by(ProcessingLog.processed_at.desc())
            .limit(1)
        )
        .scalars()
        .first()
    )

    if latest_ingestion is None or latest_ingestion.processed_at is None:
        freshness_check = {
            "status": "unknown",
            "reason": "insufficient_data",
            "actual": None,
            "threshold": thresholds["ingestion_staleness_hours_max"],
        }
        staleness_hours = None
        last_ingestion_at = None
    else:
        staleness_hours = (
            datetime.utcnow() - latest_ingestion.processed_at
        ).total_seconds() / 3600.0
        freshness_check = {
            "status": "pass"
            if staleness_hours <= thresholds["ingestion_staleness_hours_max"]
            else "fail",
            "actual": round(staleness_hours, 2),
            "threshold": thresholds["ingestion_staleness_hours_max"],
        }
        last_ingestion_at = latest_ingestion.processed_at.isoformat()

    checks = {
        "error_rate": error_rate_check,
        "ingestion_freshness": freshness_check,
    }

    overall_status = "pass"
    if any(check["status"] == "fail" for check in checks.values()):
        overall_status = "fail"
    elif any(check["status"] == "unknown" for check in checks.values()):
        overall_status = "warn"

    return {
        "overall_status": overall_status,
        "checks": checks,
        "metrics": {
            "window_days": max(recent_days, 1),
            "total_runs": total_runs,
            "error_runs": error_runs,
            "error_rate_pct": round(error_rate_pct, 2)
            if error_rate_pct is not None
            else None,
            "last_ingestion_at": last_ingestion_at,
            "staleness_hours": round(staleness_hours, 2)
            if staleness_hours is not None
            else None,
        },
        "thresholds": thresholds,
    }


def _evaluate_drift_checks(
    drift: Dict[str, Any],
    thresholds: Dict[str, float],
) -> Dict[str, Any]:
    checks: Dict[str, Any] = {}

    recent_skills = drift.get("skills", {}).get("recent_top", [])
    baseline_skills = drift.get("skills", {}).get("baseline_top", [])
    skill_drift = float(drift.get("skills", {}).get("drift_score", 0.0) or 0.0)
    if not recent_skills and not baseline_skills:
        checks["skills"] = {
            "status": "fail",
            "reason": "insufficient_data",
            "actual": skill_drift,
            "threshold": thresholds["skill_drift_max"],
        }
    else:
        checks["skills"] = {
            "status": "pass"
            if skill_drift <= thresholds["skill_drift_max"]
            else "fail",
            "actual": skill_drift,
            "threshold": thresholds["skill_drift_max"],
        }

    recent_titles = drift.get("titles", {}).get("recent_top", [])
    baseline_titles = drift.get("titles", {}).get("baseline_top", [])
    title_drift = float(drift.get("titles", {}).get("drift_score", 0.0) or 0.0)
    if not recent_titles and not baseline_titles:
        checks["titles"] = {
            "status": "fail",
            "reason": "insufficient_data",
            "actual": title_drift,
            "threshold": thresholds["title_drift_max"],
        }
    else:
        checks["titles"] = {
            "status": "pass"
            if title_drift <= thresholds["title_drift_max"]
            else "fail",
            "actual": title_drift,
            "threshold": thresholds["title_drift_max"],
        }

    salary_delta = drift.get("salary", {}).get("delta_ratio")
    if salary_delta is None:
        checks["salary"] = {
            "status": "unknown",
            "reason": "insufficient_data",
            "actual": None,
            "threshold": thresholds["salary_delta_max"],
        }
    else:
        delta_value = abs(float(salary_delta))
        checks["salary"] = {
            "status": "pass"
            if delta_value <= thresholds["salary_delta_max"]
            else "fail",
            "actual": delta_value,
            "threshold": thresholds["salary_delta_max"],
        }

    overall_status = "pass"
    if any(check["status"] == "fail" for check in checks.values()):
        overall_status = "fail"
    elif any(check["status"] == "unknown" for check in checks.values()):
        overall_status = "warn"

    return {
        "overall_status": overall_status,
        "checks": checks,
    }


def monitoring_summary(
    db: Session,
    *,
    recent_days: int = 30,
    baseline_days: int = 180,
    top_n: int = 20,
) -> Dict[str, Any]:
    quality = quality_snapshot(db)
    drift = run_drift_checks(
        db,
        recent_days=recent_days,
        baseline_days=baseline_days,
        top_n=top_n,
    )

    thresholds = _read_drift_thresholds()
    drift_gates = _evaluate_drift_checks(drift, thresholds)
    operation_thresholds = _read_operations_thresholds()
    operations = _evaluate_operations_checks(
        db,
        recent_days=recent_days,
        thresholds=operation_thresholds,
    )

    overall_status = "pass"
    if quality.get("gates", {}).get("overall_status") == "fail":
        overall_status = "fail"
    if drift_gates["overall_status"] == "fail":
        overall_status = "fail"
    elif drift_gates["overall_status"] == "warn" and overall_status == "pass":
        overall_status = "warn"
    if operations["overall_status"] == "fail":
        overall_status = "fail"
    elif operations["overall_status"] == "warn" and overall_status == "pass":
        overall_status = "warn"

    return {
        "overall_status": overall_status,
        "quality": quality,
        "operations": operations,
        "drift": {
            "metrics": drift,
            "checks": drift_gates["checks"],
            "overall_status": drift_gates["overall_status"],
            "thresholds": thresholds,
        },
    }

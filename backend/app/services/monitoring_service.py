from __future__ import annotations

import os
from typing import Any, Dict

from sqlalchemy.orm import Session

from .analytics import run_drift_checks
from .processing_quality import quality_snapshot


def _read_drift_thresholds() -> Dict[str, float]:
    return {
        "skill_drift_max": float(os.getenv("DRIFT_SKILL_MAX", "0.7")),
        "title_drift_max": float(os.getenv("DRIFT_TITLE_MAX", "0.7")),
        "salary_delta_max": float(os.getenv("DRIFT_SALARY_MAX", "0.5")),
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

    overall_status = "pass"
    if quality.get("gates", {}).get("overall_status") == "fail":
        overall_status = "fail"
    if drift_gates["overall_status"] == "fail":
        overall_status = "fail"
    elif drift_gates["overall_status"] == "warn" and overall_status == "pass":
        overall_status = "warn"

    return {
        "overall_status": overall_status,
        "quality": quality,
        "drift": {
            "metrics": drift,
            "checks": drift_gates["checks"],
            "overall_status": drift_gates["overall_status"],
            "thresholds": thresholds,
        },
    }

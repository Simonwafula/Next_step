"""Production-grade intelligence product endpoints (T-DS-974).

Routes:
  GET /api/intelligence/baseline-health            T-DS-971
  GET /api/intelligence/skill-baseline/{role}      T-DS-971
  GET /api/intelligence/reports/university         T-DS-972
  GET /api/intelligence/reports/employer           T-DS-972
  GET /api/intelligence/reports/county             T-DS-972
  GET /api/intelligence/reports/training-provider  T-DS-972
  GET /api/intelligence/salary/{role_family}       T-DS-973
  GET /api/intelligence/salary/confidence-summary  T-DS-973
  GET /api/intelligence/salary/low-confidence-log  T-DS-973
  GET /api/intelligence/export/skills-gap          T-DS-974
  GET /api/intelligence/export/market-snapshot     T-DS-974
"""

import csv
import io

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..db.database import get_db
from ..ml.model_registry import (
    get_feature_contract_dict,
    get_metric_registry,
    is_hash_fallback_active,
    load_algorithm_registry,
)
from ..services.intelligence_products import (
    build_county_report,
    build_employer_report,
    build_training_provider_report,
    build_university_report,
    get_baseline_health,
    get_confidence_aware_skill_baseline,
    get_salary_confidence_summary,
    get_salary_low_confidence_log,
    get_salary_with_market_context,
)

router = APIRouter(prefix="/api/intelligence", tags=["intelligence"])


# ---------------------------------------------------------------------------
# T-DS-983/984/985: Algorithm registry, metric registry, embedding mode
# ---------------------------------------------------------------------------


@router.get("/algorithm-registry")
def algorithm_registry():
    """T-DS-983: Algorithm registry with versioning and eval metadata."""
    return load_algorithm_registry()


@router.get("/feature-contract")
def feature_contract():
    """T-DS-982: Canonical feature contract for the ranking model."""
    return get_feature_contract_dict()


@router.get("/metric-registry")
def metric_registry(db: Session = Depends(get_db)):
    """T-DS-984: Live intelligence metric registry snapshot."""
    return get_metric_registry(db)


@router.get("/embedding-mode")
def embedding_mode_status():
    """T-DS-985: Current embedding mode — semantic or hash_fallback (degraded)."""
    degraded = is_hash_fallback_active()
    return {
        "mode": "hash_fallback" if degraded else "semantic",
        "degraded": degraded,
        "warning": (
            "Hash-vector fallback is active. Semantic search is disabled."
            if degraded
            else None
        ),
    }


# ---------------------------------------------------------------------------
# T-DS-971: Baseline health + confidence-aware skill baseline
# ---------------------------------------------------------------------------


@router.get("/baseline-health")
def baseline_health(db: Session = Depends(get_db)):
    """Return health report for all intelligence baseline tables (T-DS-971)."""
    return get_baseline_health(db)


@router.get("/skill-baseline/{role_family}")
def skill_baseline(role_family: str, db: Session = Depends(get_db)):
    """Return skill baseline for a role family with confidence metadata (T-DS-971)."""
    return get_confidence_aware_skill_baseline(db, role_family)


# ---------------------------------------------------------------------------
# T-DS-972: Report-grade datasets
# ---------------------------------------------------------------------------


@router.get("/reports/university")
def university_report(
    role_families: str | None = Query(
        None, description="Comma-separated role families to filter"
    ),
    top_skills: int = Query(15, ge=5, le=50),
    window_days: int = Query(180, ge=30, le=365),
    db: Session = Depends(get_db),
):
    """University / institution report: top demanded skills + education requirements (T-DS-972)."""
    families = [f.strip() for f in role_families.split(",")] if role_families else None
    return build_university_report(
        db,
        role_families=families,
        top_skills_per_family=top_skills,
        window_days=window_days,
    )


@router.get("/reports/employer")
def employer_report(
    role_family: str | None = Query(None),
    window_days: int = Query(90, ge=30, le=365),
    db: Session = Depends(get_db),
):
    """Employer intelligence report: candidate pool skills + experience distribution (T-DS-972)."""
    return build_employer_report(db, role_family=role_family, window_days=window_days)


@router.get("/reports/county")
def county_report(
    county: str | None = Query(None, description="County or city name"),
    window_days: int = Query(90, ge=30, le=365),
    db: Session = Depends(get_db),
):
    """County / regional report: local demand + salary bands + top employers (T-DS-972)."""
    return build_county_report(db, county=county, window_days=window_days)


@router.get("/reports/training-provider")
def training_provider_report(
    skill_focus: str | None = Query(
        None, description="Comma-separated skills to focus on"
    ),
    top_gaps: int = Query(20, ge=5, le=100),
    window_days: int = Query(180, ge=30, le=365),
    db: Session = Depends(get_db),
):
    """Training provider report: most demanded skills + role family associations (T-DS-972)."""
    focus = [s.strip() for s in skill_focus.split(",")] if skill_focus else None
    return build_training_provider_report(
        db, skill_focus=focus, top_gaps=top_gaps, window_days=window_days
    )


# ---------------------------------------------------------------------------
# T-DS-973: Salary intelligence
# ---------------------------------------------------------------------------


@router.get("/salary/confidence-summary")
def salary_confidence_summary(
    window_days: int = Query(90, ge=30, le=365),
    db: Session = Depends(get_db),
):
    """Summary of salary data coverage and confidence by role family (T-DS-973)."""
    return get_salary_confidence_summary(db, window_days=window_days)


@router.get("/salary/low-confidence-log")
def salary_low_confidence_log(
    limit: int = Query(50, ge=1, le=200),
):
    """Recent low-confidence salary estimate calls (T-DS-973)."""
    return {"entries": get_salary_low_confidence_log(limit=limit), "count": limit}


@router.get("/salary/{role_family}")
def salary_intelligence(
    role_family: str,
    location: str | None = Query(None),
    seniority: str | None = Query(None),
    currency: str = Query("KES"),
    window_days: int = Query(180, ge=30, le=365),
    db: Session = Depends(get_db),
):
    """Market-backed salary estimate with confidence metadata (T-DS-973)."""
    return get_salary_with_market_context(
        db,
        role_family=role_family,
        location=location,
        seniority=seniority,
        currency=currency,
        window_days=window_days,
    )


# ---------------------------------------------------------------------------
# T-DS-974: Intelligence exports (CSV / JSON)
# ---------------------------------------------------------------------------


@router.get("/export/skills-gap")
def export_skills_gap(
    role_families: str | None = Query(
        None, description="Comma-separated role families"
    ),
    fmt: str = Query("json", pattern="^(json|csv)$"),
    top_skills: int = Query(15, ge=5, le=50),
    window_days: int = Query(180, ge=30, le=365),
    db: Session = Depends(get_db),
):
    """Export skills-gap dataset for universities and training providers (T-DS-974)."""
    families = [f.strip() for f in role_families.split(",")] if role_families else None
    data = build_university_report(
        db,
        role_families=families,
        top_skills_per_family=top_skills,
        window_days=window_days,
    )

    if fmt == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(
            ["role_family", "skill", "skill_share", "low_confidence", "confidence_tier"]
        )
        for fam_block in data["role_families"]:
            for skill in fam_block["top_skills"]:
                writer.writerow(
                    [
                        fam_block["role_family"],
                        skill["skill"],
                        skill["share"],
                        skill["low_confidence"],
                        fam_block["confidence_tier"],
                    ]
                )
        output.seek(0)
        return StreamingResponse(
            output,
            media_type="text/csv",
            headers={
                "Content-Disposition": "attachment; filename=skills_gap_export.csv"
            },
        )

    return data


@router.get("/export/market-snapshot")
def export_market_snapshot(
    county: str | None = Query(None),
    fmt: str = Query("json", pattern="^(json|csv)$"),
    window_days: int = Query(90, ge=30, le=365),
    db: Session = Depends(get_db),
):
    """Export market snapshot (demand + salaries) for a county or national level (T-DS-974)."""
    data = build_county_report(db, county=county, window_days=window_days)

    if fmt == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["role_family", "postings", "share"])
        for row in data["demand_by_role_family"]:
            writer.writerow([row["role_family"], row["postings"], row["share"]])
        # Append org rows
        writer.writerow([])
        writer.writerow(["organisation", "sector", "postings"])
        for row in data["top_hiring_organisations"]:
            writer.writerow([row["name"], row["sector"], row["postings"]])
        output.seek(0)
        return StreamingResponse(
            output,
            media_type="text/csv",
            headers={
                "Content-Disposition": "attachment; filename=market_snapshot_export.csv"
            },
        )

    return data

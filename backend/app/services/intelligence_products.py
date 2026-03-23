"""Production-grade intelligence products service (T-DS-970).

Covers:
- T-DS-971: Confidence-aware analytics APIs + baseline refresh hardening
- T-DS-972: Report-grade dataset builder for universities, employers,
            counties, and training providers
- T-DS-973: Salary intelligence with market-backed confidence + error tracking
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from ..db.models import (
    JobPost,
    Location,
    MetricsDaily,
    Organization,
    RoleDemandSnapshot,
    RoleEducationBaseline,
    RoleExperienceBaseline,
    RoleSkillBaseline,
    TitleNorm,
)
from .salary_service import SalaryService

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# T-DS-971: Baseline health + confidence-aware analytics
# ---------------------------------------------------------------------------

# A baseline table is considered stale if its most recent row is older than
# this many days.
_BASELINE_STALENESS_DAYS = 7


def _confidence_tier(sample_size: int) -> str:
    if sample_size >= 100:
        return "high"
    if sample_size >= 30:
        return "medium"
    return "low"


def _staleness_status(updated_at: datetime | None) -> dict[str, Any]:
    if updated_at is None:
        return {"status": "missing", "age_days": None, "stale": True}
    age = (datetime.utcnow() - updated_at).total_seconds() / 86400
    stale = age > _BASELINE_STALENESS_DAYS
    return {
        "status": "stale" if stale else "fresh",
        "age_days": round(age, 1),
        "stale": stale,
        "updated_at": updated_at.date().isoformat(),
    }


def _latest_updated_at(db: Session, model) -> datetime | None:
    result = db.execute(select(func.max(model.updated_at))).scalar()
    return result


def get_baseline_health(db: Session) -> dict[str, Any]:
    """T-DS-971: Return health report for all intelligence baseline tables.

    Checks staleness and sample coverage for:
    - role_skill_baseline
    - role_education_baseline
    - role_experience_baseline
    - role_demand_snapshot
    """
    skill_updated = _latest_updated_at(db, RoleSkillBaseline)
    edu_updated = _latest_updated_at(db, RoleEducationBaseline)
    exp_updated = _latest_updated_at(db, RoleExperienceBaseline)
    demand_updated = _latest_updated_at(db, RoleDemandSnapshot)

    skill_count = db.execute(select(func.count(RoleSkillBaseline.id))).scalar() or 0
    edu_count = db.execute(select(func.count(RoleEducationBaseline.id))).scalar() or 0
    exp_count = db.execute(select(func.count(RoleExperienceBaseline.id))).scalar() or 0
    demand_count = db.execute(select(func.count(RoleDemandSnapshot.id))).scalar() or 0

    skill_low = (
        db.execute(
            select(func.count(RoleSkillBaseline.id)).where(
                RoleSkillBaseline.low_confidence.is_(True)
            )
        ).scalar()
        or 0
    )
    edu_low = (
        db.execute(
            select(func.count(RoleEducationBaseline.id)).where(
                RoleEducationBaseline.low_confidence.is_(True)
            )
        ).scalar()
        or 0
    )
    exp_low = (
        db.execute(
            select(func.count(RoleExperienceBaseline.id)).where(
                RoleExperienceBaseline.low_confidence.is_(True)
            )
        ).scalar()
        or 0
    )
    demand_low = (
        db.execute(
            select(func.count(RoleDemandSnapshot.id)).where(
                RoleDemandSnapshot.low_confidence.is_(True)
            )
        ).scalar()
        or 0
    )

    # Families with any baseline data at all
    role_families_covered = (
        db.execute(select(RoleSkillBaseline.role_family).distinct()).scalars().all()
    )

    tables = {
        "role_skill_baseline": {
            **_staleness_status(skill_updated),
            "row_count": skill_count,
            "low_confidence_rows": skill_low,
            "low_confidence_pct": round(skill_low / skill_count * 100, 1)
            if skill_count
            else 0,
        },
        "role_education_baseline": {
            **_staleness_status(edu_updated),
            "row_count": edu_count,
            "low_confidence_rows": edu_low,
            "low_confidence_pct": round(edu_low / edu_count * 100, 1)
            if edu_count
            else 0,
        },
        "role_experience_baseline": {
            **_staleness_status(exp_updated),
            "row_count": exp_count,
            "low_confidence_rows": exp_low,
            "low_confidence_pct": round(exp_low / exp_count * 100, 1)
            if exp_count
            else 0,
        },
        "role_demand_snapshot": {
            **_staleness_status(demand_updated),
            "row_count": demand_count,
            "low_confidence_rows": demand_low,
            "low_confidence_pct": round(demand_low / demand_count * 100, 1)
            if demand_count
            else 0,
        },
    }

    any_stale = any(v["stale"] for v in tables.values())
    any_missing = skill_count == 0 or demand_count == 0

    return {
        "overall_status": "needs_refresh" if (any_stale or any_missing) else "healthy",
        "role_families_covered": sorted(role_families_covered),
        "staleness_threshold_days": _BASELINE_STALENESS_DAYS,
        "tables": tables,
        "recommendations": _baseline_recommendations(tables, any_missing),
    }


def _baseline_recommendations(tables: dict[str, dict], any_missing: bool) -> list[str]:
    recs = []
    if any_missing:
        recs.append(
            "One or more baseline tables are empty. Run the baseline refresh job."
        )
    for name, info in tables.items():
        if info["stale"] and not any_missing:
            recs.append(
                f"{name} is {info['age_days']} days old (threshold: "
                f"{_BASELINE_STALENESS_DAYS}d). Schedule a refresh."
            )
        if info.get("low_confidence_pct", 0) > 40:
            recs.append(
                f"{name} has {info['low_confidence_pct']}% low-confidence rows. "
                "Ingest more jobs for affected role families."
            )
    if not recs:
        recs.append("All baselines are healthy.")
    return recs


def get_confidence_aware_skill_baseline(
    db: Session, role_family: str
) -> dict[str, Any]:
    """T-DS-971: Return skill baseline for a role family with confidence metadata."""
    rows = (
        db.execute(
            select(RoleSkillBaseline)
            .where(RoleSkillBaseline.role_family == role_family)
            .order_by(desc(RoleSkillBaseline.skill_share))
        )
        .scalars()
        .all()
    )

    if not rows:
        return {
            "role_family": role_family,
            "skills": [],
            "confidence": {"tier": "low", "sample_size": 0, "note": "No baseline data"},
        }

    sample_size = rows[0].count_total_jobs_used if rows else 0
    tier = _confidence_tier(sample_size)
    high_conf_count = sum(1 for r in rows if not r.low_confidence)

    return {
        "role_family": role_family,
        "skills": [
            {
                "skill_name": r.skill_name,
                "skill_share": round(r.skill_share, 4),
                "low_confidence": r.low_confidence,
                "updated_at": r.updated_at.date().isoformat() if r.updated_at else None,
            }
            for r in rows
        ],
        "confidence": {
            "tier": tier,
            "sample_size": sample_size,
            "high_confidence_skills": high_conf_count,
            "total_skills": len(rows),
            "note": _confidence_note(tier, sample_size),
        },
    }


def _confidence_note(tier: str, sample_size: int) -> str:
    if tier == "high":
        return f"Based on {sample_size} jobs — high confidence."
    if tier == "medium":
        return (
            f"Based on {sample_size} jobs — moderate confidence, interpret carefully."
        )
    return (
        f"Based on only {sample_size} jobs — low confidence. "
        "Results may not be representative."
    )


# ---------------------------------------------------------------------------
# T-DS-972: Report-grade dataset builder
# ---------------------------------------------------------------------------


def build_university_report(
    db: Session,
    role_families: list[str] | None = None,
    top_skills_per_family: int = 15,
    window_days: int = 180,
) -> dict[str, Any]:
    """T-DS-972: Report dataset for universities and training institutions.

    Shows top demanded skills per role family, education level distribution,
    and gap between what graduates typically have vs. what employers demand.
    """
    since = datetime.utcnow() - timedelta(days=window_days)

    # Active role families from demand snapshot
    demand_q = select(RoleDemandSnapshot).order_by(
        desc(RoleDemandSnapshot.demand_count)
    )
    demand_rows = db.execute(demand_q).scalars().all()

    families = (
        role_families
        if role_families
        else [r.role_family for r in demand_rows if r.demand_count > 0]
    )

    demand_by_family = {r.role_family: r.demand_count for r in demand_rows}

    skill_by_family: dict[str, list[dict]] = {}
    for fam in families:
        rows = (
            db.execute(
                select(RoleSkillBaseline)
                .where(RoleSkillBaseline.role_family == fam)
                .order_by(desc(RoleSkillBaseline.skill_share))
                .limit(top_skills_per_family)
            )
            .scalars()
            .all()
        )
        skill_by_family[fam] = [
            {
                "skill": r.skill_name,
                "share": round(r.skill_share, 4),
                "low_confidence": r.low_confidence,
            }
            for r in rows
        ]

    edu_by_family: dict[str, list[dict]] = {}
    for fam in families:
        rows = (
            db.execute(
                select(RoleEducationBaseline)
                .where(RoleEducationBaseline.role_family == fam)
                .order_by(desc(RoleEducationBaseline.education_share))
            )
            .scalars()
            .all()
        )
        edu_by_family[fam] = [
            {
                "education_level": r.education_level,
                "share": round(r.education_share, 4),
                "low_confidence": r.low_confidence,
            }
            for r in rows
        ]

    # Recent posting counts per family
    recent_counts = dict(
        db.execute(
            select(TitleNorm.family, func.count(JobPost.id))
            .join(JobPost, JobPost.title_norm_id == TitleNorm.id)
            .where(JobPost.is_active.is_(True), JobPost.first_seen >= since)
            .group_by(TitleNorm.family)
        ).all()
    )

    families_data = []
    for fam in families:
        sample = demand_by_family.get(fam, 0)
        families_data.append(
            {
                "role_family": fam,
                "active_postings_6m": recent_counts.get(fam, 0),
                "demand_count": demand_by_family.get(fam, 0),
                "top_skills": skill_by_family.get(fam, []),
                "education_requirements": edu_by_family.get(fam, []),
                "confidence_tier": _confidence_tier(sample),
            }
        )

    return {
        "report_type": "university",
        "generated_at": datetime.utcnow().isoformat(),
        "window_days": window_days,
        "role_families_included": len(families_data),
        "role_families": families_data,
        "meta": {
            "note": (
                "Top skills are derived from active job postings. "
                "Education distribution shows what employers require, not what graduates have."
            )
        },
    }


def build_employer_report(
    db: Session,
    role_family: str | None = None,
    window_days: int = 90,
) -> dict[str, Any]:
    """T-DS-972: Report dataset for employer intelligence packs.

    Shows candidate pool skills, experience distribution, and demand context.
    """
    since = datetime.utcnow() - timedelta(days=window_days)

    families_q = select(RoleDemandSnapshot.role_family, RoleDemandSnapshot.demand_count)
    if role_family:
        families_q = families_q.where(RoleDemandSnapshot.role_family == role_family)
    families_q = families_q.order_by(desc(RoleDemandSnapshot.demand_count))
    families = db.execute(families_q).all()

    result = []
    for fam, demand in families:
        skills = (
            db.execute(
                select(RoleSkillBaseline)
                .where(RoleSkillBaseline.role_family == fam)
                .order_by(desc(RoleSkillBaseline.skill_share))
                .limit(10)
            )
            .scalars()
            .all()
        )
        exp_rows = (
            db.execute(
                select(RoleExperienceBaseline)
                .where(RoleExperienceBaseline.role_family == fam)
                .order_by(desc(RoleExperienceBaseline.experience_share))
            )
            .scalars()
            .all()
        )

        # Recent postings for this family
        recent = (
            db.execute(
                select(func.count(JobPost.id))
                .join(TitleNorm, JobPost.title_norm_id == TitleNorm.id)
                .where(
                    JobPost.is_active.is_(True),
                    JobPost.first_seen >= since,
                    TitleNorm.family == fam,
                )
            ).scalar()
            or 0
        )

        result.append(
            {
                "role_family": fam,
                "demand_count": demand,
                "recent_postings": recent,
                "key_skills": [
                    {"skill": r.skill_name, "share": round(r.skill_share, 4)}
                    for r in skills
                ],
                "experience_distribution": [
                    {"band": r.experience_band, "share": round(r.experience_share, 4)}
                    for r in exp_rows
                ],
                "confidence_tier": _confidence_tier(demand),
            }
        )

    return {
        "report_type": "employer",
        "generated_at": datetime.utcnow().isoformat(),
        "window_days": window_days,
        "role_family_filter": role_family,
        "roles": result,
    }


def build_county_report(
    db: Session,
    county: str | None = None,
    window_days: int = 90,
) -> dict[str, Any]:
    """T-DS-972: Report dataset for county / regional labour offices.

    Shows local demand by role family, salary bands, and top hiring sectors.
    """
    since = datetime.utcnow() - timedelta(days=window_days)

    loc_filter = []
    if county:
        from sqlalchemy import or_

        loc_filter = [
            or_(
                Location.city.ilike(f"%{county}%"),
                Location.region.ilike(f"%{county}%"),
            )
        ]

    # Postings by role family in this county
    family_stmt = (
        select(TitleNorm.family, func.count(JobPost.id).label("cnt"))
        .join(JobPost, JobPost.title_norm_id == TitleNorm.id)
        .join(Location, JobPost.location_id == Location.id)
        .where(JobPost.is_active.is_(True), JobPost.first_seen >= since)
        .group_by(TitleNorm.family)
        .order_by(desc("cnt"))
    )
    if loc_filter:
        family_stmt = family_stmt.where(*loc_filter)
    family_counts = db.execute(family_stmt).all()

    # Salary stats for this county
    salary_stmt = (
        select(
            func.avg(JobPost.salary_min).label("avg_min"),
            func.avg(JobPost.salary_max).label("avg_max"),
            func.count(JobPost.id).label("with_salary"),
        )
        .join(Location, JobPost.location_id == Location.id)
        .where(
            JobPost.is_active.is_(True),
            JobPost.first_seen >= since,
            JobPost.salary_min.is_not(None),
        )
    )
    if loc_filter:
        salary_stmt = salary_stmt.where(*loc_filter)
    salary_row = db.execute(salary_stmt).one()

    # Top hiring orgs in this county
    orgs_stmt = (
        select(
            Organization.name, Organization.sector, func.count(JobPost.id).label("cnt")
        )
        .join(JobPost, JobPost.org_id == Organization.id)
        .join(Location, JobPost.location_id == Location.id)
        .where(JobPost.is_active.is_(True), JobPost.first_seen >= since)
        .group_by(Organization.name, Organization.sector)
        .order_by(desc("cnt"))
        .limit(15)
    )
    if loc_filter:
        orgs_stmt = orgs_stmt.where(*loc_filter)
    top_orgs = db.execute(orgs_stmt).all()

    total_postings = sum(cnt for _, cnt in family_counts)

    return {
        "report_type": "county",
        "generated_at": datetime.utcnow().isoformat(),
        "county": county or "All counties",
        "window_days": window_days,
        "total_postings": total_postings,
        "demand_by_role_family": [
            {
                "role_family": fam,
                "postings": cnt,
                "share": round(cnt / total_postings, 4) if total_postings else 0,
            }
            for fam, cnt in family_counts
        ],
        "salary_summary": {
            "avg_min": round(salary_row.avg_min, 0) if salary_row.avg_min else None,
            "avg_max": round(salary_row.avg_max, 0) if salary_row.avg_max else None,
            "postings_with_salary": salary_row.with_salary or 0,
        },
        "top_hiring_organisations": [
            {"name": name, "sector": sector, "postings": cnt}
            for name, sector, cnt in top_orgs
        ],
    }


def build_training_provider_report(
    db: Session,
    skill_focus: list[str] | None = None,
    top_gaps: int = 20,
    window_days: int = 180,
) -> dict[str, Any]:
    """T-DS-972: Report dataset for training providers and bootcamps.

    Shows the most demanded skills, which are highest-share in baselines
    (i.e. the ones training providers should prioritise), and their
    association to role families.
    """
    # Aggregate skill demand across all role families
    skill_stmt = (
        select(
            RoleSkillBaseline.skill_name,
            func.avg(RoleSkillBaseline.skill_share).label("avg_share"),
            func.count(RoleSkillBaseline.role_family).label("family_count"),
            func.sum(
                func.cast(RoleSkillBaseline.low_confidence, type_=func.Integer)
                if False
                else RoleSkillBaseline.count_total_jobs_used
            ).label("total_jobs"),
        )
        .group_by(RoleSkillBaseline.skill_name)
        .order_by(desc("avg_share"))
        .limit(top_gaps * 2)
    )
    raw_skills = db.execute(skill_stmt).all()

    # If skill_focus filter is provided, filter to those skills
    if skill_focus:
        focus_lower = {s.lower() for s in skill_focus}
        raw_skills = [r for r in raw_skills if r.skill_name.lower() in focus_lower]

    # For each top skill, find which role families it appears in
    skill_families: dict[str, list[str]] = defaultdict(list)
    fam_rows = db.execute(
        select(RoleSkillBaseline.skill_name, RoleSkillBaseline.role_family).where(
            RoleSkillBaseline.skill_share >= 0.1
        )
    ).all()
    for skill, fam in fam_rows:
        skill_families[skill].append(fam)

    top_skills = []
    for row in raw_skills[:top_gaps]:
        top_skills.append(
            {
                "skill": row.skill_name,
                "avg_share_across_roles": round(float(row.avg_share or 0), 4),
                "role_families": sorted(skill_families.get(row.skill_name, [])),
                "family_count": int(row.family_count or 0),
            }
        )

    # Low-confidence role families (need more data)
    low_conf_families = (
        db.execute(
            select(RoleSkillBaseline.role_family)
            .where(RoleSkillBaseline.low_confidence.is_(True))
            .distinct()
        )
        .scalars()
        .all()
    )

    return {
        "report_type": "training_provider",
        "generated_at": datetime.utcnow().isoformat(),
        "window_days": window_days,
        "skill_focus_filter": skill_focus,
        "top_demanded_skills": top_skills,
        "low_coverage_role_families": sorted(low_conf_families),
        "meta": {
            "note": (
                "avg_share_across_roles is the mean share of job postings that list "
                "this skill across all role families. Higher = more universally demanded."
            )
        },
    }


# ---------------------------------------------------------------------------
# T-DS-973: Salary intelligence with confidence + error tracking
# ---------------------------------------------------------------------------

_LOW_CONFIDENCE_THRESHOLD = 0.6
_salary_low_confidence_log: list[dict[str, Any]] = []  # in-process audit trail


def get_salary_with_market_context(
    db: Session,
    role_family: str | None,
    location: str | None = None,
    seniority: str | None = None,
    currency: str = "KES",
    window_days: int = 180,
) -> dict[str, Any]:
    """T-DS-973: Salary estimate enriched with live market data and confidence tracking.

    Strategy:
    1. Try to pull median salary from MetricsDaily for this role family.
    2. If found and sample is sufficient → data_backed confidence.
    3. Otherwise fall back to SalaryService heuristic estimate.
    4. Log low-confidence calls for operational monitoring.
    """
    since = datetime.utcnow() - timedelta(days=window_days)

    # --- Attempt market-data backed estimate ---
    if role_family:
        metrics_q = select(
            func.avg(MetricsDaily.salary_p50).label("avg_p50"),
            func.count(MetricsDaily.id).label("n"),
        ).where(
            MetricsDaily.role_family == role_family,
            MetricsDaily.date >= since,
            MetricsDaily.salary_p50.is_not(None),
        )
        if location:
            metrics_q = metrics_q.where(
                MetricsDaily.location_key.ilike(f"%{location}%")
            )
        db.execute(metrics_q).one()

    # Also try pulling from job postings directly
    job_salary_q = (
        select(JobPost.salary_min, JobPost.salary_max, JobPost.currency)
        .join(TitleNorm, JobPost.title_norm_id == TitleNorm.id, isouter=True)
        .where(JobPost.salary_min.is_not(None), JobPost.first_seen >= since)
    )
    if role_family:
        job_salary_q = job_salary_q.where(TitleNorm.family == role_family)
    if location:
        job_salary_q = job_salary_q.join(
            Location, JobPost.location_id == Location.id, isouter=True
        ).where(
            Location.city.ilike(f"%{location}%")
            | Location.region.ilike(f"%{location}%")
        )
    salary_rows = db.execute(job_salary_q).all()
    salary_mins = [r.salary_min for r in salary_rows if r.salary_min]
    salary_maxes = [r.salary_max for r in salary_rows if r.salary_max]

    if len(salary_mins) >= 10:
        salary_mins_sorted = sorted(salary_mins)
        n = len(salary_mins_sorted)
        p25 = salary_mins_sorted[n // 4]
        p50 = salary_mins_sorted[n // 2]
        p75 = salary_mins_sorted[3 * n // 4]
        p90 = salary_mins_sorted[int(n * 0.9)]
        avg_max = sum(salary_maxes) / len(salary_maxes) if salary_maxes else None
        data_source = "market_data"
        confidence_tier = _confidence_tier(n)
        confidence_score = min(0.55 + 0.05 * min(n, 9), 0.95) if n >= 10 else 0.4
        market_estimate = {
            "min": int(p25),
            "median": int(p50),
            "max": int(p75),
            "p90": int(p90),
            "avg_max_posted": int(avg_max) if avg_max else None,
            "currency": currency,
            "sample_size": n,
        }
    else:
        # Fall back to heuristic
        svc = SalaryService()
        heuristic = svc.estimate_salary_range(
            title=role_family,
            seniority=seniority,
            location_text=location,
            currency=currency,
        )
        data_source = "heuristic_estimate"
        confidence_score = float(heuristic["confidence"])
        confidence_tier = _confidence_tier(len(salary_mins))
        market_estimate = {
            "min": heuristic["min"],
            "median": (heuristic["min"] + heuristic["max"]) // 2,
            "max": heuristic["max"],
            "p90": heuristic["max"],
            "avg_max_posted": None,
            "currency": heuristic["currency"],
            "sample_size": len(salary_mins),
        }

    result = {
        "role_family": role_family or "general",
        "location": location or "all",
        "seniority": seniority,
        "salary": market_estimate,
        "confidence": {
            "score": round(confidence_score, 3),
            "tier": confidence_tier,
            "data_source": data_source,
            "note": _confidence_note(confidence_tier, market_estimate["sample_size"]),
        },
        "generated_at": datetime.utcnow().isoformat(),
    }

    # T-DS-973: Log low-confidence calls
    if confidence_score < _LOW_CONFIDENCE_THRESHOLD:
        _record_low_confidence_salary(
            role_family, location, seniority, confidence_score
        )

    return result


def _record_low_confidence_salary(
    role_family: str | None,
    location: str | None,
    seniority: str | None,
    confidence_score: float,
) -> None:
    """T-DS-973: Append a low-confidence salary call to the in-process audit log."""
    entry = {
        "role_family": role_family,
        "location": location,
        "seniority": seniority,
        "confidence_score": confidence_score,
        "logged_at": datetime.utcnow().isoformat(),
    }
    _salary_low_confidence_log.append(entry)
    if len(_salary_low_confidence_log) > 500:
        # Keep log bounded
        _salary_low_confidence_log.pop(0)
    logger.warning(
        "Low-confidence salary estimate: role=%s location=%s score=%.2f",
        role_family,
        location,
        confidence_score,
    )


def get_salary_low_confidence_log(limit: int = 50) -> list[dict[str, Any]]:
    """T-DS-973: Return the most recent low-confidence salary calls."""
    return list(reversed(_salary_low_confidence_log))[:limit]


def get_salary_confidence_summary(db: Session, window_days: int = 90) -> dict[str, Any]:
    """T-DS-973: Summary of salary data coverage by role family."""
    from sqlalchemy import case

    since = datetime.utcnow() - timedelta(days=window_days)

    rows = db.execute(
        select(
            TitleNorm.family,
            func.count(JobPost.id).label("total"),
            func.sum(
                case((JobPost.salary_min.is_not(None), 1), else_=0)
            ).label("with_salary"),
        )
        .join(TitleNorm, JobPost.title_norm_id == TitleNorm.id, isouter=True)
        .where(JobPost.is_active.is_(True), JobPost.first_seen >= since)
        .group_by(TitleNorm.family)
        .order_by(desc("total"))
    ).all()

    summary = []
    for fam, total, with_sal in rows:
        with_sal = with_sal or 0
        coverage_pct = round(with_sal / total * 100, 1) if total else 0
        tier = (
            "data_backed"
            if with_sal >= 10
            else ("partial" if with_sal >= 3 else "heuristic_only")
        )
        summary.append(
            {
                "role_family": fam or "unknown",
                "total_postings": total,
                "postings_with_salary": with_sal,
                "salary_coverage_pct": coverage_pct,
                "confidence_tier": tier,
            }
        )

    overall_total = sum(r["total_postings"] for r in summary)
    overall_with_salary = sum(r["postings_with_salary"] for r in summary)

    return {
        "window_days": window_days,
        "overall_salary_coverage_pct": round(
            overall_with_salary / overall_total * 100, 1
        )
        if overall_total
        else 0,
        "by_role_family": summary,
        "recent_low_confidence_calls": len(_salary_low_confidence_log),
    }

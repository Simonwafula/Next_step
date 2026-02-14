from collections import Counter
from datetime import datetime, timedelta

import pandas as pd
from sqlalchemy import select, func, desc, text
from sqlalchemy.orm import Session

from ..db.models import (
    JobPost,
    JobEntities,
    TitleNorm,
    SkillTrendsMonthly,
    RoleEvolution,
    TitleAdjacency,
    JobSkill,
    Skill,
)


def aggregate_skill_trends(db: Session):
    """
    Populate SkillTrendsMonthly from JobEntities.
    Aggregation: count occurrences of skills per role family per month.
    """
    # 1. Fetch raw entity data
    stmt = (
        select(JobPost.first_seen, TitleNorm.family, JobEntities.skills)
        .join(TitleNorm, JobPost.title_norm_id == TitleNorm.id)
        .join(JobEntities, JobPost.id == JobEntities.job_id)
    )

    rows = db.execute(stmt).all()
    if not rows:
        return {"status": "warning", "message": "No entity data found for aggregation"}

    data = []
    for dt, family, skills in rows:
        month = dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        # skills is stored as JSONB list
        for skill in skills or []:
            data.append({"month": month, "family": family, "skill": skill})

    df = pd.DataFrame(data)
    if df.empty:
        return {"status": "warning", "message": "No skills extracted for aggregation"}

    # 2. Group and count
    counts = df.groupby(["month", "family", "skill"]).size().reset_index(name="count")

    # 3. Save to SkillTrendsMonthly
    db.execute(
        text("DELETE FROM skill_trends_monthly")
    )  # Reset baseline for simplicity

    for _, row in counts.iterrows():
        trend = SkillTrendsMonthly(
            skill=row["skill"],
            title_norm=row["family"],
            month=row["month"],
            count=int(row["count"]),
            share=0.0,  # Could calculate relative share here
        )
        db.add(trend)

    db.commit()
    return {"status": "success", "count": len(counts)}


def generate_role_evolution(db: Session):
    """Identify top skills per role family to track evolution."""
    # Similar logic to skill trends but focusing on top-K per month
    db.execute(text("DELETE FROM role_evolution"))
    # ... logic to find top skills ...
    db.commit()
    return {"status": "success"}


def refresh_analytics_baseline(db: Session):
    """Main entry point for CLI to refresh all analytics tables."""
    skill_results = aggregate_skill_trends(db)
    generate_role_evolution(db)

    status = "success" if skill_results["status"] == "success" else "warning"
    return {
        "status": status,
        "message": f"Analytics baseline refreshed. Skill trends: {skill_results.get('count', 0)} rows.",
    }


def get_skill_trends(
    db: Session,
    role_family: str | None = None,
    months: int = 6,
    limit: int = 50,
) -> dict:
    since = datetime.utcnow().replace(day=1) - timedelta(days=30 * max(months, 1))
    stmt = select(SkillTrendsMonthly).where(SkillTrendsMonthly.month >= since)
    if role_family:
        stmt = stmt.where(SkillTrendsMonthly.title_norm == role_family)
    rows = (
        db.execute(
            stmt.order_by(
                desc(SkillTrendsMonthly.month), desc(SkillTrendsMonthly.count)
            ).limit(limit)
        )
        .scalars()
        .all()
    )
    return {
        "role_family": role_family,
        "items": [
            {
                "skill": row.skill,
                "role_family": row.title_norm,
                "month": row.month.date().isoformat() if row.month else None,
                "count": row.count,
                "share": row.share,
            }
            for row in rows
        ],
    }


def get_role_evolution(
    db: Session,
    role_family: str | None = None,
    months: int = 6,
    limit: int = 24,
) -> dict:
    since = datetime.utcnow().replace(day=1) - timedelta(days=30 * max(months, 1))
    stmt = select(RoleEvolution).where(RoleEvolution.month >= since)
    if role_family:
        stmt = stmt.where(RoleEvolution.title_norm == role_family)
    rows = (
        db.execute(stmt.order_by(desc(RoleEvolution.month)).limit(limit))
        .scalars()
        .all()
    )
    return {
        "role_family": role_family,
        "items": [
            {
                "role_family": row.title_norm,
                "month": row.month.date().isoformat() if row.month else None,
                "top_skills": row.top_skills or {},
            }
            for row in rows
        ],
    }


def get_title_adjacency(db: Session, title: str | None = None, limit: int = 25) -> dict:
    stmt = select(TitleAdjacency)
    if title:
        stmt = stmt.where(
            (TitleAdjacency.title_a == title) | (TitleAdjacency.title_b == title)
        )
    rows = (
        db.execute(stmt.order_by(desc(TitleAdjacency.similarity)).limit(limit))
        .scalars()
        .all()
    )
    return {
        "title": title,
        "items": [
            {
                "title_a": row.title_a,
                "title_b": row.title_b,
                "similarity": row.similarity,
            }
            for row in rows
        ],
    }


def _top_counts(counts: dict[str, int], top_n: int) -> list[tuple[str, int]]:
    return Counter(counts).most_common(top_n)


def _calculate_overlap(
    recent: list[tuple[str, int]], baseline: list[tuple[str, int]]
) -> float:
    recent_keys = {key for key, _ in recent}
    baseline_keys = {key for key, _ in baseline}
    if not recent_keys or not baseline_keys:
        return 0.0
    return len(recent_keys & baseline_keys) / max(len(recent_keys), len(baseline_keys))


def _fetch_skill_counts(
    db: Session,
    since: datetime,
    until: datetime | None = None,
) -> dict[str, int]:
    stmt = (
        select(Skill.name, func.count(JobSkill.id))
        .join(JobSkill, JobSkill.skill_id == Skill.id)
        .join(JobPost, JobPost.id == JobSkill.job_post_id)
        .where(JobPost.first_seen >= since)
        .group_by(Skill.name)
    )
    if until is not None:
        stmt = stmt.where(JobPost.first_seen < until)
    return {name: count for name, count in db.execute(stmt).all() if name}


def _fetch_title_counts(
    db: Session,
    since: datetime,
    until: datetime | None = None,
) -> dict[str, int]:
    stmt = (
        select(TitleNorm.family, func.count(JobPost.id))
        .join(JobPost, JobPost.title_norm_id == TitleNorm.id)
        .where(JobPost.first_seen >= since)
        .group_by(TitleNorm.family)
    )
    if until is not None:
        stmt = stmt.where(JobPost.first_seen < until)
    return {name: count for name, count in db.execute(stmt).all() if name}


def _fetch_salary_series(
    db: Session,
    since: datetime,
    until: datetime | None = None,
) -> list[float]:
    stmt = (
        select(JobPost.salary_min)
        .where(JobPost.first_seen >= since)
        .where(JobPost.salary_min.is_not(None))
    )
    if until is not None:
        stmt = stmt.where(JobPost.first_seen < until)
    return [value for (value,) in db.execute(stmt).all() if value]


def _median(values: list[float]) -> float | None:
    if not values:
        return None
    values = sorted(values)
    mid = len(values) // 2
    if len(values) % 2 == 1:
        return float(values[mid])
    return (values[mid - 1] + values[mid]) / 2.0


def run_drift_checks(
    db: Session,
    recent_days: int = 30,
    baseline_days: int = 180,
    top_n: int = 20,
) -> dict:
    recent_since = datetime.utcnow() - timedelta(days=max(recent_days, 1))
    baseline_since = datetime.utcnow() - timedelta(
        days=max(baseline_days, recent_days + 1)
    )

    recent_skills = _fetch_skill_counts(db, recent_since)
    baseline_skills = _fetch_skill_counts(db, baseline_since, until=recent_since)
    recent_titles = _fetch_title_counts(db, recent_since)
    baseline_titles = _fetch_title_counts(db, baseline_since, until=recent_since)

    recent_skill_top = _top_counts(recent_skills, top_n)
    baseline_skill_top = _top_counts(baseline_skills, top_n)
    recent_title_top = _top_counts(recent_titles, top_n)
    baseline_title_top = _top_counts(baseline_titles, top_n)

    skill_overlap = _calculate_overlap(recent_skill_top, baseline_skill_top)
    title_overlap = _calculate_overlap(recent_title_top, baseline_title_top)

    recent_salary = _median(_fetch_salary_series(db, recent_since))
    baseline_salary = _median(
        _fetch_salary_series(db, baseline_since, until=recent_since)
    )
    salary_delta = None
    if recent_salary and baseline_salary:
        salary_delta = (recent_salary - baseline_salary) / baseline_salary

    return {
        "status": "success",
        "recent_window_days": recent_days,
        "baseline_window_days": baseline_days,
        "skills": {
            "overlap_ratio": round(skill_overlap, 3),
            "drift_score": round(1 - skill_overlap, 3),
            "recent_top": recent_skill_top,
            "baseline_top": baseline_skill_top,
        },
        "titles": {
            "overlap_ratio": round(title_overlap, 3),
            "drift_score": round(1 - title_overlap, 3),
            "recent_top": recent_title_top,
            "baseline_top": baseline_title_top,
        },
        "salary": {
            "recent_median": recent_salary,
            "baseline_median": baseline_salary,
            "delta_ratio": round(salary_delta, 3) if salary_delta is not None else None,
        },
    }

from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.models import (
    RoleDemandSnapshot,
    RoleEducationBaseline,
    RoleExperienceBaseline,
    RoleSkillBaseline,
    TitleNorm,
)
from ..normalization.titles import normalize_title


def _latest_demand_by_family(db: Session) -> dict[str, RoleDemandSnapshot]:
    rows = db.execute(select(RoleDemandSnapshot)).scalars().all()
    latest: dict[str, RoleDemandSnapshot] = {}

    for row in rows:
        current = latest.get(row.role_family)
        if current is None or row.updated_at >= current.updated_at:
            latest[row.role_family] = row

    return latest


def _canonical_titles_by_family(db: Session) -> dict[str, list[str]]:
    rows = db.execute(
        select(TitleNorm.family, TitleNorm.canonical_title)
    ).all()
    grouped: dict[str, set[str]] = defaultdict(set)

    for family, canonical_title in rows:
        if family and canonical_title:
            grouped[family].add(canonical_title)

    return {
        family: sorted(canonical_titles)
        for family, canonical_titles in grouped.items()
    }


def _education_distribution(db: Session) -> dict[str, list[dict]]:
    rows = db.execute(select(RoleEducationBaseline)).scalars().all()
    grouped: dict[str, list[dict]] = defaultdict(list)

    for row in rows:
        grouped[row.role_family].append(
            {
                "education_level": row.education_level,
                "share": row.education_share,
                "count_total_jobs_used": row.count_total_jobs_used,
                "sample_job_ids": row.sample_job_ids,
            }
        )

    return grouped


def _experience_distribution(db: Session) -> dict[str, list[dict]]:
    rows = db.execute(select(RoleExperienceBaseline)).scalars().all()
    grouped: dict[str, list[dict]] = defaultdict(list)

    for row in rows:
        grouped[row.role_family].append(
            {
                "experience_band": row.experience_band,
                "share": row.experience_share,
                "count_total_jobs_used": row.count_total_jobs_used,
                "sample_job_ids": row.sample_job_ids,
            }
        )

    return grouped


def _skill_distribution(db: Session) -> dict[str, list[dict]]:
    rows = db.execute(select(RoleSkillBaseline)).scalars().all()
    grouped: dict[str, list[dict]] = defaultdict(list)

    for row in rows:
        grouped[row.role_family].append(
            {
                "skill_name": row.skill_name,
                "frequency": row.skill_share,
                "count_total_jobs_used": row.count_total_jobs_used,
                "sample_job_ids": row.sample_job_ids,
            }
        )

    for family in grouped:
        grouped[family] = sorted(
            grouped[family],
            key=lambda item: item["frequency"],
            reverse=True,
        )[:10]

    return grouped


def _combined_sample_ids(*sample_lists: list[int]) -> list[int]:
    seen = set()
    combined: list[int] = []

    for sample_list in sample_lists:
        for job_id in sample_list:
            if job_id not in seen:
                seen.add(job_id)
                combined.append(job_id)

    return combined[:10]


def explore_careers(
    db: Session,
    query: str | None = None,
    limit: int = 10,
) -> dict:
    demand_by_family = _latest_demand_by_family(db)
    if not demand_by_family:
        return {
            "guided_results": [],
            "message": (
                "Insights not yet available — run baseline aggregation first"
            ),
        }

    skill_map = _skill_distribution(db)
    education_map = _education_distribution(db)
    experience_map = _experience_distribution(db)
    titles_map = _canonical_titles_by_family(db)

    families = list(demand_by_family.keys())

    if query:
        family_hint, canonical_hint = normalize_title(query)
        query_lower = query.lower()
        families = [
            family
            for family in families
            if family == family_hint
            or query_lower in family.replace("_", " ").lower()
            or any(
                query_lower in title.lower()
                for title in titles_map.get(family, [])
            )
            or query_lower in canonical_hint.lower()
        ]

    cards = []
    for family in families:
        demand = demand_by_family.get(family)
        if not demand:
            continue

        top_skills = skill_map.get(family, [])
        education_distribution = education_map.get(family, [])
        experience_distribution = experience_map.get(family, [])
        canonical_titles = titles_map.get(family, [])

        sample_job_ids = _combined_sample_ids(
            demand.sample_job_ids,
            *[entry["sample_job_ids"] for entry in top_skills],
            *[entry["sample_job_ids"] for entry in education_distribution],
            *[entry["sample_job_ids"] for entry in experience_distribution],
        )

        cards.append(
            {
                "role_family": family,
                "description": ", ".join(canonical_titles[:5]),
                "canonical_titles": canonical_titles,
                "top_skills": top_skills,
                "education_distribution": education_distribution,
                "experience_distribution": experience_distribution,
                "demand": {
                    "count_ads": demand.demand_count,
                    "count_total_jobs_used": demand.count_total_jobs_used,
                },
                "sample_job_ids": sample_job_ids,
                "low_confidence": demand.count_total_jobs_used < 10,
            }
        )

    cards = sorted(
        cards,
        key=lambda item: item["demand"]["count_ads"],
        reverse=True,
    )[:limit]

    return {"guided_results": cards}

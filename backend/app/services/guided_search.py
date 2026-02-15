from collections import defaultdict

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..db.models import (
    JobPost,
    RoleDemandSnapshot,
    RoleEducationBaseline,
    RoleExperienceBaseline,
    RoleSkillBaseline,
    TitleNorm,
)
from ..normalization.titles import normalize_title
from .recommend import calculate_skill_overlap


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
        family_hint, _ = normalize_title(query)
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


def _normalize_skill_list(skills: list[str] | None) -> list[str]:
    if not skills:
        return []
    normalized = []
    seen = set()
    for skill in skills:
        value = " ".join(str(skill).strip().split())
        lowered = value.casefold()
        if value and lowered not in seen:
            seen.add(lowered)
            normalized.append(value)
    return normalized


def _education_rank(level: str | None) -> int:
    if not level:
        return 0

    text = level.casefold()
    if "phd" in text or "doctor" in text:
        return 4
    if "master" in text or "msc" in text or "m.s" in text:
        return 3
    if "bachelor" in text or "bsc" in text or "b.s" in text:
        return 2
    if "certificate" in text or "diploma" in text:
        return 1
    return 0


def _education_fit_score(
    user_education: str | None,
    required_education: str,
) -> float:
    required_rank = _education_rank(required_education)
    user_rank = _education_rank(user_education)
    if user_rank >= required_rank:
        return 1.0
    if required_rank - user_rank == 1:
        return 0.5
    return 0.0


def _starter_jobs_for_family(
    db: Session,
    family: str,
    limit: int = 5,
) -> list[dict]:
    rows = db.execute(
        select(JobPost, TitleNorm)
        .join(TitleNorm, TitleNorm.id == JobPost.title_norm_id)
        .where(
            TitleNorm.family == family,
            JobPost.is_active.is_(True),
            or_(
                JobPost.seniority.ilike("%entry%"),
                JobPost.seniority.ilike("%junior%"),
            ),
        )
        .order_by(JobPost.last_seen.desc())
        .limit(limit)
    ).all()

    return [
        {
            "id": job_post.id,
            "title": job_post.title_raw,
            "url": job_post.url,
            "seniority": job_post.seniority,
            "role_family": title_norm.family if title_norm else None,
        }
        for job_post, title_norm in rows
    ]


def match_roles(
    db: Session,
    query: str | None,
    user_skills: list[str],
    education: str | None,
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

    normalized_user_skills = _normalize_skill_list(user_skills)
    skill_map = _skill_distribution(db)
    education_map = _education_distribution(db)
    titles_map = _canonical_titles_by_family(db)

    families = list(demand_by_family.keys())
    if query:
        family_hint, _ = normalize_title(query)
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
        ]

    matches = []
    for family in families:
        top_skills = skill_map.get(family, [])
        if not top_skills:
            continue

        target_skills = [
            (entry["skill_name"], float(entry["frequency"] * 100))
            for entry in top_skills
        ]
        _, missing_skills = calculate_skill_overlap(
            normalized_user_skills,
            target_skills,
        )

        target_skill_names = [skill_name for skill_name, _ in target_skills]
        overlap_count = len(
            {
                skill.casefold() for skill in normalized_user_skills
            }
            & {
                skill_name.casefold() for skill_name in target_skill_names
            }
        )
        skill_overlap_score = (
            overlap_count / len(target_skill_names)
            if target_skill_names
            else 0.0
        )

        matching_skills = [
            skill_name
            for skill_name, _ in target_skills
            if skill_name.casefold()
            in {skill.casefold() for skill in normalized_user_skills}
        ]

        education_distribution = education_map.get(family, [])
        if education_distribution:
            required_education = max(
                education_distribution,
                key=lambda row: row["share"],
            )["education_level"]
        else:
            required_education = "Not specified"

        education_fit = _education_fit_score(education, required_education)
        match_score = (skill_overlap_score * 0.7) + (education_fit * 0.3)

        demand = demand_by_family.get(family)
        starter_jobs = _starter_jobs_for_family(db, family)
        sample_job_ids = _combined_sample_ids(
            demand.sample_job_ids if demand else [],
            *[entry["sample_job_ids"] for entry in top_skills],
        )

        matches.append(
            {
                "role_family": family,
                "match_score": round(match_score, 4),
                "matching_skills": matching_skills,
                "missing_skills": missing_skills[:5],
                "required_education": required_education,
                "education_fit": education_fit,
                "starter_jobs": starter_jobs,
                "sample_job_ids": sample_job_ids,
                "low_confidence": (
                    demand.count_total_jobs_used < 10 if demand else True
                ),
            }
        )

    matches = sorted(matches, key=lambda row: row["match_score"], reverse=True)
    return {"guided_results": matches[:limit]}

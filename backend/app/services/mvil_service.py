import logging
import re
from collections import defaultdict
from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..db.models import (
    JobEntities,
    JobPost,
    JobSkill,
    RoleDemandSnapshot,
    RoleEducationBaseline,
    RoleExperienceBaseline,
    RoleSkillBaseline,
    Skill,
    TitleNorm,
)

logger = logging.getLogger(__name__)

MIN_FAMILY_JOBS = 3
LOW_CONFIDENCE_THRESHOLD = 10
MAX_SAMPLE_JOB_IDS = 10


def _clean_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def _family_jobs(db: Session) -> dict[str, list[JobPost]]:
    rows = db.execute(
        select(JobPost, TitleNorm.family)
        .join(TitleNorm, TitleNorm.id == JobPost.title_norm_id)
        .where(TitleNorm.family.is_not(None), TitleNorm.family != "other")
    ).all()

    grouped: dict[str, list[JobPost]] = defaultdict(list)
    for job_post, family in rows:
        if family:
            grouped[family].append(job_post)

    return {
        family: jobs
        for family, jobs in grouped.items()
        if len(jobs) >= MIN_FAMILY_JOBS
    }


def _entities_by_job(
    db: Session,
    job_ids: list[int],
) -> dict[int, JobEntities]:
    if not job_ids:
        return {}

    rows = db.execute(
        select(JobEntities).where(JobEntities.job_id.in_(job_ids))
    ).scalars()
    return {row.job_id: row for row in rows}


def _active_recent_job_ids(jobs: list[JobPost]) -> list[int]:
    sorted_jobs = sorted(
        (job for job in jobs if job.is_active),
        key=lambda job: job.last_seen or datetime.min,
        reverse=True,
    )
    return [job.id for job in sorted_jobs[:MAX_SAMPLE_JOB_IDS]]


def _extract_nested_skill_values(raw_skills: object) -> list[str]:
    if raw_skills is None:
        return []

    extracted: list[str] = []

    if isinstance(raw_skills, list):
        for item in raw_skills:
            if isinstance(item, str):
                text_value = _clean_text(item)
                if text_value:
                    extracted.append(text_value)
            elif isinstance(item, dict):
                for key in ("name", "skill", "value"):
                    if key in item and _clean_text(item[key]):
                        extracted.append(_clean_text(item[key]))
                        break
                else:
                    for dict_key in item.keys():
                        if _clean_text(dict_key):
                            extracted.append(_clean_text(dict_key))
            elif item is not None:
                text_value = _clean_text(item)
                if text_value:
                    extracted.append(text_value)

    elif isinstance(raw_skills, dict):
        for key, value in raw_skills.items():
            key_text = _clean_text(key)
            if key_text:
                extracted.append(key_text)
            if isinstance(value, str):
                value_text = _clean_text(value)
                if value_text:
                    extracted.append(value_text)
            elif isinstance(value, list):
                for list_item in value:
                    list_text = _clean_text(list_item)
                    if list_text:
                        extracted.append(list_text)

    elif isinstance(raw_skills, str):
        text_value = _clean_text(raw_skills)
        if text_value:
            extracted.append(text_value)

    deduplicated = []
    seen = set()
    for skill_name in extracted:
        normalized = " ".join(skill_name.split())
        key = normalized.casefold()
        if key and key not in seen:
            seen.add(key)
            deduplicated.append(normalized)

    return deduplicated


def _normalize_education(value: object) -> str:
    text = _clean_text(value).casefold()

    if not text:
        return "Not specified"

    if any(token in text for token in ("phd", "doctor", "doctoral")):
        return "PhD"
    if any(
        token in text
        for token in ("master", "msc", "m.sc", "m.s", "ma", "mba")
    ):
        return "Master's"
    if any(
        token in text
        for token in (
            "bachelor",
            "bsc",
            "b.sc",
            "b.s",
            "ba",
            "bs",
            "undergraduate",
        )
    ):
        return "Bachelor's"
    if any(
        token in text for token in ("diploma", "certificate", "certification")
    ):
        return "Certificate/Diploma"

    return "Not specified"


def _education_level_from_record(
    entities_row: JobEntities | None,
    job_post: JobPost,
) -> str:
    education_value = None
    if entities_row and isinstance(entities_row.education, dict):
        joined_values = " ".join(
            _clean_text(value)
            for value in entities_row.education.values()
            if _clean_text(value)
        )
        if joined_values:
            education_value = joined_values

    if not education_value:
        education_value = job_post.education

    return _normalize_education(education_value)


def _experience_band_from_years(years_value: float | None) -> str:
    if years_value is None:
        return "Not specified"
    if years_value <= 2:
        return "0-2 years"
    if years_value <= 5:
        return "3-5 years"
    if years_value <= 10:
        return "5-10 years"
    return "10+ years"


def _extract_experience_years(value: object) -> float | None:
    text = _clean_text(value)
    if not text:
        return None

    text_lower = text.casefold()

    range_match = re.search(r"(\d+)\s*(?:-|to)\s*(\d+)", text_lower)
    if range_match:
        start_value = float(range_match.group(1))
        end_value = float(range_match.group(2))
        return (start_value + end_value) / 2

    single_match = re.search(r"(\d+)\+?\s*(?:years?|yrs?)", text_lower)
    if single_match:
        return float(single_match.group(1))

    if any(
        token in text_lower
        for token in ("entry", "junior", "graduate", "intern")
    ):
        return 1.0
    if any(token in text_lower for token in ("mid", "intermediate")):
        return 4.0
    if any(token in text_lower for token in ("senior", "staff", "expert")):
        return 7.0
    if any(token in text_lower for token in ("lead", "principal", "head")):
        return 12.0

    return None


def _experience_band_from_record(entities_row: JobEntities | None) -> str:
    if not entities_row:
        return "Not specified"

    experience_value = entities_row.experience
    if isinstance(experience_value, dict):
        joined_values = " ".join(
            _clean_text(item)
            for item in (
                list(experience_value.keys())
                + list(experience_value.values())
            )
            if _clean_text(item)
        )
    else:
        joined_values = _clean_text(experience_value)

    return _experience_band_from_years(
        _extract_experience_years(joined_values)
    )


def _is_low_confidence(total_jobs: int) -> bool:
    return total_jobs < LOW_CONFIDENCE_THRESHOLD


def _build_role_skill_rows(db: Session) -> list[RoleSkillBaseline]:
    family_jobs = _family_jobs(db)
    all_job_ids = [job.id for jobs in family_jobs.values() for job in jobs]
    entities_map = _entities_by_job(db, all_job_ids)

    job_skill_rows = db.execute(
        select(JobSkill.job_post_id, Skill.name)
        .join(Skill, Skill.id == JobSkill.skill_id)
        .where(JobSkill.job_post_id.in_(all_job_ids) if all_job_ids else False)
    ).all()

    skills_by_job: dict[int, set[str]] = defaultdict(set)
    for job_id, skill_name in job_skill_rows:
        cleaned = _clean_text(skill_name)
        if cleaned:
            skills_by_job[job_id].add(cleaned)

    baseline_rows: list[RoleSkillBaseline] = []

    for family, jobs in family_jobs.items():
        total_jobs = len(jobs)
        low_confidence = _is_low_confidence(total_jobs)
        jobs_by_id = {job.id: job for job in jobs}
        skill_to_job_ids: dict[str, set[int]] = defaultdict(set)

        for job in jobs:
            job_skills = set(skills_by_job.get(job.id, set()))
            if not job_skills:
                entity_row = entities_map.get(job.id)
                if entity_row:
                    job_skills.update(
                        _extract_nested_skill_values(entity_row.skills)
                    )

            for skill_name in job_skills:
                skill_to_job_ids[skill_name].add(job.id)

        for skill_name, skill_job_ids in sorted(skill_to_job_ids.items()):
            sorted_skill_jobs = sorted(
                (
                    jobs_by_id[job_id]
                    for job_id in skill_job_ids
                    if job_id in jobs_by_id and jobs_by_id[job_id].is_active
                ),
                key=lambda job: job.last_seen or datetime.min,
                reverse=True,
            )
            baseline_rows.append(
                RoleSkillBaseline(
                    role_family=family,
                    skill_name=skill_name,
                    skill_share=len(skill_job_ids) / total_jobs,
                    low_confidence=low_confidence,
                    sample_job_ids=[
                        job.id
                        for job in sorted_skill_jobs[:MAX_SAMPLE_JOB_IDS]
                    ],
                    count_total_jobs_used=total_jobs,
                    updated_at=datetime.utcnow(),
                )
            )

    return baseline_rows


def _build_role_education_rows(db: Session) -> list[RoleEducationBaseline]:
    family_jobs = _family_jobs(db)
    all_job_ids = [job.id for jobs in family_jobs.values() for job in jobs]
    entities_map = _entities_by_job(db, all_job_ids)

    baseline_rows: list[RoleEducationBaseline] = []

    for family, jobs in family_jobs.items():
        total_jobs = len(jobs)
        low_confidence = _is_low_confidence(total_jobs)
        jobs_by_id = {job.id: job for job in jobs}
        education_to_job_ids: dict[str, set[int]] = defaultdict(set)

        for job in jobs:
            level = _education_level_from_record(entities_map.get(job.id), job)
            education_to_job_ids[level].add(job.id)

        for level, job_ids in sorted(education_to_job_ids.items()):
            sorted_jobs = sorted(
                (
                    jobs_by_id[job_id]
                    for job_id in job_ids
                    if jobs_by_id[job_id].is_active
                ),
                key=lambda job: job.last_seen or datetime.min,
                reverse=True,
            )
            baseline_rows.append(
                RoleEducationBaseline(
                    role_family=family,
                    education_level=level,
                    education_share=len(job_ids) / total_jobs,
                    low_confidence=low_confidence,
                    sample_job_ids=[
                        job.id for job in sorted_jobs[:MAX_SAMPLE_JOB_IDS]
                    ],
                    count_total_jobs_used=total_jobs,
                    updated_at=datetime.utcnow(),
                )
            )

    return baseline_rows


def _build_role_experience_rows(db: Session) -> list[RoleExperienceBaseline]:
    family_jobs = _family_jobs(db)
    all_job_ids = [job.id for jobs in family_jobs.values() for job in jobs]
    entities_map = _entities_by_job(db, all_job_ids)

    baseline_rows: list[RoleExperienceBaseline] = []

    for family, jobs in family_jobs.items():
        total_jobs = len(jobs)
        low_confidence = _is_low_confidence(total_jobs)
        jobs_by_id = {job.id: job for job in jobs}
        experience_to_job_ids: dict[str, set[int]] = defaultdict(set)

        for job in jobs:
            band = _experience_band_from_record(entities_map.get(job.id))
            experience_to_job_ids[band].add(job.id)

        for band, job_ids in sorted(experience_to_job_ids.items()):
            sorted_jobs = sorted(
                (
                    jobs_by_id[job_id]
                    for job_id in job_ids
                    if jobs_by_id[job_id].is_active
                ),
                key=lambda job: job.last_seen or datetime.min,
                reverse=True,
            )
            baseline_rows.append(
                RoleExperienceBaseline(
                    role_family=family,
                    experience_band=band,
                    experience_share=len(job_ids) / total_jobs,
                    low_confidence=low_confidence,
                    sample_job_ids=[
                        job.id for job in sorted_jobs[:MAX_SAMPLE_JOB_IDS]
                    ],
                    count_total_jobs_used=total_jobs,
                    updated_at=datetime.utcnow(),
                )
            )

    return baseline_rows


def _build_role_demand_rows(db: Session) -> list[RoleDemandSnapshot]:
    family_jobs = _family_jobs(db)
    baseline_rows: list[RoleDemandSnapshot] = []

    for family, jobs in family_jobs.items():
        total_jobs = len(jobs)
        active_jobs = [job for job in jobs if job.is_active]
        baseline_rows.append(
            RoleDemandSnapshot(
                role_family=family,
                demand_count=len(active_jobs),
                low_confidence=_is_low_confidence(total_jobs),
                sample_job_ids=_active_recent_job_ids(jobs),
                count_total_jobs_used=total_jobs,
                updated_at=datetime.utcnow(),
            )
        )

    return baseline_rows


def _replace_rows_for_model(db: Session, model, new_rows: list[object]) -> int:
    old_ids = list(db.execute(select(model.id)).scalars())
    try:
        if new_rows:
            db.add_all(new_rows)
        db.flush()
        if old_ids:
            db.execute(delete(model).where(model.id.in_(old_ids)))
        db.commit()
    except Exception:
        db.rollback()
        raise
    return len(new_rows)


def compute_role_skill_baselines(db: Session) -> int:
    return _replace_rows_for_model(
        db,
        RoleSkillBaseline,
        _build_role_skill_rows(db),
    )


def compute_role_education_baselines(db: Session) -> int:
    return _replace_rows_for_model(
        db,
        RoleEducationBaseline,
        _build_role_education_rows(db),
    )


def compute_role_experience_baselines(db: Session) -> int:
    return _replace_rows_for_model(
        db,
        RoleExperienceBaseline,
        _build_role_experience_rows(db),
    )


def compute_role_demand_snapshots(db: Session) -> int:
    return _replace_rows_for_model(
        db,
        RoleDemandSnapshot,
        _build_role_demand_rows(db),
    )


def refresh_all_baselines(db: Session) -> dict:
    started_at = datetime.utcnow()
    skill_rows = _build_role_skill_rows(db)
    education_rows = _build_role_education_rows(db)
    experience_rows = _build_role_experience_rows(db)
    demand_rows = _build_role_demand_rows(db)

    old_ids_by_model = {
        RoleSkillBaseline: list(
            db.execute(select(RoleSkillBaseline.id)).scalars()
        ),
        RoleEducationBaseline: list(
            db.execute(select(RoleEducationBaseline.id)).scalars()
        ),
        RoleExperienceBaseline: list(
            db.execute(select(RoleExperienceBaseline.id)).scalars()
        ),
        RoleDemandSnapshot: list(
            db.execute(select(RoleDemandSnapshot.id)).scalars()
        ),
    }

    try:
        db.add_all(skill_rows)
        db.add_all(education_rows)
        db.add_all(experience_rows)
        db.add_all(demand_rows)
        db.flush()

        for model, old_ids in old_ids_by_model.items():
            if old_ids:
                db.execute(delete(model).where(model.id.in_(old_ids)))

        db.commit()
    except Exception:
        db.rollback()
        raise

    role_families = {
        row.role_family
        for row in skill_rows + education_rows + experience_rows + demand_rows
    }
    duration_seconds = (datetime.utcnow() - started_at).total_seconds()

    return {
        "status": "ok",
        "baselines_refreshed": 4,
        "role_families_processed": len(role_families),
        "duration_s": round(duration_seconds, 3),
        "rows": {
            "role_skill_baseline": len(skill_rows),
            "role_education_baseline": len(education_rows),
            "role_experience_baseline": len(experience_rows),
            "role_demand_snapshot": len(demand_rows),
        },
    }

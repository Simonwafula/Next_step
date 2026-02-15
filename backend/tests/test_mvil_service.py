from datetime import datetime, timedelta

import pytest
from sqlalchemy import select

from app.db.models import (
    JobEntities,
    JobPost,
    JobSkill,
    Organization,
    RoleDemandSnapshot,
    RoleEducationBaseline,
    RoleExperienceBaseline,
    RoleSkillBaseline,
    Skill,
    TitleNorm,
)
from app.services.mvil_service import (
    compute_role_demand_snapshots,
    compute_role_education_baselines,
    compute_role_experience_baselines,
    compute_role_skill_baselines,
    refresh_all_baselines,
)


def _seed_role_data(db_session_factory):
    db = db_session_factory()
    now = datetime.utcnow()

    org_1 = Organization(name="Data Corp")
    org_2 = Organization(name="Insights Inc")
    db.add_all([org_1, org_2])
    db.flush()

    data_family = TitleNorm(
        family="data_analytics",
        canonical_title="Data Analyst",
        aliases=["BI Analyst"],
    )
    design_family = TitleNorm(
        family="design",
        canonical_title="Product Designer",
        aliases=["UI Designer"],
    )
    other_family = TitleNorm(
        family="other",
        canonical_title="Generalist",
        aliases=[],
    )
    db.add_all([data_family, design_family, other_family])
    db.flush()

    data_jobs = [
        JobPost(
            source="test",
            url="https://example.com/jobs/data-1",
            title_raw="Data Analyst",
            title_norm_id=data_family.id,
            org_id=org_1.id,
            first_seen=now - timedelta(days=6),
            last_seen=now - timedelta(hours=1),
            is_active=True,
        ),
        JobPost(
            source="test",
            url="https://example.com/jobs/data-2",
            title_raw="Junior Data Analyst",
            title_norm_id=data_family.id,
            org_id=org_2.id,
            first_seen=now - timedelta(days=5),
            last_seen=now,
            is_active=False,
        ),
        JobPost(
            source="test",
            url="https://example.com/jobs/data-3",
            title_raw="BI Analyst",
            title_norm_id=data_family.id,
            org_id=org_1.id,
            first_seen=now - timedelta(days=3),
            last_seen=now - timedelta(hours=2),
            is_active=True,
        ),
    ]
    db.add_all(data_jobs)
    db.flush()

    design_jobs = [
        JobPost(
            source="test",
            url="https://example.com/jobs/design-1",
            title_raw="UI Designer",
            title_norm_id=design_family.id,
            org_id=org_1.id,
            first_seen=now - timedelta(days=4),
            last_seen=now - timedelta(days=1),
            is_active=True,
        ),
        JobPost(
            source="test",
            url="https://example.com/jobs/design-2",
            title_raw="Product Designer",
            title_norm_id=design_family.id,
            org_id=org_2.id,
            first_seen=now - timedelta(days=2),
            last_seen=now - timedelta(hours=3),
            is_active=True,
        ),
    ]
    db.add_all(design_jobs)
    db.flush()

    other_jobs = [
        JobPost(
            source="test",
            url=f"https://example.com/jobs/other-{index}",
            title_raw="General Role",
            title_norm_id=other_family.id,
            org_id=org_1.id,
            first_seen=now - timedelta(days=2),
            last_seen=now - timedelta(hours=index + 1),
            is_active=True,
        )
        for index in range(3)
    ]
    db.add_all(other_jobs)
    db.flush()

    python_skill = Skill(name="Python")
    sql_skill = Skill(name="SQL")
    db.add_all([python_skill, sql_skill])
    db.flush()

    db.add_all(
        [
            JobSkill(
                job_post_id=data_jobs[0].id,
                skill_id=python_skill.id,
                confidence=0.9,
            ),
            JobSkill(
                job_post_id=data_jobs[0].id,
                skill_id=sql_skill.id,
                confidence=0.9,
            ),
            JobSkill(
                job_post_id=data_jobs[1].id,
                skill_id=python_skill.id,
                confidence=0.8,
            ),
        ]
    )

    db.add_all(
        [
            JobEntities(
                job_id=data_jobs[0].id,
                skills=[{"name": "Python"}, {"name": "SQL"}],
                education={"minimum": "Bachelor of Science"},
                experience={"minimum": "1 year"},
            ),
            JobEntities(
                job_id=data_jobs[1].id,
                skills={"Python": 0.8},
                education={"preferred": "MSc"},
                experience={"range": "5-7 years"},
            ),
            JobEntities(
                job_id=data_jobs[2].id,
                skills=["Excel", "SQL"],
                education={"minimum": "Diploma"},
                experience={"level": "junior"},
            ),
            JobEntities(
                job_id=design_jobs[0].id,
                skills=["Figma"],
                education={"minimum": "Bachelor"},
                experience={"minimum": "2 years"},
            ),
            JobEntities(
                job_id=design_jobs[1].id,
                skills=["Sketch"],
                education={"minimum": "Bachelor"},
                experience={"minimum": "3 years"},
            ),
        ]
    )

    db.commit()

    data_job_ids = [data_jobs[0].id, data_jobs[1].id, data_jobs[2].id]
    active_data_job_ids = [data_jobs[0].id, data_jobs[2].id]
    db.close()

    return {
        "data_job_ids": data_job_ids,
        "active_data_job_ids": active_data_job_ids,
    }


def test_compute_role_baselines_handles_filters_shapes_and_confidence(
    db_session_factory,
):
    seeded = _seed_role_data(db_session_factory)
    db = db_session_factory()

    compute_role_skill_baselines(db)
    compute_role_education_baselines(db)
    compute_role_experience_baselines(db)
    compute_role_demand_snapshots(db)

    skill_rows = db.execute(select(RoleSkillBaseline)).scalars().all()
    assert skill_rows
    assert {row.role_family for row in skill_rows} == {"data_analytics"}
    assert all(row.low_confidence is True for row in skill_rows)
    assert all(row.count_total_jobs_used == 3 for row in skill_rows)

    excel_row = next(
        (row for row in skill_rows if row.skill_name == "Excel"),
        None,
    )
    assert excel_row is not None
    assert excel_row.skill_share == pytest.approx(1 / 3)

    education_rows = db.execute(select(RoleEducationBaseline)).scalars().all()
    assert education_rows
    assert {row.role_family for row in education_rows} == {"data_analytics"}
    assert all(row.count_total_jobs_used == 3 for row in education_rows)

    experience_rows = (
        db.execute(select(RoleExperienceBaseline)).scalars().all()
    )
    assert experience_rows
    assert {row.role_family for row in experience_rows} == {"data_analytics"}

    demand_rows = db.execute(select(RoleDemandSnapshot)).scalars().all()
    assert len(demand_rows) == 1
    demand_row = demand_rows[0]
    assert demand_row.role_family == "data_analytics"
    assert demand_row.demand_count == 2
    assert demand_row.count_total_jobs_used == 3
    assert demand_row.low_confidence is True
    assert demand_row.sample_job_ids == seeded["active_data_job_ids"]
    assert seeded["data_job_ids"][1] not in demand_row.sample_job_ids

    db.close()


def test_refresh_all_baselines_rolls_back_on_failure_preserving_old_rows(
    db_session_factory,
    monkeypatch,
):
    _seed_role_data(db_session_factory)
    db = db_session_factory()

    db.add(
        RoleDemandSnapshot(
            role_family="legacy_family",
            demand_count=99,
            sample_job_ids=[999],
            count_total_jobs_used=99,
            low_confidence=False,
        )
    )
    db.commit()

    original_flush = db.flush
    call_count = {"value": 0}

    def failing_flush(*args, **kwargs):
        call_count["value"] += 1
        if call_count["value"] == 1:
            raise RuntimeError("simulated flush failure")
        return original_flush(*args, **kwargs)

    monkeypatch.setattr(db, "flush", failing_flush)

    with pytest.raises(RuntimeError):
        refresh_all_baselines(db)

    legacy_row = db.execute(
        select(RoleDemandSnapshot).where(
            RoleDemandSnapshot.role_family == "legacy_family"
        )
    ).scalar_one_or_none()
    assert legacy_row is not None
    assert legacy_row.demand_count == 99

    db.close()

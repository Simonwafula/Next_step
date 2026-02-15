from app.db.models import (
    Base,
    RoleDemandSnapshot,
    RoleEducationBaseline,
    RoleExperienceBaseline,
    RoleSkillBaseline,
)


def test_mvil_tables_exist_in_metadata():
    tables = Base.metadata.tables
    assert "role_skill_baseline" in tables
    assert "role_education_baseline" in tables
    assert "role_experience_baseline" in tables
    assert "role_demand_snapshot" in tables


def test_mvil_models_include_required_evidence_fields():
    skill = RoleSkillBaseline(
        role_family="data_analytics",
        skill_name="python",
        skill_share=0.6,
        sample_job_ids=[1, 2, 3],
        count_total_jobs_used=12,
    )
    education = RoleEducationBaseline(
        role_family="data_analytics",
        education_level="Bachelor's",
        education_share=0.7,
        sample_job_ids=[4, 5, 6],
        count_total_jobs_used=12,
    )
    experience = RoleExperienceBaseline(
        role_family="data_analytics",
        experience_band="2-4",
        experience_share=0.5,
        sample_job_ids=[7, 8, 9],
        count_total_jobs_used=12,
    )
    demand = RoleDemandSnapshot(
        role_family="data_analytics",
        demand_count=42,
        sample_job_ids=[10, 11, 12],
        count_total_jobs_used=42,
    )

    for row in [skill, education, experience, demand]:
        assert isinstance(row.sample_job_ids, list)
        assert isinstance(row.count_total_jobs_used, int)

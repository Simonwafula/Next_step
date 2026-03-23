from datetime import datetime, timedelta

from sqlalchemy import func, desc, select
from sqlalchemy.orm import Session

from ..db.models import RoleSkillBaseline, TitleNorm, Organization, JobPost
from .salary_service import salary_service


class CareerPathwayNotFoundError(Exception):
    pass


# Static editorial content — certifications, learning resources, project ideas
# are not derivable from job market data; maintained as curated fallbacks.
_EDITORIAL: dict[str, dict] = {
    "data analyst": {
        "certifications": [
            "Google Data Analytics",
            "Microsoft Power BI Data Analyst",
            "SQL for Data Analysis",
        ],
        "learning_resources": [
            "Practice SQL daily on real datasets.",
            "Build dashboards from local market datasets.",
            "Publish portfolio writeups with insights and decisions.",
        ],
        "project_ideas": [
            "Customer churn dashboard for telecom data.",
            "E-commerce cohort retention analysis.",
            "County-level labor demand tracker.",
        ],
    },
    "software engineer": {
        "certifications": [
            "AWS Cloud Practitioner",
            "Meta Backend Developer",
            "Docker Essentials",
        ],
        "learning_resources": [
            "Ship one production-grade API with tests.",
            "Learn deployment and monitoring basics.",
            "Contribute to open-source projects.",
        ],
        "project_ideas": [
            "Job application tracker backend + frontend.",
            "Authentication service with role-based access.",
            "Search API with ranking and filtering.",
        ],
    },
    "data scientist": {
        "certifications": [
            "AWS Machine Learning Specialty",
            "Google Professional ML Engineer",
            "DeepLearning.AI Data Science",
        ],
        "learning_resources": [
            "Work through an end-to-end ML project with business framing.",
            "Publish model explainability writeups.",
            "Compete on a real dataset (Kaggle or local).",
        ],
        "project_ideas": [
            "Churn prediction model with documented business metrics.",
            "NLP classifier on local news or social data.",
            "Time-series demand forecasting for FMCG.",
        ],
    },
}


def _slug_to_family(role_slug: str) -> str:
    return (role_slug or "").strip().replace("-", " ").lower()


class CareerPathwaysService:
    def get_pathway(self, role_slug: str, db: Session) -> dict:
        family = _slug_to_family(role_slug)

        # Resolve canonical title from TitleNorm
        title_norm = db.execute(
            select(TitleNorm).where(func.lower(TitleNorm.family) == family)
        ).scalar_one_or_none()

        # T-DS-924: market-derived required skills from RoleSkillBaseline
        skill_rows = db.execute(
            select(RoleSkillBaseline.skill_name, RoleSkillBaseline.skill_share)
            .where(func.lower(RoleSkillBaseline.role_family) == family)
            .where(RoleSkillBaseline.low_confidence.is_(False))
            .order_by(desc(RoleSkillBaseline.skill_share))
            .limit(8)
        ).all()

        if not skill_rows and title_norm is None:
            raise CareerPathwayNotFoundError("Career pathway not found")

        required_skills = [row.skill_name for row in skill_rows]

        # T-DS-924: real employers actively hiring for this role (last 90 days)
        since = datetime.utcnow() - timedelta(days=90)
        employer_rows = db.execute(
            select(Organization.name, func.count(JobPost.id).label("cnt"))
            .join(JobPost, JobPost.org_id == Organization.id)
            .join(TitleNorm, JobPost.title_norm_id == TitleNorm.id)
            .where(func.lower(TitleNorm.family) == family)
            .where(JobPost.is_active.is_(True))
            .where(JobPost.first_seen >= since)
            .where(Organization.name.is_not(None))
            .group_by(Organization.name)
            .order_by(desc(func.count(JobPost.id)))
            .limit(5)
        ).all()
        employers_hiring = [row.name for row in employer_rows]

        canonical_title = (
            title_norm.canonical_title
            if title_norm
            else role_slug.replace("-", " ").title()
        )
        editorial = _EDITORIAL.get(family, {})

        salary_band = salary_service.estimate_salary_range(
            title=canonical_title,
            seniority="mid",
            location_text="Nairobi",
        )
        experience_ladder = [
            {
                "level": "Entry",
                "salary_range": salary_service.format_salary_range(
                    int(salary_band["min"] * 0.7),
                    int(salary_band["max"] * 0.75),
                    salary_band["currency"],
                ),
            },
            {
                "level": "Mid",
                "salary_range": salary_service.format_salary_range(
                    salary_band["min"],
                    salary_band["max"],
                    salary_band["currency"],
                ),
            },
            {
                "level": "Senior",
                "salary_range": salary_service.format_salary_range(
                    int(salary_band["min"] * 1.4),
                    int(salary_band["max"] * 1.5),
                    salary_band["currency"],
                ),
            },
        ]

        return {
            "role_slug": role_slug,
            "title": f"{canonical_title} in Kenya",
            "required_skills": required_skills,
            "certifications": editorial.get("certifications", []),
            "experience_ladder": experience_ladder,
            "employers_hiring": employers_hiring,
            "learning_resources": editorial.get("learning_resources", []),
            "project_ideas": editorial.get("project_ideas", []),
            "market_data": bool(skill_rows),
        }


career_pathways_service = CareerPathwaysService()

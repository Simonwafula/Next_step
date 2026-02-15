from dataclasses import dataclass

from .salary_service import salary_service


@dataclass(frozen=True)
class RoleSkillProfile:
    role: str
    core_skills: tuple[str, ...]
    recommended_projects: tuple[str, ...]


class SkillsGapService:
    def __init__(self) -> None:
        self._role_profiles = {
            "data scientist": RoleSkillProfile(
                role="Data Scientist",
                core_skills=(
                    "python",
                    "sql",
                    "machine learning",
                    "statistics",
                    "data visualization",
                ),
                recommended_projects=(
                    "Build a churn prediction model with clear business metrics.",
                    "Create an end-to-end analytics dashboard using SQL and Python.",
                    "Publish a portfolio case study explaining model decisions.",
                ),
            ),
            "data analyst": RoleSkillProfile(
                role="Data Analyst",
                core_skills=("excel", "sql", "python", "power bi", "reporting"),
                recommended_projects=(
                    "Design a KPI dashboard for a growth or operations team.",
                    "Analyze conversion funnel performance and propose optimizations.",
                    "Automate monthly reporting with Python and SQL.",
                ),
            ),
            "software engineer": RoleSkillProfile(
                role="Software Engineer",
                core_skills=(
                    "python",
                    "javascript",
                    "apis",
                    "testing",
                    "system design",
                ),
                recommended_projects=(
                    "Ship a production-ready API with tests and observability.",
                    "Build a full-stack app with authentication and role access.",
                    "Document architecture tradeoffs for a scalable feature.",
                ),
            ),
        }

    def scan_profile(
        self,
        profile_skills: dict,
        target_role: str,
        experience_level: str | None,
        preferred_location: str | None,
    ) -> dict:
        normalized_target = (target_role or "").strip().lower()
        role_profile = self._role_profiles.get(
            normalized_target,
            RoleSkillProfile(
                role=target_role.strip() if target_role else "General Role",
                core_skills=("communication", "problem solving", "excel"),
                recommended_projects=(
                    "Complete one role-relevant portfolio project.",
                    "Document measurable outcomes from recent work.",
                    "Collect feedback and iterate on your project.",
                ),
            ),
        )

        candidate_skills = {
            str(skill).strip().lower()
            for skill in (profile_skills or {}).keys()
            if str(skill).strip()
        }

        required_skills = list(role_profile.core_skills)
        matching_skills = [
            skill for skill in required_skills if skill in candidate_skills
        ]
        missing_skills = [
            skill for skill in required_skills if skill not in candidate_skills
        ]

        if required_skills:
            match_percentage = round(
                (len(matching_skills) / len(required_skills)) * 100
            )
        else:
            match_percentage = 0

        salary_estimate = salary_service.estimate_salary_range(
            title=role_profile.role,
            seniority=experience_level,
            location_text=preferred_location,
        )

        return {
            "target_role": role_profile.role,
            "match_percentage": max(0, min(match_percentage, 100)),
            "matching_skills": matching_skills,
            "missing_skills": missing_skills,
            "recommended_projects": list(role_profile.recommended_projects),
            "best_fit_roles": self._best_fit_roles(candidate_skills),
            "expected_pay_range": salary_service.format_salary_range(
                salary_estimate["min"],
                salary_estimate["max"],
                salary_estimate["currency"],
            ),
            "action_plan_30_60_90": {
                "30_days": "Close 1-2 missing core skills with focused learning and practice.",
                "60_days": "Ship at least one portfolio project demonstrating target-role capabilities.",
                "90_days": "Apply to roles with tailored CV and track interview outcomes weekly.",
            },
        }

    def _best_fit_roles(self, candidate_skills: set[str]) -> list[str]:
        role_scores: list[tuple[int, str]] = []
        for profile in self._role_profiles.values():
            score = len(set(profile.core_skills) & candidate_skills)
            role_scores.append((score, profile.role))

        role_scores.sort(key=lambda item: item[0], reverse=True)
        return [role for score, role in role_scores if score > 0][:3] or [
            "Operations Analyst",
            "Customer Success Associate",
        ]


skills_gap_service = SkillsGapService()

from sqlalchemy import func, desc, select
from sqlalchemy.orm import Session

from ..db.models import RoleSkillBaseline
from .salary_service import salary_service


# Fallback project suggestions when no DB data is available for a role
_FALLBACK_PROJECTS: tuple[str, ...] = (
    "Complete one role-relevant portfolio project.",
    "Document measurable outcomes from recent work.",
    "Collect feedback and iterate on your project.",
)


class SkillsGapService:
    def scan_profile(
        self,
        profile_skills: dict,
        target_role: str,
        experience_level: str | None,
        preferred_location: str | None,
        db: Session,
    ) -> dict:
        family = (target_role or "").strip().lower()

        # T-DS-924: market-derived core skills from RoleSkillBaseline
        skill_rows = db.execute(
            select(
                RoleSkillBaseline.skill_name,
                RoleSkillBaseline.updated_at,
                RoleSkillBaseline.count_total_jobs_used,
                RoleSkillBaseline.low_confidence,
            )
            .where(func.lower(RoleSkillBaseline.role_family) == family)
            .where(RoleSkillBaseline.low_confidence.is_(False))
            .order_by(desc(RoleSkillBaseline.skill_share))
            .limit(8)
        ).all()
        required_skills = [row.skill_name for row in skill_rows]

        # T-DS-934: intelligence provenance — surface baseline freshness + sample size
        baseline_updated_at = (
            max(row.updated_at for row in skill_rows if row.updated_at).isoformat()
            if skill_rows
            else None
        )
        baseline_sample_size = (
            max(
                row.count_total_jobs_used
                for row in skill_rows
                if row.count_total_jobs_used
            )
            if skill_rows
            else 0
        )
        intelligence_provenance = {
            "baseline_updated_at": baseline_updated_at,
            "sample_size": baseline_sample_size,
            "confidence_note": "market-derived"
            if skill_rows
            else "no baseline — generic guidance only",
        }

        candidate_skills = {
            str(skill).strip().lower()
            for skill in (profile_skills or {}).keys()
            if str(skill).strip()
        }

        if required_skills:
            matching_skills = [
                s for s in required_skills if s.lower() in candidate_skills
            ]
            missing_skills = [
                s for s in required_skills if s.lower() not in candidate_skills
            ]
            match_percentage = round(
                (len(matching_skills) / len(required_skills)) * 100
            )
        else:
            matching_skills = []
            missing_skills = []
            match_percentage = 0

        salary_estimate = salary_service.estimate_salary_range(
            title=target_role,
            seniority=experience_level,
            location_text=preferred_location,
        )

        return {
            "target_role": target_role.strip().title()
            if target_role
            else "General Role",
            "match_percentage": max(0, min(match_percentage, 100)),
            "matching_skills": matching_skills,
            "missing_skills": missing_skills,
            "recommended_projects": list(_FALLBACK_PROJECTS),
            "best_fit_roles": self._best_fit_roles(candidate_skills, db),
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
            # T-DS-934: intelligence provenance for user-facing transparency
            "intelligence_provenance": intelligence_provenance,
        }

    def _best_fit_roles(self, candidate_skills: set[str], db: Session) -> list[str]:
        if not candidate_skills:
            return []

        # T-DS-924: find role families where the most candidate skills appear in market baselines
        rows = db.execute(
            select(
                RoleSkillBaseline.role_family,
                func.count(RoleSkillBaseline.skill_name).label("matches"),
            )
            .where(func.lower(RoleSkillBaseline.skill_name).in_(candidate_skills))
            .where(RoleSkillBaseline.low_confidence.is_(False))
            .group_by(RoleSkillBaseline.role_family)
            .order_by(desc(func.count(RoleSkillBaseline.skill_name)))
            .limit(3)
        ).all()

        return [row.role_family.title() for row in rows if row.matches > 0]


skills_gap_service = SkillsGapService()

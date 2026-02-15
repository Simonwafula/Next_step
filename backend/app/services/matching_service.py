from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.models import JobPost, Location, User
from .ai_service import ai_service


class JobNotFoundError(Exception):
    pass


class ProfileNotCompleteError(Exception):
    pass


class MatchingService:
    def get_job_match(self, db: Session, user: User, job_id: int) -> dict[str, Any]:
        profile = user.profile
        if not profile:
            raise ProfileNotCompleteError("Please complete your profile first")

        result = db.execute(
            select(JobPost, Location)
            .outerjoin(Location, Location.id == JobPost.location_id)
            .where(JobPost.id == job_id)
        ).first()

        if not result:
            raise JobNotFoundError("Job not found")

        job_post, location = result
        location_text = self._build_location_text(location)
        scores = ai_service.calculate_job_match_score(
            profile,
            job_post,
            job_location_text=location_text,
        )

        overall_score = max(scores.get("overall_score", 0.0), 0.0)

        return {
            "job_id": job_post.id,
            "title": job_post.title_raw,
            "match_percentage": round(overall_score * 100),
            "overall_score": round(overall_score, 4),
            "skill_match": round(scores.get("skill_match", 0.0), 4),
            "location_match": round(scores.get("location_match", 0.0), 4),
            "experience_match": round(scores.get("experience_match", 0.0), 4),
            "salary_match": round(scores.get("salary_match", 0.0), 4),
            "matching_skills": scores.get("matching_skills", []),
            "missing_skills": scores.get("missing_skills", []),
            "explanation": scores.get("explanation", ""),
        }

    @staticmethod
    def _build_location_text(location: Location | None) -> str:
        if not location:
            return ""

        parts = [
            location.raw,
            location.city,
            location.region,
            location.country,
        ]
        return " ".join(str(part) for part in parts if part)


matching_service = MatchingService()

"""T-DS-962: Candidate-facing rejection feedback generator.

Given an ApplicationFunnelEvent with stage="rejected", generates a
human-readable feedback bundle including:
  - A personalised explanation message
  - Actionable improvement suggestions keyed to the rejection reason
  - Skills to develop (derived from the job's RoleSkillBaseline data)

The output is deterministic and template-driven — no LLM dependency.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.models import (
    ApplicationFunnelEvent,
    JobApplication,
    JobPost,
    REJECTION_REASONS,
    RoleSkillBaseline,
    TitleNorm,
    UserProfile,
)

# ---------------------------------------------------------------------------
# Feedback templates keyed by REJECTION_REASONS
# ---------------------------------------------------------------------------

_REASON_MESSAGES: dict[str, str] = {
    "skills_mismatch": (
        "The employer noted that your current skill set did not closely match "
        "the requirements for this role."
    ),
    "experience_insufficient": (
        "The employer was looking for more experience than your profile currently shows."
    ),
    "education_mismatch": (
        "The employer's education requirements were different from your listed qualifications."
    ),
    "location_mismatch": (
        "The role requires a location commitment that did not align with your profile."
    ),
    "salary_mismatch": (
        "The employer's budget and your salary expectations were not aligned for this position."
    ),
    "role_filled": (
        "The employer filled this position before reviewing all applications. "
        "Your profile was not the deciding factor."
    ),
    "over_qualified": (
        "The employer felt your experience level exceeded the scope of this role."
    ),
    "culture_fit": (
        "The employer indicated a preference for a different working style or background "
        "for this team."
    ),
    "no_response": (
        "The employer did not provide a specific reason. "
        "This sometimes happens when a role is filled quickly."
    ),
    "other": (
        "The employer did not specify a reason beyond this application not being "
        "the best match at this time."
    ),
}

_REASON_SUGGESTIONS: dict[str, list[str]] = {
    "skills_mismatch": [
        "Take a skill assessment to verify and showcase your proficiency.",
        "Review the job description and build evidence for the specific skills listed.",
        "Consider adding portfolio items or projects that demonstrate these skills.",
    ],
    "experience_insufficient": [
        "Apply to similar roles at a slightly lower seniority to build your track record.",
        "Take on freelance or contract work to add recent experience to your profile.",
        "Document informal or gig work as evidence items in your profile.",
    ],
    "education_mismatch": [
        "Consider adding any relevant certifications or short courses to your profile.",
        "Highlight practical work experience that demonstrates equivalent knowledge.",
        "Look for roles that value experience over formal qualifications.",
    ],
    "location_mismatch": [
        "Enable remote-work preferences in your profile if applicable.",
        "Search for roles explicitly tagged as remote or hybrid.",
    ],
    "salary_mismatch": [
        "Review the market salary data for this role in your location.",
        "Consider roles where the salary band is explicitly listed.",
    ],
    "role_filled": [
        "Set up a job alert for similar roles so you apply earlier next time.",
        "Check if the employer has other open positions.",
    ],
    "over_qualified": [
        "Tailor your application to highlight enthusiasm for the specific scope of the role.",
        "Consider applying to more senior positions that match your full experience.",
    ],
    "culture_fit": [
        "Research company culture before applying to find a closer match.",
        "Highlight collaboration and communication skills in your profile.",
    ],
    "no_response": [
        "Keep your profile up to date and apply to similar roles.",
        "Set up job alerts to stay ahead of new openings.",
    ],
    "other": [
        "Review your profile completeness and ensure all sections are filled in.",
        "Consider taking a skill assessment to add verified evidence to your profile.",
    ],
}


# ---------------------------------------------------------------------------
# Main generator
# ---------------------------------------------------------------------------


def generate_rejection_feedback(
    application_id: int,
    db: Session,
) -> dict:
    """Generate a candidate-facing feedback bundle for a rejected application.

    Returns:
        {
            "application_id": int,
            "job_post_id": int,
            "stage": str,                   # always "rejected"
            "reason": str | None,
            "message": str,                 # human-readable explanation
            "suggestions": list[str],       # actionable improvements
            "skills_to_develop": list[str], # from RoleSkillBaseline for this role
            "found": bool,                  # False if no rejection event exists
        }
    """
    # Load the most recent rejection event for this application
    event = db.execute(
        select(ApplicationFunnelEvent)
        .where(
            ApplicationFunnelEvent.application_id == application_id,
            ApplicationFunnelEvent.stage == "rejected",
        )
        .order_by(ApplicationFunnelEvent.event_at.desc())
        .limit(1)
    ).scalar_one_or_none()

    if not event:
        return {
            "application_id": application_id,
            "found": False,
            "message": "No rejection record found for this application.",
            "suggestions": [],
            "skills_to_develop": [],
        }

    reason = event.reason if event.reason in REJECTION_REASONS else "other"
    message = _REASON_MESSAGES.get(reason, _REASON_MESSAGES["other"])
    # Append employer's free-text detail if available
    if event.details:
        message = f"{message} Employer note: {event.details}"

    suggestions = _REASON_SUGGESTIONS.get(reason, _REASON_SUGGESTIONS["other"])

    # Resolve role family from the job
    skills_to_develop: list[str] = []
    job = db.execute(
        select(JobPost).where(JobPost.id == event.job_post_id)
    ).scalar_one_or_none()
    role_family: str | None = None
    if job and job.title_norm_id:
        tn = db.execute(
            select(TitleNorm).where(TitleNorm.id == job.title_norm_id)
        ).scalar_one_or_none()
        if tn:
            role_family = tn.family

    if role_family and reason == "skills_mismatch":
        # Load candidate's known skills for gap computation
        app_obj = db.execute(
            select(JobApplication).where(JobApplication.id == application_id)
        ).scalar_one_or_none()
        candidate_skills: set[str] = set()
        if app_obj:
            profile = db.execute(
                select(UserProfile).where(UserProfile.user_id == app_obj.user_id)
            ).scalar_one_or_none()
            if profile:
                raw = profile.skills or {}
                if isinstance(raw, dict):
                    candidate_skills = {k.lower() for k in raw if k != "skills"}
                    embedded = raw.get("skills", [])
                    if isinstance(embedded, list):
                        candidate_skills |= {str(s).lower() for s in embedded}
                elif isinstance(raw, list):
                    candidate_skills = {str(s).lower() for s in raw}

        # Top missing skills for this role family
        baseline_rows = (
            db.execute(
                select(RoleSkillBaseline)
                .where(RoleSkillBaseline.role_family == role_family)
                .order_by(RoleSkillBaseline.skill_share.desc())
                .limit(15)
            )
            .scalars()
            .all()
        )
        skills_to_develop = [
            r.skill_name
            for r in baseline_rows
            if r.skill_name.lower() not in candidate_skills
        ][:5]

    return {
        "application_id": application_id,
        "job_post_id": event.job_post_id,
        "found": True,
        "stage": "rejected",
        "reason": reason,
        "role_family": role_family,
        "message": message,
        "suggestions": suggestions,
        "skills_to_develop": skills_to_develop,
    }

"""T-DS-952: Candidate-to-job scoring service.

Scores a candidate against a job posting using three evidence layers:
  1. verified_skill_score  — from completed AssessmentSessions / SkillAssessments
  2. evidence_score        — from CandidateEvidence skills overlap
  3. profile_score         — from UserProfile.skills overlap (self-reported)

Returns a score dict with an explanation bundle suitable for employer display.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.models import (
    AssessmentSession,
    CandidateEvidence,
    JobEntities,
    JobPost,
    RoleDemandSnapshot,
    RoleSkillBaseline,
    MetricsDaily,
    SkillAssessment,
    TitleNorm,
    UserProfile,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _job_required_skills(job_post_id: int, db: Session) -> set[str]:
    """Return the set of skill names required by a job (from JobEntities)."""
    row = db.execute(
        select(JobEntities).where(JobEntities.job_id == job_post_id)
    ).scalar_one_or_none()
    if not row:
        return set()
    skills: list = row.skills or []
    # skills is stored as list of strings or dicts with a "name" key
    result: set[str] = set()
    for s in skills:
        if isinstance(s, str):
            result.add(s.lower())
        elif isinstance(s, dict) and "name" in s:
            result.add(str(s["name"]).lower())
    return result


def _verified_skills(
    user_id: int, role_family: str | None, db: Session
) -> dict[str, float]:
    """Return {skill_name: best_score} from completed assessment sessions and SkillAssessments."""
    skill_scores: dict[str, float] = {}

    # From AssessmentSession (role-family level, T-DS-942)
    sessions = (
        db.execute(
            select(AssessmentSession).where(
                AssessmentSession.user_id == user_id,
                AssessmentSession.status == "completed",
            )
        )
        .scalars()
        .all()
    )
    for session in sessions:
        if session.score is not None and session.role_family:
            # Credit the role_family as a "skill" proxy at the session score
            key = f"role:{session.role_family.lower()}"
            existing = skill_scores.get(key, 0.0)
            skill_scores[key] = max(existing, float(session.score))

    # From SkillAssessment (per-skill, T-DS-942 predecessor)
    assessments = (
        db.execute(select(SkillAssessment).where(SkillAssessment.user_id == user_id))
        .scalars()
        .all()
    )
    for sa in assessments:
        key = f"skill:{sa.skill_id}"
        existing = skill_scores.get(key, 0.0)
        skill_scores[key] = max(existing, float(sa.score))

    return skill_scores


def _evidence_skills(user_id: int, db: Session) -> set[str]:
    """Return skill names from CandidateEvidence items."""
    rows = (
        db.execute(
            select(CandidateEvidence).where(CandidateEvidence.user_id == user_id)
        )
        .scalars()
        .all()
    )
    skills: set[str] = set()
    for row in rows:
        for s in row.skills_demonstrated or []:
            if isinstance(s, str):
                skills.add(s.lower())
    return skills


def _profile_skills(user_id: int, db: Session) -> set[str]:
    """Return skill names from UserProfile.skills (self-reported)."""
    profile = db.execute(
        select(UserProfile).where(UserProfile.user_id == user_id)
    ).scalar_one_or_none()
    if not profile:
        return set()
    raw = profile.skills or {}
    if isinstance(raw, dict):
        # Common formats: {"Python": 3, ...} or {"skills": ["Python", ...]}
        keys = set(k.lower() for k in raw.keys() if k != "skills")
        embedded = raw.get("skills", [])
        if isinstance(embedded, list):
            keys |= {str(s).lower() for s in embedded}
        return keys
    if isinstance(raw, list):
        return {str(s).lower() for s in raw}
    return set()


# ---------------------------------------------------------------------------
# Main scorer
# ---------------------------------------------------------------------------


def score_candidate_for_job(
    user_id: int,
    job_post_id: int,
    db: Session,
) -> dict:
    """Score a candidate against a job post.

    Returns:
        {
            "user_id": int,
            "job_post_id": int,
            "overall_score": float,        # weighted composite [0, 1]
            "score_breakdown": {
                "verified_skill_score": float,
                "evidence_score": float,
                "profile_score": float,
            },
            "explanation": {
                "matched_skills": list[str],
                "missing_skills": list[str],
                "verified_role_families": list[str],
                "evidence_items": int,
                "notes": list[str],
            },
        }
    """
    # Resolve role family from job
    job = db.execute(
        select(JobPost).where(JobPost.id == job_post_id)
    ).scalar_one_or_none()
    role_family: str | None = None
    if job and job.title_norm_id:
        tn = db.execute(
            select(TitleNorm).where(TitleNorm.id == job.title_norm_id)
        ).scalar_one_or_none()
        if tn:
            role_family = tn.family

    required_skills = _job_required_skills(job_post_id, db)
    verified = _verified_skills(user_id, role_family, db)
    evidence = _evidence_skills(user_id, db)
    profile = _profile_skills(user_id, db)

    # --- verified_skill_score ---
    # If there's a matching role-family session, give significant credit
    verified_role_keys = {k for k in verified if k.startswith("role:")}
    role_hit = 0.0
    if role_family:
        key = f"role:{role_family.lower()}"
        if key in verified:
            role_hit = verified[key]  # score is 0–1 from the assessment
    verified_skill_score = min(1.0, role_hit)

    # --- evidence_score ---
    evidence_score = _jaccard(evidence, required_skills) if required_skills else 0.0

    # --- profile_score ---
    profile_score = _jaccard(profile, required_skills) if required_skills else 0.0

    # Weights: verified > evidence > self-reported
    overall = 0.55 * verified_skill_score + 0.30 * evidence_score + 0.15 * profile_score

    # Explanation bundle
    all_candidate_skills = evidence | profile
    matched = sorted(all_candidate_skills & required_skills)
    missing = sorted(required_skills - all_candidate_skills)
    verified_families = [k.replace("role:", "") for k in verified_role_keys]

    notes: list[str] = []
    if not required_skills:
        notes.append("No skill data extracted for this job posting.")
    if verified_skill_score > 0:
        notes.append(
            f"Candidate has a verified assessment for {role_family or 'this role'} "
            f"(score={verified_skill_score:.2f})."
        )
    if not verified_families:
        notes.append("No completed skill assessments found for this candidate.")

    # Count evidence items
    evidence_count = (
        db.execute(
            select(CandidateEvidence).where(CandidateEvidence.user_id == user_id)
        )
        .scalars()
        .all()
    )

    return {
        "user_id": user_id,
        "job_post_id": job_post_id,
        "overall_score": round(overall, 4),
        "score_breakdown": {
            "verified_skill_score": round(verified_skill_score, 4),
            "evidence_score": round(evidence_score, 4),
            "profile_score": round(profile_score, 4),
        },
        "explanation": {
            "matched_skills": matched,
            "missing_skills": missing,
            "verified_role_families": verified_families,
            "evidence_items": len(evidence_count),
            "notes": notes,
        },
    }


# ---------------------------------------------------------------------------
# T-DS-954: Intelligence sidecar builder
# ---------------------------------------------------------------------------


def build_intelligence_sidecar(role_family: str | None, db: Session) -> dict:
    """Return LMI intelligence attached to a shortlist (T-DS-954).

    Pulls required_skills, demand, salary, and confidence from the
    RoleSkillBaseline, RoleDemandSnapshot, and MetricsDaily tables.
    """
    if not role_family:
        return {
            "role_family": None,
            "confidence": "low",
            "note": "No role family resolved.",
        }

    # Required skills (top 10 by share)
    baseline_rows = (
        db.execute(
            select(RoleSkillBaseline)
            .where(RoleSkillBaseline.role_family == role_family)
            .order_by(RoleSkillBaseline.skill_share.desc())
            .limit(10)
        )
        .scalars()
        .all()
    )
    required_skills = [
        {
            "skill": r.skill_name,
            "share": round(r.skill_share, 3),
            "low_confidence": r.low_confidence,
        }
        for r in baseline_rows
    ]

    # Demand
    demand_row = db.execute(
        select(RoleDemandSnapshot)
        .where(RoleDemandSnapshot.role_family == role_family)
        .order_by(RoleDemandSnapshot.updated_at.desc())
        .limit(1)
    ).scalar_one_or_none()
    demand = {
        "count": demand_row.demand_count if demand_row else None,
        "low_confidence": demand_row.low_confidence if demand_row else True,
    }

    # Salary (latest MetricsDaily p50 for this role family)
    salary_row = db.execute(
        select(MetricsDaily)
        .where(MetricsDaily.role_family == role_family)
        .order_by(MetricsDaily.date.desc())
        .limit(1)
    ).scalar_one_or_none()
    salary = {
        "p50": salary_row.salary_p50 if salary_row else None,
        "currency": "KES",
    }

    # Overall confidence
    any_low = (
        any(r["low_confidence"] for r in required_skills) or demand["low_confidence"]
    )
    confidence = "low" if any_low else "medium" if required_skills else "low"
    if required_skills and not any_low:
        confidence = "high"

    return {
        "role_family": role_family,
        "required_skills": required_skills,
        "demand": demand,
        "salary": salary,
        "confidence": confidence,
    }

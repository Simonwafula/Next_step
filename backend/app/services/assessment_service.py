"""Skill verification assessment service (T-DS-941/942/943/944/945).

Covers:
- Question bank seeding from RoleSkillBaseline (T-DS-941)
- Assessment delivery: start, answer, complete (T-DS-942)
- Percentile calibration + versioning (T-DS-943)
- Employer-visible verification summaries (T-DS-944)
- Requirement-extraction QA for launch families (T-DS-945)
"""

from datetime import datetime, timezone
from sqlalchemy import func, desc, select
from sqlalchemy.orm import Session

from ..db.models import (
    AssessmentQuestion,
    AssessmentSession,
    AssessmentSessionAnswer,
    RoleSkillBaseline,
    SkillAssessment,
    Skill,
    CandidateEvidence,
    VerificationProvenance,
)

_QUESTION_BANK_VERSION = "v1"
_SESSION_QUESTION_COUNT = 10  # questions per session
_MIN_QUESTIONS_PER_SKILL = 2


# ---------------------------------------------------------------------------
# T-DS-941: Question bank seeder
# ---------------------------------------------------------------------------


def _build_questions_for_skill(
    skill_name: str, role_family: str, skill_share: float
) -> list[dict]:
    """Generate market-grounded MCQ questions for one skill in a role family."""
    pct = int(skill_share * 100)
    role_title = role_family.title()
    questions = []

    # Q1 — awareness: what does this skill enable in this role?
    questions.append(
        {
            "question_text": (
                f"In a {role_title} role, what does proficiency in {skill_name} "
                f"most directly enable?"
            ),
            "options": [
                f"Performing {skill_name}-related tasks efficiently and accurately",
                "Managing executive diary and boardroom scheduling",
                "Overseeing procurement and vendor contract negotiations",
                "Administering building facilities and office logistics",
            ],
            "correct_index": 0,
            "difficulty": 1,
        }
    )

    # Q2 — market signal: how common is this skill in job postings?
    if skill_share >= 0.5:
        freq = "very commonly — the majority"
    elif skill_share >= 0.25:
        freq = "commonly — roughly a quarter or more"
    else:
        freq = "regularly — a notable portion"

    questions.append(
        {
            "question_text": (
                f"How frequently does {skill_name} appear in {role_title} job "
                f"postings in the Kenyan market?"
            ),
            "options": [
                f"It appears {freq} of relevant listings (~{pct}%+)",
                "Rarely — fewer than 5% of job listings mention it",
                "Only in C-suite or executive-level listings",
                "It is not typically associated with this role family",
            ],
            "correct_index": 0,
            "difficulty": 2,
        }
    )

    return questions


def seed_question_bank(role_family: str, db: Session) -> int:
    """Seed the question bank for a role family from RoleSkillBaseline.

    Idempotent: skips questions that already exist for this role + skill + version.
    Returns count of newly created questions.
    """
    family = (role_family or "").strip().lower()

    baseline_rows = db.execute(
        select(RoleSkillBaseline.skill_name, RoleSkillBaseline.skill_share)
        .where(func.lower(RoleSkillBaseline.role_family) == family)
        .where(RoleSkillBaseline.low_confidence.is_(False))
        .order_by(desc(RoleSkillBaseline.skill_share))
        .limit(8)
    ).all()

    if not baseline_rows:
        return 0

    created = 0
    for row in baseline_rows:
        existing_count = db.execute(
            select(func.count(AssessmentQuestion.id)).where(
                func.lower(AssessmentQuestion.role_family) == family,
                func.lower(AssessmentQuestion.skill_name) == row.skill_name.lower(),
                AssessmentQuestion.question_bank_version == _QUESTION_BANK_VERSION,
            )
        ).scalar_one()

        if existing_count >= _MIN_QUESTIONS_PER_SKILL:
            continue

        for q in _build_questions_for_skill(row.skill_name, family, row.skill_share):
            db.add(
                AssessmentQuestion(
                    skill_name=row.skill_name,
                    role_family=family,
                    question_text=q["question_text"],
                    options=q["options"],
                    correct_index=q["correct_index"],
                    difficulty=q["difficulty"],
                    question_bank_version=_QUESTION_BANK_VERSION,
                )
            )
            created += 1

    db.commit()
    return created


# ---------------------------------------------------------------------------
# T-DS-942: Assessment delivery
# ---------------------------------------------------------------------------


def start_assessment(user_id: int, role_family: str, db: Session) -> dict:
    """Start a new assessment session for a user and role family.

    Auto-seeds the question bank if empty. Raises ValueError if no questions exist.
    """
    family = (role_family or "").strip().lower()

    # Auto-seed if needed
    q_count = db.execute(
        select(func.count(AssessmentQuestion.id)).where(
            func.lower(AssessmentQuestion.role_family) == family,
            AssessmentQuestion.question_bank_version == _QUESTION_BANK_VERSION,
        )
    ).scalar_one()

    if q_count == 0:
        seed_question_bank(family, db)
        q_count = db.execute(
            select(func.count(AssessmentQuestion.id)).where(
                func.lower(AssessmentQuestion.role_family) == family,
                AssessmentQuestion.question_bank_version == _QUESTION_BANK_VERSION,
            )
        ).scalar_one()

    if q_count == 0:
        raise ValueError(
            f"No question bank available for role family '{role_family}'. "
            "Ensure RoleSkillBaseline data exists for this family."
        )

    # Select questions: mix difficulties, cap at SESSION_QUESTION_COUNT
    questions = (
        db.execute(
            select(AssessmentQuestion)
            .where(func.lower(AssessmentQuestion.role_family) == family)
            .where(AssessmentQuestion.question_bank_version == _QUESTION_BANK_VERSION)
            .order_by(AssessmentQuestion.difficulty, AssessmentQuestion.id)
            .limit(_SESSION_QUESTION_COUNT)
        )
        .scalars()
        .all()
    )

    session = AssessmentSession(
        user_id=user_id,
        role_family=family,
        status="in_progress",
        question_ids=[q.id for q in questions],
        question_bank_version=_QUESTION_BANK_VERSION,
        questions_total=len(questions),
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    return {
        "session_id": session.id,
        "role_family": family,
        "question_count": len(questions),
        "question_bank_version": _QUESTION_BANK_VERSION,
        "questions": [
            {
                "id": q.id,
                "question_text": q.question_text,
                "options": q.options,
                "difficulty": q.difficulty,
            }
            for q in questions
        ],
    }


def submit_answer(
    session_id: int, question_id: int, selected_index: int, db: Session
) -> dict:
    """Record one answer for a question in an active session."""
    session = db.get(AssessmentSession, session_id)
    if not session:
        raise ValueError("Session not found")
    if session.status != "in_progress":
        raise ValueError("Session is not in progress")
    if question_id not in session.question_ids:
        raise ValueError("Question does not belong to this session")

    question = db.get(AssessmentQuestion, question_id)
    if not question:
        raise ValueError("Question not found")

    is_correct = selected_index == question.correct_index

    # Upsert: replace existing answer for this question if re-submitted
    existing = db.execute(
        select(AssessmentSessionAnswer).where(
            AssessmentSessionAnswer.session_id == session_id,
            AssessmentSessionAnswer.question_id == question_id,
        )
    ).scalar_one_or_none()

    if existing:
        existing.selected_index = selected_index
        existing.is_correct = is_correct
        existing.answered_at = datetime.now(timezone.utc)
    else:
        db.add(
            AssessmentSessionAnswer(
                session_id=session_id,
                question_id=question_id,
                selected_index=selected_index,
                is_correct=is_correct,
            )
        )

    db.commit()
    return {"question_id": question_id, "is_correct": is_correct}


def complete_assessment(session_id: int, user_id: int, db: Session) -> dict:
    """Finalise assessment: score, level, percentile, SkillAssessment records.

    T-DS-943: computes percentile against all completed sessions for same role_family.
    """
    session = db.get(AssessmentSession, session_id)
    if not session:
        raise ValueError("Session not found")
    if session.user_id != user_id:
        raise ValueError("Session does not belong to this user")
    if session.status == "completed":
        raise ValueError("Session already completed")

    answers = (
        db.execute(
            select(AssessmentSessionAnswer).where(
                AssessmentSessionAnswer.session_id == session_id
            )
        )
        .scalars()
        .all()
    )

    questions_answered = len(answers)
    questions_correct = sum(1 for a in answers if a.is_correct)
    score = (
        (questions_correct / session.questions_total)
        if session.questions_total
        else 0.0
    )

    # Level thresholds
    if score >= 0.7:
        level = "advanced"
        is_certified = True
    elif score >= 0.4:
        level = "intermediate"
        is_certified = False
    else:
        level = "beginner"
        is_certified = False

    # T-DS-943: percentile against completed sessions for same role_family
    past_scores = (
        db.execute(
            select(AssessmentSession.score)
            .where(AssessmentSession.role_family == session.role_family)
            .where(AssessmentSession.status == "completed")
            .where(AssessmentSession.score.is_not(None))
        )
        .scalars()
        .all()
    )

    if past_scores:
        below = sum(1 for s in past_scores if s < score)
        percentile = round((below / len(past_scores)) * 100, 1)
    else:
        percentile = 50.0  # first completion — assume median

    now = datetime.now(timezone.utc)
    session.status = "completed"
    session.score = score
    session.questions_correct = questions_correct
    session.percentile = percentile
    session.level = level
    session.completed_at = now

    # Create / update SkillAssessment records for each skill covered
    skill_names = (
        db.execute(
            select(AssessmentQuestion.skill_name)
            .where(AssessmentQuestion.id.in_(session.question_ids))
            .distinct()
        )
        .scalars()
        .all()
    )

    for skill_name in skill_names:
        skill = db.execute(
            select(Skill).where(func.lower(Skill.name) == skill_name.lower())
        ).scalar_one_or_none()
        if not skill:
            continue

        db.add(
            SkillAssessment(
                user_id=user_id,
                skill_id=skill.id,
                score=score,
                level=level,
                percentile=percentile,
                assessment_type="role_family_mcq",
                questions_total=session.questions_total,
                questions_correct=questions_correct,
                is_certified=is_certified,
            )
        )

    db.commit()

    return {
        "session_id": session_id,
        "role_family": session.role_family,
        "score": round(score, 3),
        "level": level,
        "percentile": percentile,
        "questions_answered": questions_answered,
        "questions_total": session.questions_total,
        "questions_correct": questions_correct,
        "is_certified": is_certified,
        "completed_at": now.isoformat(),
    }


# ---------------------------------------------------------------------------
# T-DS-944: Employer-visible verification summary
# ---------------------------------------------------------------------------


def get_verification_summary(user_id: int, db: Session) -> dict:
    """Return a verification bundle suitable for employer review.

    Aggregates: completed assessments (with level/percentile/certification),
    evidence item counts by type, and provenance confidence.
    """
    # Latest completed assessment per role_family
    completed_sessions = (
        db.execute(
            select(AssessmentSession)
            .where(AssessmentSession.user_id == user_id)
            .where(AssessmentSession.status == "completed")
            .order_by(AssessmentSession.completed_at.desc())
        )
        .scalars()
        .all()
    )

    seen_families: set[str] = set()
    assessments = []
    for s in completed_sessions:
        if s.role_family in seen_families:
            continue
        seen_families.add(s.role_family)
        assessments.append(
            {
                "role_family": s.role_family,
                "level": s.level,
                "score": round(s.score, 3) if s.score is not None else None,
                "percentile": s.percentile,
                "is_certified": s.level == "advanced",
                "completed_at": s.completed_at.isoformat() if s.completed_at else None,
                "question_bank_version": s.question_bank_version,
            }
        )

    # Evidence summary by type
    evidence_rows = db.execute(
        select(CandidateEvidence.evidence_type, func.count(CandidateEvidence.id))
        .where(CandidateEvidence.user_id == user_id)
        .group_by(CandidateEvidence.evidence_type)
    ).all()
    evidence_summary = {etype: cnt for etype, cnt in evidence_rows}

    # Highest provenance confidence across all evidence
    top_confidence = db.execute(
        select(func.max(VerificationProvenance.confidence))
        .join(
            CandidateEvidence,
            VerificationProvenance.evidence_id == CandidateEvidence.id,
        )
        .where(CandidateEvidence.user_id == user_id)
    ).scalar_one_or_none()

    return {
        "user_id": user_id,
        "assessments": assessments,
        "evidence_summary": evidence_summary,
        "total_evidence_items": sum(evidence_summary.values()),
        "top_provenance_confidence": top_confidence,
        "has_certified_skills": any(a["is_certified"] for a in assessments),
    }


# ---------------------------------------------------------------------------
# T-DS-945: Requirement-extraction QA for launch families
# ---------------------------------------------------------------------------

_MIN_SAMPLE_SIZE = 20
_MIN_QUESTIONS_FOR_LAUNCH = 4


def get_verification_qa(role_family: str, db: Session) -> dict:
    """Check whether a role family is ready for assessment launch.

    Validates: baseline data exists + meets sample size + question bank seeded.
    """
    family = (role_family or "").strip().lower()

    # Baseline check
    baseline_rows = db.execute(
        select(
            RoleSkillBaseline.skill_name,
            RoleSkillBaseline.skill_share,
            RoleSkillBaseline.count_total_jobs_used,
            RoleSkillBaseline.low_confidence,
        )
        .where(func.lower(RoleSkillBaseline.role_family) == family)
        .order_by(desc(RoleSkillBaseline.skill_share))
    ).all()

    skills_in_baseline = len(baseline_rows)
    high_confidence_skills = [r for r in baseline_rows if not r.low_confidence]
    min_sample = min((r.count_total_jobs_used for r in baseline_rows), default=0)
    baseline_ready = len(high_confidence_skills) >= 3 and min_sample >= _MIN_SAMPLE_SIZE

    # Question bank check
    question_count = db.execute(
        select(func.count(AssessmentQuestion.id)).where(
            func.lower(AssessmentQuestion.role_family) == family,
            AssessmentQuestion.question_bank_version == _QUESTION_BANK_VERSION,
        )
    ).scalar_one()

    questions_ready = question_count >= _MIN_QUESTIONS_FOR_LAUNCH

    ready_for_launch = baseline_ready and questions_ready

    return {
        "role_family": family,
        "ready_for_launch": ready_for_launch,
        "baseline": {
            "skills_total": skills_in_baseline,
            "high_confidence_skills": len(high_confidence_skills),
            "min_sample_size": min_sample,
            "baseline_ready": baseline_ready,
        },
        "question_bank": {
            "question_count": question_count,
            "version": _QUESTION_BANK_VERSION,
            "questions_ready": questions_ready,
            "min_required": _MIN_QUESTIONS_FOR_LAUNCH,
        },
        "issues": _qa_issues(
            baseline_ready, questions_ready, min_sample, question_count
        ),
    }


def _qa_issues(
    baseline_ready: bool,
    questions_ready: bool,
    min_sample: int,
    question_count: int,
) -> list[str]:
    issues = []
    if not baseline_ready:
        if min_sample < _MIN_SAMPLE_SIZE:
            issues.append(
                f"Insufficient job sample size ({min_sample} < {_MIN_SAMPLE_SIZE} required)"
            )
        else:
            issues.append("Fewer than 3 high-confidence skills in baseline")
    if not questions_ready:
        issues.append(
            f"Question bank too small ({question_count} < {_MIN_QUESTIONS_FOR_LAUNCH} required)"
        )
    return issues

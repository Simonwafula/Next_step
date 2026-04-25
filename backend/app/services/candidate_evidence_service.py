"""Candidate evidence ingestion and querying service (T-DS-932).

Handles:
- Manual evidence submission (self_reported)
- CV data extraction from UserProfile.cv_data JSONB (cv_extracted)
- Evidence listing and provenance attachment
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.models import CandidateEvidence, VerificationProvenance, UserProfile

# Extraction pipeline version — bump when the extraction logic changes
_CV_EXTRACTION_VERSION = "cv-extract-v1"

# Recognised cv_data section keys → evidence_type mapping
_CV_SECTION_MAP = {
    "work_experience": "informal_work",
    "experience": "informal_work",
    "projects": "project",
    "portfolio": "portfolio_item",
    "certifications": "certification",
    "certificates": "certification",
    "gig_work": "gig",
    "freelance": "gig",
    "work_samples": "work_sample",
}


def add_evidence(
    user_id: int,
    evidence_type: str,
    title: str,
    db: Session,
    description: str | None = None,
    url: str | None = None,
    skills_demonstrated: list[str] | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    source: str = "self_reported",
    provenance_confidence: float = 0.5,
) -> CandidateEvidence:
    """Add a single evidence item and attach a provenance record."""
    item = CandidateEvidence(
        user_id=user_id,
        evidence_type=evidence_type,
        title=title,
        description=description,
        url=url,
        skills_demonstrated=skills_demonstrated or [],
        start_date=start_date,
        end_date=end_date,
        source=source,
    )
    db.add(item)
    db.flush()  # populate item.id

    prov = VerificationProvenance(
        evidence_id=item.id,
        evidence_source=source,
        assessment_version=None,
        confidence=provenance_confidence,
    )
    db.add(prov)
    db.commit()
    db.refresh(item)
    return item


def ingest_cv_data(user_id: int, db: Session) -> list[CandidateEvidence]:
    """Extract evidence items from UserProfile.cv_data and persist them.

    Idempotent: skips items whose title already exists for this user + type.
    Returns the list of newly created evidence items.
    """
    profile = db.execute(
        select(UserProfile).where(UserProfile.user_id == user_id)
    ).scalar_one_or_none()

    if not profile or not profile.cv_data:
        return []

    cv = profile.cv_data
    created: list[CandidateEvidence] = []

    for section_key, evidence_type in _CV_SECTION_MAP.items():
        items = cv.get(section_key)
        if not items or not isinstance(items, list):
            continue

        for raw in items:
            if not isinstance(raw, dict):
                continue

            title = (
                raw.get("title")
                or raw.get("role")
                or raw.get("name")
                or raw.get("company")
                or ""
            ).strip()
            if not title:
                continue

            # Skip duplicates
            existing = db.execute(
                select(CandidateEvidence).where(
                    CandidateEvidence.user_id == user_id,
                    CandidateEvidence.evidence_type == evidence_type,
                    CandidateEvidence.title == title,
                )
            ).scalar_one_or_none()
            if existing:
                continue

            skills = raw.get("skills") or []
            if isinstance(skills, str):
                skills = [s.strip() for s in skills.split(",") if s.strip()]

            item = CandidateEvidence(
                user_id=user_id,
                evidence_type=evidence_type,
                title=title,
                description=raw.get("description") or raw.get("summary"),
                url=raw.get("url"),
                skills_demonstrated=skills if isinstance(skills, list) else [],
                start_date=raw.get("start_date") or raw.get("start"),
                end_date=raw.get("end_date") or raw.get("end"),
                source="cv_extracted",
            )
            db.add(item)
            db.flush()

            prov = VerificationProvenance(
                evidence_id=item.id,
                evidence_source="cv_extracted",
                assessment_version=_CV_EXTRACTION_VERSION,
                confidence=0.7,
            )
            db.add(prov)
            created.append(item)

    db.commit()
    return created


def get_evidence(user_id: int, db: Session) -> list[dict]:
    """Return all evidence items for a user with their latest provenance."""
    rows = (
        db.execute(
            select(CandidateEvidence)
            .where(CandidateEvidence.user_id == user_id)
            .order_by(CandidateEvidence.created_at.desc())
        )
        .scalars()
        .all()
    )

    result = []
    for item in rows:
        # Latest provenance record
        latest_prov = db.execute(
            select(VerificationProvenance)
            .where(VerificationProvenance.evidence_id == item.id)
            .order_by(VerificationProvenance.created_at.desc())
            .limit(1)
        ).scalar_one_or_none()

        result.append(
            {
                "id": item.id,
                "evidence_type": item.evidence_type,
                "title": item.title,
                "description": item.description,
                "url": item.url,
                "skills_demonstrated": item.skills_demonstrated,
                "start_date": item.start_date,
                "end_date": item.end_date,
                "source": item.source,
                "created_at": item.created_at.isoformat(),
                "provenance": {
                    "evidence_source": latest_prov.evidence_source,
                    "assessment_version": latest_prov.assessment_version,
                    "confidence": latest_prov.confidence,
                    "expiry_date": latest_prov.expiry_date,
                }
                if latest_prov
                else None,
            }
        )

    return result

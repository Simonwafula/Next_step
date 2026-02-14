from datetime import datetime, timedelta

from app.db.models import (
    HiringSignal,
    JobPost,
    Organization,
    SignalEvidence,
    TenderNotice,
    TitleNorm,
)
from app.services.signals import (
    generate_signal_aggregates,
    normalize_tender_metadata,
)


def test_normalize_tender_metadata_updates_fields(db_session_factory):
    db = db_session_factory()
    notice = TenderNotice(
        source="tender_rss",
        title="Nairobi County - Supply of IT Equipment",
        description_raw="Supply and delivery of computers in Nairobi.",
    )
    db.add(notice)
    db.commit()

    result = normalize_tender_metadata(db, limit=10)
    assert result["updated"] == 1

    refreshed = db.query(TenderNotice).filter(TenderNotice.id == notice.id).one()
    assert refreshed.organization == "Nairobi County"
    assert refreshed.category == "it"
    assert refreshed.location == "Nairobi"
    db.close()


def test_generate_signal_aggregates_creates_evidence(db_session_factory):
    db = db_session_factory()

    org = Organization(name="Acme Corp", verified=False, sector="Tech")
    db.add(org)
    db.flush()

    title_norm = TitleNorm(
        family="engineering",
        canonical_title="Software Engineer",
        aliases={},
    )
    db.add(title_norm)
    db.flush()

    now = datetime.utcnow()
    for idx in range(3):
        db.add(
            JobPost(
                source="test",
                url=f"https://example.com/jobs/{idx}",
                url_hash=f"hash-{idx}",
                title_raw="Software Engineer",
                title_norm_id=title_norm.id,
                org_id=org.id,
                first_seen=now - timedelta(days=1),
                repost_count=3,
            )
        )
    db.commit()

    result = generate_signal_aggregates(db, days=30, limit=20)
    assert result["created_total"] >= 1
    assert result["created_by_type"]["posting_velocity"] >= 1
    assert result["created_by_type"]["repost_intensity"] >= 1

    signals = db.query(HiringSignal).all()
    assert signals
    assert any(signal.evidence_ids for signal in signals)

    evidence = db.query(SignalEvidence).all()
    assert evidence
    db.close()

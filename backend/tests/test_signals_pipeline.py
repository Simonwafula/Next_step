from datetime import datetime, timedelta

from app.db.models import (
    HiringSignal,
    JobPost,
    Organization,
    ProcessingLog,
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

    refreshed = (
        db.query(TenderNotice)
        .filter(TenderNotice.id == notice.id)
        .one()
    )
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


def test_signal_aggregates_idempotent_per_window(db_session_factory):
    db = db_session_factory()

    org = Organization(name="Gamma Works", verified=False, sector="Tech")
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
                url=f"https://example.com/gamma/{idx}",
                url_hash=f"gamma-hash-{idx}",
                title_raw="Software Engineer",
                title_norm_id=title_norm.id,
                org_id=org.id,
                first_seen=now - timedelta(days=2),
                repost_count=3,
            )
        )
    db.commit()

    first = generate_signal_aggregates(db, days=30, limit=20)
    first_count = db.query(HiringSignal).count()
    assert first["created_total"] >= 1
    assert first_count >= 1

    second = generate_signal_aggregates(db, days=30, limit=20)
    second_count = db.query(HiringSignal).count()

    assert second["created_total"] == first["created_total"]
    assert second_count == first_count
    db.close()


def test_signal_aggregates_logs_evidence_links(db_session_factory):
    db = db_session_factory()

    org = Organization(name="Beta Labs", verified=False, sector="Tech")
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
    for idx in range(2):
        db.add(
            JobPost(
                source="test",
                url=f"https://example.com/beta/{idx}",
                url_hash=f"beta-hash-{idx}",
                title_raw="Software Engineer",
                title_norm_id=title_norm.id,
                org_id=org.id,
                first_seen=now - timedelta(days=1),
                repost_count=3,
            )
        )
    db.commit()

    generate_signal_aggregates(db, days=30, limit=20)

    log_entry = (
        db.query(ProcessingLog)
        .filter(ProcessingLog.process_type == "signals_aggregate")
        .order_by(ProcessingLog.id.desc())
        .first()
    )
    assert log_entry is not None
    assert log_entry.results.get("status") == "success"

    details = log_entry.results.get("details", {})
    assert details.get("created_total", 0) >= 1
    assert details.get("evidence_links_count", 0) >= 1
    assert details.get("evidence_ids")
    db.close()

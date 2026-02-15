from datetime import datetime, timedelta

from app.db.models import ProcessingLog
from app.services.monitoring_service import monitoring_summary


def _drift_ok_payload():
    return {
        "skills": {
            "drift_score": 0.1,
            "recent_top": ["python"],
            "baseline_top": ["python"],
        },
        "titles": {
            "drift_score": 0.1,
            "recent_top": ["engineer"],
            "baseline_top": ["engineer"],
        },
        "salary": {
            "delta_ratio": 0.1,
        },
    }


def _quality_ok_payload():
    return {
        "gates": {
            "overall_status": "pass",
        }
    }


def test_monitoring_summary_fails_when_ingestion_error_rate_exceeds_threshold(
    db_session_factory,
    monkeypatch,
):
    db = db_session_factory()

    now = datetime.utcnow()
    db.add_all(
        [
            ProcessingLog(
                process_type="ingestion",
                results={"status": "success"},
                processed_at=now - timedelta(hours=1),
            ),
            ProcessingLog(
                process_type="ingestion",
                results={"status": "error"},
                processed_at=now - timedelta(hours=2),
            ),
            ProcessingLog(
                process_type="ingestion",
                results={"status": "error"},
                processed_at=now - timedelta(hours=3),
            ),
        ]
    )
    db.commit()

    monkeypatch.setattr(
        "app.services.monitoring_service.run_drift_checks",
        lambda *_args, **_kwargs: _drift_ok_payload(),
    )
    monkeypatch.setattr(
        "app.services.monitoring_service.quality_snapshot",
        lambda *_args, **_kwargs: _quality_ok_payload(),
    )
    monkeypatch.setenv("MONITORING_ERROR_RATE_MAX", "20")

    summary = monitoring_summary(
        db,
        recent_days=30,
        baseline_days=180,
        top_n=20,
    )

    assert summary["operations"]["checks"]["error_rate"]["status"] == "fail"
    assert summary["overall_status"] == "fail"
    db.close()


def test_monitoring_summary_fails_when_ingestion_is_stale(
    db_session_factory,
    monkeypatch,
):
    db = db_session_factory()

    db.add(
        ProcessingLog(
            process_type="ingest_all",
            results={"status": "success"},
            processed_at=datetime.utcnow() - timedelta(hours=100),
        )
    )
    db.commit()

    monkeypatch.setattr(
        "app.services.monitoring_service.run_drift_checks",
        lambda *_args, **_kwargs: _drift_ok_payload(),
    )
    monkeypatch.setattr(
        "app.services.monitoring_service.quality_snapshot",
        lambda *_args, **_kwargs: _quality_ok_payload(),
    )
    monkeypatch.setenv("MONITORING_INGESTION_STALENESS_HOURS", "24")

    summary = monitoring_summary(
        db,
        recent_days=30,
        baseline_days=180,
        top_n=20,
    )

    assert summary["operations"]["checks"]["ingestion_freshness"]["status"] == "fail"
    assert summary["overall_status"] == "fail"
    db.close()

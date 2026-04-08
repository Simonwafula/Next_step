import cli


class _DummySession:
    def close(self):
        return None


def test_data_quality_cycle_runs_requested_steps(monkeypatch):
    calls = []

    monkeypatch.setattr(cli, "SessionLocal", lambda: _DummySession())
    monkeypatch.setattr(
        cli,
        "backfill_normalized_entities",
        lambda db, **kwargs: calls.append(("backfill", kwargs)) or {"ok": True},
    )
    monkeypatch.setattr(
        cli,
        "create_job_post_analysis_view",
        lambda: calls.append(("create_view", {})),
    )
    monkeypatch.setattr(
        cli,
        "refresh_job_post_analysis_view",
        lambda: calls.append(("refresh_view", {})),
    )

    cli.data_quality_cycle(
        dry_run=True,
        limit=25,
        orgs_only=False,
        locations_only=False,
        create_view=True,
        refresh_view=True,
    )
    assert calls[0] == (
        "backfill",
        {
            "dry_run": True,
            "limit": 25,
            "orgs_only": False,
            "locations_only": False,
        },
    )
    assert calls[1][0] == "create_view"
    assert calls[2][0] == "refresh_view"

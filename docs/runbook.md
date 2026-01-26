# Runbook (Draft)

Operational guide for Next Step ingestion, analytics, and monitoring. This is a working draft to support T-604 and will expand as T-601 to T-603 land.

## Scope
- Ingestion pipeline runs (scrape -> normalize -> dedupe -> embed -> analytics).
- Analytics refresh and dashboards.
- Monitoring, drift checks, and alerting.

## Preconditions
- `.env` configured for database + Redis.
- Access to `backend/venv3.11/` tools.
- Jobs database ready (SQLite or Postgres).

## Daily Checks
- Ingestion completed within expected window.
- New job count and duplicates within normal ranges.
- Skill trend and role evolution aggregates updated.
- Alerts delivered (email/WhatsApp) when thresholds are exceeded.

## Common Commands
```bash
backend/venv3.11/bin/ruff check backend
backend/venv3.11/bin/ruff format backend
backend/venv3.11/bin/pytest backend
```

```bash
python backend/cli.py ingest --source all
python backend/cli.py process --batch-size 500
python backend/cli.py analytics --refresh
```

## Known Failure Modes
- Scraper 403/429 responses (rate limits, selector drift).
- Database lock timeouts during batch writes.
- Embedding refresh failures (model download or GPU/CPU memory).
- Analytics refresh returning empty aggregates (missing entities).

## Initial Triage
- Check processing logs and error traces.
- Verify last processed watermark (T-601).
- Re-run targeted stage via CLI with smaller batch sizes.

## Rollback Notes
- Preserve raw scrape outputs.
- Revert to last known good analytics snapshot if aggregates are empty.
- Disable flaky source entries in `backend/app/ingestion/sources.yaml`.

## Next Additions
- Define runbooks for drift thresholds, evidence tracking, and regression suites.
- Document alert routing and escalation paths.

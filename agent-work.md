# Agent Work Dashboard - Next Step

Status: Active summary. Keep current; move completed work to `changemap.md`.

## Focus Now
- Add/update government sources in `backend/app/ingestion/government_sources.yaml`.
- Improve data quality (company, location, salary, seniority coverage).
- Maintain ingestion reliability across active sources.

## Last Completed
- 2026-01-25: Instruction audit and agent dashboard refresh; added compatibility files.

## Risks / Blockers
- (List current blockers or "None".)

## Quick Metrics
- Total jobs: 1865
- With organization: 1466
- With location: 1109
- With salary: 9
- With seniority: 475

## Weekly Maintenance
- Review `backend/app/ingestion/government_sources.yaml` for stale or broken URLs.
- Run a small ingestion sample and confirm job_post counts change as expected.
- Check data quality deltas (org/location/salary/seniority coverage).
- Update `changemap.md` with notable changes and outcomes.

## Notes
- Keep this file short; use `changemap.md` for detailed logs.

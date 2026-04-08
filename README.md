# Next Step

Next Step is a job-matching and labour market intelligence platform built around:

- a FastAPI backend for search, recommendation, ingestion, and admin workflows
- a static frontend for public search and user journeys
- dbt models for analytics and reporting

This README is intentionally brief. Detailed operational and workflow instructions
live in the canonical documents listed below.

## Repo Layout

- `backend/` - API, models, services, ingestion, tests
- `frontend/` - static site assets and pages
- `dbt/` - analytics models
- `deploy/` - committed systemd unit templates
- `scripts/` - operational helpers and bootstrap scripts
- `docs/` - canonical project documentation

## Canonical Docs

- Deployment: `docs/deployment.md`
- Runbook: `docs/runbook.md`
- Ingestion workflows: `docs/ingestion-workflows.md`
- Product and roadmap context: `docs/product.md`
- Features: `docs/features.md`
- User journey: `docs/userjourney.md`

## Workflow Docs

- Repo/agent operating rules: `AGENTS.md`
- Change tracking: `changemap.md`
- Session handoff log: `handoff.md`

## Production Summary

- Domain: `nextstep.co.ke`
- Repo root: `/home/nextstep.co.ke/public_html`
- Frontend docroot: `/home/nextstep.co.ke/public_html/frontend`
- Runtime env: `/home/nextstep.co.ke/.env`
- Runtime venv: `/home/nextstep.co.ke/.venv`
- Backend bind: `127.0.0.1:8010`

For production commands and service details, use `docs/deployment.md`.

## Notes

- Do not commit runtime artifacts, large outputs, or secrets.
- Do not treat this README as the source of truth for deployment or agent workflow.
- Historical or superseded notes have been moved under `docs/archive/`.

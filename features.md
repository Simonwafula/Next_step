# Features

## Done
- Skill and course-based job search with filters.
- Job ingestion from ATS boards (Greenhouse, Lever) and RSS feeds.
- Government career-page monitoring pipeline (HTML ingest + scheduled workers).
- **High-Precision Normalization**: Production-ready modules for Titles, Companies, Locations, and Skills.
- **Deduplication Engine**: MinHash + LSH based deduplication for clean datasets.
- **Production Schema**: Migrated to PostgreSQL with `pgvector`, `pg_trgm`, and `unaccent` support.
- **Semantic Embeddings**: Full integration with `intfloat/e5-small-v2` for high-quality retrieval.
- **Data Parsers**: Robust salary and date standardization logic.
- FastAPI endpoints for search, recommendations, and admin ingestion.
- Email/password auth with JWT tokens.
- Google OAuth sign-in and password reset flow.
- Frontend landing + search UI with auth modals and account overview.
- Admin dashboard with KPIs, source snapshot, and ingestion actions.
- User dashboard with recommendations, saved roles, applications, and notifications.
- dbt models for basic LMI aggregates.

## Partial / In Progress
- Personalized recommendations (basic matching; deeper personalization pending).
- Automated workflows and scrapers (operational but needs broader coverage).
- Notifications (email/WhatsApp hooks exist; delivery logic is stubbed).
- Analytics dashboards endpoints for admin/user views (T-403).
- Incremental ingestion updates and drift monitoring (T-601/T-602).

## Planned / Future
- Full NLP skill extraction and richer role matching.
- Employer accounts and verified recruiter tools.
- Saved searches, alerts, and application tracking UX.
- Advanced analytics dashboards and benchmarking (Metabase + LMI).
- Expanded data sources (private sector boards, international roles).
- Subscription billing and premium tiers.
- Signals pipeline (tenders, task→role mapping, hiring signals, evidence tracking).
- Regression tests and operational runbook hardening.

## Proposed / Under Consideration
- Source health monitoring with uptime checks, change detection, and auto-disable on repeated failures.
- Data quality scoring with a manual review queue for noisy sources.
- Resume import (PDF/Doc) with structured profile extraction.
- Geo-aware search with commute filters and county-level salary insights.
- Public API keys with rate limits for partners and researchers.
- Government PDF ingestion with OCR for gazette-style postings.

# Features

## Done
- Skill and course-based job search with filters.
- Job ingestion from ATS boards (Greenhouse, Lever) and RSS feeds.
- Government career-page monitoring pipeline (HTML ingest + scheduled workers).
- Title normalization and basic skill extraction.
- Job deduplication logic and URL hashing.
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
- Embeddings (hash fallback available; real model integration optional).

## Planned / Future
- Full NLP skill extraction and richer role matching.
- Employer accounts and verified recruiter tools.
- Saved searches, alerts, and application tracking UX.
- Advanced analytics dashboards and benchmarking (Metabase + LMI).
- Expanded data sources (private sector boards, international roles).
- Subscription billing and premium tiers.

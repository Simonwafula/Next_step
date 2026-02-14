# Later Features - Not MVP

This directory contains features that were started but are not part of the Minimum Viable Product (MVP). They have been moved here to reduce codebase complexity and maintenance burden until user demand validates their need.

## Moved Features

### 1. Payment/Subscription System
**Files:** `services/payment_service.py`, related models
**Reason:** No validated demand, hardcoded credentials, security risk
**Dependencies:** M-Pesa API, Stripe (not configured)
**Restore when:** User research validates premium tier demand + payment provider accounts secured

### 2. LinkedIn Integration
**Files:** `services/linkedin_service.py`, `db/integration_models.py` (LinkedInProfile)
**Reason:** No validated demand, OAuth maintenance burden
**Dependencies:** LinkedIn API credentials
**Restore when:** Users explicitly request profile import/sync feature

### 3. Calendar Integration (Google/Microsoft)
**Files:** `services/calendar_service.py`, `db/integration_models.py` (CalendarIntegration, CalendarEvent)
**Reason:** No clear use case, complex OAuth for two providers
**Dependencies:** Google Calendar API, Microsoft Graph API
**Restore when:** Interview scheduling or deadline tracking becomes validated need

### 4. ATS Integration Models (partial)
**Files:** `db/integration_models.py` (ATSIntegration, ATSJobSync, ATSApplicationSync, IntegrationActivityLog)
**Reason:** Unclear if this is for ingestion (already working) or employer dashboard (not MVP)
**Dependencies:** None currently
**Restore when:** Employer accounts feature is validated

## Not Moved (Needs Completion)

- **Notification Service:** Core feature, needs delivery implementation
- **Career Tools/AI Service:** Per OUTCOMES_PLAN.md, needs RAG pipeline before production
- **ATS Ingestion Connectors:** Already working, part of core functionality

## Restoration Process

When restoring a feature:
1. Validate user demand with research/interviews
2. Review and update code for security/best practices
3. Write tests before reintegration
4. Update documentation
5. Plan phased rollout

# Scope Cleanup - 2026-02-14

## Summary

Moved scope creep features to `later_features/` to reduce codebase complexity and focus on MVP (Minimum Viable Product) as defined in `OUTCOMES_PLAN.md`.

## Impact Metrics

- **~3,000 lines of code** removed from active codebase
- **0 tests** for moved features (confirming they were incomplete)
- **3 service files** moved
- **1 API routes file** moved
- **1 integration models file** copied for reference

## Files Moved to `later_features/`

### Services
1. **`payment_service.py`** (~500 lines)
   - M-Pesa integration (hardcoded credentials)
   - Stripe integration (not implemented)
   - Subscription models exist but no endpoints
   - **Risk:** Security issue with placeholder credentials in code
   - **Restore when:** User research validates premium tier demand

2. **`linkedin_service.py`** (~600 lines)
   - LinkedIn OAuth flow scaffolded
   - No actual profile sync implemented
   - Database models unused
   - **Restore when:** Users explicitly request LinkedIn integration

3. **`calendar_service.py`** (~700 lines)
   - Google Calendar and Microsoft Graph OAuth flows
   - Event creation stubbed but not functional
   - No clear use case validated
   - **Restore when:** Interview scheduling becomes validated need

4. **`ats_service.py`** (~900 lines)
   - ATS (Greenhouse, Lever, Workday, BambooHR) integration
   - Unclear if for ingestion (already works) or employer dashboard (not MVP)
   - **Restore when:** Clarify intent and validate demand

### API Routes
5. **`integration_routes.py`** (~600 lines)
   - LinkedIn auth/callback/profile/sync endpoints
   - Calendar auth/callback/integrations/events endpoints
   - ATS integration CRUD endpoints
   - Integration activity logs
   - **Restore when:** Any of the above services are restored

### Database Models
6. **`integration_models.py`** (copied to `later_features/db/`)
   - LinkedInProfile
   - CalendarIntegration, CalendarEvent
   - ATSIntegration, ATSJobSync, ATSApplicationSync
   - IntegrationActivityLog
   - **Note:** Models still exist in active DB schema but unused
   - **Action needed:** Consider migration to drop unused tables in production

## Code Changes

### Commented Out Imports
- `backend/app/main.py`: Commented out `integration_router` import and route registration
- `backend/app/api/routes.py`: Commented out `integration_routes` import and inclusion

### Working Features Preserved
- ✅ Authentication (email/password, Google OAuth)
- ✅ Job search and matching
- ✅ Government ingestion
- ✅ Analytics endpoints
- ✅ Admin dashboard
- ✅ User dashboard
- ✅ Notification models (delivery needs completion)
- ✅ WhatsApp webhook
- ✅ Career tools service (needs RAG completion per OUTCOMES_PLAN.md)

## Features That Need Completion (Not Moved)

1. **Notification Delivery** - Core feature per outcomes plan
   - Models exist, delivery stubbed
   - Priority: HIGH - users expect job alerts

2. **Career Tools / AI Service** - Per OUTCOMES_PLAN.md Phase 2
   - T-801-805: RAG, grounding, guardrails, evaluation all missing
   - Current implementation is mock/prompt-only
   - Priority: MEDIUM - defer until Phase 2 or remove UI exposure

3. **Learned Ranking** - T-306
   - Basic matching works, LTR/classification pending
   - Priority: LOW - validate with user feedback first

## Database Cleanup Recommendations

Consider Alembic migration to drop unused tables in production:
- `linkedin_profile`
- `calendar_integration`
- `calendar_event`
- `ats_integration`
- `ats_job_sync`
- `ats_application_sync`
- `integration_activity_log`
- `subscription` (from payment_service)
- `payment` (from payment_service)
- `company_review` (not part of moved features but also unused)
- `skill_assessment` (not part of moved features but also unused)

**Note:** Keep `career_document` table as career tools service is partially implemented.

## Restoration Process

When restoring a feature:
1. ✅ Validate user demand with research/interviews
2. ✅ Review code for security/best practices
3. ✅ Write tests before reintegration (TDD)
4. ✅ Update documentation
5. ✅ Plan phased rollout with feature flags

## Testing Status

After cleanup:
- ✅ App imports successfully
- ⏳ Need to run full test suite: `uv run pytest -q`
- ⏳ Need to verify dev server starts: `./scripts/dev-start.sh`

## Next Actions

1. Run test suite to ensure no breakage
2. Update `changemap.md` with cleanup notes
3. Consider creating feature flags for Career Tools to hide incomplete features
4. Document Phase 1-3 priorities per `OUTCOMES_PLAN.md`
5. Create migration to drop unused DB tables (optional, VPS only)

## References

- Audit report: Internal analysis (2026-02-14)
- Product direction: `OUTCOMES_PLAN.md`
- Feature tracking: `changemap.md`
- Architecture decisions: `docs/ml-db-production-plan.md`

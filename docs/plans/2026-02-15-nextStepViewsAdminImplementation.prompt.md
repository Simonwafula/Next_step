# NextStep Views + Admin Implementation Plan

## Scope
Implement the plan in phased, shippable increments with immediate focus on Phase 1 outcomes:
- Guest conversion flow quality (Search → Results → Detail hook)
- Professional actionability (better job cards + filters)
- Admin reliability surface (navigation + command-center framing)
- Brand consistency by adapting UI colors to logo palette

## Phase 1 (This Iteration)

### 1) Guest Search/Results Upgrades
- Replace homepage quick chips with market-first chips:
  - Remote, Internships, Entry-level, Govt, NGO, Tech, Sales
- Extend results filters to include:
  - Role family, Seniority, County, Sector, High-confidence only
- Upgrade job cards to show:
  - Title, employer, location, contract type, posted date
  - Top skills preview
  - Quality tag (High confidence / Medium)
  - Direct apply link

### 2) Search API Contract Upgrade
- Extend `/api/search` query params:
  - `role_family`, `county`, `sector`, `high_confidence_only`
- Extend search facets payload:
  - `role_families`, `seniority_buckets`, `counties_hiring`, `sectors_hiring`
- Keep backward compatibility for existing fields:
  - `results`, `jobs`, `title_clusters`, `companies_hiring`, `selected`

### 3) Admin IA Alignment
- Add sticky admin section nav for core information architecture:
  - Dashboard, Sources, Runs, Dedup Review, Taxonomy, Moderation, Analytics, Users & Billing, Audit Logs
- Keep existing admin cards and wire section anchors for immediate usability without backend churn.

### 4) Brand Adaptation (Logo-aligned)
- Shift theme accents toward logo colors:
  - Green as primary brand action color
  - Blue as secondary accent color
- Replace hardcoded accent colors in key interactive states with tokens.
- Preserve readability/contrast by retaining dark neutral (`--ink`) for primary text and high-contrast surfaces.

## Out of Scope (Deferred)
- Full institutional portal pages
- Full moderation workflow engine beyond existing controls
- Multi-tenant partitioning implementation
- Snapshot/replay engine implementation
- Link health checker scheduler

## Backend Design Notes
- Confidence threshold for `high_confidence_only`:
  - `quality_score >= 0.7`
- County derivation:
  - prefer `Location.region`, fallback `Location.city`, then `Location.raw`
- Skills preview source:
  - from `JobEntities.skills` via existing `skills_found` projection

## Frontend Design Notes
- Filter chips remain multi-block with single-select behavior per block.
- New filters should be additive with existing `title/company` filters.
- Results metadata should still show count and degrade gracefully when facets are missing.

## Verification Plan
- Backend tests:
  - add focused tests for `/api/search` forwarding and new params/facets behavior
- Regression tests:
  - existing guided search tests must still pass
- Manual smoke:
  - verify homepage chip interactions
  - verify new filters modify search request
  - verify admin section nav anchors

## Change Tracking
- Every implementation step logged in `changemap.md` with:
  - files changed
  - behavior delivered
  - commands run
  - pass/fail status

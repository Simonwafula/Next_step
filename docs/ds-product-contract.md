# DS Product Contract

Last updated: 2026-03-23

This document is the control-plane contract for the DS / ML roadmap in Next Step.

It resolves `T-DS-900`:
- `T-DS-901` primary execution track
- `T-DS-902` canonical score glossary
- `T-DS-903` mission metric tree + intelligence metric tree
- `T-DS-904` two-track roadmap

## Source Of Truth

- Product problem source of truth: `PROBLEM.md`
- DS / ML execution audit: `DS_ML.md`
- Delivery control plane: `changemap.md`

The product is not a generic job-search or pure LMI product first.

The mission remains:

> Build a trust layer for Kenya's labor market that verifies skills, pre-screens candidates, provides feedback, and creates real access.

## Primary Track Decision

For the next 6 months:

- Primary track: `Trust-Layer First`
- Mandatory supporting workstream: `LMI / Intelligence`

Reason:

- The root problem in `PROBLEM.md` is trust, access, feedback, and employer overload, not search convenience.
- Search, recommendation, and intelligence remain necessary, but they are supporting systems unless they improve trust-layer outcomes.
- Intelligence is mandatory because verification, skills-gap, salary context, and shortlist quality depend on market-grounded baselines.

## Canonical Score Glossary

These terms are frozen and must not be used interchangeably.

### Retrieval Score

- What it means: relevance from retrieval-time matching between a query/profile and a job or role candidate set
- Typical inputs: embeddings, lexical match, structured filter match
- Used in: search candidate generation, role/pathway discovery
- Not the same as: final ranking, verification, shortlist quality

### Heuristic Score

- What it means: deterministic weighted score assembled from interpretable rules and features
- Typical inputs: title overlap, recency, salary alignment, location fit, skill overlap
- Used in: search ordering, fallback ranking, recommendation ranking, prescreening components
- Not the same as: model probability or verified skill signal

### Verification Score

- What it means: evidence-backed estimate of whether a candidate can actually perform a skill or role-relevant task
- Typical inputs: assessments, candidate evidence, provenance confidence, expiry/versioning
- Used in: trust-layer candidate profiles, employer-facing candidate evaluation
- Not the same as: self-reported skills or search relevance

### Shortlist Score

- What it means: employer-side candidate-to-job fit score used to reduce application overload
- Typical inputs: verification score, evidence strength, profile/job fit, intelligence sidecars
- Used in: pre-screening and “The 20”
- Not the same as: job-search ranking for job seekers

### Feedback Score

- What it means: structured explanation signal about why a candidate did or did not progress and what would improve odds next time
- Typical inputs: funnel events, rejection reasons, employer ratings, role baselines
- Used in: candidate feedback, learning loops, outcome analysis
- Not the same as: generic recommendation explanation text

## Intelligence Terminology

### Baseline Confidence

- Confidence in a labor-market baseline for a role family, based on sample size, freshness, and low-confidence share

### Representativeness

- How well the observed dataset reflects the market rather than a narrow slice of sources, geographies, or sectors

### Demand Share

- The share of relevant postings within a scoped market window that mention a skill, role pattern, or requirement

### Salary Estimate Confidence

- Confidence that a salary output is backed by enough real posting data rather than a heuristic fallback

## Mission Metric Tree

### North Star

- Qualified chances created
- Operational definition: candidates who reach shortlist, interview, offer, or hire states because of Next Step trust-layer signals

### Mission Metrics

- Verified candidates rate
- Candidate shortlist rate
- Shortlist-to-interview conversion
- Interview-to-offer conversion
- Offer / hire outcome count
- Candidate feedback coverage rate

### Supporting Product Metrics

- Search hit rate at k
- Search MRR / nDCG on logged sessions
- Recommendation apply/save/click rate
- Assessment completion rate
- Assessment certification rate
- Employer quick-rating capture rate

## Intelligence Metric Tree

### North Star

- Decision-grade intelligence coverage
- Operational definition: the share of user-facing intelligence outputs that are fresh, sufficiently sampled, and explicitly confidence-labeled

### Core Intelligence Metrics

- Baseline freshness
- Sample size coverage
- Low-confidence row share
- Source-mix diversity
- Geography coverage
- Sector coverage
- Coverage-gap count
- Salary low-confidence call rate

### Productized Intelligence Metrics

- Skills-gap responses with provenance attached
- Career pathway responses using market-derived baselines
- Employer shortlist responses with intelligence sidecars
- Admin intelligence dashboard health status

## Two-Track Roadmap

### Track A: Trust-Layer First

1. `T-DS-900`
   Publish the DS contract, score glossary, metric trees, and track decision.
2. `T-DS-910`
   Finish instrumentation and offline evaluation so search, recommendations, and ranking can be measured.
3. `T-DS-920`
   Keep intelligence baselines market-grounded and representative enough to support trust-layer products.
4. `T-DS-930`
   Build candidate evidence and provenance as the substrate for credible profiles.
5. `T-DS-940`
   Ship operational skill verification for narrow launch families.
6. `T-DS-950`
   Use verification + evidence to power employer-side shortlist reduction.
7. `T-DS-960`
   Close the loop with rejection feedback and hiring outcomes.
8. `T-DS-970` and `T-DS-980`
   Harden intelligence products and consolidate the model stack around the trust-layer.

### Track B: LMI / Intelligence First

This remains valid as a secondary route, but not the primary one.

1. `T-DS-900`
2. `T-DS-910`
3. `T-DS-920`
4. `T-DS-970`
5. `T-DS-930`
6. `T-DS-960`
7. `T-DS-940`
8. `T-DS-950`
9. `T-DS-980`

Constraint:

- Track B is allowed only if intelligence outputs are still explicitly tied back to trust-layer outcomes.

## Working Rules

- Do not describe search scores as verification.
- Do not describe recommendation quality as shortlist quality.
- Do not expose intelligence outputs without provenance/confidence metadata where available.
- Do not treat prototype delivery in older roadmap sections as proof of mission-complete trust-layer delivery.

## Immediate Next Work

- Reconcile `changemap.md` so completed DS phases match branch history.
- Run environment-backed `pytest` for the newest DS evaluation coverage.
- Continue from the first actually unresolved implementation tasks after reconciliation.

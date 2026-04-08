Outcome Plan v2 for NextStep
Product promise
NextStep turns messy job adverts into career navigation:
Public (no account): show what’s hiring now (titles + companies) with direct application links.
Logged-in: guide different users (students, early-career, professionals) to decisions and actions using market evidence.
Non-negotiable outcomes
O0: Public search must work without an account
Definition of done
A user can search and immediately see:
Job titles available (clusters, counts)
Companies hiring for those titles (counts)
Sample jobs with Apply button that redirects to the real application page
Clicking a title/company filters to the job list.
Acceptance criteria
application_url exists or clean fallback to source_url
/r/apply/{job_id} logs and redirects
O1: Student outcomes (Explore mode)
Students must be able to learn:
what a career/role is
educational requirements
the map to get there
live jobs as evidence (optional)
Definition of done
Search in Student mode returns “career cards” (role-level), not only jobs.
Each card shows: education distribution, common skills/tools, demand count, and “view map”.
O2: Early-career outcomes (Match mode)
Early-career users must be able to answer:
“What roles can I do with my course/skills?”
“What am I missing?”
“Where are the starter jobs?”
Definition of done
Search returns ranked role matches + 3–5 starter job previews per role.
Each role shows missing skills (derived from ads) + link to apply list.
O3: Professional outcomes (Advance mode)
Professionals must be able to:
plan transitions/promotions
see skill gap + trend shifts
access live target jobs
Definition of done
Search returns transition cards with:
target role
tradeoffs proxy (time/cost/difficulty)
missing skills vs baseline
“see target jobs” + “transition plan”
O4: Admin paid outcomes (LMI & early warning)
Admin must get market intelligence from adverts:
trends
emerging skills/tools
role demand shifts
employer shifts
Definition of done
Admin dashboard/API exposes the “minimum viable insights layer” (below)
Each insight includes sample job IDs as evidence
The canonical data strategy (keep saving raw, but formalize layers)
Layer 1 — Raw (immutable)
raw HTML/PDF/text snapshots + fetch metadata
Layer 2 — Canonical JobPost (clean record)
title_raw, title_norm, company_norm, location, deadline, application_url, source_url, timestamps
dedupe mapping + versioning
Layer 3 — Extracted Entities (meaning)
skills, education, experience, seniority, tasks, tools
confidences + spans/snippets if possible
Layer 4 — Insights (what the product sells)
This is what makes outputs “satisfactory.”
Minimum Viable Insights Layer (MVIL)
Build these 8 derived datasets and make the product read from them:
role_demand_daily (role_norm, date, count_ads, unique_employers, sample_job_ids)
skill_demand_daily (skill, date, count_ads, role_mix, sample_job_ids)
role_skill_matrix (role_norm, skill, frequency/share, sample_job_ids)
education_by_role (role_norm, requirement bins, distribution, sample_job_ids)
experience_by_role (role_norm, exp bands distribution, sample_job_ids)
salary_by_role (role_norm, bands/percentiles if available, sample_job_ids)
transition_edges (role_a, role_b, weight + why, sample_job_ids)
emerging_signals (role/skill/tool, growth score, sample_job_ids)
Hard rule: every insight row stores:
count_total_jobs_used
sample_job_ids (3–10)
Search experience specification (public vs logged-in)
Public Search (no auth)
UI
Titles available (clusters)
Companies hiring per title
Job preview list
Apply redirects correctly
API response
title_clusters[]
companies_hiring[] (grouped by title)
jobs[] (paged)
Logged-in Search
Same search bar, but now:
Mode selector: Explore / Match / Advance
Default tab: Guidance
Secondary tab: Jobs (same as public)
API response
includes public blocks plus mode-specific guided_results[]
Execution order (agent must follow)
Phase 1 (P0): Public search + application redirection
Ensure application_url is reliable
Add /r/apply/{job_id}
Build title clusters + companies hiring aggregates
Stop condition: public search feels useful even without login.
Phase 2 (P0): Role baselines + evidence wiring
Build role_skill_matrix, education_by_role, experience_by_role, role_demand_daily
Every role card/transition card must cite evidence job IDs
Stop condition: student/early/pro cards show real distributions and counts.
Phase 3 (P0): Guided modes at search
Implement Explore/Match/Advance result types + routing
Keep Jobs tab separate
Stop condition: the 3 user categories are correctly served at search.
Phase 4 (P1): Admin LMI + early warning
Implement emerging_signals, skill_demand_daily, transition_edges
Add admin alerts and export
Phase 5 (P1+): Add more sources safely
Only after Phases 1–3 are stable.
Data source expansion (allowed, but controlled)
Yes, you can add more sources — but do it by a source contract so it doesn’t break quality.
Add sources in this order
ATS/structured feeds (Greenhouse, Lever, Workable, etc.) – highest quality
Company career pages (HTML stable pages)
Gov portals (but must improve doc parsing and QA)
Linked content (professional associations, program pages, scholarship/certification sources)
Optional: curated “skills taxonomy” sources (O*NET/ESCO style) for labels—not truth
Rule: new source must pass quality gates (coverage, extraction success, dedupe rate) before it influences MVIL.
Agent steering rules (so no “improvements” before outcomes)
No UI polish unless it directly enables the outcomes above.
No new features until Phases 1–3 are green.
No LLM “advice” unless it cites evidence job IDs and uses role baselines.
Always prefer deterministic extraction; use LLM only for targeted hard cases with strict schema + evaluation.
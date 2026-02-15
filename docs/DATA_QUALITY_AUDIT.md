# Data Quality Infrastructure Audit

**Date:** 2026-02-15
**Context:** Before building LMI user-facing products, audit existing data quality infrastructure

---

## Executive Summary

**Bottom Line:** You have solid foundations (deduplication, quality scoring) but critical gaps in normalization that will cause "inflated and fragmented" LMI stats until fixed.

**Priority Order:**
1. 🔴 **CRITICAL:** Expand skill normalization (25 aliases → 200+ needed)
2. 🟡 **HIGH:** Add seniority inference to role taxonomy
3. 🟢 **MEDIUM:** Verify deduplication coverage in production data
4. 🟢 **LOW:** Add representativeness metadata (source mix, location bias)

---

## 1. Deduplication ✅ IMPLEMENTED

### What Exists

**Code:** `backend/app/services/deduplication_service.py` (580 lines)
**Database:** `JobDedupeMap` table with `(job_id, canonical_job_id, similarity_score)`
**Integration:** `run_incremental_dedup()` runs in pipeline (Step 4)

**Strategies:**
1. **Exact URL matching** (after normalization - removes tracking params, normalizes www)
2. **Fuzzy title + company + location** (SequenceMatcher with 80% threshold)
3. **Content similarity** (MinHash LSH with 90% threshold for embeddings)

**Quality:**
- URL normalization removes 18+ tracking params (utm_*, fbclid, gclid, etc.)
- Title normalization removes "jobs at", "urgent", parenthetical content
- Self-mapping creates record for unique jobs (prevents re-processing)
- Updates `last_seen` timestamp on duplicate detection (signals repost urgency)

### Gaps

1. **Coverage unknown** - No data on what % of jobs are deduplicated in production
2. **Cross-source matching** - Does it catch same job on LinkedIn + BrighterMonday?
3. **Repost counting** - Code has `repost_count` increment but field may not exist in JobPost model

### Recommendations

✅ **Keep as-is** - Implementation is solid
📊 **Add monitoring:** Track dedupe stats (% unique vs duplicate) per pipeline run
🔍 **Verify coverage:** Check `JobDedupeMap` row count vs `JobPost` count in production DB

---

## 2. Skill Normalization ⚠️ PARTIAL (CRITICAL GAP)

### What Exists

**Code:** `backend/app/normalization/skill_mapping.py`
**Dictionary:** `skill_mapping.json` with **only 25 alias mappings**
**Function:** `canonicalize_skill(name)` normalizes whitespace + applies aliases

**Current aliases:**
```json
{
  "amazon web services": "aws",
  "google cloud platform": "gcp",
  "ml": "machine learning",
  "nodejs": "node.js",
  "k8s": "kubernetes",
  ...
}
```

**Skill table schema:**
- `name` (String 120, unique, indexed)
- `taxonomy_ref` (String 120, nullable) - NOT populated
- `aliases` (JSONB) - NOT actively used

### Gaps (THIS IS THE PROBLEM)

❌ **Tiny dictionary:** 25 aliases won't catch common variations:
- "MS Excel", "Advanced Excel", "Excel Macros" → NOT normalized to "Excel"
- "PowerBI", "Power BI Desktop", "DAX" → NOT normalized to "Power BI"
- "Python 3", "Python Programming", "Python3" → NOT normalized to "Python"

❌ **No skill taxonomy:** Skills aren't grouped into families (e.g., "Python" + "Pandas" + "NumPy" = Python Data Stack)

❌ **Database fields unused:**
- `Skill.taxonomy_ref` is always NULL
- `Skill.aliases` is always `{}`

### Impact on LMI

**This causes the exact problems you described:**
- Skill demand charts are **fragmented** (Excel counted separately from MS Excel)
- Skill trends are **inflated** (same skill counted multiple times under different names)
- Match scoring will **undercount** overlaps (user has "Excel", job requires "MS Excel" → miss)

### Recommendations

🔴 **CRITICAL:** Expand `skill_mapping.json` to 200-300 aliases covering:
- Common variations (Excel, MS Excel, Advanced Excel, Excel Macros)
- Tool-specific terms (Power BI, PowerBI, Power BI Desktop, DAX, Power Query)
- Programming languages (Python, Python3, Python Programming)
- Abbreviations (SQL, Structured Query Language, T-SQL, PL/SQL)

🟡 **Populate taxonomy_ref:** Add skill families (e.g., "data_analysis", "programming", "cloud_infra")

🟢 **Build skill bundles:** For match scoring, create related skill sets:
```python
{
  "python_data_stack": ["python", "pandas", "numpy", "scikit-learn"],
  "power_bi_stack": ["power bi", "dax", "power query"],
  "aws_stack": ["aws", "ec2", "s3", "lambda", "cloudformation"]
}
```

---

## 3. Role Taxonomy ⚠️ PARTIAL

### What Exists

**Code:** `backend/app/normalization/titles.py`
**Database:** `TitleNorm` table with `(family, canonical_title, aliases)`
**Dictionary:** `TITLE_ALIASES` with ~20 role families

**Example mappings:**
```python
"data analyst": [
  "data ninja",
  "bi analyst",
  "analytics associate",
  "business intelligence analyst"
]
```

**Integration:** `normalize_title()` runs in `post_ingestion_processing_service.py`

### Gaps

❌ **No seniority inference:** Titles aren't classified by level (Junior, Mid, Senior, Lead)
❌ **No role families stored:** `TitleNorm.family` exists but may not group related roles
❌ **Small coverage:** ~20 role families won't cover Kenyan job market diversity

### Impact on LMI

- Career pathways can't show progression (Junior Data Analyst → Senior Data Analyst)
- Salary intelligence can't segment by seniority
- Role demand charts are fragmented (Data Analyst vs Senior Data Analyst counted separately)

### Recommendations

🟡 **Add seniority classification:** Parse titles for "junior", "senior", "lead", "principal", "head"
🟡 **Expand TITLE_ALIASES:** Add 50+ more role families (operations, logistics, healthcare, education)
🟢 **Implement role family grouping:** Store in `TitleNorm.family` field for analytics queries

---

## 4. Quality Scoring ✅ IMPLEMENTED

### What Exists

**Code:** `backend/app/services/processing_quality.py`
**Function:** `calculate_quality_score()` with deterministic formula
**Database:** `JobPost.quality_score` field (Float, 0-1 scale)

**Formula (weights):**
- Title quality (not generic): **0.25**
- Description length (up to 800 chars): **0.35**
- Skills count (≥5 skills): **0.20**
- Organization linked: **0.10**
- Salary data present: **0.10**

**Generic title filter:** Rejects "job posting", "vacancy", "careers", etc.

### Strengths

✅ **Simple and explainable** - Clear weights, no black box
✅ **Integrated in pipeline** - Runs automatically on all jobs
✅ **Quality gates** - Environment variables control thresholds

### Gaps

🟢 **No validation scoring:** Doesn't detect scams, duplicate listings, or low-quality employers
🟢 **No content analysis:** Doesn't check for clear responsibilities, requirements, application process

### Recommendations

✅ **Keep as-is** - Formula is reasonable
🟢 **Add validation flags:** Detect missing contact info, suspicious language, unrealistic salary
🟢 **Add employer reputation score:** Track hiring success rate, application completion rate

---

## 5. Time-Series Hygiene ⚠️ NEEDS VERIFICATION

### What Exists

**Database fields:**
- `JobPost.first_seen` (DateTime) - First scrape timestamp
- `JobPost.last_seen` (DateTime) - Most recent scrape timestamp
- `JobPost.scrape_date` - MAY exist (not in models.py)

**Deduplication behavior:**
- Updates `last_seen` when duplicate detected
- Increments `repost_count` (if field exists)

### Gaps

❓ **Unclear:** Is `first_seen` the *original posting date* or *first time we scraped it*?
❓ **Repost detection:** How do you distinguish "job reposted by employer" from "job still open"?
❌ **No posting date extraction:** Jobs often have "Posted 3 days ago" text, not extracted

### Impact on LMI

- Trend charts may show false spikes when jobs are rescraped
- "New jobs this week" counts may include old jobs reposted
- Time-to-hire estimates will be wrong if based on scrape dates

### Recommendations

🟡 **Extract original posting date:** Parse "Posted X days ago", "Date Posted: 2024-12-01" from job text
🟡 **Clarify semantics:** Document whether `first_seen` = original post date or first scrape
🟢 **Add staleness flag:** Mark jobs as "likely expired" if last_seen > 60 days ago

---

## 6. What's Missing (From Your Quality Ladder)

### ✅ Already Have
1. Standard schema (JobPost, Skill, TitleNorm)
2. Dedup + canonical job record (JobDedupeMap)
3. Quality scoring (calculate_quality_score)
4. Some skill extraction + normalization (partial)

### ❌ Need to Build
1. **Comprehensive skill synonym dictionary** (25 → 200+ aliases)
2. **Seniority inference** (Junior/Mid/Senior classification)
3. **Skill taxonomy** (skill families + related skill bundles)
4. **Representativeness metadata** (source mix, location bias labels)
5. **Trend correctness** (original posting date vs scrape date)

---

## Data Volume Check (NEEDS VERIFICATION)

**Cannot verify without database access.** Run these queries:

```sql
-- Total jobs
SELECT COUNT(*) FROM job_post;

-- Deduplication coverage
SELECT
  COUNT(*) as dedupe_entries,
  (SELECT COUNT(*) FROM job_post) as total_jobs,
  ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM job_post), 1) as coverage_pct
FROM job_dedupe_map;

-- Skill normalization usage
SELECT COUNT(*) FROM skill WHERE aliases != '{}';
SELECT COUNT(*) FROM skill WHERE taxonomy_ref IS NOT NULL;

-- Quality scoring coverage
SELECT
  COUNT(*) FILTER (WHERE quality_score IS NOT NULL) as with_score,
  COUNT(*) as total,
  ROUND(100.0 * COUNT(*) FILTER (WHERE quality_score IS NOT NULL) / COUNT(*), 1) as coverage_pct
FROM job_post;

-- Skill diversity (check for fragmentation)
SELECT name, COUNT(*) as job_count
FROM skill s
JOIN job_skill js ON s.id = js.skill_id
GROUP BY s.name
HAVING COUNT(*) > 50
ORDER BY COUNT(*) DESC
LIMIT 20;
```

**Expected issues if normalization is weak:**
- "Excel" has 500 jobs, "MS Excel" has 300 jobs, "Advanced Excel" has 150 jobs → Should be 950 total under "Excel"

---

## Priority Roadmap (Before Building User Products)

### Phase 0: Data Quality First (2-3 weeks)

**Week 1: Skill Normalization (CRITICAL)**
1. Expand `skill_mapping.json` to 200+ aliases
2. Add skill taxonomy reference (families: data_analysis, programming, cloud, etc.)
3. Build skill bundle definitions for match scoring
4. Re-run post-processing pipeline to normalize existing skills

**Week 2: Role Taxonomy Enhancement**
1. Implement seniority inference (parse titles for level keywords)
2. Expand TITLE_ALIASES to 50+ role families
3. Populate TitleNorm.family field
4. Re-run pipeline to classify existing jobs

**Week 3: Verification & Monitoring**
1. Run data volume queries (dedup coverage, skill fragmentation, quality scores)
2. Build quality monitoring dashboard (track coverage %, fragmentation %, dedup stats)
3. Add representativeness labels (source mix, location bias warnings)
4. Document data quality metrics for B2B clients

### THEN: Phase 1 User Products (LMI_IMPLEMENTATION_PLAN.md)

Once data is clean:
- Match scoring will be accurate (no undercounting due to synonym misses)
- Skill trends will be correct (no fragmentation)
- Salary intelligence will be segmented properly (by seniority)
- Career pathways will show real progression

---

## Conclusion

**Your infrastructure is 60% there.** The deduplication and quality scoring are solid. The critical gap is skill normalization - 25 aliases won't cut it for production LMI.

**Action:** Spend 2-3 weeks fixing normalization BEFORE building match scoring, skills gap scan, or salary intelligence. Otherwise, your LMI products will show inflated/fragmented data and users won't trust them.

**Rule of thumb applied:**
- Inconsistent/noisy LMI → **Normalization problem** ✅ Diagnosed
- Narrow coverage → Source diversity problem (check this next)

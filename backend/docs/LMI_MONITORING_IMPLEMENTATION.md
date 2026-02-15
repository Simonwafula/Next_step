# LMI Monitoring System - Implementation Summary

**Date:** 2026-02-15
**Status:** ✅ Production Ready

---

## What Was Built

### Core Monitoring Service

**File:** `app/services/lmi_monitoring.py`

Implements 5 key monitoring functions:

1. **`get_daily_scorecard()`** - The 10-point minimum scorecard
2. **`check_canonical_job_integrity()`** - Data integrity checks
3. **`check_skill_normalization()`** - Skill quality monitoring
4. **`check_seniority_coverage()`** - Seniority inference tracking
5. **`get_lmi_health_report()`** - Comprehensive health report

### Admin API Endpoints

**File:** `app/api/admin_routes.py`

Added 5 new monitoring endpoints:

| Endpoint | Function | Purpose |
|----------|----------|---------|
| `GET /api/admin/lmi-scorecard` | Daily/weekly scorecard | Track 10 key metrics |
| `GET /api/admin/lmi-health` | Full health report | Comprehensive overview |
| `GET /api/admin/lmi-integrity` | Integrity checks | Verify canonical records |
| `GET /api/admin/lmi-skills` | Skill quality | Detect fragmentation |
| `GET /api/admin/lmi-seniority` | Seniority coverage | Track inference |

### Test Coverage

**Files:**
- `tests/test_lmi_monitoring.py` - 8 test classes
- `tests/test_admin_processing_endpoints.py` - 5 new endpoint tests

**Coverage:**
- Scorecard structure ✓
- Integrity checks ✓
- Fragmentation detection ✓
- Seniority coverage ✓
- API endpoint responses ✓

---

## The 10-Point Scorecard

### What It Tracks Daily/Weekly

```json
{
  "date": "2026-02-15",
  "period_days": 1,
  "metrics": {
    "1_raw_postings_ingested": 500,
    "2_canonical_jobs_added": 350,
    "3_canonical_jobs_updated": 100,
    "4_dedupe_collapse_rate_by_source": [
      {
        "source": "brighter_monday",
        "raw_count": 200,
        "canonical_count": 140,
        "collapse_rate": 0.30
      }
    ],
    "5_pct_jobs_with_company": 85.0,
    "6_pct_jobs_with_role_family": 92.0,
    "7_pct_jobs_with_3plus_skills": 84.0,
    "8_error_rate_pct": 2.5,
    "9_block_detections": 0,
    "10_trend_spikes": []
  }
}
```

### How to Use It

**Daily Check (2 minutes):**
```bash
curl -X GET "http://localhost:8000/api/admin/lmi-scorecard?days_back=1" \
  -H "Authorization: Bearer YOUR_TOKEN" | jq
```

**What to Look For:**
- ✅ Raw postings > 0 (scraping working)
- ✅ Dedupe collapse 20-40% for boards (dedup working)
- ✅ Skill coverage > 80% (extraction working)
- ✅ Error rate < 5% (processing healthy)
- ✅ Trend spikes = [] (no anomalies)

**Weekly Deep Dive:**
```bash
curl -X GET "http://localhost:8000/api/admin/lmi-health" \
  -H "Authorization: Bearer YOUR_TOKEN" | jq
```

---

## Usage Examples

### Example 1: Check Daily Health

```bash
# Get yesterday's metrics
curl -X GET "http://localhost:8000/api/admin/lmi-scorecard?days_back=1" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Interpretation:**
- If `1_raw_postings_ingested` = 0 → Scrapers down
- If `4_dedupe_collapse_rate` near 0% → Dedup broken
- If `7_pct_jobs_with_3plus_skills` < 50% → Skill extraction failing
- If `10_trend_spikes` has entries → Investigate anomalies

### Example 2: Verify Skill Normalization

```bash
# Check for fragmentation
curl -X GET "http://localhost:8000/api/admin/lmi-skills" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Expected Response:**
```json
{
  "total_unique_skills": 350,
  "fragmentation_detected": [],
  "quality_status": "good"
}
```

**If fragmentation detected:**
```json
{
  "fragmentation_detected": [
    {
      "canonical": "excel",
      "found_variants": ["ms excel", "advanced excel"],
      "issue": "'excel' exists alongside variants"
    }
  ],
  "quality_status": "needs_improvement"
}
```

**Action:** Run skill re-normalization:
```bash
curl -X POST "http://localhost:8000/api/admin/renormalize-skills?limit=2000" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Example 3: Monitor Seniority Coverage

```bash
# Check seniority inference
curl -X GET "http://localhost:8000/api/admin/lmi-seniority" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Expected:**
```json
{
  "total_jobs": 5000,
  "with_seniority": 4500,
  "coverage_pct": 90.0,
  "status": "good"
}
```

**If < 80%:** Run post-processing to populate seniority:
```bash
curl -X POST "http://localhost:8000/api/admin/process?only_unprocessed=false&limit=2000" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Integration with Existing Tools

### Works With

- `/api/admin/quality` - Overall quality snapshot
- `/api/admin/process` - Post-ingestion processing
- `/api/admin/renormalize-skills` - Skill re-normalization
- Skill normalization (351 aliases)
- Seniority inference (5 levels)
- Deduplication service (3 strategies)

### Complements

- `scripts/verify_data_quality.py` - Offline verification
- `docs/DATA_QUALITY_VERIFICATION.md` - Manual SQL queries
- `docs/LMI_QA_MONITORING_CHECKLIST.md` - Full checklist

---

## Monitoring Schedule

### Daily (Automated)

**Set up cron job:**
```bash
# Every day at 8am, fetch scorecard and alert on anomalies
0 8 * * * /usr/local/bin/check_lmi_scorecard.sh
```

**Script example:**
```bash
#!/bin/bash
SCORECARD=$(curl -s -X GET "http://localhost:8000/api/admin/lmi-scorecard" \
  -H "Authorization: Bearer ${ADMIN_TOKEN}")

# Check for trend spikes
SPIKES=$(echo "$SCORECARD" | jq '.metrics["10_trend_spikes"] | length')
if [ "$SPIKES" -gt 0 ]; then
  echo "ALERT: Trend spikes detected!"
  echo "$SCORECARD" | jq '.metrics["10_trend_spikes"]'
fi

# Check error rate
ERROR_RATE=$(echo "$SCORECARD" | jq '.metrics["8_error_rate_pct"]')
if (( $(echo "$ERROR_RATE > 10" | bc -l) )); then
  echo "ALERT: High error rate: ${ERROR_RATE}%"
fi
```

### Weekly (Manual Review)

1. **Monday 9am:** Full health report
2. **Wednesday:** Skills fragmentation check
3. **Friday:** Review week's scorecard trends

### Monthly (Deep Dive)

1. Run full LMI health report
2. Verify all integrity checks pass
3. Check skill normalization quality
4. Review seniority distribution
5. Audit dedupe collapse rates per source

---

## Alert Thresholds

### Critical (Immediate Action)

| Metric | Threshold | Action |
|--------|-----------|--------|
| Raw postings | = 0 for 2+ days | Check scrapers |
| Error rate | > 20% | Check processing pipeline |
| Skill coverage | < 50% | Re-run skill extraction |
| Integrity checks | Any `false` | Investigate data corruption |

### Warning (Review Within 24h)

| Metric | Threshold | Action |
|--------|-----------|--------|
| Dedupe collapse | < 10% or > 60% | Review dedup config |
| Skill coverage | 50-80% | Consider re-processing |
| Seniority coverage | < 80% | Re-run processing |
| Trend spikes | Any detected | Investigate cause |

### Info (Weekly Review)

| Metric | Threshold | Note |
|--------|-----------|------|
| Company coverage | < 80% | Improve normalization |
| Role family coverage | < 80% | Expand taxonomy |
| Block detections | > 0 | Update scrapers |

---

## What's Still Manual

### Priority 1 (Should Automate)

1. **Block/Captcha Detection**
   - Currently: Manual check
   - Should: Automated detection + alerting

2. **Golden Dataset Regression**
   - Currently: No dataset
   - Should: 200 known cases + automated tests

3. **Posted Date Extraction**
   - Currently: Using scrape dates
   - Should: Extract "Posted X days ago"

### Priority 2 (Can Stay Manual)

1. **Same Job Across Sources Test**
   - Curated test set of known duplicates
   - Run manually after dedup changes

2. **Source Quality Tiers**
   - Label sources by quality/reliability
   - Update quarterly

3. **Dead Link Validation**
   - Check `application_url` HTTP status
   - Run monthly

---

## Success Metrics

### Before Implementation

- ❌ No automated monitoring
- ❌ Manual SQL queries required
- ❌ No daily scorecard
- ❌ No fragmentation detection
- ❌ No seniority tracking

### After Implementation

- ✅ 10-point daily scorecard automated
- ✅ 5 admin API endpoints
- ✅ Automated fragmentation detection
- ✅ Seniority coverage tracking
- ✅ Comprehensive health reports
- ✅ Test coverage for all checks
- ✅ Clear alerts and thresholds

### Impact

**Time Savings:**
- Manual checks: 1-2 hours/week → 5 minutes/week
- Faster issue detection (daily vs weekly)
- Automated anomaly alerts

**Quality Improvements:**
- Clear visibility into data health
- Proactive issue detection
- Reproducible metrics

---

## Files Created/Modified

### New Files

1. `app/services/lmi_monitoring.py` - Core monitoring service
2. `tests/test_lmi_monitoring.py` - Service tests
3. `docs/LMI_QA_MONITORING_CHECKLIST.md` - Full QA checklist
4. `docs/LMI_MONITORING_IMPLEMENTATION.md` - This document

### Modified Files

1. `app/api/admin_routes.py` - Added 5 endpoints
2. `tests/test_admin_processing_endpoints.py` - Added endpoint tests

---

## Next Steps

### Immediate (This Week)

1. ✅ Deploy monitoring service
2. ✅ Test all endpoints
3. Set up daily cron job for scorecard
4. Document alerting thresholds

### Short Term (This Month)

1. Implement block/captcha detection
2. Create golden dataset (200 test cases)
3. Add posted_at extraction
4. Set up automated alerting

### Long Term (This Quarter)

1. Source quality tiers
2. Dead link validation
3. Canary source monitoring
4. ML-based anomaly detection

---

**Status:** ✅ Ready for Production

The monitoring infrastructure is complete and provides clear visibility into LMI system health. The 10-point scorecard gives daily insights, and comprehensive checks ensure data quality is maintained.

# VPS Deployment: Job Data Migration

## Overview

Migrate 102,169 jobs from local SQLite to VPS PostgreSQL database.

---

## Step 1: Upload JSON to VPS

From your LOCAL machine:

```bash
# Upload the migration file to VPS
scp backend/data/migration/jobs_export.json user@nextstep.co.ke:/home/nextstep.co.ke/
```

**Note:** The file is 688 MB. Upload may take 10-20 minutes.

---

## Step 2: Upload Import Script to VPS

```bash
# Upload the import script
scp backend/scripts/import_jobs_to_db.py user@nextstep.co.ke:/home/nextstep.co.ke/nextstep/backend/scripts/
```

---

## Step 3: SSH to VPS and Run Import

```bash
# SSH to VPS
ssh user@nextstep.co.ke

# Navigate to app directory
cd /home/nextstep.co.ke/nextstep/backend

# Activate virtual environment
source .venv/bin/activate

# Run import (this will use PostgreSQL via DATABASE_URL env var)
python scripts/import_jobs_to_db.py --input /home/nextstep.co.ke/jobs_export.json --batch-size 2000
```

---

## Step 4: Verify Import

```bash
# Connect to PostgreSQL
psql -d nextstep

# Check counts
SELECT COUNT(*) FROM job_post;
SELECT COUNT(*) FROM organization;
SELECT COUNT(*) FROM location;

# Sample data
SELECT title_raw, seniority, education FROM job_post LIMIT 5;

# Exit psql
\q
```

Expected output:
```
 job_post: 102,169 rows
 organization: ~2,933 rows
 location: ~925 rows
```

---

## Step 5: Restart Backend Service

```bash
sudo systemctl restart nextstep-backend
```

---

## Step 6: Test API

```bash
# Test search endpoint
curl https://nextstep.co.ke/api/search?q=data%20analyst

# Test health endpoint
curl https://nextstep.co.ke/health
```

---

## Troubleshooting

### Error: "relation 'job_post' does not exist"
The tables need to be created first. Run migrations:
```bash
cd /home/nextstep.co.ke/nextstep/backend
source .venv/bin/activate
alembic upgrade head
```

### Error: "permission denied"
Make sure the files are owned by the correct user:
```bash
sudo chown -R nextstep.co.ke:nextstep.co.ke /home/nextstep.co.ke/nextstep
```

### Error: "disk quota exceeded"
Check available disk space:
```bash
df -h
```
The JSON file is 688 MB, and PostgreSQL will need additional space for indexes.

---

## Quick Reference

| File | Size | Location |
|------|------|----------|
| jobs_export.json | 688 MB | `backend/data/migration/jobs_export.json` (local) |
| import_jobs_to_db.py | ~15 KB | `backend/scripts/import_jobs_to_db.py` |

---

## Alternative: Direct Database Copy (Faster)

If you have direct PostgreSQL access:

```bash
# On LOCAL machine, convert JSON to SQL
python scripts/import_jobs_to_db.py --input ./data/migration/jobs_export.json --output-sql

# Upload SQL file
scp data/migration/jobs_import.sql user@nextstep.co.ke:/home/nextstep.co.ke/

# On VPS, import directly
psql -d nextstep -f /home/nextstep.co.ke/jobs_import.sql
```

---

*Last updated: February 14, 2026*

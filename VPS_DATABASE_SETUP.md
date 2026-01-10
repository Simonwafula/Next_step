# PostgreSQL Setup on VPS (CyberPanel)

**For**: NextStep LMI Platform
**VPS**: Ubuntu with CyberPanel
**Domain**: nextstep.co.ke
**Database**: PostgreSQL 16 + pgvector extension

---

## Option 1: PostgreSQL Setup on Your VPS (Recommended)

### Why Use VPS Database?
✅ **Pros**:
- Full control over database
- No monthly fees beyond VPS cost
- Lower latency (database on same server as app)
- No external dependencies
- Better for data sovereignty

❌ **Cons**:
- You manage backups
- You manage performance tuning
- Shares resources with app server

**Recommended if**: Your VPS has 4GB+ RAM and you want full control

---

## Step-by-Step PostgreSQL Setup

### 1. Install PostgreSQL 16 + pgvector

```bash
# SSH into your VPS
ssh root@nextstep.co.ke

# Add PostgreSQL repository
sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'

# Import repository signing key
wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -

# Update package list
sudo apt update

# Install PostgreSQL 16
sudo apt install -y postgresql-16 postgresql-contrib-16 postgresql-16-pgvector

# Verify installation
psql --version
# Expected: psql (PostgreSQL) 16.x
```

**Installation Time**: 5-10 minutes

---

### 2. Configure PostgreSQL for Production

#### Update PostgreSQL Configuration

```bash
# Edit PostgreSQL config
sudo nano /etc/postgresql/16/main/postgresql.conf
```

**Add/Update these settings**:

```conf
# Connection Settings
listen_addresses = 'localhost'          # Only accept local connections (secure)
max_connections = 100                   # Adjust based on your needs

# Memory Settings (for 4GB RAM VPS - adjust if different)
shared_buffers = 256MB                  # 25% of RAM for small VPS
effective_cache_size = 1GB              # 50-75% of RAM
work_mem = 4MB                          # Per query operation
maintenance_work_mem = 64MB             # For VACUUM, CREATE INDEX

# Checkpoint Settings
checkpoint_completion_target = 0.9
wal_buffers = 16MB

# Query Planning
random_page_cost = 1.1                  # For SSD storage
effective_io_concurrency = 200          # For SSD storage

# Logging (important for debugging)
logging_collector = on
log_directory = 'log'
log_filename = 'postgresql-%Y-%m-%d_%H%M%S.log'
log_statement = 'ddl'                   # Log schema changes
log_line_prefix = '%m [%p] %u@%d '
```

**For 8GB RAM VPS, use**:
```conf
shared_buffers = 512MB
effective_cache_size = 3GB
work_mem = 8MB
maintenance_work_mem = 128MB
```

**For 2GB RAM VPS, use**:
```conf
shared_buffers = 128MB
effective_cache_size = 512MB
work_mem = 2MB
maintenance_work_mem = 32MB
```

#### Update Authentication Settings

```bash
sudo nano /etc/postgresql/16/main/pg_hba.conf
```

**Add this line** (before other rules):
```conf
# Allow local connections with password
local   all             all                                     md5
host    all             all             127.0.0.1/32            md5
host    all             all             ::1/128                 md5
```

#### Restart PostgreSQL

```bash
sudo systemctl restart postgresql
sudo systemctl enable postgresql  # Start on boot

# Verify it's running
sudo systemctl status postgresql
```

---

### 3. Create Database and User

```bash
# Switch to postgres user
sudo -u postgres psql

# Run these SQL commands:
```

```sql
-- Create database
CREATE DATABASE nextstep_lmi;

-- Create user with strong password
CREATE USER nextstep_user WITH PASSWORD 'your_very_secure_password_here_change_this';

-- Grant all privileges on database
GRANT ALL PRIVILEGES ON DATABASE nextstep_lmi TO nextstep_user;

-- Connect to the database
\c nextstep_lmi

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Grant schema permissions
GRANT ALL ON SCHEMA public TO nextstep_user;

-- Exit
\q
```

**Security Note**: Use a strong password! Generate one with:
```bash
openssl rand -base64 32
```

---

### 4. Verify Database Setup

```bash
# Test connection as nextstep_user
psql -U nextstep_user -d nextstep_lmi -h localhost

# Should prompt for password, then show:
# nextstep_lmi=>

# Test pgvector extension
\dx
# Should show "vector" extension

# Exit
\q
```

✅ **If you can connect and see the vector extension, you're good!**

---

### 5. Update Your Application .env File

```bash
cd /home/nextstep.co.ke/public_html/backend

# Edit .env file
nano .env
```

**Update database settings**:
```bash
# Database Configuration
DATABASE_URL=postgresql://nextstep_user:your_very_secure_password_here_change_this@localhost:5432/nextstep_lmi

# Individual settings (for backwards compatibility)
POSTGRES_USER=nextstep_user
POSTGRES_PASSWORD=your_very_secure_password_here_change_this
POSTGRES_DB=nextstep_lmi
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
```

---

### 6. Run Database Migrations

```bash
cd /home/nextstep.co.ke/public_html/backend

# Activate virtual environment (if using one)
source venv/bin/activate

# Run Alembic migrations
alembic upgrade head

# Expected output:
# INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
# INFO  [alembic.runtime.migration] Will assume transactional DDL.
# INFO  [alembic.runtime.migration] Running upgrade  -> 001_dedup_fields, add deduplication fields to job_post
```

#### If Alembic Isn't Set Up Yet:

```bash
# Initialize Alembic
alembic init alembic

# Edit alembic.ini
nano alembic.ini
# Change: sqlalchemy.url = postgresql://nextstep_user:password@localhost:5432/nextstep_lmi

# Edit alembic/env.py
nano alembic/env.py
# Add near the top:
# from app.db.models import Base
# target_metadata = Base.metadata

# Create initial migration
alembic revision --autogenerate -m "initial migration"

# Apply migration
alembic upgrade head
```

**Alternative: Run SQL Directly**:
```bash
psql -U nextstep_user -d nextstep_lmi -h localhost < backend/migrations/add_deduplication_fields.sql
```

---

### 7. Test Database Connection from Application

```bash
cd /home/nextstep.co.ke/public_html/backend

# Create test script
nano test_db.py
```

```python
import asyncio
from app.db.database import engine, SessionLocal
from app.db.models import Organization

async def test_connection():
    """Test database connection"""
    try:
        # Test sync connection
        db = SessionLocal()

        # Try to create a test organization
        test_org = Organization(
            name="Test Company",
            sector="Technology",
            verified=False
        )
        db.add(test_org)
        db.commit()
        db.refresh(test_org)

        print(f"✅ Database connection successful!")
        print(f"✅ Created test organization with ID: {test_org.id}")

        # Clean up
        db.delete(test_org)
        db.commit()
        db.close()

        print("✅ Database is ready!")

    except Exception as e:
        print(f"❌ Database connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_connection())
```

```bash
# Run test
python test_db.py

# Expected output:
# ✅ Database connection successful!
# ✅ Created test organization with ID: 1
# ✅ Database is ready!
```

---

### 8. Set Up Automated Backups

#### Create Backup Script

```bash
sudo mkdir -p /home/backups/nextstep
sudo nano /usr/local/bin/backup-nextstep-db.sh
```

```bash
#!/bin/bash
# PostgreSQL Backup Script for NextStep LMI

BACKUP_DIR="/home/backups/nextstep"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="nextstep_lmi"
DB_USER="nextstep_user"

# Create backup directory if it doesn't exist
mkdir -p $BACKUP_DIR

# Backup database (plain SQL format)
echo "Starting backup at $DATE..."
PGPASSWORD='your_very_secure_password_here_change_this' pg_dump \
    -U $DB_USER \
    -h localhost \
    -d $DB_NAME \
    -F p \
    -f $BACKUP_DIR/nextstep_db_$DATE.sql

# Compress backup
gzip $BACKUP_DIR/nextstep_db_$DATE.sql

# Keep only last 7 days of backups
find $BACKUP_DIR -name "nextstep_db_*.sql.gz" -mtime +7 -delete

echo "Backup completed: nextstep_db_$DATE.sql.gz"

# Optional: Upload to cloud storage (S3, Google Cloud, etc.)
# aws s3 cp $BACKUP_DIR/nextstep_db_$DATE.sql.gz s3://your-bucket/backups/
```

```bash
sudo chmod +x /usr/local/bin/backup-nextstep-db.sh

# Test backup
sudo /usr/local/bin/backup-nextstep-db.sh

# Check backup was created
ls -lh /home/backups/nextstep/
```

#### Schedule Daily Backups

```bash
# Edit crontab
sudo crontab -e

# Add this line (runs at 2 AM daily)
0 2 * * * /usr/local/bin/backup-nextstep-db.sh >> /var/log/nextstep-backup.log 2>&1

# Verify crontab
sudo crontab -l
```

---

### 9. Restore from Backup (If Needed)

```bash
# List available backups
ls -lh /home/backups/nextstep/

# Restore from backup
cd /home/backups/nextstep

# Uncompress backup
gunzip nextstep_db_20260108_020001.sql.gz

# Restore to database
PGPASSWORD='your_password' psql \
    -U nextstep_user \
    -h localhost \
    -d nextstep_lmi \
    < nextstep_db_20260108_020001.sql

echo "Database restored successfully!"
```

---

### 10. Performance Monitoring

#### Monitor Database Size

```bash
# Check database size
sudo -u postgres psql -c "SELECT pg_size_pretty(pg_database_size('nextstep_lmi'));"

# Check table sizes
sudo -u postgres psql -d nextstep_lmi -c "
SELECT
    schemaname || '.' || tablename AS table,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
LIMIT 10;"
```

#### Monitor Active Connections

```bash
sudo -u postgres psql -c "SELECT count(*) as active_connections FROM pg_stat_activity;"
```

#### Monitor Slow Queries

```bash
# Edit postgresql.conf to log slow queries
sudo nano /etc/postgresql/16/main/postgresql.conf

# Add:
log_min_duration_statement = 1000  # Log queries taking > 1 second

# Restart PostgreSQL
sudo systemctl restart postgresql

# View slow queries
sudo tail -f /var/log/postgresql/postgresql-16-main.log
```

---

### 11. Security Hardening

#### Secure PostgreSQL

```bash
# 1. Ensure PostgreSQL only listens on localhost
sudo nano /etc/postgresql/16/main/postgresql.conf
# Verify: listen_addresses = 'localhost'

# 2. Firewall (ensure PostgreSQL port 5432 is not exposed)
sudo ufw status
# Port 5432 should NOT be listed (only 22, 80, 443, 8000)

# 3. Strong password policy
# Already set during user creation

# 4. Regular updates
sudo apt update
sudo apt upgrade postgresql-16
```

#### Enable SSL Connections (Optional but Recommended)

```bash
# Generate self-signed certificate
sudo -u postgres openssl req -new -x509 -days 365 -nodes \
    -text -out /etc/postgresql/16/main/server.crt \
    -keyout /etc/postgresql/16/main/server.key \
    -subj "/CN=nextstep.co.ke"

sudo chmod 600 /etc/postgresql/16/main/server.key
sudo chown postgres:postgres /etc/postgresql/16/main/server.*

# Enable SSL in postgresql.conf
sudo nano /etc/postgresql/16/main/postgresql.conf
# Add: ssl = on

# Restart PostgreSQL
sudo systemctl restart postgresql
```

---

### 12. Migrate Data from jobs.sqlite3

Once PostgreSQL is set up, migrate your 102K jobs:

```bash
cd /home/nextstep.co.ke/public_html/backend

# Create migration script
nano migrate_sqlite_to_postgres.py
```

```python
"""
Migrate data from jobs.sqlite3 to PostgreSQL
"""
import sqlite3
import asyncio
from app.db.database import SessionLocal
from app.processors.data_cleaner import JobDataCleaner
from app.processors.database_saver import JobDatabaseSaver
from app.services.deduplication_service import deduplication_service

async def migrate_jobs():
    """Migrate jobs from SQLite to PostgreSQL"""

    # Connect to SQLite
    sqlite_conn = sqlite3.connect('/Users/hp/.../jobs.sqlite3')
    sqlite_cursor = sqlite_conn.cursor()

    # Get total count
    total = sqlite_cursor.execute("SELECT COUNT(*) FROM jobs_data").fetchone()[0]
    print(f"Found {total} jobs to migrate")

    # Process in batches
    batch_size = 100
    offset = 0
    processed = 0
    duplicates = 0
    errors = 0

    cleaner = JobDataCleaner()
    saver = JobDatabaseSaver()
    db = SessionLocal()

    while offset < total:
        # Fetch batch
        sqlite_cursor.execute(
            "SELECT id, full_link, title, content FROM jobs_data LIMIT ? OFFSET ?",
            (batch_size, offset)
        )
        batch = sqlite_cursor.fetchall()

        for row in batch:
            try:
                job_id, url, title, content = row

                # Check for duplicate
                dup_result = await deduplication_service.find_all_duplicates(
                    db=db,
                    url=url,
                    title=title,
                    content=content[:500]  # First 500 chars for similarity check
                )

                if dup_result['is_duplicate']:
                    duplicates += 1
                    continue

                # Parse and clean data
                raw_data = {
                    'url': url,
                    'title': title,
                    'content': content,
                    'source': 'migration',
                    'extracted_at': datetime.utcnow()
                }

                cleaned_data = cleaner.clean_job_data(raw_data)

                # Save to PostgreSQL
                job_id = saver.save_job_data(cleaned_data)

                if job_id:
                    processed += 1
                else:
                    errors += 1

            except Exception as e:
                print(f"Error processing job {job_id}: {e}")
                errors += 1
                continue

        offset += batch_size
        print(f"Progress: {offset}/{total} ({processed} new, {duplicates} duplicates, {errors} errors)")

    sqlite_conn.close()
    db.close()

    print(f"\nMigration complete!")
    print(f"Total jobs: {total}")
    print(f"New jobs saved: {processed}")
    print(f"Duplicates skipped: {duplicates}")
    print(f"Errors: {errors}")

if __name__ == "__main__":
    asyncio.run(migrate_jobs())
```

```bash
# Run migration (this will take 30-60 minutes for 102K jobs)
python migrate_sqlite_to_postgres.py
```

---

## Database Performance Benchmarks

**Expected Performance (4GB RAM VPS)**:
- 100K job records: ~500MB database size
- Simple queries: <10ms
- Complex searches: 50-200ms
- Embeddings search: 100-500ms (with indexes)
- Concurrent connections: 50-100

**Monitor with**:
```bash
sudo -u postgres psql -d nextstep_lmi -c "
SELECT
    query,
    calls,
    mean_exec_time,
    max_exec_time
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;"
```

---

## Troubleshooting

### Issue: "peer authentication failed"
**Solution**:
```bash
sudo nano /etc/postgresql/16/main/pg_hba.conf
# Change: local all all peer
# To: local all all md5
sudo systemctl restart postgresql
```

### Issue: "could not connect to server"
**Solution**:
```bash
# Check if PostgreSQL is running
sudo systemctl status postgresql

# Check if port is listening
sudo netstat -plnt | grep 5432

# Restart PostgreSQL
sudo systemctl restart postgresql
```

### Issue: Out of Memory
**Solution**:
```bash
# Reduce shared_buffers in postgresql.conf
sudo nano /etc/postgresql/16/main/postgresql.conf
# Set: shared_buffers = 128MB (for 2GB VPS)
sudo systemctl restart postgresql
```

### Issue: Slow Queries
**Solution**:
```bash
# Add indexes
sudo -u postgres psql -d nextstep_lmi
CREATE INDEX idx_job_post_url_hash ON job_post(url_hash);
CREATE INDEX idx_job_post_first_seen ON job_post(first_seen);
CREATE INDEX idx_job_post_org_id ON job_post(org_id);
```

---

## Next Steps

1. ✅ PostgreSQL installed and configured
2. ✅ Database and user created
3. ✅ pgvector extension enabled
4. ✅ Migrations applied
5. ✅ Backups scheduled
6. [ ] Migrate jobs.sqlite3 data (102K jobs)
7. [ ] Test application with PostgreSQL
8. [ ] Monitor performance
9. [ ] Scale as needed

---

## VPS Resource Recommendations

**Minimum**: 2GB RAM, 1 CPU, 20GB SSD
- Can handle 50K jobs
- Good for development/testing

**Recommended**: 4GB RAM, 2 CPU, 40GB SSD
- Can handle 100K-200K jobs
- Good for production (small-medium scale)

**Optimal**: 8GB RAM, 4 CPU, 80GB SSD
- Can handle 500K+ jobs
- Good for production (large scale)

**Current VPS**: Check with `free -h` and `df -h`

---

## Cost Comparison

**VPS Database (PostgreSQL on your server)**:
- Cost: $0 (included in VPS)
- Storage: Limited by VPS disk
- Maintenance: You manage

**vs Cloud Database (Supabase/Railway)**:
- Cost: $25-50/month
- Storage: Scalable
- Maintenance: Managed for you

**Recommendation**: Start with VPS database, migrate to cloud if you outgrow VPS resources.

---

**Setup Time**: 30-45 minutes
**Difficulty**: Medium
**Status**: Production-ready ✅

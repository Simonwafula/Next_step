# Operations

Consolidated documentation.

## Runbook

Operational procedures and triage steps live in `docs/runbook.md`. Keep it in sync with incremental update, monitoring, and regression-test changes (T-601 to T-604).

## NextStep Career Platform - CyberPanel Deployment Guide

This guide provides deployment instructions for the NextStep Career Platform on a VPS with CyberPanel already configured.

### Production Hosting Context

- **Domain**: `nextstep.co.ke` (already provisioned in CyberPanel)
- **Server access**: `ssh root@57.217.62.77` (use your saved passphrase) and switch to `nexts7595` for day-to-day operations
- **Application root**: `/home/nextstep.co.ke/public_html` (the Git working tree)
- **Runtime assets**: production `.env` and `.venv` live at `/home/nextstep.co.ke/.env` and `/home/nextstep.co.ke/.venv`; keep them owned by `nexts7595`
- **Repository permissions**: ensure `/home/nextstep.co.ke/public_html` is owned by `nexts7595:nexts7595` so automated updates stay writable

### Current VPS Status

✅ **VPS Setup Complete**
- Ubuntu server with CyberPanel installed and configured
- Domain: nextstep.co.ke
- SSL certificates configured
- Basic web server functionality operational

### Prerequisites Met

- ✅ VPS with CyberPanel installed
- ✅ Domain configured (nextstep.co.ke)
- ✅ SSL certificates active
- ✅ Basic server infrastructure ready

### Deployment Steps

#### 1. Application Deployment

##### Clone Latest Repository
```bash
cd /home/nextstep.co.ke/public_html
git pull origin main
```

##### One-shot Production Bootstrap (optional)

If you want a single command to prepare the database, Redis, systemd services, migrations, and the Python environment, run:

```bash
cd /home/nextstep.co.ke/public_html
sudo AUTO_INSTALL=1 bash scripts/bootstrap_prod.sh
```

Set `AUTO_INSTALL=1` only if you want the script to install missing packages (PostgreSQL/Redis). Otherwise omit it to fail fast.

##### Bootstrap Python Environment (run once as `nexts7595`)

```bash
cd /home/nextstep.co.ke/public_html
bash scripts/setup_prod_environment.sh
```

The script installs dependencies into `/home/nextstep.co.ke/.venv` and verifies the repo sits under the expected path. Keep your `.env` at `/home/nextstep.co.ke/.env` before running this helper.

##### Configure Environment Variables
```bash
## Update the shared production environment file
cp .env.example /home/nextstep.co.ke/.env
nano /home/nextstep.co.ke/.env
## Load the variables for one-off commands
set -o allexport
source /home/nextstep.co.ke/.env
set +o allexport
```

**Required Environment Variables:**
```bash
## Application Configuration
APP_ENV=production
APP_HOST=0.0.0.0
APP_PORT=8000
CORS_ORIGINS=https://nextstep.co.ke

## Domain Configuration
DOMAIN=nextstep.co.ke
API_DOMAIN=api.nextstep.co.ke
WEBSITE_URL=https://nextstep.co.ke
API_BASE_URL=https://api.nextstep.co.ke

## Database Configuration (CyberPanel PostgreSQL)
POSTGRES_USER=nextstep_user
POSTGRES_PASSWORD=your_secure_password
POSTGRES_DB=career_lmi
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

## Redis Configuration
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

## API Keys
OPENAI_API_KEY=your_openai_api_key
TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_token
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886

## LinkedIn Integration
LINKEDIN_CLIENT_ID=your_linkedin_client_id
LINKEDIN_CLIENT_SECRET=your_linkedin_client_secret

## Google Calendar Integration
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret

## Microsoft Calendar Integration
MICROSOFT_CLIENT_ID=your_microsoft_client_id
MICROSOFT_CLIENT_SECRET=your_microsoft_client_secret

## Security
SECRET_KEY=your_very_secure_secret_key_here
```

#### 2. Database Setup

##### Create Database and User
```bash
## Access PostgreSQL (via CyberPanel or command line)
sudo -u postgres psql

## Create database and user
CREATE DATABASE career_lmi;
CREATE USER nextstep_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE career_lmi TO nextstep_user;
\q
```

##### Run Database Migrations
```bash
cd /home/nextstep.co.ke/public_html/backend
python -m alembic upgrade head
```
If `alembic.ini` is not present in the repo, run:
```bash
cd /home/nextstep.co.ke/public_html/backend
python -c "from app.db.database import init_db; init_db()"
```

#### 3. Install Dependencies

##### Backend Dependencies
```bash
cd /home/nextstep.co.ke/public_html/backend
source /home/nextstep.co.ke/.venv/bin/activate
pip install -r requirements.txt
```

##### Install Redis (if not already installed)
```bash
sudo apt update
sudo apt install redis-server -y
sudo systemctl enable redis-server
sudo systemctl start redis-server
```

#### 4. Configure Services

##### Create Systemd Service for FastAPI Backend
```bash
sudo nano /etc/systemd/system/nextstep-backend.service
```

```ini
[Unit]
Description=NextStep Career Platform Backend
After=network.target

[Service]
Type=simple
User=nexts7595
WorkingDirectory=/home/nextstep.co.ke/public_html/backend
EnvironmentFile=/home/nextstep.co.ke/.env
Environment=PATH=/home/nextstep.co.ke/.venv/bin:/usr/local/bin:/usr/bin
ExecStart=/home/nextstep.co.ke/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always

[Install]
WantedBy=multi-user.target
```

##### Create Systemd Service for Celery Worker
```bash
sudo nano /etc/systemd/system/nextstep-celery.service
```

```ini
[Unit]
Description=NextStep Celery Worker
After=network.target redis.service

[Service]
Type=simple
User=nexts7595
WorkingDirectory=/home/nextstep.co.ke/public_html/backend
EnvironmentFile=/home/nextstep.co.ke/.env
Environment=PATH=/home/nextstep.co.ke/.venv/bin:/usr/local/bin:/usr/bin
ExecStart=/home/nextstep.co.ke/.venv/bin/celery -A app.core.celery_app worker --loglevel=info
Restart=always

[Install]
WantedBy=multi-user.target
```

##### Create Systemd Service for Celery Beat (Scheduler)
```bash
sudo nano /etc/systemd/system/nextstep-celery-beat.service
```

```ini
[Unit]
Description=NextStep Celery Beat Scheduler
After=network.target redis.service

[Service]
Type=simple
User=nexts7595
WorkingDirectory=/home/nextstep.co.ke/public_html/backend
EnvironmentFile=/home/nextstep.co.ke/.env
Environment=PATH=/home/nextstep.co.ke/.venv/bin:/usr/local/bin:/usr/bin
ExecStart=/home/nextstep.co.ke/.venv/bin/celery -A app.core.celery_app beat --loglevel=info
Restart=always

[Install]
WantedBy=multi-user.target
```

##### Enable and Start Services
```bash
sudo systemctl daemon-reload
sudo systemctl enable nextstep-backend
sudo systemctl enable nextstep-celery
sudo systemctl enable nextstep-celery-beat

sudo systemctl start nextstep-backend
sudo systemctl start nextstep-celery
sudo systemctl start nextstep-celery-beat
```

#### 5. Configure CyberPanel Reverse Proxy

##### Update CyberPanel Virtual Host Configuration
1. Access CyberPanel admin panel
2. Go to Websites → List Websites
3. Select nextstep.co.ke
4. Configure reverse proxy for API endpoints:

**API Proxy Configuration:**
- Path: `/api/`
- Destination: `http://localhost:8000/`
- Enable proxy headers

#### 6. Frontend Deployment

##### Build and Deploy Frontend
```bash
cd /home/nextstep.co.ke/public_html/frontend

## Ensure static files are properly served
## Update any API endpoints in JavaScript files to use production URLs
```

#### 7. Automated Workflow System Setup

##### Test Scraper Configurations
```bash
cd /home/nextstep.co.ke/public_html/backend
python test_automated_workflow.py
```

##### Verify Celery Tasks
```bash
## Check Celery worker status
sudo systemctl status nextstep-celery

## Check Celery beat scheduler
sudo systemctl status nextstep-celery-beat

## Monitor Celery tasks
celery -A app.core.celery_app events
```

#### 8. Integration Setup

##### LinkedIn Integration
1. Configure LinkedIn OAuth app in LinkedIn Developer Console
2. Set redirect URI: `https://nextstep.co.ke/api/integration/linkedin/callback`
3. Update environment variables with client credentials

##### Calendar Integration
1. **Google Calendar:**
   - Configure Google Cloud Console OAuth app
   - Set redirect URI: `https://nextstep.co.ke/api/integration/calendar/google/callback`

2. **Microsoft Calendar:**
   - Configure Azure AD app registration
   - Set redirect URI: `https://nextstep.co.ke/api/integration/calendar/microsoft/callback`

##### ATS Integration
1. Configure webhook endpoints for supported ATS platforms
2. Set webhook URLs:
   - Greenhouse: `https://nextstep.co.ke/api/integration/ats/greenhouse/webhook`
   - Lever: `https://nextstep.co.ke/api/integration/ats/lever/webhook`

#### 9. Monitoring and Maintenance

##### Service Status Monitoring
```bash
## Check all services
sudo systemctl status nextstep-backend
sudo systemctl status nextstep-celery
sudo systemctl status nextstep-celery-beat
sudo systemctl status redis-server

## View service logs
sudo journalctl -u nextstep-backend -f
sudo journalctl -u nextstep-celery -f
```

##### Application Updates
```bash
## Update application
cd /home/nextstep.co.ke/public_html
git pull origin main

## Restart services
sudo systemctl restart nextstep-backend
sudo systemctl restart nextstep-celery
sudo systemctl restart nextstep-celery-beat

## Run any new migrations
cd backend
python -m alembic upgrade head
```

##### Database Backup
```bash
## Create automated backup script
sudo nano /usr/local/bin/backup-nextstep.sh
```

```bash
##!/bin/bash
BACKUP_DIR="/home/backups/nextstep"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

## Backup database
pg_dump -U nextstep_user -h localhost career_lmi > $BACKUP_DIR/db_backup_$DATE.sql

## Backup application files
tar -czf $BACKUP_DIR/app_backup_$DATE.tar.gz /home/nextstep.co.ke/public_html

## Keep only last 7 days of backups
find $BACKUP_DIR -name "*.sql" -mtime +7 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete
```

```bash
sudo chmod +x /usr/local/bin/backup-nextstep.sh

## Add to crontab for daily backups
sudo crontab -e
## Add: 0 2 * * * /usr/local/bin/backup-nextstep.sh
```

#### 10. Performance Optimization

##### Redis Configuration
```bash
sudo nano /etc/redis/redis.conf

## Optimize for production
maxmemory 256mb
maxmemory-policy allkeys-lru
```

##### PostgreSQL Optimization
```bash
sudo nano /etc/postgresql/*/main/postgresql.conf

## Basic optimizations
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 4MB
maintenance_work_mem = 64MB
```

#### 11. Security Considerations

##### Firewall Configuration (if not managed by CyberPanel)
```bash
## Allow necessary ports
sudo ufw allow 80
sudo ufw allow 443
sudo ufw allow 8000  # FastAPI backend
sudo ufw allow 22    # SSH
```

##### SSL Certificate Renewal
- CyberPanel should handle SSL certificate renewal automatically
- Monitor certificate expiration dates

#### 12. Troubleshooting

##### Common Issues and Solutions

1. **Service Won't Start:**
   ```bash
   sudo journalctl -u nextstep-backend -n 50
   ```

2. **Database Connection Issues:**
   ```bash
   # Test database connection
   psql -U nextstep_user -h localhost -d career_lmi
   ```

3. **Celery Tasks Not Running:**
   ```bash
   # Check Redis connection
   redis-cli ping
   
   # Check Celery worker logs
   sudo journalctl -u nextstep-celery -f
   ```

4. **API Not Accessible:**
   - Verify CyberPanel reverse proxy configuration
   - Check FastAPI service status
   - Review nginx/OpenLiteSpeed logs

##### Health Check Endpoints
- Backend Health: `https://nextstep.co.ke/api/health`
- Workflow Status: `https://nextstep.co.ke/api/workflow/workflow-status`

#### 13. Next Steps

1. **Monitor System Performance:**
   - Set up monitoring for CPU, memory, and disk usage
   - Monitor application logs for errors

2. **Test All Integrations:**
   - LinkedIn profile sync
   - Calendar integrations
   - ATS connections
   - Automated workflows

3. **Configure Alerts:**
   - Set up email alerts for service failures
   - Monitor workflow execution status

4. **Performance Testing:**
   - Test API response times
   - Monitor database query performance
   - Verify scraper efficiency

---

### Support and Maintenance

**Current Status:** ✅ VPS with CyberPanel configured and ready for application deployment

**Next Actions:**
1. Deploy application code
2. Configure services
3. Test all integrations
4. Monitor system performance

For technical support or deployment issues, check service logs and system status using the commands provided above.

## PostgreSQL Setup on VPS (CyberPanel)

**For**: NextStep LMI Platform
**VPS**: Ubuntu with CyberPanel
**Domain**: nextstep.co.ke
**Database**: PostgreSQL 16 + pgvector extension

---

### Option 1: PostgreSQL Setup on Your VPS (Recommended)

#### Why Use VPS Database?
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

### Step-by-Step PostgreSQL Setup

#### 1. Install PostgreSQL 16 + pgvector

```bash
## SSH into your VPS
ssh root@nextstep.co.ke

## Add PostgreSQL repository
sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'

## Import repository signing key
wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -

## Update package list
sudo apt update

## Install PostgreSQL 16
sudo apt install -y postgresql-16 postgresql-contrib-16 postgresql-16-pgvector

## Verify installation
psql --version
## Expected: psql (PostgreSQL) 16.x
```

**Installation Time**: 5-10 minutes

---

#### 2. Configure PostgreSQL for Production

##### Update PostgreSQL Configuration

```bash
## Edit PostgreSQL config
sudo nano /etc/postgresql/16/main/postgresql.conf
```

**Add/Update these settings**:

```conf
## Connection Settings
listen_addresses = 'localhost'          # Only accept local connections (secure)
max_connections = 100                   # Adjust based on your needs

## Memory Settings (for 4GB RAM VPS - adjust if different)
shared_buffers = 256MB                  # 25% of RAM for small VPS
effective_cache_size = 1GB              # 50-75% of RAM
work_mem = 4MB                          # Per query operation
maintenance_work_mem = 64MB             # For VACUUM, CREATE INDEX

## Checkpoint Settings
checkpoint_completion_target = 0.9
wal_buffers = 16MB

## Query Planning
random_page_cost = 1.1                  # For SSD storage
effective_io_concurrency = 200          # For SSD storage

## Logging (important for debugging)
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

##### Update Authentication Settings

```bash
sudo nano /etc/postgresql/16/main/pg_hba.conf
```

**Add this line** (before other rules):
```conf
## Allow local connections with password
local   all             all                                     md5
host    all             all             127.0.0.1/32            md5
host    all             all             ::1/128                 md5
```

##### Restart PostgreSQL

```bash
sudo systemctl restart postgresql
sudo systemctl enable postgresql  # Start on boot

## Verify it's running
sudo systemctl status postgresql
```

---

#### 3. Create Database and User

```bash
## Switch to postgres user
sudo -u postgres psql

## Run these SQL commands:
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

#### 4. Verify Database Setup

```bash
## Test connection as nextstep_user
psql -U nextstep_user -d nextstep_lmi -h localhost

## Should prompt for password, then show:
## nextstep_lmi=>

## Test pgvector extension
\dx
## Should show "vector" extension

## Exit
\q
```

✅ **If you can connect and see the vector extension, you're good!**

---

#### 5. Update Your Application .env File

```bash
cd /home/nextstep.co.ke/public_html/backend

## Edit .env file
nano .env
```

**Update database settings**:
```bash
## Database Configuration
DATABASE_URL=postgresql://nextstep_user:your_very_secure_password_here_change_this@localhost:5432/nextstep_lmi

## Individual settings (for backwards compatibility)
POSTGRES_USER=nextstep_user
POSTGRES_PASSWORD=your_very_secure_password_here_change_this
POSTGRES_DB=nextstep_lmi
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
```

---

#### 6. Run Database Migrations

```bash
cd /home/nextstep.co.ke/public_html/backend

## Activate virtual environment (if using one)
source venv/bin/activate

## Run Alembic migrations
alembic upgrade head

## Expected output:
## INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
## INFO  [alembic.runtime.migration] Will assume transactional DDL.
## INFO  [alembic.runtime.migration] Running upgrade  -> 001_dedup_fields, add deduplication fields to job_post
```

##### If Alembic Isn't Set Up Yet:

```bash
## Initialize Alembic
alembic init alembic

## Edit alembic.ini
nano alembic.ini
## Change: sqlalchemy.url = postgresql://nextstep_user:password@localhost:5432/nextstep_lmi

## Edit alembic/env.py
nano alembic/env.py
## Add near the top:
## from app.db.models import Base
## target_metadata = Base.metadata

## Create initial migration
alembic revision --autogenerate -m "initial migration"

## Apply migration
alembic upgrade head
```

**Alternative: Run SQL Directly**:
```bash
psql -U nextstep_user -d nextstep_lmi -h localhost < backend/migrations/add_deduplication_fields.sql
```

---

#### 7. Test Database Connection from Application

```bash
cd /home/nextstep.co.ke/public_html/backend

## Create test script
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
## Run test
python test_db.py

## Expected output:
## ✅ Database connection successful!
## ✅ Created test organization with ID: 1
## ✅ Database is ready!
```

---

#### 8. Set Up Automated Backups

##### Create Backup Script

```bash
sudo mkdir -p /home/backups/nextstep
sudo nano /usr/local/bin/backup-nextstep-db.sh
```

```bash
##!/bin/bash
## PostgreSQL Backup Script for NextStep LMI

BACKUP_DIR="/home/backups/nextstep"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="nextstep_lmi"
DB_USER="nextstep_user"

## Create backup directory if it doesn't exist
mkdir -p $BACKUP_DIR

## Backup database (plain SQL format)
echo "Starting backup at $DATE..."
PGPASSWORD='your_very_secure_password_here_change_this' pg_dump \
    -U $DB_USER \
    -h localhost \
    -d $DB_NAME \
    -F p \
    -f $BACKUP_DIR/nextstep_db_$DATE.sql

## Compress backup
gzip $BACKUP_DIR/nextstep_db_$DATE.sql

## Keep only last 7 days of backups
find $BACKUP_DIR -name "nextstep_db_*.sql.gz" -mtime +7 -delete

echo "Backup completed: nextstep_db_$DATE.sql.gz"

## Optional: Upload to cloud storage (S3, Google Cloud, etc.)
## aws s3 cp $BACKUP_DIR/nextstep_db_$DATE.sql.gz s3://your-bucket/backups/
```

```bash
sudo chmod +x /usr/local/bin/backup-nextstep-db.sh

## Test backup
sudo /usr/local/bin/backup-nextstep-db.sh

## Check backup was created
ls -lh /home/backups/nextstep/
```

##### Schedule Daily Backups

```bash
## Edit crontab
sudo crontab -e

## Add this line (runs at 2 AM daily)
0 2 * * * /usr/local/bin/backup-nextstep-db.sh >> /var/log/nextstep-backup.log 2>&1

## Verify crontab
sudo crontab -l
```

---

#### 9. Restore from Backup (If Needed)

```bash
## List available backups
ls -lh /home/backups/nextstep/

## Restore from backup
cd /home/backups/nextstep

## Uncompress backup
gunzip nextstep_db_20260108_020001.sql.gz

## Restore to database
PGPASSWORD='your_password' psql \
    -U nextstep_user \
    -h localhost \
    -d nextstep_lmi \
    < nextstep_db_20260108_020001.sql

echo "Database restored successfully!"
```

---

#### 10. Performance Monitoring

##### Monitor Database Size

```bash
## Check database size
sudo -u postgres psql -c "SELECT pg_size_pretty(pg_database_size('nextstep_lmi'));"

## Check table sizes
sudo -u postgres psql -d nextstep_lmi -c "
SELECT
    schemaname || '.' || tablename AS table,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
LIMIT 10;"
```

##### Monitor Active Connections

```bash
sudo -u postgres psql -c "SELECT count(*) as active_connections FROM pg_stat_activity;"
```

##### Monitor Slow Queries

```bash
## Edit postgresql.conf to log slow queries
sudo nano /etc/postgresql/16/main/postgresql.conf

## Add:
log_min_duration_statement = 1000  # Log queries taking > 1 second

## Restart PostgreSQL
sudo systemctl restart postgresql

## View slow queries
sudo tail -f /var/log/postgresql/postgresql-16-main.log
```

---

#### 11. Security Hardening

##### Secure PostgreSQL

```bash
## 1. Ensure PostgreSQL only listens on localhost
sudo nano /etc/postgresql/16/main/postgresql.conf
## Verify: listen_addresses = 'localhost'

## 2. Firewall (ensure PostgreSQL port 5432 is not exposed)
sudo ufw status
## Port 5432 should NOT be listed (only 22, 80, 443, 8000)

## 3. Strong password policy
## Already set during user creation

## 4. Regular updates
sudo apt update
sudo apt upgrade postgresql-16
```

##### Enable SSL Connections (Optional but Recommended)

```bash
## Generate self-signed certificate
sudo -u postgres openssl req -new -x509 -days 365 -nodes \
    -text -out /etc/postgresql/16/main/server.crt \
    -keyout /etc/postgresql/16/main/server.key \
    -subj "/CN=nextstep.co.ke"

sudo chmod 600 /etc/postgresql/16/main/server.key
sudo chown postgres:postgres /etc/postgresql/16/main/server.*

## Enable SSL in postgresql.conf
sudo nano /etc/postgresql/16/main/postgresql.conf
## Add: ssl = on

## Restart PostgreSQL
sudo systemctl restart postgresql
```

---

#### 12. Migrate Data from jobs.sqlite3

Once PostgreSQL is set up, migrate your 102K jobs:

```bash
cd /home/nextstep.co.ke/public_html/backend

## Create migration script
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
## Run migration (this will take 30-60 minutes for 102K jobs)
python migrate_sqlite_to_postgres.py
```

---

### Database Performance Benchmarks

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

### Troubleshooting

#### Issue: "peer authentication failed"
**Solution**:
```bash
sudo nano /etc/postgresql/16/main/pg_hba.conf
## Change: local all all peer
## To: local all all md5
sudo systemctl restart postgresql
```

#### Issue: "could not connect to server"
**Solution**:
```bash
## Check if PostgreSQL is running
sudo systemctl status postgresql

## Check if port is listening
sudo netstat -plnt | grep 5432

## Restart PostgreSQL
sudo systemctl restart postgresql
```

#### Issue: Out of Memory
**Solution**:
```bash
## Reduce shared_buffers in postgresql.conf
sudo nano /etc/postgresql/16/main/postgresql.conf
## Set: shared_buffers = 128MB (for 2GB VPS)
sudo systemctl restart postgresql
```

#### Issue: Slow Queries
**Solution**:
```bash
## Add indexes
sudo -u postgres psql -d nextstep_lmi
CREATE INDEX idx_job_post_url_hash ON job_post(url_hash);
CREATE INDEX idx_job_post_first_seen ON job_post(first_seen);
CREATE INDEX idx_job_post_org_id ON job_post(org_id);
```

---

### Next Steps

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

### VPS Resource Recommendations

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

### Cost Comparison

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

## dbt for LMI

This is a tiny dbt project to generate simple aggregates (weekly postings, top skills).

### Setup
- Install dbt for Postgres on your machine (or use a container).
- Copy `profiles.example.yml` to `~/.dbt/profiles.yml` and adjust credentials to match your `.env`.
- Run:
  - `dbt debug`
  - `dbt run`
  - `dbt test`

### Models
- `models/postings_daily.sql`: fact table copied from raw job posts (example).
- `models/weekly_metrics.sql`: weekly aggregates for Metabase.

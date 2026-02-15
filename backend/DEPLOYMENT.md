# Next Step Backend - Deployment Guide

## Overview

Next Step is a career advisory platform for Kenya that aggregates jobs from multiple sources and provides intelligent search, recommendations, and notifications.

## Quick Start (Development)

```bash
# 1. Clone and setup
cd backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt

# 2. Setup environment
cp .env.example .env
# Edit .env with your configuration

# 3. Initialize database
python -c "from app.db.database import init_db; init_db()"

# 4. Run server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Environment Variables

### Required

```bash
# Database (PostgreSQL recommended for production)
DATABASE_URL=postgresql://user:pass@localhost:5432/nextstep
# OR for SQLite (development only)
DATABASE_URL=sqlite:///var/nextstep.sqlite

# Security
SECRET_KEY=your-secure-random-key-here
ADMIN_EMAILS=admin@example.com,admin2@example.com
```

### Optional

```bash
# Admin API Key (for server-to-server auth)
ADMIN_API_KEY=your-api-key-here

# Rate Limiting
RATE_LIMIT_PER_MINUTE=60

# Email (for notifications)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
EMAIL_FROM=noreply@nextstep.co.ke

# WhatsApp (Twilio)
TWILIO_ACCOUNT_SID=your-sid
TWILIO_AUTH_TOKEN=your-token
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886

# AI/ML
OPENAI_API_KEY=sk-...
EMBEDDING_MODEL=all-MiniLM-L6-v2

# Redis (for Celery)
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
```

## Production Deployment

### 1. Using Docker

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
docker build -t nextstep-backend .
docker run -d -p 8000:8000 --env-file .env nextstep-backend
```

### 2. Using systemd

```ini
# /etc/systemd/system/nextstep.service
[Unit]
Description=Next Step Backend API
After=network.target

[Service]
User=www-data
WorkingDirectory=/var/www/nextstep/backend
Environment=PATH=/var/www/nextstep/backend/venv/bin
EnvironmentFile=/var/www/nextstep/backend/.env
ExecStart=/var/www/nextstep/backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable nextstep
sudo systemctl start nextstep
```

### 3. With nginx reverse proxy

```nginx
server {
    listen 80;
    server_name api.nextstep.co.ke;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

## Database Setup

### PostgreSQL (Production)

```bash
# Create database
createdb nextstep

# Run migrations (if using alembic)
alembic upgrade head

# Or initialize tables directly
python -c "from app.db.database import init_db; init_db()"
```

### SQLite (Development)

```bash
# Tables are auto-created when DATABASE_URL starts with sqlite://
DATABASE_URL=sqlite:///var/nextstep.sqlite
```

## Running Celery (Background Tasks)

```bash
# Start Celery worker
celery -A app.core.celery_app worker --loglevel=info

# Start Celery beat (scheduled tasks)
celery -A app.core.celery_app beat --loglevel=info

# Combined (development only)
celery -A app.core.celery_app worker --beat --loglevel=info
```

## Job Ingestion

### Run All Sources

```bash
python -c "
from app.db.database import SessionLocal
from app.ingestion.runner import run_all_sources
db = SessionLocal()
count = run_all_sources(db)
print(f'Ingested {count} jobs')
db.close()
"
```

### Run Specific Sources

```bash
# BrighterMonday
python scripts/run_brightermonday_ingestion.py --pages 5

# Government sources only
python -c "
from app.db.database import SessionLocal
from app.ingestion.runner import run_government_sources
db = SessionLocal()
count = run_government_sources(db)
print(f'Ingested {count} jobs')
db.close()
"
```

## Embeddings

The API can optionally compute semantic similarity scores using embeddings stored in `job_embeddings`.

### Backfill / Incremental Updates

Run the incremental embedding backfill (idempotent; it only processes rows missing an embedding):

```bash
python -m cli embed --batch-size 64
```

In production we recommend a `systemd` timer so new jobs get embedded automatically. See:

- `deploy/systemd/nextstep-embeddings.service`
- `deploy/systemd/nextstep-embeddings.timer`

## API Endpoints

### Health Checks

- `GET /health` - Basic health check
- `GET /health/detailed` - Detailed health with DB check
- `GET /api/ingestion/status` - Ingestion metrics

### Search & Jobs

- `GET /api/search?q=analyst&location=Nairobi` - Job search
- `GET /api/jobs/{id}` - Get job details
- `GET /api/translate-title?title=data+ninja` - Title normalization
- `GET /api/careers-for-degree?degree=economics` - Career suggestions

### Recommendations

- `GET /api/recommend?current=data+analyst` - Career transitions
- `GET /api/trending-transitions` - Trending transitions
- `GET /api/transition-salary?target_role=analyst` - Salary insights

### Admin (requires authentication)

- `GET /api/admin/overview` - Admin dashboard
- `GET /api/admin/users` - User management
- `GET /api/admin/jobs` - Job management
- `GET /api/admin/sources` - Source management

## Monitoring

### Logs

Logs are structured JSON in production (APP_ENV=prod):

```json
{"timestamp": "2026-01-22T10:00:00Z", "level": "INFO", "message": "Request completed", "request_id": "abc123"}
```

### Metrics

- `/api/ingestion/status` - Job ingestion metrics
- `/health/detailed` - System health metrics

## Troubleshooting

### Common Issues

1. **Database connection failed**
   - Check DATABASE_URL is correct
   - Ensure PostgreSQL is running
   - Check firewall rules

2. **Rate limiting errors (429)**
   - Increase RATE_LIMIT_PER_MINUTE
   - Check for misconfigured proxies

3. **Scraper failures**
   - Check target site is accessible
   - Update selectors if site changed
   - Check for rate limiting by target

### Smoke Test

```bash
python scripts/smoke_test.py --api-url http://localhost:8000
```

Expected output: 6/6 tests passing

## Security Checklist

- [ ] Change SECRET_KEY from default
- [ ] Set ADMIN_EMAILS for admin access
- [ ] Configure CORS_ORIGINS for production
- [ ] Enable HTTPS in nginx
- [ ] Set up rate limiting
- [ ] Configure ADMIN_API_KEY for scripts
- [ ] Review file permissions

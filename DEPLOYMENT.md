# NextStep Career Platform - CyberPanel Deployment Guide

This guide provides deployment instructions for the NextStep Career Platform on a VPS with CyberPanel already configured.

## Current VPS Status

✅ **VPS Setup Complete**
- Ubuntu server with CyberPanel installed and configured
- Domain: nextstep.co.ke
- SSL certificates configured
- Basic web server functionality operational

## Prerequisites Met

- ✅ VPS with CyberPanel installed
- ✅ Domain configured (nextstep.co.ke)
- ✅ SSL certificates active
- ✅ Basic server infrastructure ready

## Deployment Steps

### 1. Application Deployment

#### Clone Latest Repository
```bash
cd /home/nextstep.co.ke/public_html
git pull origin main
```

#### Configure Environment Variables
```bash
# Update production environment
cp .env.example .env
nano .env
```

**Required Environment Variables:**
```bash
# Application Configuration
APP_ENV=production
APP_HOST=0.0.0.0
APP_PORT=8000
CORS_ORIGINS=https://nextstep.co.ke

# Domain Configuration
DOMAIN=nextstep.co.ke
API_DOMAIN=api.nextstep.co.ke
WEBSITE_URL=https://nextstep.co.ke
API_BASE_URL=https://api.nextstep.co.ke

# Database Configuration (CyberPanel PostgreSQL)
POSTGRES_USER=nextstep_user
POSTGRES_PASSWORD=your_secure_password
POSTGRES_DB=career_lmi
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# Redis Configuration
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# API Keys
OPENAI_API_KEY=your_openai_api_key
TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_token
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886

# LinkedIn Integration
LINKEDIN_CLIENT_ID=your_linkedin_client_id
LINKEDIN_CLIENT_SECRET=your_linkedin_client_secret

# Google Calendar Integration
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret

# Microsoft Calendar Integration
MICROSOFT_CLIENT_ID=your_microsoft_client_id
MICROSOFT_CLIENT_SECRET=your_microsoft_client_secret

# Security
SECRET_KEY=your_very_secure_secret_key_here
```

### 2. Database Setup

#### Create Database and User
```bash
# Access PostgreSQL (via CyberPanel or command line)
sudo -u postgres psql

# Create database and user
CREATE DATABASE career_lmi;
CREATE USER nextstep_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE career_lmi TO nextstep_user;
\q
```

#### Run Database Migrations
```bash
cd /home/nextstep.co.ke/public_html/backend
python -m alembic upgrade head
```

### 3. Install Dependencies

#### Backend Dependencies
```bash
cd /home/nextstep.co.ke/public_html/backend
pip install -r requirements.txt
```

#### Install Redis (if not already installed)
```bash
sudo apt update
sudo apt install redis-server -y
sudo systemctl enable redis-server
sudo systemctl start redis-server
```

### 4. Configure Services

#### Create Systemd Service for FastAPI Backend
```bash
sudo nano /etc/systemd/system/nextstep-backend.service
```

```ini
[Unit]
Description=NextStep Career Platform Backend
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/home/nextstep.co.ke/public_html/backend
Environment=PATH=/usr/local/bin
ExecStart=/usr/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always

[Install]
WantedBy=multi-user.target
```

#### Create Systemd Service for Celery Worker
```bash
sudo nano /etc/systemd/system/nextstep-celery.service
```

```ini
[Unit]
Description=NextStep Celery Worker
After=network.target redis.service

[Service]
Type=simple
User=www-data
WorkingDirectory=/home/nextstep.co.ke/public_html/backend
Environment=PATH=/usr/local/bin
ExecStart=/usr/bin/python -m celery -A app.core.celery_app worker --loglevel=info
Restart=always

[Install]
WantedBy=multi-user.target
```

#### Create Systemd Service for Celery Beat (Scheduler)
```bash
sudo nano /etc/systemd/system/nextstep-celery-beat.service
```

```ini
[Unit]
Description=NextStep Celery Beat Scheduler
After=network.target redis.service

[Service]
Type=simple
User=www-data
WorkingDirectory=/home/nextstep.co.ke/public_html/backend
Environment=PATH=/usr/local/bin
ExecStart=/usr/bin/python -m celery -A app.core.celery_app beat --loglevel=info
Restart=always

[Install]
WantedBy=multi-user.target
```

#### Enable and Start Services
```bash
sudo systemctl daemon-reload
sudo systemctl enable nextstep-backend
sudo systemctl enable nextstep-celery
sudo systemctl enable nextstep-celery-beat

sudo systemctl start nextstep-backend
sudo systemctl start nextstep-celery
sudo systemctl start nextstep-celery-beat
```

### 5. Configure CyberPanel Reverse Proxy

#### Update CyberPanel Virtual Host Configuration
1. Access CyberPanel admin panel
2. Go to Websites → List Websites
3. Select nextstep.co.ke
4. Configure reverse proxy for API endpoints:

**API Proxy Configuration:**
- Path: `/api/`
- Destination: `http://localhost:8000/`
- Enable proxy headers

### 6. Frontend Deployment

#### Build and Deploy Frontend
```bash
cd /home/nextstep.co.ke/public_html/frontend

# Ensure static files are properly served
# Update any API endpoints in JavaScript files to use production URLs
```

### 7. Automated Workflow System Setup

#### Test Scraper Configurations
```bash
cd /home/nextstep.co.ke/public_html/backend
python test_automated_workflow.py
```

#### Verify Celery Tasks
```bash
# Check Celery worker status
sudo systemctl status nextstep-celery

# Check Celery beat scheduler
sudo systemctl status nextstep-celery-beat

# Monitor Celery tasks
celery -A app.core.celery_app events
```

### 8. Integration Setup

#### LinkedIn Integration
1. Configure LinkedIn OAuth app in LinkedIn Developer Console
2. Set redirect URI: `https://nextstep.co.ke/api/integration/linkedin/callback`
3. Update environment variables with client credentials

#### Calendar Integration
1. **Google Calendar:**
   - Configure Google Cloud Console OAuth app
   - Set redirect URI: `https://nextstep.co.ke/api/integration/calendar/google/callback`

2. **Microsoft Calendar:**
   - Configure Azure AD app registration
   - Set redirect URI: `https://nextstep.co.ke/api/integration/calendar/microsoft/callback`

#### ATS Integration
1. Configure webhook endpoints for supported ATS platforms
2. Set webhook URLs:
   - Greenhouse: `https://nextstep.co.ke/api/integration/ats/greenhouse/webhook`
   - Lever: `https://nextstep.co.ke/api/integration/ats/lever/webhook`

### 9. Monitoring and Maintenance

#### Service Status Monitoring
```bash
# Check all services
sudo systemctl status nextstep-backend
sudo systemctl status nextstep-celery
sudo systemctl status nextstep-celery-beat
sudo systemctl status redis-server

# View service logs
sudo journalctl -u nextstep-backend -f
sudo journalctl -u nextstep-celery -f
```

#### Application Updates
```bash
# Update application
cd /home/nextstep.co.ke/public_html
git pull origin main

# Restart services
sudo systemctl restart nextstep-backend
sudo systemctl restart nextstep-celery
sudo systemctl restart nextstep-celery-beat

# Run any new migrations
cd backend
python -m alembic upgrade head
```

#### Database Backup
```bash
# Create automated backup script
sudo nano /usr/local/bin/backup-nextstep.sh
```

```bash
#!/bin/bash
BACKUP_DIR="/home/backups/nextstep"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup database
pg_dump -U nextstep_user -h localhost career_lmi > $BACKUP_DIR/db_backup_$DATE.sql

# Backup application files
tar -czf $BACKUP_DIR/app_backup_$DATE.tar.gz /home/nextstep.co.ke/public_html

# Keep only last 7 days of backups
find $BACKUP_DIR -name "*.sql" -mtime +7 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete
```

```bash
sudo chmod +x /usr/local/bin/backup-nextstep.sh

# Add to crontab for daily backups
sudo crontab -e
# Add: 0 2 * * * /usr/local/bin/backup-nextstep.sh
```

### 10. Performance Optimization

#### Redis Configuration
```bash
sudo nano /etc/redis/redis.conf

# Optimize for production
maxmemory 256mb
maxmemory-policy allkeys-lru
```

#### PostgreSQL Optimization
```bash
sudo nano /etc/postgresql/*/main/postgresql.conf

# Basic optimizations
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 4MB
maintenance_work_mem = 64MB
```

### 11. Security Considerations

#### Firewall Configuration (if not managed by CyberPanel)
```bash
# Allow necessary ports
sudo ufw allow 80
sudo ufw allow 443
sudo ufw allow 8000  # FastAPI backend
sudo ufw allow 22    # SSH
```

#### SSL Certificate Renewal
- CyberPanel should handle SSL certificate renewal automatically
- Monitor certificate expiration dates

### 12. Troubleshooting

#### Common Issues and Solutions

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

#### Health Check Endpoints
- Backend Health: `https://nextstep.co.ke/api/health`
- Workflow Status: `https://nextstep.co.ke/api/workflow/workflow-status`

### 13. Next Steps

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

## Support and Maintenance

**Current Status:** ✅ VPS with CyberPanel configured and ready for application deployment

**Next Actions:**
1. Deploy application code
2. Configure services
3. Test all integrations
4. Monitor system performance

For technical support or deployment issues, check service logs and system status using the commands provided above.

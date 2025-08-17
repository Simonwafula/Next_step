# VPS Deployment Guide - NextStep Career Platform

This guide provides step-by-step instructions for deploying the NextStep Career Platform on a VPS using Docker.

## Prerequisites

- VPS with Ubuntu 20.04+ or similar Linux distribution
- Minimum 2GB RAM, 2 CPU cores, 20GB storage
- Root or sudo access
- Domain name (optional but recommended)

## 1. Server Setup

### Update System
```bash
sudo apt update && sudo apt upgrade -y
```

### Install Docker and Docker Compose
```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify installation
docker --version
docker-compose --version
```

### Install Git
```bash
sudo apt install git -y
```

## 2. Application Deployment

### Clone Repository
```bash
cd /opt
sudo git clone <your-repository-url> nextstep
sudo chown -R $USER:$USER nextstep
cd nextstep
```

### Configure Environment
```bash
# Copy environment template
cp .env.example .env

# Edit environment variables
nano .env
```

### Required Environment Variables
Update the following in your `.env` file:

```bash
# Application Configuration
APP_ENV=production
APP_HOST=0.0.0.0
APP_PORT=8000
CORS_ORIGINS=https://yourdomain.com

# Domain Configuration (replace with your domain)
DOMAIN=yourdomain.com
API_DOMAIN=api.yourdomain.com
WEBSITE_URL=https://yourdomain.com
API_BASE_URL=https://api.yourdomain.com

# PostgreSQL Database Configuration
POSTGRES_USER=nextstep_user
POSTGRES_PASSWORD=your_secure_password_here
POSTGRES_DB=career_lmi
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

# API Keys (Replace with your actual keys)
OPENAI_API_KEY=your_openai_api_key_here
TWILIO_ACCOUNT_SID=your_twilio_account_sid_here
TWILIO_AUTH_TOKEN=your_twilio_auth_token_here
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886

# Security
SECRET_KEY=your_very_secure_secret_key_here
```

### Deploy with Docker Compose
```bash
# Build and start services
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f
```

## 3. Nginx Reverse Proxy Setup

### Install Nginx
```bash
sudo apt install nginx -y
```

### Configure Nginx
Create nginx configuration:
```bash
sudo nano /etc/nginx/sites-available/nextstep
```

Add the following configuration:
```nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    # Frontend
    location / {
        root /opt/nextstep/frontend;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    # API Backend
    location /api/ {
        proxy_pass http://localhost:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Metabase (optional)
    location /analytics/ {
        proxy_pass http://localhost:3000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Enable Site
```bash
sudo ln -s /etc/nginx/sites-available/nextstep /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## 4. SSL Certificate (Let's Encrypt)

### Install Certbot
```bash
sudo apt install certbot python3-certbot-nginx -y
```

### Obtain SSL Certificate
```bash
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

## 5. Firewall Configuration

```bash
# Enable UFW
sudo ufw enable

# Allow SSH
sudo ufw allow ssh

# Allow HTTP and HTTPS
sudo ufw allow 'Nginx Full'

# Check status
sudo ufw status
```

## 6. Database Initialization

### Run Database Migrations
```bash
# Access backend container
docker-compose exec backend bash

# Run any initialization scripts if needed
python -m app.db.init_db
```

## 7. Monitoring and Maintenance

### Service Management
```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# Restart services
docker-compose restart

# View logs
docker-compose logs -f [service_name]

# Update application
git pull
docker-compose build
docker-compose up -d
```

### System Monitoring
```bash
# Check disk usage
df -h

# Check memory usage
free -h

# Check running containers
docker ps

# Check system resources
htop
```

### Backup Database
```bash
# Create backup
docker-compose exec postgres pg_dump -U nextstep_user career_lmi > backup_$(date +%Y%m%d_%H%M%S).sql

# Restore backup
docker-compose exec -T postgres psql -U nextstep_user career_lmi < backup_file.sql
```

## 8. Troubleshooting

### Common Issues

1. **Port conflicts**: Ensure ports 80, 443, 8000, 5432, 3000 are available
2. **Permission issues**: Check file ownership and Docker group membership
3. **Database connection**: Verify PostgreSQL is running and credentials are correct
4. **API not accessible**: Check nginx configuration and firewall rules

### Useful Commands
```bash
# Check service logs
docker-compose logs backend
docker-compose logs postgres

# Restart specific service
docker-compose restart backend

# Check nginx configuration
sudo nginx -t

# Check SSL certificate
sudo certbot certificates

# Monitor system resources
docker stats
```

## 9. Security Recommendations

1. **Change default passwords**: Update all default passwords in `.env`
2. **Regular updates**: Keep system and Docker images updated
3. **Backup strategy**: Implement regular database and file backups
4. **Monitor logs**: Set up log monitoring and alerting
5. **Fail2ban**: Install fail2ban for SSH protection
6. **Regular security audits**: Scan for vulnerabilities

## 10. Performance Optimization

### For Production
1. **Resource limits**: Set appropriate Docker resource limits
2. **Database tuning**: Optimize PostgreSQL configuration
3. **Caching**: Implement Redis for caching if needed
4. **CDN**: Use CDN for static assets
5. **Load balancing**: Consider load balancer for high traffic

### Docker Compose Production Override
Create `docker-compose.prod.yml`:
```yaml
version: "3.9"
services:
  backend:
    restart: unless-stopped
    command: ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
    
  postgres:
    restart: unless-stopped
    
  metabase:
    restart: unless-stopped
```

Deploy with:
```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## Support

For issues or questions:
1. Check application logs: `docker-compose logs`
2. Review this deployment guide
3. Check system resources and connectivity
4. Verify environment configuration

---

**Note**: Replace `yourdomain.com` with your actual domain name throughout this guide.

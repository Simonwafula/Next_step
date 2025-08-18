#!/bin/bash

# NextStep Career Platform - CyberPanel Deployment Script
# This script deploys the application to a VPS with CyberPanel already configured
# 
# CyberPanel Configuration Notes:
# - Uses /home/domain-name/public_html instead of /var/www/html
# - Services run under domain user (nextstep.co.ke) instead of www-data
# - Assumes domain user exists and has proper permissions

set -e  # Exit on any error

echo "🚀 Starting NextStep Career Platform deployment to CyberPanel..."

# Default domain user (can be overridden)
DEFAULT_DOMAIN_USER="nextstep.co.ke"

# Determine DOMAIN_USER in this order: CLI arg, DEPLOY_DOMAIN_USER env var, default
if [[ -n "$1" ]]; then
    DOMAIN_USER="$1"
elif [[ -n "$DEPLOY_DOMAIN_USER" ]]; then
    DOMAIN_USER="$DEPLOY_DOMAIN_USER"
else
    DOMAIN_USER="$DEFAULT_DOMAIN_USER"
fi

# Derive application paths from the DOMAIN_USER
APP_DIR="/home/$DOMAIN_USER/public_html"
BACKEND_DIR="$APP_DIR/backend"
FRONTEND_DIR="$APP_DIR/frontend"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root. For safety we disallow root unless ALLOW_ROOT=1 is set.
if [[ $EUID -eq 0 ]]; then
    if [[ "$ALLOW_ROOT" == "1" ]]; then
        print_warning "Running as root because ALLOW_ROOT=1 was set. Proceeding with caution."
    else
        print_error "This script should not be run as root for security reasons."
        echo
        echo "If you understand the risks and still want to run as root, re-run with the environment variable set:"
        echo "  ALLOW_ROOT=1 ./deploy-to-cyberpanel.sh <domain_user>"
        exit 1
    fi
fi

# Check if we're in the correct directory
if [[ ! -f "backend/app/main.py" ]]; then
    print_error "Please run this script from the project root directory"
    exit 1
fi

print_status "Checking prerequisites..."

# Check if CyberPanel is installed
if ! command -v cyberpanel &> /dev/null; then
    print_warning "CyberPanel command not found. Assuming CyberPanel is installed via web interface."
fi

# Check if domain user exists
if ! id "$DOMAIN_USER" &>/dev/null; then
    print_error "Domain user '$DOMAIN_USER' does not exist. Please create the domain in CyberPanel first."
    exit 1
fi

# Check if application directory exists
if [[ ! -d "$APP_DIR" ]]; then
    print_status "Creating application directory: $APP_DIR"
    sudo mkdir -p "$APP_DIR"
    sudo chown "$DOMAIN_USER:$DOMAIN_USER" "$APP_DIR"
fi

# Check if PostgreSQL is installed
if ! command -v psql &> /dev/null; then
    print_error "PostgreSQL is not installed. Please install it first."
    exit 1
fi

# Check if Redis is installed
if ! command -v redis-cli &> /dev/null; then
    print_warning "Redis is not installed. Installing Redis..."
    sudo apt update
    sudo apt install redis-server -y
    sudo systemctl enable redis-server
    sudo systemctl start redis-server
fi

# Check if Python 3.9+ is available
python_version=$(python3 --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
if (( $(echo "$python_version < 3.9" | bc -l) )); then
    print_error "Python 3.9+ is required. Current version: $python_version"
    exit 1
fi

print_status "Installing Python dependencies..."

# Install pip if not available
if ! command -v pip3 &> /dev/null; then
    sudo apt update
    sudo apt install python3-pip -y
fi

# Install required system packages
sudo apt install -y python3-venv python3-dev build-essential libpq-dev

# Navigate to backend directory and install dependencies
cd backend
print_status "Installing backend dependencies..."

# Create virtual environment if it doesn't exist
if [[ ! -d "venv" ]]; then
    # create the venv as the domain user so files are owned correctly
    sudo -u "$DOMAIN_USER" python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install requirements
pip install -r requirements.txt

# ensure venv is owned by domain user
sudo chown -R "$DOMAIN_USER:$DOMAIN_USER" "$BACKEND_DIR/venv"

print_status "Setting up environment configuration..."

# Copy environment file if it doesn't exist
if [[ ! -f ".env" ]]; then
    if [[ -f ".env.example" ]]; then
        cp .env.example .env
        print_warning "Environment file created from template. Please update .env with your actual values."
    else
        print_error ".env.example file not found"
        exit 1
    fi
fi

print_status "Setting up database..."

# Check if database exists
DB_EXISTS=$(sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='career_lmi'")
if [[ "$DB_EXISTS" != "1" ]]; then
    print_status "Creating database and user..."
    
    # Prompt for database password
    read -s -p "Enter password for database user 'nextstep_user': " DB_PASSWORD
    echo
    
    # Create database and user
    sudo -u postgres psql << EOF
CREATE DATABASE career_lmi;
CREATE USER nextstep_user WITH PASSWORD '$DB_PASSWORD';
GRANT ALL PRIVILEGES ON DATABASE career_lmi TO nextstep_user;
\q
EOF
    
    print_status "Database created successfully"
else
    print_status "Database already exists"
fi

print_status "Running database migrations..."

# Run Alembic migrations
python -m alembic upgrade head

print_status "Setting up systemd services..."

# Create systemd service for FastAPI backend
sudo tee /etc/systemd/system/nextstep-backend.service > /dev/null << EOF
[Unit]
Description=NextStep Career Platform Backend
After=network.target

[Service]
Type=simple
User=$DOMAIN_USER
WorkingDirectory=$BACKEND_DIR
Environment="PATH=$BACKEND_DIR/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin"
ExecStart=$BACKEND_DIR/venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

# Create systemd service for Celery worker
sudo tee /etc/systemd/system/nextstep-celery.service > /dev/null << EOF
[Unit]
Description=NextStep Celery Worker
After=network.target redis.service

[Service]
Type=simple
User=$DOMAIN_USER
WorkingDirectory=$BACKEND_DIR
Environment="PATH=$BACKEND_DIR/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin"
ExecStart=$BACKEND_DIR/venv/bin/python -m celery -A app.core.celery_app worker --loglevel=info
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

# Create systemd service for Celery beat
sudo tee /etc/systemd/system/nextstep-celery-beat.service > /dev/null << EOF
[Unit]
Description=NextStep Celery Beat Scheduler
After=network.target redis.service

[Service]
Type=simple
User=$DOMAIN_USER
WorkingDirectory=$BACKEND_DIR
Environment="PATH=$BACKEND_DIR/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin"
ExecStart=$BACKEND_DIR/venv/bin/python -m celery -A app.core.celery_app beat --loglevel=info
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

print_status "Enabling and starting services..."

# Reload systemd and enable services
sudo systemctl daemon-reload
sudo systemctl enable nextstep-backend
sudo systemctl enable nextstep-celery
sudo systemctl enable nextstep-celery-beat

# Start services
sudo systemctl start nextstep-backend
sudo systemctl start nextstep-celery
sudo systemctl start nextstep-celery-beat

print_status "Checking service status..."

# Check if services are running
if sudo systemctl is-active --quiet nextstep-backend; then
    print_status "✅ Backend service is running"
else
    print_error "❌ Backend service failed to start"
    sudo systemctl status nextstep-backend
fi

if sudo systemctl is-active --quiet nextstep-celery; then
    print_status "✅ Celery worker is running"
else
    print_error "❌ Celery worker failed to start"
    sudo systemctl status nextstep-celery
fi

if sudo systemctl is-active --quiet nextstep-celery-beat; then
    print_status "✅ Celery beat scheduler is running"
else
    print_error "❌ Celery beat scheduler failed to start"
    sudo systemctl status nextstep-celery-beat
fi

print_status "Setting up file permissions..."

# Set proper permissions for CyberPanel
sudo chown -R "$DOMAIN_USER:$DOMAIN_USER" "$APP_DIR"
sudo chmod -R 755 $APP_DIR

print_status "Testing API endpoint..."

# Wait a moment for services to fully start
sleep 5

# Test the health endpoint
if curl -f -s http://localhost:8000/health > /dev/null; then
    print_status "✅ API health check passed"
else
    print_warning "⚠️  API health check failed. Check service logs."
fi

print_status "Setting up backup script..."

# Create backup script
sudo tee /usr/local/bin/backup-nextstep.sh > /dev/null << EOF
#!/bin/bash
BACKUP_DIR="/home/backups/nextstep"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup database
pg_dump -U nextstep_user -h localhost career_lmi > $BACKUP_DIR/db_backup_$DATE.sql

# Backup application files
tar -czf $BACKUP_DIR/app_backup_$DATE.tar.gz "$APP_DIR"

# Keep only last 7 days of backups
find $BACKUP_DIR -name "*.sql" -mtime +7 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete

echo "Backup completed: $DATE"
EOF

sudo chmod +x /usr/local/bin/backup-nextstep.sh

# Install daily cron job for backups (runs at 02:00) if not already installed
if ! crontab -l 2>/dev/null | grep -q "/usr/local/bin/backup-nextstep.sh"; then
    (crontab -l 2>/dev/null; echo "0 2 * * * /usr/local/bin/backup-nextstep.sh >> /var/log/backup-nextstep.log 2>&1") | crontab -
    print_status "Installed daily cron job for backups"
fi

print_status "Creating deployment update script..."

# Create update script for future deployments
tee update-deployment.sh > /dev/null << 'EOF'
#!/bin/bash
echo "🔄 Updating NextStep Career Platform..."

# Pull latest changes
git pull origin main

# Activate virtual environment
cd backend
source venv/bin/activate

# Install any new dependencies
pip install -r requirements.txt

# Run any new migrations
python -m alembic upgrade head

# Restart services
sudo systemctl restart nextstep-backend
sudo systemctl restart nextstep-celery
sudo systemctl restart nextstep-celery-beat

echo "✅ Deployment updated successfully"
EOF

chmod +x update-deployment.sh

print_status "Deployment completed successfully! 🎉"

echo
echo "📋 Next Steps:"
echo "1. Update your .env file with actual API keys and credentials"
echo "2. Configure CyberPanel reverse proxy for /api/ to http://localhost:8000/"
echo "3. Test the integrations (LinkedIn, Calendar, ATS)"
echo "4. Set up monitoring and alerts"
echo
echo "🔧 Useful Commands:"
echo "- Check service status: sudo systemctl status nextstep-backend"
echo "- View logs: sudo journalctl -u nextstep-backend -f"
echo "- Update deployment: ./update-deployment.sh"
echo "- Run backup: sudo /usr/local/bin/backup-nextstep.sh"
echo
echo "🌐 API Endpoints:"
echo "- Health Check: http://localhost:8000/health"
echo "- Workflow Status: http://localhost:8000/api/workflow/workflow-status"
echo "- API Documentation: http://localhost:8000/docs"
echo
echo "⚠️  Remember to:"
echo "- Configure CyberPanel reverse proxy settings"
echo "- Update environment variables with real API keys"
echo "- Set up SSL certificates (should be handled by CyberPanel)"
echo "- Configure firewall rules if needed"

deactivate 2>/dev/null || true

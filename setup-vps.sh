#!/bin/bash

# VPS Setup Script for NextStep Career Platform
# This script automates the initial VPS setup process

set -e

echo "🔧 NextStep Career Platform - VPS Setup Script"
echo "=============================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   print_error "This script should not be run as root for security reasons"
   exit 1
fi

print_header "1. Updating system packages..."
sudo apt update && sudo apt upgrade -y

print_header "2. Installing essential packages..."
sudo apt install -y curl wget git htop nano ufw fail2ban

print_header "3. Installing Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    rm get-docker.sh
    print_status "Docker installed successfully"
else
    print_status "Docker is already installed"
fi

print_header "4. Installing Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    print_status "Docker Compose installed successfully"
else
    print_status "Docker Compose is already installed"
fi

print_header "5. Installing Nginx..."
if ! command -v nginx &> /dev/null; then
    sudo apt install -y nginx
    sudo systemctl enable nginx
    print_status "Nginx installed successfully"
else
    print_status "Nginx is already installed"
fi

print_header "6. Installing Certbot for SSL..."
if ! command -v certbot &> /dev/null; then
    sudo apt install -y certbot python3-certbot-nginx
    print_status "Certbot installed successfully"
else
    print_status "Certbot is already installed"
fi

print_header "7. Configuring firewall..."
sudo ufw --force enable
sudo ufw allow ssh
sudo ufw allow 'Nginx Full'
sudo ufw status
print_status "Firewall configured"

print_header "8. Configuring fail2ban..."
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
print_status "Fail2ban configured"

print_header "9. Creating application directory..."
sudo mkdir -p /opt/nextstep
sudo chown -R $USER:$USER /opt/nextstep
print_status "Application directory created at /opt/nextstep"

echo ""
print_status "VPS setup completed successfully! 🎉"
echo ""
echo "📋 Next Steps:"
echo "   1. Clone your repository to /opt/nextstep"
echo "   2. Configure your .env file"
echo "   3. Set up Nginx configuration"
echo "   4. Run the deployment script"
echo ""
echo "🔧 Useful Commands:"
echo "   - Check Docker: docker --version"
echo "   - Check Docker Compose: docker-compose --version"
echo "   - Check Nginx: sudo systemctl status nginx"
echo "   - Check firewall: sudo ufw status"
echo ""
print_warning "Please log out and log back in for Docker group changes to take effect"
echo ""
print_status "Setup script completed!"

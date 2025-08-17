#!/bin/bash

# NextStep Career Platform Deployment Script
# Usage: ./deploy.sh [environment]
# Environment: dev (default) or prod

set -e

ENVIRONMENT=${1:-dev}
PROJECT_NAME="nextstep"

echo "🚀 Starting deployment for $PROJECT_NAME in $ENVIRONMENT mode..."

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

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Check if .env file exists
if [ ! -f .env ]; then
    print_warning ".env file not found. Creating from .env.example..."
    if [ -f .env.example ]; then
        cp .env.example .env
        print_warning "Please edit .env file with your configuration before running again."
        exit 1
    else
        print_error ".env.example file not found. Cannot create .env file."
        exit 1
    fi
fi

# Validate required environment variables
print_status "Validating environment configuration..."
source .env

required_vars=("POSTGRES_USER" "POSTGRES_PASSWORD" "POSTGRES_DB")
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        print_error "Required environment variable $var is not set in .env file"
        exit 1
    fi
done

# Stop existing containers
print_status "Stopping existing containers..."
docker-compose down

# Pull latest images
print_status "Pulling latest images..."
docker-compose pull

# Build application
print_status "Building application..."
if [ "$ENVIRONMENT" = "prod" ]; then
    docker-compose -f docker-compose.yml -f docker-compose.prod.yml build
else
    docker-compose build
fi

# Start services
print_status "Starting services..."
if [ "$ENVIRONMENT" = "prod" ]; then
    docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
else
    docker-compose up -d
fi

# Wait for services to be healthy
print_status "Waiting for services to be ready..."
sleep 10

# Check service health
print_status "Checking service health..."
if docker-compose ps | grep -q "Up"; then
    print_status "Services are running successfully!"
else
    print_error "Some services failed to start. Check logs with: docker-compose logs"
    exit 1
fi

# Display service status
print_status "Service Status:"
docker-compose ps

# Display useful information
echo ""
print_status "Deployment completed successfully! 🎉"
echo ""
echo "📋 Service Information:"
echo "   - Backend API: http://localhost:8000"
echo "   - Metabase: http://localhost:3000"
echo "   - Frontend: Serve from ./frontend directory"
echo ""
echo "🔧 Useful Commands:"
echo "   - View logs: docker-compose logs -f"
echo "   - Stop services: docker-compose down"
echo "   - Restart services: docker-compose restart"
echo "   - Check status: docker-compose ps"
echo ""

if [ "$ENVIRONMENT" = "prod" ]; then
    echo "🔒 Production Notes:"
    echo "   - Configure Nginx reverse proxy"
    echo "   - Set up SSL certificates"
    echo "   - Configure firewall rules"
    echo "   - Set up monitoring and backups"
    echo ""
fi

print_status "Deployment script completed!"

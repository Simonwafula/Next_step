#!/bin/bash

# Next_KE Platform Upgrades v2.0 Deployment Script
# This script handles database migrations, dependency installation, and deployment

set -e  # Exit on any error

echo "🚀 Starting Next_KE Platform v2.0 Upgrade Deployment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in the right directory
if [ ! -f "backend/requirements.txt" ]; then
    print_error "Please run this script from the project root directory"
    exit 1
fi

# Step 1: Environment Setup
print_status "Step 1: Setting up environment configuration..."

if [ ! -f ".env" ]; then
    print_warning ".env file not found. Creating from .env.example..."
    cp .env.example .env
    print_warning "Please edit .env file with your actual configuration values before continuing."
    read -p "Press Enter after you've updated the .env file..."
fi

print_success "Environment configuration ready"

# Step 2: Backend Dependencies Installation
print_status "Step 2: Installing backend dependencies..."

cd backend

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    print_status "Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
print_status "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
print_status "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
print_status "Installing Python dependencies..."
pip install -r requirements.txt

print_success "Backend dependencies installed successfully"

# Step 3: Database Setup and Migrations
print_status "Step 3: Setting up database and running migrations..."

# Check if alembic is configured
if [ ! -f "alembic.ini" ]; then
    print_status "Initializing Alembic for database migrations..."
    alembic init alembic
    
    # Update alembic.ini with database URL
    print_status "Configuring Alembic..."
    sed -i 's|sqlalchemy.url = driver://user:pass@localhost/dbname|sqlalchemy.url = postgresql://postgres:postgres@localhost/career_lmi|g' alembic.ini
fi

# Run database migrations
print_status "Running database migrations..."

# Check database connection
print_status "Checking database connection..."
python -c "
from app.db.database import engine
try:
    with engine.connect() as conn:
        print('Database connection successful')
except Exception as e:
    print(f'Database connection failed: {e}')
    exit(1)
"

# Run migrations
print_status "Applying database migrations..."
alembic upgrade head

print_success "Database migrations completed successfully"

# Step 4: Initialize AI Models
print_status "Step 4: Initializing AI models..."

print_status "Downloading sentence-transformers model..."
python -c "
from sentence_transformers import SentenceTransformer
import os
print('Downloading all-MiniLM-L6-v2 model...')
model = SentenceTransformer('all-MiniLM-L6-v2')
print('Model downloaded and cached successfully')
"

print_success "AI models initialized successfully"

# Step 5: Create initial data
print_status "Step 5: Creating initial data..."

python -c "
from app.db.database import SessionLocal
from app.db.models import TitleNorm, Skill
from app.normalization.titles import TITLE_FAMILIES

db = SessionLocal()

# Create title normalizations
print('Creating title normalizations...')
for family, data in TITLE_FAMILIES.items():
    existing = db.query(TitleNorm).filter(TitleNorm.family == family).first()
    if not existing:
        title_norm = TitleNorm(
            family=family,
            canonical_title=data['canonical'],
            aliases={'aliases': data.get('aliases', [])}
        )
        db.add(title_norm)

# Create basic skills
print('Creating basic skills...')
basic_skills = [
    'Python', 'JavaScript', 'Java', 'SQL', 'Excel', 'PowerPoint',
    'Project Management', 'Communication', 'Leadership', 'Teamwork',
    'Problem Solving', 'Data Analysis', 'Marketing', 'Sales',
    'Customer Service', 'Finance', 'Accounting', 'HR'
]

for skill_name in basic_skills:
    existing = db.query(Skill).filter(Skill.name == skill_name).first()
    if not existing:
        skill = Skill(name=skill_name)
        db.add(skill)

db.commit()
db.close()
print('Initial data created successfully')
"

print_success "Initial data created successfully"

# Step 6: Test the installation
print_status "Step 6: Testing the installation..."

print_status "Testing API endpoints..."
python -c "
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)

# Test health endpoint
try:
    response = client.get('/health')
    if response.status_code == 200:
        print('✓ Health endpoint working')
    else:
        print('✗ Health endpoint failed')
except Exception as e:
    print(f'✗ Health endpoint error: {e}')

# Test search endpoint
try:
    response = client.get('/api/search?q=data analyst')
    if response.status_code == 200:
        print('✓ Search endpoint working')
    else:
        print('✗ Search endpoint failed')
except Exception as e:
    print(f'✗ Search endpoint error: {e}')

print('API testing completed')
"

print_success "Installation testing completed"

# Step 7: Start services (optional)
print_status "Step 7: Service startup options..."

echo ""
echo "🎉 Next_KE Platform v2.0 upgrade deployment completed successfully!"
echo ""
echo "📋 Next Steps:"
echo "1. Update your .env file with actual API keys and configuration"
echo "2. Start the backend server:"
echo "   cd backend && source venv/bin/activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
echo ""
echo "3. Optional: Start background services:"
echo "   - Redis: redis-server"
echo "   - Celery: celery -A app.celery worker --loglevel=info"
echo ""
echo "4. Access the application:"
echo "   - Frontend: http://localhost:3000"
echo "   - API Documentation: http://localhost:8000/docs"
echo "   - API Base: http://localhost:8000/api"
echo ""
echo "🔧 New Features Available:"
echo "   ✅ User Authentication (/api/auth/*)"
echo "   ✅ Personalized Recommendations (/api/users/recommendations)"
echo "   ✅ Job Management (/api/users/saved-jobs, /api/users/applications)"
echo "   ✅ AI Career Advice (/api/users/career-advice)"
echo "   ✅ Enhanced Search with personalization"
echo "   ✅ Real-time notifications"
echo ""

# Ask if user wants to start the server
read -p "Would you like to start the development server now? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_status "Starting development server..."
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
fi

print_success "Deployment script completed!"

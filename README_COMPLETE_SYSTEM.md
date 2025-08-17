# CareerSearch - Complete Job Search Platform

A comprehensive job search platform with automated data processing, Google-like search interface, premium career tools, and WhatsApp notifications.

## 🚀 Features

### Core Features
- **Google-like Search Interface**: Intuitive job search with advanced filtering
- **WhatsApp Bot Integration**: Get job alerts and interact via WhatsApp
- **Automated Data Processing**: Continuous scraping and cleaning of job data
- **Market Insights**: Real-time labor market intelligence and trends
- **Career Path Recommendations**: AI-powered career transition suggestions

### Premium Features
- **AI-Powered CV Builder**: Generate professional CVs tailored to specific roles
- **Cover Letter Generator**: Create personalized cover letters for job applications
- **"Why Work With Me" Statements**: Craft compelling professional statements
- **Advanced Career Coaching**: Personalized career advice and guidance
- **Priority Job Alerts**: Get notified first about new opportunities
- **Salary Negotiation Tips**: Expert advice on salary discussions

### Payment Integration
- **M-Pesa Integration**: Local payment method for Kenyan users
- **Stripe Integration**: International payment support
- **Flexible Subscription Plans**: Professional and Enterprise tiers

## 🏗️ System Architecture

### Backend Services
```
backend/
├── app/
│   ├── main.py                     # FastAPI application entry point
│   ├── api/routes.py              # API endpoints
│   ├── services/
│   │   ├── data_processing_service.py    # Automated data processing
│   │   ├── notification_service.py       # Job alerts and notifications
│   │   ├── career_tools_service.py       # CV/cover letter generation
│   │   ├── payment_service.py            # Payment processing
│   │   ├── search.py                     # Job search functionality
│   │   ├── recommend.py                  # Career recommendations
│   │   └── lmi.py                        # Labor market intelligence
│   ├── processors/
│   │   ├── job_processor.py              # Main job processing pipeline
│   │   ├── job_extractor.py              # Job data extraction
│   │   ├── data_cleaner.py               # Data cleaning and normalization
│   │   └── database_saver.py             # Database operations
│   ├── scrapers/                         # Web scraping modules
│   ├── webhooks/whatsapp.py              # WhatsApp integration
│   └── db/                               # Database models and setup
```

### Frontend Application
```
frontend/
├── index.html                     # Main application interface
├── styles/main.css               # Comprehensive styling
└── js/
    ├── config.js                 # Configuration and utilities
    ├── api.js                    # API client and services
    ├── search.js                 # Search functionality
    └── main.js                   # Main application controller
```

## 🛠️ Installation & Setup

### Prerequisites
- Python 3.8+
- Node.js 16+ (for frontend development)
- PostgreSQL database
- Redis (for caching)

### Backend Setup

1. **Clone the repository**
```bash
git clone <repository-url>
cd Next_KE
```

2. **Create virtual environment**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Environment Configuration**
```bash
cp .env.example .env
# Edit .env with your configuration
```

Required environment variables:
```env
# Database
DATABASE_URL=postgresql://user:password@localhost/careersearch

# API Keys
OPENAI_API_KEY=your_openai_api_key_here
TWILIO_ACCOUNT_SID=your_twilio_account_sid_here
TWILIO_AUTH_TOKEN=your_twilio_auth_token_here
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886

# OpenAI Configuration
OPENAI_MODEL=gpt-4o-mini
OPENAI_MAX_TOKENS=1000
OPENAI_TEMPERATURE=0.7

# Payment Integration
MPESA_CONSUMER_KEY=your_mpesa_key
MPESA_CONSUMER_SECRET=your_mpesa_secret
STRIPE_SECRET_KEY=your_stripe_key

# CORS
CORS_ORIGINS=http://localhost:3000,https://yourdomain.com
```

5. **Database Setup**
```bash
# Run database migrations
python -m alembic upgrade head

# Initialize database
python -c "from app.db.database import init_db; init_db()"
```

6. **Start the backend server**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Setup

1. **Serve the frontend**
```bash
cd frontend
# Using Python's built-in server
python -m http.server 3000

# Or using Node.js
npx serve -p 3000
```

2. **Configure API endpoint**
Edit `frontend/js/config.js` to point to your backend:
```javascript
const CONFIG = {
    API_BASE_URL: 'http://localhost:8000/api',
    // ... other config
};
```

## 🔧 Configuration

### Job Scrapers
Configure job sources in `backend/app/scrapers/config.yaml`:
```yaml
scrapers:
  brightermonday:
    enabled: true
    base_url: "https://www.brightermonday.co.ke"
    rate_limit: 1
  
  linkedin:
    enabled: true
    base_url: "https://www.linkedin.com"
    rate_limit: 2
```

### WhatsApp Integration
1. Set up WhatsApp Business API
2. Configure webhook URL in WhatsApp settings
3. Update `WHATSAPP_TOKEN` in environment variables

### Payment Integration

#### M-Pesa Setup
1. Register with Safaricom Developer Portal
2. Create a new app and get credentials
3. Configure callback URLs
4. Update M-Pesa credentials in environment

#### Stripe Setup
1. Create Stripe account
2. Get API keys from dashboard
3. Configure webhook endpoints
4. Update Stripe credentials in environment

## 🚀 Usage

### Starting the Complete System

1. **Start Backend Services**
```bash
cd backend
uvicorn app.main:app --reload
```

2. **Start Data Processing**
```python
from app.services.data_processing_service import data_processing_service
import asyncio

# Start automated data processing
asyncio.run(data_processing_service.start_continuous_processing())
```

3. **Start Notification Service**
```python
from app.services.notification_service import notification_service
import asyncio

# Start notification service
asyncio.run(notification_service.start_notification_service())
```

4. **Access the Application**
- Frontend: http://localhost:3000
- API Documentation: http://localhost:8000/docs
- Admin Panel: http://localhost:8000/admin

### API Endpoints

#### Job Search
```bash
# Search jobs
GET /api/search?q=data analyst&location=nairobi

# Get career recommendations
GET /api/recommend?current=software engineer

# Get market insights
GET /api/lmi/weekly-insights
```

#### Career Tools (Premium)
```bash
# Generate CV
POST /api/career-tools/cv
{
  "user_data": {...},
  "target_role": "Data Analyst"
}

# Generate cover letter
POST /api/career-tools/cover-letter
{
  "user_data": {...},
  "job_data": {...}
}
```

#### Payment
```bash
# Initiate M-Pesa payment
POST /api/payments/mpesa/initiate
{
  "user_id": 1,
  "plan_id": "professional",
  "phone_number": "+254712345678"
}
```

## 🔄 Data Processing Pipeline

### Automated Processing Flow
1. **Job Scraping**: Continuous scraping from configured sources
2. **Data Extraction**: Extract structured data from job postings
3. **Data Cleaning**: Normalize and clean extracted data
4. **Database Storage**: Save processed data to database
5. **Opportunity Detection**: Identify new opportunities for notifications
6. **User Matching**: Match opportunities with user preferences
7. **Notification Delivery**: Send alerts via WhatsApp/email

### Processing Configuration
```python
# Configure processing intervals
data_processing_service.processing_interval = 300  # 5 minutes
notification_service.check_interval = 3600  # 1 hour
```

## 💳 Premium Features

### Subscription Plans

#### Professional Plan (KSh 2,500/month)
- AI-powered CV optimization
- Personalized cover letters
- Advanced career coaching
- Priority job alerts
- Salary negotiation tips

#### Enterprise Plan (KSh 5,000/month)
- Everything in Professional
- 1-on-1 career coaching
- Interview preparation
- LinkedIn profile optimization
- Direct recruiter connections
- Custom job alerts

### Feature Access Control
```python
# Check user access to premium features
from app.services.payment_service import payment_service

has_access = await payment_service.check_feature_access(
    user_id=1, 
    feature="ai_cv_optimization"
)
```

## 📱 WhatsApp Integration

### Supported Commands
- `search [query]` - Search for jobs
- `alerts on/off` - Toggle job alerts
- `profile` - View/update profile
- `help` - Get help information

### Setting Up Notifications
1. Users sign up via web interface
2. Provide phone number for WhatsApp
3. Configure notification preferences
4. Receive automated job alerts

## 🔍 Search Features

### Advanced Search Capabilities
- **Semantic Search**: Natural language job queries
- **Degree Translation**: "I studied economics" → relevant careers
- **Location Filtering**: City, region, or remote options
- **Seniority Levels**: Entry, mid, senior, executive
- **Salary Ranges**: Filter by compensation
- **Company Size**: Startup to enterprise

### Search Intelligence
- **Auto-suggestions**: Real-time search suggestions
- **Typo Tolerance**: Handle misspelled queries
- **Synonym Matching**: Match related terms
- **Career Insights**: Show transition opportunities
- **Salary Benchmarks**: Display market rates

## 📊 Analytics & Insights

### Market Intelligence
- Weekly job market overview
- Trending skills and technologies
- Salary insights by role and location
- Career transition patterns
- Company hiring trends

### User Analytics
- Search history and patterns
- Application tracking
- Career progression insights
- Skill gap analysis

## 🛡️ Security & Privacy

### Data Protection
- Encrypted user data storage
- Secure payment processing
- GDPR compliance ready
- Regular security audits

### API Security
- JWT authentication
- Rate limiting
- Input validation
- SQL injection protection

## 🚀 Deployment

### Production Deployment

#### Using Docker
```bash
# Build and run with Docker Compose
docker-compose up -d
```

#### Manual Deployment
```bash
# Backend
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker

# Frontend
# Deploy to CDN or static hosting
```

### Environment Configuration
- Set production environment variables
- Configure database connections
- Set up SSL certificates
- Configure domain and CORS

## 🧪 Testing

### Run Tests
```bash
# Backend tests
cd backend
pytest

# Integration tests
python test_integration.py

# Processor tests
python test_processors.py
```

### Test Coverage
- Unit tests for all services
- Integration tests for API endpoints
- End-to-end tests for user workflows
- Performance tests for search functionality

## 📈 Monitoring & Maintenance

### Health Checks
```bash
# Check system health
GET /health

# Check scraper status
GET /api/scrapers/status

# Check processing status
GET /api/processing/status
```

### Maintenance Tasks
- Regular database cleanup
- Update job scraper configurations
- Monitor payment processing
- Review notification delivery rates

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Make changes with tests
4. Submit pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Email: support@careersearch.co.ke
- WhatsApp: +254700000000
- Documentation: https://docs.careersearch.co.ke

## 🔮 Future Enhancements

### Planned Features
- Mobile app (React Native)
- Video interview preparation
- Skills assessment tests
- Company review system
- Referral network
- AI-powered interview coaching
- Blockchain-verified credentials
- Advanced analytics dashboard

### Roadmap
- Q1 2025: Mobile app launch
- Q2 2025: Advanced AI features
- Q3 2025: Enterprise partnerships
- Q4 2025: Regional expansion

---

**Built with ❤️ for the Kenyan job market**

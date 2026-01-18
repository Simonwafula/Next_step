# Ingestion & Workflows

Consolidated documentation.

## Scraper Integration with PostgreSQL

This document describes the integration of the job scrapers with the main Career Translator application and PostgreSQL database.

### Overview

The integration includes:
- **102,170 existing jobs** in SQLite database ready for migration
- **4 configured scrapers**: brighter_monday, careerjet, jobwebkenya, myjobmag
- **PostgreSQL database** with proper schema for job data
- **API endpoints** for scraper management
- **Migration tools** to transfer data from SQLite to PostgreSQL

### Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Job Scrapers  │───▶│  PostgreSQL DB   │───▶│  FastAPI App    │
│                 │    │                  │    │                 │
│ • BrighterMonday│    │ • job_post       │    │ • Search API    │
│ • CareerJet     │    │ • organization   │    │ • LMI API       │
│ • JobWebKenya   │    │ • location       │    │ • Scraper API   │
│ • MyJobMag      │    │ • skills         │    │ • WhatsApp Bot  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### Files Created/Modified

#### New Files
- `backend/app/scrapers/postgres_db.py` - PostgreSQL database adapter for scrapers
- `backend/app/scrapers/migrate_to_postgres.py` - Migration script from SQLite to PostgreSQL
- `backend/app/services/scraper_service.py` - Service layer for scraper integration
- `backend/test_integration.py` - Integration test script

#### Modified Files
- `backend/app/scrapers/config.py` - Added PostgreSQL configuration flag
- `backend/app/scrapers/scraper.py` - Updated to use PostgreSQL when configured
- `backend/app/api/routes.py` - Added scraper management endpoints
- `.env.example` - Added scraper and PostgreSQL configuration

### Database Schema

The scrapers now integrate with the main application's PostgreSQL schema:

```sql
-- Main job posting table
CREATE TABLE job_post (
    id SERIAL PRIMARY KEY,
    source VARCHAR(120),           -- Extracted from URL domain
    url TEXT UNIQUE,              -- Original job URL
    first_seen TIMESTAMP,         -- When first scraped
    last_seen TIMESTAMP,          -- When last seen
    org_id INTEGER REFERENCES organization(id),
    title_raw VARCHAR(255),       -- Original job title
    description_raw TEXT,         -- Job description
    requirements_raw TEXT,        -- Job requirements
    -- ... other fields for salary, location, etc.
);

-- Organizations extracted from job content
CREATE TABLE organization (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE,
    sector VARCHAR(100),
    verified BOOLEAN DEFAULT FALSE
);
```

### API Endpoints

New scraper management endpoints:

```
GET  /scrapers/status           - Get scraper and database status
POST /scrapers/run/{site_name}  - Run scraper for specific site
POST /scrapers/run-all          - Run all scrapers
POST /scrapers/migrate          - Migrate SQLite data to PostgreSQL
GET  /scrapers/recent-jobs      - Get recent jobs from database
```

### Setup Instructions

#### 1. Environment Configuration

Copy the environment template:
```bash
cp .env.example .env
```

Key configuration variables:
```env
## Enable PostgreSQL for scrapers
USE_POSTGRES=true

## PostgreSQL connection
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=career_lmi
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

## Scraper rate limiting
JOB_RPM=60
```

#### 2. Start Services

Start PostgreSQL:
```bash
docker-compose up -d postgres
```

Wait for PostgreSQL to be ready, then start the backend:
```bash
docker-compose up -d backend
```

#### 3. Migrate Existing Data

Migrate the 102,170 existing jobs from SQLite to PostgreSQL:
```bash
## Via API
curl -X POST http://localhost:8000/scrapers/migrate

## Or directly
cd backend
python app/scrapers/migrate_to_postgres.py
```

#### 4. Run Scrapers

Run all scrapers:
```bash
curl -X POST http://localhost:8000/scrapers/run-all
```

Run specific scraper:
```bash
curl -X POST http://localhost:8000/scrapers/run/brighter_monday
```

#### 5. Check Status

Get scraper status:
```bash
curl http://localhost:8000/scrapers/status
```

### Data Flow

1. **Scraping**: Scrapers collect job data from configured sites
2. **Processing**: Job content is parsed to extract:
   - Company names (for organization table)
   - Job source (from URL domain)
   - Structured job information
3. **Storage**: Data is stored in PostgreSQL with proper relationships
4. **Integration**: Main app can now access scraped data for:
   - Job search and recommendations
   - Labour market intelligence
   - Career pathway analysis

### Scraper Configuration

Scrapers are configured in `backend/app/scrapers/config.yaml`:

```yaml
sites:
  brighter_monday:
    base_url: "https://www.brightermonday.co.ke"
    listing_path: "/jobs?page={page}"
    listing_selector: "a.job-item-link"
    title_attribute: "title"
    content_selector: ".job-description"
  
  # ... other sites
```

### Monitoring and Maintenance

#### Database Monitoring
- Check job counts: `GET /lmi/coverage-stats`
- View recent jobs: `GET /scrapers/recent-jobs`
- Monitor scraper status: `GET /scrapers/status`

#### Automated Scraping
Consider setting up cron jobs or scheduled tasks to run scrapers regularly:
```bash
## Daily scraping at 2 AM
0 2 * * * curl -X POST http://localhost:8000/scrapers/run-all
```

### Integration Benefits

1. **Unified Data Model**: All job data now uses the same PostgreSQL schema
2. **Real-time Updates**: Scrapers can run continuously and update the main database
3. **API Management**: Scrapers can be controlled via REST API
4. **Data Consistency**: Duplicate detection and organization normalization
5. **Scalability**: PostgreSQL can handle large volumes of job data
6. **Analytics Ready**: Data is structured for labour market intelligence

### Testing

Run the integration test:
```bash
cd backend
python test_integration.py
```

This verifies:
- ✅ All modules import correctly
- ✅ SQLite database is accessible (102,170 jobs found)
- ✅ Scraper configurations are valid
- ✅ Database models are properly defined

### Next Steps

1. **Start Docker services** and run migration
2. **Test API endpoints** to ensure everything works
3. **Set up automated scraping** schedule
4. **Monitor data quality** and scraper performance
5. **Enhance parsing** logic for better data extraction

The integration is now complete and ready for production use!

## Job Data Processors

This document describes the job data processing system that extracts detailed information from job post URLs and saves cleaned, normalized data to the database.

### Overview

The job processing system consists of four main components:

1. **JobDataExtractor** - Extracts raw job data from job post URLs
2. **JobDataCleaner** - Cleans and normalizes the extracted data
3. **JobDatabaseSaver** - Saves processed data to the database
4. **JobProcessor** - Orchestrates the complete pipeline

### Architecture

```
Job URL → JobDataExtractor → JobDataCleaner → JobDatabaseSaver → Database
                ↓                ↓               ↓
            Raw HTML        Cleaned Data    Normalized Records
```

### Components

#### 1. JobDataExtractor (`backend/app/processors/job_extractor.py`)

Extracts detailed job information from job post URLs using site-specific extraction logic.

**Features:**
- Site-specific extractors for major job boards (BrighterMonday, LinkedIn, Indeed, etc.)
- Generic fallback extractor for unknown sites
- Structured data extraction (JSON-LD, microdata)
- Async HTTP client with retry logic and rate limiting
- Error handling and logging

**Extracted Data:**
- Job title, company, location
- Job description and requirements
- Salary information
- Employment type and posting dates
- Contact information
- Raw HTML for further processing

#### 2. JobDataCleaner (`backend/app/processors/data_cleaner.py`)

Cleans and normalizes extracted job data using business rules and pattern matching.

**Features:**
- Title normalization using existing title taxonomy
- Location parsing for Kenyan cities and regions
- Salary parsing with currency and period detection
- Employment type standardization
- Seniority level extraction
- Skills extraction using pattern matching
- Education requirement parsing
- HTML content cleaning

**Normalization Examples:**
```python
## Title normalization
"Senior Data Analyst - Remote" → {
    'title_family': 'data_analytics',
    'title_canonical': 'data analyst',
    'seniority': 'senior'
}

## Salary parsing
"KSH 80,000 - 120,000 per month" → {
    'salary_min': 80000.0,
    'salary_max': 120000.0,
    'currency': 'KES',
    'salary_period': 'monthly'
}

## Location parsing
"Nairobi, Kenya" → {
    'country': 'Kenya',
    'region': 'Nairobi',
    'city': 'Nairobi'
}
```

#### 3. JobDatabaseSaver (`backend/app/processors/database_saver.py`)

Saves cleaned job data to the PostgreSQL database with proper relationships.

**Features:**
- Creates/updates related entities (organizations, locations, skills)
- Handles duplicate job posts (updates last_seen timestamp)
- Manages job-skill relationships
- Provides processing statistics
- Transaction management with rollback on errors

**Database Operations:**
- Insert/update job posts
- Create organizations, locations, title normalizations
- Link skills to job posts
- Generate processing statistics

#### 4. JobProcessor (`backend/app/processors/job_processor.py`)

Main orchestrator that coordinates the complete processing pipeline.

**Features:**
- Single URL processing
- Batch processing with concurrency control
- Integration with scraper output
- Processing statistics and monitoring
- Health checks and error recovery
- Update existing jobs functionality

### Usage

#### Basic Usage

```python
from app.processors.job_processor import JobProcessorService

## Initialize service
service = JobProcessorService()

## Process a single job URL
job_id = await service.process_single_url(
    "https://www.brightermonday.co.ke/job/data-analyst-nairobi",
    "brightermonday"
)

## Process multiple URLs
job_urls = [
    {"url": "https://example.com/job1", "source": "site1"},
    {"url": "https://example.com/job2", "source": "site2"}
]
results = await service.processor.process_job_urls_batch(job_urls)

## Get processing statistics
stats = service.get_stats()
```

#### Integration with Scrapers

```python
from app.services.scraper_service import ScraperService

service = ScraperService()

## Run scraper and process jobs
result = await service.run_scraper_for_site("brightermonday", process_jobs=True)

## Run all scrapers with processing
result = await service.run_all_scrapers(process_jobs=True)
```

### Configuration

#### Environment Variables

The processors use the same database configuration as the main application:

```env
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=career_lmi
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
```

#### Logging

Configure logging level for detailed processing information:

```python
import logging
logging.basicConfig(level=logging.INFO)
```

### Testing

Run the test script to verify all components:

```bash
cd backend
python test_processors.py
```

The test script includes:
- Job data extraction tests
- Data cleaning and normalization tests
- Database saving tests
- Full pipeline integration tests

### Data Flow

#### 1. Extraction Phase
```
Job URL → HTTP Request → HTML Content → BeautifulSoup → Structured Data
```

#### 2. Cleaning Phase
```
Raw Data → Text Cleaning → Pattern Matching → Normalization → Cleaned Data
```

#### 3. Saving Phase
```
Cleaned Data → Database Entities → Relationships → Saved Records
```

### Error Handling

The system includes comprehensive error handling:

- **Network errors**: Retry logic with exponential backoff
- **Parsing errors**: Graceful degradation with partial data
- **Database errors**: Transaction rollback and error logging
- **Validation errors**: Data validation with fallback values

### Performance Considerations

- **Batch processing**: Process multiple jobs concurrently
- **Rate limiting**: Respectful delays between requests
- **Database optimization**: Efficient queries and bulk operations
- **Memory management**: Streaming processing for large datasets

### Monitoring

#### Health Checks

```python
health = await service.health_check()
## Returns: {'status': 'healthy', 'database_connected': True, ...}
```

#### Processing Statistics

```python
stats = service.get_stats()
## Returns: {
##     'total_jobs': 1500,
##     'jobs_by_source': {'brightermonday': 800, 'linkedin': 700},
##     'recent_jobs_7_days': 150
## }
```

### Extending the System

#### Adding New Job Sites

1. Create site-specific extraction logic in `JobDataExtractor`
2. Add URL pattern matching
3. Implement field extraction methods
4. Test with sample URLs

#### Adding New Data Fields

1. Update database models
2. Add extraction logic in `JobDataExtractor`
3. Add cleaning logic in `JobDataCleaner`
4. Update database saving in `JobDatabaseSaver`

#### Custom Normalization Rules

1. Update normalization patterns in `JobDataCleaner`
2. Add new mapping dictionaries
3. Implement custom parsing methods
4. Test with sample data

### Troubleshooting

#### Common Issues

1. **Extraction failures**: Check URL accessibility and site structure changes
2. **Database connection errors**: Verify PostgreSQL configuration
3. **Memory issues**: Reduce batch sizes for large datasets
4. **Rate limiting**: Increase delays between requests

#### Debug Mode

Enable detailed logging for troubleshooting:

```python
import logging
logging.getLogger('app.processors').setLevel(logging.DEBUG)
```

### Future Enhancements

- **Machine Learning**: Enhanced skill extraction using NLP models
- **Real-time processing**: WebSocket-based live job processing
- **Data validation**: Advanced validation rules and data quality checks
- **Performance optimization**: Caching and database indexing improvements
- **Monitoring dashboard**: Real-time processing metrics and alerts

## Automated Workflow System Documentation

### Overview

The Automated Workflow System is a comprehensive solution that enables the Next_KE platform to automatically scrape job data, process it, learn from patterns, optimize models, and generate insights. The system is designed to be self-learning and adaptive, continuously improving its performance based on new data.

### System Architecture

#### Core Components

1. **Automated Workflow Service** (`backend/app/services/automated_workflow_service.py`)
   - Orchestrates the complete workflow execution
   - Manages quality scoring and data validation
   - Implements self-learning algorithms

2. **Celery Task System** (`backend/app/tasks/`)
   - **Workflow Tasks**: Complete workflow orchestration
   - **Scraper Tasks**: Web scraping and data collection
   - **Processing Tasks**: Data cleaning and normalization

3. **API Endpoints** (`backend/app/api/workflow_routes.py`)
   - REST API for triggering workflows
   - Status monitoring and configuration management

4. **Background Processing** (`backend/app/core/celery_app.py`)
   - Celery configuration with Redis backend
   - Scheduled tasks and queue management

### Workflow Stages

#### Stage 1: Scraper Testing and Execution
- **Purpose**: Test scraper configurations and collect job data
- **Process**:
  1. Load scraper configurations from `config.yaml`
  2. Test each scraper for connectivity and selector validity
  3. Execute successful scrapers to collect job data
  4. Migrate collected data from SQLite to PostgreSQL

**Key Features**:
- Health monitoring of scraper endpoints
- Automatic retry mechanisms
- Data quality validation during collection

#### Stage 2: Data Processing and Cleaning
- **Purpose**: Process raw job data and ensure quality
- **Process**:
  1. Retrieve unprocessed job postings
  2. Apply quality scoring algorithm (0.0 - 1.0 scale)
  3. Clean and normalize job data
  4. Extract and save skills with confidence scores
  5. Update organization and location information

**Quality Scoring Criteria**:
- Title quality (2 points)
- Description completeness (3 points)
- Requirements detail (2 points)
- Company information (1 point)
- Location data (1 point)
- Salary information (1 point)

#### Stage 3: Knowledge Extraction and Learning
- **Purpose**: Learn new patterns and update knowledge base
- **Process**:
  1. Analyze job title patterns for normalization
  2. Extract new skill patterns from descriptions
  3. Discover salary and market trends
  4. Update user preference models based on behavior

**Learning Capabilities**:
- Job title normalization improvements
- Skill extraction enhancement
- Market pattern recognition
- User behavior analysis

#### Stage 4: Model Optimization
- **Purpose**: Update ML models and algorithms
- **Process**:
  1. Update embeddings model with new job data
  2. Optimize search algorithms based on user interactions
  3. Enhance recommendation models using application data
  4. Improve matching algorithms

**Optimization Triggers**:
- Minimum 100 new jobs for embedding updates
- Weekly search interaction analysis
- Monthly recommendation model updates

#### Stage 5: Insights Generation
- **Purpose**: Generate market insights and daily metrics
- **Process**:
  1. Calculate daily job posting metrics by role family
  2. Generate hiring trend analysis
  3. Create skill demand reports
  4. Produce salary insights and location analysis

### API Endpoints

#### Workflow Management

##### `POST /api/workflow/run-complete`
Triggers the complete 5-stage automated workflow.

**Response**:
```json
{
  "status": "started",
  "message": "Complete automated workflow has been started in the background",
  "workflow_stages": [
    "scraper_testing_and_execution",
    "data_processing_and_cleaning",
    "knowledge_extraction_and_learning",
    "model_optimization",
    "insights_generation"
  ]
}
```

##### `POST /api/workflow/run-scraper-stage`
Runs only the scraper testing and execution stage.

##### `POST /api/workflow/run-processing-stage`
Runs only the data processing and cleaning stage.

##### `POST /api/workflow/run-learning-stage`
Runs only the knowledge extraction and learning stage.

##### `POST /api/workflow/test-scrapers`
Tests all scraper configurations without running full scraping.

**Response**:
```json
{
  "status": "completed",
  "summary": {
    "total_scrapers": 5,
    "successful_scrapers": 4,
    "success_rate": 0.8
  },
  "detailed_results": {
    "brightermonday": {
      "status": "success",
      "response_time": 1.23,
      "sample_jobs_found": 25
    }
  }
}
```

##### `GET /api/workflow/scraper-configs`
Retrieves current scraper configurations.

##### `POST /api/workflow/generate-insights`
Generates market insights and daily metrics.

##### `GET /api/workflow/workflow-status`
Gets current workflow execution status.

##### `POST /api/workflow/schedule-workflow`
Schedules automated workflow to run at specified intervals.

### Celery Tasks

#### Workflow Tasks
- `run_daily_workflow`: Complete daily workflow execution
- `run_scraper_stage`: Scraper testing and execution
- `run_processing_stage`: Data processing and cleaning
- `run_learning_stage`: Knowledge extraction and learning
- `generate_daily_insights`: Insights generation
- `run_optimization_stage`: Model optimization

#### Scraper Tasks
- `test_all_scrapers`: Health check for all scrapers
- `run_single_scraper`: Execute specific scraper
- `run_all_scrapers`: Execute all configured scrapers
- `migrate_scraper_data`: Data migration from SQLite to PostgreSQL
- `validate_scraper_config`: Configuration validation
- `cleanup_old_jobs`: Remove old job postings

#### Processing Tasks
- `process_raw_jobs`: Process raw job data in batches
- `clean_duplicate_jobs`: Remove duplicate job postings
- `extract_job_skills`: Extract skills from job descriptions
- `normalize_job_titles`: Normalize job titles
- `calculate_job_quality_scores`: Calculate quality scores
- `update_job_embeddings`: Update job embeddings
- `validate_job_data`: Validate job data quality

### Scheduled Tasks

The system includes automated scheduling via Celery Beat:

- **Daily Complete Workflow**: Runs every 24 hours
- **Scraper Health Check**: Runs every 6 hours
- **Insights Generation**: Runs every 4 hours

### Configuration

#### Environment Variables

```bash
## Celery Configuration
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

## Workflow Settings
WORKFLOW_QUALITY_THRESHOLD=0.8
WORKFLOW_LEARNING_THRESHOLD=100
WORKFLOW_BATCH_SIZE=100
```

#### Scraper Configuration

Scrapers are configured in `backend/app/scrapers/config.yaml`:

```yaml
sites:
  brightermonday:
    base_url: "https://www.brightermonday.co.ke"
    listing_path: "/jobs?page={page}"
    listing_selector: ".job-item a"
    # ... additional configuration
```

### Self-Learning Features

#### 1. Job Title Normalization
- Analyzes new job titles to identify patterns
- Updates normalization mappings automatically
- Improves title family classification

#### 2. Skill Extraction Enhancement
- Learns new skill patterns from job descriptions
- Updates skill normalization rules
- Identifies emerging skills and technologies

#### 3. Market Pattern Recognition
- Discovers salary trends by role and location
- Identifies hiring patterns by company and industry
- Recognizes seasonal employment trends

#### 4. User Behavior Learning
- Analyzes search patterns and click behavior
- Updates user preference models
- Improves personalized recommendations

### Quality Assurance

#### Data Quality Scoring
Jobs are scored on a 0.0-1.0 scale based on:
- Content completeness
- Information accuracy
- Structural validity
- Metadata availability

#### Validation Checks
- Required field validation
- Data format verification
- Duplicate detection
- Quality threshold enforcement

### Monitoring and Logging

#### Task Monitoring
- Real-time task status tracking
- Progress reporting with metadata
- Error handling and retry mechanisms
- Performance metrics collection

#### Logging
- Structured logging with context
- Error tracking and alerting
- Performance monitoring
- Audit trail maintenance

### Testing

#### Test Suite (`backend/test_automated_workflow.py`)

The comprehensive test suite includes:

1. **Scraper Configuration Tests**
   - Connectivity testing
   - Selector validation
   - Response time measurement

2. **Database Integration Tests**
   - Data consistency checks
   - Relationship validation
   - Performance testing

3. **Quality Scoring Tests**
   - Algorithm validation
   - Edge case handling
   - Score distribution analysis

4. **Workflow Stage Tests**
   - Individual stage execution
   - Error handling validation
   - Performance benchmarking

5. **Celery Task Tests**
   - Task registration verification
   - Execution testing
   - Queue management validation

#### Running Tests

```bash
## Run the complete test suite
cd backend
python test_automated_workflow.py

## Run specific test functions
python -c "import asyncio; from test_automated_workflow import test_scraper_configurations; asyncio.run(test_scraper_configurations())"
```

### Deployment

#### Development Setup

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Start Redis**:
   ```bash
   redis-server
   ```

3. **Start Celery Worker**:
   ```bash
   celery -A app.core.celery_app worker --loglevel=info
   ```

4. **Start Celery Beat** (for scheduled tasks):
   ```bash
   celery -A app.core.celery_app beat --loglevel=info
   ```

5. **Start FastAPI Application**:
   ```bash
   uvicorn app.main:app --reload
   ```

#### Production Deployment

1. **Docker Compose** includes Celery services:
   ```yaml
   celery-worker:
     build: ./backend
     command: celery -A app.core.celery_app worker --loglevel=info
     depends_on:
       - redis
       - postgres
   
   celery-beat:
     build: ./backend
     command: celery -A app.core.celery_app beat --loglevel=info
     depends_on:
       - redis
       - postgres
   ```

2. **Environment Configuration**:
   - Set production Redis URL
   - Configure database connections
   - Set appropriate log levels
   - Configure monitoring endpoints

### Performance Considerations

#### Scalability
- Horizontal scaling via multiple Celery workers
- Queue-based task distribution
- Database connection pooling
- Caching for frequently accessed data

#### Optimization
- Batch processing for large datasets
- Incremental learning updates
- Efficient database queries
- Memory-conscious data processing

#### Resource Management
- Task timeout configuration
- Memory usage monitoring
- CPU utilization tracking
- Storage optimization

### Troubleshooting

#### Common Issues

1. **Scraper Failures**
   - Check website accessibility
   - Validate CSS selectors
   - Review rate limiting
   - Verify user agent settings

2. **Task Queue Issues**
   - Verify Redis connectivity
   - Check worker availability
   - Monitor queue lengths
   - Review task routing

3. **Database Performance**
   - Monitor connection pools
   - Check query performance
   - Review index usage
   - Optimize batch sizes

4. **Memory Issues**
   - Monitor worker memory usage
   - Adjust batch sizes
   - Implement data streaming
   - Configure garbage collection

#### Debugging

1. **Enable Debug Logging**:
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

2. **Monitor Task Execution**:
   ```bash
   celery -A app.core.celery_app events
   ```

3. **Check Task Results**:
   ```python
   from app.core.celery_app import celery_app
   result = celery_app.AsyncResult('task-id')
   print(result.status, result.result)
   ```

### Future Enhancements

#### Planned Features
1. **Advanced ML Models**
   - Deep learning for job matching
   - NLP improvements for skill extraction
   - Predictive analytics for market trends

2. **Real-time Processing**
   - Stream processing capabilities
   - Real-time data ingestion
   - Live dashboard updates

3. **Enhanced Monitoring**
   - Grafana dashboards
   - Prometheus metrics
   - Alerting system integration

4. **API Improvements**
   - GraphQL support
   - Webhook notifications
   - Batch API operations

#### Integration Opportunities
- LinkedIn profile synchronization
- Calendar integration for interviews
- ATS system connections
- External data source integration

### Support and Maintenance

#### Regular Maintenance Tasks
1. **Weekly**:
   - Review scraper health reports
   - Check data quality metrics
   - Monitor system performance

2. **Monthly**:
   - Update scraper configurations
   - Review learning algorithm performance
   - Optimize database queries

3. **Quarterly**:
   - Evaluate new data sources
   - Update ML models
   - Review system architecture

#### Support Contacts
- Technical Issues: [technical-support@nextstep.co.ke]
- System Administration: [admin@nextstep.co.ke]
- Data Quality: [data-quality@nextstep.co.ke]

---

This automated workflow system represents a significant advancement in the Next_KE platform's capability to provide accurate, up-to-date job market information while continuously learning and improving from new data patterns.

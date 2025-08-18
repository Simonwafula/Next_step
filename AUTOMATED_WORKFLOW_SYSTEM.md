# Automated Workflow System Documentation

## Overview

The Automated Workflow System is a comprehensive solution that enables the Next_KE platform to automatically scrape job data, process it, learn from patterns, optimize models, and generate insights. The system is designed to be self-learning and adaptive, continuously improving its performance based on new data.

## System Architecture

### Core Components

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

## Workflow Stages

### Stage 1: Scraper Testing and Execution
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

### Stage 2: Data Processing and Cleaning
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

### Stage 3: Knowledge Extraction and Learning
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

### Stage 4: Model Optimization
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

### Stage 5: Insights Generation
- **Purpose**: Generate market insights and daily metrics
- **Process**:
  1. Calculate daily job posting metrics by role family
  2. Generate hiring trend analysis
  3. Create skill demand reports
  4. Produce salary insights and location analysis

## API Endpoints

### Workflow Management

#### `POST /api/workflow/run-complete`
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

#### `POST /api/workflow/run-scraper-stage`
Runs only the scraper testing and execution stage.

#### `POST /api/workflow/run-processing-stage`
Runs only the data processing and cleaning stage.

#### `POST /api/workflow/run-learning-stage`
Runs only the knowledge extraction and learning stage.

#### `POST /api/workflow/test-scrapers`
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

#### `GET /api/workflow/scraper-configs`
Retrieves current scraper configurations.

#### `POST /api/workflow/generate-insights`
Generates market insights and daily metrics.

#### `GET /api/workflow/workflow-status`
Gets current workflow execution status.

#### `POST /api/workflow/schedule-workflow`
Schedules automated workflow to run at specified intervals.

## Celery Tasks

### Workflow Tasks
- `run_daily_workflow`: Complete daily workflow execution
- `run_scraper_stage`: Scraper testing and execution
- `run_processing_stage`: Data processing and cleaning
- `run_learning_stage`: Knowledge extraction and learning
- `generate_daily_insights`: Insights generation
- `run_optimization_stage`: Model optimization

### Scraper Tasks
- `test_all_scrapers`: Health check for all scrapers
- `run_single_scraper`: Execute specific scraper
- `run_all_scrapers`: Execute all configured scrapers
- `migrate_scraper_data`: Data migration from SQLite to PostgreSQL
- `validate_scraper_config`: Configuration validation
- `cleanup_old_jobs`: Remove old job postings

### Processing Tasks
- `process_raw_jobs`: Process raw job data in batches
- `clean_duplicate_jobs`: Remove duplicate job postings
- `extract_job_skills`: Extract skills from job descriptions
- `normalize_job_titles`: Normalize job titles
- `calculate_job_quality_scores`: Calculate quality scores
- `update_job_embeddings`: Update job embeddings
- `validate_job_data`: Validate job data quality

## Scheduled Tasks

The system includes automated scheduling via Celery Beat:

- **Daily Complete Workflow**: Runs every 24 hours
- **Scraper Health Check**: Runs every 6 hours
- **Insights Generation**: Runs every 4 hours

## Configuration

### Environment Variables

```bash
# Celery Configuration
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Workflow Settings
WORKFLOW_QUALITY_THRESHOLD=0.8
WORKFLOW_LEARNING_THRESHOLD=100
WORKFLOW_BATCH_SIZE=100
```

### Scraper Configuration

Scrapers are configured in `backend/app/scrapers/config.yaml`:

```yaml
sites:
  brightermonday:
    base_url: "https://www.brightermonday.co.ke"
    listing_path: "/jobs?page={page}"
    listing_selector: ".job-item a"
    # ... additional configuration
```

## Self-Learning Features

### 1. Job Title Normalization
- Analyzes new job titles to identify patterns
- Updates normalization mappings automatically
- Improves title family classification

### 2. Skill Extraction Enhancement
- Learns new skill patterns from job descriptions
- Updates skill normalization rules
- Identifies emerging skills and technologies

### 3. Market Pattern Recognition
- Discovers salary trends by role and location
- Identifies hiring patterns by company and industry
- Recognizes seasonal employment trends

### 4. User Behavior Learning
- Analyzes search patterns and click behavior
- Updates user preference models
- Improves personalized recommendations

## Quality Assurance

### Data Quality Scoring
Jobs are scored on a 0.0-1.0 scale based on:
- Content completeness
- Information accuracy
- Structural validity
- Metadata availability

### Validation Checks
- Required field validation
- Data format verification
- Duplicate detection
- Quality threshold enforcement

## Monitoring and Logging

### Task Monitoring
- Real-time task status tracking
- Progress reporting with metadata
- Error handling and retry mechanisms
- Performance metrics collection

### Logging
- Structured logging with context
- Error tracking and alerting
- Performance monitoring
- Audit trail maintenance

## Testing

### Test Suite (`backend/test_automated_workflow.py`)

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

### Running Tests

```bash
# Run the complete test suite
cd backend
python test_automated_workflow.py

# Run specific test functions
python -c "import asyncio; from test_automated_workflow import test_scraper_configurations; asyncio.run(test_scraper_configurations())"
```

## Deployment

### Development Setup

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

### Production Deployment

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

## Performance Considerations

### Scalability
- Horizontal scaling via multiple Celery workers
- Queue-based task distribution
- Database connection pooling
- Caching for frequently accessed data

### Optimization
- Batch processing for large datasets
- Incremental learning updates
- Efficient database queries
- Memory-conscious data processing

### Resource Management
- Task timeout configuration
- Memory usage monitoring
- CPU utilization tracking
- Storage optimization

## Troubleshooting

### Common Issues

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

### Debugging

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

## Future Enhancements

### Planned Features
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

### Integration Opportunities
- LinkedIn profile synchronization
- Calendar integration for interviews
- ATS system connections
- External data source integration

## Support and Maintenance

### Regular Maintenance Tasks
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

### Support Contacts
- Technical Issues: [technical-support@nextstep.co.ke]
- System Administration: [admin@nextstep.co.ke]
- Data Quality: [data-quality@nextstep.co.ke]

---

This automated workflow system represents a significant advancement in the Next_KE platform's capability to provide accurate, up-to-date job market information while continuously learning and improving from new data patterns.

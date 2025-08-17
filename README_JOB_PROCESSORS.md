# Job Data Processors

This document describes the job data processing system that extracts detailed information from job post URLs and saves cleaned, normalized data to the database.

## Overview

The job processing system consists of four main components:

1. **JobDataExtractor** - Extracts raw job data from job post URLs
2. **JobDataCleaner** - Cleans and normalizes the extracted data
3. **JobDatabaseSaver** - Saves processed data to the database
4. **JobProcessor** - Orchestrates the complete pipeline

## Architecture

```
Job URL → JobDataExtractor → JobDataCleaner → JobDatabaseSaver → Database
                ↓                ↓               ↓
            Raw HTML        Cleaned Data    Normalized Records
```

## Components

### 1. JobDataExtractor (`backend/app/processors/job_extractor.py`)

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

### 2. JobDataCleaner (`backend/app/processors/data_cleaner.py`)

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
# Title normalization
"Senior Data Analyst - Remote" → {
    'title_family': 'data_analytics',
    'title_canonical': 'data analyst',
    'seniority': 'senior'
}

# Salary parsing
"KSH 80,000 - 120,000 per month" → {
    'salary_min': 80000.0,
    'salary_max': 120000.0,
    'currency': 'KES',
    'salary_period': 'monthly'
}

# Location parsing
"Nairobi, Kenya" → {
    'country': 'Kenya',
    'region': 'Nairobi',
    'city': 'Nairobi'
}
```

### 3. JobDatabaseSaver (`backend/app/processors/database_saver.py`)

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

### 4. JobProcessor (`backend/app/processors/job_processor.py`)

Main orchestrator that coordinates the complete processing pipeline.

**Features:**
- Single URL processing
- Batch processing with concurrency control
- Integration with scraper output
- Processing statistics and monitoring
- Health checks and error recovery
- Update existing jobs functionality

## Usage

### Basic Usage

```python
from app.processors.job_processor import JobProcessorService

# Initialize service
service = JobProcessorService()

# Process a single job URL
job_id = await service.process_single_url(
    "https://www.brightermonday.co.ke/job/data-analyst-nairobi",
    "brightermonday"
)

# Process multiple URLs
job_urls = [
    {"url": "https://example.com/job1", "source": "site1"},
    {"url": "https://example.com/job2", "source": "site2"}
]
results = await service.processor.process_job_urls_batch(job_urls)

# Get processing statistics
stats = service.get_stats()
```

### Integration with Scrapers

```python
from app.services.scraper_service import ScraperService

service = ScraperService()

# Run scraper and process jobs
result = await service.run_scraper_for_site("brightermonday", process_jobs=True)

# Run all scrapers with processing
result = await service.run_all_scrapers(process_jobs=True)
```

## Configuration

### Environment Variables

The processors use the same database configuration as the main application:

```env
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=career_lmi
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
```

### Logging

Configure logging level for detailed processing information:

```python
import logging
logging.basicConfig(level=logging.INFO)
```

## Testing

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

## Data Flow

### 1. Extraction Phase
```
Job URL → HTTP Request → HTML Content → BeautifulSoup → Structured Data
```

### 2. Cleaning Phase
```
Raw Data → Text Cleaning → Pattern Matching → Normalization → Cleaned Data
```

### 3. Saving Phase
```
Cleaned Data → Database Entities → Relationships → Saved Records
```

## Error Handling

The system includes comprehensive error handling:

- **Network errors**: Retry logic with exponential backoff
- **Parsing errors**: Graceful degradation with partial data
- **Database errors**: Transaction rollback and error logging
- **Validation errors**: Data validation with fallback values

## Performance Considerations

- **Batch processing**: Process multiple jobs concurrently
- **Rate limiting**: Respectful delays between requests
- **Database optimization**: Efficient queries and bulk operations
- **Memory management**: Streaming processing for large datasets

## Monitoring

### Health Checks

```python
health = await service.health_check()
# Returns: {'status': 'healthy', 'database_connected': True, ...}
```

### Processing Statistics

```python
stats = service.get_stats()
# Returns: {
#     'total_jobs': 1500,
#     'jobs_by_source': {'brightermonday': 800, 'linkedin': 700},
#     'recent_jobs_7_days': 150
# }
```

## Extending the System

### Adding New Job Sites

1. Create site-specific extraction logic in `JobDataExtractor`
2. Add URL pattern matching
3. Implement field extraction methods
4. Test with sample URLs

### Adding New Data Fields

1. Update database models
2. Add extraction logic in `JobDataExtractor`
3. Add cleaning logic in `JobDataCleaner`
4. Update database saving in `JobDatabaseSaver`

### Custom Normalization Rules

1. Update normalization patterns in `JobDataCleaner`
2. Add new mapping dictionaries
3. Implement custom parsing methods
4. Test with sample data

## Troubleshooting

### Common Issues

1. **Extraction failures**: Check URL accessibility and site structure changes
2. **Database connection errors**: Verify PostgreSQL configuration
3. **Memory issues**: Reduce batch sizes for large datasets
4. **Rate limiting**: Increase delays between requests

### Debug Mode

Enable detailed logging for troubleshooting:

```python
import logging
logging.getLogger('app.processors').setLevel(logging.DEBUG)
```

## Future Enhancements

- **Machine Learning**: Enhanced skill extraction using NLP models
- **Real-time processing**: WebSocket-based live job processing
- **Data validation**: Advanced validation rules and data quality checks
- **Performance optimization**: Caching and database indexing improvements
- **Monitoring dashboard**: Real-time processing metrics and alerts

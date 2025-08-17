"""
Test script for job processors
"""

import asyncio
import logging
from app.processors.job_processor import JobProcessorService
from app.processors.job_extractor import JobDataExtractor
from app.processors.data_cleaner import JobDataCleaner
from app.processors.database_saver import JobDatabaseSaver

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_job_extractor():
    """Test the job data extractor"""
    print("\n=== Testing Job Data Extractor ===")
    
    # Test URLs (you can replace these with actual job URLs)
    test_urls = [
        {
            'url': 'https://www.brightermonday.co.ke/job/data-analyst-nairobi',
            'source': 'brightermonday'
        },
        # Add more test URLs as needed
    ]
    
    async with JobDataExtractor() as extractor:
        for test_case in test_urls:
            print(f"\nTesting extraction from: {test_case['url']}")
            
            try:
                data = await extractor.extract_job_details(
                    test_case['url'], 
                    test_case['source']
                )
                
                if data:
                    print(f"✓ Successfully extracted data")
                    print(f"  Title: {data.get('title', 'N/A')}")
                    print(f"  Company: {data.get('company', 'N/A')}")
                    print(f"  Location: {data.get('location', 'N/A')}")
                    print(f"  Description length: {len(data.get('description', ''))}")
                else:
                    print("✗ Failed to extract data")
                    
            except Exception as e:
                print(f"✗ Error: {e}")

def test_data_cleaner():
    """Test the data cleaner"""
    print("\n=== Testing Data Cleaner ===")
    
    # Sample raw data
    raw_data = {
        'url': 'https://example.com/job/123',
        'source': 'test',
        'title': 'Senior Data Analyst - Remote',
        'company': 'Tech Corp Ltd.',
        'location': 'Nairobi, Kenya',
        'description': '<p>We are looking for a <strong>data analyst</strong> with SQL and Python skills.</p>',
        'requirements': '<ul><li>Bachelor\'s degree</li><li>3+ years experience</li></ul>',
        'salary_text': 'KSH 80,000 - 120,000 per month',
        'employment_type': 'Full Time',
        'posted_date': '2 days ago',
        'application_deadline': '2024-02-15',
        'contact_info': 'Apply via email: jobs@techcorp.com'
    }
    
    cleaner = JobDataCleaner()
    
    try:
        cleaned_data = cleaner.clean_job_data(raw_data)
        
        print("✓ Successfully cleaned data")
        print(f"  Original title: {raw_data['title']}")
        print(f"  Cleaned title: {cleaned_data.get('title_raw')}")
        print(f"  Title family: {cleaned_data.get('title_family')}")
        print(f"  Title canonical: {cleaned_data.get('title_canonical')}")
        print(f"  Company: {cleaned_data.get('company_name')}")
        print(f"  Location: {cleaned_data.get('location_raw')}")
        print(f"  City: {cleaned_data.get('city')}")
        print(f"  Region: {cleaned_data.get('region')}")
        print(f"  Salary min: {cleaned_data.get('salary_min')}")
        print(f"  Salary max: {cleaned_data.get('salary_max')}")
        print(f"  Currency: {cleaned_data.get('currency')}")
        print(f"  Employment type: {cleaned_data.get('employment_type')}")
        print(f"  Seniority: {cleaned_data.get('seniority')}")
        print(f"  Skills: {cleaned_data.get('skills')}")
        print(f"  Education: {cleaned_data.get('education')}")
        
    except Exception as e:
        print(f"✗ Error: {e}")

def test_database_saver():
    """Test the database saver"""
    print("\n=== Testing Database Saver ===")
    
    # Sample cleaned data
    cleaned_data = {
        'url': 'https://example.com/job/test-123',
        'source': 'test',
        'title_raw': 'Senior Data Analyst',
        'title_family': 'data_analytics',
        'title_canonical': 'data analyst',
        'company_name': 'Tech Corp',
        'location_raw': 'Nairobi, Kenya',
        'country': 'Kenya',
        'region': 'Nairobi',
        'city': 'Nairobi',
        'description_raw': 'We are looking for a data analyst with SQL and Python skills.',
        'requirements_raw': 'Bachelor\'s degree, 3+ years experience',
        'salary_min': 80000.0,
        'salary_max': 120000.0,
        'currency': 'KES',
        'employment_type': 'full-time',
        'seniority': 'senior',
        'skills': ['sql', 'python'],
        'education': 'bachelors'
    }
    
    saver = JobDatabaseSaver()
    
    try:
        job_id = saver.save_job_data(cleaned_data)
        
        if job_id:
            print(f"✓ Successfully saved job with ID: {job_id}")
            
            # Get stats
            stats = saver.get_job_stats()
            print(f"  Total jobs in DB: {stats.get('total_jobs', 0)}")
            print(f"  Total organizations: {stats.get('total_organizations', 0)}")
            print(f"  Total locations: {stats.get('total_locations', 0)}")
            print(f"  Total skills: {stats.get('total_skills', 0)}")
        else:
            print("✗ Failed to save job data")
            
    except Exception as e:
        print(f"✗ Error: {e}")

async def test_full_pipeline():
    """Test the complete processing pipeline"""
    print("\n=== Testing Full Pipeline ===")
    
    service = JobProcessorService()
    
    # Test health check
    try:
        health = await service.health_check()
        print(f"Health check: {health.get('status', 'unknown')}")
        
        if health.get('status') == 'healthy':
            print("✓ Pipeline is healthy")
        else:
            print(f"✗ Pipeline unhealthy: {health.get('error', 'unknown error')}")
            
    except Exception as e:
        print(f"✗ Health check failed: {e}")
    
    # Test processing a single URL (replace with actual URL for real testing)
    test_url = "https://example.com/test-job"
    
    try:
        print(f"\nTesting single URL processing: {test_url}")
        job_id = await service.process_single_url(test_url, 'test')
        
        if job_id:
            print(f"✓ Successfully processed job with ID: {job_id}")
        else:
            print("✗ Failed to process job (this is expected for example URL)")
            
    except Exception as e:
        print(f"✗ Error processing URL: {e}")
    
    # Get processing stats
    try:
        stats = service.get_stats()
        print(f"\nProcessing Statistics:")
        print(f"  Total jobs: {stats.get('total_jobs', 0)}")
        print(f"  Jobs by source: {stats.get('jobs_by_source', {})}")
        print(f"  Recent jobs (7 days): {stats.get('recent_jobs_7_days', 0)}")
        
    except Exception as e:
        print(f"✗ Error getting stats: {e}")

async def main():
    """Run all tests"""
    print("Starting Job Processor Tests")
    print("=" * 50)
    
    # Test individual components
    await test_job_extractor()
    test_data_cleaner()
    test_database_saver()
    
    # Test full pipeline
    await test_full_pipeline()
    
    print("\n" + "=" * 50)
    print("Tests completed!")

if __name__ == "__main__":
    asyncio.run(main())

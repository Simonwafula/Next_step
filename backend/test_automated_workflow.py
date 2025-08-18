"""
Test script for the automated workflow system
"""
import asyncio
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.services.automated_workflow_service import automated_workflow_service
from app.tasks.workflow_tasks import run_daily_workflow
from app.tasks.scraper_tasks import test_all_scrapers
from app.tasks.processing_tasks import process_raw_jobs
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_scraper_configurations():
    """Test all scraper configurations"""
    logger.info("Testing scraper configurations...")
    
    try:
        # Get scraper configs
        configs = await automated_workflow_service._get_scraper_configs()
        logger.info(f"Found {len(configs)} scraper configurations")
        
        # Test each scraper
        test_results = {}
        for site_name, config in configs.items():
            logger.info(f"Testing scraper for {site_name}...")
            test_result = await automated_workflow_service._test_scraper(site_name, config)
            test_results[site_name] = test_result
            
            status = test_result.get('status', 'unknown')
            response_time = test_result.get('response_time', 0)
            jobs_found = test_result.get('sample_jobs_found', 0)
            
            logger.info(f"  {site_name}: {status} ({response_time:.2f}s, {jobs_found} jobs found)")
        
        # Calculate success rate
        successful = sum(1 for result in test_results.values() if result.get('status') == 'success')
        success_rate = successful / len(test_results) if test_results else 0
        
        logger.info(f"Scraper test summary: {successful}/{len(test_results)} successful ({success_rate:.1%})")
        
        return test_results
        
    except Exception as e:
        logger.error(f"Scraper configuration test failed: {str(e)}")
        raise

async def test_workflow_stages():
    """Test individual workflow stages"""
    logger.info("Testing workflow stages...")
    
    async for db in get_db():
        try:
            # Test scraper stage
            logger.info("Testing scraper stage...")
            scraper_results = await automated_workflow_service._run_scraper_stage(db)
            logger.info(f"Scraper stage: {scraper_results.get('status', 'unknown')}")
            
            # Test processing stage
            logger.info("Testing processing stage...")
            processing_results = await automated_workflow_service._run_processing_stage(db)
            logger.info(f"Processing stage: {processing_results.get('status', 'unknown')}")
            
            # Test learning stage
            logger.info("Testing learning stage...")
            learning_results = await automated_workflow_service._run_learning_stage(db)
            logger.info(f"Learning stage: {learning_results.get('status', 'unknown')}")
            
            # Test optimization stage
            logger.info("Testing optimization stage...")
            optimization_results = await automated_workflow_service._run_optimization_stage(db)
            logger.info(f"Optimization stage: {optimization_results.get('status', 'unknown')}")
            
            # Test insights generation
            logger.info("Testing insights generation...")
            insights_results = await automated_workflow_service._generate_insights(db)
            logger.info(f"Insights stage: {insights_results.get('status', 'unknown')}")
            
            return {
                "scraper": scraper_results,
                "processing": processing_results,
                "learning": learning_results,
                "optimization": optimization_results,
                "insights": insights_results
            }
            
        except Exception as e:
            logger.error(f"Workflow stage test failed: {str(e)}")
            raise
        finally:
            await db.close()

async def test_complete_workflow():
    """Test the complete automated workflow"""
    logger.info("Testing complete automated workflow...")
    
    async for db in get_db():
        try:
            workflow_results = await automated_workflow_service.run_complete_workflow(db)
            
            logger.info(f"Complete workflow: {workflow_results.get('status', 'unknown')}")
            logger.info(f"Duration: {workflow_results.get('duration_minutes', 0):.2f} minutes")
            
            # Log stage results
            stages = workflow_results.get('stages', {})
            for stage_name, stage_result in stages.items():
                status = stage_result.get('status', 'unknown')
                logger.info(f"  {stage_name}: {status}")
            
            return workflow_results
            
        except Exception as e:
            logger.error(f"Complete workflow test failed: {str(e)}")
            raise
        finally:
            await db.close()

async def test_database_integration():
    """Test database integration and data quality"""
    logger.info("Testing database integration...")
    
    async for db in get_db():
        try:
            from sqlalchemy import select, func
            from app.db.models import JobPost, Organization, Skill, TitleNorm
            
            # Check job posts
            job_count_result = await db.execute(select(func.count(JobPost.id)))
            job_count = job_count_result.scalar()
            logger.info(f"Total job posts: {job_count}")
            
            # Check organizations
            org_count_result = await db.execute(select(func.count(Organization.id)))
            org_count = org_count_result.scalar()
            logger.info(f"Total organizations: {org_count}")
            
            # Check skills
            skill_count_result = await db.execute(select(func.count(Skill.id)))
            skill_count = skill_count_result.scalar()
            logger.info(f"Total skills: {skill_count}")
            
            # Check title normalizations
            title_norm_result = await db.execute(select(func.count(TitleNorm.id)))
            title_norm_count = title_norm_result.scalar()
            logger.info(f"Total title normalizations: {title_norm_count}")
            
            # Check recent jobs
            from datetime import datetime, timedelta
            recent_cutoff = datetime.utcnow() - timedelta(days=7)
            recent_jobs_result = await db.execute(
                select(func.count(JobPost.id)).where(JobPost.first_seen >= recent_cutoff)
            )
            recent_jobs = recent_jobs_result.scalar()
            logger.info(f"Jobs from last 7 days: {recent_jobs}")
            
            return {
                "total_jobs": job_count,
                "total_organizations": org_count,
                "total_skills": skill_count,
                "total_title_norms": title_norm_count,
                "recent_jobs": recent_jobs
            }
            
        except Exception as e:
            logger.error(f"Database integration test failed: {str(e)}")
            raise
        finally:
            await db.close()

async def test_quality_scoring():
    """Test job quality scoring system"""
    logger.info("Testing quality scoring system...")
    
    # Test with sample job data
    sample_jobs = [
        {
            "title": "Senior Software Engineer",
            "description": "We are looking for an experienced software engineer to join our team. You will be responsible for developing high-quality software solutions using modern technologies. Requirements include 5+ years of experience in Python, JavaScript, and cloud platforms.",
            "requirements": "Bachelor's degree in Computer Science, 5+ years Python experience, AWS knowledge, strong problem-solving skills",
            "company": "Tech Solutions Ltd",
            "location": "Nairobi, Kenya",
            "salary_min": 150000,
            "salary_max": 200000
        },
        {
            "title": "Dev",
            "description": "Job",
            "requirements": "",
            "company": "",
            "location": "",
            "salary_min": None,
            "salary_max": None
        }
    ]
    
    quality_scores = []
    for i, job_data in enumerate(sample_jobs):
        score = await automated_workflow_service._calculate_job_quality_score(job_data)
        quality_scores.append(score)
        logger.info(f"Sample job {i+1} quality score: {score:.2f}")
    
    logger.info(f"Average quality score: {sum(quality_scores)/len(quality_scores):.2f}")
    
    return quality_scores

def test_celery_tasks():
    """Test Celery task definitions"""
    logger.info("Testing Celery task definitions...")
    
    try:
        from app.core.celery_app import celery_app
        
        # Check if tasks are registered
        registered_tasks = list(celery_app.tasks.keys())
        logger.info(f"Registered Celery tasks: {len(registered_tasks)}")
        
        workflow_tasks = [task for task in registered_tasks if 'workflow_tasks' in task]
        scraper_tasks = [task for task in registered_tasks if 'scraper_tasks' in task]
        processing_tasks = [task for task in registered_tasks if 'processing_tasks' in task]
        
        logger.info(f"Workflow tasks: {len(workflow_tasks)}")
        logger.info(f"Scraper tasks: {len(scraper_tasks)}")
        logger.info(f"Processing tasks: {len(processing_tasks)}")
        
        return {
            "total_tasks": len(registered_tasks),
            "workflow_tasks": workflow_tasks,
            "scraper_tasks": scraper_tasks,
            "processing_tasks": processing_tasks
        }
        
    except Exception as e:
        logger.error(f"Celery task test failed: {str(e)}")
        raise

async def run_all_tests():
    """Run all automated workflow tests"""
    logger.info("Starting automated workflow system tests...")
    
    test_results = {}
    
    try:
        # Test 1: Scraper configurations
        test_results["scraper_configs"] = await test_scraper_configurations()
        
        # Test 2: Database integration
        test_results["database_integration"] = await test_database_integration()
        
        # Test 3: Quality scoring
        test_results["quality_scoring"] = await test_quality_scoring()
        
        # Test 4: Celery tasks
        test_results["celery_tasks"] = test_celery_tasks()
        
        # Test 5: Individual workflow stages
        test_results["workflow_stages"] = await test_workflow_stages()
        
        # Test 6: Complete workflow (optional - can be time-consuming)
        # test_results["complete_workflow"] = await test_complete_workflow()
        
        logger.info("All tests completed successfully!")
        
        return test_results
        
    except Exception as e:
        logger.error(f"Test suite failed: {str(e)}")
        raise

if __name__ == "__main__":
    # Run the test suite
    asyncio.run(run_all_tests())

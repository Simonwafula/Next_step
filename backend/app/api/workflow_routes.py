from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional
import logging

from ..db.database import get_db, SessionLocal
from ..services.automated_workflow_service import automated_workflow_service
from ..services.auth_service import get_current_user
from ..services.processing_log_service import (
    log_processing_event_async,
    update_processing_event,
)
from ..db.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/workflow", tags=["workflow"])


async def _run_insights_async() -> Dict[str, Any]:
    async for db in get_db():
        try:
            return await automated_workflow_service._generate_insights(db)
        finally:
            await db.close()


def _run_insights_with_log(log_id: int) -> None:
    db = SessionLocal()
    try:
        result = asyncio.run(_run_insights_async())
        update_processing_event(
            db,
            log_id=log_id,
            status="success",
            message="Insights generation completed",
            details={"result": result},
        )
    except Exception as exc:
        update_processing_event(
            db,
            log_id=log_id,
            status="error",
            message=str(exc),
        )
    finally:
        db.close()

@router.post("/run-complete")
async def run_complete_workflow(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Trigger the complete automated workflow:
    1. Test and run scrapers
    2. Process and clean data
    3. Extract knowledge and learn
    4. Optimize models
    5. Generate insights
    """
    try:
        log = await log_processing_event_async(
            db,
            process_type="run_complete_workflow",
            status="started",
            message="Complete workflow queued by admin",
            details={"triggered_by": current_user.email},
        )

        # Run workflow in background
        background_tasks.add_task(
            automated_workflow_service.run_complete_workflow,
            db
        )
        
        return {
            "status": "started",
            "message": "Complete automated workflow has been started in the background",
            "log_id": log.id,
            "workflow_stages": [
                "scraper_testing_and_execution",
                "data_processing_and_cleaning", 
                "knowledge_extraction_and_learning",
                "model_optimization",
                "insights_generation"
            ]
        }
        
    except Exception as e:
        logger.error(f"Failed to start complete workflow: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to start workflow: {str(e)}")

@router.post("/run-scraper-stage")
async def run_scraper_stage(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Run only the scraper testing and execution stage
    """
    try:
        background_tasks.add_task(
            automated_workflow_service._run_scraper_stage,
            db
        )
        
        return {
            "status": "started",
            "message": "Scraper stage has been started in the background",
            "stage": "scraper_testing_and_execution"
        }
        
    except Exception as e:
        logger.error(f"Failed to start scraper stage: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to start scraper stage: {str(e)}")

@router.post("/run-processing-stage")
async def run_processing_stage(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Run only the data processing and cleaning stage
    """
    try:
        background_tasks.add_task(
            automated_workflow_service._run_processing_stage,
            db
        )
        
        return {
            "status": "started",
            "message": "Processing stage has been started in the background",
            "stage": "data_processing_and_cleaning"
        }
        
    except Exception as e:
        logger.error(f"Failed to start processing stage: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to start processing stage: {str(e)}")

@router.post("/run-learning-stage")
async def run_learning_stage(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Run only the knowledge extraction and learning stage
    """
    try:
        background_tasks.add_task(
            automated_workflow_service._run_learning_stage,
            db
        )
        
        return {
            "status": "started",
            "message": "Learning stage has been started in the background",
            "stage": "knowledge_extraction_and_learning"
        }
        
    except Exception as e:
        logger.error(f"Failed to start learning stage: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to start learning stage: {str(e)}")

@router.post("/test-scrapers")
async def test_scrapers(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Test all scraper configurations without running full scraping
    """
    try:
        # Get scraper configs
        scraper_configs = await automated_workflow_service._get_scraper_configs()
        
        test_results = {}
        for site_name, config in scraper_configs.items():
            test_result = await automated_workflow_service._test_scraper(site_name, config)
            test_results[site_name] = test_result
        
        # Calculate summary
        total_scrapers = len(test_results)
        successful_scrapers = sum(1 for result in test_results.values() if result["status"] == "success")
        
        response = {
            "status": "completed",
            "summary": {
                "total_scrapers": total_scrapers,
                "successful_scrapers": successful_scrapers,
                "success_rate": successful_scrapers / total_scrapers if total_scrapers > 0 else 0
            },
            "detailed_results": test_results
        }
        await log_processing_event_async(
            db,
            process_type="test_scrapers",
            status="success",
            message="Scraper test completed",
            details={
                "summary": response["summary"],
                "triggered_by": current_user.email,
            },
        )
        return response
        
    except Exception as e:
        logger.error(f"Failed to test scrapers: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to test scrapers: {str(e)}")

@router.get("/scraper-configs")
async def get_scraper_configs(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get current scraper configurations
    """
    try:
        configs = await automated_workflow_service._get_scraper_configs()
        
        return {
            "status": "success",
            "scraper_configs": configs,
            "total_sites": len(configs)
        }
        
    except Exception as e:
        logger.error(f"Failed to get scraper configs: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get scraper configs: {str(e)}")

@router.post("/generate-insights")
async def generate_insights(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Generate market insights and daily metrics
    """
    try:
        log = await log_processing_event_async(
            db,
            process_type="generate_insights",
            status="started",
            message="Insights generation queued by admin",
            details={"triggered_by": current_user.email},
        )

        background_tasks.add_task(_run_insights_with_log, log.id)
        
        return {
            "status": "started",
            "message": "Insights generation has been started in the background",
            "log_id": log.id,
            "stage": "insights_generation"
        }
        
    except Exception as e:
        logger.error(f"Failed to start insights generation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to start insights generation: {str(e)}")

@router.get("/workflow-status")
async def get_workflow_status(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get current workflow execution status
    """
    # This would typically check a workflow status table or cache
    # For now, return a basic status
    return {
        "status": "ready",
        "message": "Workflow system is ready to execute",
        "available_stages": [
            "scraper_testing_and_execution",
            "data_processing_and_cleaning",
            "knowledge_extraction_and_learning", 
            "model_optimization",
            "insights_generation"
        ]
    }

@router.post("/schedule-workflow")
async def schedule_workflow(
    schedule_config: Dict[str, Any],
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Schedule automated workflow to run at specified intervals
    """
    try:
        # This would integrate with Celery Beat for scheduling
        # For now, return a placeholder response
        
        return {
            "status": "scheduled",
            "message": "Automated workflow has been scheduled",
            "schedule": schedule_config,
            "note": "Celery Beat integration required for actual scheduling"
        }
        
    except Exception as e:
        logger.error(f"Failed to schedule workflow: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to schedule workflow: {str(e)}")

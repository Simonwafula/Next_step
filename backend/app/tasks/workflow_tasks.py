from celery import current_task
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any

from ..core.celery_app import celery_app
from ..db.database import get_db, SessionLocal
from ..services.automated_workflow_service import automated_workflow_service
from ..services.processing_log_service import log_processing_event

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="app.tasks.workflow_tasks.run_daily_workflow")
def run_daily_workflow(self):
    """
    Run the complete daily automated workflow
    """
    try:
        # Update task status
        self.update_state(
            state="PROGRESS", meta={"status": "Starting daily workflow", "progress": 0}
        )

        # Run the async workflow
        result = asyncio.run(_run_async_workflow())

        # Update final status
        self.update_state(
            state="SUCCESS",
            meta={
                "status": "Daily workflow completed successfully",
                "progress": 100,
                "result": result,
            },
        )

        db = SessionLocal()
        try:
            log_processing_event(
                db,
                process_type="daily_workflow",
                status="success",
                message="Daily workflow completed",
                details={"result": result},
            )
        finally:
            db.close()
        return result

    except Exception as e:
        logger.error(f"Daily workflow failed: {str(e)}")
        db = SessionLocal()
        try:
            log_processing_event(
                db,
                process_type="daily_workflow",
                status="error",
                message=str(e),
            )
        finally:
            db.close()
        self.update_state(
            state="FAILURE",
            meta={"status": f"Daily workflow failed: {str(e)}", "progress": 0},
        )
        raise


@celery_app.task(bind=True, name="app.tasks.workflow_tasks.run_scraper_stage")
def run_scraper_stage(self):
    """
    Run only the scraper testing and execution stage
    """
    try:
        self.update_state(
            state="PROGRESS", meta={"status": "Starting scraper stage", "progress": 0}
        )

        result = asyncio.run(_run_async_scraper_stage())

        self.update_state(
            state="SUCCESS",
            meta={
                "status": "Scraper stage completed successfully",
                "progress": 100,
                "result": result,
            },
        )

        return result

    except Exception as e:
        logger.error(f"Scraper stage failed: {str(e)}")
        self.update_state(
            state="FAILURE",
            meta={"status": f"Scraper stage failed: {str(e)}", "progress": 0},
        )
        raise


@celery_app.task(bind=True, name="app.tasks.workflow_tasks.run_processing_stage")
def run_processing_stage(self):
    """
    Run only the data processing and cleaning stage
    """
    try:
        self.update_state(
            state="PROGRESS",
            meta={"status": "Starting processing stage", "progress": 0},
        )

        result = asyncio.run(_run_async_processing_stage())

        self.update_state(
            state="SUCCESS",
            meta={
                "status": "Processing stage completed successfully",
                "progress": 100,
                "result": result,
            },
        )

        return result

    except Exception as e:
        logger.error(f"Processing stage failed: {str(e)}")
        self.update_state(
            state="FAILURE",
            meta={"status": f"Processing stage failed: {str(e)}", "progress": 0},
        )
        raise


@celery_app.task(bind=True, name="app.tasks.workflow_tasks.run_learning_stage")
def run_learning_stage(self):
    """
    Run only the knowledge extraction and learning stage
    """
    try:
        self.update_state(
            state="PROGRESS", meta={"status": "Starting learning stage", "progress": 0}
        )

        result = asyncio.run(_run_async_learning_stage())

        self.update_state(
            state="SUCCESS",
            meta={
                "status": "Learning stage completed successfully",
                "progress": 100,
                "result": result,
            },
        )

        return result

    except Exception as e:
        logger.error(f"Learning stage failed: {str(e)}")
        self.update_state(
            state="FAILURE",
            meta={"status": f"Learning stage failed: {str(e)}", "progress": 0},
        )
        raise


@celery_app.task(bind=True, name="app.tasks.workflow_tasks.generate_daily_insights")
def generate_daily_insights(self):
    """
    Generate daily market insights and metrics
    """
    try:
        self.update_state(
            state="PROGRESS",
            meta={"status": "Starting insights generation", "progress": 0},
        )

        result = asyncio.run(_run_async_insights_generation())

        self.update_state(
            state="SUCCESS",
            meta={
                "status": "Insights generation completed successfully",
                "progress": 100,
                "result": result,
            },
        )

        db = SessionLocal()
        try:
            log_processing_event(
                db,
                process_type="daily_insights",
                status="success",
                message="Daily insights completed",
                details={"result": result},
            )
        finally:
            db.close()
        return result

    except Exception as e:
        logger.error(f"Insights generation failed: {str(e)}")
        db = SessionLocal()
        try:
            log_processing_event(
                db,
                process_type="daily_insights",
                status="error",
                message=str(e),
            )
        finally:
            db.close()
        self.update_state(
            state="FAILURE",
            meta={"status": f"Insights generation failed: {str(e)}", "progress": 0},
        )
        raise


@celery_app.task(bind=True, name="app.tasks.workflow_tasks.run_optimization_stage")
def run_optimization_stage(self):
    """
    Run model optimization stage
    """
    try:
        self.update_state(
            state="PROGRESS",
            meta={"status": "Starting optimization stage", "progress": 0},
        )

        result = asyncio.run(_run_async_optimization_stage())

        self.update_state(
            state="SUCCESS",
            meta={
                "status": "Optimization stage completed successfully",
                "progress": 100,
                "result": result,
            },
        )

        return result

    except Exception as e:
        logger.error(f"Optimization stage failed: {str(e)}")
        self.update_state(
            state="FAILURE",
            meta={"status": f"Optimization stage failed: {str(e)}", "progress": 0},
        )
        raise


# Async helper functions
async def _run_async_workflow() -> Dict[str, Any]:
    """Run the complete workflow asynchronously"""
    async for db in get_db():
        try:
            result = await automated_workflow_service.run_complete_workflow(db)
            return result
        finally:
            await db.close()


async def _run_async_scraper_stage() -> Dict[str, Any]:
    """Run scraper stage asynchronously"""
    async for db in get_db():
        try:
            result = await automated_workflow_service._run_scraper_stage(db)
            return result
        finally:
            await db.close()


async def _run_async_processing_stage() -> Dict[str, Any]:
    """Run processing stage asynchronously"""
    async for db in get_db():
        try:
            result = await automated_workflow_service._run_processing_stage(db)
            return result
        finally:
            await db.close()


async def _run_async_learning_stage() -> Dict[str, Any]:
    """Run learning stage asynchronously"""
    async for db in get_db():
        try:
            result = await automated_workflow_service._run_learning_stage(db)
            return result
        finally:
            await db.close()


async def _run_async_insights_generation() -> Dict[str, Any]:
    """Run insights generation asynchronously"""
    async for db in get_db():
        try:
            result = await automated_workflow_service._generate_insights(db)
            return result
        finally:
            await db.close()


async def _run_async_optimization_stage() -> Dict[str, Any]:
    """Run optimization stage asynchronously"""
    async for db in get_db():
        try:
            result = await automated_workflow_service._run_optimization_stage(db)
            return result
        finally:
            await db.close()

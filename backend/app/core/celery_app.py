from celery import Celery
from .config import settings
import logging

logger = logging.getLogger(__name__)

# Create Celery instance
celery_app = Celery(
    "nextstep_workflows",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.tasks.workflow_tasks",
        "app.tasks.scraper_tasks",
        "app.tasks.gov_monitor_tasks",
        "app.tasks.processing_tasks"
    ]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    result_expires=3600,  # 1 hour
    beat_schedule={
        # Run complete workflow daily at 2 AM
        'daily-complete-workflow': {
            'task': 'app.tasks.workflow_tasks.run_daily_workflow',
            'schedule': 60.0 * 60.0 * 24.0,  # 24 hours
            'options': {'queue': 'workflow'}
        },
        # Run scraper tests every 6 hours
        'scraper-health-check': {
            'task': 'app.tasks.scraper_tasks.test_all_scrapers',
            'schedule': 60.0 * 60.0 * 6.0,  # 6 hours
            'options': {'queue': 'scrapers'}
        },
        # Monitor government career pages every 6 hours
        'gov-source-monitor': {
            'task': 'app.tasks.gov_monitor_tasks.run_government_sources',
            'schedule': 60.0 * 60.0 * 6.0,  # 6 hours
            'options': {'queue': 'scrapers'}
        },
        # Generate insights every 4 hours
        'generate-insights': {
            'task': 'app.tasks.workflow_tasks.generate_daily_insights',
            'schedule': 60.0 * 60.0 * 4.0,  # 4 hours
            'options': {'queue': 'insights'}
        }
    },
    task_routes={
        'app.tasks.workflow_tasks.*': {'queue': 'workflow'},
        'app.tasks.scraper_tasks.*': {'queue': 'scrapers'},
        'app.tasks.gov_monitor_tasks.*': {'queue': 'scrapers'},
        'app.tasks.processing_tasks.*': {'queue': 'processing'},
    }
)

# Configure logging
celery_app.conf.worker_log_format = '[%(asctime)s: %(levelname)s/%(processName)s] %(message)s'
celery_app.conf.worker_task_log_format = '[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s'

if __name__ == '__main__':
    celery_app.start()

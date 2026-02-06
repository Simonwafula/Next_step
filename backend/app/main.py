from datetime import datetime, timedelta
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, func, text
from .core.config import settings
from .core.rate_limiter import rate_limit_middleware
from .core.logging_config import setup_logging, logging_middleware, get_logger
from .db.database import init_db, SessionLocal, DATABASE_URL
from .db.models import JobPost, Organization
from .api.routes import api_router
from .api.admin_routes import router as admin_router
from .api.workflow_routes import router as workflow_router
from .api.integration_routes import router as integration_router
from .webhooks.whatsapp import router as whatsapp_router

# Initialize logging
setup_logging()
logger = get_logger(__name__)

app = FastAPI(title="Career Translator + LMI", version="0.1.0")

# Logging middleware (request tracing)
app.middleware("http")(logging_middleware)

# Rate limiting middleware
app.middleware("http")(rate_limit_middleware)

# CORS
origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
allow_credentials = True
allow_origins = origins

# Browsers will reject `Access-Control-Allow-Credentials: true` when the origin is `*`.
if not allow_origins:
    allow_credentials = False
elif "*" in allow_origins:
    allow_origins = ["*"]
    allow_credentials = False

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event():
    logger.info("Application starting up...")
    init_db()
    logger.info("Database initialized successfully")


@app.get("/health")
def health():
    """Basic health check - returns ok if app is running"""
    return {"ok": True, "timestamp": datetime.utcnow().isoformat()}


@app.get("/health/detailed")
def health_detailed():
    """Detailed health check including database connectivity"""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {},
    }

    # Check database connectivity
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        health_status["checks"]["database"] = {
            "status": "healthy",
            "type": "sqlite" if "sqlite" in DATABASE_URL else "postgresql",
        }
        db.close()
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["checks"]["database"] = {"status": "unhealthy", "error": str(e)}

    return health_status


@app.get("/api/ingestion/status")
def ingestion_status():
    """Get current ingestion status and metrics"""
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        last_24h = now - timedelta(hours=24)
        last_7d = now - timedelta(days=7)

        # Total jobs
        total_jobs = db.execute(select(func.count(JobPost.id))).scalar() or 0

        # Jobs by source
        source_counts = db.execute(
            select(JobPost.source, func.count(JobPost.id)).group_by(JobPost.source)
        ).all()

        # Recent ingestion (last 24h)
        jobs_last_24h = (
            db.execute(
                select(func.count(JobPost.id)).where(JobPost.first_seen >= last_24h)
            ).scalar()
            or 0
        )

        # Last 7 days
        jobs_last_7d = (
            db.execute(
                select(func.count(JobPost.id)).where(JobPost.first_seen >= last_7d)
            ).scalar()
            or 0
        )

        # Latest job timestamp
        latest_job = db.execute(select(func.max(JobPost.first_seen))).scalar()

        # Data quality metrics
        jobs_with_org = (
            db.execute(
                select(func.count(JobPost.id)).where(JobPost.org_id.is_not(None))
            ).scalar()
            or 0
        )

        jobs_with_location = (
            db.execute(
                select(func.count(JobPost.id)).where(JobPost.location_id.is_not(None))
            ).scalar()
            or 0
        )

        jobs_with_salary = (
            db.execute(
                select(func.count(JobPost.id)).where(JobPost.salary_min.is_not(None))
            ).scalar()
            or 0
        )

        return {
            "status": "operational",
            "timestamp": now.isoformat(),
            "totals": {
                "jobs": total_jobs,
                "organizations": db.execute(
                    select(func.count(Organization.id))
                ).scalar()
                or 0,
            },
            "sources": {source: count for source, count in source_counts},
            "ingestion": {
                "last_24h": jobs_last_24h,
                "last_7d": jobs_last_7d,
                "latest_job": latest_job.isoformat() if latest_job else None,
                "ingestion_rate_24h": round(jobs_last_24h / 24, 1)
                if jobs_last_24h
                else 0,
            },
            "data_quality": {
                "with_organization": {
                    "count": jobs_with_org,
                    "percentage": round(jobs_with_org / total_jobs * 100, 1)
                    if total_jobs
                    else 0,
                },
                "with_location": {
                    "count": jobs_with_location,
                    "percentage": round(jobs_with_location / total_jobs * 100, 1)
                    if total_jobs
                    else 0,
                },
                "with_salary": {
                    "count": jobs_with_salary,
                    "percentage": round(jobs_with_salary / total_jobs * 100, 1)
                    if total_jobs
                    else 0,
                },
            },
        }
    except Exception as e:
        return {
            "status": "error",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e),
        }
    finally:
        db.close()


# API routers
app.include_router(api_router, prefix="/api")
app.include_router(admin_router)
app.include_router(workflow_router)
app.include_router(integration_router)
app.include_router(whatsapp_router, prefix="/whatsapp")

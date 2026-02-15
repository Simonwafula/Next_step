from datetime import datetime, timedelta

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy import func, select, text
from starlette.exceptions import HTTPException as StarletteHTTPException

from .api.admin_routes import router as admin_router
from .api.admin_audit_routes import router as admin_audit_router
from .api.admin_dedup_routes import router as admin_dedup_router
from .api.admin_moderation_routes import router as admin_moderation_router
from .api.beta_routes import router as beta_router
from .api.career_insight_routes import router as career_insight_router
from .api.redirect_routes import router as redirect_router
from .api.routes import api_router
from .api.workflow_routes import router as workflow_router
from .core.config import settings
from .core.logging_config import get_logger, logging_middleware, setup_logging
from .core.rate_limiter import rate_limit_middleware
from .db.database import DATABASE_URL, SessionLocal, init_db
from .db.models import JobPost, Organization
from .webhooks.whatsapp import router as whatsapp_router

setup_logging()
logger = get_logger(__name__)

app = FastAPI(title="Career Translator + LMI", version="0.1.0")

app.middleware("http")(logging_middleware)

app.middleware("http")(rate_limit_middleware)

origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
allow_credentials = True
allow_origins = origins

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

        total_jobs = db.execute(select(func.count(JobPost.id))).scalar() or 0

        source_counts = db.execute(
            select(JobPost.source, func.count(JobPost.id)).group_by(JobPost.source)
        ).all()

        jobs_last_24h = (
            db.execute(
                select(func.count(JobPost.id)).where(JobPost.first_seen >= last_24h)
            ).scalar()
            or 0
        )

        jobs_last_7d = (
            db.execute(
                select(func.count(JobPost.id)).where(JobPost.first_seen >= last_7d)
            ).scalar()
            or 0
        )

        latest_job = db.execute(select(func.max(JobPost.first_seen))).scalar()

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


def _wants_json(request: Request) -> bool:
    accept = request.headers.get("accept", "")
    return "application/json" in accept


def _error_html(code: int, title: str, message: str) -> str:
    return (
        "<!DOCTYPE html><html lang='en'><head><meta charset='UTF-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>{title} - NextStep Careers</title>"
        "<style>"
        "body{{font-family:system-ui,sans-serif;background:#faf8f5;color:#1a1a2e;"
        "display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0}}"
        ".card{{text-align:center;max-width:420px;padding:2rem}}"
        ".code{{font-size:4rem;font-weight:700;color:#0d9488}}"
        "h1{{margin:.5rem 0;font-size:1.3rem}}"
        "p{{color:#555;line-height:1.5;margin-bottom:1.5rem}}"
        "a{{color:#0d9488;text-decoration:none;font-weight:500}}"
        "</style></head><body><div class='card'>"
        "<div class='code'>{code}</div>"
        "<h1>{title}</h1><p>{message}</p>"
        "<a href='/'>Back to home</a>"
        "</div></body></html>"
    ).format(code=code, title=title, message=message)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    code = exc.status_code
    detail = exc.detail or "An error occurred"

    if _wants_json(request):
        return JSONResponse(
            status_code=code,
            content={"detail": detail},
        )

    titles = {
        403: "Access denied",
        404: "Page not found",
        500: "Something went wrong",
    }
    messages = {
        403: "You don't have permission to access this resource.",
        404: "The page you're looking for doesn't exist or may have been moved.",
        500: "We hit an unexpected error. Please try again in a moment.",
    }

    return HTMLResponse(
        status_code=code,
        content=_error_html(
            code,
            titles.get(code, f"Error {code}"),
            messages.get(code, str(detail)),
        ),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception: %s", exc, exc_info=True)

    if _wants_json(request):
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )

    return HTMLResponse(
        status_code=500,
        content=_error_html(
            500,
            "Something went wrong",
            "We hit an unexpected error. Please try again in a moment.",
        ),
    )


app.include_router(redirect_router)
app.include_router(api_router, prefix="/api")
app.include_router(beta_router, prefix="/api")
app.include_router(admin_router)
app.include_router(admin_audit_router)
app.include_router(admin_dedup_router)
app.include_router(admin_moderation_router)
app.include_router(workflow_router)
app.include_router(career_insight_router, prefix="/api")
app.include_router(whatsapp_router, prefix="/whatsapp")

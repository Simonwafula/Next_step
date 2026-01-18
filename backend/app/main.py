from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from .core.config import settings
from .db.database import init_db, get_db
from .api.routes import api_router
from .api.admin_routes import router as admin_router
from .api.workflow_routes import router as workflow_router
from .api.integration_routes import router as integration_router
from .webhooks.whatsapp import router as whatsapp_router

app = FastAPI(title="Career Translator + LMI", version="0.1.0")

# CORS
origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    init_db()

@app.get("/health")
def health():
    return {"ok": True}

# API routers
app.include_router(api_router, prefix="/api")
app.include_router(admin_router)
app.include_router(workflow_router)
app.include_router(integration_router)
app.include_router(whatsapp_router, prefix="/whatsapp")

# ruff: noqa: E402

import os
import sys
from pathlib import Path

# Ensure SQLAlchemy models choose SQLite-friendly types (JSON instead of JSONB)
# during import time.
os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("APP_ENV", "dev")

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.models import Base


@pytest.fixture()
def db_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture()
def db_session_factory(db_engine):
    return sessionmaker(bind=db_engine, autocommit=False, autoflush=False)

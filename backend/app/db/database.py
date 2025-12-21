import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from ..core.config import settings

# Allow overriding the database URL via environment for testing (e.g. SQLite)
DATABASE_URL = os.getenv("DATABASE_URL") or (
    f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
    f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
)

# Support async engines when DATABASE_URL indicates an async dialect
if "+async" in DATABASE_URL or DATABASE_URL.startswith("sqlite+aiosqlite"):
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    engine = create_async_engine(DATABASE_URL, future=True)
    SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    USE_ASYNC = True
else:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    USE_ASYNC = False

# If using SQLite for tests, create all tables automatically to avoid requiring
# a running Postgres instance or separate migrations step.
if DATABASE_URL.startswith("sqlite"):
    try:
        from .models import Base  # noqa: F401
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        import traceback
        traceback.print_exc()
        # If model import or create_all fails for any reason, surface the error
        # to aid debugging (tests will still proceed but with missing tables).

def init_db():
    # Ensure pgvector extension
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        conn.commit()
    # Create tables
    from .models import Base  # noqa
    Base.metadata.create_all(bind=engine)

async def get_db():
    """Async generator that yields a sync Session wrapped with async helpers.

    Tests expect `async for db in get_db()` and then to `await db.execute(...)`.
    We provide a minimal async wrapper that runs blocking DB calls in a thread
    executor so tests can `await db.execute(...)` while the underlying session
    remains synchronous (SQLite in-memory for tests).
    """
    import asyncio

    class _AsyncSessionShim:
        def __init__(self, sync_session):
            self._session = sync_session

        async def execute(self, *args, **kwargs):
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, lambda: self._session.execute(*args, **kwargs))

        async def commit(self):
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, lambda: self._session.commit())

        async def rollback(self):
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, lambda: self._session.rollback())

        async def close(self):
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._session.close)

        # Provide access to sync session attributes when needed (e.g., add)
        def __getattr__(self, item):
            return getattr(self._session, item)

    # Ensure tables exist for SQLite in this process before yielding session
    if DATABASE_URL.startswith("sqlite"):
        try:
            from .models import Base  # noqa: F401
            Base.metadata.create_all(bind=engine)
        except Exception:
            pass

    # If configured to use real async sessions, yield an AsyncSession directly
    if USE_ASYNC:
        # SessionLocal is configured to return AsyncSession instances
        async with SessionLocal() as async_db:
            try:
                yield async_db
            finally:
                await async_db.close()

    # Otherwise, provide shim wrapping sync Session
    db = SessionLocal()
    try:
        shim = _AsyncSessionShim(db)
        yield shim
    finally:
        db.close()


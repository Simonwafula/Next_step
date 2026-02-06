import os
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from ..core.config import settings

logger = logging.getLogger(__name__)

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
    except Exception:
        import traceback

        traceback.print_exc()
        # If model import or create_all fails for any reason, surface the error
        # to aid debugging (tests will still proceed but with missing tables).


def init_db():
    # Create tables
    from .models import Base  # noqa

    if DATABASE_URL.startswith("sqlite"):
        Base.metadata.create_all(bind=engine)
        return

    # Postgres: ensure pgvector extension, create tables, then ensure the new
    # vector column exists for existing deployments.
    embedding_dim = settings.EMBEDDING_DIM
    create_index = os.getenv("PGVECTOR_CREATE_INDEX", "").lower() in (
        "1",
        "true",
        "yes",
    )

    with engine.connect() as conn:
        try:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            conn.commit()
        except Exception as exc:
            logger.warning(f"Could not ensure pgvector extension is installed: {exc}")

        Base.metadata.create_all(bind=conn)

        # Backward-compatible schema update for existing `job_post` tables.
        try:
            conn.execute(
                text(
                    "ALTER TABLE IF EXISTS job_post "
                    f"ADD COLUMN IF NOT EXISTS embedding_vector vector({embedding_dim});"
                )
            )
            conn.commit()
        except Exception as exc:
            logger.warning(f"Could not add job_post.embedding_vector column: {exc}")
            # Fall back to TEXT so the app can still start on Postgres without pgvector.
            try:
                conn.execute(
                    text(
                        "ALTER TABLE IF EXISTS job_post "
                        "ADD COLUMN IF NOT EXISTS embedding_vector TEXT;"
                    )
                )
                conn.commit()
                logger.warning(
                    "Added job_post.embedding_vector as TEXT (pgvector unavailable)"
                )
            except Exception as exc2:
                logger.warning(
                    f"Could not add job_post.embedding_vector column as TEXT either: {exc2}"
                )

        if create_index:
            # Index creation can be expensive on large tables; keep it opt-in.
            # Prefer HNSW when available, fall back to IVFFlat.
            try:
                conn.execute(
                    text(
                        "CREATE INDEX IF NOT EXISTS ix_job_post_embedding_vector_hnsw "
                        "ON job_post USING hnsw "
                        "(embedding_vector vector_cosine_ops);"
                    )
                )
                conn.commit()
            except Exception:
                try:
                    conn.execute(
                        text(
                            "CREATE INDEX IF NOT EXISTS ix_job_post_embedding_vector_ivfflat "
                            "ON job_post USING ivfflat "
                            "(embedding_vector vector_cosine_ops) "
                            "WITH (lists = 100);"
                        )
                    )
                    conn.commit()
                except Exception as exc:
                    logger.warning(f"Could not create pgvector index: {exc}")


async def get_db():
    """Async generator that yields a Session compatible with sync + async usage.

    Some tests use `async for db in get_db()` and `await db.execute(...)`,
    while the API code expects sync-style `db.execute(...)`. The hybrid wrapper
    supports both without forcing async engines.
    """

    class _HybridResult:
        def __init__(self, result):
            self._result = result

        def __await__(self):
            async def _wrap():
                return self._result

            return _wrap().__await__()

        def __getattr__(self, item):
            return getattr(self._result, item)

    class _HybridSession:
        def __init__(self, sync_session):
            self._session = sync_session

        def execute(self, *args, **kwargs):
            return _HybridResult(self._session.execute(*args, **kwargs))

        def commit(self):
            return _HybridResult(self._session.commit())

        def rollback(self):
            return _HybridResult(self._session.rollback())

        def close(self):
            return _HybridResult(self._session.close())

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

    # Otherwise, provide a hybrid wrapper around sync Session
    db = SessionLocal()
    try:
        yield _HybridSession(db)
    finally:
        db.close()

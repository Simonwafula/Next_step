from __future__ import annotations

import logging
import uuid
from contextlib import contextmanager
from typing import Iterator

from .config import settings

logger = logging.getLogger(__name__)

_RELEASE_LOCK_LUA = """
if redis.call("get", KEYS[1]) == ARGV[1] then
  return redis.call("del", KEYS[1])
end
return 0
"""


@contextmanager
def redis_lock(key: str, *, ttl_seconds: int) -> Iterator[bool]:
    """Best-effort distributed lock using Redis.

    Yields True if the lock was acquired, False if another worker holds it.
    If Redis is unavailable, yields True (fail-open) and logs a warning.
    """
    token = uuid.uuid4().hex
    try:
        import redis  # Imported lazily to keep import-time side effects minimal.

        client = redis.Redis.from_url(settings.REDIS_URL)
        acquired = bool(client.set(key, token, nx=True, ex=int(ttl_seconds)))
        if not acquired:
            yield False
            return
        try:
            yield True
        finally:
            try:
                client.eval(_RELEASE_LOCK_LUA, 1, key, token)
            except Exception as exc:  # pragma: no cover
                logger.warning("Failed to release redis lock %s: %s", key, exc)
    except Exception as exc:  # pragma: no cover
        logger.warning("Redis unavailable; proceeding without lock (%s): %s", key, exc)
        yield True

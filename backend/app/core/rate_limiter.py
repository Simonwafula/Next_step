"""
Rate limiting middleware for FastAPI.

Uses in-memory storage for development/single-instance deployments.
For production with multiple instances, configure Redis backend.
"""
import time
from collections import defaultdict
from typing import Callable, Optional
from fastapi import HTTPException, Request, status
from functools import wraps
import logging

from .config import settings

logger = logging.getLogger(__name__)


class RateLimiter:
    """Simple in-memory rate limiter using sliding window."""

    def __init__(self):
        # Store: {key: [(timestamp, count), ...]}
        self._requests: dict = defaultdict(list)
        self._cleanup_interval = 60  # seconds
        self._last_cleanup = time.time()

    def _cleanup_old_requests(self, window_seconds: int):
        """Remove expired request records."""
        now = time.time()
        if now - self._last_cleanup < self._cleanup_interval:
            return

        cutoff = now - window_seconds
        for key in list(self._requests.keys()):
            self._requests[key] = [
                (ts, count) for ts, count in self._requests[key]
                if ts > cutoff
            ]
            if not self._requests[key]:
                del self._requests[key]

        self._last_cleanup = now

    def is_allowed(self, key: str, max_requests: int, window_seconds: int = 60) -> tuple[bool, int]:
        """
        Check if request is allowed under rate limit.

        Returns:
            (is_allowed, remaining_requests)
        """
        now = time.time()
        self._cleanup_old_requests(window_seconds)

        cutoff = now - window_seconds
        self._requests[key] = [
            (ts, count) for ts, count in self._requests[key]
            if ts > cutoff
        ]

        current_count = sum(count for _, count in self._requests[key])

        if current_count >= max_requests:
            return False, 0

        self._requests[key].append((now, 1))
        remaining = max_requests - current_count - 1
        return True, remaining

    def get_retry_after(self, key: str, window_seconds: int = 60) -> int:
        """Get seconds until rate limit resets."""
        if key not in self._requests or not self._requests[key]:
            return 0

        oldest_ts = min(ts for ts, _ in self._requests[key])
        retry_after = int(oldest_ts + window_seconds - time.time())
        return max(0, retry_after)


# Global rate limiter instance
rate_limiter = RateLimiter()


def get_client_identifier(request: Request) -> str:
    """
    Get a unique identifier for the client.
    Uses X-Forwarded-For if behind a proxy, otherwise client host.
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()

    if request.client:
        return request.client.host

    return "unknown"


def rate_limit(
    max_requests: Optional[int] = None,
    window_seconds: int = 60,
    key_func: Optional[Callable[[Request], str]] = None
):
    """
    Decorator for rate limiting endpoints.

    Args:
        max_requests: Maximum requests per window (defaults to settings.RATE_LIMIT_PER_MINUTE)
        window_seconds: Time window in seconds
        key_func: Function to generate rate limit key from request

    Usage:
        @app.get("/api/search")
        @rate_limit(max_requests=30, window_seconds=60)
        async def search(...):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request: Optional[Request] = kwargs.get("request")

            if request is None:
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break

            if request is None:
                return await func(*args, **kwargs)

            limit = max_requests or settings.RATE_LIMIT_PER_MINUTE

            if key_func:
                key = key_func(request)
            else:
                client_id = get_client_identifier(request)
                key = f"{request.url.path}:{client_id}"

            allowed, remaining = rate_limiter.is_allowed(key, limit, window_seconds)

            if not allowed:
                retry_after = rate_limiter.get_retry_after(key, window_seconds)
                logger.warning(f"Rate limit exceeded for {key}")
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded. Try again in {retry_after} seconds.",
                    headers={
                        "Retry-After": str(retry_after),
                        "X-RateLimit-Limit": str(limit),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(int(time.time()) + retry_after)
                    }
                )

            return await func(*args, **kwargs)

        return wrapper
    return decorator


async def rate_limit_middleware(request: Request, call_next):
    """
    Global rate limiting middleware.

    Applies a base rate limit to all API endpoints.
    Specific endpoints can have stricter limits via the decorator.
    """
    if not request.url.path.startswith("/api"):
        return await call_next(request)

    if request.url.path in ["/health", "/health/detailed"]:
        return await call_next(request)

    client_id = get_client_identifier(request)
    key = f"global:{client_id}"

    global_limit = settings.RATE_LIMIT_PER_MINUTE * 2

    allowed, remaining = rate_limiter.is_allowed(key, global_limit, 60)

    if not allowed:
        retry_after = rate_limiter.get_retry_after(key, 60)
        logger.warning(f"Global rate limit exceeded for {client_id}")
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "detail": f"Too many requests. Try again in {retry_after} seconds."
            },
            headers={
                "Retry-After": str(retry_after),
                "X-RateLimit-Limit": str(global_limit),
                "X-RateLimit-Remaining": "0"
            }
        )

    response = await call_next(request)

    response.headers["X-RateLimit-Limit"] = str(global_limit)
    response.headers["X-RateLimit-Remaining"] = str(remaining)

    return response

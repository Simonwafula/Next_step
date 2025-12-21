"""Lightweight stub for the `ratelimit` package used in tests.

Provides `limits` and `sleep_and_retry` decorators as no-ops so rate
limiting doesn't interfere with unit tests.
"""
from typing import Callable, Any

def limits(calls: int = 1, period: int = 60):
    def decorator(func: Callable[..., Any]):
        return func
    return decorator

def sleep_and_retry(func: Callable[..., Any]) -> Callable[..., Any]:
    return func

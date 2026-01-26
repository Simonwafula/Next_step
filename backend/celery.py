"""Lightweight stub of the `celery` package for local tests.

This provides a minimal `Celery` class and `current_task` object so the
application modules can import and register tasks without requiring the
real Celery runtime in the dev/test environment.
"""

from typing import Callable, Any


class _Conf(dict):
    def update(self, d: dict | None = None, **kwargs):
        if d:
            super().update(d)
        if kwargs:
            super().update(kwargs)


class Celery:
    def __init__(self, *args, **kwargs):
        self._args = args
        self._kwargs = kwargs
        self.conf = _Conf()
        self.tasks = {}

    def task(
        self, *targs, **tkwargs
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            name = tkwargs.get("name") or func.__name__
            self.tasks[name] = func
            return func

        return decorator

    def start(self):
        # no-op for tests
        return


class _CurrentTask:
    def __init__(self):
        self.request = None


current_task = _CurrentTask()

"""A small in-memory sliding-window rate limiter.

Good for learning and single-process development. With several server
processes (or several servers) each one has its own counters, so a real
deployment should move this to Redis (e.g. `slowapi` / `fastapi-limiter`).
The *usage* in the routes stays the same.
"""
import math
import threading
import time
from collections import defaultdict, deque

from fastapi import Request

from app.core.config import get_settings
from app.utils.errors import AppError

_lock = threading.Lock()
_hits: dict[tuple[str, str], deque[float]] = defaultdict(deque)


class RateLimiter:
    """Use as a route dependency: `dependencies=[Depends(RateLimiter("login", 10, 300))]`."""

    def __init__(self, name: str, max_requests: int, window_seconds: int) -> None:
        self.name = name
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    def __call__(self, request: Request) -> None:
        if not get_settings().rate_limit_enabled:
            return
        client_ip = request.client.host if request.client else "unknown"
        key = (self.name, client_ip)
        now = time.monotonic()
        with _lock:
            window = _hits[key]
            while window and now - window[0] > self.window_seconds:
                window.popleft()
            if len(window) >= self.max_requests:
                retry_after = max(1, math.ceil(self.window_seconds - (now - window[0])))
                raise AppError(
                    429,
                    "RATE_LIMITED",
                    "Too many requests. Please wait a moment and try again.",
                    headers={"Retry-After": str(retry_after)},
                )
            window.append(now)


def reset_rate_limits() -> None:
    with _lock:
        _hits.clear()

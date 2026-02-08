"""
Rate Limiting for Upsonic Gateway

Provides Redis-backed distributed rate limiting for API traffic management.
Supports multiple rate limiting strategies with configurable limits.
"""

from __future__ import annotations

import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

import redis.asyncio as redis


@dataclass
class RateLimitResult:
    """Result of a rate limit check."""

    allowed: bool
    remaining: int
    reset_time: float
    limit_type: str
    retry_after: Optional[float] = None

    def to_headers(self) -> dict[str, str]:
        """Convert to HTTP headers."""
        headers = {
            "X-RateLimit-Limit": str(
                self.remaining + (0 if self.allowed else self.remaining)
            ),
            "X-RateLimit-Remaining": str(
                max(0, self.remaining - (0 if self.allowed else 1))
            ),
            "X-RateLimit-Reset": str(int(self.reset_time)),
        }

        if not self.allowed:
            headers["Retry-After"] = str(int(self.retry_after or 1))

        return headers


class RateLimiter(ABC):
    """Abstract base class for rate limiters."""

    @abstractmethod
    async def check_rate_limit(self, key: str, endpoint: str) -> RateLimitResult:
        """Check if request is allowed under rate limit."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close the rate limiter and cleanup resources."""
        pass


class RedisRateLimiter(RateLimiter):
    """Redis-backed distributed rate limiter using sliding window algorithm."""

    def __init__(
        self,
        redis_url: Optional[str] = None,
        default_limits: Optional[dict[str, tuple[int, int]]] = None,
    ):
        self.redis_url = redis_url or os.environ.get(
            "UPSONIC_REDIS_URL", "redis://localhost:6379/0"
        )
        self.default_limits = default_limits or {
            "default": (100, 60),
            "query": (50, 60),
            "chat": (30, 60),
            "models": (10, 60),
        }

        self._client: Optional[redis.Redis] = None

    async def _get_client(self) -> redis.Redis:
        """Get or create Redis client."""
        if self._client is None:
            self._client = redis.from_url(self.redis_url)
        return self._client

    async def check_rate_limit(
        self, key: str, endpoint: str = "default"
    ) -> RateLimitResult:
        """Check rate limit using Redis sliding window."""
        limit, window = self.default_limits.get(
            endpoint, self.default_limits["default"]
        )

        client = await self._get_client()
        now = time.time()
        window_start = now - window

        pipe = client.pipeline()

        pipe.zremrangebyscore(f"ratelimit:{key}", 0, window_start)
        pipe.zadd(f"ratelimit:{key}", {str(now): now})
        pipe.zcard(f"ratelimit:{key}")
        pipe.expire(f"ratelimit:{key}", window)

        results = await pipe.execute()
        current_count = results[2]

        if current_count < limit:
            return RateLimitResult(
                allowed=True,
                remaining=limit - current_count - 1,
                reset_time=now + window,
                limit_type=endpoint,
            )
        else:
            oldest = await client.zrange(f"ratelimit:{key}", 0, 0, withscores=True)
            oldest_time = oldest[0][1] if oldest else now
            retry_after = oldest_time + window - now

            return RateLimitResult(
                allowed=False,
                remaining=0,
                reset_time=oldest_time + window,
                limit_type=endpoint,
                retry_after=retry_after,
            )

    async def close(self) -> None:
        """Close Redis connection."""
        if self._client:
            await self._client.close()
            self._client = None


class InMemoryRateLimiter(RateLimiter):
    """In-memory rate limiter for single-instance deployments."""

    def __init__(
        self,
        default_limits: Optional[dict[str, tuple[int, int]]] = None,
    ):
        self.default_limits = default_limits or {
            "default": (100, 60),
            "query": (50, 60),
            "chat": (30, 60),
            "models": (10, 60),
        }
        self._windows: dict[str, list[float]] = {}

    async def check_rate_limit(
        self, key: str, endpoint: str = "default"
    ) -> RateLimitResult:
        """Check rate limit using in-memory sliding window."""
        limit, window = self.default_limits.get(
            endpoint, self.default_limits["default"]
        )
        now = time.time()
        window_start = now - window

        window_key = f"{key}:{endpoint}"
        requests = self._windows.get(window_key, [])

        self._windows[window_key] = [t for t in requests if t > window_start]

        if len(self._windows[window_key]) < limit:
            self._windows[window_key].append(now)
            return RateLimitResult(
                allowed=True,
                remaining=limit - len(self._windows[window_key]) - 1,
                reset_time=now + window,
                limit_type=endpoint,
            )
        else:
            retry_after = window - (now - self._windows[window_key][0])
            return RateLimitResult(
                allowed=False,
                remaining=0,
                reset_time=now + window,
                limit_type=endpoint,
                retry_after=retry_after,
            )

    async def close(self) -> None:
        """No cleanup needed for in-memory limiter."""
        pass


def get_rate_limiter() -> RateLimiter:
    """Factory function to get configured rate limiter."""
    use_redis = os.environ.get("UPSONIC_USE_REDIS", "false").lower() == "true"

    if use_redis:
        return RedisRateLimiter()
    return InMemoryRateLimiter()

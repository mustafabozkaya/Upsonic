"""
Gateway Middleware for Upsonic

FastAPI middleware composition for authentication, rate limiting, and request processing.
Provides gateway-level functionality for the Upsonic API.
"""

from __future__ import annotations

import os
import time
import uuid
from typing import Callable, Optional

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from apps.gateway.auth import AuthProvider, get_auth_provider
from apps.gateway.ratelimit import RateLimiter, get_rate_limiter
from apps.gateway.config import GatewayConfig


class GatewayMiddleware:
    """Gateway middleware combining auth and rate limiting."""

    def __init__(
        self,
        auth_provider: Optional[AuthProvider] = None,
        rate_limiter: Optional[RateLimiter] = None,
        config: Optional[GatewayConfig] = None,
    ):
        self.auth_provider = auth_provider or get_auth_provider()
        self.rate_limiter = rate_limiter or get_rate_limiter()
        self.config = config or GatewayConfig()

    async def authenticate(self, request: Request) -> tuple[bool, dict]:
        """Authenticate request and return (success, auth_context)."""
        credentials = {
            "Authorization": request.headers.get("Authorization", ""),
            "X-API-Key": request.headers.get("X-API-Key", ""),
        }

        result = await self.auth_provider.authenticate(credentials)

        if not result.success:
            return False, {"error": result.error}

        return True, {
            "user_id": result.user_id,
            "roles": result.roles,
        }

    async def check_rate_limit(
        self, request: Request, auth_context: dict
    ) -> tuple[bool, dict]:
        """Check rate limit and return (allowed, rate_limit_info)."""
        endpoint = self._get_endpoint_type(request.url.path)
        user_id = auth_context.get("user_id", "anonymous")
        key = f"{user_id}:{request.client.host}" if user_id else request.client.host

        result = await self.rate_limiter.check_rate_limit(key, endpoint)

        if not result.allowed:
            return False, {
                "error": "Rate limit exceeded",
                "retry_after": result.retry_after,
                "reset_time": result.reset_time,
            }

        return True, {"rate_limit": result.to_headers()}

    def _get_endpoint_type(self, path: str) -> str:
        """Determine endpoint type for rate limiting."""
        if "/query" in path:
            return "query"
        elif "/chat" in path:
            return "chat"
        elif "/models" in path:
            return "models"
        return "default"

    async def process_request(
        self, request: Request
    ) -> tuple[Optional[Response], dict]:
        """Process request through auth and rate limiting.

        Returns (response, context). If response is not None, send it and stop processing.
        """
        auth_context = {}

        auth_success, auth_result = await self.authenticate(request)
        if not auth_success:
            return JSONResponse(
                status_code=401,
                content={"error": auth_result.get("error", "Authentication failed")},
            ), auth_context

        auth_context.update(auth_result)

        rate_success, rate_result = await self.check_rate_limit(request, auth_context)
        if not rate_success:
            headers = rate_result.get("headers", {})
            return JSONResponse(
                status_code=429,
                content={
                    "error": rate_result.get("error", "Rate limit exceeded"),
                    "retry_after": rate_result.get("retry_after"),
                },
                headers=headers,
            ), auth_context

        if "rate_limit" in rate_result:
            request.state.rate_limit_headers = rate_result["rate_limit"]

        return None, auth_context

    def add_to_app(self, app: FastAPI) -> None:
        """Add middleware to FastAPI app."""

        @app.middleware("http")
        async def gateway_middleware(request: Request, call_next):
            start_time = time.time()
            request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

            request.state.request_id = request_id
            request.state.start_time = start_time

            response, auth_context = await self.process_request(request)

            if response is not None:
                response.headers["X-Request-ID"] = request_id
                response.headers["X-Processing-Time"] = str(time.time() - start_time)

                if hasattr(request.state, "rate_limit_headers"):
                    response.headers.update(request.state.rate_limit_headers)

                return response

            request.state.auth_context = auth_context

            response = await call_next(request)

            response.headers["X-Request-ID"] = request_id
            response.headers["X-Processing-Time"] = str(time.time() - start_time)

            if hasattr(request.state, "rate_limit_headers"):
                response.headers.update(request.state.rate_limit_headers)

            return response

    async def close(self) -> None:
        """Cleanup middleware resources."""
        await self.rate_limiter.close()


async def create_gateway_middleware(
    auth_provider: Optional[AuthProvider] = None,
    rate_limiter: Optional[RateLimiter] = None,
) -> GatewayMiddleware:
    """Factory function to create gateway middleware."""
    return GatewayMiddleware(
        auth_provider=auth_provider,
        rate_limiter=rate_limiter,
    )


def setup_gateway(app: FastAPI) -> GatewayMiddleware:
    """Setup gateway middleware on FastAPI app."""
    middleware = GatewayMiddleware()
    middleware.add_to_app(app)
    return middleware

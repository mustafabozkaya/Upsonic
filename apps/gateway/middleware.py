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
from apps.gateway.safety import SafetyChecker, get_safety_checker


class GatewayMiddleware:
    """Gateway middleware combining auth, rate limiting, and safety checks."""

    def __init__(
        self,
        auth_provider: Optional[AuthProvider] = None,
        rate_limiter: Optional[RateLimiter] = None,
        safety_checker: Optional[SafetyChecker] = None,
        config: Optional[GatewayConfig] = None,
    ):
        self.auth_provider = auth_provider or get_auth_provider()
        self.rate_limiter = rate_limiter or get_rate_limiter()
        self.config = config or GatewayConfig()
        self.safety_checker = safety_checker or get_safety_checker(
            enabled_policies=self.config.safety_policies
            if self.config.safety_enabled
            else []
        )

    async def authenticate(self, request: Request) -> tuple[bool, dict]:
        """Authenticate request and return (success, auth_context)."""
        # Check if auth is required
        if not getattr(self.config, "require_auth", False):
            return True, {"user_id": "anonymous", "roles": []}

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

    def _should_skip_safety_check(self, path: str) -> bool:
        """Determine if safety check should be skipped for this path."""
        skip_paths = ["/health", "/docs", "/openapi.json", "/", "/models", "/tools"]
        return any(path.startswith(skip) or path == skip for skip in skip_paths)

    async def check_safety(self, request: Request) -> tuple[bool, Optional[dict]]:
        """Check request content safety and return (is_safe, violation_info).

        Only checks POST/PUT/PATCH requests with body content.
        """
        if not self.config.safety_enabled:
            return True, None

        if self._should_skip_safety_check(request.url.path):
            return True, None

        # Only check methods that typically have body content
        if request.method not in ["POST", "PUT", "PATCH"]:
            return True, None

        try:
            # Read and parse request body
            body = await request.body()
            if not body:
                return True, None

            import json

            content = json.loads(body)

            # Extract text fields to check
            texts_to_check = []

            # Check user_query field (primary)
            if "user_query" in content and content["user_query"]:
                texts_to_check.append(content["user_query"])

            # Check message field (chat endpoint)
            if "message" in content and content["message"]:
                texts_to_check.append(content["message"])

            # Check messages array (chat history)
            if "messages" in content and isinstance(content["messages"], list):
                for msg in content["messages"]:
                    if isinstance(msg, dict) and msg.get("content"):
                        texts_to_check.append(msg["content"])

            if not texts_to_check:
                return True, None

            # Check each text
            for text in texts_to_check:
                result = self.safety_checker.check_content(text)
                if not result.is_safe:
                    return False, {
                        "policy_triggered": result.policy_triggered,
                        "reason": result.reason,
                        "blocked": self.config.safety_block_on_violation,
                    }

            return True, None

        except json.JSONDecodeError:
            # Non-JSON body, skip safety check
            return True, None
        except Exception as e:
            # Log error but allow request (fail open for safety system errors)
            print(f"Safety check error: {e}")
            return True, None

    async def process_request(
        self, request: Request
    ) -> tuple[Optional[Response], dict]:
        """Process request through auth, rate limiting, and safety checks.

        Returns (response, context). If response is not None, send it and stop processing.
        """
        auth_context = {}

        # 1. Authentication
        auth_success, auth_result = await self.authenticate(request)
        if not auth_success:
            return JSONResponse(
                status_code=401,
                content={"error": auth_result.get("error", "Authentication failed")},
            ), auth_context

        auth_context.update(auth_result)

        # 2. Rate Limiting
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

        # 3. Safety Check (Content Filtering)
        safety_success, safety_result = await self.check_safety(request)
        if not safety_success and safety_result and safety_result.get("blocked"):
            return JSONResponse(
                status_code=400,
                content={
                    "error": "Content violates safety policy",
                    "policy": safety_result.get("policy_triggered"),
                    "reason": safety_result.get("reason"),
                },
            ), auth_context

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
    safety_checker: Optional[SafetyChecker] = None,
) -> GatewayMiddleware:
    """Factory function to create gateway middleware."""
    return GatewayMiddleware(
        auth_provider=auth_provider,
        rate_limiter=rate_limiter,
        safety_checker=safety_checker,
    )


def setup_gateway(app: FastAPI) -> GatewayMiddleware:
    """Setup gateway middleware on FastAPI app."""
    middleware = GatewayMiddleware()
    middleware.add_to_app(app)
    return middleware

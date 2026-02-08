"""
Gateway Layer for Upsonic

Enterprise gateway components for authentication, rate limiting, and request routing.
Provides security and traffic management for the Upsonic API.

Modules:
- auth: JWT/OAuth2 authentication
- ratelimit: Redis-backed rate limiting
- middleware: FastAPI middleware composition
- config: Gateway configuration
"""

from __future__ import annotations

__version__ = "1.0.0"
__author__ = "Upsonic Team"

from .auth import AuthProvider, JWTAuthProvider, APIKeyAuthProvider
from .ratelimit import RateLimiter, RedisRateLimiter
from .middleware import GatewayMiddleware, create_gateway_middleware
from .config import GatewayConfig, get_gateway_config

__all__ = [
    "AuthProvider",
    "JWTAuthProvider",
    "APIKeyAuthProvider",
    "RateLimiter",
    "RedisRateLimiter",
    "GatewayMiddleware",
    "create_gateway_middleware",
    "GatewayConfig",
    "get_gateway_config",
]

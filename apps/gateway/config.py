"""
Gateway Configuration for Upsonic

Configuration management for gateway components including auth, rate limiting, and middleware settings.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class GatewayConfig:
    """Configuration for the Upsonic Gateway."""

    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    reload: bool = True

    auth_type: str = "jwt"
    jwt_secret: str = "dev-secret-key"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60
    require_auth: bool = False

    use_redis: bool = False
    redis_url: str = "redis://localhost:6379/0"
    rate_limit_default: tuple[int, int] = (100, 60)
    rate_limit_query: tuple[int, int] = (50, 60)
    rate_limit_chat: tuple[int, int] = (30, 60)
    rate_limit_models: tuple[int, int] = (10, 60)

    cors_origins: list[str] = None
    cors_credentials: bool = True

    log_level: str = "INFO"
    request_id_header: str = "X-Request-ID"

    def __post_init__(self):
        if self.cors_origins is None:
            self.cors_origins = ["*"]

    @classmethod
    def from_env(cls) -> "GatewayConfig":
        """Create configuration from environment variables."""
        return cls(
            host=os.environ.get("UPSONIC_HOST", "0.0.0.0"),
            port=int(os.environ.get("UPSONIC_PORT", "8000")),
            debug=os.environ.get("UPSONIC_DEBUG", "false").lower() == "true",
            reload=os.environ.get("UPSONIC_RELOAD", "true").lower() == "true",
            auth_type=os.environ.get("UPSONIC_AUTH_TYPE", "jwt"),
            jwt_secret=os.environ.get("UPSONIC_JWT_SECRET", "dev-secret-key"),
            jwt_algorithm=os.environ.get("UPSONIC_JWT_ALGORITHM", "HS256"),
            jwt_expire_minutes=int(os.environ.get("UPSONIC_JWT_EXPIRE_MINUTES", "60")),
            require_auth=os.environ.get("UPSONIC_REQUIRE_AUTH", "false").lower()
            == "true",
            use_redis=os.environ.get("UPSONIC_USE_REDIS", "false").lower() == "true",
            redis_url=os.environ.get("UPSONIC_REDIS_URL", "redis://localhost:6379/0"),
            log_level=os.environ.get("UPSONIC_LOG_LEVEL", "INFO"),
        )


def get_gateway_config() -> GatewayConfig:
    """Factory function to get gateway configuration."""
    return GatewayConfig.from_env()

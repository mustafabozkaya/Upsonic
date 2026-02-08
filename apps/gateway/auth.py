"""
Authentication Providers for Upsonic Gateway

Provides JWT and API key authentication for the Upsonic API.
Supports multiple authentication strategies with configurable providers.
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

import jwt
from pydantic import BaseModel


@dataclass
class AuthResult:
    """Result of an authentication attempt."""

    success: bool
    user_id: Optional[str] = None
    roles: list[str] = None
    error: Optional[str] = None
    token_type: Optional[str] = None

    def __post_init__(self):
        if self.roles is None:
            self.roles = []


class AuthProvider(ABC):
    """Abstract base class for authentication providers."""

    @abstractmethod
    async def authenticate(self, credentials: dict) -> AuthResult:
        """Authenticate credentials and return AuthResult."""
        pass

    @abstractmethod
    async def create_token(self, user_id: str, roles: list[str]) -> str:
        """Create a new authentication token."""
        pass

    @abstractmethod
    async def validate_token(self, token: str) -> AuthResult:
        """Validate a token and return AuthResult."""
        pass


class JWTAuthProvider(AuthProvider):
    """JWT-based authentication provider."""

    def __init__(
        self,
        secret_key: Optional[str] = None,
        algorithm: str = "HS256",
        token_expire_minutes: int = 60,
    ):
        self.secret_key = secret_key or os.environ.get(
            "UPSONIC_JWT_SECRET", "dev-secret-key"
        )
        self.algorithm = algorithm
        self.token_expire_minutes = token_expire_minutes

    async def authenticate(self, credentials: dict) -> AuthResult:
        """Authenticate with JWT token from Authorization header."""
        auth_header = credentials.get("Authorization", "")

        if not auth_header.startswith("Bearer "):
            return AuthResult(
                success=False, error="Invalid authorization header format"
            )

        token = auth_header[7:]
        return await self.validate_token(token)

    async def create_token(self, user_id: str, roles: list[str]) -> str:
        """Create a new JWT token."""
        expire = datetime.utcnow() + timedelta(minutes=self.token_expire_minutes)

        payload = {
            "sub": user_id,
            "roles": roles,
            "exp": expire,
            "iat": datetime.utcnow(),
        }

        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return token

    async def validate_token(self, token: str) -> AuthResult:
        """Validate a JWT token."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])

            user_id = payload.get("sub")
            roles = payload.get("roles", [])

            return AuthResult(
                success=True, user_id=user_id, roles=roles, token_type="Bearer"
            )

        except jwt.ExpiredSignatureError:
            return AuthResult(success=False, error="Token has expired")
        except jwt.InvalidTokenError as e:
            return AuthResult(success=False, error=f"Invalid token: {str(e)}")


class APIKeyAuthProvider(AuthProvider):
    """API Key based authentication provider."""

    def __init__(
        self,
        valid_api_keys: Optional[dict[str, dict]] = None,
    ):
        self.valid_api_keys = valid_api_keys or self._load_api_keys()

    def _load_api_keys(self) -> dict[str, dict]:
        """Load valid API keys from environment or config."""
        keys = {}

        api_key = os.environ.get("UPSONIC_API_KEY")
        if api_key:
            keys[api_key] = {"user_id": "default", "roles": ["user"]}

        return keys

    async def authenticate(self, credentials: dict) -> AuthResult:
        """Authenticate with API key from X-API-Key header."""
        api_key = credentials.get("X-API-Key", "")

        if not api_key:
            return AuthResult(success=False, error="API key required")

        if api_key not in self.valid_api_keys:
            return AuthResult(success=False, error="Invalid API key")

        key_data = self.valid_api_keys[api_key]
        return AuthResult(
            success=True,
            user_id=key_data.get("user_id", "unknown"),
            roles=key_data.get("roles", ["user"]),
            token_type="ApiKey",
        )

    async def create_token(self, user_id: str, roles: list[str]) -> str:
        """API keys don't use tokens - return empty string."""
        return ""

    async def validate_token(self, token: str) -> AuthResult:
        """API keys are validated through authenticate method."""
        return await self.authenticate({"X-API-Key": token})


class CompositeAuthProvider(AuthProvider):
    """Composite authentication provider supporting multiple strategies."""

    def __init__(self, providers: list[AuthProvider]):
        self.providers = providers

    async def authenticate(self, credentials: dict) -> AuthResult:
        """Try authentication with each provider until one succeeds."""
        for provider in self.providers:
            result = await provider.authenticate(credentials)
            if result.success:
                return result
        return AuthResult(
            success=False, error="Authentication failed with all providers"
        )

    async def create_token(self, user_id: str, roles: list[str]) -> str:
        """Create token using first JWT-capable provider."""
        for provider in self.providers:
            if isinstance(provider, JWTAuthProvider):
                return await provider.create_token(user_id, roles)
        return ""

    async def validate_token(self, token: str) -> AuthResult:
        """Validate token using first JWT-capable provider."""
        for provider in self.providers:
            if isinstance(provider, JWTAuthProvider):
                return await provider.validate_token(token)
        return AuthResult(success=False, error="No JWT provider available")


def get_auth_provider() -> AuthProvider:
    """Factory function to get configured authentication provider."""
    auth_type = os.environ.get("UPSONIC_AUTH_TYPE", "jwt")

    if auth_type == "composite":
        return CompositeAuthProvider(
            [
                JWTAuthProvider(),
                APIKeyAuthProvider(),
            ]
        )

    elif auth_type == "apikey":
        return APIKeyAuthProvider()

    return JWTAuthProvider()

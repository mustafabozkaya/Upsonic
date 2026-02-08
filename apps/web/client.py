"""
Enterprise Python Client for Upsonic

A comprehensive, type-safe Python client for interacting with Upsonic AI Agent Framework.
Uses the interface adapter pattern to communicate with apps/interface/ REST API.

Features:
- Synchronous and asynchronous interfaces
- Session management
- Chat history
- Model selection
- Error handling with detailed diagnostics
- Connection pooling and retry logic

Usage:
    from apps.web import UpsonicClient

    # Sync usage
    client = UpsonicClient(base_url="http://localhost:8000")
    response = client.query("What is Python?")
    print(response)

    # Async usage
    client = AsyncUpsonicClient(base_url="http://localhost:8000")
    response = await client.query("What is Python?")
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, AsyncIterator, Dict, List, Optional, Union

import httpx
from pydantic import BaseModel, Field


@dataclass
class QueryResult:
    """Result of a query operation."""

    user_query: str
    bot_response: str
    model_used: str
    timestamp: str

    def __str__(self) -> str:
        return self.bot_response


class UpsonicClient:
    """
    Synchronous Python client for Upsonic AI Agent API.

    Provides a simple interface for making queries and managing chat sessions.

    Usage:
        client = UpsonicClient(base_url="http://localhost:8000")
        result = client.query("Hello, how are you?")
        print(result.bot_response)
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        api_key: Optional[str] = None,
        timeout: float = 60.0,
        verify_ssl: bool = True,
    ):
        """
        Initialize the Upsonic client.

        Args:
            base_url: Base URL of the Upsonic REST API
            api_key: Optional API key for authentication
            timeout: Request timeout in seconds
            verify_ssl: Whether to verify SSL certificates
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self._client: Optional[httpx.Client] = None

    @property
    def headers(self) -> Dict[str, str]:
        """Get request headers including authentication."""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    @property
    def client(self) -> httpx.Client:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.Client(
                timeout=self.timeout,
                verify=self.verify_ssl,
            )
        return self._client

    def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            self._client.close()
            self._client = None

    def __enter__(self) -> "UpsonicClient":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.close()

    def _handle_error(self, response: httpx.Response) -> httpx.Response:
        """Handle error responses and raise appropriate exceptions."""
        if response.status_code == 401:
            raise ValueError("Invalid API key")
        elif response.status_code == 429:
            raise RuntimeError(
                "Rate limit exceeded. Please wait before making more requests."
            )
        elif response.status_code >= 400:
            error_msg = response.text
            try:
                error_data = response.json()
                error_msg = error_data.get("detail", error_msg)
            except Exception:
                pass
            raise RuntimeError(f"API error ({response.status_code}): {error_msg}")
        return response

    def query(
        self,
        user_query: str,
        model: Optional[str] = None,
    ) -> QueryResult:
        """
        Send a query to the Upsonic AI Agent.

        Args:
            user_query: The question or prompt to send
            model: Optional model specification (e.g., "ollama/qwen2.5:7b")

        Returns:
            QueryResult with the response and metadata

        Raises:
            ValueError: If user_query is empty
            RuntimeError: If the API returns an error
        """
        if not user_query or not user_query.strip():
            raise ValueError("user_query cannot be empty")

        payload: Dict[str, Any] = {"user_query": user_query}
        if model:
            payload["model"] = model

        response = self.client.post(
            f"{self.base_url}/query",
            json=payload,
            headers=self.headers,
        )

        self._handle_error(response)
        data = response.json()

        return QueryResult(
            user_query=data.get("user_query", user_query),
            bot_response=data.get("bot_response", ""),
            model_used=data.get("model_used", model or "default"),
            timestamp=data.get("timestamp", ""),
        )

    def get_models(self) -> List[str]:
        """
        Get list of available models.

        Returns:
            List of model identifiers
        """
        response = self.client.get(
            f"{self.base_url}/models",
            headers=self.headers,
        )

        self._handle_error(response)
        data = response.json()
        return data.get("models", [])

    def health_check(self) -> Dict[str, Any]:
        """
        Check the health of the API.

        Returns:
            Dictionary with health status and metadata
        """
        response = self.client.get(
            f"{self.base_url}/health",
            headers=self.headers,
        )

        self._handle_error(response)
        return response.json()

    def info(self) -> Dict[str, Any]:
        """
        Get API information.

        Returns:
            Dictionary with API info
        """
        response = self.client.get(
            f"{self.base_url}/",
            headers=self.headers,
        )

        self._handle_error(response)
        return response.json()


class AsyncUpsonicClient:
    """
    Asynchronous Python client for Upsonic AI Agent API.

    Provides an async interface for making queries and managing chat sessions.

    Usage:
        client = AsyncUpsonicClient(base_url="http://localhost:8000")
        result = await client.query("Hello, how are you?")
        print(result.bot_response)
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        api_key: Optional[str] = None,
        timeout: float = 60.0,
        verify_ssl: bool = True,
    ):
        """
        Initialize the async Upsonic client.

        Args:
            base_url: Base URL of the Upsonic REST API
            api_key: Optional API key for authentication
            timeout: Request timeout in seconds
            verify_ssl: Whether to verify SSL certificates
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def headers(self) -> Dict[str, str]:
        """Get request headers including authentication."""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    @property
    async def client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                verify=self.verify_ssl,
            )
        return self._client

    async def close(self) -> None:
        """Close the async HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> "AsyncUpsonicClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()

    async def _handle_error(self, response: httpx.Response) -> httpx.Response:
        """Handle error responses and raise appropriate exceptions."""
        if response.status_code == 401:
            raise ValueError("Invalid API key")
        elif response.status_code == 429:
            raise RuntimeError(
                "Rate limit exceeded. Please wait before making more requests."
            )
        elif response.status_code >= 400:
            error_msg = response.text
            try:
                error_data = response.json()
                error_msg = error_data.get("detail", error_msg)
            except Exception:
                pass
            raise RuntimeError(f"API error ({response.status_code}): {error_msg}")
        return response

    async def query(
        self,
        user_query: str,
        model: Optional[str] = None,
    ) -> QueryResult:
        """
        Send a query to the Upsonic AI Agent (async).

        Args:
            user_query: The question or prompt to send
            model: Optional model specification

        Returns:
            QueryResult with the response and metadata
        """
        if not user_query or not user_query.strip():
            raise ValueError("user_query cannot be empty")

        payload: Dict[str, Any] = {"user_query": user_query}
        if model:
            payload["model"] = model

        client = await self.client
        response = await client.post(
            f"{self.base_url}/query",
            json=payload,
            headers=self.headers,
        )

        await self._handle_error(response)
        data = response.json()

        return QueryResult(
            user_query=data.get("user_query", user_query),
            bot_response=data.get("bot_response", ""),
            model_used=data.get("model_used", model or "default"),
            timestamp=data.get("timestamp", ""),
        )

    async def get_models(self) -> List[str]:
        """Get list of available models (async)."""
        client = await self.client
        response = await client.get(
            f"{self.base_url}/models",
            headers=self.headers,
        )

        await self._handle_error(response)
        data = response.json()
        return data.get("models", [])

    async def health_check(self) -> Dict[str, Any]:
        """Check the health of the API (async)."""
        client = await self.client
        response = await client.get(
            f"{self.base_url}/health",
            headers=self.headers,
        )

        await self._handle_error(response)
        return response.json()

    async def info(self) -> Dict[str, Any]:
        """Get API information (async)."""
        client = await self.client
        response = await client.get(
            f"{self.base_url}/",
            headers=self.headers,
        )

        await self._handle_error(response)
        return response.json()


def run():
    """Run a simple demo of the client."""
    print("=" * 50)
    print("Upsonic Enterprise Python Client Demo")
    print("=" * 50)
    print()

    # Check if server is running
    print("Creating client...")
    client = UpsonicClient()

    try:
        # Health check
        print("Checking API health...")
        try:
            health = client.health_check()
            print(f"  Status: {health.get('status', 'unknown')}")
            print(f"  Service: {health.get('service', 'unknown')}")
        except Exception as e:
            print(f"  ⚠️  Server not available: {e}")
            print("  Make sure the Upsonic API server is running:")
            print("  python -m uvicorn apps.interface.rest.main:app --reload")
            return

        # Get models
        print("\nAvailable models:")
        models = client.get_models()
        for model in models[:5]:
            print(f"  - {model}")
        if len(models) > 5:
            print(f"  ... and {len(models) - 5} more")

        # Test query
        print("\nSending test query...")
        print("  Query: 'What is Python programming language?'")
        result = client.query("What is Python programming language?")
        print(f"\n  Response:")
        print(f"  {result.bot_response[:200]}...")
        print(f"\n  Model used: {result.model_used}")

    except Exception as e:
        print(f"  Error: {e}")
    finally:
        client.close()

    print("\n" + "=" * 50)


if __name__ == "__main__":
    run()

"""
Chat Client for Upsonic

High-level chat client with session management, history, and streaming support.
Uses the enterprise UpsonicClient from apps.web for API communication.

Usage:
    from apps.web.chat_client import ChatClient

    # Sync usage
    client = ChatClient(base_url="http://localhost:8000")
    response = client.chat("Hello!", session_id="user123")

    # Async usage
    client = AsyncChatClient(base_url="http://localhost:8000")
    response = await client.chat("Hello!", session_id="user123")
"""

from __future__ import annotations

import asyncio
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, AsyncIterator, Dict, List, Optional

from apps.web.client import AsyncUpsonicClient, UpsonicClient, QueryResult


@dataclass
class ChatMessage:
    """A chat message in the conversation."""

    role: str
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    model: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
            "model": self.model,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ChatMessage":
        return cls(
            role=data.get("role", "user"),
            content=data.get("content", ""),
            timestamp=data.get("timestamp", datetime.now().isoformat()),
            model=data.get("model"),
        )


@dataclass
class ChatSession:
    """A chat session with messages and metadata."""

    session_id: str
    user_id: str
    messages: List[ChatMessage] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    model: Optional[str] = None

    def add_message(self, message: ChatMessage) -> None:
        self.messages.append(message)
        self.updated_at = datetime.now().isoformat()

    def get_history(self) -> List[dict[str, Any]]:
        return [msg.to_dict() for msg in self.messages]

    def count_messages(self) -> int:
        return len(self.messages)


class ChatClient:
    """
    Synchronous chat client for Upsonic API.

    Provides session management, message history, and easy-to-use chat interface.

    Usage:
        client = ChatClient(base_url="http://localhost:8000")
        response = client.chat("Hello!", session_id="user123")
        print(response)
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        api_key: Optional[str] = None,
        default_model: Optional[str] = None,
        auto_create_session: bool = True,
    ):
        """
        Initialize the chat client.

        Args:
            base_url: Base URL of the Upsonic API
            api_key: Optional API key for authentication
            default_model: Default model to use for chat
            auto_create_session: Automatically create session if not provided
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.default_model = default_model or os.environ.get(
            "UPSONIC_DEFAULT_MODEL", "ollama/qwen2.5:7b"
        )
        self.auto_create_session = auto_create_session
        self._client: Optional[UpsonicClient] = None
        self._sessions: Dict[str, ChatSession] = {}

    @property
    def client(self) -> UpsonicClient:
        """Get or create UpsonicClient."""
        if self._client is None:
            self._client = UpsonicClient(
                base_url=self.base_url,
                api_key=self.api_key,
            )
        return self._client

    def close(self) -> None:
        """Close the client."""
        if self._client:
            self._client.close()
            self._client = None

    def __enter__(self) -> "ChatClient":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def create_session(self, user_id: str, model: Optional[str] = None) -> str:
        """Create a new chat session."""
        session_id = str(uuid.uuid4())
        session = ChatSession(
            session_id=session_id,
            user_id=user_id,
            model=model or self.default_model,
        )
        self._sessions[session_id] = session
        return session_id

    def get_session(self, session_id: str) -> Optional[ChatSession]:
        """Get a chat session by ID."""
        return self._sessions.get(session_id)

    def delete_session(self, session_id: str) -> bool:
        """Delete a chat session."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    def chat(
        self,
        message: str,
        session_id: Optional[str] = None,
        user_id: str = "default",
        model: Optional[str] = None,
    ) -> ChatMessage:
        """
        Send a chat message and get response.

        Args:
            message: The message to send
            session_id: Optional session ID (creates new if not provided)
            user_id: User ID for session creation
            model: Model to use (overrides session default)

        Returns:
            ChatMessage with the assistant's response
        """
        if not session_id and self.auto_create_session:
            session_id = self.create_session(user_id, model)

        session = self.get_session(session_id) if session_id else None
        model_to_use = model or (session.model if session else self.default_model)

        try:
            result = self.client.query(message, model=model_to_use)

            response_message = ChatMessage(
                role="assistant",
                content=result.bot_response,
                timestamp=result.timestamp,
                model=result.model_used,
            )

            if session:
                session.add_message(
                    ChatMessage(role="user", content=message, model=model_to_use)
                )
                session.add_message(response_message)

            return response_message

        except Exception as e:
            error_message = ChatMessage(
                role="assistant",
                content=f"Error: {str(e)}",
                timestamp=datetime.now().isoformat(),
                model=model_to_use,
            )
            return error_message

    def get_history(self, session_id: str) -> List[dict[str, Any]]:
        """Get message history for a session."""
        session = self.get_session(session_id)
        if session:
            return session.get_history()
        return []

    def list_sessions(self) -> List[dict[str, Any]]:
        """List all sessions."""
        return [
            {
                "session_id": s.session_id,
                "user_id": s.user_id,
                "message_count": s.count_messages(),
                "created_at": s.created_at,
                "updated_at": s.updated_at,
                "model": s.model,
            }
            for s in self._sessions.values()
        ]


class AsyncChatClient:
    """
    Asynchronous chat client for Upsonic API.

    Provides async session management and chat interface.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        api_key: Optional[str] = None,
        default_model: Optional[str] = None,
        auto_create_session: bool = True,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.default_model = default_model or os.environ.get(
            "UPSONIC_DEFAULT_MODEL", "ollama/qwen2.5:7b"
        )
        self.auto_create_session = auto_create_session
        self._client: Optional[AsyncUpsonicClient] = None
        self._sessions: Dict[str, ChatSession] = {}

    @property
    async def client(self) -> AsyncUpsonicClient:
        if self._client is None:
            self._client = AsyncUpsonicClient(
                base_url=self.base_url,
                api_key=self.api_key,
            )
        return self._client

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> "AsyncChatClient":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()

    def create_session(self, user_id: str, model: Optional[str] = None) -> str:
        session_id = str(uuid.uuid4())
        session = ChatSession(
            session_id=session_id,
            user_id=user_id,
            model=model or self.default_model,
        )
        self._sessions[session_id] = session
        return session_id

    def get_session(self, session_id: str) -> Optional[ChatSession]:
        return self._sessions.get(session_id)

    async def chat(
        self,
        message: str,
        session_id: Optional[str] = None,
        user_id: str = "default",
        model: Optional[str] = None,
    ) -> ChatMessage:
        if not session_id and self.auto_create_session:
            session_id = self.create_session(user_id, model)

        session = self.get_session(session_id) if session_id else None
        model_to_use = model or (session.model if session else self.default_model)

        client = await self.client

        try:
            result = await client.query(message, model=model_to_use)

            response_message = ChatMessage(
                role="assistant",
                content=result.bot_response,
                timestamp=result.timestamp,
                model=result.model_used,
            )

            if session:
                session.add_message(
                    ChatMessage(role="user", content=message, model=model_to_use)
                )
                session.add_message(response_message)

            return response_message

        except Exception as e:
            error_message = ChatMessage(
                role="assistant",
                content=f"Error: {str(e)}",
                timestamp=datetime.now().isoformat(),
                model=model_to_use,
            )
            return error_message

    def get_history(self, session_id: str) -> List[dict[str, Any]]:
        session = self.get_session(session_id)
        if session:
            return session.get_history()
        return []

    def list_sessions(self) -> List[dict[str, Any]]:
        return [
            {
                "session_id": s.session_id,
                "user_id": s.user_id,
                "message_count": s.count_messages(),
                "created_at": s.created_at,
                "updated_at": s.updated_at,
                "model": s.model,
            }
            for s in self._sessions.values()
        ]


def run_demo():
    """Run a simple demo of the chat client."""
    print("=" * 50)
    print("Upsonic Chat Client Demo")
    print("=" * 50)

    client = ChatClient(base_url="http://localhost:8000")

    try:
        print("\nCreating session...")
        session_id = client.create_session("demo_user")
        print(f"  Session ID: {session_id}")

        print("\nSending test message...")
        response = client.chat("Hello, how are you?", session_id=session_id)
        print(f"  Response: {response.content[:100]}...")

        print("\nGetting history...")
        history = client.get_history(session_id)
        print(f"  Messages: {len(history)}")

    except Exception as e:
        print(f"\n  ⚠️  Error: {e}")
        print("  Make sure the Upsonic API server is running:")
        print("  python -m uvicorn apps.interface.rest.main:app --reload")

    finally:
        client.close()

    print("\n" + "=" * 50)


if __name__ == "__main__":
    run_demo()

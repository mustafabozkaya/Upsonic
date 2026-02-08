"""
Web Clients for Upsonic

Provides web-based clients for interacting with Upsonic AI Agent Framework:
- Python client for programmatic access (UpsonicClient)
- Chat client with session management (ChatClient)
- Streamlit web interface

All clients use the new architecture:
    Client → apps/interface/rest/main.py → src/upsonic/

Modules:
- client: Enterprise Python client (sync + async)
- chat_client: High-level chat client with sessions
- streamlit_app: Streamlit web interface
"""

from __future__ import annotations

__version__ = "1.0.0"
__author__ = "Upsonic Team"

from .client import UpsonicClient, AsyncUpsonicClient, QueryResult
from .chat_client import ChatClient, AsyncChatClient, ChatMessage, ChatSession

__all__ = [
    "UpsonicClient",
    "AsyncUpsonicClient",
    "QueryResult",
    "ChatClient",
    "AsyncChatClient",
    "ChatMessage",
    "ChatSession",
]

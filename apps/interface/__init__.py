"""
Interface Layer for Upsonic

This module provides adapters for external communication:
- REST API (FastAPI)
- WebSocket
- Platform integrations (WhatsApp, Slack, Gmail)

All interfaces use enterprise modules from src/upsonic/ as the backend.
"""

from __future__ import annotations

__version__ = "1.0.0"
__author__ = "Upsonic Team"

from .rest.main import create_app

__all__ = ["create_app"]

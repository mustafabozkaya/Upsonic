"""
REST Interface Adapters for Upsonic

Provides FastAPI adapters for the Upsonic enterprise backend.
All business logic is delegated to src/upsonic/ modules.
"""

from __future__ import annotations

from .main import create_app

__all__ = ["create_app"]

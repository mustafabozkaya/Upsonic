"""
Web Clients for Upsonic

Provides web-based clients for interacting with Upsonic AI Agent Framework:
- Python client for programmatic access
- Streamlit web interface

All clients delegate to apps/interface/ adapters.
"""

from __future__ import annotations

__version__ = "1.0.0"
__author__ = "Upsonic Team"

from .client import UpsonicClient, AsyncUpsonicClient
from .streamlit_app import main as run_streamlit

__all__ = ["UpsonicClient", "AsyncUpsonicClient", "run_streamlit"]

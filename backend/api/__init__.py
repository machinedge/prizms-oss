"""
Prizms API package.

Provides the FastAPI application for the Prizms debate orchestration service.
"""

from .app import app, create_app

__all__ = ["app", "create_app"]

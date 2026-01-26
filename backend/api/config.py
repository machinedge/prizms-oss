"""
API configuration - re-exports from shared config.

This module provides compatibility with the story specification while
using the centralized shared configuration.
"""

from shared.config import Settings as APISettings, get_settings

__all__ = ["APISettings", "get_settings"]

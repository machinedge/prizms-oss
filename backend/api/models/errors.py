"""
Error response models.

Standardized error responses for the API.
"""

from pydantic import BaseModel
from typing import Optional


class ErrorResponse(BaseModel):
    """Standard error response format."""

    error: str
    detail: Optional[str] = None
    code: Optional[str] = None


class ValidationErrorResponse(BaseModel):
    """Validation error response format."""

    error: str = "Validation Error"
    detail: list[dict]

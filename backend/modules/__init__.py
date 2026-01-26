"""
Feature modules for Prizms backend.

Each module is self-contained with its own:
- interfaces.py: Protocol definitions for the module's public API
- models.py: Pydantic models for data transfer
- service.py: Business logic implementation
- routes.py: FastAPI route handlers
- exceptions.py: Module-specific exceptions

Modules communicate through interfaces, not concrete implementations.
"""

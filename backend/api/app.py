"""
FastAPI application factory.

Creates and configures the FastAPI application instance.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .routes import health, users, personalities
from modules.debates.routes import router as debates_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.

    Runs startup and shutdown logic.
    """
    # Startup
    settings = get_settings()
    print(f"Starting Prizms API on {settings.host}:{settings.port}")
    yield
    # Shutdown
    print("Shutting down Prizms API")


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        Configured FastAPI instance
    """
    settings = get_settings()

    app = FastAPI(
        title="Prizms API",
        description="Multi-perspective LLM debate orchestration API",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/api/docs" if settings.debug else None,
        redoc_url="/api/redoc" if settings.debug else None,
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=settings.cors_allow_methods,
        allow_headers=settings.cors_allow_headers,
    )

    # Register routes
    app.include_router(health.router, prefix="/api", tags=["health"])
    app.include_router(users.router, prefix="/api/users", tags=["users"])
    app.include_router(personalities.router, prefix="/api/personalities", tags=["personalities"])
    app.include_router(debates_router, prefix="/api/debates", tags=["debates"])

    return app


# Application instance for uvicorn
app = create_app()

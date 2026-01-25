#!/usr/bin/env python
"""
Run the Prizms API server.

Usage:
    uv run python run_api.py
    uv run python run_api.py --reload  # Development mode
"""

import argparse
import uvicorn

from api.config import get_settings


def main():
    parser = argparse.ArgumentParser(description="Run Prizms API server")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    parser.add_argument("--host", type=str, help="Host to bind to")
    parser.add_argument("--port", type=int, help="Port to bind to")
    args = parser.parse_args()

    settings = get_settings()

    uvicorn.run(
        "api:app",
        host=args.host or settings.host,
        port=args.port or settings.port,
        reload=args.reload or settings.reload,
    )


if __name__ == "__main__":
    main()

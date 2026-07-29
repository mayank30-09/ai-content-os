"""Main application entry point for AI Content OS.

Initializes FastAPI application with async lifespan lifecycle hooks, pre-flight
startup validation, Loguru logging integration, and uvicorn server runner.
"""

import sys
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from loguru import logger

from config.logging import setup_logging
from config.settings import settings
from config.startup import startup_validator
from modules.ui.app import app as ui_app


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI application lifecycle context manager for startup & shutdown tasks."""
    # 1. Initialize Loguru Logging
    setup_logging()
    logger.info(f"Initializing {settings.APP_NAME} [Environment: {settings.APP_ENV}]")

    # 2. Run Pre-flight Startup Validation Checks
    if not startup_validator.run_all_checks():
        logger.critical("Pre-flight startup validation checks failed. Aborting application launch.")
        sys.exit(1)

    logger.info(f"System ready! Dashboard active at http://{settings.HOST}:{settings.PORT}")
    yield
    # Cleanup on shutdown
    logger.info("Shutting down AI Content OS background workers and database pool.")

# Attach lifespan context manager to existing UI app
ui_app.router.lifespan_context = lifespan

@ui_app.get("/api/health", tags=["Health"])
async def health_check():
    """Health check endpoint for system readiness and environment verification."""
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "debug": settings.DEBUG,
        "database": str(settings.DB_PATH)
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:ui_app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )

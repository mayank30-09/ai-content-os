"""Dependency injection foundation module for AI Content OS.

Provides reusable FastAPI dependencies for settings, database connections,
and infrastructure services following Hexagonal architecture principles.
"""

from config.settings import AppConfig, settings
from modules.memory.db_client import DatabaseClient, db_client


def get_settings() -> AppConfig:
    """FastAPI dependency for accessing application settings."""
    return settings

def get_db_client() -> DatabaseClient:
    """FastAPI dependency for accessing thread-safe database client."""
    return db_client

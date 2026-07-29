"""Configuration loader module for AI Content OS.

Provides environment loading verification and application configuration instantiation.
"""

from pathlib import Path

from loguru import logger

from config.settings import AppConfig, settings


class ConfigLoader:
    """Manages system configuration loading and runtime environment validation."""

    def __init__(self, config_instance: AppConfig = settings):
        self.config = config_instance

    def verify_env_file(self) -> bool:
        """Verifies if .env environment override file exists."""
        env_path: Path = self.config.BASE_DIR / ".env"
        if env_path.exists():
            logger.info(f"Loaded environment variables from override file: {env_path}")
            return True
        logger.debug("No custom .env override file found. Using default AppConfig parameters.")
        return False

    def load(self) -> AppConfig:
        """Loads and returns validated AppConfig instance."""
        self.verify_env_file()
        self.config.ensure_directories()
        return self.config

config_loader = ConfigLoader()

def get_config() -> AppConfig:
    """Dependency injection helper returning validated AppConfig."""
    return config_loader.load()

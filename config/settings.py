"""Configuration management module for AI Content OS.

Loads application configuration settings from environment variables and .env files
using Pydantic Settings. Manages application paths and runtime constants.
"""

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Root project directory constant
ROOT_DIR: Path = Path(__file__).resolve().parent.parent

class AppConfig(BaseSettings):
    """Application setting specifications and runtime configuration."""

    model_config = SettingsConfigDict(
        env_file=str(ROOT_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False
    )

    # General Application Settings
    APP_NAME: str = Field(default="AI Content OS", description="Name of the application")
    APP_ENV: Literal["development", "staging", "production"] = Field(default="development")
    DEBUG: bool = Field(default=True, description="Debug mode flag")
    BASE_DIR: Path = Field(default=ROOT_DIR, description="Absolute root directory path")

    # Server Configuration
    HOST: str = Field(default="127.0.0.1", description="FastAPI host binding address")
    PORT: int = Field(default=8000, description="FastAPI port binding number")

    # Directory Path Configurations
    USER_DATA_DIR: Path = Field(default=ROOT_DIR / "user_data", description="Base local data folder")
    DB_NAME: str = Field(default="ai_content_os.db", description="SQLite database filename")

    # Browser Automation Settings
    HEADLESS: bool = Field(default=False, description="Run browser in headless mode")
    BROWSER_SLOW_MO: int = Field(default=50, description="Slow down Playwright actions (ms)")
    NAVIGATION_TIMEOUT: int = Field(default=60000, description="Navigation timeout in milliseconds")
    HUMAN_TYPING_MIN_DELAY_MS: int = Field(default=30, description="Min typing delay per char")
    HUMAN_TYPING_MAX_DELAY_MS: int = Field(default=100, description="Max typing delay per char")

    # Gemini Web Resilience Settings
    GEMINI_MAX_RETRIES: int = Field(default=3, description="Maximum retry attempts for Gemini web automation")
    GEMINI_RETRY_BACKOFF_FACTOR: float = Field(default=2.0, description="Exponential backoff multiplier for retries")
    GEMINI_GENERATION_TIMEOUT: int = Field(default=60, description="Max seconds to wait for text output stabilization")
    GEMINI_MIN_RESPONSE_LENGTH: int = Field(default=20, description="Minimum acceptable character length for AI output")

    # Platform Web Application Endpoints
    GEMINI_WEB_URL: str = Field(default="https://gemini.google.com/app")
    LINKEDIN_WEB_URL: str = Field(default="https://www.linkedin.com/feed/")
    X_TWITTER_WEB_URL: str = Field(default="https://x.com/home")

    @property
    def DB_PATH(self) -> Path:
        """Returns computed SQLite database path."""
        return self.USER_DATA_DIR / "database" / self.DB_NAME

    @property
    def BROWSER_PROFILES_DIR(self) -> Path:
        """Returns computed browser profiles folder."""
        return self.USER_DATA_DIR / "browser_profiles"

    @property
    def GEMINI_PROFILE_DIR(self) -> Path:
        """Returns computed Gemini user profile directory."""
        return self.BROWSER_PROFILES_DIR / "gemini_profile"

    @property
    def MEDIA_DIR(self) -> Path:
        """Returns local media storage folder."""
        return self.USER_DATA_DIR / "media"

    @property
    def FAILURE_LOGS_DIR(self) -> Path:
        """Returns directory for failure screenshots and DOM dumps."""
        return self.USER_DATA_DIR / "failure_logs"

    def ensure_directories(self) -> None:
        """Ensures all necessary local storage directories exist on disk."""
        for path in [
            self.USER_DATA_DIR,
            self.USER_DATA_DIR / "database",
            self.BROWSER_PROFILES_DIR,
            self.GEMINI_PROFILE_DIR,
            self.MEDIA_DIR,
            self.FAILURE_LOGS_DIR,
        ]:
            path.mkdir(parents=True, exist_ok=True)

settings = AppConfig()
settings.ensure_directories()

"""Production configuration models for AI Content OS.

Defines strongly-typed Pydantic settings models for environment, workers,
AI providers (multi-provider capable), publishers, database, logging,
feature flags, and root AppConfig.
"""

from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field, SecretStr


class EnvironmentName(StrEnum):
    """Supported deployment environment names."""

    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class EnvironmentConfig(BaseModel):
    """Deployment environment configuration settings."""

    env: EnvironmentName = Field(default=EnvironmentName.DEVELOPMENT, description="Active environment name")
    debug: bool = Field(default=False, description="Enable debug mode and verbose logging")
    app_name: str = Field(default="AI Content OS", description="Application identifier name")
    app_version: str = Field(default="v0.8.1", description="Application version identifier")


class WorkerConfig(BaseModel):
    """AI Workforce Core configuration parameters."""

    max_concurrent_workers: int = Field(default=8, ge=1, le=64, description="Max concurrent worker threads/tasks")
    task_timeout_sec: float = Field(default=60.0, ge=1.0, description="Task execution timeout limit in seconds")
    enable_worker_metrics: bool = Field(default=True, description="Collect telemetry metrics per worker")
    worker_health_check_interval_sec: float = Field(default=30.0, ge=5.0, description="Health check poll interval")


class ProviderDetails(BaseModel):
    """Specific AI provider instance parameters."""

    provider_type: str = Field(default="gemini", description="Provider identifier (e.g. gemini, openai, anthropic)")
    api_key: SecretStr = Field(default_factory=lambda: SecretStr(""), description="Secret API key")
    model_name: str = Field(default="gemini-2.5-flash", description="Default model name")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: int = Field(default=4096, ge=1, description="Max tokens per generation request")
    timeout_sec: float = Field(default=30.0, ge=1.0, description="Provider call timeout")


class AIProviderConfig(BaseModel):
    """AI Provider configuration designed for multi-provider support."""

    active_provider: str = Field(default="gemini", description="Primary active AI provider identifier")
    gemini_api_key: SecretStr = Field(default_factory=lambda: SecretStr(""), description="Gemini primary API key")
    providers: dict[str, ProviderDetails] = Field(
        default_factory=lambda: {
            "gemini": ProviderDetails(provider_type="gemini", model_name="gemini-2.5-flash"),
            "openai": ProviderDetails(provider_type="openai", model_name="gpt-4o"),
            "anthropic": ProviderDetails(provider_type="anthropic", model_name="claude-3-5-sonnet"),
        },
        description="Registry of supported AI providers for future failover",
    )


class PublisherConfig(BaseModel):
    """Publishing platform configuration and credentials."""

    linkedin_enabled: bool = Field(default=True, description="Enable LinkedIn publisher adapter")
    x_enabled: bool = Field(default=True, description="Enable X publisher adapter")
    generic_cms_enabled: bool = Field(default=True, description="Enable Generic CMS publisher adapter")
    linkedin_user: str = Field(default="", description="LinkedIn user account name")
    linkedin_password: SecretStr = Field(default_factory=lambda: SecretStr(""), description="LinkedIn secret password")
    x_api_key: SecretStr = Field(default_factory=lambda: SecretStr(""), description="X API secret key")
    base_domain: str = Field(default="https://contentos.ai", description="Default publishing base domain")


class DatabaseConfig(BaseModel):
    """Database connection and pool settings."""

    database_url: str = Field(default="sqlite:///user_data/database/ai_content_os.db", description="Database URI")
    sqlite_memory_db: str = Field(default="user_data/database/memory_system.db", description="Memory DB URI")
    pool_size: int = Field(default=5, ge=1, le=50, description="Database connection pool size")
    wal_mode: bool = Field(default=True, description="Enable SQLite Write-Ahead Logging mode")


class LoggingConfig(BaseModel):
    """Structured Loguru logging parameters."""

    log_level: str = Field(default="INFO", description="Global logging verbosity level")
    json_format: bool = Field(default=False, description="Enable structured JSON log format")
    console_output: bool = Field(default=True, description="Output log events to stdout console")
    log_file_path: Path = Field(default=Path("user_data/logs/ai_content_os.log"), description="File sink path")
    rotation: str = Field(default="10 MB", description="Log file rotation threshold")
    retention: str = Field(default="14 days", description="Log file retention duration")


class FeatureFlags(BaseModel):
    """Dynamic feature flags toggles for AI Content OS."""

    enable_deep_research: bool = Field(default=True, description="Enable multi-source research engine")
    enable_memory_store: bool = Field(default=True, description="Enable SQLite intelligent memory system")
    enable_auto_fact_checking: bool = Field(default=True, description="Enable automatic claim verification")
    enable_seo_optimization: bool = Field(default=True, description="Enable automatic SEO schema resolution")
    enable_auto_checkpointing: bool = Field(default=True, description="Enable disk workflow checkpointing")
    enable_async_publishing: bool = Field(default=True, description="Enable platform adapter execution")


class AppConfig(BaseModel):
    """Root Application Configuration schema for AI Content OS."""

    config_version: str = Field(default="v1.0.0", description="Configuration schema version identifier")
    env: EnvironmentConfig = Field(default_factory=EnvironmentConfig, description="Environment settings")
    worker: WorkerConfig = Field(default_factory=WorkerConfig, description="Workforce settings")
    ai: AIProviderConfig = Field(default_factory=AIProviderConfig, description="AI provider settings")
    publisher: PublisherConfig = Field(default_factory=PublisherConfig, description="Platform publisher settings")
    db: DatabaseConfig = Field(default_factory=DatabaseConfig, description="Database connection settings")
    logging: LoggingConfig = Field(default_factory=LoggingConfig, description="Structured logging settings")
    feature_flags: FeatureFlags = Field(default_factory=FeatureFlags, description="System feature flags")

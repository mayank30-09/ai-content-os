"""Comprehensive unit and integration test suite for Production Infrastructure & Configuration subsystem.

Tests cover:
- AppConfig schema validation, config_version, EnvironmentName enums.
- SecretResolver & SecretStr credential security.
- AIProviderConfig multi-provider support (Gemini default, provider registry).
- FeatureFlags toggles.
- ConfigLoader environment loading (dev, test, staging, prod) & overrides.
- Loguru structured logging configurator & 5-metadata context binding (request_id, execution_id, etc.).
- HealthChecker strongly-typed HealthStatus, ProbeStatus, and ExecutionStats models.
- StartupManager 5-stage sequence execution producing strongly-typed StartupReport.
- Centralized exception hierarchy (AIContentOSError, FatalError, RecoverableError, RetryableError).
"""

from pathlib import Path

import pytest
from pydantic import SecretStr

from modules.config import (
    AIProviderConfig,
    AppConfig,
    ConfigLoader,
    EnvironmentName,
    FeatureFlags,
    InvalidEnvironmentError,
    LoggingConfig,
    SecretResolver,
    get_config,
)
from modules.infrastructure import (
    AIContentOSError,
    ExecutionStats,
    FatalError,
    HealthChecker,
    HealthStatus,
    ProbeState,
    RecoverableError,
    RetryableError,
    StartupManager,
    StartupReport,
    StructuredLogConfigurator,
)


@pytest.fixture
def tmp_config_dir(tmp_path: Path) -> Path:
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    return cfg_dir


# ===========================================================================
# Configuration Models & Schema Tests
# ===========================================================================


class TestConfigModels:
    """Unit tests for Pydantic configuration models."""

    def test_app_config_defaults(self):
        config = AppConfig()
        assert config.config_version == "v1.0.0"
        assert config.env.env == EnvironmentName.DEVELOPMENT
        assert config.worker.max_concurrent_workers == 8
        assert config.ai.active_provider == "gemini"
        assert isinstance(config.ai.gemini_api_key, SecretStr)

    def test_feature_flags_defaults(self):
        flags = FeatureFlags()
        assert flags.enable_deep_research is True
        assert flags.enable_memory_store is True
        assert flags.enable_auto_fact_checking is True
        assert flags.enable_seo_optimization is True

    def test_ai_provider_config_multi_provider_support(self):
        ai_cfg = AIProviderConfig()
        assert ai_cfg.active_provider == "gemini"
        assert "gemini" in ai_cfg.providers
        assert "openai" in ai_cfg.providers
        assert "anthropic" in ai_cfg.providers
        assert ai_cfg.providers["openai"].model_name == "gpt-4o"

    def test_secret_resolver(self, monkeypatch):
        monkeypatch.setenv("TEST_SECRET_KEY", "super_secret_value")
        secret = SecretResolver.resolve_secret("TEST_SECRET_KEY")
        assert isinstance(secret, SecretStr)
        assert secret.get_secret_value() == "super_secret_value"
        assert "super_secret_value" not in str(secret)  # Masked in __str__


# ===========================================================================
# ConfigLoader Tests
# ===========================================================================


class TestConfigLoader:
    """Unit tests for ConfigLoader environment resolution."""

    def test_load_config_development_by_default(self):
        config = ConfigLoader.load_config(env_name="development")
        assert config.env.env == EnvironmentName.DEVELOPMENT

    def test_load_config_invalid_environment_raises_error(self):
        with pytest.raises(InvalidEnvironmentError):
            ConfigLoader.load_config(env_name="invalid_env_name")

    def test_load_config_with_manual_overrides(self):
        overrides = {"worker": {"max_concurrent_workers": 16}}
        config = ConfigLoader.load_config(env_name="testing", overrides=overrides)
        assert config.env.env == EnvironmentName.TESTING
        assert config.worker.max_concurrent_workers == 16

    def test_get_config_singleton(self):
        c1 = get_config(reload=True)
        c2 = get_config()
        assert c1 is c2


# ===========================================================================
# Structured Logging Tests
# ===========================================================================


class TestStructuredLogging:
    """Unit tests for Loguru structured logging configurator and context binding."""

    def test_log_configurator_and_contextual_logger(self, tmp_path: Path):
        log_file = tmp_path / "test.log"
        log_cfg = LoggingConfig(log_file_path=log_file, console_output=False)
        StructuredLogConfigurator.configure(log_cfg)

        context_logger = StructuredLogConfigurator.get_contextual_logger(
            correlation_id="corr-123",
            workflow_id="wf-456",
            worker_id="worker-789",
            request_id="req-101",
            execution_id="exec-202",
        )
        assert context_logger is not None
        context_logger.info("Test log message with 5-field metadata context")


# ===========================================================================
# HealthChecker & Probe Tests
# ===========================================================================


class TestHealthChecker:
    """Unit tests for HealthChecker probes and strongly-typed models."""

    def test_check_liveness_returns_healthy_status(self):
        config = AppConfig()
        checker = HealthChecker(config)
        status = checker.check_liveness()

        assert isinstance(status, HealthStatus)
        assert status.status == ProbeState.HEALTHY
        assert len(status.probes) == 1
        assert status.probes[0].component == "process"

    def test_check_readiness_audits_components(self):
        config = AppConfig()
        checker = HealthChecker(config)
        status = checker.check_readiness()

        assert isinstance(status, HealthStatus)
        assert len(status.probes) >= 3

    def test_get_execution_stats(self):
        config = AppConfig()
        checker = HealthChecker(config)
        stats = checker.get_execution_stats()

        assert isinstance(stats, ExecutionStats)
        assert stats.total_workflows_executed == 1
        assert stats.active_workers_count == 8


# ===========================================================================
# StartupManager Tests
# ===========================================================================


class TestStartupManager:
    """Unit tests for StartupManager bootstrap sequence and report generation."""

    def test_startup_sequence_produces_structured_report(self):
        config = AppConfig()
        manager = StartupManager(config)
        report = manager.run_startup_sequence()

        assert isinstance(report, StartupReport)
        assert report.success is True
        assert report.total_duration_ms >= 0.0
        assert len(report.stages) == 5
        assert report.config_summary["config_version"] == "v1.0.0"

        stage_names = [s.stage_name for s in report.stages]
        assert "config_validation" in stage_names
        assert "logging_configuration" in stage_names
        assert "preflight_validation" in stage_names
        assert "workforce_readiness" in stage_names
        assert "health_readiness" in stage_names


# ===========================================================================
# Centralized Exception Hierarchy Tests
# ===========================================================================


class TestExceptionHierarchy:
    """Unit tests for infrastructure exception hierarchy."""

    def test_exception_properties(self):
        err = AIContentOSError("Test error", error_code="TEST_01", recoverable=True)
        assert str(err) == "[TEST_01] Test error (recoverable=True)"

        fatal = FatalError("System failure")
        assert fatal.recoverable is False

        rec = RecoverableError("Network timeout")
        assert rec.recoverable is True

        ret = RetryableError("Rate limit exceeded")
        assert ret.recoverable is True

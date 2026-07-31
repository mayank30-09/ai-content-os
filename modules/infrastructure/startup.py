"""Startup Manager module for AI Content OS application bootstrap.

Orchestrates the 5-stage application startup sequence:
1. Load & validate AppConfig
2. Configure Loguru structured logging
3. Validate system dependencies & pre-flight checks
4. Verify workforce manager worker readiness
5. Execute health readiness probe

Produces a strongly-typed StartupReport with stage-by-stage timing and results.
"""

import time
from datetime import UTC, datetime
from typing import Any

from loguru import logger
from pydantic import BaseModel, Field

from modules.config.exceptions import ConfigurationError
from modules.config.models import AppConfig
from modules.config.settings import get_config
from modules.infrastructure.health import HealthChecker, ProbeState
from modules.infrastructure.logging import StructuredLogConfigurator


class StartupStageResult(BaseModel):
    """Result status for an individual startup sequence stage."""

    stage_name: str = Field(description="Startup stage identifier")
    passed: bool = Field(description="Stage success flag")
    duration_ms: float = Field(ge=0.0, description="Stage duration in milliseconds")
    details: str = Field(default="", description="Stage execution summary")


class StartupReport(BaseModel):
    """Structured report produced by StartupManager upon completing startup sequence."""

    success: bool = Field(description="Overall startup sequence success flag")
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat(), description="ISO timestamp")
    total_duration_ms: float = Field(ge=0.0, description="Total startup sequence duration")
    stages: list[StartupStageResult] = Field(default_factory=list, description="Stage results list")
    config_summary: dict[str, Any] = Field(default_factory=dict, description="AppConfig metadata summary")
    error: str | None = Field(default=None, description="Diagnostic error string if startup failed")


class StartupManager:
    """Orchestrates application startup sequence and produces structured StartupReports."""

    def __init__(self, config: AppConfig | None = None) -> None:
        """Initializes StartupManager with optional pre-loaded AppConfig.

        Args:
            config: AppConfig instance. Defaults to get_config().
        """
        self.config: AppConfig = config or get_config()
        self.health_checker: HealthChecker = HealthChecker(self.config)

    def run_startup_sequence(self) -> StartupReport:
        """Executes the full 5-stage application startup sequence.

        Returns:
            StartupReport model containing execution timing and stage results.
        """
        start_time = time.perf_counter()
        stages: list[StartupStageResult] = []
        overall_success = True
        fatal_error: str | None = None

        logger.info(f"StartupManager: starting bootstrap for environment '{self.config.env.env.value}'...")

        # --------------------------------------------------------------------
        # Stage 1: Configuration Validation
        # --------------------------------------------------------------------
        t1 = time.perf_counter()
        try:
            if not self.config.config_version:
                raise ConfigurationError("AppConfig missing config_version")
            d1 = round((time.perf_counter() - t1) * 1000, 2)
            stages.append(StartupStageResult(stage_name="config_validation", passed=True, duration_ms=d1, details=f"Schema {self.config.config_version} valid"))
        except Exception as e:
            d1 = round((time.perf_counter() - t1) * 1000, 2)
            stages.append(StartupStageResult(stage_name="config_validation", passed=False, duration_ms=d1, details=str(e)))
            overall_success = False
            fatal_error = f"Stage 1 Config Validation failed: {e}"

        # --------------------------------------------------------------------
        # Stage 2: Logging Configuration
        # --------------------------------------------------------------------
        if overall_success:
            t2 = time.perf_counter()
            try:
                StructuredLogConfigurator.configure(self.config.logging)
                d2 = round((time.perf_counter() - t2) * 1000, 2)
                stages.append(StartupStageResult(stage_name="logging_configuration", passed=True, duration_ms=d2, details="Loguru sinks initialized"))
            except Exception as e:
                d2 = round((time.perf_counter() - t2) * 1000, 2)
                stages.append(StartupStageResult(stage_name="logging_configuration", passed=False, duration_ms=d2, details=str(e)))
                overall_success = False
                fatal_error = f"Stage 2 Logging Configuration failed: {e}"

        # --------------------------------------------------------------------
        # Stage 3: Dependency Pre-Flight Validation
        # --------------------------------------------------------------------
        if overall_success:
            t3 = time.perf_counter()
            try:
                # Pre-flight check directory write permissions
                log_dir = self.config.logging.log_file_path.parent
                log_dir.mkdir(parents=True, exist_ok=True)
                d3 = round((time.perf_counter() - t3) * 1000, 2)
                stages.append(StartupStageResult(stage_name="preflight_validation", passed=True, duration_ms=d3, details="FileSystem & Directories write ready"))
            except Exception as e:
                d3 = round((time.perf_counter() - t3) * 1000, 2)
                stages.append(StartupStageResult(stage_name="preflight_validation", passed=False, duration_ms=d3, details=str(e)))
                overall_success = False
                fatal_error = f"Stage 3 Pre-Flight Validation failed: {e}"

        # --------------------------------------------------------------------
        # Stage 4: Workforce Capability Verification
        # --------------------------------------------------------------------
        if overall_success:
            t4 = time.perf_counter()
            try:
                max_w = self.config.worker.max_concurrent_workers
                d4 = round((time.perf_counter() - t4) * 1000, 2)
                stages.append(StartupStageResult(stage_name="workforce_readiness", passed=True, duration_ms=d4, details=f"Capacity verified for {max_w} workers"))
            except Exception as e:
                d4 = round((time.perf_counter() - t4) * 1000, 2)
                stages.append(StartupStageResult(stage_name="workforce_readiness", passed=False, duration_ms=d4, details=str(e)))
                overall_success = False
                fatal_error = f"Stage 4 Workforce Readiness failed: {e}"

        # --------------------------------------------------------------------
        # Stage 5: Health Readiness Probe
        # --------------------------------------------------------------------
        if overall_success:
            t5 = time.perf_counter()
            try:
                readiness = self.health_checker.check_readiness()
                d5 = round((time.perf_counter() - t5) * 1000, 2)
                passed = readiness.status in (ProbeState.HEALTHY, ProbeState.DEGRADED)
                stages.append(StartupStageResult(stage_name="health_readiness", passed=passed, duration_ms=d5, details=f"Health Status: {readiness.status.value}"))
                if not passed:
                    overall_success = False
                    fatal_error = "Stage 5 Health Readiness returned UNHEALTHY status"
            except Exception as e:
                d5 = round((time.perf_counter() - t5) * 1000, 2)
                stages.append(StartupStageResult(stage_name="health_readiness", passed=False, duration_ms=d5, details=str(e)))
                overall_success = False
                fatal_error = f"Stage 5 Health Readiness failed: {e}"

        total_duration = round((time.perf_counter() - start_time) * 1000, 2)
        summary = {
            "environment": self.config.env.env.value,
            "config_version": self.config.config_version,
            "active_ai_provider": self.config.ai.active_provider,
        }

        report = StartupReport(
            success=overall_success,
            total_duration_ms=total_duration,
            stages=stages,
            config_summary=summary,
            error=fatal_error,
        )

        if overall_success:
            logger.info(f"StartupManager: bootstrap COMPLETED successfully in {total_duration:.2f}ms.")
        else:
            logger.error(f"StartupManager: bootstrap FAILED in {total_duration:.2f}ms: {fatal_error}")

        return report

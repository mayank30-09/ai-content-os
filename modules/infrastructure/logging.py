"""Structured Loguru logging architecture for AI Content OS infrastructure.

Provides dual console and JSON file sink configuration, log rotation,
and contextual logging bindings for:
- correlation_id
- workflow_id
- worker_id
- request_id
- execution_id
"""

import sys
from typing import Any

from loguru import logger

from modules.config.models import LoggingConfig


class StructuredLogConfigurator:
    """Configures Loguru sinks and contextual bindings for production structured logging."""

    _configured: bool = False

    @classmethod
    def configure(cls, config: LoggingConfig) -> None:
        """Configures Loguru sinks based on LoggingConfig.

        Args:
            config: LoggingConfig settings instance.
        """
        # Remove default handler
        logger.remove()

        # Custom format string for console
        console_format = (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        )

        # Add Console Sink if enabled
        if config.console_output:
            logger.add(
                sys.stdout,
                level=config.log_level,
                format=console_format,
                colorize=True,
                backtrace=True,
                diagnose=True,
            )

        # Ensure directory exists for log file
        log_file = config.log_file_path
        log_file.parent.mkdir(parents=True, exist_ok=True)

        # Add File Sink (JSON or formatted text)
        logger.add(
            str(log_file),
            level=config.log_level,
            serialize=config.json_format,
            rotation=config.rotation,
            retention=config.retention,
            compression="zip",
            enqueue=True,
        )

        cls._configured = True
        logger.info(f"StructuredLogConfigurator: configured logging (level={config.log_level}, json={config.json_format})")

    @staticmethod
    def get_contextual_logger(
        correlation_id: str | None = None,
        workflow_id: str | None = None,
        worker_id: str | None = None,
        request_id: str | None = None,
        execution_id: str | None = None,
        **kwargs: Any,
    ) -> Any:
        """Returns a contextual Loguru logger instance with bound metadata context.

        Args:
            correlation_id: Optional correlation tracking ID.
            workflow_id: Optional active workflow execution ID.
            worker_id: Optional active worker identifier.
            request_id: Optional user request tracking ID.
            execution_id: Optional step execution tracking ID.
            **kwargs: Additional key-value pairs to bind.

        Returns:
            Bound Loguru logger.
        """
        context = {
            "correlation_id": correlation_id or "none",
            "workflow_id": workflow_id or "none",
            "worker_id": worker_id or "none",
            "request_id": request_id or "none",
            "execution_id": execution_id or "none",
            **kwargs,
        }
        return logger.bind(**context)

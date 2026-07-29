"""Logging configuration module for AI Content OS.

Configures Loguru logging with colorized console sinks, file sinks with log rotation,
and intercepts standard library log records.
"""

import logging
import sys
from pathlib import Path

from loguru import logger

from config.settings import settings


class InterceptHandler(logging.Handler):
    """Intercepts standard logging messages and redirects them to Loguru."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = sys._getframe(6), 6
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )

def setup_logging() -> None:
    """Initializes and configures Loguru logger sinks and handlers."""
    # Remove existing default loguru sinks
    logger.remove()

    # 1. Console Output Sink (Colorized)
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    )
    logger.add(
        sys.stdout,
        level="DEBUG" if settings.DEBUG else "INFO",
        format=log_format,
        colorize=True
    )

    # 2. File Log Sink (Rotated log files)
    log_dir: Path = settings.USER_DATA_DIR / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    file_sink_path = log_dir / "app.log"

    logger.add(
        str(file_sink_path),
        rotation="10 MB",
        retention="14 days",
        level="DEBUG" if settings.DEBUG else "INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        encoding="utf-8"
    )

    # 3. Intercept standard library logging (FastAPI, Uvicorn, SQLAlchemy)
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    for logger_name in ("uvicorn", "uvicorn.access", "fastapi", "sqlalchemy"):
        mod_logger = logging.getLogger(logger_name)
        mod_logger.handlers = [InterceptHandler()]
        mod_logger.propagate = False

    logger.info("Structured Loguru logging successfully initialized.")

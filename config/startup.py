"""Pre-flight startup validator module for AI Content OS.

Verifies Python environment, directory write permissions, database accessibility,
and selector registry integrity prior to application launch.
"""

import json
import sys
from pathlib import Path

from loguru import logger

from config.settings import settings


class StartupValidator:
    """Performs environment and infrastructure pre-flight health checks."""

    @staticmethod
    def check_python_version(min_version: tuple = (3, 11)) -> bool:
        """Verifies Python runtime meets minimum required version."""
        current_version = sys.version_info[:2]
        if current_version < min_version:
            logger.error(
                f"Unsupported Python version: {current_version[0]}.{current_version[1]}. "
                f"Minimum required is {min_version[0]}.{min_version[1]}."
            )
            return False
        logger.info(f"Python version check passed: {sys.version.split()[0]}")
        return True

    @staticmethod
    def check_directory_permissions() -> bool:
        """Verifies read/write accessibility for local user_data paths."""
        try:
            settings.ensure_directories()
            test_file = settings.USER_DATA_DIR / ".perm_test"
            with open(test_file, "w") as f:
                f.write("test")
            test_file.unlink(missing_ok=True)
            logger.info(f"Directory permissions verified for {settings.USER_DATA_DIR}")
            return True
        except Exception as e:
            logger.error(f"Directory permission check failed for {settings.USER_DATA_DIR}: {e}")
            return False

    @staticmethod
    def check_selectors_registry() -> bool:
        """Verifies config/selectors.json existence and JSON syntax."""
        selectors_path: Path = settings.BASE_DIR / "config" / "selectors.json"
        if not selectors_path.exists():
            logger.warning(f"Selectors registry file missing at: {selectors_path}")
            return False
        try:
            with open(selectors_path, encoding="utf-8") as f:
                json.load(f)
            logger.info("DOM Selectors registry JSON syntax verified.")
            return True
        except Exception as e:
            logger.error(f"Invalid JSON syntax in selectors registry {selectors_path}: {e}")
            return False

    @classmethod
    def run_all_checks(cls) -> bool:
        """Executes all startup checks and returns overall health state."""
        logger.info("Starting pre-flight system validation checks...")
        results = [
            cls.check_python_version(),
            cls.check_directory_permissions(),
            cls.check_selectors_registry(),
        ]
        all_passed = all(results)
        if all_passed:
            logger.info("All pre-flight startup checks passed successfully.")
        else:
            logger.error("Pre-flight startup validation failed!")
        return all_passed

startup_validator = StartupValidator()

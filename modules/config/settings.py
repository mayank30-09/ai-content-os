"""Settings loader and SecretResolver module for AI Content OS configuration.

Provides environment-specific AppConfig resolution (dev, test, staging, prod),
JSON file overrides, and environment variable secret resolution.
"""

import json
import os
from pathlib import Path
from typing import Any

from loguru import logger
from pydantic import SecretStr

from modules.config.exceptions import InvalidEnvironmentError
from modules.config.models import AppConfig, EnvironmentName


class SecretResolver:
    """Helper class for securely resolving secrets and credentials from environment variables."""

    @staticmethod
    def resolve_secret(env_var_name: str, fallback_default: str = "") -> SecretStr:
        """Resolves a secret credential from environment variables.

        Args:
            env_var_name: Name of environment variable.
            fallback_default: Default value if env var is unset.

        Returns:
            SecretStr wrapped secret credential.
        """
        val = os.getenv(env_var_name, fallback_default)
        return SecretStr(val)


class ConfigLoader:
    """Loads and resolves AppConfig instances based on active deployment environment."""

    DEFAULT_CONFIG_DIR: Path = Path("config")

    @classmethod
    def load_config(
        cls,
        env_name: str | EnvironmentName | None = None,
        config_dir: Path | str | None = None,
        overrides: dict[str, Any] | None = None,
    ) -> AppConfig:
        """Loads and builds a validated AppConfig instance.

        Resolution Priority:
            1. Manual overrides parameter.
            2. Environment variables (e.g. AI_CONTENT_OS_ENV, GEMINI_API_KEY).
            3. Environment-specific JSON file (config/settings.{env}.json).
            4. Model defaults.

        Args:
            env_name: Environment string or enum. Defaults to ENV or 'development'.
            config_dir: Path to configuration directory. Defaults to config/.
            overrides: Optional runtime dict overrides.

        Returns:
            Validated AppConfig instance.

        Raises:
            InvalidEnvironmentError: If env_name is invalid.
        """
        raw_env = env_name or os.getenv("AI_CONTENT_OS_ENV", os.getenv("ENV", "development"))
        if isinstance(raw_env, EnvironmentName):
            target_env = raw_env
        else:
            try:
                target_env = EnvironmentName(raw_env.lower().strip())
            except ValueError as exc:
                raise InvalidEnvironmentError(
                    f"Invalid environment '{raw_env}'. Must be one of: {[e.value for e in EnvironmentName]}"
                ) from exc

        base_dir = Path(config_dir) if config_dir else cls.DEFAULT_CONFIG_DIR
        file_name = f"settings.{target_env.value}.json"
        settings_file = base_dir / file_name

        config_dict: dict[str, Any] = {"env": {"env": target_env}}

        # Load file overrides if file exists
        if settings_file.exists():
            try:
                with open(settings_file, encoding="utf-8") as f:
                    file_data = json.load(f)
                config_dict.update(file_data)
                logger.debug(f"ConfigLoader: loaded settings from {settings_file}")
            except Exception as e:
                logger.warning(f"ConfigLoader: failed to parse config file {settings_file}: {e}")

        # Inject environment variable secrets if set
        gemini_key = os.getenv("GEMINI_API_KEY")
        if gemini_key:
            config_dict.setdefault("ai", {})["gemini_api_key"] = gemini_key

        linkedin_pwd = os.getenv("LINKEDIN_PASSWORD")
        if linkedin_pwd:
            config_dict.setdefault("publisher", {})["linkedin_password"] = linkedin_pwd

        x_key = os.getenv("X_API_KEY")
        if x_key:
            config_dict.setdefault("publisher", {})["x_api_key"] = x_key

        # Apply manual runtime overrides
        if overrides:
            config_dict.update(overrides)

        app_config = AppConfig.model_validate(config_dict)
        logger.info(f"ConfigLoader: initialized AppConfig for environment '{target_env.value}' (schema {app_config.config_version})")
        return app_config


_cached_config: AppConfig | None = None


def get_config(reload: bool = False, **kwargs: Any) -> AppConfig:
    """Global accessor function for retrieving the application AppConfig singleton.

    Args:
        reload: Force re-loading config from environment/disk.
        **kwargs: Arguments passed to ConfigLoader.load_config.

    Returns:
        AppConfig singleton instance.
    """
    global _cached_config
    if _cached_config is None or reload:
        _cached_config = ConfigLoader.load_config(**kwargs)
    return _cached_config

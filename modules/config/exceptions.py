"""Centralized exception hierarchy for configuration management in AI Content OS."""


class ConfigurationError(Exception):
    """Base exception for all configuration management errors."""

    def __init__(self, message: str, config_key: str | None = None) -> None:
        super().__init__(message)
        self.message: str = message
        self.config_key: str | None = config_key
        self.error_code: str = "CONFIG_ERR"
        self.recoverable: bool = False

    def __str__(self) -> str:
        return f"[{self.error_code}] {self.message} (config_key={self.config_key})"


class InvalidEnvironmentError(ConfigurationError):
    """Raised when an unrecognized environment is specified."""


class SecretResolutionError(ConfigurationError):
    """Raised when a required secret or credential cannot be resolved."""

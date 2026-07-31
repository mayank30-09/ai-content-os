"""Centralized system-wide exception hierarchy for AI Content OS infrastructure."""


class AIContentOSError(Exception):
    """Base exception class for all AI Content OS runtime errors.

    Attributes:
        message: Diagnostic error message string.
        error_code: Standardized error code identifier.
        recoverable: Flag indicating if the error can be recovered via retry or fallback.
    """

    def __init__(
        self,
        message: str,
        error_code: str = "SYS_ERR",
        recoverable: bool = False,
    ) -> None:
        super().__init__(message)
        self.message: str = message
        self.error_code: str = error_code
        self.recoverable: bool = recoverable

    def __str__(self) -> str:
        return f"[{self.error_code}] {self.message} (recoverable={self.recoverable})"


class FatalError(AIContentOSError):
    """Unrecoverable system-level error requiring process exit or immediate alert."""

    def __init__(self, message: str, error_code: str = "FATAL_ERR") -> None:
        super().__init__(message=message, error_code=error_code, recoverable=False)


class RecoverableError(AIContentOSError):
    """Operation failure that can be recovered via alternative paths or fallbacks."""

    def __init__(self, message: str, error_code: str = "RECOVERABLE_ERR") -> None:
        super().__init__(message=message, error_code=error_code, recoverable=True)


class RetryableError(AIContentOSError):
    """Transient operation failure that can be safely retried with exponential backoff."""

    def __init__(self, message: str, error_code: str = "RETRYABLE_ERR") -> None:
        super().__init__(message=message, error_code=error_code, recoverable=True)

"""Retry Manager module for Workflow Engine subsystem.

Executes step dispatches with configurable exponential backoff and retry policies,
distinguishing between transient retryable exceptions and fatal fail-fast errors.
"""

import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

from loguru import logger

from modules.workflow.models import RetryPolicy, WorkflowStep
from modules.workforce.models import TaskResult

T = TypeVar("T")


class RetryManager:
    """Executes async callable operations with configurable exponential backoff retries."""

    async def execute_with_retry(
        self,
        step: WorkflowStep,
        func: Callable[[], Awaitable[TaskResult]],
    ) -> TaskResult:
        """Executes an async task dispatch function with retries according to step.retry_policy.

        Args:
            step: Target WorkflowStep model.
            func: Async callable producing a TaskResult.

        Returns:
            TaskResult: Result of successful execution or last failed attempt.
        """
        policy = step.retry_policy
        attempts = 0

        while True:
            attempts += 1
            try:
                result = await func()
                # If TaskResult reports success, return immediately
                if result.status.value == "COMPLETED":
                    return result

                # Handle TaskResult reported failure as potential retryable error
                error_msg = result.error or "Task reported status FAILED"
                if not self._should_retry_msg(error_msg, attempts, policy):
                    logger.warning(
                        f"RetryManager: step '{step.step_id}' failed on attempt {attempts}/{policy.max_retries + 1}. "
                        f"No more retries. Error: {error_msg}"
                    )
                    return result

            except Exception as exc:
                exc_type_name = type(exc).__name__
                if not self._should_retry_exc(exc_type_name, attempts, policy):
                    logger.error(
                        f"RetryManager: step '{step.step_id}' fatal exception '{exc_type_name}' "
                        f"on attempt {attempts}/{policy.max_retries + 1}: {exc}"
                    )
                    raise exc

            # Calculate backoff delay
            delay = self.calculate_delay(attempts, policy)
            logger.info(
                f"RetryManager: step '{step.step_id}' attempt {attempts}/{policy.max_retries + 1} "
                f"failed. Retrying in {delay:.2f}s..."
            )
            await asyncio.sleep(delay)

    @staticmethod
    def _should_retry_exc(exc_name: str, attempt_count: int, policy: RetryPolicy) -> bool:
        """Checks if an exception is retryable and retry limit is not exceeded.

        Args:
            exc_name: Exception class name.
            attempt_count: Current attempt number.
            policy: RetryPolicy model.

        Returns:
            bool: True if retry should occur.
        """
        if attempt_count > policy.max_retries:
            return False
        return exc_name in policy.retryable_exceptions or len(policy.retryable_exceptions) == 0

    @staticmethod
    def _should_retry_msg(error_msg: str, attempt_count: int, policy: RetryPolicy) -> bool:
        """Checks if a failure message is retryable and retry limit is not exceeded.

        Args:
            error_msg: Error message string.
            attempt_count: Current attempt number.
            policy: RetryPolicy model.

        Returns:
            bool: True if retry should occur.
        """
        return attempt_count <= policy.max_retries

    @staticmethod
    def calculate_delay(attempt_number: int, policy: RetryPolicy) -> float:
        """Calculates exponential backoff delay for a given attempt.

        Args:
            attempt_number: Current attempt index (1-based).
            policy: RetryPolicy model.

        Returns:
            Calculated delay in seconds capped at max_delay_sec.
        """
        delay = policy.initial_delay_sec * (policy.backoff_factor ** (attempt_number - 1))
        return min(policy.max_delay_sec, round(delay, 3))

"""Base worker abstract module for AI Workforce Core subsystem.

Defines the abstract base class contract for all concrete AI workforce workers.
"""

from abc import ABC, abstractmethod

from modules.workforce.context import SharedContext
from modules.workforce.models import (
    Task,
    TaskResult,
    WorkerMetrics,
    WorkerState,
)


class BaseWorker(ABC):
    """Abstract interface contract for specialized AI workforce workers."""

    def __init__(
        self,
        worker_id: str,
        worker_name: str,
        role: str,
        capabilities: list[str],
    ):
        self.worker_id: str = worker_id
        self.worker_name: str = worker_name
        self.role: str = role
        self.capabilities: list[str] = capabilities
        self.state: WorkerState = WorkerState.CREATED
        self.metrics: WorkerMetrics = WorkerMetrics()

    @abstractmethod
    async def initialize(self) -> bool:
        """Initializes worker resources and transitions state to READY.

        Returns:
            bool: True if initialization succeeded, False otherwise.
        """
        pass

    @abstractmethod
    async def execute(self, task: Task, context: SharedContext) -> TaskResult:
        """Executes assigned Task using SharedContext and returns a TaskResult.

        Args:
            task: Task model specification.
            context: SharedContext payload.

        Returns:
            TaskResult: Standardized execution result.
        """
        pass

    @abstractmethod
    async def shutdown(self) -> bool:
        """Gracefully shuts down worker resources and transitions state to STOPPED.

        Returns:
            bool: True if shutdown completed cleanly, False otherwise.
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Audits worker health status.

        Returns:
            bool: True if worker is healthy and ready, False otherwise.
        """
        pass

    def record_execution_metrics(
        self, duration_sec: float, was_successful: bool
    ) -> None:
        """Updates internal WorkerMetrics after a task execution."""
        total_tasks = self.metrics.tasks_completed + self.metrics.tasks_failed + 1
        if was_successful:
            self.metrics.tasks_completed += 1
        else:
            self.metrics.tasks_failed += 1

        self.metrics.success_rate = self.metrics.tasks_completed / total_tasks
        # Moving average for execution time
        prev_avg = self.metrics.average_execution_time
        self.metrics.average_execution_time = (
            (prev_avg * (total_tasks - 1)) + duration_sec
        ) / total_tasks

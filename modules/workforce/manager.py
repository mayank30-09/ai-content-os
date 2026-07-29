"""Workforce manager orchestrator module for AI Workforce Core subsystem.

Coordinates task scheduling, capability-based worker assignment, execution tracking,
retry policies, health monitoring, and graceful shutdowns.
"""

import asyncio
import time

from loguru import logger

from modules.workforce.bus import MessageBus, message_bus
from modules.workforce.context import SharedContext
from modules.workforce.models import (
    Task,
    TaskMessage,
    TaskResult,
    TaskStatus,
    WorkerState,
)
from modules.workforce.registry import WorkerRegistry, worker_registry
from modules.workforce.scheduler import TaskScheduler


class WorkforceManager:
    """Orchestrates task scheduling, worker assignment, and execution lifecycles."""

    def __init__(
        self,
        scheduler: TaskScheduler | None = None,
        registry: WorkerRegistry | None = None,
        bus: MessageBus | None = None,
        context: SharedContext | None = None,
    ):
        self.scheduler: TaskScheduler = scheduler or TaskScheduler()
        self.registry: WorkerRegistry = registry or worker_registry
        self.bus: MessageBus = bus or message_bus
        self.context: SharedContext = context or SharedContext()

    def submit_task(self, task: Task) -> str:
        """Submits a Task to the workforce scheduler.

        Args:
            task: Task specification.

        Returns:
            str: Task ID string.
        """
        logger.info(f"Submitting task '{task.id}' [Type: {task.type}, Priority: {task.priority.name}]")
        self.scheduler.enqueue(task)

        # Emit TaskCreated Event
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(
                self._safe_emit_event(
                    "TaskCreated", "WorkforceManager", {"task_id": task.id, "type": task.type}
                )
            )
        except RuntimeError:
            pass
        return task.id

    async def _safe_emit_event(
        self, event_type: str, source: str, data: dict
    ) -> None:
        """Safely emits workforce events over MessageBus."""
        try:
            await self.bus.emit_event(event_type, source, data)
        except Exception as e:
            logger.error(f"Failed to emit event '{event_type}': {e}")

    async def dispatch_next(self) -> TaskResult | None:
        """Pops the next highest-priority task from scheduler and executes it on an eligible worker.

        Returns:
            Optional[TaskResult]: Result of worker execution, or None if queue empty or no worker available.
        """
        task = self.scheduler.pop_next()
        if not task:
            logger.debug("No pending tasks in scheduler queue.")
            return None

        # Find eligible workers matching required capability (task.type)
        eligible_workers = self.registry.find_by_capability(task.type)
        if not eligible_workers:
            logger.warning(f"No active worker found for capability '{task.type}' on task '{task.id}'")
            # Schedule retry or mark FAILED
            if not self.scheduler.schedule_retry(task):
                await self._safe_emit_event("TaskFailed", "WorkforceManager", {"task_id": task.id, "error": "No matching worker"})
            return None

        # Assign to first ready worker
        assigned_worker = eligible_workers[0]
        task.assigned_worker = assigned_worker.worker_id
        task.status = TaskStatus.ASSIGNED

        await self._safe_emit_event(
            "TaskAssigned", "WorkforceManager", {"task_id": task.id, "worker_id": assigned_worker.worker_id}
        )

        # Deliver message to worker inbox
        msg = TaskMessage(
            sender="WorkforceManager",
            recipient=assigned_worker.worker_id,
            task_id=task.id,
            payload=task.payload
        )
        await self.bus.publish_message(msg)

        # Execute worker
        logger.info(f"Executing task '{task.id}' on worker '{assigned_worker.worker_id}' ({assigned_worker.role})")
        task.status = TaskStatus.IN_PROGRESS
        assigned_worker.state = WorkerState.RUNNING

        await self._safe_emit_event("TaskStarted", "WorkforceManager", {"task_id": task.id})

        start_time = time.perf_counter()
        try:
            result = await assigned_worker.execute(task, self.context.clone())
            duration = round(time.perf_counter() - start_time, 3)
            result.execution_time = duration

            was_success = result.status == TaskStatus.COMPLETED
            assigned_worker.record_execution_metrics(duration, was_success)

            if was_success:
                task.status = TaskStatus.COMPLETED
                assigned_worker.state = WorkerState.READY
                await self._safe_emit_event(
                    "TaskCompleted", assigned_worker.worker_id, {"task_id": task.id, "duration": duration}
                )
                return result
            else:
                raise RuntimeError(result.error or "Worker execution failed")

        except Exception as e:
            duration = round(time.perf_counter() - start_time, 3)
            assigned_worker.record_execution_metrics(duration, was_successful=False)
            assigned_worker.state = WorkerState.READY
            logger.error(f"Task execution failed on worker '{assigned_worker.worker_id}': {e}")

            err_result = TaskResult(
                task_id=task.id,
                worker_id=assigned_worker.worker_id,
                status=TaskStatus.FAILED,
                execution_time=duration,
                error=str(e)
            )

            # Schedule retry or fail permanently
            if not self.scheduler.schedule_retry(task):
                await self._safe_emit_event(
                    "TaskFailed", assigned_worker.worker_id, {"task_id": task.id, "error": str(e)}
                )

            return err_result

    async def monitor_health(self) -> dict[str, bool]:
        """Audits health status across all registered workers."""
        return await self.registry.run_health_checks()

    async def shutdown_all(self) -> list[str]:
        """Gracefully shuts down all active workers."""
        stopped = []
        for worker_id in self.registry.discover():
            worker = self.registry.get_worker(worker_id)
            if worker:
                await worker.shutdown()
                stopped.append(worker_id)
                await self._safe_emit_event("WorkerStopped", "WorkforceManager", {"worker_id": worker_id})
        logger.info(f"WorkforceManager shut down {len(stopped)} workers.")
        return stopped

workforce_manager = WorkforceManager()

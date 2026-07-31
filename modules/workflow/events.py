"""Workflow Events module for Workflow Engine subsystem.

Defines workflow lifecycle events emitted over MessageBus during workflow execution.
"""

from typing import Any

from loguru import logger

from modules.workforce.bus import MessageBus, message_bus


class WorkflowEventDispatcher:
    """Helper class for emitting workflow lifecycle events over MessageBus."""

    def __init__(self, bus: MessageBus | None = None) -> None:
        """Initializes WorkflowEventDispatcher with injected MessageBus.

        Args:
            bus: MessageBus instance.
        """
        self.bus: MessageBus = bus or message_bus

    async def emit_workflow_started(self, workflow_id: str, topic: str, template: str) -> None:
        """Emits WorkflowStarted event."""
        await self._safe_emit("WorkflowStarted", workflow_id, {"topic": topic, "template": template})

    async def emit_step_started(self, workflow_id: str, step_id: str, worker_type: str) -> None:
        """Emits StepStarted event."""
        await self._safe_emit("StepStarted", workflow_id, {"step_id": step_id, "worker_type": worker_type})

    async def emit_step_completed(self, workflow_id: str, step_id: str, duration_sec: float) -> None:
        """Emits StepCompleted event."""
        await self._safe_emit("StepCompleted", workflow_id, {"step_id": step_id, "duration_sec": duration_sec})

    async def emit_step_failed(self, workflow_id: str, step_id: str, error: str, retry_count: int) -> None:
        """Emits StepFailed event."""
        await self._safe_emit(
            "StepFailed", workflow_id, {"step_id": step_id, "error": error, "retry_count": retry_count}
        )

    async def emit_checkpoint_created(self, workflow_id: str, checkpoint_id: str, step_index: int) -> None:
        """Emits CheckpointCreated event."""
        await self._safe_emit(
            "CheckpointCreated", workflow_id, {"checkpoint_id": checkpoint_id, "step_index": step_index}
        )

    async def emit_workflow_paused(self, workflow_id: str, step_index: int) -> None:
        """Emits WorkflowPaused event."""
        await self._safe_emit("WorkflowPaused", workflow_id, {"step_index": step_index})

    async def emit_workflow_resumed(self, workflow_id: str, step_index: int) -> None:
        """Emits WorkflowResumed event."""
        await self._safe_emit("WorkflowResumed", workflow_id, {"step_index": step_index})

    async def emit_workflow_completed(self, workflow_id: str, final_url: str | None, total_time_sec: float) -> None:
        """Emits WorkflowCompleted event."""
        await self._safe_emit(
            "WorkflowCompleted", workflow_id, {"final_url": final_url, "total_time_sec": total_time_sec}
        )

    async def emit_workflow_failed(self, workflow_id: str, failed_step_id: str, error: str) -> None:
        """Emits WorkflowFailed event."""
        await self._safe_emit(
            "WorkflowFailed", workflow_id, {"failed_step_id": failed_step_id, "error": error}
        )

    async def _safe_emit(self, event_type: str, source_id: str, data: dict[str, Any]) -> None:
        """Safely dispatches event over MessageBus."""
        try:
            await self.bus.emit_event(event_type, f"workflow_{source_id}", data)
        except Exception as e:
            logger.error(f"WorkflowEventDispatcher failed to emit event '{event_type}': {e}")

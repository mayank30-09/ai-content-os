"""Checkpoint Manager module for Workflow Engine subsystem.

Manages persistent disk auto-saving of workflow execution state and artifact snapshots
for fault tolerance, crash recovery, and resume capability.
"""

import json
from pathlib import Path

from loguru import logger

from modules.workflow.artifact_registry import ArtifactRegistry
from modules.workflow.context import WorkflowContext
from modules.workflow.models import (
    CheckpointMetadata,
    WorkflowCheckpoint,
    WorkflowExecution,
    WorkflowRequest,
)


class CheckpointManager:
    """Manages persistent JSON checkpoint snapshots on disk.

    Enables saving state after every step and resuming interrupted or crashed
    workflows from the last valid step snapshot.
    """

    DEFAULT_STORAGE_DIR: Path = Path(".checkpoints")

    def __init__(self, storage_dir: Path | str | None = None) -> None:
        """Initializes CheckpointManager with storage directory.

        Args:
            storage_dir: Storage directory path. Defaults to .checkpoints.
        """
        self.storage_dir: Path = Path(storage_dir) if storage_dir else self.DEFAULT_STORAGE_DIR
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def save_checkpoint(
        self,
        execution: WorkflowExecution,
        context: WorkflowContext,
    ) -> WorkflowCheckpoint:
        """Saves a checkpoint snapshot of current workflow execution state and artifacts.

        Args:
            execution: Current WorkflowExecution state model.
            context: Current WorkflowContext instance.

        Returns:
            Saved WorkflowCheckpoint model.
        """
        step_index = execution.current_step_index
        step_id = (
            execution.steps[step_index].step_id
            if step_index < len(execution.steps)
            else "completion"
        )
        checkpoint_id = f"chk_{execution.workflow_id}_step_{step_index}"

        metadata = CheckpointMetadata(
            checkpoint_id=checkpoint_id,
            workflow_id=execution.workflow_id,
            step_index=step_index,
            step_id=step_id,
        )

        context_artifacts = context.artifacts.to_dict()

        checkpoint = WorkflowCheckpoint(
            metadata=metadata,
            execution_state=execution,
            context_artifacts=context_artifacts,
            request=context.request,
        )

        file_path = self.storage_dir / f"{execution.workflow_id}_latest.json"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(checkpoint.model_dump_json(indent=2))

        logger.info(
            f"CheckpointManager: saved checkpoint '{checkpoint_id}' "
            f"to {file_path}"
        )
        return checkpoint

    def load_checkpoint(
        self,
        workflow_id: str,
    ) -> tuple[WorkflowExecution, WorkflowContext]:
        """Loads the latest checkpoint snapshot for a workflow ID.

        Args:
            workflow_id: Workflow execution ID.

        Returns:
            Tuple of:
            - WorkflowExecution state.
            - WorkflowContext re-hydrated with ArtifactRegistry and original request.

        Raises:
            FileNotFoundError: If no checkpoint file exists for workflow_id.
        """
        file_path = self.storage_dir / f"{workflow_id}_latest.json"
        if not file_path.exists():
            raise FileNotFoundError(f"Checkpoint file not found for workflow '{workflow_id}': {file_path}")

        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)

        checkpoint = WorkflowCheckpoint.model_validate(data)
        execution = checkpoint.execution_state

        # Re-hydrate WorkflowContext & ArtifactRegistry
        registry = ArtifactRegistry.from_dict(checkpoint.context_artifacts)

        # Restore original WorkflowRequest or fallback to topic from artifacts
        request = checkpoint.request or WorkflowRequest(
            topic=checkpoint.context_artifacts.get("topic", "Resumed Workflow"),
            template_name=execution.template_name,
        )
        context = WorkflowContext(
            request=request,
            workflow_id=execution.workflow_id,
            initial_registry=registry,
        )

        logger.info(
            f"CheckpointManager: loaded checkpoint for workflow '{workflow_id}' "
            f"at step index {execution.current_step_index}."
        )
        return execution, context

    def has_checkpoint(self, workflow_id: str) -> bool:
        """Checks if a checkpoint file exists for workflow_id.

        Args:
            workflow_id: Workflow execution ID.

        Returns:
            bool: True if checkpoint exists.
        """
        file_path = self.storage_dir / f"{workflow_id}_latest.json"
        return file_path.exists()

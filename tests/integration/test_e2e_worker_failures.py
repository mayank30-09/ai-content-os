"""Per-worker Failure Recovery Integration Tests for AI Content OS.

Tests per-worker step failures across all 8 pipeline positions:
- Research Worker failure
- Memory Worker failure
- Content Strategist failure
- Writer Worker failure
- Fact Checker failure
- Editor Worker failure
- SEO Worker failure
- Publisher Worker failure

Verifies clean step state transition to FAILED, overall workflow status FAILED,
emergency failure checkpoint saving, and correct error message reporting.
"""

from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from modules.workflow.checkpoint import CheckpointManager
from modules.workflow.engine import WorkflowEngine
from modules.workflow.models import (
    ExecutionState,
    WorkflowRequest,
    WorkflowStatus,
)
from modules.workforce.bus import MessageBus
from modules.workforce.context import SharedContext
from modules.workforce.manager import WorkforceManager
from modules.workforce.models import Task, TaskResult, TaskStatus


@pytest.fixture
def tmp_checkpoint_dir(tmp_path: Path) -> Path:
    chk_dir = tmp_path / "failure_checkpoints"
    chk_dir.mkdir(parents=True, exist_ok=True)
    return chk_dir


@pytest.fixture
def failure_request() -> WorkflowRequest:
    return WorkflowRequest(
        topic="Failure Recovery Pipeline Test",
        keywords=["Test", "Failure"],
        template_name="standard_content_pipeline",
    )


class TestE2EWorkerFailures:
    """Integration test suite for per-worker failure handling across the pipeline."""

    @pytest.mark.parametrize(
        ("failing_worker_type", "failing_step_index"),
        [
            ("research_worker", 0),
            ("memory_worker", 1),
            ("strategist_worker", 2),
            ("writer_worker", 3),
            ("fact_checker_worker", 4),
            ("editor_worker", 5),
            ("seo_worker", 6),
            ("publisher_worker", 7),
        ],
    )
    @pytest.mark.asyncio
    async def test_per_worker_failure_handling(
        self,
        failing_worker_type: str,
        failing_step_index: int,
        failure_request: WorkflowRequest,
        tmp_checkpoint_dir: Path,
    ):
        workforce_mgr = WorkforceManager(bus=MessageBus())

        async def mock_execute(task: Task, context: SharedContext) -> TaskResult:
            if task.type == failing_worker_type:
                return TaskResult(
                    task_id=task.id,
                    worker_id=f"worker_{task.type}",
                    status=TaskStatus.FAILED,
                    error=f"Simulated failure at worker '{failing_worker_type}'",
                )
            return TaskResult(
                task_id=task.id,
                worker_id=f"worker_{task.type}",
                status=TaskStatus.COMPLETED,
                artifacts={f"{task.type}_output": "data"},
            )

        workforce_mgr.assign_and_execute = AsyncMock(side_effect=mock_execute)
        chk_mgr = CheckpointManager(storage_dir=tmp_checkpoint_dir)
        engine = WorkflowEngine(
            checkpoint_mgr=chk_mgr,
            workforce_mgr=workforce_mgr,
            bus=MessageBus(),
        )

        result = await engine.execute_workflow(failure_request)

        # Assertions
        assert result.status == WorkflowStatus.FAILED
        assert result.steps_completed == failing_step_index
        assert f"Simulated failure at worker '{failing_worker_type}'" in result.error
        assert result.publication_package is None

        # Verify emergency checkpoint was saved
        assert chk_mgr.has_checkpoint(result.workflow_id) is True
        loaded_exec, _ = chk_mgr.load_checkpoint(result.workflow_id)
        assert loaded_exec.status == WorkflowStatus.FAILED
        assert loaded_exec.steps[failing_step_index].state == ExecutionState.FAILED

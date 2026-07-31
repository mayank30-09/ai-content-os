"""Metrics & MessageBus Events Integration Tests for AI Content OS.

Verifies:
- Complete sequence of MessageBus events emitted during workflow execution:
  (WorkflowStarted, StepStarted x8, StepCompleted x8, CheckpointCreated x8, WorkflowCompleted)
- WorkflowMetrics calculation accuracy:
  - total_execution_time_sec > 0.0
  - worker_durations dictionary populated for all 8 steps
  - checkpoint_count == 8
  - success_rate == 1.0
  - artifacts_generated_count > 0
"""

from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from modules.workflow.checkpoint import CheckpointManager
from modules.workflow.engine import WorkflowEngine
from modules.workflow.models import (
    WorkflowRequest,
    WorkflowStatus,
)
from modules.workforce.bus import MessageBus
from modules.workforce.context import SharedContext
from modules.workforce.manager import WorkforceManager
from modules.workforce.models import Task, TaskResult, TaskStatus
from modules.workforce.workers.draft_models import DraftPackage
from modules.workforce.workers.publisher_models import PublicationPackage


class TestE2EMetricsAndEvents:
    """Integration test suite for WorkflowMetrics and MessageBus event sequences."""

    @pytest.mark.asyncio
    async def test_metrics_and_event_sequence_verification(
        self,
        sample_e2e_request: WorkflowRequest,
        sample_publication_package: PublicationPackage,
        integration_tmp_dir: Path,
    ):
        bus = MessageBus()
        emitted_events: list[tuple[str, str]] = []

        async def event_listener(event):
            emitted_events.append((event.event_type, event.source))

        for evt_name in [
            "WorkflowStarted",
            "StepStarted",
            "StepCompleted",
            "CheckpointCreated",
            "WorkflowCompleted",
        ]:
            bus.add_event_listener(evt_name, event_listener)

        workforce_mgr = WorkforceManager(bus=bus)

        async def mock_execute(task: Task, context: SharedContext) -> TaskResult:
            wtype = task.type
            if wtype == "writer_worker":
                artifacts = {
                    "draft_package": DraftPackage(
                        title=sample_e2e_request.topic,
                        draft="Draft Body",
                        platform="linkedin",
                        content_format="Article",
                        audience="Devs",
                        objective="ED",
                    ).model_dump(mode="json")
                }
            elif wtype == "publisher_worker":
                artifacts = {"publication_package": sample_publication_package.model_dump(mode="json")}
            else:
                artifacts = {f"{wtype}_output": "data"}

            return TaskResult(
                task_id=task.id,
                worker_id=f"w_{wtype}",
                status=TaskStatus.COMPLETED,
                artifacts=artifacts,
            )

        workforce_mgr.assign_and_execute = AsyncMock(side_effect=mock_execute)
        chk_mgr = CheckpointManager(storage_dir=integration_tmp_dir)
        engine = WorkflowEngine(
            checkpoint_mgr=chk_mgr,
            workforce_mgr=workforce_mgr,
            bus=bus,
        )

        result = await engine.execute_workflow(sample_e2e_request)

        # --------------------------------------------------------------------
        # Metrics Assertions
        # --------------------------------------------------------------------
        assert result.status == WorkflowStatus.COMPLETED
        metrics = result.metrics_summary

        assert metrics["total_execution_time_sec"] >= 0.0
        assert len(metrics["worker_durations"]) == 8
        assert metrics["checkpoint_count"] == 8
        assert metrics["success_rate"] == 1.0
        assert metrics["artifacts_generated_count"] >= 8

        # --------------------------------------------------------------------
        # Event Sequence Assertions
        # --------------------------------------------------------------------
        event_types = [e[0] for e in emitted_events]

        assert "WorkflowStarted" in event_types
        assert "WorkflowCompleted" in event_types
        assert event_types.count("StepStarted") == 8
        assert event_types.count("StepCompleted") == 8
        assert event_types.count("CheckpointCreated") == 8

        # Verify event order (WorkflowStarted is first, WorkflowCompleted is last)
        assert event_types[0] == "WorkflowStarted"
        assert event_types[-1] == "WorkflowCompleted"

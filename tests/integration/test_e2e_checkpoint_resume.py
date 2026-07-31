"""Checkpoint Crash Recovery & Resumption Integration Tests for AI Content OS.

Verifies:
- Saving atomic JSON step checkpoints after every worker completion
- Simulating a process crash midway through pipeline execution (e.g. step 4)
- Re-hydrating WorkflowContext, ArtifactRegistry, and original WorkflowRequest from disk
- Resuming pipeline execution from step N+1 to full completion
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


class TestE2ECheckpointResume:
    """Integration test suite for checkpoint crash recovery and resume behavior."""

    @pytest.mark.asyncio
    async def test_simulated_crash_and_resume_to_completion(
        self,
        sample_e2e_request: WorkflowRequest,
        sample_publication_package: PublicationPackage,
        integration_tmp_dir: Path,
    ):
        step_call_counts: dict[str, int] = {}

        # --------------------------------------------------------------------
        # Run 1: Crash at Step 4 (writer_worker)
        # --------------------------------------------------------------------
        workforce_run_1 = WorkforceManager(bus=MessageBus())

        async def execute_run_1(task: Task, context: SharedContext) -> TaskResult:
            wtype = task.type
            step_call_counts[wtype] = step_call_counts.get(wtype, 0) + 1

            if wtype == "writer_worker":
                return TaskResult(
                    task_id=task.id,
                    worker_id=f"worker_{wtype}",
                    status=TaskStatus.FAILED,
                    error="Simulated process crash at writer_worker",
                )
            return TaskResult(
                task_id=task.id,
                worker_id=f"worker_{wtype}",
                status=TaskStatus.COMPLETED,
                artifacts={f"{wtype}_output": "data"},
            )

        workforce_run_1.assign_and_execute = AsyncMock(side_effect=execute_run_1)
        chk_mgr = CheckpointManager(storage_dir=integration_tmp_dir)
        engine_1 = WorkflowEngine(
            checkpoint_mgr=chk_mgr,
            workforce_mgr=workforce_run_1,
            bus=MessageBus(),
        )

        run_1_result = await engine_1.execute_workflow(sample_e2e_request)
        wf_id = run_1_result.workflow_id

        assert run_1_result.status == WorkflowStatus.FAILED
        assert run_1_result.steps_completed == 3  # Research, Memory, Strategist completed
        assert step_call_counts["research_worker"] == 1
        assert step_call_counts["memory_worker"] == 1
        assert step_call_counts["strategist_worker"] == 1
        assert step_call_counts["writer_worker"] == 4  # 1 initial + 3 retry attempts

        # --------------------------------------------------------------------
        # Run 2: Resume workflow from checkpoint (Fix writer_worker)
        # --------------------------------------------------------------------
        workforce_run_2 = WorkforceManager(bus=MessageBus())

        async def execute_run_2(task: Task, context: SharedContext) -> TaskResult:
            wtype = task.type
            step_call_counts[wtype] = step_call_counts.get(wtype, 0) + 1

            if wtype == "writer_worker":
                return TaskResult(
                    task_id=task.id,
                    worker_id=f"worker_{wtype}",
                    status=TaskStatus.COMPLETED,
                    artifacts={
                        "draft_package": DraftPackage(
                            title=sample_e2e_request.topic,
                            draft="Resumed Draft Content",
                            platform="linkedin",
                            content_format="Article",
                            audience="Devs",
                            objective="ED",
                        ).model_dump(mode="json")
                    },
                )
            if wtype == "publisher_worker":
                return TaskResult(
                    task_id=task.id,
                    worker_id=f"worker_{wtype}",
                    status=TaskStatus.COMPLETED,
                    artifacts={"publication_package": sample_publication_package.model_dump(mode="json")},
                )
            return TaskResult(
                task_id=task.id,
                worker_id=f"worker_{wtype}",
                status=TaskStatus.COMPLETED,
                artifacts={f"{wtype}_output": "data"},
            )

        workforce_run_2.assign_and_execute = AsyncMock(side_effect=execute_run_2)
        engine_2 = WorkflowEngine(
            checkpoint_mgr=chk_mgr,
            workforce_mgr=workforce_run_2,
            bus=MessageBus(),
        )

        resumed_result = await engine_2.resume_workflow(wf_id)

        assert resumed_result.workflow_id == wf_id
        assert resumed_result.status == WorkflowStatus.COMPLETED
        assert resumed_result.publication_package is not None
        assert resumed_result.publication_package.final_url == "https://linkedin.com/post/e2e-123456"

        # Verify steps 1-3 were NOT re-executed during resume
        assert step_call_counts["research_worker"] == 1
        assert step_call_counts["memory_worker"] == 1
        assert step_call_counts["strategist_worker"] == 1
        assert step_call_counts["writer_worker"] == 5  # 4 failed attempts in run 1 + 1 successful in run 2
        assert step_call_counts["publisher_worker"] == 1  # Completed step 8

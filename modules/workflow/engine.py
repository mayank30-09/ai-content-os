"""Workflow Engine core module for AI Content OS.

Top-level orchestration engine that accepts user WorkflowRequests, builds execution
plans via ExecutionPlanner, dispatches worker tasks through WorkforceManager,
manages artifact flow via ArtifactRegistry, auto-saves checkpoints, handles retries,
and emits workflow events over MessageBus.
"""

import time
import uuid
from datetime import UTC, datetime
from typing import Any

from loguru import logger

from modules.workflow.checkpoint import CheckpointManager
from modules.workflow.context import WorkflowContext
from modules.workflow.events import WorkflowEventDispatcher
from modules.workflow.metrics import WorkflowMetrics
from modules.workflow.models import (
    ExecutionState,
    WorkflowExecution,
    WorkflowRequest,
    WorkflowResult,
    WorkflowStatus,
    WorkflowStep,
)
from modules.workflow.planner import ExecutionPlanner
from modules.workflow.retry import RetryManager
from modules.workforce.bus import MessageBus, message_bus
from modules.workforce.manager import WorkforceManager, workforce_manager
from modules.workforce.workers.editor_models import EditQualityScores
from modules.workforce.workers.publisher_models import PublicationPackage
from modules.workforce.workers.seo_models import SEOScores
from modules.workforce.workers.verification_models import VerificationReport


class WorkflowEngine:
    """Core Orchestrator for the autonomous AI Content OS workflow pipeline.

    Orchestrates the 8 production AI workers in dependency order via WorkforceManager.
    Never executes worker logic directly and never bypasses WorkforceManager.
    """

    WORKFLOW_ENGINE_VERSION: str = "v0.7.0"

    def __init__(
        self,
        planner: ExecutionPlanner | None = None,
        checkpoint_mgr: CheckpointManager | None = None,
        retry_mgr: RetryManager | None = None,
        workforce_mgr: WorkforceManager | None = None,
        bus: MessageBus | None = None,
    ) -> None:
        """Initializes WorkflowEngine with injected dependencies.

        Args:
            planner: ExecutionPlanner instance.
            checkpoint_mgr: CheckpointManager instance.
            retry_mgr: RetryManager instance.
            workforce_mgr: WorkforceManager instance.
            bus: MessageBus instance.
        """
        self.planner: ExecutionPlanner = planner or ExecutionPlanner()
        self.checkpoint_mgr: CheckpointManager = checkpoint_mgr or CheckpointManager()
        self.retry_mgr: RetryManager = retry_mgr or RetryManager()
        self.workforce_mgr: WorkforceManager = workforce_mgr or workforce_manager
        self.events: WorkflowEventDispatcher = WorkflowEventDispatcher(bus=bus or message_bus)

    async def execute_workflow(self, request: WorkflowRequest) -> WorkflowResult:
        """Executes an end-to-end workflow request.

        Pipeline:
            1. Generate unique workflow ID.
            2. Build execution plan via ExecutionPlanner (DAG validation).
            3. Instantiate WorkflowContext with request parameters.
            4. Save initial checkpoint.
            5. Emit WorkflowStarted event.
            6. Execute steps sequentially via RetryManager and WorkforceManager.
            7. Save checkpoint after each step.
            8. Extract final PublicationPackage and lineage.
            9. Emit WorkflowCompleted event.
            10. Return WorkflowResult.

        Args:
            request: User WorkflowRequest instance.

        Returns:
            WorkflowResult model containing final artifacts and execution metrics.
        """
        workflow_id = f"wf_{uuid.uuid4().hex[:12]}"
        start_time = time.perf_counter()
        logger.info(f"WorkflowEngine: initiating workflow '{workflow_id}' for topic: '{request.topic}'")

        try:
            # 1. Build plan
            execution = self.planner.build_plan(request, workflow_id)
            context = WorkflowContext(request=request, workflow_id=workflow_id)

            # Store topic in context for checkpoint re-hydration
            context.store_artifact("topic", request.topic)

            execution.status = WorkflowStatus.RUNNING
            self.checkpoint_mgr.save_checkpoint(execution, context)
            await self.events.emit_workflow_started(workflow_id, request.topic, execution.template_name)

            # 2. Execute pipeline steps
            result = await self._run_pipeline(execution, context, start_time)
            return result

        except Exception as e:
            duration = round(time.perf_counter() - start_time, 3)
            logger.error(f"WorkflowEngine: execution exception for workflow '{workflow_id}': {e}")
            await self.events.emit_workflow_failed(workflow_id, "initialization", str(e))

            metrics = WorkflowMetrics(
                total_execution_time_sec=duration,
                success_rate=0.0,
            )
            return WorkflowResult(
                workflow_id=workflow_id,
                status=WorkflowStatus.FAILED,
                execution_time_sec=duration,
                steps_completed=0,
                metrics_summary=metrics.model_dump(mode="json"),
                error=str(e),
            )

    async def resume_workflow(self, workflow_id: str) -> WorkflowResult:
        """Resumes a paused or crashed workflow execution from its latest checkpoint.

        Args:
            workflow_id: Target workflow execution ID.

        Returns:
            WorkflowResult model.
        """
        start_time = time.perf_counter()
        logger.info(f"WorkflowEngine: resuming workflow '{workflow_id}' from checkpoint...")

        try:
            execution, context = self.checkpoint_mgr.load_checkpoint(workflow_id)
            execution.status = WorkflowStatus.RUNNING
            await self.events.emit_workflow_resumed(workflow_id, execution.current_step_index)

            result = await self._run_pipeline(execution, context, start_time)
            return result

        except Exception as e:
            duration = round(time.perf_counter() - start_time, 3)
            logger.error(f"WorkflowEngine: failed to resume workflow '{workflow_id}': {e}")
            await self.events.emit_workflow_failed(workflow_id, "resume", str(e))

            return WorkflowResult(
                workflow_id=workflow_id,
                status=WorkflowStatus.FAILED,
                execution_time_sec=duration,
                steps_completed=0,
                error=f"Resume failed: {e}",
            )

    async def _run_pipeline(
        self,
        execution: WorkflowExecution,
        context: WorkflowContext,
        start_time: float,
    ) -> WorkflowResult:
        """Runs the active steps loop from current_step_index to completion.

        Args:
            execution: WorkflowExecution state model.
            context: WorkflowContext instance.
            start_time: Performance counter start time.

        Returns:
            WorkflowResult model.
        """
        worker_durations: dict[str, float] = {}
        total_retries = 0
        checkpoint_count = 0

        total_steps = len(execution.steps)
        while execution.current_step_index < total_steps:
            idx = execution.current_step_index
            step = execution.steps[idx]
            step.state = ExecutionState.IN_PROGRESS

            await self.events.emit_step_started(execution.workflow_id, step.step_id, step.worker_type)
            step_start = time.perf_counter()

            # Execute step with retry
            async def dispatch_step(step_target: WorkflowStep = step) -> Any:
                task = context.build_worker_task(step_target)
                return await self.workforce_mgr.assign_and_execute(task, context)

            try:
                task_result = await self.retry_mgr.execute_with_retry(step, dispatch_step)
            except Exception as step_exc:
                return await self._handle_step_failure(
                    execution, context, step, str(step_exc), step.retry_policy.max_retries,
                    start_time, worker_durations, total_retries, checkpoint_count, idx, total_steps
                )

            # Check TaskResult status
            if task_result.status.value != "COMPLETED":
                error_msg = task_result.error or f"TaskResult status was {task_result.status.value}"
                return await self._handle_step_failure(
                    execution, context, step, error_msg, 0,
                    start_time, worker_durations, total_retries, checkpoint_count, idx, total_steps
                )

            # Successful step completion
            step_duration = round(time.perf_counter() - step_start, 3)
            step.execution_time_sec = step_duration
            step.state = ExecutionState.COMPLETED
            worker_durations[step.step_id] = step_duration

            # Store generated artifact into ArtifactRegistry
            if task_result.artifacts:
                for art_key, art_val in task_result.artifacts.items():
                    context.store_artifact(art_key, art_val)
                    # Also map to step output key if specified
                    if step.output_artifact_key and art_key != step.output_artifact_key:
                        context.store_artifact(step.output_artifact_key, art_val)

            await self.events.emit_step_completed(execution.workflow_id, step.step_id, step_duration)

            # Advance current step index & save checkpoint
            execution.current_step_index += 1
            self.checkpoint_mgr.save_checkpoint(execution, context)
            checkpoint_count += 1
            await self.events.emit_checkpoint_created(
                execution.workflow_id, f"chk_{execution.workflow_id}_step_{execution.current_step_index}", execution.current_step_index
            )

        # --------------------------------------------------------------------
        # Workflow Completed Successfully
        # --------------------------------------------------------------------
        execution.status = WorkflowStatus.COMPLETED
        execution.end_time = datetime.now(UTC).isoformat()
        total_duration = round(time.perf_counter() - start_time, 3)

        # Extract final PublicationPackage & Lineage
        pub_pkg: PublicationPackage | None = None
        raw_pub = context.get_artifact("publication_package")
        if raw_pub:
            if isinstance(raw_pub, PublicationPackage):
                pub_pkg = raw_pub
            elif isinstance(raw_pub, dict):
                pub_pkg = PublicationPackage.model_validate(raw_pub)

        # Extract lineage objects if present
        ver_report: VerificationReport | None = None
        raw_ver = context.get_artifact("verification_report")
        if raw_ver:
            ver_report = raw_ver if isinstance(raw_ver, VerificationReport) else VerificationReport.model_validate(raw_ver)
        elif pub_pkg and pub_pkg.verification_report:
            ver_report = pub_pkg.verification_report

        qual_scores: EditQualityScores | None = None
        raw_qual = context.get_artifact("quality_scores")
        if raw_qual:
            qual_scores = raw_qual if isinstance(raw_qual, EditQualityScores) else EditQualityScores.model_validate(raw_qual)
        elif pub_pkg and pub_pkg.quality_scores:
            qual_scores = pub_pkg.quality_scores

        seo_scores: SEOScores | None = None
        raw_seo = context.get_artifact("seo_scores")
        if raw_seo:
            seo_scores = raw_seo if isinstance(raw_seo, SEOScores) else SEOScores.model_validate(raw_seo)
        elif pub_pkg and pub_pkg.seo_scores:
            seo_scores = pub_pkg.seo_scores

        metrics = WorkflowMetrics(
            total_execution_time_sec=total_duration,
            worker_durations=worker_durations,
            total_retries=total_retries,
            checkpoint_count=checkpoint_count,
            success_rate=1.0,
            artifacts_generated_count=len(context.artifacts),
        )

        final_url = pub_pkg.final_url if pub_pkg else None
        await self.events.emit_workflow_completed(execution.workflow_id, final_url, total_duration)

        logger.info(
            f"WorkflowEngine: workflow '{execution.workflow_id}' COMPLETED successfully. "
            f"Steps={total_steps}, Duration={total_duration:.2f}s."
        )

        return WorkflowResult(
            workflow_id=execution.workflow_id,
            status=WorkflowStatus.COMPLETED,
            publication_package=pub_pkg,
            execution_time_sec=total_duration,
            steps_completed=total_steps,
            metrics_summary=metrics.model_dump(mode="json"),
            verification_report=ver_report,
            quality_scores=qual_scores,
            seo_scores=seo_scores,
        )

    async def _handle_step_failure(
        self,
        execution: WorkflowExecution,
        context: WorkflowContext,
        step: WorkflowStep,
        error_msg: str,
        retry_count: int,
        start_time: float,
        worker_durations: dict[str, float],
        total_retries: int,
        checkpoint_count: int,
        idx: int,
        total_steps: int,
    ) -> WorkflowResult:
        """Helper method to format failure state, save checkpoint, and emit events.

        Args:
            execution: Active WorkflowExecution model.
            context: Active WorkflowContext.
            step: Failed WorkflowStep.
            error_msg: Failure error message.
            retry_count: Count of retries performed.
            start_time: Performance counter start time.
            worker_durations: Durations dictionary.
            total_retries: Total retry count.
            checkpoint_count: Count of saved checkpoints.
            idx: Step index.
            total_steps: Total step count.

        Returns:
            WorkflowResult model representing workflow failure.
        """
        step.state = ExecutionState.FAILED
        step.error = error_msg
        execution.status = WorkflowStatus.FAILED
        execution.end_time = datetime.now(UTC).isoformat()
        self.checkpoint_mgr.save_checkpoint(execution, context)

        await self.events.emit_step_failed(execution.workflow_id, step.step_id, error_msg, retry_count)
        await self.events.emit_workflow_failed(execution.workflow_id, step.step_id, error_msg)

        duration = round(time.perf_counter() - start_time, 3)
        metrics = WorkflowMetrics(
            total_execution_time_sec=duration,
            worker_durations=worker_durations,
            total_retries=total_retries,
            checkpoint_count=checkpoint_count,
            success_rate=round(idx / total_steps, 2),
            artifacts_generated_count=len(context.artifacts),
        )
        return WorkflowResult(
            workflow_id=execution.workflow_id,
            status=WorkflowStatus.FAILED,
            execution_time_sec=duration,
            steps_completed=idx,
            metrics_summary=metrics.model_dump(mode="json"),
            error=f"Step '{step.step_id}' failed: {error_msg}",
        )

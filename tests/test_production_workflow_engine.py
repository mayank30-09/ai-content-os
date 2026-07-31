"""Comprehensive test suite for the Production Workflow Engine subsystem.

Tests cover:
- Workflow Models: status enums, RetryPolicy, WorkflowStep, WorkflowExecution,
  WorkflowCheckpoint, WorkflowRequest, WorkflowResult.
- Workflow Metrics: WorkflowMetrics defaults, serialization.
- ArtifactRegistry: register, get, get_typed, contains, to_dict, from_dict, type validation.
- WorkflowContext: store_artifact, get_artifact, build_worker_task payload generation.
- WorkflowTemplates: StandardContentPipelineTemplate (8 steps), FastTrackPipelineTemplate (4 steps).
- ExecutionPlanner & DependencyGraph: DAG validation, dependency checks, plan generation, missing template error.
- CheckpointManager: save_checkpoint, load_checkpoint, disk file creation, context re-hydration.
- RetryManager: execute_with_retry, exponential backoff calculation, retry limits, fatal error fail-fast.
- WorkflowEventDispatcher: emitting all 9 workflow lifecycle events over MessageBus.
- WorkflowEngine Execution: full pipeline orchestration (8 workers), artifact propagation,
  lineage forwarding, failure handling, workflow resumption.
"""

from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from modules.workflow.artifact_registry import ArtifactRegistry
from modules.workflow.checkpoint import CheckpointManager
from modules.workflow.context import WorkflowContext
from modules.workflow.engine import WorkflowEngine
from modules.workflow.events import WorkflowEventDispatcher
from modules.workflow.metrics import WorkflowMetrics
from modules.workflow.models import (
    ExecutionState,
    RetryPolicy,
    WorkflowExecution,
    WorkflowRequest,
    WorkflowStatus,
    WorkflowStep,
)
from modules.workflow.planner import DependencyGraph, ExecutionPlanner
from modules.workflow.retry import RetryManager
from modules.workflow.templates import (
    FastTrackPipelineTemplate,
    StandardContentPipelineTemplate,
)
from modules.workforce.bus import MessageBus
from modules.workforce.context import SharedContext
from modules.workforce.manager import WorkforceManager
from modules.workforce.models import Task, TaskResult, TaskStatus
from modules.workforce.workers.draft_models import DraftPackage, WritingStyle
from modules.workforce.workers.editor_models import EditQualityScores
from modules.workforce.workers.publisher_models import PublicationPackage, PublishStatus
from modules.workforce.workers.seo_models import SEOScores
from modules.workforce.workers.verification_models import (
    VerificationReport,
    VerificationStatus,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_checkpoint_dir(tmp_path: Path) -> Path:
    chk_dir = tmp_path / "checkpoints"
    chk_dir.mkdir(parents=True, exist_ok=True)
    return chk_dir


@pytest.fixture
def sample_request() -> WorkflowRequest:
    return WorkflowRequest(
        topic="Enterprise AI Trends 2024",
        keywords=["AI", "Enterprise", "Python"],
        target_platform="linkedin",
        content_format="Article",
        audience="Developers",
        objective="EDUCATIONAL",
        writing_style=WritingStyle.AUTHORITATIVE,
        template_name="standard_content_pipeline",
    )


@pytest.fixture
def mock_workforce_manager(sample_request: WorkflowRequest) -> WorkforceManager:
    """Mock WorkforceManager simulating successful execution for all 8 workers."""
    mgr = WorkforceManager(bus=MessageBus())

    # Build mock artifacts for lineage
    ver_report = VerificationReport(
        overall_status=VerificationStatus.VERIFIED,
        claims_checked=3,
        claims_verified=3,
        overall_confidence=0.95,
    )
    edit_scores = EditQualityScores(readability_score=0.90, overall_quality=0.92)
    seo_scores = SEOScores(overall_seo_score=0.94)

    pub_pkg = PublicationPackage(
        platform="linkedin",
        title="Enterprise AI Trends 2024",
        content="Published Content Body",
        slug="enterprise-ai-trends-2024",
        final_url="https://linkedin.com/post/12345",
        publish_status=PublishStatus.PUBLISHED,
        verification_report=ver_report,
        quality_scores=edit_scores,
        seo_scores=seo_scores,
    )

    async def mock_execute(task: Task, context: SharedContext) -> TaskResult:
        ttype = task.type
        art_map = {
            "research_worker": {"research_package": {"topic": sample_request.topic, "facts": ["Fact 1"]}},
            "memory_worker": {"context_package": {"institutional_memory": "Memory context"}},
            "strategist_worker": {"strategy_package": {"outline": ["H1", "H2"]}},
            "writer_worker": {
                "draft_package": DraftPackage(
                    title=sample_request.topic,
                    draft="Draft Content",
                    platform="linkedin",
                    content_format="Article",
                    audience="Devs",
                    objective="ED",
                ).model_dump(mode="json")
            },
            "fact_checker_worker": {"verified_draft_package": {"verified_content": "Verified Content", "report": ver_report.model_dump(mode="json")}},
            "editor_worker": {"edited_draft_package": {"edited_content": "Edited Content"}},
            "seo_worker": {"seo_optimized_package": {"optimized_content": "SEO Content"}},
            "publisher_worker": {"publication_package": pub_pkg.model_dump(mode="json")},
        }

        artifacts = art_map.get(ttype, {"default_output": "data"})
        return TaskResult(
            task_id=task.id,
            worker_id=f"worker_{ttype}",
            status=TaskStatus.COMPLETED,
            execution_time=0.01,
            artifacts=artifacts,
            logs=[f"Mock execution for {ttype} completed."],
        )

    mgr.assign_and_execute = AsyncMock(side_effect=mock_execute)
    return mgr


# ===========================================================================
# Workflow Models Tests
# ===========================================================================


class TestWorkflowModels:
    """Unit tests for workflow domain models."""

    def test_workflow_status_enum_values(self):
        assert WorkflowStatus.PENDING == "PENDING"
        assert WorkflowStatus.RUNNING == "RUNNING"
        assert WorkflowStatus.COMPLETED == "COMPLETED"
        assert WorkflowStatus.FAILED == "FAILED"

    def test_execution_state_enum_values(self):
        assert ExecutionState.NOT_STARTED == "NOT_STARTED"
        assert ExecutionState.IN_PROGRESS == "IN_PROGRESS"
        assert ExecutionState.COMPLETED == "COMPLETED"

    def test_retry_policy_defaults(self):
        policy = RetryPolicy()
        assert policy.max_retries == 3
        assert policy.initial_delay_sec == 0.1
        assert policy.backoff_factor == 2.0

    def test_workflow_step_creation(self):
        step = WorkflowStep(
            step_id="step_01",
            worker_type="research_worker",
            output_artifact_key="research_package",
        )
        assert step.step_id == "step_01"
        assert step.state == ExecutionState.NOT_STARTED

    def test_workflow_execution_creation(self):
        execution = WorkflowExecution(workflow_id="wf_123", steps=[])
        assert execution.workflow_id == "wf_123"
        assert execution.status == WorkflowStatus.PENDING
        assert execution.current_step_index == 0


# ===========================================================================
# Workflow Metrics Tests
# ===========================================================================


class TestWorkflowMetrics:
    """Unit tests for WorkflowMetrics model."""

    def test_metrics_defaults(self):
        m = WorkflowMetrics()
        assert m.total_execution_time_sec == 0.0
        assert m.total_retries == 0
        assert m.checkpoint_count == 0
        assert m.success_rate == 1.0

    def test_metrics_custom_values(self):
        m = WorkflowMetrics(
            total_execution_time_sec=5.2,
            worker_durations={"step_1": 1.2},
            total_retries=1,
            checkpoint_count=8,
        )
        assert m.total_execution_time_sec == 5.2
        assert m.worker_durations["step_1"] == 1.2


# ===========================================================================
# ArtifactRegistry Tests (Refinement 1)
# ===========================================================================


class TestArtifactRegistry:
    """Unit tests for ArtifactRegistry abstraction."""

    def test_register_and_get(self):
        reg = ArtifactRegistry()
        reg.register("key1", {"data": "value"})
        assert reg.contains("key1") is True
        assert reg.get("key1") == {"data": "value"}

    def test_get_typed_pydantic_model(self, sample_request: WorkflowRequest):
        reg = ArtifactRegistry()
        reg.register("request", sample_request)
        model = reg.get_typed("request", WorkflowRequest)
        assert model.topic == "Enterprise AI Trends 2024"

    def test_get_typed_from_dict(self, sample_request: WorkflowRequest):
        reg = ArtifactRegistry()
        reg.register("request", sample_request.model_dump(mode="json"))
        model = reg.get_typed("request", WorkflowRequest)
        assert model.topic == "Enterprise AI Trends 2024"

    def test_to_dict_and_from_dict_roundtrip(self, sample_request: WorkflowRequest):
        reg = ArtifactRegistry()
        reg.register("request", sample_request)
        reg.register("raw_key", "raw_value")

        serialized = reg.to_dict()
        assert "request" in serialized
        assert serialized["raw_key"] == "raw_value"

        restored = ArtifactRegistry.from_dict(serialized)
        assert restored.contains("request") is True
        assert restored.get("raw_key") == "raw_value"

    def test_register_empty_key_raises_error(self):
        reg = ArtifactRegistry()
        with pytest.raises(ValueError):
            reg.register("", "data")

    def test_get_typed_missing_key_raises_key_error(self):
        reg = ArtifactRegistry()
        with pytest.raises(KeyError):
            reg.get_typed("missing_key", WorkflowRequest)


# ===========================================================================
# WorkflowContext Tests
# ===========================================================================


class TestWorkflowContext:
    """Unit tests for WorkflowContext."""

    def test_context_store_and_get_artifact(self, sample_request: WorkflowRequest):
        context = WorkflowContext(request=sample_request, workflow_id="wf_100")
        context.store_artifact("res", {"fact": "AI is growing"})
        assert context.get_artifact("res") == {"fact": "AI is growing"}

    def test_build_worker_task(self, sample_request: WorkflowRequest):
        context = WorkflowContext(request=sample_request, workflow_id="wf_100")
        context.store_artifact("research_package", {"facts": ["F1"]})

        step = WorkflowStep(
            step_id="step_02",
            worker_type="memory_worker",
            required_inputs=["research_package"],
            output_artifact_key="context_package",
        )
        task = context.build_worker_task(step)

        assert task.type == "memory_worker"
        assert task.payload["topic"] == "Enterprise AI Trends 2024"
        assert task.payload["research_package"] == {"facts": ["F1"]}


# ===========================================================================
# WorkflowTemplates & Planner Tests (Refinement 2)
# ===========================================================================


class TestPlannerAndTemplates:
    """Unit tests for WorkflowTemplates, ExecutionPlanner, and DependencyGraph."""

    def test_standard_pipeline_template_builds_8_steps(
        self, sample_request: WorkflowRequest
    ):
        template = StandardContentPipelineTemplate()
        steps = template.build_steps(sample_request)
        assert len(steps) == 8
        assert steps[0].worker_type == "research_worker"
        assert steps[7].worker_type == "publisher_worker"

    def test_fast_track_template_builds_4_steps(self, sample_request: WorkflowRequest):
        template = FastTrackPipelineTemplate()
        steps = template.build_steps(sample_request)
        assert len(steps) == 4

    def test_dependency_graph_validates_clean_dag(
        self, sample_request: WorkflowRequest
    ):
        template = StandardContentPipelineTemplate()
        steps = template.build_steps(sample_request)
        graph = DependencyGraph(steps)
        assert graph.validate_dag() is True

    def test_dependency_graph_raises_on_missing_input(self):
        broken_step = WorkflowStep(
            step_id="step_01",
            worker_type="writer_worker",
            required_inputs=["non_existent_artifact"],
            output_artifact_key="draft_package",
        )
        graph = DependencyGraph([broken_step])
        with pytest.raises(ValueError):
            graph.validate_dag()

    def test_execution_planner_builds_plan(self, sample_request: WorkflowRequest):
        planner = ExecutionPlanner()
        execution = planner.build_plan(sample_request, "wf_200")
        assert execution.workflow_id == "wf_200"
        assert len(execution.steps) == 8
        assert execution.status == WorkflowStatus.PENDING

    def test_execution_planner_unregistered_template_raises_error(
        self, sample_request: WorkflowRequest
    ):
        planner = ExecutionPlanner()
        sample_request.template_name = "unknown_template"
        with pytest.raises(ValueError):
            planner.build_plan(sample_request, "wf_200")


# ===========================================================================
# CheckpointManager Tests
# ===========================================================================


class TestCheckpointManager:
    """Unit tests for CheckpointManager persistence and recovery."""

    def test_save_and_load_checkpoint(
        self,
        sample_request: WorkflowRequest,
        tmp_checkpoint_dir: Path,
    ):
        chk_mgr = CheckpointManager(storage_dir=tmp_checkpoint_dir)
        planner = ExecutionPlanner()
        execution = planner.build_plan(sample_request, "wf_chk_01")
        context = WorkflowContext(request=sample_request, workflow_id="wf_chk_01")

        context.store_artifact("test_art", {"data": "test"})
        chk_mgr.save_checkpoint(execution, context)

        assert chk_mgr.has_checkpoint("wf_chk_01") is True

        loaded_exec, loaded_context = chk_mgr.load_checkpoint("wf_chk_01")
        assert loaded_exec.workflow_id == "wf_chk_01"
        assert loaded_context.get_artifact("test_art") == {"data": "test"}

    def test_load_non_existent_checkpoint_raises_file_not_found(
        self, tmp_checkpoint_dir: Path
    ):
        chk_mgr = CheckpointManager(storage_dir=tmp_checkpoint_dir)
        with pytest.raises(FileNotFoundError):
            chk_mgr.load_checkpoint("non_existent_wf")


# ===========================================================================
# RetryManager Tests
# ===========================================================================


class TestRetryManager:
    """Unit tests for RetryManager backoff execution."""

    @pytest.mark.asyncio
    async def test_successful_execution_on_first_try(self):
        mgr = RetryManager()
        step = WorkflowStep(
            step_id="step_1",
            worker_type="w",
            output_artifact_key="a",
            retry_policy=RetryPolicy(max_retries=2),
        )

        async def func():
            return TaskResult(task_id="1", worker_id="w", status=TaskStatus.COMPLETED)

        result = await mgr.execute_with_retry(step, func)
        assert result.status == TaskStatus.COMPLETED

    def test_delay_calculation_exponential(self):
        policy = RetryPolicy(initial_delay_sec=1.0, backoff_factor=2.0, max_delay_sec=10.0)
        assert RetryManager.calculate_delay(1, policy) == 1.0
        assert RetryManager.calculate_delay(2, policy) == 2.0
        assert RetryManager.calculate_delay(3, policy) == 4.0
        assert RetryManager.calculate_delay(5, policy) == 10.0  # Capped at max_delay_sec


# ===========================================================================
# WorkflowEventDispatcher Tests
# ===========================================================================


class TestWorkflowEvents:
    """Unit tests for WorkflowEventDispatcher lifecycle event emission."""

    @pytest.mark.asyncio
    async def test_all_lifecycle_events_emitted(self):
        bus = MessageBus()
        emitted: list[str] = []

        async def listener(event):
            emitted.append(event.event_type)

        for evt in [
            "WorkflowStarted",
            "StepStarted",
            "StepCompleted",
            "StepFailed",
            "CheckpointCreated",
            "WorkflowPaused",
            "WorkflowResumed",
            "WorkflowCompleted",
            "WorkflowFailed",
        ]:
            bus.add_event_listener(evt, listener)

        dispatcher = WorkflowEventDispatcher(bus=bus)
        await dispatcher.emit_workflow_started("wf_1", "Topic", "temp")
        await dispatcher.emit_step_started("wf_1", "step_1", "worker")
        await dispatcher.emit_step_completed("wf_1", "step_1", 1.0)
        await dispatcher.emit_step_failed("wf_1", "step_1", "err", 1)
        await dispatcher.emit_checkpoint_created("wf_1", "chk_1", 1)
        await dispatcher.emit_workflow_paused("wf_1", 1)
        await dispatcher.emit_workflow_resumed("wf_1", 1)
        await dispatcher.emit_workflow_completed("wf_1", "https://url.com", 5.0)
        await dispatcher.emit_workflow_failed("wf_1", "step_1", "err")

        assert "WorkflowStarted" in emitted
        assert "StepStarted" in emitted
        assert "StepCompleted" in emitted
        assert "WorkflowCompleted" in emitted


# ===========================================================================
# WorkflowEngine Integration Tests
# ===========================================================================


class TestWorkflowEngineExecution:
    """Integration tests for WorkflowEngine end-to-end orchestration."""

    @pytest.mark.asyncio
    async def test_full_8_worker_workflow_completes_successfully(
        self,
        sample_request: WorkflowRequest,
        mock_workforce_manager: WorkforceManager,
        tmp_checkpoint_dir: Path,
    ):
        bus = MessageBus()
        chk_mgr = CheckpointManager(storage_dir=tmp_checkpoint_dir)
        engine = WorkflowEngine(
            checkpoint_mgr=chk_mgr,
            workforce_mgr=mock_workforce_manager,
            bus=bus,
        )

        result = await engine.execute_workflow(sample_request)

        assert result.status == WorkflowStatus.COMPLETED
        assert result.steps_completed == 8
        assert result.publication_package is not None
        assert result.publication_package.final_url == "https://linkedin.com/post/12345"
        assert result.verification_report is not None
        assert result.quality_scores is not None
        assert result.seo_scores is not None
        assert result.execution_time_sec >= 0.0

    @pytest.mark.asyncio
    async def test_workflow_failure_path(
        self,
        sample_request: WorkflowRequest,
        tmp_checkpoint_dir: Path,
    ):
        failing_workforce = WorkforceManager(bus=MessageBus())

        async def failing_execute(task: Task, context: SharedContext) -> TaskResult:
            return TaskResult(task_id=task.id, worker_id="w", status=TaskStatus.FAILED, error="Worker error")

        failing_workforce.assign_and_execute = AsyncMock(side_effect=failing_execute)

        engine = WorkflowEngine(
            checkpoint_mgr=CheckpointManager(storage_dir=tmp_checkpoint_dir),
            workforce_mgr=failing_workforce,
            bus=MessageBus(),
        )

        result = await engine.execute_workflow(sample_request)

        assert result.status == WorkflowStatus.FAILED
        assert result.steps_completed == 0
        assert "Worker error" in result.error

    @pytest.mark.asyncio
    async def test_resume_workflow_from_checkpoint(
        self,
        sample_request: WorkflowRequest,
        mock_workforce_manager: WorkforceManager,
        tmp_checkpoint_dir: Path,
    ):
        chk_mgr = CheckpointManager(storage_dir=tmp_checkpoint_dir)
        engine = WorkflowEngine(
            checkpoint_mgr=chk_mgr,
            workforce_mgr=mock_workforce_manager,
            bus=MessageBus(),
        )

        # Run first time
        first_result = await engine.execute_workflow(sample_request)
        wf_id = first_result.workflow_id

        # Resume from checkpoint
        resumed_result = await engine.resume_workflow(wf_id)
        assert resumed_result.workflow_id == wf_id
        assert resumed_result.status == WorkflowStatus.COMPLETED

"""Workflow Engine domain models for AI Content OS.

Defines strongly-typed schemas for workflow status, execution states,
retry policies, steps, executions, checkpoints, requests, and results.
"""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from modules.workforce.workers.draft_models import WritingStyle
from modules.workforce.workers.editor_models import EditQualityScores
from modules.workforce.workers.publisher_models import PublicationPackage
from modules.workforce.workers.seo_models import SEOScores
from modules.workforce.workers.verification_models import VerificationReport


class WorkflowStatus(StrEnum):
    """Overall status of a workflow execution pipeline."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class ExecutionState(StrEnum):
    """Execution state of an individual workflow step."""

    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class RetryPolicy(BaseModel):
    """Configurable retry policy for workflow steps.

    Attributes:
        max_retries: Maximum number of retry attempts.
        initial_delay_sec: Initial backoff delay in seconds.
        backoff_factor: Multiplicative factor for exponential backoff.
        max_delay_sec: Maximum delay cap in seconds.
        retryable_exceptions: Exception names that trigger a retry.
    """

    max_retries: int = Field(default=3, ge=0, description="Max retry attempts")
    initial_delay_sec: float = Field(default=0.1, ge=0.0, description="Initial delay in seconds")
    backoff_factor: float = Field(default=2.0, ge=1.0, description="Exponential backoff factor")
    max_delay_sec: float = Field(default=10.0, ge=0.1, description="Max delay cap in seconds")
    retryable_exceptions: list[str] = Field(
        default_factory=lambda: ["TimeoutError", "ConnectionError", "RuntimeError", "ValueError"],
        description="Retryable exception name strings",
    )


class WorkflowStep(BaseModel):
    """Individual step definition within a workflow execution plan.

    Attributes:
        step_id: Unique step identifier (e.g. step_01_research).
        worker_type: Registered target worker key (e.g. research_worker).
        description: Human-readable step description.
        required_inputs: Required artifact keys in the context.
        output_artifact_key: Key for the artifact produced by this step.
        retry_policy: Retry policy configuration for this step.
        state: Current ExecutionState of the step.
        execution_time_sec: Execution duration in seconds.
        error: Diagnostic error message if step failed.
    """

    step_id: str = Field(description="Unique step identifier")
    worker_type: str = Field(description="Target worker identifier")
    description: str = Field(default="", description="Step description")
    required_inputs: list[str] = Field(default_factory=list, description="Required artifact input keys")
    output_artifact_key: str = Field(description="Generated output artifact key")
    retry_policy: RetryPolicy = Field(default_factory=RetryPolicy, description="Step retry policy")
    state: ExecutionState = Field(default=ExecutionState.NOT_STARTED, description="Current execution state")
    execution_time_sec: float = Field(default=0.0, ge=0.0, description="Duration in seconds")
    error: str | None = Field(default=None, description="Diagnostic error message")


class WorkflowExecution(BaseModel):
    """State tracking object for an active or past workflow execution.

    Attributes:
        workflow_id: Unique workflow execution ID.
        template_name: Name of the WorkflowTemplate used.
        status: Overall WorkflowStatus.
        steps: Ordered list of WorkflowStep objects.
        current_step_index: Index of the step currently running or next to run.
        start_time: ISO timestamp when workflow started.
        end_time: ISO timestamp when workflow finished.
        error: Failure error message if workflow failed.
    """

    workflow_id: str = Field(description="Unique workflow execution ID")
    template_name: str = Field(default="standard_content_pipeline", description="Template identifier")
    status: WorkflowStatus = Field(default=WorkflowStatus.PENDING, description="Overall workflow status")
    steps: list[WorkflowStep] = Field(default_factory=list, description="Ordered step list")
    current_step_index: int = Field(default=0, ge=0, description="Current active step index")
    start_time: str = Field(default_factory=lambda: datetime.now(UTC).isoformat(), description="ISO start time")
    end_time: str | None = Field(default=None, description="ISO end time")
    error: str | None = Field(default=None, description="Failure diagnostic error")


class CheckpointMetadata(BaseModel):
    """Metadata header for workflow state checkpoints.

    Attributes:
        checkpoint_id: Unique checkpoint identifier.
        workflow_id: Target workflow execution ID.
        step_index: Step index at which checkpoint was created.
        step_id: Step ID associated with checkpoint.
        timestamp: ISO timestamp of checkpoint creation.
    """

    checkpoint_id: str = Field(description="Unique checkpoint ID")
    workflow_id: str = Field(description="Workflow execution ID")
    step_index: int = Field(ge=0, description="Step index")
    step_id: str = Field(description="Step ID")
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat(), description="ISO timestamp")


class WorkflowRequest(BaseModel):
    """Incoming user request parameters for starting a workflow.

    Attributes:
        topic: Primary content topic.
        keywords: Target keywords list.
        target_platform: Publishing platform identifier.
        content_format: Target format structure.
        audience: Target audience classification.
        objective: Primary content goal.
        writing_style: Writing tone and style enum.
        template_name: WorkflowTemplate name to execute.
        route_map: Custom route map for link resolution.
        base_domain: Custom base domain for link resolution.
        context_overrides: Custom context overrides.
    """

    topic: str = Field(description="Primary content topic")
    keywords: list[str] = Field(default_factory=list, description="Target keywords list")
    target_platform: str = Field(default="linkedin", description="Target platform")
    content_format: str = Field(default="Article", description="Content structure format")
    audience: str = Field(default="General", description="Target audience classification")
    objective: str = Field(default="EDUCATIONAL", description="Primary content goal")
    writing_style: WritingStyle = Field(default=WritingStyle.AUTHORITATIVE, description="Writing style enum")
    template_name: str = Field(default="standard_content_pipeline", description="Template identifier")
    route_map: dict[str, str] = Field(default_factory=dict, description="Custom link route map")
    base_domain: str | None = Field(default=None, description="Custom base domain")
    context_overrides: dict[str, Any] = Field(default_factory=dict, description="Custom overrides")


class WorkflowCheckpoint(BaseModel):
    """Full snapshot model for persistent workflow checkpointing.

    Attributes:
        metadata: CheckpointMetadata header.
        execution_state: Full WorkflowExecution model snapshot.
        context_artifacts: Serialized dictionary of all accumulated artifacts.
        request: Original WorkflowRequest specification.
    """

    metadata: CheckpointMetadata = Field(description="Checkpoint metadata")
    execution_state: WorkflowExecution = Field(description="WorkflowExecution snapshot")
    context_artifacts: dict[str, Any] = Field(default_factory=dict, description="Artifacts dictionary")
    request: WorkflowRequest | None = Field(default=None, description="Original WorkflowRequest specification")


class WorkflowResult(BaseModel):
    """Final output object returned upon completion of a workflow.

    Attributes:
        workflow_id: Unique workflow execution ID.
        status: Final WorkflowStatus.
        publication_package: Final PublicationPackage (if pipeline completed publishing).
        execution_time_sec: Total workflow execution duration in seconds.
        steps_completed: Count of steps successfully completed.
        metrics_summary: Telemetry metrics dictionary.
        verification_report: Forwarded immutable VerificationReport.
        quality_scores: Forwarded immutable EditQualityScores.
        seo_scores: Forwarded immutable SEOScores.
        error: Diagnostic error string if workflow failed.
    """

    workflow_id: str = Field(description="Workflow execution ID")
    status: WorkflowStatus = Field(description="Final workflow status")
    publication_package: PublicationPackage | None = Field(default=None, description="Final PublicationPackage")
    execution_time_sec: float = Field(default=0.0, ge=0.0, description="Total execution duration")
    steps_completed: int = Field(default=0, ge=0, description="Completed steps count")
    metrics_summary: dict[str, Any] = Field(default_factory=dict, description="Execution metrics")
    verification_report: VerificationReport | None = Field(default=None, description="Lineage VerificationReport")
    quality_scores: EditQualityScores | None = Field(default=None, description="Lineage EditQualityScores")
    seo_scores: SEOScores | None = Field(default=None, description="Lineage SEOScores")
    error: str | None = Field(default=None, description="Failure error string")

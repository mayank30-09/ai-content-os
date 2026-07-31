"""Workflow Engine telemetry metrics model.

Tracks performance indicators for the entire workflow orchestration pipeline.
"""

from pydantic import BaseModel, Field


class WorkflowMetrics(BaseModel):
    """Telemetry metrics for the Workflow Engine execution pipeline.

    Attributes:
        total_execution_time_sec: Total workflow duration in seconds.
        worker_durations: Per-step execution durations dictionary {step_id: duration_sec}.
        total_retries: Total retry attempts executed across all steps.
        queue_wait_time_sec: Time spent waiting in queue between steps.
        checkpoint_count: Count of persistent checkpoints saved.
        success_rate: Step completion ratio (0.0–1.0).
        artifacts_generated_count: Total count of typed artifacts produced.
    """

    total_execution_time_sec: float = Field(default=0.0, ge=0.0, description="Total duration in seconds")
    worker_durations: dict[str, float] = Field(default_factory=dict, description="Per-step durations")
    total_retries: int = Field(default=0, ge=0, description="Total retry attempts")
    queue_wait_time_sec: float = Field(default=0.0, ge=0.0, description="Queue wait duration")
    checkpoint_count: int = Field(default=0, ge=0, description="Checkpoints saved count")
    success_rate: float = Field(default=1.0, ge=0.0, le=1.0, description="Step success ratio")
    artifacts_generated_count: int = Field(default=0, ge=0, description="Generated artifacts count")

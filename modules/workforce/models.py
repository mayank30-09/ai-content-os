"""Data models module for AI Workforce Core subsystem.

Defines Pydantic schemas and enums for tasks, task results, messages, worker states,
worker metrics, and workforce events.
"""

import uuid
from datetime import UTC, datetime
from enum import Enum, StrEnum
from typing import Any

from pydantic import BaseModel, Field


class RetryStrategy(StrEnum):
    """Supported task execution retry strategies."""
    IMMEDIATE = "IMMEDIATE"
    EXPONENTIAL_BACKOFF = "EXPONENTIAL_BACKOFF"
    MANUAL = "MANUAL"

class WorkerState(StrEnum):
    """Enumeration of worker lifecycle states."""
    CREATED = "CREATED"
    READY = "READY"
    RUNNING = "RUNNING"
    WAITING = "WAITING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    STOPPED = "STOPPED"

class TaskPriority(int, Enum):
    """Priority weights for scheduler queue ordering."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4

class TaskStatus(StrEnum):
    """Lifecycle status of a workforce task."""
    PENDING = "PENDING"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

class Task(BaseModel):
    """Strongly typed task specification for AI workforce execution."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique task ID")
    type: str = Field(..., description="Task category e.g. research, script, carousel, copywriting")
    priority: TaskPriority = Field(default=TaskPriority.NORMAL, description="Priority level")
    creator: str = Field(..., description="System module or worker ID that submitted task")
    assigned_worker: str | None = Field(default=None, description="Assigned worker ID")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="Current task status")
    max_retries: int = Field(default=3, ge=0, description="Max allowed retry attempts")
    retry_count: int = Field(default=0, ge=0, description="Current retry attempt count")
    retry_strategy: RetryStrategy = Field(default=RetryStrategy.EXPONENTIAL_BACKOFF, description="Retry strategy")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Creation timestamp")
    deadline: datetime | None = Field(default=None, description="Optional completion deadline")
    payload: dict[str, Any] = Field(default_factory=dict, description="Task arguments and input data")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Arbitrary task execution metadata")

class TaskResult(BaseModel):
    """Standardized result output returned by worker execution."""
    task_id: str = Field(..., description="Target task ID")
    worker_id: str = Field(..., description="Executing worker ID")
    status: TaskStatus = Field(..., description="Execution outcome status")
    execution_time: float = Field(default=0.0, description="Execution duration in seconds")
    artifacts: dict[str, Any] = Field(default_factory=dict, description="Generated output deliverables")
    logs: list[str] = Field(default_factory=list, description="Worker execution log entries")
    metrics: dict[str, Any] = Field(default_factory=dict, description="Execution performance metrics")
    error: str | None = Field(default=None, description="Error message if execution failed")

class WorkerMetrics(BaseModel):
    """Telemetry metrics model for worker monitoring dashboards."""
    tasks_completed: int = Field(default=0, ge=0, description="Count of successfully completed tasks")
    tasks_failed: int = Field(default=0, ge=0, description="Count of failed task attempts")
    success_rate: float = Field(default=1.0, ge=0.0, le=1.0, description="Ratio of successful tasks")
    average_execution_time: float = Field(default=0.0, ge=0.0, description="Average task duration in seconds")
    last_execution: datetime | None = Field(default=None, description="Timestamp of last task execution")
    uptime: float = Field(default=0.0, ge=0.0, description="Worker active uptime in seconds")

class TaskMessage(BaseModel):
    """Decoupled communication message passed between workforce workers."""
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique message ID")
    sender: str = Field(..., description="Sender worker ID or system module name")
    recipient: str = Field(..., description="Target worker ID or broadcast indicator")
    task_id: str = Field(..., description="Associated task ID")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Message timestamp")
    payload: dict[str, Any] = Field(default_factory=dict, description="Message body payload")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Message metadata")

class WorkforceEvent(BaseModel):
    """Event payload emitted on workforce state transitions."""
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique event ID")
    event_type: str = Field(..., description="e.g. TaskCreated, TaskAssigned, TaskCompleted")
    source: str = Field(..., description="Event origin source identifier")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Event timestamp")
    data: dict[str, Any] = Field(default_factory=dict, description="Event data details")

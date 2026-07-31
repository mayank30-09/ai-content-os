"""Production Observability & Monitoring models for AI Content OS.

Defines Pydantic v2 domain schemas for distributed trace contexts, spans,
time-series metric points, structured audit events, and telemetry summaries.
"""

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class MetricType(StrEnum):
    """Metric type classification enumeration."""

    COUNTER = "COUNTER"
    GAUGE = "GAUGE"
    HISTOGRAM = "HISTOGRAM"


class TraceContext(BaseModel):
    """5-field correlation metadata context model for distributed tracing."""

    correlation_id: str = Field(default_factory=lambda: f"corr_{uuid.uuid4().hex[:12]}", description="End-to-end trace correlation UUID")
    workflow_id: str = Field(default="none", description="Workflow execution ID")
    worker_id: str = Field(default="none", description="Active worker ID")
    request_id: str = Field(default="none", description="External request ID")
    execution_id: str = Field(default="none", description="Step execution instance ID")
    span_id: str = Field(default_factory=lambda: f"span_{uuid.uuid4().hex[:8]}", description="Active span ID")
    parent_span_id: str | None = Field(default=None, description="Parent span ID for DAG hierarchy")


class Span(BaseModel):
    """Distributed tracing span model representing an operation execution segment."""

    trace_id: str = Field(default_factory=lambda: f"trace_{uuid.uuid4().hex[:16]}", description="Root trace ID")
    span_id: str = Field(description="Unique span identifier")
    name: str = Field(description="Operation or task name")
    context: TraceContext = Field(description="Correlation context metadata")
    start_time_iso: str = Field(default_factory=lambda: datetime.now(UTC).isoformat(), description="ISO start timestamp")
    end_time_iso: str | None = Field(default=None, description="ISO finish timestamp")
    duration_ms: float = Field(default=0.0, ge=0.0, description="Duration in milliseconds")
    attributes: dict[str, Any] = Field(default_factory=dict, description="Custom span tags & attributes")
    status: str = Field(default="OK", description="Span execution status (OK, ERROR)")

    def finish(self, status: str = "OK") -> None:
        """Marks the span finished, calculating duration in milliseconds."""
        self.end_time_iso = datetime.now(UTC).isoformat()
        self.status = status
        start_dt = datetime.fromisoformat(self.start_time_iso)
        end_dt = datetime.fromisoformat(self.end_time_iso)
        self.duration_ms = round((end_dt - start_dt).total_seconds() * 1000, 3)


class MetricPoint(BaseModel):
    """Time-series metric data point model."""

    name: str = Field(description="Metric name string")
    metric_type: MetricType = Field(description="Type of metric")
    value: float = Field(description="Numeric metric value")
    labels: dict[str, str] = Field(default_factory=dict, description="Dimensions and labels dictionary")
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat(), description="ISO timestamp")


class AuditEvent(BaseModel):
    """Structured security and operational audit log event model."""

    event_id: str = Field(default_factory=lambda: f"audit_{uuid.uuid4().hex[:12]}", description="Audit event UUID")
    action: str = Field(description="Audited action name")
    actor: str = Field(default="system", description="Entity initiating action")
    target: str = Field(default="system", description="Target resource or entity")
    status: str = Field(default="SUCCESS", description="Outcome status (SUCCESS, FAILURE)")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Contextual payload metadata")
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat(), description="ISO timestamp")


class TelemetrySummary(BaseModel):
    """Aggregated telemetry metrics and statistics summary model."""

    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat(), description="ISO generation timestamp")
    total_spans_recorded: int = Field(default=0, ge=0, description="Total finished spans count")
    total_metrics_recorded: int = Field(default=0, ge=0, description="Total metrics data points count")
    counters: dict[str, float] = Field(default_factory=dict, description="Counter metrics sum")
    gauges: dict[str, float] = Field(default_factory=dict, description="Current gauge state values")
    histograms_p95_ms: dict[str, float] = Field(default_factory=dict, description="Histogram 95th percentile latencies")
    audit_events_count: int = Field(default=0, ge=0, description="Total audit events recorded")

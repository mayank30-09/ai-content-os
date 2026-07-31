"""MessageBus event subscriber for non-blocking observability collection.

Decouples telemetry collection from business workflow execution by converting system events
into tracing spans, time-series metrics, and structured audit logs.
"""

import threading
from typing import Any

from loguru import logger

from modules.observability.audit import AuditLogger
from modules.observability.metrics import MetricsCollector
from modules.observability.models import TraceContext
from modules.observability.tracing import Tracer
from modules.workforce.bus import MessageBus


class ObservabilitySubscriber:
    """Listens to MessageBus events and updates Tracer, MetricsCollector, and AuditLogger."""

    def __init__(
        self,
        tracer: Tracer,
        metrics: MetricsCollector,
        audit: AuditLogger,
        bus: MessageBus | None = None,
    ) -> None:
        """Initializes ObservabilitySubscriber with components.

        Args:
            tracer: Tracer engine instance.
            metrics: MetricsCollector instance.
            audit: AuditLogger instance.
            bus: MessageBus instance to subscribe to.
        """
        self.tracer: Tracer = tracer
        self.metrics: MetricsCollector = metrics
        self.audit: AuditLogger = audit
        self.bus: MessageBus | None = bus
        self._active_step_spans: dict[str, Any] = {}
        self._span_lock: threading.Lock = threading.Lock()

        if self.bus:
            self.attach_to_bus(self.bus)

    def attach_to_bus(self, bus: MessageBus) -> None:
        """Attaches async event listeners to the provided MessageBus.

        Args:
            bus: MessageBus instance.
        """
        self.bus = bus
        for event_name in [
            "WorkflowStarted",
            "StepStarted",
            "StepCompleted",
            "WorkflowCompleted",
            "WorkflowFailed",
        ]:
            bus.add_event_listener(event_name, self._handle_event)
        logger.info("ObservabilitySubscriber: attached listeners to MessageBus")

    async def _handle_event(self, event: Any) -> None:
        """Asynchronous event handler catching all exceptions to guarantee non-blocking safety."""
        try:
            evt_type = getattr(event, "event_type", "Unknown")
            source = getattr(event, "source", "system")
            payload = getattr(event, "data", getattr(event, "payload", {}))

            wf_id = payload.get("workflow_id", "none")
            step_name = payload.get("step_name", payload.get("worker_type", "step"))

            if evt_type == "WorkflowStarted":
                self.metrics.increment_counter("ai_content_os_workflows_started_total")
                self.metrics.set_gauge("ai_content_os_active_workflows", 1)
                self.audit.record_audit_event(
                    action="workflow_started",
                    actor=source,
                    target=wf_id,
                    metadata=payload,
                )

            elif evt_type == "StepStarted":
                ctx = TraceContext(workflow_id=wf_id, worker_id=step_name)
                span = self.tracer.start_span(name=f"step_{step_name}", context=ctx, attributes=payload)
                with self._span_lock:
                    self._active_step_spans[f"{wf_id}_{step_name}"] = span

            elif evt_type == "StepCompleted":
                span_key = f"{wf_id}_{step_name}"
                with self._span_lock:
                    span = self._active_step_spans.pop(span_key, None)
                if span:
                    self.tracer.finish_span(span, status="OK")
                    self.metrics.observe_histogram(
                        "ai_content_os_worker_task_duration_milliseconds",
                        span.duration_ms,
                        labels={"worker_type": step_name, "status": "COMPLETED"},
                    )

                self.metrics.increment_counter(
                    "ai_content_os_worker_tasks_executed_total",
                    labels={"worker_type": step_name, "status": "COMPLETED"},
                )

            elif evt_type == "WorkflowCompleted":
                self.metrics.increment_counter("ai_content_os_workflows_completed_total")
                self.metrics.set_gauge("ai_content_os_active_workflows", 0)
                exec_time = payload.get("execution_time_sec", 0.0)
                self.metrics.observe_histogram("ai_content_os_workflow_duration_seconds", exec_time * 1000.0)
                self.audit.record_audit_event(
                    action="workflow_completed",
                    actor=source,
                    target=wf_id,
                    metadata=payload,
                )

            elif evt_type == "WorkflowFailed":
                self.metrics.increment_counter("ai_content_os_errors_total", labels={"error_code": "WORKFLOW_FAILED"})
                self.metrics.set_gauge("ai_content_os_active_workflows", 0)
                self.audit.record_audit_event(
                    action="workflow_failed",
                    actor=source,
                    target=wf_id,
                    status="FAILURE",
                    metadata=payload,
                )

        except Exception as e:
            # Isolated error handling ensures core execution is never impacted
            logger.warning(f"ObservabilitySubscriber: internal exception caught gracefully: {e}")

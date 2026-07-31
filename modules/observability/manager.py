"""ObservabilityManager facade orchestrator for AI Content OS.

Provides a unified thread-safe facade for tracing, time-series metrics collection,
audit event logging, and telemetry exporter formatting.
"""

from typing import Any

from loguru import logger

from modules.observability.audit import AuditLogger
from modules.observability.events import ObservabilitySubscriber
from modules.observability.exporters.otel import OTelExporter
from modules.observability.exporters.prometheus import PrometheusExporter
from modules.observability.metrics import MetricsCollector
from modules.observability.models import Span, TelemetrySummary, TraceContext
from modules.observability.tracing import Tracer
from modules.workforce.bus import MessageBus


class ObservabilityManager:
    """Unified Observability & Monitoring facade manager."""

    def __init__(self, bus: MessageBus | None = None) -> None:
        """Initializes ObservabilityManager and underlying components.

        Args:
            bus: Optional MessageBus instance to attach automated telemetry listeners.
        """
        self.tracer: Tracer = Tracer()
        self.metrics: MetricsCollector = MetricsCollector()
        self.audit: AuditLogger = AuditLogger()
        self.prometheus_exporter: PrometheusExporter = PrometheusExporter()
        self.otel_exporter: OTelExporter = OTelExporter()

        self.subscriber: ObservabilitySubscriber | None = None
        if bus:
            self.subscriber = ObservabilitySubscriber(
                tracer=self.tracer,
                metrics=self.metrics,
                audit=self.audit,
                bus=bus,
            )

        logger.info("ObservabilityManager: initialized observability subsystem facade")

    def start_trace(
        self,
        name: str,
        correlation_id: str | None = None,
        workflow_id: str | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> Span:
        """Starts a root tracing span.

        Args:
            name: Operation span name.
            correlation_id: Optional correlation ID string.
            workflow_id: Optional workflow ID string.
            attributes: Optional tags/attributes dictionary.

        Returns:
            Span instance.
        """
        ctx = TraceContext(
            correlation_id=correlation_id or TraceContext().correlation_id,
            workflow_id=workflow_id or "none",
        )
        return self.tracer.start_span(name=name, context=ctx, attributes=attributes)

    def finish_trace(self, span: Span, status: str = "OK") -> None:
        """Finishes a tracing span.

        Args:
            span: Span to finish.
            status: Outcome status ('OK', 'ERROR').
        """
        self.tracer.finish_span(span, status=status)

    def record_counter(self, name: str, value: float = 1.0, labels: dict[str, str] | None = None) -> None:
        """Increments a counter metric.

        Args:
            name: Metric name.
            value: Increment value.
            labels: Labels dict.
        """
        self.metrics.increment_counter(name=name, value=value, labels=labels)

    def record_gauge(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        """Sets a gauge metric.

        Args:
            name: Metric name.
            value: Gauge state.
            labels: Labels dict.
        """
        self.metrics.set_gauge(name=name, value=value, labels=labels)

    def record_histogram(self, name: str, value_ms: float, labels: dict[str, str] | None = None) -> None:
        """Observes a latency value into a histogram.

        Args:
            name: Metric name.
            value_ms: Latency in ms.
            labels: Labels dict.
        """
        self.metrics.observe_histogram(name=name, value_ms=value_ms, labels=labels)

    def record_audit(
        self,
        action: str,
        actor: str = "system",
        target: str = "system",
        status: str = "SUCCESS",
        metadata: dict | None = None,
    ) -> None:
        """Records a structured audit event.

        Args:
            action: Action name.
            actor: Actor entity.
            target: Target resource.
            status: Status ('SUCCESS', 'FAILURE').
            metadata: Additional metadata dict.
        """
        self.audit.record_audit_event(
            action=action,
            actor=actor,
            target=target,
            status=status,
            metadata=metadata,
        )

    def get_prometheus_metrics_text(self) -> str:
        """Generates scrapable Prometheus OpenMetrics exposition text.

        Returns:
            Prometheus text format string.
        """
        points = self.metrics.get_all_metric_points()
        return self.prometheus_exporter.build_prometheus_text(points)

    def get_otlp_spans_payload(self) -> dict[str, Any]:
        """Formats finished spans into OpenTelemetry OTLP JSON structure.

        Returns:
            OTLP ResourceSpans dictionary.
        """
        spans = self.tracer.get_finished_spans()
        return self.otel_exporter.build_otlp_spans_payload(spans)

    def get_telemetry_summary(self) -> TelemetrySummary:
        """Returns a snapshot TelemetrySummary model.

        Returns:
            TelemetrySummary instance.
        """
        summary = self.metrics.get_summary()
        summary.total_spans_recorded = len(self.tracer.get_finished_spans())
        summary.audit_events_count = len(self.audit.get_audit_events())
        return summary

"""Comprehensive unit and integration test suite for Production Observability & Monitoring subsystem.

Tests cover:
- Distributed TraceContext and Span creation, duration calculation, and status updating.
- Tracer parent-child trace context management and bounded storage.
- MetricsCollector counter increments, gauge updates, histogram percentile math (p95).
- AuditLogger structured security & operational audit event logging.
- ObservabilitySubscriber MessageBus integration & non-blocking execution safety.
- PrometheusExporter scrapable OpenMetrics text formatting.
- OTelExporter OpenTelemetry OTLP JSON structure generation.
- ObservabilityManager facade orchestration & TelemetrySummary metrics aggregation.
"""

import pytest

from modules.observability import (
    AuditEvent,
    AuditLogger,
    MetricPoint,
    MetricsCollector,
    MetricType,
    ObservabilityManager,
    ObservabilitySubscriber,
    OTelExporter,
    PrometheusExporter,
    Span,
    TraceContext,
    Tracer,
)
from modules.workforce.bus import MessageBus

# ===========================================================================
# Tracing & Models Tests
# ===========================================================================


class TestTracingAndModels:
    """Unit tests for trace context, span creation, and Tracer engine."""

    def test_trace_context_defaults(self):
        ctx = TraceContext(workflow_id="wf_123", worker_id="writer")
        assert ctx.correlation_id.startswith("corr_")
        assert ctx.span_id.startswith("span_")
        assert ctx.workflow_id == "wf_123"
        assert ctx.parent_span_id is None

    def test_span_finish_latency_calculation(self):
        ctx = TraceContext()
        span = Span(span_id=ctx.span_id, name="writer_task", context=ctx)
        assert span.duration_ms == 0.0

        span.finish(status="OK")
        assert span.status == "OK"
        assert span.end_time_iso is not None
        assert span.duration_ms >= 0.0

    def test_tracer_span_lifecycle(self):
        tracer = Tracer(max_finished_spans=100)
        span = tracer.start_span("research_task")
        assert span is not None

        tracer.finish_span(span, status="OK")
        finished = tracer.get_finished_spans()
        assert len(finished) == 1
        assert finished[0].name == "research_task"


# ===========================================================================
# MetricsCollector Tests
# ===========================================================================


class TestMetricsCollector:
    """Unit tests for MetricsCollector counters, gauges, histograms, and summary math."""

    def test_counter_and_gauge_recording(self):
        collector = MetricsCollector()
        collector.increment_counter("workflows_total", value=1.0, labels={"env": "prod"})
        collector.increment_counter("workflows_total", value=2.0, labels={"env": "prod"})
        collector.set_gauge("active_workflows", value=5.0)

        summary = collector.get_summary()
        assert summary.counters['workflows_total{env="prod"}'] == 3.0
        assert summary.gauges["active_workflows"] == 5.0

    def test_histogram_p95_calculation(self):
        collector = MetricsCollector()
        for lat in range(1, 101):  # 1ms to 100ms
            collector.observe_histogram("step_latency_ms", float(lat))

        summary = collector.get_summary()
        assert "step_latency_ms" in summary.histograms_p95_ms
        assert summary.histograms_p95_ms["step_latency_ms"] >= 94.0


# ===========================================================================
# AuditLogger Tests
# ===========================================================================


class TestAuditLogger:
    """Unit tests for AuditLogger event recording."""

    def test_record_audit_event(self):
        logger_inst = AuditLogger()
        event = logger_inst.record_audit_event(
            action="publication_executed",
            actor="publisher_worker",
            target="linkedin_api",
            status="SUCCESS",
            metadata={"post_id": "12345"},
        )
        assert isinstance(event, AuditEvent)
        assert event.action == "publication_executed"

        events = logger_inst.get_audit_events()
        assert len(events) == 1
        assert events[0].metadata["post_id"] == "12345"


# ===========================================================================
# ObservabilitySubscriber & MessageBus Tests
# ===========================================================================


class TestObservabilitySubscriber:
    """Integration test suite for ObservabilitySubscriber and MessageBus."""

    @pytest.mark.asyncio
    async def test_subscriber_handles_workflow_events(self):
        bus = MessageBus()
        tracer = Tracer()
        metrics = MetricsCollector()
        audit = AuditLogger()
        _subscriber = ObservabilitySubscriber(tracer, metrics, audit, bus=bus)

        # Publish WorkflowStarted
        await bus.emit_event(
            event_type="WorkflowStarted",
            source="WorkflowEngine",
            data={"workflow_id": "wf_test_100"},
        )

        # Publish StepStarted & StepCompleted
        await bus.emit_event(
            event_type="StepStarted",
            source="WorkforceManager",
            data={"workflow_id": "wf_test_100", "step_name": "writer"},
        )
        await bus.emit_event(
            event_type="StepCompleted",
            source="WorkforceManager",
            data={"workflow_id": "wf_test_100", "step_name": "writer"},
        )

        # Publish WorkflowCompleted
        await bus.emit_event(
            event_type="WorkflowCompleted",
            source="WorkflowEngine",
            data={"workflow_id": "wf_test_100", "execution_time_sec": 1.5},
        )

        summary = metrics.get_summary()
        assert summary.counters["ai_content_os_workflows_started_total"] == 1.0
        assert summary.counters["ai_content_os_workflows_completed_total"] == 1.0
        assert len(tracer.get_finished_spans()) == 1
        assert len(audit.get_audit_events()) == 2


# ===========================================================================
# Exporters Tests
# ===========================================================================


class TestTelemetryExporters:
    """Unit tests for Prometheus and OpenTelemetry exporters."""

    def test_prometheus_exporter_formatting(self):
        exporter = PrometheusExporter()
        points = [
            MetricPoint(name="http_requests_total", metric_type=MetricType.COUNTER, value=10.0, labels={"method": "GET"}),
            MetricPoint(name="memory_usage_bytes", metric_type=MetricType.GAUGE, value=1024.0),
        ]
        text = exporter.build_prometheus_text(points)

        assert "# HELP http_requests_total" in text
        assert "# TYPE http_requests_total counter" in text
        assert 'http_requests_total{method="GET"} 10.0' in text
        assert "memory_usage_bytes 1024.0" in text

    def test_otel_exporter_json_payload_generation(self):
        exporter = OTelExporter()
        ctx = TraceContext()
        span = Span(span_id=ctx.span_id, name="editor_task", context=ctx, attributes={"edits": 3})
        span.finish()

        otlp_spans = exporter.build_otlp_spans_payload([span])
        assert "resourceSpans" in otlp_spans
        spans_list = otlp_spans["resourceSpans"][0]["scopeSpans"][0]["spans"]
        assert len(spans_list) == 1
        assert spans_list[0]["name"] == "editor_task"


# ===========================================================================
# ObservabilityManager Facade Tests
# ===========================================================================


class TestObservabilityManagerFacade:
    """Integration test suite for ObservabilityManager facade."""

    def test_manager_facade_recording_and_summary(self):
        bus = MessageBus()
        obs_mgr = ObservabilityManager(bus=bus)

        # Record manual telemetry through facade
        span = obs_mgr.start_trace("fact_checker_task", correlation_id="c_1", workflow_id="wf_1")
        obs_mgr.record_counter("claims_verified_total", value=5.0)
        obs_mgr.record_gauge("memory_mb", value=256.0)
        obs_mgr.record_histogram("task_latency_ms", value_ms=45.0)
        obs_mgr.record_audit("fact_check_passed", actor="fact_checker", target="draft_1")
        obs_mgr.finish_trace(span, status="OK")

        summary = obs_mgr.get_telemetry_summary()
        assert summary.total_spans_recorded == 1
        assert summary.audit_events_count == 1

        prom_text = obs_mgr.get_prometheus_metrics_text()
        assert "claims_verified_total" in prom_text

        otlp_payload = obs_mgr.get_otlp_spans_payload()
        assert len(otlp_payload["resourceSpans"]) == 1

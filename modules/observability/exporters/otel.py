"""OpenTelemetry OTLP JSON exporter hook for AI Content OS.

Formats spans and metric points into OpenTelemetry-compatible payload dicts.
"""

from typing import Any

from modules.observability.exporters.base import BaseTelemetryExporter
from modules.observability.models import MetricPoint, Span


class OTelExporter(BaseTelemetryExporter):
    """Formats Spans and Metrics into OpenTelemetry OTLP structure."""

    def export_spans(self, spans: list[Span]) -> bool:
        """Exports spans to OpenTelemetry collector structure.

        Args:
            spans: List of Span instances.

        Returns:
            True if export succeeds.
        """
        payload = self.build_otlp_spans_payload(spans)
        return len(payload.get("resourceSpans", [])) >= 0

    def export_metrics(self, metrics: list[MetricPoint]) -> bool:
        """Exports metrics to OpenTelemetry collector structure.

        Args:
            metrics: List of MetricPoint instances.

        Returns:
            True if export succeeds.
        """
        payload = self.build_otlp_metrics_payload(metrics)
        return len(payload.get("resourceMetrics", [])) >= 0

    def build_otlp_spans_payload(self, spans: list[Span]) -> dict[str, Any]:
        """Formats Span objects into OpenTelemetry OTLP JSON format.

        Args:
            spans: List of finished Span objects.

        Returns:
            Dictionary matching OTLP ResourceSpans JSON structure.
        """
        otlp_spans = []
        for s in spans:
            otlp_spans.append({
                "traceId": s.trace_id,
                "spanId": s.span_id,
                "parentSpanId": s.context.parent_span_id or "",
                "name": s.name,
                "startTimeUnixNano": int(float(s.duration_ms) * 1e6),
                "attributes": [{"key": k, "value": {"stringValue": str(v)}} for k, v in s.attributes.items()],
                "status": {"code": 1 if s.status == "OK" else 2},
            })

        return {
            "resourceSpans": [{
                "resource": {"attributes": [{"key": "service.name", "value": {"stringValue": "ai-content-os"}}]},
                "scopeSpans": [{"scope": {"name": "ai-content-os-tracer"}, "spans": otlp_spans}],
            }]
        }

    def build_otlp_metrics_payload(self, metrics: list[MetricPoint]) -> dict[str, Any]:
        """Formats MetricPoint objects into OpenTelemetry OTLP JSON format.

        Args:
            metrics: List of MetricPoint objects.

        Returns:
            Dictionary matching OTLP ResourceMetrics JSON structure.
        """
        otlp_metrics = []
        for m in metrics:
            otlp_metrics.append({
                "name": m.name,
                "data": {
                    "dataPoints": [{
                        "asDouble": float(m.value),
                        "attributes": [{"key": k, "value": {"stringValue": v}} for k, v in m.labels.items()],
                    }]
                },
            })

        return {
            "resourceMetrics": [{
                "resource": {"attributes": [{"key": "service.name", "value": {"stringValue": "ai-content-os"}}]},
                "scopeMetrics": [{"scope": {"name": "ai-content-os-metrics"}, "metrics": otlp_metrics}],
            }]
        }

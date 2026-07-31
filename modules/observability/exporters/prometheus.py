"""Prometheus exposition format builder for AI Content OS metrics.

Formats time-series counters, gauges, and histograms into scrapable
Prometheus / OpenMetrics text format lines.
"""

from modules.observability.exporters.base import BaseTelemetryExporter
from modules.observability.models import MetricPoint, Span


class PrometheusExporter(BaseTelemetryExporter):
    """Generates Prometheus scrapable text exposition format from metrics data."""

    def export_spans(self, spans: list[Span]) -> bool:
        """Prometheus exporter does not export trace spans.

        Returns:
            Always True.
        """
        return True

    def export_metrics(self, metrics: list[MetricPoint]) -> bool:
        """Validates metric points formatting readiness.

        Returns:
            Always True.
        """
        return True

    def build_prometheus_text(self, metrics: list[MetricPoint]) -> str:
        """Formats MetricPoint instances into Prometheus OpenMetrics text format.

        Args:
            metrics: List of MetricPoint instances.

        Returns:
            Formatted Prometheus exposition text string.
        """
        lines: list[str] = []
        seen_headers: set[str] = set()

        for m in metrics:
            if m.name not in seen_headers:
                lines.append(f"# HELP {m.name} AI Content OS telemetry metric {m.name}")
                lines.append(f"# TYPE {m.name} {m.metric_type.value.lower()}")
                seen_headers.add(m.name)

            lbl_str = ""
            if m.labels:
                lbls = ",".join(f'{k}="{v}"' for k, v in sorted(m.labels.items()))
                lbl_str = f"{{{lbls}}}"

            lines.append(f"{m.name}{lbl_str} {m.value}")

        return "\n".join(lines) + "\n" if lines else ""

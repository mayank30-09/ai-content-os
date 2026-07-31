"""Base telemetry exporter interface for AI Content OS.

Defines the abstract interface for exporting spans and metrics to external systems
(e.g., Prometheus, OpenTelemetry Collector, Datadog).
"""

from abc import ABC, abstractmethod

from modules.observability.models import MetricPoint, Span


class BaseTelemetryExporter(ABC):
    """Abstract strategy interface for exporting spans and metrics."""

    @abstractmethod
    def export_spans(self, spans: list[Span]) -> bool:
        """Exports a list of finished trace Spans.

        Args:
            spans: List of Span models.

        Returns:
            True if export succeeded, False otherwise.
        """
        pass

    @abstractmethod
    def export_metrics(self, metrics: list[MetricPoint]) -> bool:
        """Exports a list of MetricPoint objects.

        Args:
            metrics: List of MetricPoint models.

        Returns:
            True if export succeeded, False otherwise.
        """
        pass

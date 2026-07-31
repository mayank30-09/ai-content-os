"""Time-series MetricsCollector and aggregator for AI Content OS.

Provides thread-safe counter increments, gauge updates, latency histogram distribution
observations, and telemetry summary generation.
"""

import math
import threading
from collections import defaultdict, deque

from modules.observability.models import MetricPoint, MetricType, TelemetrySummary


class MetricsCollector:
    """Thread-safe time-series metrics aggregator."""

    def __init__(self, histogram_buffer_size: int = 1000) -> None:
        """Initializes MetricsCollector.

        Args:
            histogram_buffer_size: Maximum latency values retained per histogram metric.
        """
        self._counters: defaultdict[str, float] = defaultdict(float)
        self._gauges: dict[str, float] = {}
        self._histograms: defaultdict[str, deque[float]] = defaultdict(lambda: deque(maxlen=histogram_buffer_size))
        self._metric_points: deque[MetricPoint] = deque(maxlen=10000)
        self._lock: threading.Lock = threading.Lock()

    def increment_counter(self, name: str, value: float = 1.0, labels: dict[str, str] | None = None) -> None:
        """Increments a counter metric by value.

        Args:
            name: Metric name string.
            value: Increment value (default 1.0).
            labels: Metric dimensions/labels dictionary.
        """
        lbls = labels or {}
        key = self._format_key(name, lbls)
        with self._lock:
            self._counters[key] += value
            self._metric_points.append(
                MetricPoint(name=name, metric_type=MetricType.COUNTER, value=value, labels=lbls)
            )

    def set_gauge(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        """Sets a gauge metric value.

        Args:
            name: Metric name string.
            value: New gauge state value.
            labels: Metric dimensions/labels dictionary.
        """
        lbls = labels or {}
        key = self._format_key(name, lbls)
        with self._lock:
            self._gauges[key] = value
            self._metric_points.append(
                MetricPoint(name=name, metric_type=MetricType.GAUGE, value=value, labels=lbls)
            )

    def observe_histogram(self, name: str, value_ms: float, labels: dict[str, str] | None = None) -> None:
        """Observes a latency value into a histogram distribution.

        Args:
            name: Metric name string.
            value_ms: Latency observation in milliseconds.
            labels: Metric dimensions/labels dictionary.
        """
        lbls = labels or {}
        key = self._format_key(name, lbls)
        with self._lock:
            self._histograms[key].append(value_ms)
            self._metric_points.append(
                MetricPoint(name=name, metric_type=MetricType.HISTOGRAM, value=value_ms, labels=lbls)
            )

    def get_summary(self) -> TelemetrySummary:
        """Calculates percentile math and returns a TelemetrySummary snapshot.

        Returns:
            TelemetrySummary model.
        """
        with self._lock:
            counters_copy = dict(self._counters)
            gauges_copy = dict(self._gauges)
            total_points = len(self._metric_points)

            h_p95: dict[str, float] = {}
            for k, samples in self._histograms.items():
                if samples:
                    sorted_s = sorted(samples)
                    idx = math.ceil(0.95 * len(sorted_s)) - 1
                    h_p95[k] = round(sorted_s[max(0, idx)], 2)
                else:
                    h_p95[k] = 0.0

        return TelemetrySummary(
            total_metrics_recorded=total_points,
            counters=counters_copy,
            gauges=gauges_copy,
            histograms_p95_ms=h_p95,
        )

    def get_all_metric_points(self) -> list[MetricPoint]:
        """Returns a snapshot list of recorded MetricPoints.

        Returns:
            List of MetricPoint objects.
        """
        with self._lock:
            return list(self._metric_points)

    def clear(self) -> None:
        """Clears all counters, gauges, histograms, and metric points."""
        with self._lock:
            self._counters.clear()
            self._gauges.clear()
            self._histograms.clear()
            self._metric_points.clear()

    @staticmethod
    def _format_key(name: str, labels: dict[str, str]) -> str:
        if not labels:
            return name
        lbl_str = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
        return f"{name}{{{lbl_str}}}"

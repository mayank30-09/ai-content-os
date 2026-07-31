"""Example 04: Observability & Metrics Export.

Demonstrates initializing ObservabilityManager, creating traces, recording latency metrics, and extracting Prometheus format text.
"""

from modules.config import get_config
from modules.observability.manager import ObservabilityManager


def main() -> None:
    """Records telemetry samples and prints scrapable Prometheus metrics."""
    config = get_config()
    obs = ObservabilityManager(config=config)

    # 1. Create a distributed trace span
    span = obs.create_trace(
        name="example_workflow_span",
        correlation_id="corr_example_12345",
        metadata={"worker_id": "writer_worker", "workflow_id": "wf_demo"},
    )
    print(f"📊 Created Span: {span.name} [ID: {span.span_id}]")

    # 2. Record counter and histogram samples
    obs.record_metric("worker_execution_count", 1.0, labels={"worker": "writer_worker"})
    obs.record_metric("worker_latency_seconds", 0.42, labels={"worker": "writer_worker"})
    obs.record_metric("worker_latency_seconds", 0.88, labels={"worker": "writer_worker"})

    # 3. Export Prometheus scrapable text
    prom_output = obs.get_prometheus_metrics()
    print("\n--- Prometheus /metrics Scrapable Output Sample ---")
    print(prom_output[:300] if prom_output else "No metrics collected.")
    print("----------------------------------------------------\n")


if __name__ == "__main__":
    main()

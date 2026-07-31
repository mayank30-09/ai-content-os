# API Reference: Observability Subsystem (`modules.observability`)

Thread-safe distributed tracing, latency histograms (p95 math), counters, gauges, structured audit logging, and Prometheus scrapers.

---

## `ObservabilityManager`

```python
from modules.observability import ObservabilityManager

obs = ObservabilityManager(config=config)
```

### Methods

#### `create_trace(name: str, correlation_id: str) -> Span`
Creates a root trace span.

#### `record_metric(metric_name: str, value: float, labels: dict = None)`
Records a counter, gauge, or latency histogram sample.

#### `get_prometheus_metrics() -> str`
Generates Prometheus scrapable text format output for `/metrics`.

---

## ➡️ Next Reading

Read the **[Infrastructure API Reference](infrastructure.md)**.

# AI Content OS Examples 💡

This directory contains standalone, executable Python scripts demonstrating how to extend, configure, and run **AI Content OS**.

---

## Example Scripts Index

- **`01_basic_workflow.py`**: Submits a complete `WorkflowRequest` to `WorkflowEngine` and executes all 8 production AI workers from end to end.
- **`02_custom_worker.py`**: Implements a custom `TranslationWorker` with a Pydantic v2 output model and registers it with `WorkforceManager`.
- **`03_custom_template.py`**: Registers a custom DAG `WorkflowTemplate` that skips non-essential steps for rapid social media drafting.
- **`04_observability_export.py`**: Initializes `ObservabilityManager`, creates distributed trace spans, records latency metrics, and extracts scrapable Prometheus `/metrics`.

---

## 🏃 Running Examples

Set your Gemini API key and execute any script directly with `uv`:

```bash
export GEMINI_API_KEY="your_api_key_here"
uv run python examples/01_basic_workflow.py
```

# Developer Guide: Building Custom Workflows ⚡

Learn how to define custom DAG workflow templates for specific content creation pipelines.

---

## Defining a Fast-Track Workflow Template

Create a custom workflow template that executes a subset of production workers (e.g., skip Fact Checker for fast drafting):

```python
from modules.workflow.templates import WorkflowTemplate

fast_track_template = WorkflowTemplate(
    template_id="fast_track_pipeline",
    name="Fast-Track Article Generation",
    description="Executes Research -> Writer -> SEO -> Publisher",
    worker_dag=["research_worker", "writer_worker", "seo_worker", "publisher_worker"]
)
```

Submit a request referencing your template:

```python
request = WorkflowRequest(
    topic="Quick Tech News Announcement",
    template_id="fast_track_pipeline"
)
result = await engine.execute_workflow(request)
```

---

## ➡️ Next Reading

Learn how to configure syndication in the **[Multi-Platform Publishing Guide](publishing.md)**.

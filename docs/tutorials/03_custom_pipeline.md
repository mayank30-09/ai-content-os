# Tutorial 3: Building a Custom Fast-Track Pipeline 🚀

Learn how to define and run a custom lightweight pipeline for rapid social media drafting.

---

## Code Example

```python
import asyncio
from modules.config import get_config
from modules.workflow import WorkflowEngine, WorkflowRequest
from modules.workflow.templates import WorkflowTemplate

async def run_custom_pipeline_tutorial():
    config = get_config()
    engine = WorkflowEngine(config=config)
    
    # Define custom template skipping Fact Checker and Editor for speed
    fast_template = WorkflowTemplate(
        template_id="rapid_social",
        name="Rapid Social Drafting",
        worker_dag=["research_worker", "content_strategist_worker", "writer_worker", "publisher_worker"]
    )
    engine.register_template(fast_template)
    
    request = WorkflowRequest(
        topic="Breaking News in AI Agents",
        template_id="rapid_social",
        target_platforms=["twitter"]
    )
    
    result = await engine.execute_workflow(request)
    print(f"✅ Rapid Execution Status: {result.status}")

if __name__ == "__main__":
    asyncio.run(run_custom_pipeline_tutorial())
```

---

## ➡️ Next Reading

Return to the **[Documentation Map](../index.md)**.

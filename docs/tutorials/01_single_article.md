# Tutorial 1: Generating a Single SEO Article 📰

Learn how to execute a full 8-worker pipeline to research, write, fact-check, edit, optimize for SEO, and package a technical blog article.

---

## Code Example

```python
import asyncio
from modules.config import get_config
from modules.workflow import WorkflowEngine, WorkflowRequest

async def run_tutorial():
    config = get_config()
    engine = WorkflowEngine(config=config)
    
    request = WorkflowRequest(
        topic="High-Performance Asynchronous Python with UV",
        target_platforms=["blog"],
        tone="technical and authoritative",
        audience="Python Backend Engineers"
    )
    
    print(f"Executing workflow for: {request.topic}")
    result = await engine.execute_workflow(request)
    
    if result.status == "SUCCESS":
        print("✅ Article generation complete!")
        publication_package = result.artifacts["publication_package"]
        print(f"Meta Description: {publication_package['meta_description']}")
    else:
        print(f"❌ Workflow failed: {result.error_message}")

if __name__ == "__main__":
    asyncio.run(run_tutorial())
```

---

## ➡️ Next Tutorial

Proceed to **[Tutorial 2: Multi-Platform Syndication](02_multi_platform.md)**.

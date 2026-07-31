# Tutorial 2: Multi-Platform Syndication 🌐

Learn how to generate and distribute content simultaneously to LinkedIn, X (Twitter), and your CMS.

---

## Code Example

```python
import asyncio
from modules.config import get_config
from modules.workflow import WorkflowEngine, WorkflowRequest

async def run_multi_platform_tutorial():
    config = get_config()
    engine = WorkflowEngine(config=config)
    
    request = WorkflowRequest(
        topic="Launching AI Content OS v0.8.3",
        target_platforms=["linkedin", "twitter", "cms"],
        tone="engaging and professional",
        audience="Tech Community & Developers"
    )
    
    result = await engine.execute_workflow(request)
    package = result.artifacts["publication_package"]
    
    print("📢 Generated Platform Payloads:")
    for platform, payload in package["payloads"].items():
        print(f"[{platform.upper()}]: {payload['formatted_text'][:100]}...")

if __name__ == "__main__":
    asyncio.run(run_multi_platform_tutorial())
```

---

## ➡️ Next Tutorial

Proceed to **[Tutorial 3: Custom Fast-Track Pipeline](03_custom_pipeline.md)**.

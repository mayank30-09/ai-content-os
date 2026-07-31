# 5-Minute Quickstart Guide ⚡

This guide walks you through executing your first autonomous content workflow with **AI Content OS** in under 5 minutes.

---

## 📋 Prerequisites

- **Python**: 3.14+ installed.
- **Package Manager**: [`uv`](https://docs.astral.sh/uv/) (recommended) or `pip`.
- **API Key**: Google Gemini API key (`GEMINI_API_KEY`).

---

## 🛠️ Step-by-Step Instructions

### Step 1: Clone Repository & Install Dependencies
```bash
git clone https://github.com/mayank30-09/ai-content-os.git
cd ai-content-os
uv sync
```

### Step 2: Configure Environment Variables
Copy the template `.env` file or export your Gemini API key:
```bash
export GEMINI_API_KEY="AIzaSyYourSecretGeminiApiKeyHere"
export APP_ENV="development"
export LOG_LEVEL="INFO"
```

### Step 3: Execute Your First Content Workflow
Run a python snippet to submit a `WorkflowRequest` to `WorkflowEngine`:

```python
import asyncio
from modules.config import get_config
from modules.workflow import WorkflowEngine, WorkflowRequest

async def main():
    config = get_config()
    engine = WorkflowEngine(config=config)
    
    request = WorkflowRequest(
        topic="Autonomous AI Agents in Enterprise Systems",
        target_platforms=["linkedin", "twitter", "blog"],
        tone="professional",
        audience="Software Architects and CTOs"
    )
    
    print(f"🚀 Launching Workflow: {request.topic}")
    result = await engine.execute_workflow(request)
    
    print(f"✅ Workflow Status: {result.status}")
    print(f"📦 Generated Artifacts: {list(result.artifacts.keys())}")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## ➡️ Next Reading

Learn more about full installation options in the **[Installation Guide](installation.md)** or explore system design in the **[Architecture Overview](architecture/overview.md)**.

"""Example 01: Basic Workflow Execution.

Demonstrates submitting a WorkflowRequest to WorkflowEngine and executing the full 8-worker DAG pipeline.
"""

import asyncio

from modules.config import get_config
from modules.workflow.engine import WorkflowEngine
from modules.workflow.models import WorkflowRequest


async def main() -> None:
    """Executes a basic single-topic workflow."""
    config = get_config()
    engine = WorkflowEngine(config=config)

    request = WorkflowRequest(
        topic="Autonomous AI Workforce Orchestration in Python 3.14",
        target_platforms=["linkedin", "twitter", "blog"],
        tone="professional and technical",
        audience="Software Architects and Senior Engineers",
    )

    print(f"🚀 Executing Workflow for topic: {request.topic}")
    result = await engine.execute_workflow(request)

    print(f"✅ Workflow Status: {result.status}")
    print(f"📦 Execution ID: {result.execution_id}")
    print(f"📊 Produced Artifact Keys: {list(result.artifacts.keys())}")


if __name__ == "__main__":
    asyncio.run(main())

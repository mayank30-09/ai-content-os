"""Example 03: Custom DAG Workflow Template.

Demonstrates registering a custom WorkflowTemplate for rapid drafting.
"""

import asyncio

from modules.config import get_config
from modules.workflow.engine import WorkflowEngine
from modules.workflow.models import WorkflowRequest
from modules.workflow.templates import WorkflowTemplate


async def main() -> None:
    """Registers a fast-track workflow template and runs a request."""
    config = get_config()
    engine = WorkflowEngine(config=config)

    # Register custom template with customized worker DAG
    fast_template = WorkflowTemplate(
        template_id="fast_track_social",
        name="Fast-Track Social Drafting",
        description="Executes Research -> Strategist -> Writer -> Publisher",
        worker_dag=[
            "research_worker",
            "content_strategist_worker",
            "writer_worker",
            "publisher_worker",
        ],
    )
    engine.register_template(fast_template)

    request = WorkflowRequest(
        topic="Rapid Announcement in AI Tech",
        template_id="fast_track_social",
        target_platforms=["twitter"],
    )

    print(f"🚀 Submitting custom template request: {request.template_id}")
    result = await engine.execute_workflow(request)
    print(f"✅ Fast-Track Workflow Status: {result.status}")


if __name__ == "__main__":
    asyncio.run(main())

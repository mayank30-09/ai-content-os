import pytest

from modules.memory.repositories import content_repo
from modules.orchestration.tasks import task_research


@pytest.mark.asyncio
async def test_task_research_step():
    content_id = content_repo.create(topic="Python Async Microservices", format_type="multi_format")
    context = {
        "content_id": content_id,
        "topic": "Python Async Microservices",
        "sources": ["Python Async Microservices"]
    }

    updated_ctx = await task_research(context)
    assert "research_summary" in updated_ctx
    assert len(updated_ctx["research_summary"]) > 0

    item = content_repo.get_by_id(content_id)
    assert item["state"] == "RESEARCHED"

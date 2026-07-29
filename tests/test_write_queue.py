import pytest

from modules.memory.repositories import content_repo


@pytest.mark.asyncio
async def test_async_write_queue():
    content_id = await content_repo.create_async(
        topic="Async Write Queue Validation",
        format_type="reels"
    )
    assert content_id is not None

    item = content_repo.get_by_id(content_id)
    assert item["topic"] == "Async Write Queue Validation"

    await content_repo.update_research_async(content_id, "Async research summary")
    item = content_repo.get_by_id(content_id)
    assert item["state"] == "RESEARCHED"
    assert item["research_summary"] == "Async research summary"

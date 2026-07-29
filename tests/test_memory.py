from modules.memory.repositories import content_repo, knowledge_repo


def test_content_repository_lifecycle():
    # 1. Create content item
    content_id = content_repo.create(topic="Test Architecture Topic", format_type="multi_format")
    assert content_id is not None

    item = content_repo.get_by_id(content_id)
    assert item["topic"] == "Test Architecture Topic"
    assert item["state"] == "INITIATED"
    assert item["is_human_approved"] == 0

    # 2. Update research
    content_repo.update_research(content_id, "Sample Research Data")
    item = content_repo.get_by_id(content_id)
    assert item["state"] == "RESEARCHED"
    assert item["research_summary"] == "Sample Research Data"

    # 3. Update AI output
    content_repo.update_ai_outputs(
        content_id=content_id,
        ai_raw_output="Raw AI Output Text",
        reels_script="Reel Script Text",
        carousel_json='{"slides": []}'
    )
    item = content_repo.get_by_id(content_id)
    assert item["state"] == "PENDING_APPROVAL"
    assert item["ai_raw_output"] == "Raw AI Output Text"

    # 4. Set approval gate
    content_repo.set_approval(content_id, is_approved=True)
    item = content_repo.get_by_id(content_id)
    assert item["state"] == "APPROVED"
    assert item["is_human_approved"] == 1

def test_knowledge_repository_fts():
    kb_id = knowledge_repo.add(
        title="Playwright Stealth Best Practices",
        source_type="web",
        url="https://example.com/stealth",
        content_body="How to avoid bot detection using Playwright and Chromium flags.",
        tags="playwright,stealth"
    )
    assert kb_id is not None

    # Search full text index
    results = knowledge_repo.search("Playwright")
    assert len(results) > 0
    assert results[0]["title"] == "Playwright Stealth Best Practices"

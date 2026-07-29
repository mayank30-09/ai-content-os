import logging
from typing import Any

from modules.ai.gemini_web import GeminiWebProvider
from modules.ai.prompt_templates import prompt_library
from modules.memory.repositories import content_repo, logger_repo
from modules.research.registry import research_registry

logger = logging.getLogger("AIContentOS.OrchestratorTasks")

async def task_research(context: dict[str, Any]) -> dict[str, Any]:
    content_id = context["content_id"]
    topic = context["topic"]
    sources = context.get("sources", [topic])

    logger.info(f"[Task Research] Gathering research for content_id: {content_id}")
    logger_repo.log(content_id, "RESEARCH", "INFO", f"Starting research for topic: {topic}")

    research_summary = await research_registry.gather_research(sources)
    content_repo.update_research(content_id, research_summary)

    context["research_summary"] = research_summary
    logger_repo.log(content_id, "RESEARCH", "SUCCESS", "Research completed and saved.")
    return context

async def task_generate_content(context: dict[str, Any]) -> dict[str, Any]:
    content_id = context["content_id"]
    topic = context["topic"]
    research_summary = context.get("research_summary", "")

    logger.info(f"[Task AI Generate] Generating multi-format content for content_id: {content_id}")
    logger_repo.log(content_id, "AI_GENERATE", "INFO", "Sending prompt to Gemini Web Adapter")

    provider = GeminiWebProvider()

    # 1. Render Carousel Prompt
    carousel_prompt = prompt_library.render_carousel_prompt(topic, research_summary)
    ai_raw_output = await provider.generate(carousel_prompt)

    # 2. Render Reels Prompt
    reels_prompt = prompt_library.render_reels_prompt(topic, research_summary)
    reels_output = await provider.generate(reels_prompt)

    # Save to SQLite repo (State updates to PENDING_APPROVAL)
    content_repo.update_ai_outputs(
        content_id=content_id,
        ai_raw_output=ai_raw_output,
        reels_script=reels_output,
        carousel_json=ai_raw_output
    )

    logger_repo.log(content_id, "AI_GENERATE", "SUCCESS", "Content generated and placed in PENDING_APPROVAL gate.")
    context["state"] = "PENDING_APPROVAL"
    return context

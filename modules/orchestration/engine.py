import logging
from collections.abc import Callable

from modules.memory.repositories import content_repo, logger_repo
from modules.orchestration.tasks import task_generate_content, task_research

logger = logging.getLogger("AIContentOS.AgentOrchestrator")

class PipelineStep:
    def __init__(self, name: str, handler: Callable):
        self.name = name
        self.handler = handler

class AgentOrchestrator:
    def __init__(self):
        self.pipeline: list[PipelineStep] = [
            PipelineStep("Research", task_research),
            PipelineStep("AI Generation", task_generate_content)
        ]

    async def run_content_pipeline(self, topic: str, format_type: str = "multi_format", sources: list[str] = None) -> str:
        # Create content record in SQLite
        content_id = content_repo.create(topic=topic, format_type=format_type)
        context = {
            "content_id": content_id,
            "topic": topic,
            "format_type": format_type,
            "sources": sources or [topic]
        }

        logger.info(f"Starting Agent Pipeline for content_id: {content_id}")
        logger_repo.log(content_id, "PIPELINE", "INFO", f"Pipeline initiated for topic: {topic}")

        try:
            for step in self.pipeline:
                logger.info(f"Executing pipeline step: {step.name}")
                context = await step.handler(context)

            logger.info(f"Pipeline execution completed. Item {content_id} awaiting human approval.")
            return content_id
        except Exception as e:
            logger.error(f"Pipeline execution failed for content_id {content_id}: {e}")
            logger_repo.log(content_id, "PIPELINE", "ERROR", f"Pipeline failed: {str(e)}")
            raise e

orchestrator = AgentOrchestrator()

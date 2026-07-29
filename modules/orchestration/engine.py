"""Agent orchestrator DAG engine module for AI Content OS.

Coordinates multi-step pipeline execution (Research -> Synthesis -> Generation -> Approval).
"""

from collections.abc import Callable

from loguru import logger

from modules.memory.repositories import content_repo, logger_repo
from modules.orchestration.tasks import task_generate_content, task_research


class PipelineStep:
    """Represents a single atomic step in an orchestrator DAG pipeline."""

    def __init__(self, name: str, handler: Callable):
        self.name: str = name
        self.handler: Callable = handler

class AgentOrchestrator:
    """DAG pipeline runner coordinating execution order and state updates."""

    def __init__(self):
        self.pipeline: list[PipelineStep] = [
            PipelineStep("Research", task_research),
            PipelineStep("AI Generation", task_generate_content),
        ]

    async def run_content_pipeline(
        self,
        topic: str,
        format_type: str = "multi_format",
        sources: list[str] = None
    ) -> str:
        """Runs complete content creation pipeline for a given topic."""
        content_id = content_repo.create(topic=topic, format_type=format_type)
        context = {
            "content_id": content_id,
            "topic": topic,
            "format_type": format_type,
            "sources": sources or [topic],
        }

        logger.info(f"Starting Agent Pipeline for content_id: '{content_id}'")
        logger_repo.log(content_id, "PIPELINE", "INFO", f"Pipeline initiated for topic: {topic}")

        try:
            for step in self.pipeline:
                logger.info(f"Executing pipeline step: '{step.name}'")
                context = await step.handler(context)

            logger.info(f"Pipeline execution completed. Content ID '{content_id}' awaiting human approval.")
            return content_id
        except Exception as e:
            logger.error(f"Pipeline execution failed for content_id '{content_id}': {e}")
            logger_repo.log(content_id, "PIPELINE", "ERROR", f"Pipeline failed: {str(e)}")
            raise e

orchestrator = AgentOrchestrator()

"""Research strategy factory and selector module."""

from loguru import logger

from modules.workforce.models import Task
from modules.workforce.workers.strategies import (
    BaseResearchStrategy,
    CommunityResearchStrategy,
    GeneralResearchStrategy,
    MediaResearchStrategy,
    TechnicalResearchStrategy,
)


class ResearchStrategyFactory:
    """Factory selecting research strategy based on task payload and topic metadata."""

    @staticmethod
    def get_strategy(task: Task) -> BaseResearchStrategy:
        """Selects research strategy based on explicit metadata or topic heuristics.

        Args:
            task: Task specification.

        Returns:
            BaseResearchStrategy: Selected strategy instance.
        """
        payload = task.payload or {}
        explicit_strategy = payload.get("strategy", "").lower()

        if explicit_strategy == "technical":
            return TechnicalResearchStrategy()
        elif explicit_strategy == "community":
            return CommunityResearchStrategy()
        elif explicit_strategy == "media":
            return MediaResearchStrategy()
        elif explicit_strategy == "general":
            return GeneralResearchStrategy()

        # Keyword heuristics
        query = str(payload.get("topic", payload.get("query", ""))).lower()
        tech_keywords = {"code", "python", "fastapi", "github", "api", "framework", "library", "architecture", "bug"}
        community_keywords = {"reddit", "discussion", "opinion", "review", "community", "sentiment"}
        media_keywords = {"youtube", "video", "transcript", "tutorial", "reels"}

        if any(kw in query for kw in tech_keywords):
            logger.info("Auto-selected TechnicalResearchStrategy based on query keywords.")
            return TechnicalResearchStrategy()
        elif any(kw in query for kw in community_keywords):
            logger.info("Auto-selected CommunityResearchStrategy based on query keywords.")
            return CommunityResearchStrategy()
        elif any(kw in query for kw in media_keywords):
            logger.info("Auto-selected MediaResearchStrategy based on query keywords.")
            return MediaResearchStrategy()

        logger.info("Auto-selected default GeneralResearchStrategy.")
        return GeneralResearchStrategy()

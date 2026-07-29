"""Community research strategy implementation."""

from typing import Any

from modules.workforce.models import Task
from modules.workforce.workers.strategies.base_strategy import BaseResearchStrategy


class CommunityResearchStrategy(BaseResearchStrategy):
    """Community discussion and sentiment research strategy via Reddit and Web."""

    def __init__(self):
        super().__init__(
            strategy_name="Community Research Strategy",
            required_plugins=["web", "reddit"],
            max_results=8
        )

    def configure(self, task: Task) -> dict[str, Any]:
        topic = task.payload.get("topic", task.payload.get("query", "Community Discussion"))
        return {
            "query": f"{topic} opinion discussion review",
            "enabled_plugins": self.required_plugins,
            "max_results_per_plugin": self.max_results
        }

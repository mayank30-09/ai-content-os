"""Technical research strategy implementation."""

from typing import Any

from modules.workforce.models import Task
from modules.workforce.workers.strategies.base_strategy import BaseResearchStrategy


class TechnicalResearchStrategy(BaseResearchStrategy):
    """Deep technical research strategy utilizing GitHub, Web, and Technical Documentation."""

    def __init__(self):
        super().__init__(
            strategy_name="Technical Research Strategy",
            required_plugins=["web", "github", "documentation"],
            max_results=8
        )

    def configure(self, task: Task) -> dict[str, Any]:
        topic = task.payload.get("topic", task.payload.get("query", "Technical Topic"))
        return {
            "query": f"{topic} architecture framework library",
            "enabled_plugins": self.required_plugins,
            "max_results_per_plugin": self.max_results
        }

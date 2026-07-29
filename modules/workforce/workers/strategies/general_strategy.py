"""General research strategy implementation."""

from typing import Any

from modules.workforce.models import Task
from modules.workforce.workers.strategies.base_strategy import BaseResearchStrategy


class GeneralResearchStrategy(BaseResearchStrategy):
    """Broad web research strategy across general sources."""

    def __init__(self):
        super().__init__(
            strategy_name="General Research Strategy",
            required_plugins=["web"],
            max_results=10
        )

    def configure(self, task: Task) -> dict[str, Any]:
        topic = task.payload.get("topic", task.payload.get("query", "General Topic"))
        return {
            "query": topic,
            "enabled_plugins": self.required_plugins,
            "max_results_per_plugin": self.max_results
        }

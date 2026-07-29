"""Media research strategy implementation."""

from typing import Any

from modules.workforce.models import Task
from modules.workforce.workers.strategies.base_strategy import BaseResearchStrategy


class MediaResearchStrategy(BaseResearchStrategy):
    """Video and multimedia transcript research strategy via YouTube and Web."""

    def __init__(self):
        super().__init__(
            strategy_name="Media Research Strategy",
            required_plugins=["web", "youtube"],
            max_results=6
        )

    def configure(self, task: Task) -> dict[str, Any]:
        topic = task.payload.get("topic", task.payload.get("query", "Video Topic"))
        return {
            "query": f"{topic} tutorial breakdown video",
            "enabled_plugins": self.required_plugins,
            "max_results_per_plugin": self.max_results
        }

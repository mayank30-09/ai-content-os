"""Base research strategy abstract module."""

from abc import ABC, abstractmethod
from typing import Any

from modules.workforce.models import Task


class BaseResearchStrategy(ABC):
    """Abstract interface contract for specialized research strategies."""

    def __init__(self, strategy_name: str, required_plugins: list[str], max_results: int = 5):
        self.strategy_name: str = strategy_name
        self.required_plugins: list[str] = required_plugins
        self.max_results: int = max_results

    @abstractmethod
    def configure(self, task: Task) -> dict[str, Any]:
        """Configures strategy parameters based on task payload.

        Args:
            task: Assigned Task specification.

        Returns:
            Dict[str, Any]: Execution arguments for ResearchManager.
        """
        pass

from abc import ABC, abstractmethod
from typing import Any


class BaseResearchPlugin(ABC):
    @property
    @abstractmethod
    def source_name(self) -> str:
        """Source name identifier (e.g. 'web', 'youtube', 'reddit', 'github')."""
        pass

    @abstractmethod
    async def can_handle(self, target: str) -> bool:
        """Determines if this plugin handles the target URL or query type."""
        pass

    @abstractmethod
    async def extract_content(self, target: str) -> dict[str, Any]:
        """Extracts clean text context, title, and metadata."""
        pass

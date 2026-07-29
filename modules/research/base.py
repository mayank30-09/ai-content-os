"""Base research plugin module for Research Engine.

Defines abstract interface for all concrete research plugins (Web, GitHub, Reddit, YouTube, Docs).
"""

from abc import ABC, abstractmethod
from typing import Any

from modules.research.models import PluginMetadata, ResearchDocument


class BaseResearchPlugin(ABC):
    """Abstract base class contract for research plugins."""

    def __init__(self, metadata: PluginMetadata):
        self.metadata: PluginMetadata = metadata

    @property
    def plugin_id(self) -> str:
        """Returns unique plugin identifier ID."""
        return self.metadata.plugin_id

    @property
    def name(self) -> str:
        """Returns unique plugin name."""
        return self.metadata.name

    @property
    def version(self) -> str:
        """Returns plugin version string."""
        return self.metadata.version

    @property
    def enabled(self) -> bool:
        """Returns whether plugin is enabled."""
        return self.metadata.enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        """Sets plugin enabled flag."""
        self.metadata.enabled = value

    @abstractmethod
    async def can_handle(self, target: str) -> bool:
        """Determines if this plugin can handle the given target URL or query string.

        Args:
            target: Input URL or search query string.

        Returns:
            bool: True if plugin handles target, False otherwise.
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Verifies plugin readiness and connectivity.

        Returns:
            bool: True if healthy, False otherwise.
        """
        pass

    @abstractmethod
    async def execute(
        self, query: str, options: dict[str, Any] | None = None
    ) -> list[ResearchDocument]:
        """Asynchronously executes research gathering for query and returns documents.

        Args:
            query: Input topic or URL search string.
            options: Optional execution options.

        Returns:
            List[ResearchDocument]: Extracted research documents.
        """
        pass

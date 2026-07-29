"""Plugin registry module for Research Engine.

Manages dynamic registration, enabling, disabling, discovery, and health checks
for research plugins.
"""


from loguru import logger

from modules.research.base import BaseResearchPlugin
from modules.research.plugins.docs_plugin import DocumentationPlugin
from modules.research.plugins.github_plugin import GitHubPlugin
from modules.research.plugins.reddit_plugin import RedditPlugin
from modules.research.plugins.web_plugin import WebPlugin
from modules.research.plugins.youtube_plugin import YouTubePlugin


class PluginRegistry:
    """Central registry managing research plugins and their lifecycles."""

    def __init__(self, register_defaults: bool = False):
        self._plugins: dict[str, BaseResearchPlugin] = {}
        if register_defaults:
            self.register(WebPlugin())
            self.register(GitHubPlugin())
            self.register(RedditPlugin())
            self.register(YouTubePlugin())
            self.register(DocumentationPlugin())

    def register(self, plugin: BaseResearchPlugin) -> None:
        """Registers a research plugin in the registry.

        Args:
            plugin: BaseResearchPlugin instance to register.
        """
        if plugin.name in self._plugins:
            logger.warning(f"Overwriting existing registered plugin: '{plugin.name}'")
        self._plugins[plugin.name] = plugin
        logger.info(f"Registered research plugin: '{plugin.name}' [Source: {plugin.metadata.source_type}]")

    def unregister(self, name: str) -> BaseResearchPlugin | None:
        """Unregisters and returns plugin by name.

        Args:
            name: Name of plugin to unregister.

        Returns:
            Optional[BaseResearchPlugin]: Removed plugin instance or None if not found.
        """
        plugin = self._plugins.pop(name, None)
        if plugin:
            logger.info(f"Unregistered research plugin: '{name}'")
        else:
            logger.warning(f"Plugin '{name}' not found for unregistration.")
        return plugin

    def enable(self, name: str) -> bool:
        """Enables a registered plugin by name.

        Args:
            name: Plugin identifier name.

        Returns:
            bool: True if plugin was found and enabled, False otherwise.
        """
        plugin = self._plugins.get(name)
        if plugin:
            plugin.enabled = True
            logger.info(f"Enabled research plugin: '{name}'")
            return True
        logger.warning(f"Cannot enable missing plugin: '{name}'")
        return False

    def disable(self, name: str) -> bool:
        """Disables a registered plugin by name.

        Args:
            name: Plugin identifier name.

        Returns:
            bool: True if plugin was found and disabled, False otherwise.
        """
        plugin = self._plugins.get(name)
        if plugin:
            plugin.enabled = False
            logger.info(f"Disabled research plugin: '{name}'")
            return True
        logger.warning(f"Cannot disable missing plugin: '{name}'")
        return False

    def get_plugin(self, name: str) -> BaseResearchPlugin | None:
        """Gets a plugin instance by name.

        Args:
            name: Plugin identifier name.

        Returns:
            Optional[BaseResearchPlugin]: Plugin instance if found, None otherwise.
        """
        return self._plugins.get(name)

    def discover(self) -> list[str]:
        """Discovers and returns all registered plugin names."""
        return list(self._plugins.keys())

    def get_active_plugins(self) -> list[BaseResearchPlugin]:
        """Returns list of all currently enabled plugins."""
        return [p for p in self._plugins.values() if p.enabled]

    async def run_health_checks(self) -> dict[str, bool]:
        """Runs health checks on all registered plugins and returns health status dictionary."""
        statuses = {}
        for name, plugin in self._plugins.items():
            try:
                is_healthy = await plugin.health_check()
                statuses[name] = is_healthy
                logger.debug(f"Plugin health check '{name}': {'HEALTHY' if is_healthy else 'UNHEALTHY'}")
            except Exception as e:
                logger.error(f"Health check error for plugin '{name}': {e}")
                statuses[name] = False
        return statuses

# Global singleton populated with standard defaults
plugin_registry = PluginRegistry(register_defaults=True)

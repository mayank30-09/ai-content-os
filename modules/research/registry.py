import logging

from modules.research.base import BaseResearchPlugin
from modules.research.web_plugin import WebResearchPlugin

logger = logging.getLogger("AIContentOS.ResearchRegistry")

class ResearchRegistry:
    def __init__(self):
        self.plugins: list[BaseResearchPlugin] = []
        # Register default plugins
        self.register(WebResearchPlugin())

    def register(self, plugin: BaseResearchPlugin):
        self.plugins.append(plugin)
        logger.info(f"Registered Research Plugin: {plugin.source_name}")

    async def gather_research(self, topic_or_urls: list[str]) -> str:
        """Runs appropriate research plugins on inputs and aggregates text summary."""
        aggregated_results = []
        for item in topic_or_urls:
            handled = False
            for plugin in self.plugins:
                if await plugin.can_handle(item):
                    res = await plugin.extract_content(item)
                    aggregated_results.append(
                        f"--- SOURCE [{res['source'].upper()}]: {res.get('title', item)} ---\n"
                        f"URL: {res.get('url', '')}\n"
                        f"CONTENT:\n{res.get('content_body', '')}\n"
                    )
                    handled = True
                    break
            if not handled:
                aggregated_results.append(f"--- KEYWORD TOPIC ---:\n{item}")

        return "\n\n".join(aggregated_results)

research_registry = ResearchRegistry()

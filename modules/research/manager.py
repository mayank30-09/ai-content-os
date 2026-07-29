"""Research manager module for Research Engine.

Coordinates parallel research plugin execution, timeout guards, task cancellation,
aggregation, deduplication, ranking, and packaging.
"""

import asyncio
import contextlib
import time
from typing import Any

from loguru import logger

from modules.research.aggregator import Aggregator, aggregator
from modules.research.deduplicator import Deduplicator, deduplicator
from modules.research.models import ResearchDocument, ResearchPackage
from modules.research.ranker import Ranker, ranker
from modules.research.registry import PluginRegistry, plugin_registry
from modules.research.summarizer import Summarizer, summarizer


class ResearchManager:
    """Orchestrates multi-plugin parallel research tasks and outputs ResearchPackages."""

    def __init__(
        self,
        registry: PluginRegistry = plugin_registry,
        aggregator_inst: Aggregator = aggregator,
        deduplicator_inst: Deduplicator = deduplicator,
        ranker_inst: Ranker = ranker,
        summarizer_inst: Summarizer = summarizer,
    ):
        self.registry = registry
        self.aggregator = aggregator_inst
        self.deduplicator = deduplicator_inst
        self.ranker = ranker_inst
        self.summarizer = summarizer_inst

    async def _safe_execute_plugin(
        self, plugin: Any, query: str, options: dict[str, Any]
    ) -> list[ResearchDocument]:
        """Safely executes a single plugin with exception isolation."""
        try:
            if not await plugin.can_handle(query):
                logger.debug(f"Plugin '{plugin.name}' cannot handle query/url: '{query}'")
                return []
            logger.info(f"Executing plugin '{plugin.name}'...")
            docs = await plugin.execute(query, options)
            logger.info(f"Plugin '{plugin.name}' returned {len(docs)} documents.")
            return docs
        except Exception as e:
            logger.error(f"Plugin '{plugin.name}' failed execution: {e}")
            return []

    async def conduct_research(
        self,
        query: str,
        timeout_sec: float = 15.0,
        options: dict[str, Any] | None = None,
    ) -> ResearchPackage:
        """Runs parallel research across active plugins and produces a ResearchPackage.

        Args:
            query: User topic or target URL search query.
            timeout_sec: Maximum timeout in seconds for parallel execution.
            options: Execution flags and options.

        Returns:
            ResearchPackage: Synthesized research output package.
        """
        start_time = time.perf_counter()
        active_plugins = self.registry.get_active_plugins()
        opts = options or {}

        logger.info(f"Starting research for query: '{query}' across {len(active_plugins)} active plugins.")

        if not active_plugins:
            logger.warning("No active research plugins found in registry.")
            return self.summarizer.build_package(query, [], {"duration_sec": 0.0, "plugins_run": 0})

        # Wrap coroutines in explicit asyncio.Task instances for execution tracking
        task_objs = [
            asyncio.create_task(self._safe_execute_plugin(plugin, query, opts))
            for plugin in active_plugins
        ]

        plugin_results = []
        try:
            # Enforce global timeout guard across tasks
            gathered = await asyncio.wait_for(
                asyncio.gather(*task_objs, return_exceptions=True),
                timeout=timeout_sec
            )
            plugin_results = list(gathered)
        except TimeoutError:
            logger.warning(f"Research execution timed out after {timeout_sec}s. Gathering partial completed results...")
            for task in task_objs:
                if task.done() and not task.cancelled():
                    with contextlib.suppress(Exception):
                        plugin_results.append(task.result())
                elif not task.done():
                    task.cancel()

        # Filter out exception objects from return_exceptions
        clean_results: list[list[ResearchDocument]] = [
            res for res in plugin_results if isinstance(res, list)
        ]

        # 1. Aggregate
        aggregated_docs = self.aggregator.aggregate(clean_results)

        # 2. Deduplicate
        unique_docs = self.deduplicator.deduplicate(aggregated_docs)

        # 3. Rank
        ranked_docs = self.ranker.rank(unique_docs, query)

        duration = round(time.perf_counter() - start_time, 3)
        metrics = {
            "duration_sec": duration,
            "plugins_run": len(active_plugins),
            "raw_documents_count": len(aggregated_docs),
            "unique_documents_count": len(ranked_docs),
        }

        # 4. Summarize & Build Package
        package = self.summarizer.build_package(query, ranked_docs, metrics)
        logger.info(f"Research completed in {duration}s for query: '{query}'")
        return package

research_manager = ResearchManager()

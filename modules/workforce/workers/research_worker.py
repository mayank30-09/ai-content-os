"""Production Research Worker implementation for AI Workforce Core.

Performs multi-source topic research, source quality auditing, citation tracking,
and automated long-term memory persistence.
"""

import time

from loguru import logger

from modules.memory.manager import MemoryManager, memory_manager
from modules.memory.models import KnowledgeMemory, ResearchMemory
from modules.research.manager import ResearchManager, research_manager
from modules.research.models import ResearchPackage
from modules.workforce.base_worker import BaseWorker
from modules.workforce.bus import MessageBus, message_bus
from modules.workforce.context import SharedContext
from modules.workforce.models import Task, TaskResult, TaskStatus, WorkerState
from modules.workforce.workers.quality import QualityValidator
from modules.workforce.workers.research_strategy import ResearchStrategyFactory


class ResearchWorker(BaseWorker):
    """Production AI Worker for autonomous multi-channel topic research."""

    def __init__(
        self,
        worker_id: str = "worker_research_prod",
        research_mgr: ResearchManager | None = None,
        memory_mgr: MemoryManager | None = None,
        bus: MessageBus | None = None,
    ):
        super().__init__(
            worker_id=worker_id,
            worker_name="Production Research Worker",
            role="Research Specialist",
            capabilities=["research", "web_search", "github", "reddit", "youtube", "documentation"],
        )
        self.research_manager: ResearchManager = research_mgr or research_manager
        self.memory_manager: MemoryManager = memory_mgr or memory_manager
        self.bus: MessageBus = bus or message_bus
        self.quality_validator: QualityValidator = QualityValidator()

    async def initialize(self) -> bool:
        """Initializes ResearchWorker and transitions state to READY."""
        self.state = WorkerState.READY
        logger.info(f"Initialized Production ResearchWorker '{self.worker_id}' [Role: {self.role}]")
        return True

    async def execute(self, task: Task, context: SharedContext) -> TaskResult:
        """Executes autonomous research task pipeline.

        Args:
            task: Task specification.
            context: SharedContext payload.

        Returns:
            TaskResult: Standardized result containing ResearchPackage and citations.
        """
        start_time = time.perf_counter()
        query = task.payload.get("topic", task.payload.get("query", "General Research"))
        logger.info(f"ResearchWorker '{self.worker_id}' executing task '{task.id}' for query: '{query}'")

        await self._safe_emit_event("ResearchStarted", {"task_id": task.id, "query": query})

        try:
            # 1. Strategy Selection
            strategy = ResearchStrategyFactory.get_strategy(task)
            strat_config = strategy.configure(task)
            logger.info(f"Using research strategy '{strategy.strategy_name}' for query '{query}'")

            # 2. Research Engine Execution
            package: ResearchPackage = await self.research_manager.conduct_research(
                query=strat_config["query"],
                options={
                    "enabled_plugins": strat_config.get("enabled_plugins"),
                    "max_results_per_plugin": strat_config.get("max_results_per_plugin", 5),
                },
            )

            # 3. Quality Auditing & Citation Building
            citations, avg_quality = self.quality_validator.validate_and_filter(package.ranked_documents)

            # 4. Memory Manager Persistence
            res_mem_id = None
            knw_mem_ids: list[str] = []

            if package.ranked_documents:
                # Save ResearchMemory
                res_record = ResearchMemory(
                    query=query,
                    content=package.executive_summary or f"Research summary for {query}",
                    key_facts=package.key_facts,
                    source_urls=[c.url for c in citations],
                )
                res_mem_id = self.memory_manager.store_memory(res_record)

                # Save KnowledgeMemory for high-authority citations (authority_score >= 0.8)
                high_auth_citations = [
                    c for c in citations
                    if c.authority_score >= self.quality_validator.quality_model.high_authority_threshold
                ]
                for c in high_auth_citations:
                    knw_record = KnowledgeMemory(
                        entity_name=c.title,
                        category=c.source_type,
                        content=f"Verified knowledge from {c.domain}: {c.title}. URL: {c.url}",
                        tags=[c.source_type, c.domain],
                        claims=[c.title],
                    )
                    k_id = self.memory_manager.store_memory(knw_record)
                    knw_mem_ids.append(k_id)

                await self._safe_emit_event(
                    "ResearchStored",
                    {"task_id": task.id, "research_memory_id": res_mem_id, "knowledge_count": len(knw_mem_ids)},
                )

            duration = round(time.perf_counter() - start_time, 3)

            # 5. Compile TaskResult
            artifacts = {
                "package": package.model_dump(mode="json"),
                "citations": [c.model_dump(mode="json") for c in citations],
                "quality_score": avg_quality,
                "memory_references": {
                    "research_memory_id": res_mem_id,
                    "knowledge_memory_ids": knw_mem_ids,
                },
            }

            metrics = {
                "sources_found": len(package.ranked_documents),
                "sources_used": len(citations),
                "high_authority_sources": len(knw_mem_ids),
                "average_source_quality": avg_quality,
                "execution_time": duration,
            }

            await self._safe_emit_event(
                "ResearchCompleted", {"task_id": task.id, "quality_score": avg_quality, "sources": len(citations)}
            )

            return TaskResult(
                task_id=task.id,
                worker_id=self.worker_id,
                status=TaskStatus.COMPLETED,
                execution_time=duration,
                artifacts=artifacts,
                logs=[f"Research completed successfully for '{query}' with {len(citations)} citations."],
                metrics=metrics,
            )

        except Exception as e:
            duration = round(time.perf_counter() - start_time, 3)
            logger.error(f"ResearchWorker exception for task '{task.id}': {e}")
            await self._safe_emit_event("ResearchFailed", {"task_id": task.id, "error": str(e)})

            return TaskResult(
                task_id=task.id,
                worker_id=self.worker_id,
                status=TaskStatus.FAILED,
                execution_time=duration,
                error=str(e),
                logs=[f"Research failed: {e}"],
            )

    async def _safe_emit_event(self, event_type: str, data: dict) -> None:
        """Safely emits workforce events over MessageBus."""
        try:
            await self.bus.emit_event(event_type, self.worker_id, data)
        except Exception as e:
            logger.error(f"Event emission exception: {e}")

    async def shutdown(self) -> bool:
        """Shuts down ResearchWorker."""
        self.state = WorkerState.STOPPED
        logger.info(f"Shutdown Production ResearchWorker '{self.worker_id}'")
        return True

    async def health_check(self) -> bool:
        """Audits worker health."""
        return self.state != WorkerState.STOPPED

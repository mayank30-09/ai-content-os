"""Production Memory Worker implementation for AI Workforce Core subsystem.

Performs cross-namespace memory analysis, deduplication, promotion rules evaluation,
TTL pruning, and role-tailored ContextPackage optimization.
"""

import time

from loguru import logger

from modules.memory.manager import MemoryManager, memory_manager
from modules.memory.models import ContextPackage
from modules.research.models import ResearchPackage
from modules.workforce.base_worker import BaseWorker
from modules.workforce.bus import MessageBus, message_bus
from modules.workforce.context import SharedContext
from modules.workforce.models import Task, TaskResult, TaskStatus, WorkerState
from modules.workforce.workers.context_optimizer import ContextOptimizer
from modules.workforce.workers.memory_analyzer import MemoryAnalyzer


class MemoryWorker(BaseWorker):
    """Production AI Worker for knowledge management, deduplication, and context optimization."""

    def __init__(
        self,
        worker_id: str = "worker_memory_prod",
        memory_mgr: MemoryManager | None = None,
        bus: MessageBus | None = None,
    ):
        super().__init__(
            worker_id=worker_id,
            worker_name="Production Memory Worker",
            role="Knowledge Manager",
            capabilities=["memory_management", "knowledge_promotion", "context_building", "deduplication"],
        )
        self.memory_manager: MemoryManager = memory_mgr or memory_manager
        self.bus: MessageBus = bus or message_bus
        self.analyzer: MemoryAnalyzer = MemoryAnalyzer(memory_mgr=self.memory_manager)
        self.optimizer: ContextOptimizer = ContextOptimizer(memory_mgr=self.memory_manager)

    async def initialize(self) -> bool:
        """Initializes MemoryWorker and transitions state to READY."""
        self.state = WorkerState.READY
        logger.info(f"Initialized Production MemoryWorker '{self.worker_id}' [Role: {self.role}]")
        return True

    async def execute(self, task: Task, context: SharedContext) -> TaskResult:
        """Executes knowledge analysis, deduplication, promotion, and context preparation.

        Args:
            task: Task specification.
            context: SharedContext payload.

        Returns:
            TaskResult: Result payload containing tailored ContextPackage and metrics.
        """
        start_time = time.perf_counter()
        topic = task.payload.get("topic", task.payload.get("query", "General Topic"))
        target_role = task.payload.get("target_role", "writer")

        logger.info(f"MemoryWorker '{self.worker_id}' executing memory task '{task.id}' for topic: '{topic}'")
        await self._safe_emit_event("MemoryAnalyzed", {"task_id": task.id, "topic": topic})

        try:
            # Parse incoming ResearchPackage if present in payload or context
            raw_package = task.payload.get("package") or (
                context.research_context.model_dump(mode="json") if context.research_context else None
            )
            package: ResearchPackage | None = None
            if raw_package:
                if isinstance(raw_package, dict):
                    package = ResearchPackage.model_validate(raw_package)
                elif isinstance(raw_package, ResearchPackage):
                    package = raw_package

            # 1. Analyze memories, deduplicate, promote, and prune
            metrics, processed_ids = await self.analyzer.analyze_and_process(query=topic, package=package)

            if metrics.memories_promoted > 0:
                await self._safe_emit_event("MemoryPromoted", {"task_id": task.id, "promoted_count": metrics.memories_promoted})
            if metrics.memories_archived > 0:
                await self._safe_emit_event("MemoryArchived", {"task_id": task.id, "archived_count": metrics.memories_archived})
            if metrics.memories_expired > 0:
                await self._safe_emit_event("MemoryExpired", {"task_id": task.id, "expired_count": metrics.memories_expired})

            # 2. Optimize ContextPackage for target role
            optimized_context: ContextPackage = self.optimizer.optimize_for_role(
                topic=topic, target_role=target_role, max_items=20
            )

            total_context_items = (
                len(optimized_context.research_memories)
                + len(optimized_context.knowledge_memories)
                + len(optimized_context.style_memories)
                + len(optimized_context.prompt_memories)
                + len(optimized_context.generation_memories)
            )
            metrics.context_items_selected = total_context_items
            duration = round(time.perf_counter() - start_time, 3)

            await self._safe_emit_event(
                "ContextPrepared",
                {"task_id": task.id, "target_role": target_role, "context_items": total_context_items},
            )

            artifacts = {
                "context_package": optimized_context.model_dump(mode="json"),
                "processed_memory_ids": processed_ids,
                "target_role": target_role,
            }

            return TaskResult(
                task_id=task.id,
                worker_id=self.worker_id,
                status=TaskStatus.COMPLETED,
                execution_time=duration,
                artifacts=artifacts,
                logs=[
                    f"MemoryWorker analysis finished. Promoted: {metrics.memories_promoted}, "
                    f"Archived: {metrics.memories_archived}, Selected {total_context_items} context items for {target_role}."
                ],
                metrics=metrics.model_dump(mode="json"),
            )

        except Exception as e:
            duration = round(time.perf_counter() - start_time, 3)
            logger.error(f"MemoryWorker exception for task '{task.id}': {e}")
            await self._safe_emit_event("MemoryTaskFailed", {"task_id": task.id, "error": str(e)})

            # Fallback empty ContextPackage on failure for graceful degradation
            fallback_context = ContextPackage(topic=topic)
            return TaskResult(
                task_id=task.id,
                worker_id=self.worker_id,
                status=TaskStatus.FAILED,
                execution_time=duration,
                artifacts={"context_package": fallback_context.model_dump(mode="json")},
                error=str(e),
                logs=[f"MemoryWorker failed: {e}"],
            )

    async def _safe_emit_event(self, event_type: str, data: dict) -> None:
        """Safely emits workforce events over MessageBus."""
        try:
            await self.bus.emit_event(event_type, self.worker_id, data)
        except Exception as e:
            logger.error(f"Event emission exception: {e}")

    async def shutdown(self) -> bool:
        """Shuts down MemoryWorker."""
        self.state = WorkerState.STOPPED
        logger.info(f"Shutdown Production MemoryWorker '{self.worker_id}'")
        return True

    async def health_check(self) -> bool:
        """Audits worker health."""
        return self.state != WorkerState.STOPPED

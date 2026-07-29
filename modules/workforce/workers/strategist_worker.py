"""Production Content Strategist Worker implementation for AI Workforce Core subsystem.

Transforms research and memory payloads into structured ContentBrief models for downstream
creative workers (Writer, Carousel Worker, Script Worker, Copywriter Worker).
"""

import time

from loguru import logger

from modules.memory.models import ContextPackage
from modules.research.models import ResearchPackage
from modules.workforce.base_worker import BaseWorker
from modules.workforce.bus import MessageBus, message_bus
from modules.workforce.context import SharedContext
from modules.workforce.models import Task, TaskResult, TaskStatus, WorkerState
from modules.workforce.workers.brief_models import ContentBrief, ContentObjective, ContentPriority
from modules.workforce.workers.strategy_engine import StrategyEngine


class ContentStrategistWorker(BaseWorker):
    """Production AI Worker for audience analysis, platform selection, and brief generation."""

    def __init__(
        self,
        worker_id: str = "worker_strategist_prod",
        bus: MessageBus | None = None,
    ):
        super().__init__(
            worker_id=worker_id,
            worker_name="Production Content Strategist Worker",
            role="Content Strategist",
            capabilities=["content_strategy", "brief_generation", "audience_analysis", "platform_selection"],
        )
        self.bus: MessageBus = bus or message_bus
        self.strategy_engine: StrategyEngine = StrategyEngine()

    async def initialize(self) -> bool:
        """Initializes ContentStrategistWorker and transitions state to READY."""
        self.state = WorkerState.READY
        logger.info(f"Initialized Production ContentStrategistWorker '{self.worker_id}' [Role: {self.role}]")
        return True

    async def execute(self, task: Task, context: SharedContext) -> TaskResult:
        """Executes audience analysis, platform mapping, and ContentBrief generation.

        Args:
            task: Task specification.
            context: SharedContext payload.

        Returns:
            TaskResult: Result payload containing generated ContentBrief and metrics.
        """
        start_time = time.perf_counter()
        topic = task.payload.get("topic", task.payload.get("query", "General Topic"))
        raw_goal = task.payload.get("content_goal", "EDUCATIONAL").upper()
        raw_priority = task.payload.get("priority", "MEDIUM").upper()

        try:
            goal = ContentObjective(raw_goal)
        except ValueError:
            goal = ContentObjective.EDUCATIONAL

        try:
            priority = ContentPriority(raw_priority)
        except ValueError:
            priority = ContentPriority.MEDIUM

        logger.info(f"ContentStrategistWorker '{self.worker_id}' executing strategy task '{task.id}' for topic: '{topic}'")
        await self._safe_emit_event("StrategyStarted", {"task_id": task.id, "topic": topic})

        try:
            # Parse incoming ResearchPackage & ContextPackage from payload or context
            raw_package = task.payload.get("package") or (
                context.research_context.model_dump(mode="json") if context.research_context else None
            )
            package: ResearchPackage | None = None
            if raw_package:
                if isinstance(raw_package, dict):
                    package = ResearchPackage.model_validate(raw_package)
                elif isinstance(raw_package, ResearchPackage):
                    package = raw_package

            raw_context = task.payload.get("context_package")
            context_pkg: ContextPackage | None = None
            if raw_context:
                if isinstance(raw_context, dict):
                    context_pkg = ContextPackage.model_validate(raw_context)
                elif isinstance(raw_context, ContextPackage):
                    context_pkg = raw_context

            # 1. Synthesize ContentBrief via StrategyEngine
            brief: ContentBrief = self.strategy_engine.generate_brief(
                topic=topic,
                goal=goal,
                priority=priority,
                package=package,
                context=context_pkg,
            )
            await self._safe_emit_event(
                "BriefGenerated",
                {"task_id": task.id, "title": brief.title_idea, "platform": brief.platform, "format": brief.content_format},
            )

            # 2. Compute telemetry metrics
            metrics = self.strategy_engine.compute_metrics(brief, package)
            duration = round(time.perf_counter() - start_time, 3)

            await self._safe_emit_event("StrategyCompleted", {"task_id": task.id, "duration": duration})

            artifacts = {
                "content_brief": brief.model_dump(mode="json"),
                "platform": brief.platform,
                "content_format": brief.content_format,
                "audience": brief.audience,
            }

            return TaskResult(
                task_id=task.id,
                worker_id=self.worker_id,
                status=TaskStatus.COMPLETED,
                execution_time=duration,
                artifacts=artifacts,
                logs=[
                    f"ContentStrategistWorker successfully generated brief '{brief.title_idea}' for "
                    f"{brief.platform} [{brief.content_format}] targeted at {brief.audience}."
                ],
                metrics=metrics.model_dump(mode="json"),
            )

        except Exception as e:
            duration = round(time.perf_counter() - start_time, 3)
            logger.error(f"ContentStrategistWorker exception for task '{task.id}': {e}")
            await self._safe_emit_event("StrategyFailed", {"task_id": task.id, "error": str(e)})

            # Fallback basic ContentBrief on failure for graceful degradation
            fallback_brief = ContentBrief(
                title_idea=f"Overview of {topic}",
                audience="General",
                platform="LinkedIn",
                content_format="Deep Dive",
                tone="Informative",
                complexity="Intermediate",
                estimated_length="1000 words",
                hook_strategy=f"Introduction to {topic}",
                call_to_action="Share your thoughts.",
            )

            return TaskResult(
                task_id=task.id,
                worker_id=self.worker_id,
                status=TaskStatus.FAILED,
                execution_time=duration,
                artifacts={"content_brief": fallback_brief.model_dump(mode="json")},
                error=str(e),
                logs=[f"ContentStrategistWorker failed: {e}"],
            )

    async def _safe_emit_event(self, event_type: str, data: dict) -> None:
        """Safely emits workforce events over MessageBus."""
        try:
            await self.bus.emit_event(event_type, self.worker_id, data)
        except Exception as e:
            logger.error(f"Event emission exception: {e}")

    async def shutdown(self) -> bool:
        """Shuts down ContentStrategistWorker."""
        self.state = WorkerState.STOPPED
        logger.info(f"Shutdown Production ContentStrategistWorker '{self.worker_id}'")
        return True

    async def health_check(self) -> bool:
        """Audits worker health."""
        return self.state != WorkerState.STOPPED

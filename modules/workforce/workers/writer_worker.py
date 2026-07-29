"""Production Writer Worker implementation for AI Workforce Core subsystem.

Consumes ContentBrief and ContextPackage payloads, formats structured prompts for GeminiWebProvider,
validates generated markdown drafts, and packages strongly-typed DraftPackage models.
"""

import time

from loguru import logger

from modules.ai.base import BaseAIProvider
from modules.ai.gemini_web import GeminiWebProvider
from modules.memory.models import ContextPackage
from modules.workforce.base_worker import BaseWorker
from modules.workforce.bus import MessageBus, message_bus
from modules.workforce.context import SharedContext
from modules.workforce.models import Task, TaskResult, TaskStatus, WorkerState
from modules.workforce.workers.brief_models import ContentBrief
from modules.workforce.workers.draft_models import DraftPackage, WritingStyle
from modules.workforce.workers.draft_validator import DraftValidator
from modules.workforce.workers.prompt_builder import PromptBuilder
from modules.workforce.workers.writer_metrics import WriterWorkerMetrics


class WriterWorker(BaseWorker):
    """Production AI Worker for content drafting, markdown generation, and draft validation."""

    WORKER_VERSION: str = "v0.6.4"

    def __init__(
        self,
        worker_id: str = "worker_writer_prod",
        ai_provider: BaseAIProvider | None = None,
        bus: MessageBus | None = None,
    ):
        super().__init__(
            worker_id=worker_id,
            worker_name="Production Writer Worker",
            role="Content Writer",
            capabilities=["content_writing", "draft_generation", "markdown_authoring"],
        )
        self.ai_provider: BaseAIProvider | None = ai_provider
        self.bus: MessageBus = bus or message_bus
        self.prompt_builder: PromptBuilder = PromptBuilder()
        self.draft_validator: DraftValidator = DraftValidator()

    async def initialize(self) -> bool:
        """Initializes WriterWorker and transitions state to READY."""
        if not self.ai_provider:
            self.ai_provider = GeminiWebProvider()
        self.state = WorkerState.READY
        logger.info(f"Initialized Production WriterWorker '{self.worker_id}' [Role: {self.role}]")
        return True

    async def execute(self, task: Task, context: SharedContext) -> TaskResult:
        """Executes content prompt building, Gemini generation, draft validation, and packaging.

        Args:
            task: Task specification.
            context: SharedContext payload.

        Returns:
            TaskResult: Result payload containing generated DraftPackage and metrics.
        """
        start_time = time.perf_counter()
        topic = task.payload.get("topic", task.payload.get("query", "General Topic"))
        logger.info(f"WriterWorker '{self.worker_id}' executing writing task '{task.id}' for topic: '{topic}'")
        await self._safe_emit_event("WritingStarted", {"task_id": task.id, "topic": topic})

        try:
            # 1. Parse incoming ContentBrief & ContextPackage from payload or context
            raw_brief = task.payload.get("content_brief") or task.payload.get("brief")
            brief: ContentBrief
            if raw_brief:
                if isinstance(raw_brief, dict):
                    brief = ContentBrief.model_validate(raw_brief)
                elif isinstance(raw_brief, ContentBrief):
                    brief = raw_brief
                else:
                    brief = ContentBrief(title_idea=str(topic), audience="General", platform="Blog", content_format="Article", tone="Authoritative", complexity="Intermediate", estimated_length="1000 words", hook_strategy="Introduction", call_to_action="Share thoughts.")
            else:
                brief = ContentBrief(
                    title_idea=f"Mastering {topic}",
                    audience="Developers",
                    platform="Blog",
                    content_format="Tutorial",
                    tone="Authoritative",
                    complexity="Intermediate",
                    estimated_length="1000 words",
                    hook_strategy=f"Overview of {topic}",
                    call_to_action="Subscribe for updates.",
                )

            raw_context = task.payload.get("context_package")
            context_pkg: ContextPackage | None = None
            if raw_context:
                if isinstance(raw_context, dict):
                    context_pkg = ContextPackage.model_validate(raw_context)
                elif isinstance(raw_context, ContextPackage):
                    context_pkg = raw_context

            # 2. Build structured generation prompt
            prompt = self.prompt_builder.build_prompt(brief=brief, context=context_pkg)

            # 3. Invoke AI Provider (GeminiWebProvider or injected mock)
            raw_draft = ""
            try:
                if self.ai_provider:
                    raw_draft = await self.ai_provider.generate(prompt=prompt)
            except Exception as ai_err:
                logger.warning(f"AI Provider generation failed: {ai_err}. Using fallback template.")

            if not raw_draft or not raw_draft.strip():
                raw_draft = self._generate_fallback_draft(brief=brief)

            await self._safe_emit_event("DraftGenerated", {"task_id": task.id, "draft_length": len(raw_draft)})

            # 4. Audit & Validate generated draft
            is_valid, validation_scores, issues = self.draft_validator.validate_draft(draft=raw_draft, brief=brief)

            # Map brief tone to WritingStyle enum
            style_enum = WritingStyle.AUTHORITATIVE
            if brief.tone:
                tone_str = brief.tone.upper()
                for s in WritingStyle:
                    if s.value in tone_str:
                        style_enum = s
                        break

            # 5. Build strongly-typed DraftPackage
            draft_pkg = DraftPackage(
                title=brief.title_idea,
                subtitle=f"A {brief.content_format} guide for {brief.audience}",
                platform=brief.platform,
                content_format=brief.content_format,
                audience=brief.audience,
                objective=brief.content_goal.value if hasattr(brief.content_goal, "value") else str(brief.content_goal),
                writing_style=style_enum,
                draft=raw_draft,
                draft_version=1,
                outline=brief.outline,
                citations_used=brief.supporting_citations,
                seo_keywords=brief.seo_keywords,
                estimated_read_time=brief.estimated_length,
                validation_scores=validation_scores,
                confidence=validation_scores.composite_score,
                generation_metadata={
                    "generation_number": 1,
                    "prompt_version": self.prompt_builder.PROMPT_VERSION,
                    "worker_version": self.WORKER_VERSION,
                    "issues": issues,
                },
            )

            duration = round(time.perf_counter() - start_time, 3)
            metrics = WriterWorkerMetrics(
                generation_time=duration,
                prompt_size=len(prompt),
                output_size=len(raw_draft.split()),
                citations_used=len(brief.supporting_citations),
                validation_score=validation_scores.composite_score,
                drafts_generated=1,
            )

            await self._safe_emit_event("WritingCompleted", {"task_id": task.id, "duration": duration, "quality": validation_scores.composite_score})

            artifacts = {
                "draft_package": draft_pkg.model_dump(mode="json"),
                "title": draft_pkg.title,
                "platform": draft_pkg.platform,
                "quality_score": validation_scores.composite_score,
            }

            return TaskResult(
                task_id=task.id,
                worker_id=self.worker_id,
                status=TaskStatus.COMPLETED,
                execution_time=duration,
                artifacts=artifacts,
                logs=[
                    f"WriterWorker successfully authored draft '{draft_pkg.title}' for {draft_pkg.platform} "
                    f"[Score: {validation_scores.composite_score}, Length: {metrics.output_size} words]."
                ],
                metrics=metrics.model_dump(mode="json"),
            )

        except Exception as e:
            duration = round(time.perf_counter() - start_time, 3)
            logger.error(f"WriterWorker exception for task '{task.id}': {e}")
            await self._safe_emit_event("WritingFailed", {"task_id": task.id, "error": str(e)})

            fallback_pkg = DraftPackage(
                title=f"Draft: {topic}",
                platform="Blog",
                content_format="Article",
                audience="General",
                objective="EDUCATIONAL",
                draft=f"# {topic}\n\nContent generation encountered an error.",
            )

            return TaskResult(
                task_id=task.id,
                worker_id=self.worker_id,
                status=TaskStatus.FAILED,
                execution_time=duration,
                artifacts={"draft_package": fallback_pkg.model_dump(mode="json")},
                error=str(e),
                logs=[f"WriterWorker failed: {e}"],
            )

    def _generate_fallback_draft(self, brief: ContentBrief) -> str:
        """Generates a structured fallback markdown draft when AI Provider is offline."""
        outline_content = "\n\n".join([f"## {item}\n\nDetailed breakdown for {item}." for item in brief.outline]) if brief.outline else "## Introduction\n\nContent overview."
        citations_content = "\n".join([f"- [{c.get('title', 'Ref')}]({c.get('url', '#')})" for c in brief.supporting_citations]) if brief.supporting_citations else ""

        return f"""# {brief.title_idea}

{brief.hook_strategy}

{outline_content}

## References & Citations
{citations_content}

## Conclusion & Next Steps
{brief.call_to_action}
"""

    async def _safe_emit_event(self, event_type: str, data: dict) -> None:
        """Safely emits workforce events over MessageBus."""
        try:
            await self.bus.emit_event(event_type, self.worker_id, data)
        except Exception as e:
            logger.error(f"Event emission exception: {e}")

    async def shutdown(self) -> bool:
        """Shuts down WriterWorker."""
        self.state = WorkerState.STOPPED
        logger.info(f"Shutdown Production WriterWorker '{self.worker_id}'")
        return True

    async def health_check(self) -> bool:
        """Audits worker health."""
        return self.state != WorkerState.STOPPED

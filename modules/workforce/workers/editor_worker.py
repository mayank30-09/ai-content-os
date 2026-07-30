"""Production Editor Worker implementation for AI Workforce Core subsystem.

Consumes VerifiedDraftPackage from the Fact Checker Worker, improves
readability, grammar, flow, transitions, and style via the Gemini Web
Adapter, validates preservation of facts and citations, and produces
a strongly-typed EditedDraftPackage.
"""

import time

from loguru import logger

from modules.ai.base import BaseAIProvider
from modules.ai.gemini_web import GeminiWebProvider
from modules.workforce.base_worker import BaseWorker
from modules.workforce.bus import MessageBus, message_bus
from modules.workforce.context import SharedContext
from modules.workforce.models import Task, TaskResult, TaskStatus, WorkerState
from modules.workforce.workers.edit_validator import EditValidator
from modules.workforce.workers.editing_prompt_builder import EditingPromptBuilder
from modules.workforce.workers.editor_metrics import EditorWorkerMetrics
from modules.workforce.workers.editor_models import EditedDraftPackage, EditQualityScores
from modules.workforce.workers.verification_models import VerifiedDraftPackage


class EditorWorker(BaseWorker):
    """Production AI Worker for draft editing, readability improvement, and quality enhancement.

    Responsibilities:
    - Parse VerifiedDraftPackage from Task payload.
    - Enforce ``is_approved_for_edit`` gate.
    - Build structured editing prompt via EditingPromptBuilder.
    - Invoke GeminiWebProvider for AI-assisted prose editing.
    - Validate edited output via EditValidator.
    - Preserve VerificationReport, citations, and SEO keywords.
    - Produce EditedDraftPackage inside TaskResult.
    - Emit workforce events at each pipeline stage.

    This worker NEVER invents facts, removes valid citations, performs
    research, verifies facts, or publishes content.
    """

    WORKER_VERSION: str = "v0.6.6"

    def __init__(
        self,
        worker_id: str = "worker_editor_prod",
        ai_provider: BaseAIProvider | None = None,
        prompt_builder: EditingPromptBuilder | None = None,
        edit_validator: EditValidator | None = None,
        bus: MessageBus | None = None,
    ) -> None:
        """Initializes EditorWorker with injected dependencies.

        Args:
            worker_id: Unique worker identifier.
            ai_provider: BaseAIProvider instance for text generation.
            prompt_builder: EditingPromptBuilder instance.
            edit_validator: EditValidator instance.
            bus: MessageBus instance.
        """
        super().__init__(
            worker_id=worker_id,
            worker_name="Production Editor Worker",
            role="Content Editor",
            capabilities=["editing", "readability_improvement", "grammar_correction", "style_enhancement"],
        )
        self.ai_provider: BaseAIProvider | None = ai_provider
        self.prompt_builder: EditingPromptBuilder = prompt_builder or EditingPromptBuilder()
        self.edit_validator: EditValidator = edit_validator or EditValidator()
        self.bus: MessageBus = bus or message_bus

    async def initialize(self) -> bool:
        """Initializes EditorWorker and transitions state to READY.

        Returns:
            bool: True if initialization succeeded.
        """
        if not self.ai_provider:
            self.ai_provider = GeminiWebProvider()
        self.state = WorkerState.READY
        logger.info(f"Initialized Production EditorWorker '{self.worker_id}' [Role: {self.role}]")
        return True

    async def execute(self, task: Task, context: SharedContext) -> TaskResult:
        """Executes the full editing pipeline.

        Pipeline:
            1. Parse VerifiedDraftPackage from Task payload.
            2. Check is_approved_for_edit gate.
            3. Compute pre-edit readability baseline.
            4. Build editing prompt via EditingPromptBuilder.
            5. Invoke GeminiWebProvider for AI-assisted editing.
            6. Fall back to original draft if AI fails.
            7. Run EditValidator to compute quality scores.
            8. Assemble EditedDraftPackage.
            9. Return TaskResult.

        Args:
            task: Task specification containing payload with verified_draft_package.
            context: SharedContext payload.

        Returns:
            TaskResult: Contains EditedDraftPackage artifact and metrics.
        """
        start_time = time.perf_counter()
        topic = task.payload.get("topic", task.payload.get("query", "Unknown Topic"))
        logger.info(f"EditorWorker '{self.worker_id}' executing task '{task.id}' for topic: '{topic}'")

        try:
            # ----------------------------------------------------------------
            # 1. Parse VerifiedDraftPackage
            # ----------------------------------------------------------------
            verified_pkg = self._parse_verified_draft_package(task)
            draft_pkg = verified_pkg.draft_package
            original_draft = draft_pkg.draft

            await self._safe_emit_event(
                "EditingStarted",
                {"task_id": task.id, "title": draft_pkg.title, "topic": topic},
            )

            # ----------------------------------------------------------------
            # 2. Check is_approved_for_edit gate
            # ----------------------------------------------------------------
            if not verified_pkg.is_approved_for_edit:
                logger.warning(
                    f"EditorWorker: draft '{draft_pkg.title}' not approved for editing. "
                    f"Passing through unchanged."
                )
                return self._build_passthrough_result(task, verified_pkg, start_time)

            # ----------------------------------------------------------------
            # 3. Pre-edit readability baseline
            # ----------------------------------------------------------------
            readability_before = self.edit_validator._estimate_readability(original_draft)

            # ----------------------------------------------------------------
            # 4. Build editing prompt
            # ----------------------------------------------------------------
            prompt = self.prompt_builder.build_editing_prompt(verified_pkg)
            system_instruction = self.prompt_builder.build_system_instruction()

            # ----------------------------------------------------------------
            # 5. Invoke AI provider
            # ----------------------------------------------------------------
            edited_draft = ""
            try:
                if self.ai_provider:
                    edited_draft = await self.ai_provider.generate(
                        prompt=prompt,
                        system_instruction=system_instruction,
                    )
            except Exception as ai_err:
                logger.warning(f"AI Provider editing failed: {ai_err}. Using original draft as fallback.")

            # ----------------------------------------------------------------
            # 6. Fallback to original if AI failed
            # ----------------------------------------------------------------
            if not edited_draft or not edited_draft.strip():
                logger.info("EditorWorker: AI returned empty output. Using original draft as fallback.")
                edited_draft = original_draft

            await self._safe_emit_event(
                "DraftEdited",
                {
                    "task_id": task.id,
                    "original_length": len(original_draft),
                    "edited_length": len(edited_draft),
                },
            )

            # ----------------------------------------------------------------
            # 7. Run EditValidator
            # ----------------------------------------------------------------
            quality_scores, issues = self.edit_validator.validate_edit(
                original_draft=original_draft,
                edited_draft=edited_draft,
                verified_pkg=verified_pkg,
            )

            # ----------------------------------------------------------------
            # 8. Assemble EditedDraftPackage
            # ----------------------------------------------------------------
            readability_after = quality_scores.readability_score

            edited_pkg = EditedDraftPackage(
                original_draft_version=draft_pkg.draft_version,
                edited_draft_version=1,
                title=draft_pkg.title,
                subtitle=draft_pkg.subtitle,
                platform=draft_pkg.platform,
                content_format=draft_pkg.content_format,
                audience=draft_pkg.audience,
                objective=draft_pkg.objective,
                writing_style=draft_pkg.writing_style,
                edited_content=edited_draft,
                preserved_citations=draft_pkg.citations_used,
                preserved_keywords=draft_pkg.seo_keywords,
                verification_report=verified_pkg.verification_report,
                quality_scores=quality_scores,
                editor_metadata={
                    "editor_version": self.WORKER_VERSION,
                    "prompt_version": self.prompt_builder.PROMPT_VERSION,
                    "edit_pass_count": 1,
                    "issues": issues,
                },
            )

            duration = round(time.perf_counter() - start_time, 3)

            metrics = EditorWorkerMetrics(
                editing_time=duration,
                readability_before=readability_before,
                readability_after=readability_after,
                grammar_improvement=round(quality_scores.grammar_score - readability_before, 3),
                style_improvement=round(quality_scores.style_score - 0.7, 3),
                citation_preservation=quality_scores.citation_preservation_score,
                keyword_preservation=quality_scores.keyword_preservation_score,
                overall_quality=quality_scores.overall_quality,
            )

            await self._safe_emit_event(
                "EditingCompleted",
                {
                    "task_id": task.id,
                    "overall_quality": quality_scores.overall_quality,
                    "citation_preservation": quality_scores.citation_preservation_score,
                    "duration": duration,
                },
            )

            logger.info(
                f"EditorWorker: editing completed for '{draft_pkg.title}'. "
                f"Quality={quality_scores.overall_quality:.2f}, "
                f"Citations preserved={quality_scores.citation_preservation_score:.2f}."
            )

            return TaskResult(
                task_id=task.id,
                worker_id=self.worker_id,
                status=TaskStatus.COMPLETED,
                execution_time=duration,
                artifacts={"edited_draft_package": edited_pkg.model_dump(mode="json")},
                logs=[
                    f"EditorWorker: edited draft '{edited_pkg.title}' for {edited_pkg.platform} "
                    f"[Quality: {quality_scores.overall_quality:.2f}, "
                    f"Issues: {len(issues)}]."
                ],
                metrics=metrics.model_dump(mode="json"),
            )

        except Exception as e:
            duration = round(time.perf_counter() - start_time, 3)
            logger.error(f"EditorWorker exception for task '{task.id}': {e}")
            await self._safe_emit_event("EditingFailed", {"task_id": task.id, "error": str(e)})

            return TaskResult(
                task_id=task.id,
                worker_id=self.worker_id,
                status=TaskStatus.FAILED,
                execution_time=duration,
                error=str(e),
                logs=[f"EditorWorker failed: {e}"],
            )

    # ------------------------------------------------------------------
    # Input parsing helpers
    # ------------------------------------------------------------------

    def _parse_verified_draft_package(self, task: Task) -> VerifiedDraftPackage:
        """Parses VerifiedDraftPackage from task payload.

        Args:
            task: Task containing payload with ``verified_draft_package`` key.

        Returns:
            Validated VerifiedDraftPackage instance.

        Raises:
            ValueError: If no verified_draft_package is found in the payload.
        """
        raw = task.payload.get("verified_draft_package")
        if isinstance(raw, VerifiedDraftPackage):
            return raw
        if isinstance(raw, dict):
            return VerifiedDraftPackage.model_validate(raw)
        raise ValueError(
            f"EditorWorker: task '{task.id}' payload missing required 'verified_draft_package'."
        )

    def _build_passthrough_result(
        self,
        task: Task,
        verified_pkg: VerifiedDraftPackage,
        start_time: float,
    ) -> TaskResult:
        """Builds a passthrough TaskResult when editing is not approved.

        The original verified draft is returned unchanged inside an
        EditedDraftPackage with default quality scores.

        Args:
            task: Original task.
            verified_pkg: VerifiedDraftPackage that was not approved.
            start_time: Pipeline start timestamp.

        Returns:
            TaskResult with status COMPLETED and unchanged draft.
        """
        draft_pkg = verified_pkg.draft_package
        duration = round(time.perf_counter() - start_time, 3)

        passthrough_pkg = EditedDraftPackage(
            original_draft_version=draft_pkg.draft_version,
            edited_draft_version=1,
            title=draft_pkg.title,
            subtitle=draft_pkg.subtitle,
            platform=draft_pkg.platform,
            content_format=draft_pkg.content_format,
            audience=draft_pkg.audience,
            objective=draft_pkg.objective,
            writing_style=draft_pkg.writing_style,
            edited_content=draft_pkg.draft,
            preserved_citations=draft_pkg.citations_used,
            preserved_keywords=draft_pkg.seo_keywords,
            verification_report=verified_pkg.verification_report,
            quality_scores=EditQualityScores(),
            editor_metadata={
                "editor_version": self.WORKER_VERSION,
                "prompt_version": self.prompt_builder.PROMPT_VERSION,
                "edit_pass_count": 0,
                "passthrough": True,
                "reason": "not_approved_for_edit",
            },
        )

        return TaskResult(
            task_id=task.id,
            worker_id=self.worker_id,
            status=TaskStatus.COMPLETED,
            execution_time=duration,
            artifacts={"edited_draft_package": passthrough_pkg.model_dump(mode="json")},
            logs=[f"EditorWorker: draft '{draft_pkg.title}' not approved for editing. Passed through unchanged."],
            metrics=EditorWorkerMetrics(editing_time=duration).model_dump(mode="json"),
        )

    # ------------------------------------------------------------------
    # Lifecycle and bus helpers
    # ------------------------------------------------------------------

    async def _safe_emit_event(self, event_type: str, data: dict) -> None:
        """Safely emits workforce events over MessageBus.

        Args:
            event_type: Event classification string.
            data: Event payload data.
        """
        try:
            await self.bus.emit_event(event_type, self.worker_id, data)
        except Exception as e:
            logger.error(f"EditorWorker event emission exception: {e}")

    async def shutdown(self) -> bool:
        """Shuts down EditorWorker and transitions state to STOPPED.

        Returns:
            bool: True if shutdown completed cleanly.
        """
        self.state = WorkerState.STOPPED
        logger.info(f"Shutdown Production EditorWorker '{self.worker_id}'")
        return True

    async def health_check(self) -> bool:
        """Audits worker health.

        Returns:
            bool: True if worker is not STOPPED.
        """
        return self.state != WorkerState.STOPPED

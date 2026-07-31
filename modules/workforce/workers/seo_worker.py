"""Production SEO Worker implementation for AI Workforce Core subsystem.

Consumes EditedDraftPackage from the Editor Worker, analyzes SEO fitness,
builds optimization prompts for GeminiWebProvider, validates preservation
of facts and citations, and produces a strongly-typed SEOOptimizedPackage.
"""

import json
import re
import time

from loguru import logger

from modules.ai.base import BaseAIProvider
from modules.ai.gemini_web import GeminiWebProvider
from modules.workforce.base_worker import BaseWorker
from modules.workforce.bus import MessageBus, message_bus
from modules.workforce.context import SharedContext
from modules.workforce.models import Task, TaskResult, TaskStatus, WorkerState
from modules.workforce.workers.editor_models import EditedDraftPackage
from modules.workforce.workers.seo_analyzer import SEOAnalyzer
from modules.workforce.workers.seo_metrics import SEOWorkerMetrics
from modules.workforce.workers.seo_models import SEOOptimizedPackage
from modules.workforce.workers.seo_prompt_builder import SEOPromptBuilder
from modules.workforce.workers.seo_validator import SEOValidator


class SEOWorker(BaseWorker):
    """Production AI Worker for SEO optimization of edited content.

    Responsibilities:
    - Parse EditedDraftPackage from Task payload.
    - Run deterministic SEO analysis via SEOAnalyzer.
    - Build structured optimization prompt via SEOPromptBuilder.
    - Invoke GeminiWebProvider for AI-assisted SEO optimization.
    - Parse structured JSON response from AI provider.
    - Fall back to original content if AI fails.
    - Run SEOValidator to compute SEO quality scores.
    - Assemble SEOOptimizedPackage with lineage data.
    - Produce TaskResult with SEOOptimizedPackage and metrics.
    - Emit workforce events at each pipeline stage.

    This worker NEVER invents facts, removes valid citations, performs
    research, verifies facts, or publishes content.
    """

    WORKER_VERSION: str = "v0.6.7"

    def __init__(
        self,
        worker_id: str = "worker_seo_prod",
        ai_provider: BaseAIProvider | None = None,
        prompt_builder: SEOPromptBuilder | None = None,
        seo_analyzer: SEOAnalyzer | None = None,
        seo_validator: SEOValidator | None = None,
        bus: MessageBus | None = None,
    ) -> None:
        """Initializes SEOWorker with injected dependencies.

        Args:
            worker_id: Unique worker identifier.
            ai_provider: BaseAIProvider instance for text generation.
            prompt_builder: SEOPromptBuilder instance.
            seo_analyzer: SEOAnalyzer instance.
            seo_validator: SEOValidator instance.
            bus: MessageBus instance.
        """
        super().__init__(
            worker_id=worker_id,
            worker_name="Production SEO Worker",
            role="SEO Specialist",
            capabilities=["seo_optimization", "meta_generation", "keyword_optimization", "schema_generation"],
        )
        self.ai_provider: BaseAIProvider | None = ai_provider
        self.prompt_builder: SEOPromptBuilder = prompt_builder or SEOPromptBuilder()
        self.seo_analyzer: SEOAnalyzer = seo_analyzer or SEOAnalyzer()
        self.seo_validator: SEOValidator = seo_validator or SEOValidator()
        self.bus: MessageBus = bus or message_bus

    async def initialize(self) -> bool:
        """Initializes SEOWorker and transitions state to READY.

        Returns:
            bool: True if initialization succeeded.
        """
        if not self.ai_provider:
            self.ai_provider = GeminiWebProvider()
        self.state = WorkerState.READY
        logger.info(f"Initialized Production SEOWorker '{self.worker_id}' [Role: {self.role}]")
        return True

    async def execute(self, task: Task, context: SharedContext) -> TaskResult:
        """Executes the full SEO optimization pipeline.

        Pipeline:
            1. Parse EditedDraftPackage from Task payload.
            2. Run SEOAnalyzer for pre-optimization analysis.
            3. Build optimization prompt via SEOPromptBuilder.
            4. Invoke GeminiWebProvider for AI-assisted optimization.
            5. Parse structured JSON response.
            6. Fall back to original content if AI fails.
            7. Run SEOValidator to compute quality scores.
            8. Assemble SEOOptimizedPackage.
            9. Return TaskResult.

        Args:
            task: Task specification containing payload with edited_draft_package.
            context: SharedContext payload.

        Returns:
            TaskResult: Contains SEOOptimizedPackage artifact and metrics.
        """
        start_time = time.perf_counter()
        topic = task.payload.get("topic", task.payload.get("query", "Unknown Topic"))
        logger.info(f"SEOWorker '{self.worker_id}' executing task '{task.id}' for topic: '{topic}'")

        try:
            # ----------------------------------------------------------------
            # 1. Parse EditedDraftPackage
            # ----------------------------------------------------------------
            edited_pkg = self._parse_edited_draft_package(task)
            original_content = edited_pkg.edited_content
            focus_keyword = edited_pkg.preserved_keywords[0] if edited_pkg.preserved_keywords else ""

            await self._safe_emit_event(
                "SEOOptimizationStarted",
                {"task_id": task.id, "title": edited_pkg.title, "topic": topic},
            )

            # ----------------------------------------------------------------
            # 2. Run SEOAnalyzer
            # ----------------------------------------------------------------
            analysis = self.seo_analyzer.analyze(
                content=original_content,
                title=edited_pkg.title,
                focus_keyword=focus_keyword,
                secondary_keywords=edited_pkg.preserved_keywords[1:] if len(edited_pkg.preserved_keywords) > 1 else [],
                citations=edited_pkg.preserved_citations,
            )

            await self._safe_emit_event(
                "SEOAnalysisCompleted",
                {
                    "task_id": task.id,
                    "content_score": analysis.content_score,
                    "keyword_density": analysis.current_keyword_density,
                    "heading_issues": len(analysis.heading_analysis.issues),
                },
            )

            # ----------------------------------------------------------------
            # 3. Build optimization prompt
            # ----------------------------------------------------------------
            prompt = self.prompt_builder.build_optimization_prompt(edited_pkg, analysis)
            system_instruction = self.prompt_builder.build_system_instruction()

            # ----------------------------------------------------------------
            # 4. Invoke AI provider
            # ----------------------------------------------------------------
            ai_response = ""
            try:
                if self.ai_provider:
                    ai_response = await self.ai_provider.generate(
                        prompt=prompt,
                        system_instruction=system_instruction,
                    )
            except Exception as ai_err:
                logger.warning(f"AI Provider SEO optimization failed: {ai_err}. Using fallback.")

            # ----------------------------------------------------------------
            # 5. Parse structured JSON response
            # ----------------------------------------------------------------
            parsed = self._parse_ai_response(ai_response)
            optimized_content = parsed.get("optimized_content", "").strip()
            meta_title = parsed.get("meta_title", analysis.meta_analysis.suggested_meta_title)
            meta_description = parsed.get("meta_description", analysis.meta_analysis.suggested_meta_description)
            faq_section = parsed.get("faq_section", [])
            schema_markup = parsed.get("schema_markup", {})
            internal_links = parsed.get("internal_link_suggestions", [])
            external_links = parsed.get("external_link_suggestions", [])
            image_alts = parsed.get("image_alt_suggestions", [])

            # ----------------------------------------------------------------
            # 6. Fallback if AI returned empty content
            # ----------------------------------------------------------------
            if not optimized_content:
                logger.info("SEOWorker: AI returned empty optimized content. Using original as fallback.")
                optimized_content = original_content

            await self._safe_emit_event(
                "SEOOptimized",
                {
                    "task_id": task.id,
                    "original_length": len(original_content),
                    "optimized_length": len(optimized_content),
                },
            )

            # ----------------------------------------------------------------
            # 7. Run SEOValidator
            # ----------------------------------------------------------------
            seo_scores, issues = self.seo_validator.validate_optimization(
                original_content=original_content,
                optimized_content=optimized_content,
                edited_pkg=edited_pkg,
                analysis=analysis,
                meta_title=meta_title,
                meta_description=meta_description,
            )

            # ----------------------------------------------------------------
            # 8. Assemble SEOOptimizedPackage
            # ----------------------------------------------------------------
            heading_structure = self._extract_headings(optimized_content)
            slug = analysis.meta_analysis.suggested_slug
            final_keyword_density = SEOAnalyzer.calculate_keyword_density(
                optimized_content, focus_keyword
            )

            seo_pkg = SEOOptimizedPackage(
                title=edited_pkg.title,
                meta_title=meta_title,
                meta_description=meta_description,
                slug=slug,
                focus_keyword=focus_keyword,
                secondary_keywords=edited_pkg.preserved_keywords[1:] if len(edited_pkg.preserved_keywords) > 1 else [],
                keyword_density=final_keyword_density,
                optimized_content=optimized_content,
                heading_structure=heading_structure,
                faq_section=faq_section,
                internal_link_suggestions=internal_links,
                external_link_suggestions=external_links,
                schema_markup=schema_markup,
                image_alt_suggestions=image_alts,
                readability_score=edited_pkg.quality_scores.readability_score,
                seo_score=seo_scores.overall_seo_score,
                seo_scores=seo_scores,
                verification_report=edited_pkg.verification_report,
                quality_scores=edited_pkg.quality_scores,
                platform=edited_pkg.platform,
                content_format=edited_pkg.content_format,
                audience=edited_pkg.audience,
                objective=edited_pkg.objective,
                writing_style=edited_pkg.writing_style,
                optimization_metadata={
                    "seo_version": self.WORKER_VERSION,
                    "prompt_version": self.prompt_builder.PROMPT_VERSION,
                    "optimization_pass_count": 1,
                    "issues": issues,
                },
            )

            duration = round(time.perf_counter() - start_time, 3)

            # ----------------------------------------------------------------
            # 9. Compute metrics
            # ----------------------------------------------------------------
            metrics = SEOWorkerMetrics(
                optimization_time=duration,
                seo_score_before=analysis.content_score,
                seo_score_after=seo_scores.overall_seo_score,
                keyword_density=final_keyword_density,
                heading_score=seo_scores.heading_quality_score,
                meta_score=seo_scores.meta_quality_score,
                internal_links_suggested=len(internal_links),
                external_links_suggested=len(external_links),
                faq_generated=len(faq_section) > 0,
                schema_generated=len(schema_markup) > 0,
            )

            await self._safe_emit_event(
                "SEOOptimizationCompleted",
                {
                    "task_id": task.id,
                    "seo_score": seo_scores.overall_seo_score,
                    "keyword_density": analysis.current_keyword_density,
                    "duration": duration,
                },
            )

            logger.info(
                f"SEOWorker: optimization completed for '{edited_pkg.title}'. "
                f"SEO Score={seo_scores.overall_seo_score:.2f}, "
                f"Duration={duration:.2f}s."
            )

            return TaskResult(
                task_id=task.id,
                worker_id=self.worker_id,
                status=TaskStatus.COMPLETED,
                execution_time=duration,
                artifacts={"seo_optimized_package": seo_pkg.model_dump(mode="json")},
                logs=[
                    f"SEOWorker: optimized '{seo_pkg.title}' for {seo_pkg.platform} "
                    f"[SEO: {seo_scores.overall_seo_score:.2f}, Issues: {len(issues)}]."
                ],
                metrics=metrics.model_dump(mode="json"),
            )

        except Exception as e:
            duration = round(time.perf_counter() - start_time, 3)
            logger.error(f"SEOWorker exception for task '{task.id}': {e}")
            await self._safe_emit_event("SEOOptimizationFailed", {"task_id": task.id, "error": str(e)})

            return TaskResult(
                task_id=task.id,
                worker_id=self.worker_id,
                status=TaskStatus.FAILED,
                execution_time=duration,
                error=str(e),
                logs=[f"SEOWorker failed: {e}"],
            )

    # ------------------------------------------------------------------
    # Input parsing helpers
    # ------------------------------------------------------------------

    def _parse_edited_draft_package(self, task: Task) -> EditedDraftPackage:
        """Parses EditedDraftPackage from task payload.

        Args:
            task: Task containing payload with ``edited_draft_package`` key.

        Returns:
            Validated EditedDraftPackage instance.

        Raises:
            ValueError: If no edited_draft_package is found in the payload.
        """
        raw = task.payload.get("edited_draft_package")
        if isinstance(raw, EditedDraftPackage):
            return raw
        if isinstance(raw, dict):
            return EditedDraftPackage.model_validate(raw)
        raise ValueError(
            f"SEOWorker: task '{task.id}' payload missing required 'edited_draft_package'."
        )

    def _parse_ai_response(self, response: str) -> dict:
        """Parses structured JSON from the AI provider response.

        Attempts to extract a JSON object from the response text.
        Returns an empty dict if parsing fails.

        Args:
            response: Raw AI provider response string.

        Returns:
            Parsed dict or empty dict on failure.
        """
        if not response or not response.strip():
            return {}

        # Try direct JSON parse
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass

        # Try extracting JSON from markdown code block
        json_match = re.search(r"```(?:json)?\s*\n(.*?)\n```", response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # Try extracting any JSON object
        brace_match = re.search(r"\{.*\}", response, re.DOTALL)
        if brace_match:
            try:
                return json.loads(brace_match.group(0))
            except json.JSONDecodeError:
                pass

        logger.warning("SEOWorker: Could not parse AI response as JSON. Using fallback.")
        return {}

    @staticmethod
    def _extract_headings(content: str) -> list[dict]:
        """Extracts heading structure from markdown content.

        Args:
            content: Markdown content.

        Returns:
            List of heading dicts with ``level`` and ``text`` keys.
        """
        return SEOAnalyzer.extract_headings(content)

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
            logger.error(f"SEOWorker event emission exception: {e}")

    async def shutdown(self) -> bool:
        """Shuts down SEOWorker and transitions state to STOPPED.

        Returns:
            bool: True if shutdown completed cleanly.
        """
        self.state = WorkerState.STOPPED
        logger.info(f"Shutdown Production SEOWorker '{self.worker_id}'")
        return True

    async def health_check(self) -> bool:
        """Audits worker health.

        Returns:
            bool: True if worker is not STOPPED.
        """
        return self.state != WorkerState.STOPPED

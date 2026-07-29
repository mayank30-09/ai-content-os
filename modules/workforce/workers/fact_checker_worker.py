"""Production Fact Checker Worker implementation for AI Workforce Core subsystem.

Consumes DraftPackage, ResearchPackage, and ContextPackage payloads,
extracts factual claims, verifies citations, validates claim-to-source
correspondence, and produces a strongly-typed VerifiedDraftPackage.
"""

import time
from datetime import UTC, datetime

from loguru import logger

from modules.memory.models import ContextPackage
from modules.research.models import ResearchPackage
from modules.workforce.base_worker import BaseWorker
from modules.workforce.bus import MessageBus, message_bus
from modules.workforce.context import SharedContext
from modules.workforce.models import Task, TaskResult, TaskStatus, WorkerState
from modules.workforce.workers.citation_verifier import CitationAuditResult, CitationVerifier
from modules.workforce.workers.claim_extractor import ClaimExtractor, ExtractedClaim
from modules.workforce.workers.draft_models import DraftPackage
from modules.workforce.workers.fact_checker_metrics import FactCheckerMetrics
from modules.workforce.workers.fact_validator import FactValidator
from modules.workforce.workers.verification_models import (
    VerificationReport,
    VerificationStatus,
    VerifiedDraftPackage,
)

# Confidence threshold above which a draft is automatically approved for editing
_APPROVAL_THRESHOLD = 0.70

# Confidence threshold below which a draft is escalated for human review
_HUMAN_REVIEW_THRESHOLD = 0.50


class FactCheckerWorker(BaseWorker):
    """Production AI Worker for deterministic fact verification and draft auditing.

    Responsibilities:
    - Parse DraftPackage, ResearchPackage, and ContextPackage from Task payload.
    - Extract factual claims using ClaimExtractor.
    - Audit citations via CitationVerifier.
    - Validate claims against source evidence via FactValidator.
    - Assemble VerificationReport and VerifiedDraftPackage.
    - Emit workforce events at each pipeline stage.
    - Return TaskResult with VerifiedDraftPackage as artifact.

    This worker NEVER rewrites, edits, publishes, or generates new content.
    """

    WORKER_VERSION: str = "v0.6.5"

    def __init__(
        self,
        worker_id: str = "worker_fact_checker_prod",
        claim_extractor: ClaimExtractor | None = None,
        citation_verifier: CitationVerifier | None = None,
        fact_validator: FactValidator | None = None,
        bus: MessageBus | None = None,
    ) -> None:
        """Initializes FactCheckerWorker with injected dependencies.

        Args:
            worker_id: Unique worker identifier.
            claim_extractor: ClaimExtractor instance.
            citation_verifier: CitationVerifier instance.
            fact_validator: FactValidator instance.
            bus: MessageBus instance.
        """
        super().__init__(
            worker_id=worker_id,
            worker_name="Production Fact Checker Worker",
            role="Fact Checker",
            capabilities=["fact_checking", "claim_extraction", "citation_verification", "hallucination_detection"],
        )
        self.claim_extractor: ClaimExtractor = claim_extractor or ClaimExtractor()
        self.citation_verifier: CitationVerifier = citation_verifier or CitationVerifier()
        self.fact_validator: FactValidator = fact_validator or FactValidator()
        self.bus: MessageBus = bus or message_bus

    async def initialize(self) -> bool:
        """Initializes FactCheckerWorker and transitions state to READY.

        Returns:
            bool: True if initialization succeeded.
        """
        self.state = WorkerState.READY
        logger.info(f"Initialized Production FactCheckerWorker '{self.worker_id}' [Role: {self.role}]")
        return True

    async def execute(self, task: Task, context: SharedContext) -> TaskResult:
        """Executes the full fact verification pipeline.

        Pipeline:
            1. Parse DraftPackage, ResearchPackage, ContextPackage from payload.
            2. Extract factual claims using ClaimExtractor.
            3. Verify citations using CitationVerifier.
            4. Validate claims using FactValidator.
            5. Compute aggregate metrics and VerificationReport.
            6. Assemble VerifiedDraftPackage.
            7. Return TaskResult.

        Args:
            task: Task specification containing payload with draft_package,
                research_package, and optionally context_package.
            context: SharedContext payload.

        Returns:
            TaskResult: Contains VerifiedDraftPackage artifact and metrics.
        """
        start_time = time.perf_counter()
        topic = task.payload.get("topic", task.payload.get("query", "Unknown Topic"))
        logger.info(f"FactCheckerWorker '{self.worker_id}' executing task '{task.id}' for topic: '{topic}'")

        await self._safe_emit_event("FactCheckingStarted", {"task_id": task.id, "topic": topic})

        try:
            # ----------------------------------------------------------------
            # 1. Parse input payloads
            # ----------------------------------------------------------------
            draft_pkg = self._parse_draft_package(task)
            research_pkg = self._parse_research_package(task)
            context_pkg = self._parse_context_package(task)

            # ----------------------------------------------------------------
            # 2. Claim extraction
            # ----------------------------------------------------------------
            claims: list[ExtractedClaim] = self.claim_extractor.extract_claims(draft_pkg.draft)
            logger.info(f"FactCheckerWorker: extracted {len(claims)} claims from draft '{draft_pkg.title}'.")

            await self._safe_emit_event(
                "ClaimsExtracted",
                {"task_id": task.id, "claims_count": len(claims), "title": draft_pkg.title},
            )

            # ----------------------------------------------------------------
            # 3. Citation verification
            # ----------------------------------------------------------------
            citation_audit_results: list[CitationAuditResult]
            duplicate_citation_count: int
            citation_audit_results, duplicate_citation_count = self.citation_verifier.verify_citations(
                citations_used=draft_pkg.citations_used,
                research_package=research_pkg,
            )

            # ----------------------------------------------------------------
            # 4. Claim validation against evidence
            # ----------------------------------------------------------------
            claim_results = self.fact_validator.validate_claims(
                claims=claims,
                research_package=research_pkg,
                context_package=context_pkg,
            )

            # ----------------------------------------------------------------
            # 5. Aggregate metrics and build VerificationReport
            # ----------------------------------------------------------------
            duration = round(time.perf_counter() - start_time, 3)
            metrics = self._compute_metrics(
                claims=claims,
                claim_results_list=claim_results,
                citation_audit=citation_audit_results,
                duplicate_count=duplicate_citation_count,
                duration=duration,
            )

            report = self._build_report(
                claim_results_list=claim_results,
                citation_audit=citation_audit_results,
                metrics=metrics,
            )

            # ----------------------------------------------------------------
            # 6. Assemble VerifiedDraftPackage
            # ----------------------------------------------------------------
            is_approved = report.overall_confidence >= _APPROVAL_THRESHOLD
            requires_review = report.overall_confidence < _HUMAN_REVIEW_THRESHOLD or report.hallucination_count > 0

            verified_pkg = VerifiedDraftPackage(
                draft_package=draft_pkg,
                verification_report=report,
                is_approved_for_edit=is_approved,
                requires_human_review=requires_review,
                audit_timestamp=datetime.now(UTC).isoformat(),
            )

            await self._safe_emit_event(
                "VerificationCompleted",
                {
                    "task_id": task.id,
                    "overall_status": report.overall_status,
                    "overall_confidence": report.overall_confidence,
                    "claims_verified": report.claims_verified,
                    "is_approved_for_edit": is_approved,
                    "requires_human_review": requires_review,
                },
            )

            logger.info(
                f"FactCheckerWorker: verification completed for '{draft_pkg.title}'. "
                f"Status={report.overall_status}, Confidence={report.overall_confidence:.2f}, "
                f"Approved={is_approved}, RequiresReview={requires_review}."
            )

            return TaskResult(
                task_id=task.id,
                worker_id=self.worker_id,
                status=TaskStatus.COMPLETED,
                execution_time=duration,
                artifacts={"verified_draft_package": verified_pkg.model_dump(mode="json")},
                logs=[
                    f"FactCheckerWorker: verified draft '{draft_pkg.title}' "
                    f"[{report.claims_verified}/{report.claims_checked} claims supported, "
                    f"confidence={report.overall_confidence:.2f}]."
                ],
                metrics=metrics.model_dump(mode="json"),
            )

        except Exception as e:
            duration = round(time.perf_counter() - start_time, 3)
            logger.error(f"FactCheckerWorker exception for task '{task.id}': {e}")
            await self._safe_emit_event("VerificationFailed", {"task_id": task.id, "error": str(e)})

            return TaskResult(
                task_id=task.id,
                worker_id=self.worker_id,
                status=TaskStatus.FAILED,
                execution_time=duration,
                error=str(e),
                logs=[f"FactCheckerWorker failed: {e}"],
            )

    # ------------------------------------------------------------------
    # Input parsing helpers
    # ------------------------------------------------------------------

    def _parse_draft_package(self, task: Task) -> DraftPackage:
        """Parses DraftPackage from task payload.

        Args:
            task: Task containing payload with ``draft_package`` key.

        Returns:
            Validated DraftPackage instance.

        Raises:
            ValueError: If no draft_package is found in the payload.
        """
        raw = task.payload.get("draft_package")
        if isinstance(raw, DraftPackage):
            return raw
        if isinstance(raw, dict):
            return DraftPackage.model_validate(raw)
        raise ValueError(
            f"FactCheckerWorker: task '{task.id}' payload missing required 'draft_package'."
        )

    def _parse_research_package(self, task: Task) -> ResearchPackage | None:
        """Parses optional ResearchPackage from task payload.

        Args:
            task: Task containing optional ``research_package`` key.

        Returns:
            Validated ResearchPackage or None if absent.
        """
        raw = task.payload.get("research_package")
        if isinstance(raw, ResearchPackage):
            return raw
        if isinstance(raw, dict):
            try:
                return ResearchPackage.model_validate(raw)
            except Exception as e:
                logger.warning(f"FactCheckerWorker: failed to parse research_package: {e}")
        return None

    def _parse_context_package(self, task: Task) -> ContextPackage | None:
        """Parses optional ContextPackage from task payload.

        Args:
            task: Task containing optional ``context_package`` key.

        Returns:
            Validated ContextPackage or None if absent.
        """
        raw = task.payload.get("context_package")
        if isinstance(raw, ContextPackage):
            return raw
        if isinstance(raw, dict):
            try:
                return ContextPackage.model_validate(raw)
            except Exception as e:
                logger.warning(f"FactCheckerWorker: failed to parse context_package: {e}")
        return None

    # ------------------------------------------------------------------
    # Metrics and report builders
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_metrics(
        claims: list[ExtractedClaim],
        claim_results_list: list,
        citation_audit: list[CitationAuditResult],
        duplicate_count: int,
        duration: float,
    ) -> FactCheckerMetrics:
        """Computes aggregate FactCheckerMetrics from pipeline outputs.

        Args:
            claims: Extracted claims list.
            claim_results_list: ClaimResult list from FactValidator.
            citation_audit: CitationAuditResult list from CitationVerifier.
            duplicate_count: Count of duplicate citations.
            duration: Total pipeline execution time in seconds.

        Returns:
            FactCheckerMetrics instance.
        """
        total_claims = len(claims)
        verified_statuses = {VerificationStatus.VERIFIED, VerificationStatus.PARTIALLY_VERIFIED}
        claims_verified = sum(1 for r in claim_results_list if r.status in verified_statuses)
        unsupported = sum(1 for r in claim_results_list if r.status == VerificationStatus.UNVERIFIED)
        hallucinations = sum(1 for r in claim_results_list if r.status == VerificationStatus.HALLUCINATION_SUSPECTED)

        confidences = [r.confidence for r in claim_results_list]
        avg_confidence = round(sum(confidences) / len(confidences), 3) if confidences else 1.0

        citations_checked = len(citation_audit)

        # Overall confidence is a weighted average of claim confidence
        # penalized by hallucination and unsupported counts
        if total_claims > 0:
            base = avg_confidence
            penalty = (hallucinations * 0.10 + unsupported * 0.03)
            overall_confidence = round(max(0.0, min(1.0, base - penalty)), 3)
        else:
            overall_confidence = 1.0

        return FactCheckerMetrics(
            claims_found=total_claims,
            claims_verified=claims_verified,
            citations_checked=citations_checked,
            duplicate_citation_count=duplicate_count,
            unsupported_claims=unsupported,
            hallucination_count=hallucinations,
            verification_time=duration,
            overall_confidence=overall_confidence,
            average_claim_confidence=avg_confidence,
        )

    @staticmethod
    def _build_report(
        claim_results_list: list,
        citation_audit: list[CitationAuditResult],
        metrics: FactCheckerMetrics,
    ) -> VerificationReport:
        """Assembles VerificationReport from claim results and citation audit.

        Args:
            claim_results_list: ClaimResult list from FactValidator.
            citation_audit: CitationAuditResult list from CitationVerifier.
            metrics: Computed FactCheckerMetrics.

        Returns:
            VerificationReport instance with overall status.
        """
        # Determine overall verification status based on confidence and hallucinations
        if metrics.hallucination_count > 0:
            overall_status = VerificationStatus.HALLUCINATION_SUSPECTED
        elif metrics.overall_confidence >= 0.80:
            overall_status = VerificationStatus.VERIFIED
        elif metrics.overall_confidence >= 0.50:
            overall_status = VerificationStatus.PARTIALLY_VERIFIED
        elif metrics.overall_confidence > 0.0:
            overall_status = VerificationStatus.UNVERIFIED
        else:
            overall_status = VerificationStatus.UNVERIFIED

        citation_audit_dicts = [
            {
                "url": r.url,
                "title": r.title,
                "status": r.status,
                "matched_document_title": r.matched_document_title,
            }
            for r in citation_audit
        ]

        return VerificationReport(
            overall_status=overall_status,
            claims_checked=metrics.claims_found,
            claims_verified=metrics.claims_verified,
            unsupported_claims=metrics.unsupported_claims,
            hallucination_count=metrics.hallucination_count,
            overall_confidence=metrics.overall_confidence,
            claim_results=claim_results_list,
            citation_audit=citation_audit_dicts,
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
            logger.error(f"FactCheckerWorker event emission exception: {e}")

    async def shutdown(self) -> bool:
        """Shuts down FactCheckerWorker and transitions state to STOPPED.

        Returns:
            bool: True if shutdown completed cleanly.
        """
        self.state = WorkerState.STOPPED
        logger.info(f"Shutdown Production FactCheckerWorker '{self.worker_id}'")
        return True

    async def health_check(self) -> bool:
        """Audits worker health.

        Returns:
            bool: True if worker is not STOPPED.
        """
        return self.state != WorkerState.STOPPED

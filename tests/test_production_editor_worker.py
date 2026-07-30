"""Comprehensive test suite for the Production Editor Worker subsystem.

Tests cover:
- EditedDraftPackage model: defaults, serialization, field validation.
- EditingPromptBuilder: prompt assembly, claim/citation/keyword blocks.
- EditValidator: citation preservation, keyword preservation, readability, grammar, style.
- EditorWorker: full pipeline, AI failure fallback, approval gate, lifecycle,
  events, serialization, concurrent execution, dependency injection.
"""

import asyncio
import json
from unittest.mock import AsyncMock

import pytest

from modules.workforce.bus import MessageBus
from modules.workforce.context import SharedContext
from modules.workforce.models import Task, TaskPriority
from modules.workforce.workers.draft_models import DraftPackage, WritingStyle
from modules.workforce.workers.edit_validator import EditValidator
from modules.workforce.workers.editing_prompt_builder import EditingPromptBuilder
from modules.workforce.workers.editor_metrics import EditorWorkerMetrics
from modules.workforce.workers.editor_models import EditedDraftPackage, EditQualityScores
from modules.workforce.workers.editor_worker import EditorWorker
from modules.workforce.workers.verification_models import (
    ClaimResult,
    VerificationReport,
    VerificationStatus,
    VerifiedDraftPackage,
)

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_draft_text() -> str:
    return """# AI Adoption in 2024

In 2024, over 78% of enterprise software teams adopted some form of AI tooling.
The market grew by $1.2 billion in Q3 2024 alone.

## Key Findings

Python is the most popular language for AI development.
TensorFlow has been downloaded more than 100 million times.

Visit https://tensorflow.org/about for more information.
See the full analysis at https://gartner.com/report-2024 for details.

## Conclusion

AI adoption will continue to accelerate in the coming years.
Subscribe for updates on the latest AI trends.
"""


@pytest.fixture
def sample_draft_package(sample_draft_text: str) -> DraftPackage:
    return DraftPackage(
        title="AI Adoption in 2024",
        subtitle="A comprehensive overview",
        platform="Blog",
        content_format="Article",
        audience="Developers",
        objective="EDUCATIONAL",
        writing_style=WritingStyle.AUTHORITATIVE,
        draft=sample_draft_text,
        draft_version=1,
        citations_used=[
            {"url": "https://tensorflow.org/about", "title": "TensorFlow About"},
            {"url": "https://gartner.com/report-2024", "title": "Gartner AI Report"},
        ],
        seo_keywords=["AI", "2024", "enterprise", "TensorFlow"],
    )


@pytest.fixture
def sample_verification_report() -> VerificationReport:
    return VerificationReport(
        overall_status=VerificationStatus.VERIFIED,
        claims_checked=3,
        claims_verified=3,
        overall_confidence=0.85,
        claim_results=[
            ClaimResult(
                claim_text="78% of enterprise teams adopted AI tooling",
                category="statistic",
                status=VerificationStatus.VERIFIED,
                confidence=0.90,
            ),
            ClaimResult(
                claim_text="Market grew by $1.2 billion in Q3 2024",
                category="statistic",
                status=VerificationStatus.VERIFIED,
                confidence=0.85,
            ),
        ],
    )


@pytest.fixture
def sample_verified_draft_package(
    sample_draft_package: DraftPackage,
    sample_verification_report: VerificationReport,
) -> VerifiedDraftPackage:
    return VerifiedDraftPackage(
        draft_package=sample_draft_package,
        verification_report=sample_verification_report,
        is_approved_for_edit=True,
        requires_human_review=False,
    )


@pytest.fixture
def unapproved_verified_draft_package(
    sample_draft_package: DraftPackage,
    sample_verification_report: VerificationReport,
) -> VerifiedDraftPackage:
    return VerifiedDraftPackage(
        draft_package=sample_draft_package,
        verification_report=sample_verification_report,
        is_approved_for_edit=False,
        requires_human_review=True,
    )


@pytest.fixture
def mock_ai_provider(sample_draft_text: str) -> AsyncMock:
    provider = AsyncMock()
    # Simulate AI editing: return slightly improved version preserving content
    edited = sample_draft_text.replace(
        "In 2024, over 78%",
        "Throughout 2024, an impressive 78%",
    ).replace(
        "AI adoption will continue",
        "AI adoption is poised to continue",
    )
    provider.generate = AsyncMock(return_value=edited)
    return provider


@pytest.fixture
def editor_worker(mock_ai_provider: AsyncMock) -> EditorWorker:
    bus = MessageBus()
    return EditorWorker(ai_provider=mock_ai_provider, bus=bus)


@pytest.fixture
def shared_context() -> SharedContext:
    return SharedContext()


def _make_task(payload: dict) -> Task:
    return Task(type="editing", creator="test_suite", payload=payload, priority=TaskPriority.NORMAL)


# ===========================================================================
# EditedDraftPackage Model Tests
# ===========================================================================


class TestEditedDraftPackageModel:
    """Unit tests for EditedDraftPackage and EditQualityScores models."""

    def test_edit_quality_scores_defaults(self):
        scores = EditQualityScores()
        assert scores.readability_score == 1.0
        assert scores.grammar_score == 1.0
        assert scores.style_score == 1.0
        assert scores.citation_preservation_score == 1.0
        assert scores.keyword_preservation_score == 1.0
        assert scores.overall_quality == 1.0

    def test_edit_quality_scores_custom_values(self):
        scores = EditQualityScores(
            readability_score=0.8,
            grammar_score=0.7,
            style_score=0.9,
            citation_preservation_score=1.0,
            keyword_preservation_score=0.5,
            overall_quality=0.78,
        )
        assert scores.readability_score == 0.8
        assert scores.keyword_preservation_score == 0.5

    def test_edited_draft_package_creation(
        self,
        sample_verification_report: VerificationReport,
    ):
        pkg = EditedDraftPackage(
            original_draft_version=1,
            edited_draft_version=1,
            title="Test Title",
            platform="Blog",
            content_format="Article",
            audience="Developers",
            objective="EDUCATIONAL",
            edited_content="# Edited Content\n\nImproved text.",
            verification_report=sample_verification_report,
        )
        assert pkg.title == "Test Title"
        assert pkg.original_draft_version == 1
        assert pkg.edited_draft_version == 1
        assert pkg.verification_report.overall_status == VerificationStatus.VERIFIED

    def test_edited_draft_package_defaults(
        self,
        sample_verification_report: VerificationReport,
    ):
        pkg = EditedDraftPackage(
            original_draft_version=1,
            title="T",
            platform="Blog",
            content_format="Article",
            audience="General",
            objective="EDUCATIONAL",
            edited_content="Content.",
            verification_report=sample_verification_report,
        )
        assert pkg.subtitle is None
        assert pkg.preserved_citations == []
        assert pkg.preserved_keywords == []
        assert pkg.writing_style == WritingStyle.AUTHORITATIVE
        assert pkg.editor_metadata["editor_version"] == "v0.6.6"

    def test_edited_draft_package_serialization(
        self,
        sample_verification_report: VerificationReport,
    ):
        pkg = EditedDraftPackage(
            original_draft_version=1,
            edited_draft_version=1,
            title="Serialization Test",
            platform="Blog",
            content_format="Article",
            audience="Developers",
            objective="EDUCATIONAL",
            edited_content="# Content\n\nBody text.",
            preserved_citations=[{"url": "https://example.com", "title": "Ex"}],
            preserved_keywords=["AI", "test"],
            verification_report=sample_verification_report,
        )
        data = pkg.model_dump(mode="json")
        assert "edited_content" in data
        assert "verification_report" in data
        assert "quality_scores" in data
        # Roundtrip
        restored = EditedDraftPackage.model_validate(data)
        assert restored.title == "Serialization Test"

    def test_verification_report_preserved_immutably(
        self,
        sample_verification_report: VerificationReport,
    ):
        pkg = EditedDraftPackage(
            original_draft_version=1,
            title="Immutability Test",
            platform="Blog",
            content_format="Article",
            audience="General",
            objective="EDUCATIONAL",
            edited_content="Content.",
            verification_report=sample_verification_report,
        )
        # The verification report fields should match exactly
        assert pkg.verification_report.claims_checked == 3
        assert pkg.verification_report.claims_verified == 3
        assert pkg.verification_report.overall_confidence == 0.85


# ===========================================================================
# EditorWorkerMetrics Tests
# ===========================================================================


class TestEditorWorkerMetrics:
    """Unit tests for EditorWorkerMetrics model."""

    def test_metrics_defaults(self):
        m = EditorWorkerMetrics()
        assert m.editing_time == 0.0
        assert m.readability_before == 1.0
        assert m.readability_after == 1.0
        assert m.grammar_improvement == 0.0
        assert m.citation_preservation == 1.0
        assert m.keyword_preservation == 1.0
        assert m.overall_quality == 1.0

    def test_metrics_serialization(self):
        m = EditorWorkerMetrics(editing_time=1.5, readability_before=0.7, readability_after=0.9)
        data = m.model_dump(mode="json")
        assert data["editing_time"] == 1.5
        assert data["readability_before"] == 0.7


# ===========================================================================
# EditingPromptBuilder Tests
# ===========================================================================


class TestEditingPromptBuilder:
    """Unit tests for EditingPromptBuilder prompt assembly."""

    def setup_method(self):
        self.builder = EditingPromptBuilder()

    def test_system_instruction_contains_key_constraints(self):
        instruction = self.builder.build_system_instruction()
        assert "professional copy editor" in instruction
        assert "MUST NOT change any facts" in instruction
        assert "MUST NOT remove or alter any citations" in instruction
        assert "MUST NOT add new facts" in instruction
        assert "SEO keywords" in instruction

    def test_editing_prompt_contains_original_draft(
        self,
        sample_verified_draft_package: VerifiedDraftPackage,
    ):
        prompt = self.builder.build_editing_prompt(sample_verified_draft_package)
        assert "AI Adoption in 2024" in prompt
        assert "78%" in prompt

    def test_editing_prompt_contains_citations(
        self,
        sample_verified_draft_package: VerifiedDraftPackage,
    ):
        prompt = self.builder.build_editing_prompt(sample_verified_draft_package)
        assert "https://tensorflow.org/about" in prompt
        assert "https://gartner.com/report-2024" in prompt
        assert "CITATIONS" in prompt

    def test_editing_prompt_contains_keywords(
        self,
        sample_verified_draft_package: VerifiedDraftPackage,
    ):
        prompt = self.builder.build_editing_prompt(sample_verified_draft_package)
        assert "AI" in prompt
        assert "enterprise" in prompt
        assert "TensorFlow" in prompt
        assert "SEO KEYWORDS" in prompt

    def test_editing_prompt_contains_verified_claims(
        self,
        sample_verified_draft_package: VerifiedDraftPackage,
    ):
        prompt = self.builder.build_editing_prompt(sample_verified_draft_package)
        assert "VERIFIED CLAIMS" in prompt
        assert "78% of enterprise teams adopted AI tooling" in prompt

    def test_editing_prompt_contains_style_guidance(
        self,
        sample_verified_draft_package: VerifiedDraftPackage,
    ):
        prompt = self.builder.build_editing_prompt(sample_verified_draft_package)
        assert "AUTHORITATIVE" in prompt
        assert "Developers" in prompt
        assert "Blog" in prompt

    def test_editing_prompt_constraints_block(
        self,
        sample_verified_draft_package: VerifiedDraftPackage,
    ):
        prompt = self.builder.build_editing_prompt(sample_verified_draft_package)
        assert "DO NOT change any facts" in prompt
        assert "DO NOT remove or alter any citations" in prompt

    def test_editing_prompt_empty_claims(
        self,
        sample_draft_package: DraftPackage,
    ):
        empty_report = VerificationReport()
        vdp = VerifiedDraftPackage(
            draft_package=sample_draft_package,
            verification_report=empty_report,
        )
        prompt = self.builder.build_editing_prompt(vdp)
        assert "No specific claims to preserve" in prompt

    def test_editing_prompt_empty_citations(
        self,
        sample_verification_report: VerificationReport,
    ):
        pkg = DraftPackage(
            title="No Citations",
            platform="Blog",
            content_format="Article",
            audience="General",
            objective="EDUCATIONAL",
            draft="Simple draft.",
            citations_used=[],
        )
        vdp = VerifiedDraftPackage(
            draft_package=pkg,
            verification_report=sample_verification_report,
        )
        prompt = self.builder.build_editing_prompt(vdp)
        assert "No citations to preserve" in prompt

    def test_prompt_version_attribute(self):
        assert self.builder.PROMPT_VERSION == "v1.0.0"


# ===========================================================================
# EditValidator Tests
# ===========================================================================


class TestEditValidator:
    """Unit tests for EditValidator deterministic validation."""

    def setup_method(self):
        self.validator = EditValidator()

    def test_all_citations_preserved(
        self,
        sample_draft_text: str,
        sample_verified_draft_package: VerifiedDraftPackage,
    ):
        edited = sample_draft_text  # No changes — all citations still present
        scores, issues = self.validator.validate_edit(
            sample_draft_text, edited, sample_verified_draft_package
        )
        assert scores.citation_preservation_score == 1.0
        assert not any("Citation URL missing" in i for i in issues)

    def test_citation_removed_detected(
        self,
        sample_draft_text: str,
        sample_verified_draft_package: VerifiedDraftPackage,
    ):
        # Remove one citation URL
        edited = sample_draft_text.replace("https://tensorflow.org/about", "")
        scores, issues = self.validator.validate_edit(
            sample_draft_text, edited, sample_verified_draft_package
        )
        assert scores.citation_preservation_score < 1.0
        assert any("tensorflow.org" in i for i in issues)

    def test_all_keywords_preserved(
        self,
        sample_draft_text: str,
        sample_verified_draft_package: VerifiedDraftPackage,
    ):
        scores, issues = self.validator.validate_edit(
            sample_draft_text, sample_draft_text, sample_verified_draft_package
        )
        assert scores.keyword_preservation_score == 1.0
        assert not any("SEO keyword missing" in i for i in issues)

    def test_keyword_removed_detected(
        self,
        sample_draft_text: str,
        sample_verified_draft_package: VerifiedDraftPackage,
    ):
        # Remove "enterprise" keyword from draft
        edited = sample_draft_text.replace("enterprise", "business")
        scores, issues = self.validator.validate_edit(
            sample_draft_text, edited, sample_verified_draft_package
        )
        assert scores.keyword_preservation_score < 1.0
        assert any("enterprise" in i for i in issues)

    def test_readability_scoring_optimal_range(self):
        # Sentences averaging ~15 words
        text = (
            "This is a sentence with about fifteen words in it. "
            "Here is another sentence that also has about fifteen words total. "
            "And one more sentence to round out the average word count well."
        )
        score = self.validator._estimate_readability(text)
        assert score >= 0.7

    def test_readability_scoring_long_sentences(self):
        text = (
            "This is an extremely long and overly verbose sentence that goes on and on "
            "without ever seeming to reach a natural stopping point, which makes it very "
            "difficult for readers to follow the argument being presented here in this text "
            "block and maintain their focus throughout the entire duration of the reading."
        )
        score = self.validator._estimate_readability(text)
        assert score < 0.9

    def test_grammar_improvement_estimation(self, sample_draft_text: str):
        score = self.validator._estimate_grammar_improvement(
            sample_draft_text, sample_draft_text
        )
        assert 0.0 <= score <= 1.0

    def test_style_score_with_headings(self):
        text = "# Heading\n\nParagraph one.\n\n## Sub Heading\n\nParagraph two.\n\nParagraph three."
        score = self.validator._estimate_style_score(text)
        assert score >= 0.8

    def test_style_score_without_headings(self):
        text = "Just plain text without any structure or headings."
        score = self.validator._estimate_style_score(text)
        assert score < 1.0

    def test_overall_quality_is_weighted(
        self,
        sample_draft_text: str,
        sample_verified_draft_package: VerifiedDraftPackage,
    ):
        scores, _ = self.validator.validate_edit(
            sample_draft_text, sample_draft_text, sample_verified_draft_package
        )
        assert 0.0 <= scores.overall_quality <= 1.0

    def test_empty_draft_handled(
        self,
        sample_verified_draft_package: VerifiedDraftPackage,
    ):
        scores, issues = self.validator.validate_edit(
            "", "", sample_verified_draft_package
        )
        assert isinstance(scores, EditQualityScores)

    def test_no_citations_returns_perfect_score(self):
        pkg = DraftPackage(
            title="T",
            platform="Blog",
            content_format="Article",
            audience="General",
            objective="EDUCATIONAL",
            draft="Simple.",
            citations_used=[],
            seo_keywords=[],
        )
        vdp = VerifiedDraftPackage(
            draft_package=pkg,
            verification_report=VerificationReport(),
        )
        scores, issues = self.validator.validate_edit("Simple.", "Improved.", vdp)
        assert scores.citation_preservation_score == 1.0
        assert scores.keyword_preservation_score == 1.0


# ===========================================================================
# EditorWorker Lifecycle Tests
# ===========================================================================


class TestEditorWorkerLifecycle:
    """Unit tests for EditorWorker lifecycle management."""

    @pytest.mark.asyncio
    async def test_initialize_transitions_to_ready(self, editor_worker: EditorWorker):
        result = await editor_worker.initialize()
        assert result is True
        from modules.workforce.models import WorkerState

        assert editor_worker.state == WorkerState.READY

    @pytest.mark.asyncio
    async def test_shutdown_transitions_to_stopped(self, editor_worker: EditorWorker):
        await editor_worker.initialize()
        result = await editor_worker.shutdown()
        assert result is True
        from modules.workforce.models import WorkerState

        assert editor_worker.state == WorkerState.STOPPED

    @pytest.mark.asyncio
    async def test_health_check_true_when_ready(self, editor_worker: EditorWorker):
        await editor_worker.initialize()
        assert await editor_worker.health_check() is True

    @pytest.mark.asyncio
    async def test_health_check_false_when_stopped(self, editor_worker: EditorWorker):
        await editor_worker.initialize()
        await editor_worker.shutdown()
        assert await editor_worker.health_check() is False

    def test_worker_attributes(self, editor_worker: EditorWorker):
        assert "editing" in editor_worker.capabilities
        assert "grammar_correction" in editor_worker.capabilities
        assert editor_worker.worker_name == "Production Editor Worker"
        assert editor_worker.role == "Content Editor"


# ===========================================================================
# EditorWorker Execution Tests
# ===========================================================================


class TestEditorWorkerExecution:
    """Integration tests for EditorWorker.execute() pipeline."""

    @pytest.mark.asyncio
    async def test_full_pipeline_completes_successfully(
        self,
        editor_worker: EditorWorker,
        sample_verified_draft_package: VerifiedDraftPackage,
        shared_context: SharedContext,
    ):
        await editor_worker.initialize()
        task = _make_task({
            "topic": "AI Adoption 2024",
            "verified_draft_package": sample_verified_draft_package.model_dump(mode="json"),
        })
        result = await editor_worker.execute(task, shared_context)

        assert result.status.value == "COMPLETED"
        assert "edited_draft_package" in result.artifacts
        assert result.execution_time >= 0.0
        assert len(result.logs) > 0

    @pytest.mark.asyncio
    async def test_edited_draft_package_structure(
        self,
        editor_worker: EditorWorker,
        sample_verified_draft_package: VerifiedDraftPackage,
        shared_context: SharedContext,
    ):
        await editor_worker.initialize()
        task = _make_task({
            "verified_draft_package": sample_verified_draft_package.model_dump(mode="json"),
        })
        result = await editor_worker.execute(task, shared_context)

        edp = result.artifacts["edited_draft_package"]
        assert "edited_content" in edp
        assert "preserved_citations" in edp
        assert "preserved_keywords" in edp
        assert "verification_report" in edp
        assert "quality_scores" in edp
        assert "editor_metadata" in edp
        assert edp["original_draft_version"] == 1

    @pytest.mark.asyncio
    async def test_verification_report_forwarded(
        self,
        editor_worker: EditorWorker,
        sample_verified_draft_package: VerifiedDraftPackage,
        shared_context: SharedContext,
    ):
        await editor_worker.initialize()
        task = _make_task({
            "verified_draft_package": sample_verified_draft_package.model_dump(mode="json"),
        })
        result = await editor_worker.execute(task, shared_context)

        edp = result.artifacts["edited_draft_package"]
        report = edp["verification_report"]
        assert report["claims_checked"] == 3
        assert report["claims_verified"] == 3
        assert report["overall_confidence"] == 0.85

    @pytest.mark.asyncio
    async def test_approval_gate_not_approved(
        self,
        editor_worker: EditorWorker,
        unapproved_verified_draft_package: VerifiedDraftPackage,
        shared_context: SharedContext,
    ):
        """When is_approved_for_edit=False, original draft passes through unchanged."""
        await editor_worker.initialize()
        task = _make_task({
            "verified_draft_package": unapproved_verified_draft_package.model_dump(mode="json"),
        })
        result = await editor_worker.execute(task, shared_context)

        assert result.status.value == "COMPLETED"
        edp = result.artifacts["edited_draft_package"]
        # Passthrough should have edit_pass_count=0
        assert edp["editor_metadata"]["passthrough"] is True
        assert edp["editor_metadata"]["edit_pass_count"] == 0
        # Content should be original
        assert edp["edited_content"] == unapproved_verified_draft_package.draft_package.draft

    @pytest.mark.asyncio
    async def test_ai_failure_fallback_to_original(
        self,
        sample_verified_draft_package: VerifiedDraftPackage,
        shared_context: SharedContext,
    ):
        """When AI provider fails, original draft is used as fallback."""
        failing_provider = AsyncMock()
        failing_provider.generate = AsyncMock(side_effect=RuntimeError("AI unavailable"))

        worker = EditorWorker(ai_provider=failing_provider, bus=MessageBus())
        await worker.initialize()
        task = _make_task({
            "verified_draft_package": sample_verified_draft_package.model_dump(mode="json"),
        })
        result = await worker.execute(task, shared_context)

        assert result.status.value == "COMPLETED"
        edp = result.artifacts["edited_draft_package"]
        assert edp["edited_content"] == sample_verified_draft_package.draft_package.draft

    @pytest.mark.asyncio
    async def test_ai_returns_empty_fallback(
        self,
        sample_verified_draft_package: VerifiedDraftPackage,
        shared_context: SharedContext,
    ):
        """When AI returns empty string, original draft is used."""
        empty_provider = AsyncMock()
        empty_provider.generate = AsyncMock(return_value="")

        worker = EditorWorker(ai_provider=empty_provider, bus=MessageBus())
        await worker.initialize()
        task = _make_task({
            "verified_draft_package": sample_verified_draft_package.model_dump(mode="json"),
        })
        result = await worker.execute(task, shared_context)

        assert result.status.value == "COMPLETED"
        edp = result.artifacts["edited_draft_package"]
        assert edp["edited_content"] == sample_verified_draft_package.draft_package.draft

    @pytest.mark.asyncio
    async def test_missing_verified_draft_package_returns_failed(
        self,
        editor_worker: EditorWorker,
        shared_context: SharedContext,
    ):
        await editor_worker.initialize()
        task = _make_task({"topic": "Missing input"})
        result = await editor_worker.execute(task, shared_context)
        assert result.status.value == "FAILED"
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_metrics_populated_in_result(
        self,
        editor_worker: EditorWorker,
        sample_verified_draft_package: VerifiedDraftPackage,
        shared_context: SharedContext,
    ):
        await editor_worker.initialize()
        task = _make_task({
            "verified_draft_package": sample_verified_draft_package.model_dump(mode="json"),
        })
        result = await editor_worker.execute(task, shared_context)
        metrics = result.metrics
        assert "editing_time" in metrics
        assert "readability_before" in metrics
        assert "readability_after" in metrics
        assert "grammar_improvement" in metrics
        assert "citation_preservation" in metrics
        assert "keyword_preservation" in metrics
        assert "overall_quality" in metrics

    @pytest.mark.asyncio
    async def test_events_emitted_during_execution(
        self,
        sample_verified_draft_package: VerifiedDraftPackage,
        shared_context: SharedContext,
        mock_ai_provider: AsyncMock,
    ):
        bus = MessageBus()
        emitted_events: list[str] = []

        async def capture_event(event):
            emitted_events.append(event.event_type)

        bus.add_event_listener("EditingStarted", capture_event)
        bus.add_event_listener("DraftEdited", capture_event)
        bus.add_event_listener("EditingCompleted", capture_event)

        worker = EditorWorker(ai_provider=mock_ai_provider, bus=bus)
        await worker.initialize()
        task = _make_task({
            "verified_draft_package": sample_verified_draft_package.model_dump(mode="json"),
        })
        await worker.execute(task, shared_context)

        assert "EditingStarted" in emitted_events
        assert "DraftEdited" in emitted_events
        assert "EditingCompleted" in emitted_events

    @pytest.mark.asyncio
    async def test_failure_event_emitted_on_error(self, shared_context: SharedContext):
        bus = MessageBus()
        emitted_events: list[str] = []

        async def capture_event(event):
            emitted_events.append(event.event_type)

        bus.add_event_listener("EditingFailed", capture_event)

        provider = AsyncMock()
        worker = EditorWorker(ai_provider=provider, bus=bus)
        await worker.initialize()
        task = _make_task({"topic": "No verified package"})
        await worker.execute(task, shared_context)

        assert "EditingFailed" in emitted_events

    @pytest.mark.asyncio
    async def test_serialization_roundtrip(
        self,
        editor_worker: EditorWorker,
        sample_verified_draft_package: VerifiedDraftPackage,
        shared_context: SharedContext,
    ):
        await editor_worker.initialize()
        task = _make_task({
            "verified_draft_package": sample_verified_draft_package.model_dump(mode="json"),
        })
        result = await editor_worker.execute(task, shared_context)
        result_json = json.dumps(result.model_dump(mode="json"))
        restored = json.loads(result_json)
        assert restored["status"] == "COMPLETED"
        assert "edited_draft_package" in restored["artifacts"]

    @pytest.mark.asyncio
    async def test_concurrent_execution(
        self,
        sample_verified_draft_package: VerifiedDraftPackage,
        shared_context: SharedContext,
    ):
        workers = []
        for i in range(3):
            provider = AsyncMock()
            provider.generate = AsyncMock(return_value="# Edited\n\nConcurrent test content.")
            workers.append(EditorWorker(worker_id=f"worker_editor_{i}", ai_provider=provider, bus=MessageBus()))

        for w in workers:
            await w.initialize()

        task = _make_task({
            "verified_draft_package": sample_verified_draft_package.model_dump(mode="json"),
        })

        results = await asyncio.gather(*[w.execute(task, shared_context) for w in workers])
        assert all(r.status.value == "COMPLETED" for r in results)
        worker_ids = {r.worker_id for r in results}
        assert len(worker_ids) == 3

    @pytest.mark.asyncio
    async def test_dependency_injection_custom_components(
        self,
        sample_verified_draft_package: VerifiedDraftPackage,
        shared_context: SharedContext,
    ):
        custom_provider = AsyncMock()
        custom_provider.generate = AsyncMock(return_value="# Custom Edited\n\nCustom content.")
        custom_builder = EditingPromptBuilder()
        custom_validator = EditValidator()

        worker = EditorWorker(
            ai_provider=custom_provider,
            prompt_builder=custom_builder,
            edit_validator=custom_validator,
            bus=MessageBus(),
        )
        await worker.initialize()
        task = _make_task({
            "verified_draft_package": sample_verified_draft_package.model_dump(mode="json"),
        })
        result = await worker.execute(task, shared_context)
        assert result.status.value == "COMPLETED"

    @pytest.mark.asyncio
    async def test_citations_preserved_in_output(
        self,
        editor_worker: EditorWorker,
        sample_verified_draft_package: VerifiedDraftPackage,
        shared_context: SharedContext,
    ):
        await editor_worker.initialize()
        task = _make_task({
            "verified_draft_package": sample_verified_draft_package.model_dump(mode="json"),
        })
        result = await editor_worker.execute(task, shared_context)
        edp = result.artifacts["edited_draft_package"]
        assert len(edp["preserved_citations"]) == 2
        urls = [c["url"] for c in edp["preserved_citations"]]
        assert "https://tensorflow.org/about" in urls

    @pytest.mark.asyncio
    async def test_keywords_preserved_in_output(
        self,
        editor_worker: EditorWorker,
        sample_verified_draft_package: VerifiedDraftPackage,
        shared_context: SharedContext,
    ):
        await editor_worker.initialize()
        task = _make_task({
            "verified_draft_package": sample_verified_draft_package.model_dump(mode="json"),
        })
        result = await editor_worker.execute(task, shared_context)
        edp = result.artifacts["edited_draft_package"]
        assert "AI" in edp["preserved_keywords"]
        assert "TensorFlow" in edp["preserved_keywords"]

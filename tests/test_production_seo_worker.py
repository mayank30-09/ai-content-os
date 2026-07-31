"""Comprehensive test suite for the Production SEO Worker subsystem.

Tests cover:
- SEOOptimizedPackage model: defaults, serialization, lineage immutability.
- SEOScores model: defaults, custom values.
- SEOAnalysisResult model: construction, sub-model embedding.
- SEOWorkerMetrics model: defaults, serialization.
- SEOAnalyzer: keyword density, heading hierarchy, meta fitness, FAQ detection,
  schema detection, empty content, content scoring.
- SEOPromptBuilder: system instruction, full prompt, keyword block, constraints,
  heading guidance, meta block, empty inputs, prompt version.
- SEOValidator: citation preservation, keyword preservation, heading quality,
  meta quality, keyword density scoring, overall score, empty content, no citations.
- SEOWorker: full pipeline, package structure, lineage forwarded, AI failure
  fallback, AI empty fallback, missing input, metrics, events, failure event,
  serialization roundtrip, JSON parsing.
"""

import json
from unittest.mock import AsyncMock

import pytest

from modules.workforce.bus import MessageBus
from modules.workforce.context import SharedContext
from modules.workforce.models import Task, TaskPriority
from modules.workforce.workers.draft_models import WritingStyle
from modules.workforce.workers.editor_models import EditedDraftPackage, EditQualityScores
from modules.workforce.workers.seo_analyzer import SEOAnalyzer
from modules.workforce.workers.seo_metrics import SEOWorkerMetrics
from modules.workforce.workers.seo_models import (
    HeadingAnalysis,
    MetaAnalysis,
    SEOAnalysisResult,
    SEOOptimizedPackage,
    SEOScores,
)
from modules.workforce.workers.seo_prompt_builder import SEOPromptBuilder
from modules.workforce.workers.seo_validator import SEOValidator
from modules.workforce.workers.seo_worker import SEOWorker
from modules.workforce.workers.verification_models import (
    ClaimResult,
    VerificationReport,
    VerificationStatus,
)

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_content() -> str:
    return """# AI Adoption in 2024

In 2024, over 78% of enterprise software teams adopted some form of AI tooling.
The market grew by $1.2 billion in Q3 2024 alone.

## Key Findings

Python is the most popular language for AI development.
TensorFlow has been downloaded more than 100 million times.

Visit https://tensorflow.org/about for more information.
See the full analysis at https://gartner.com/report-2024 for details.

## How to Get Started

Step 1. Choose your AI framework.
Step 2. Set up your development environment.
Step 3. Train your first model.

## Conclusion

AI adoption will continue to accelerate in the coming years.
Subscribe for updates on the latest AI trends.
"""


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
        ],
    )


@pytest.fixture
def sample_quality_scores() -> EditQualityScores:
    return EditQualityScores(
        readability_score=0.88,
        grammar_score=0.90,
        style_score=0.85,
        citation_preservation_score=1.0,
        keyword_preservation_score=1.0,
        overall_quality=0.89,
    )


@pytest.fixture
def sample_edited_draft_package(
    sample_content: str,
    sample_verification_report: VerificationReport,
    sample_quality_scores: EditQualityScores,
) -> EditedDraftPackage:
    return EditedDraftPackage(
        original_draft_version=1,
        edited_draft_version=1,
        title="AI Adoption in 2024",
        subtitle="A comprehensive overview",
        platform="Blog",
        content_format="Article",
        audience="Developers",
        objective="EDUCATIONAL",
        writing_style=WritingStyle.AUTHORITATIVE,
        edited_content=sample_content,
        preserved_citations=[
            {"url": "https://tensorflow.org/about", "title": "TensorFlow About"},
            {"url": "https://gartner.com/report-2024", "title": "Gartner AI Report"},
        ],
        preserved_keywords=["AI", "2024", "enterprise", "TensorFlow"],
        verification_report=sample_verification_report,
        quality_scores=sample_quality_scores,
    )


@pytest.fixture
def mock_ai_provider(sample_content: str) -> AsyncMock:
    provider = AsyncMock()
    # Return structured JSON with optimized content
    ai_response = json.dumps({
        "optimized_content": sample_content.replace(
            "# AI Adoption in 2024",
            "# AI Adoption in 2024: Enterprise AI Trends and Statistics",
        ),
        "meta_title": "AI Adoption in 2024: Enterprise AI Trends",
        "meta_description": "Discover how 78% of enterprise teams adopted AI in 2024. Explore key findings on TensorFlow adoption and market growth.",
        "faq_section": [
            {"question": "What percentage of teams adopted AI?", "answer": "78% of enterprise software teams adopted AI tooling in 2024."},
        ],
        "schema_markup": {
            "@type": "Article",
            "headline": "AI Adoption in 2024",
            "author": "{{AUTHOR}}",
            "datePublished": "{{DATE}}",
            "url": "{{CANONICAL_URL}}",
        },
        "internal_link_suggestions": [
            {"anchor_text": "Python AI frameworks", "target_topic": "python-ai-frameworks", "rationale": "Related concept"},
        ],
        "external_link_suggestions": [
            {"anchor_text": "TensorFlow documentation", "target_topic": "tensorflow-docs", "rationale": "Authoritative source"},
        ],
        "image_alt_suggestions": [
            {"image_ref": "hero_image", "alt_text": "AI adoption statistics chart for 2024"},
        ],
    })
    provider.generate = AsyncMock(return_value=ai_response)
    return provider


@pytest.fixture
def seo_worker(mock_ai_provider: AsyncMock) -> SEOWorker:
    bus = MessageBus()
    return SEOWorker(ai_provider=mock_ai_provider, bus=bus)


@pytest.fixture
def shared_context() -> SharedContext:
    return SharedContext()


def _make_task(payload: dict) -> Task:
    return Task(type="seo_optimization", creator="test_suite", payload=payload, priority=TaskPriority.NORMAL)


# ===========================================================================
# SEOScores Model Tests
# ===========================================================================


class TestSEOScoresModel:
    """Unit tests for SEOScores model."""

    def test_seo_scores_defaults(self):
        scores = SEOScores()
        assert scores.keyword_density_score == 1.0
        assert scores.heading_quality_score == 1.0
        assert scores.meta_quality_score == 1.0
        assert scores.citation_preservation_score == 1.0
        assert scores.keyword_preservation_score == 1.0
        assert scores.content_structure_score == 1.0
        assert scores.overall_seo_score == 1.0

    def test_seo_scores_custom_values(self):
        scores = SEOScores(
            keyword_density_score=0.8,
            heading_quality_score=0.9,
            meta_quality_score=0.7,
            overall_seo_score=0.82,
        )
        assert scores.keyword_density_score == 0.8
        assert scores.overall_seo_score == 0.82


# ===========================================================================
# SEOAnalysisResult Model Tests
# ===========================================================================


class TestSEOAnalysisResultModel:
    """Unit tests for SEOAnalysisResult model."""

    def test_analysis_result_defaults(self):
        result = SEOAnalysisResult()
        assert result.current_keyword_density == 0.0
        assert result.content_length == 0
        assert result.content_score == 0.0
        assert isinstance(result.heading_analysis, HeadingAnalysis)
        assert isinstance(result.meta_analysis, MetaAnalysis)

    def test_analysis_result_construction(self):
        heading = HeadingAnalysis(has_h1=True, heading_count=3, heading_hierarchy_valid=True)
        meta = MetaAnalysis(title_length=30, title_has_keyword=True)
        result = SEOAnalysisResult(
            current_keyword_density=2.1,
            heading_analysis=heading,
            meta_analysis=meta,
            content_length=500,
            content_score=0.75,
        )
        assert result.current_keyword_density == 2.1
        assert result.heading_analysis.has_h1 is True
        assert result.meta_analysis.title_has_keyword is True


# ===========================================================================
# SEOOptimizedPackage Model Tests
# ===========================================================================


class TestSEOOptimizedPackageModel:
    """Unit tests for SEOOptimizedPackage model."""

    def test_package_creation(
        self,
        sample_verification_report: VerificationReport,
        sample_quality_scores: EditQualityScores,
    ):
        pkg = SEOOptimizedPackage(
            title="Test Title",
            meta_title="Test Meta Title",
            meta_description="Test meta description for SEO.",
            slug="test-title",
            focus_keyword="test",
            optimized_content="# Test\n\nOptimized content.",
            verification_report=sample_verification_report,
            quality_scores=sample_quality_scores,
            platform="Blog",
            content_format="Article",
            audience="Developers",
            objective="EDUCATIONAL",
        )
        assert pkg.title == "Test Title"
        assert pkg.meta_title == "Test Meta Title"
        assert pkg.slug == "test-title"
        assert pkg.verification_report.claims_checked == 3

    def test_package_defaults(
        self,
        sample_verification_report: VerificationReport,
    ):
        pkg = SEOOptimizedPackage(
            title="T",
            optimized_content="Content.",
            verification_report=sample_verification_report,
            platform="Blog",
            content_format="Article",
            audience="General",
            objective="EDUCATIONAL",
        )
        assert pkg.meta_title == ""
        assert pkg.meta_description == ""
        assert pkg.slug == ""
        assert pkg.faq_section == []
        assert pkg.internal_link_suggestions == []
        assert pkg.external_link_suggestions == []
        assert pkg.schema_markup == {}
        assert pkg.image_alt_suggestions == []
        assert pkg.optimization_metadata["seo_version"] == "v0.6.7"

    def test_package_serialization_roundtrip(
        self,
        sample_verification_report: VerificationReport,
        sample_quality_scores: EditQualityScores,
    ):
        pkg = SEOOptimizedPackage(
            title="Serialization Test",
            meta_title="Ser Test",
            meta_description="Description.",
            slug="serialization-test",
            focus_keyword="serialization",
            optimized_content="# Content\n\nBody.",
            verification_report=sample_verification_report,
            quality_scores=sample_quality_scores,
            platform="Blog",
            content_format="Article",
            audience="Developers",
            objective="EDUCATIONAL",
            faq_section=[{"question": "Q?", "answer": "A."}],
            schema_markup={"@type": "Article", "author": "{{AUTHOR}}"},
        )
        data = pkg.model_dump(mode="json")
        assert "optimized_content" in data
        assert "verification_report" in data
        assert "seo_scores" in data
        restored = SEOOptimizedPackage.model_validate(data)
        assert restored.title == "Serialization Test"

    def test_lineage_preserved_immutably(
        self,
        sample_verification_report: VerificationReport,
        sample_quality_scores: EditQualityScores,
    ):
        pkg = SEOOptimizedPackage(
            title="Lineage",
            optimized_content="C.",
            verification_report=sample_verification_report,
            quality_scores=sample_quality_scores,
            platform="Blog",
            content_format="Article",
            audience="G",
            objective="E",
        )
        assert pkg.verification_report.claims_checked == 3
        assert pkg.verification_report.overall_confidence == 0.85
        assert pkg.quality_scores.readability_score == 0.88

    def test_hybrid_link_suggestions(
        self,
        sample_verification_report: VerificationReport,
    ):
        pkg = SEOOptimizedPackage(
            title="Links",
            optimized_content="C.",
            verification_report=sample_verification_report,
            platform="Blog",
            content_format="Article",
            audience="G",
            objective="E",
            internal_link_suggestions=[
                {"anchor_text": "Python Memory", "target_topic": "python-memory", "rationale": "Related"},
            ],
            external_link_suggestions=[
                {"anchor_text": "TF Docs", "target_topic": "tensorflow-docs", "rationale": "Auth source"},
            ],
        )
        assert len(pkg.internal_link_suggestions) == 1
        assert pkg.internal_link_suggestions[0]["target_topic"] == "python-memory"
        # No final URLs — only topics
        assert "url" not in pkg.internal_link_suggestions[0] or pkg.internal_link_suggestions[0].get("url") is None

    def test_schema_template_placeholders(
        self,
        sample_verification_report: VerificationReport,
    ):
        pkg = SEOOptimizedPackage(
            title="Schema",
            optimized_content="C.",
            verification_report=sample_verification_report,
            platform="Blog",
            content_format="Article",
            audience="G",
            objective="E",
            schema_markup={
                "@type": "Article",
                "headline": "Schema",
                "author": "{{AUTHOR}}",
                "datePublished": "{{DATE}}",
                "url": "{{CANONICAL_URL}}",
            },
        )
        assert pkg.schema_markup["author"] == "{{AUTHOR}}"
        assert pkg.schema_markup["datePublished"] == "{{DATE}}"
        assert pkg.schema_markup["url"] == "{{CANONICAL_URL}}"


# ===========================================================================
# SEOWorkerMetrics Tests
# ===========================================================================


class TestSEOWorkerMetrics:
    """Unit tests for SEOWorkerMetrics model."""

    def test_metrics_defaults(self):
        m = SEOWorkerMetrics()
        assert m.optimization_time == 0.0
        assert m.seo_score_before == 0.0
        assert m.seo_score_after == 0.0
        assert m.faq_generated is False
        assert m.schema_generated is False

    def test_metrics_serialization(self):
        m = SEOWorkerMetrics(optimization_time=1.5, seo_score_before=0.4, seo_score_after=0.8)
        data = m.model_dump(mode="json")
        assert data["optimization_time"] == 1.5
        assert data["seo_score_before"] == 0.4


# ===========================================================================
# SEOAnalyzer Tests
# ===========================================================================


class TestSEOAnalyzer:
    """Unit tests for SEOAnalyzer deterministic analysis."""

    def setup_method(self):
        self.analyzer = SEOAnalyzer()

    def test_keyword_density_calculation(self, sample_content: str):
        density = self.analyzer._calculate_keyword_density(sample_content, "AI")
        assert density > 0.0

    def test_keyword_density_empty_content(self):
        density = self.analyzer._calculate_keyword_density("", "AI")
        assert density == 0.0

    def test_keyword_density_empty_keyword(self, sample_content: str):
        density = self.analyzer._calculate_keyword_density(sample_content, "")
        assert density == 0.0

    def test_heading_structure_valid(self, sample_content: str):
        analysis = self.analyzer._analyze_heading_structure(sample_content)
        assert analysis.has_h1 is True
        assert analysis.heading_count >= 3
        assert len(analysis.headings) >= 3

    def test_heading_structure_no_headings(self):
        analysis = self.analyzer._analyze_heading_structure("Just plain text.")
        assert analysis.has_h1 is False
        assert analysis.heading_count == 0

    def test_heading_hierarchy_skip_detected(self):
        content = "# H1\n\n### H3 Skipping H2\n\nContent."
        analysis = self.analyzer._analyze_heading_structure(content)
        assert analysis.heading_hierarchy_valid is False
        assert any("skip" in i.lower() for i in analysis.issues)

    def test_meta_fitness_analysis(self):
        analysis = self.analyzer._analyze_meta_fitness("AI Adoption in 2024", "AI")
        assert analysis.title_has_keyword is True
        assert analysis.title_length == 19
        assert analysis.suggested_slug != ""

    def test_meta_fitness_missing_keyword(self):
        analysis = self.analyzer._analyze_meta_fitness("Technology Trends", "AI")
        assert analysis.title_has_keyword is False
        assert any("Focus keyword" in i for i in analysis.issues)

    def test_faq_opportunities_detected(self, sample_content: str):
        # Content with question-like sentences
        content_with_questions = sample_content + "\nHow does AI impact productivity?\nWhat tools are best for beginners?\n"
        faqs = self.analyzer._detect_faq_opportunities(content_with_questions)
        assert len(faqs) >= 1

    def test_schema_opportunities_detected(self, sample_content: str):
        schemas = self.analyzer._detect_schema_opportunities(sample_content, "AI Adoption")
        assert "Article" in schemas

    def test_howto_schema_detected(self, sample_content: str):
        schemas = self.analyzer._detect_schema_opportunities(sample_content, "AI")
        assert "HowTo" in schemas  # Content has "Step 1.", "Step 2."

    def test_full_analyze(self, sample_content: str):
        result = self.analyzer.analyze(
            content=sample_content,
            title="AI Adoption in 2024",
            focus_keyword="AI",
            secondary_keywords=["enterprise", "TensorFlow"],
            citations=[{"url": "https://tensorflow.org/about"}],
        )
        assert isinstance(result, SEOAnalysisResult)
        assert result.content_length > 0
        assert 0.0 <= result.content_score <= 1.0

    def test_slug_generation(self):
        slug = SEOAnalyzer._generate_slug("AI Adoption in 2024: A Comprehensive Guide!")
        assert slug == "ai-adoption-in-2024-a-comprehensive-guide"

    def test_slug_empty_title(self):
        slug = SEOAnalyzer._generate_slug("")
        assert slug == ""

    def test_content_score_high_quality(self):
        heading = HeadingAnalysis(has_h1=True, heading_count=5, heading_hierarchy_valid=True)
        meta = MetaAnalysis(title_length=30, title_has_keyword=True)
        score = self.analyzer._calculate_content_score(2.0, heading, meta, 1200)
        assert score >= 0.8


# ===========================================================================
# SEOPromptBuilder Tests
# ===========================================================================


class TestSEOPromptBuilder:
    """Unit tests for SEOPromptBuilder prompt assembly."""

    def setup_method(self):
        self.builder = SEOPromptBuilder()

    def test_system_instruction_key_constraints(self):
        instruction = self.builder.build_system_instruction()
        assert "SEO specialist" in instruction
        assert "MUST NOT invent facts" in instruction
        assert "MUST NOT remove or alter any citations" in instruction
        assert "valid JSON" in instruction

    def test_optimization_prompt_contains_content(
        self,
        sample_edited_draft_package: EditedDraftPackage,
    ):
        analysis = SEOAnalysisResult(content_length=100, content_score=0.5)
        prompt = self.builder.build_optimization_prompt(sample_edited_draft_package, analysis)
        assert "AI Adoption in 2024" in prompt
        assert "78%" in prompt

    def test_optimization_prompt_contains_keywords(
        self,
        sample_edited_draft_package: EditedDraftPackage,
    ):
        analysis = SEOAnalysisResult()
        prompt = self.builder.build_optimization_prompt(sample_edited_draft_package, analysis)
        assert "AI" in prompt
        assert "TARGET KEYWORDS" in prompt

    def test_optimization_prompt_contains_constraints(
        self,
        sample_edited_draft_package: EditedDraftPackage,
    ):
        analysis = SEOAnalysisResult()
        prompt = self.builder.build_optimization_prompt(sample_edited_draft_package, analysis)
        assert "DO NOT change any facts" in prompt
        assert "DO NOT remove or alter any citations" in prompt
        assert "{{PLACEHOLDER}}" in prompt or "{{AUTHOR}}" in prompt

    def test_optimization_prompt_json_format(
        self,
        sample_edited_draft_package: EditedDraftPackage,
    ):
        analysis = SEOAnalysisResult()
        prompt = self.builder.build_optimization_prompt(sample_edited_draft_package, analysis)
        assert "JSON" in prompt
        assert "meta_title" in prompt
        assert "meta_description" in prompt
        assert "faq_section" in prompt
        assert "schema_markup" in prompt
        assert "internal_link_suggestions" in prompt
        assert "anchor_text" in prompt
        assert "target_topic" in prompt

    def test_prompt_with_citations(
        self,
        sample_edited_draft_package: EditedDraftPackage,
    ):
        analysis = SEOAnalysisResult()
        prompt = self.builder.build_optimization_prompt(sample_edited_draft_package, analysis)
        assert "https://tensorflow.org/about" in prompt
        assert "CITATIONS" in prompt

    def test_empty_keywords_handled(
        self,
        sample_verification_report: VerificationReport,
    ):
        pkg = EditedDraftPackage(
            original_draft_version=1,
            title="No Keywords",
            platform="Blog",
            content_format="Article",
            audience="G",
            objective="E",
            edited_content="Simple content.",
            verification_report=sample_verification_report,
            preserved_keywords=[],
        )
        analysis = SEOAnalysisResult()
        prompt = self.builder.build_optimization_prompt(pkg, analysis)
        assert "No keywords specified" in prompt

    def test_prompt_version_attribute(self):
        assert self.builder.PROMPT_VERSION == "v1.0.0"


# ===========================================================================
# SEOValidator Tests
# ===========================================================================


class TestSEOValidator:
    """Unit tests for SEOValidator deterministic validation."""

    def setup_method(self):
        self.validator = SEOValidator()

    def test_all_citations_preserved(
        self,
        sample_content: str,
        sample_edited_draft_package: EditedDraftPackage,
    ):
        analysis = SEOAnalysisResult()
        scores, issues = self.validator.validate_optimization(
            sample_content, sample_content, sample_edited_draft_package, analysis,
            meta_title="AI Adoption", meta_description="Description here.",
        )
        assert scores.citation_preservation_score == 1.0
        assert not any("Citation URL missing" in i for i in issues)

    def test_citation_removed_detected(
        self,
        sample_content: str,
        sample_edited_draft_package: EditedDraftPackage,
    ):
        optimized = sample_content.replace("https://tensorflow.org/about", "")
        analysis = SEOAnalysisResult()
        scores, issues = self.validator.validate_optimization(
            sample_content, optimized, sample_edited_draft_package, analysis,
        )
        assert scores.citation_preservation_score < 1.0
        assert any("tensorflow.org" in i for i in issues)

    def test_all_keywords_preserved(
        self,
        sample_content: str,
        sample_edited_draft_package: EditedDraftPackage,
    ):
        analysis = SEOAnalysisResult()
        scores, issues = self.validator.validate_optimization(
            sample_content, sample_content, sample_edited_draft_package, analysis,
        )
        assert scores.keyword_preservation_score == 1.0

    def test_keyword_removed_detected(
        self,
        sample_content: str,
        sample_edited_draft_package: EditedDraftPackage,
    ):
        optimized = sample_content.replace("enterprise", "business")
        analysis = SEOAnalysisResult()
        scores, issues = self.validator.validate_optimization(
            sample_content, optimized, sample_edited_draft_package, analysis,
        )
        assert scores.keyword_preservation_score < 1.0
        assert any("enterprise" in i for i in issues)

    def test_heading_quality_with_valid_structure(self, sample_content: str):
        score = self.validator._score_heading_quality(sample_content)
        assert score >= 0.7

    def test_heading_quality_no_headings(self):
        score = self.validator._score_heading_quality("Just text without headings.")
        assert score <= 0.5

    def test_meta_quality_valid(self):
        score = self.validator._score_meta_quality("Good Title", "Good description.", [])
        assert score == 1.0

    def test_meta_quality_too_long(self):
        issues: list[str] = []
        score = self.validator._score_meta_quality("A" * 70, "B" * 170, issues)
        assert score < 1.0
        assert len(issues) >= 1

    def test_keyword_density_optimal(self):
        # Build content with ~2% keyword density
        content = ("AI " * 20) + ("other words " * 980)
        score = self.validator._score_keyword_density(content, "AI")
        assert score >= 0.5

    def test_overall_seo_score_weighted(
        self,
        sample_content: str,
        sample_edited_draft_package: EditedDraftPackage,
    ):
        analysis = SEOAnalysisResult()
        scores, _ = self.validator.validate_optimization(
            sample_content, sample_content, sample_edited_draft_package, analysis,
            meta_title="Title", meta_description="Desc.",
        )
        assert 0.0 <= scores.overall_seo_score <= 1.0

    def test_empty_content_handled(
        self,
        sample_edited_draft_package: EditedDraftPackage,
    ):
        analysis = SEOAnalysisResult()
        scores, _ = self.validator.validate_optimization(
            "", "", sample_edited_draft_package, analysis,
        )
        assert isinstance(scores, SEOScores)

    def test_no_citations_returns_perfect_score(
        self,
        sample_verification_report: VerificationReport,
    ):
        pkg = EditedDraftPackage(
            original_draft_version=1,
            title="T",
            platform="Blog",
            content_format="Article",
            audience="G",
            objective="E",
            edited_content="Simple.",
            verification_report=sample_verification_report,
            preserved_citations=[],
            preserved_keywords=[],
        )
        analysis = SEOAnalysisResult()
        scores, _ = self.validator.validate_optimization("Simple.", "Improved.", pkg, analysis)
        assert scores.citation_preservation_score == 1.0
        assert scores.keyword_preservation_score == 1.0


# ===========================================================================
# SEOWorker Lifecycle Tests
# ===========================================================================


class TestSEOWorkerLifecycle:
    """Unit tests for SEOWorker lifecycle management."""

    @pytest.mark.asyncio
    async def test_initialize_transitions_to_ready(self, seo_worker: SEOWorker):
        result = await seo_worker.initialize()
        assert result is True
        from modules.workforce.models import WorkerState
        assert seo_worker.state == WorkerState.READY

    @pytest.mark.asyncio
    async def test_shutdown_transitions_to_stopped(self, seo_worker: SEOWorker):
        await seo_worker.initialize()
        result = await seo_worker.shutdown()
        assert result is True
        from modules.workforce.models import WorkerState
        assert seo_worker.state == WorkerState.STOPPED

    @pytest.mark.asyncio
    async def test_health_check_true_when_ready(self, seo_worker: SEOWorker):
        await seo_worker.initialize()
        assert await seo_worker.health_check() is True

    @pytest.mark.asyncio
    async def test_health_check_false_when_stopped(self, seo_worker: SEOWorker):
        await seo_worker.initialize()
        await seo_worker.shutdown()
        assert await seo_worker.health_check() is False

    def test_worker_attributes(self, seo_worker: SEOWorker):
        assert "seo_optimization" in seo_worker.capabilities
        assert "meta_generation" in seo_worker.capabilities
        assert seo_worker.worker_name == "Production SEO Worker"
        assert seo_worker.role == "SEO Specialist"


# ===========================================================================
# SEOWorker Execution Tests
# ===========================================================================


class TestSEOWorkerExecution:
    """Integration tests for SEOWorker.execute() pipeline."""

    @pytest.mark.asyncio
    async def test_full_pipeline_completes_successfully(
        self,
        seo_worker: SEOWorker,
        sample_edited_draft_package: EditedDraftPackage,
        shared_context: SharedContext,
    ):
        await seo_worker.initialize()
        task = _make_task({
            "topic": "AI Adoption 2024",
            "edited_draft_package": sample_edited_draft_package.model_dump(mode="json"),
        })
        result = await seo_worker.execute(task, shared_context)

        assert result.status.value == "COMPLETED"
        assert "seo_optimized_package" in result.artifacts
        assert result.execution_time >= 0.0

    @pytest.mark.asyncio
    async def test_seo_package_structure(
        self,
        seo_worker: SEOWorker,
        sample_edited_draft_package: EditedDraftPackage,
        shared_context: SharedContext,
    ):
        await seo_worker.initialize()
        task = _make_task({
            "edited_draft_package": sample_edited_draft_package.model_dump(mode="json"),
        })
        result = await seo_worker.execute(task, shared_context)

        pkg = result.artifacts["seo_optimized_package"]
        assert "optimized_content" in pkg
        assert "meta_title" in pkg
        assert "meta_description" in pkg
        assert "slug" in pkg
        assert "faq_section" in pkg
        assert "schema_markup" in pkg
        assert "internal_link_suggestions" in pkg
        assert "external_link_suggestions" in pkg
        assert "verification_report" in pkg
        assert "quality_scores" in pkg
        assert "seo_scores" in pkg
        assert "optimization_metadata" in pkg

    @pytest.mark.asyncio
    async def test_lineage_forwarded(
        self,
        seo_worker: SEOWorker,
        sample_edited_draft_package: EditedDraftPackage,
        shared_context: SharedContext,
    ):
        await seo_worker.initialize()
        task = _make_task({
            "edited_draft_package": sample_edited_draft_package.model_dump(mode="json"),
        })
        result = await seo_worker.execute(task, shared_context)

        pkg = result.artifacts["seo_optimized_package"]
        assert pkg["verification_report"]["claims_checked"] == 3
        assert pkg["verification_report"]["overall_confidence"] == 0.85
        assert pkg["quality_scores"]["readability_score"] == 0.88

    @pytest.mark.asyncio
    async def test_ai_failure_fallback(
        self,
        sample_edited_draft_package: EditedDraftPackage,
        shared_context: SharedContext,
    ):
        failing_provider = AsyncMock()
        failing_provider.generate = AsyncMock(side_effect=RuntimeError("AI unavailable"))

        worker = SEOWorker(ai_provider=failing_provider, bus=MessageBus())
        await worker.initialize()
        task = _make_task({
            "edited_draft_package": sample_edited_draft_package.model_dump(mode="json"),
        })
        result = await worker.execute(task, shared_context)

        assert result.status.value == "COMPLETED"
        pkg = result.artifacts["seo_optimized_package"]
        assert pkg["optimized_content"] == sample_edited_draft_package.edited_content

    @pytest.mark.asyncio
    async def test_ai_empty_response_fallback(
        self,
        sample_edited_draft_package: EditedDraftPackage,
        shared_context: SharedContext,
    ):
        empty_provider = AsyncMock()
        empty_provider.generate = AsyncMock(return_value="")

        worker = SEOWorker(ai_provider=empty_provider, bus=MessageBus())
        await worker.initialize()
        task = _make_task({
            "edited_draft_package": sample_edited_draft_package.model_dump(mode="json"),
        })
        result = await worker.execute(task, shared_context)

        assert result.status.value == "COMPLETED"
        pkg = result.artifacts["seo_optimized_package"]
        assert pkg["optimized_content"] == sample_edited_draft_package.edited_content

    @pytest.mark.asyncio
    async def test_missing_edited_draft_package_returns_failed(
        self,
        seo_worker: SEOWorker,
        shared_context: SharedContext,
    ):
        await seo_worker.initialize()
        task = _make_task({"topic": "Missing input"})
        result = await seo_worker.execute(task, shared_context)
        assert result.status.value == "FAILED"
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_metrics_populated(
        self,
        seo_worker: SEOWorker,
        sample_edited_draft_package: EditedDraftPackage,
        shared_context: SharedContext,
    ):
        await seo_worker.initialize()
        task = _make_task({
            "edited_draft_package": sample_edited_draft_package.model_dump(mode="json"),
        })
        result = await seo_worker.execute(task, shared_context)
        metrics = result.metrics
        assert "optimization_time" in metrics
        assert "seo_score_before" in metrics
        assert "seo_score_after" in metrics
        assert "keyword_density" in metrics
        assert "heading_score" in metrics
        assert "meta_score" in metrics
        assert "internal_links_suggested" in metrics
        assert "faq_generated" in metrics

    @pytest.mark.asyncio
    async def test_events_emitted(
        self,
        sample_edited_draft_package: EditedDraftPackage,
        shared_context: SharedContext,
        mock_ai_provider: AsyncMock,
    ):
        bus = MessageBus()
        emitted_events: list[str] = []

        async def capture_event(event):
            emitted_events.append(event.event_type)

        bus.add_event_listener("SEOOptimizationStarted", capture_event)
        bus.add_event_listener("SEOAnalysisCompleted", capture_event)
        bus.add_event_listener("SEOOptimized", capture_event)
        bus.add_event_listener("SEOOptimizationCompleted", capture_event)

        worker = SEOWorker(ai_provider=mock_ai_provider, bus=bus)
        await worker.initialize()
        task = _make_task({
            "edited_draft_package": sample_edited_draft_package.model_dump(mode="json"),
        })
        await worker.execute(task, shared_context)

        assert "SEOOptimizationStarted" in emitted_events
        assert "SEOAnalysisCompleted" in emitted_events
        assert "SEOOptimized" in emitted_events
        assert "SEOOptimizationCompleted" in emitted_events

    @pytest.mark.asyncio
    async def test_failure_event_emitted(self, shared_context: SharedContext):
        bus = MessageBus()
        emitted_events: list[str] = []

        async def capture_event(event):
            emitted_events.append(event.event_type)

        bus.add_event_listener("SEOOptimizationFailed", capture_event)

        provider = AsyncMock()
        worker = SEOWorker(ai_provider=provider, bus=bus)
        await worker.initialize()
        task = _make_task({"topic": "No package"})
        await worker.execute(task, shared_context)

        assert "SEOOptimizationFailed" in emitted_events

    @pytest.mark.asyncio
    async def test_serialization_roundtrip(
        self,
        seo_worker: SEOWorker,
        sample_edited_draft_package: EditedDraftPackage,
        shared_context: SharedContext,
    ):
        await seo_worker.initialize()
        task = _make_task({
            "edited_draft_package": sample_edited_draft_package.model_dump(mode="json"),
        })
        result = await seo_worker.execute(task, shared_context)
        pkg_data = result.artifacts["seo_optimized_package"]
        restored = SEOOptimizedPackage.model_validate(pkg_data)
        assert restored.title == "AI Adoption in 2024"

    @pytest.mark.asyncio
    async def test_schema_has_placeholders(
        self,
        seo_worker: SEOWorker,
        sample_edited_draft_package: EditedDraftPackage,
        shared_context: SharedContext,
    ):
        await seo_worker.initialize()
        task = _make_task({
            "edited_draft_package": sample_edited_draft_package.model_dump(mode="json"),
        })
        result = await seo_worker.execute(task, shared_context)
        pkg = result.artifacts["seo_optimized_package"]
        schema = pkg.get("schema_markup", {})
        if schema:
            assert schema.get("author") == "{{AUTHOR}}"
            assert schema.get("datePublished") == "{{DATE}}"

    @pytest.mark.asyncio
    async def test_link_suggestions_hybrid_format(
        self,
        seo_worker: SEOWorker,
        sample_edited_draft_package: EditedDraftPackage,
        shared_context: SharedContext,
    ):
        await seo_worker.initialize()
        task = _make_task({
            "edited_draft_package": sample_edited_draft_package.model_dump(mode="json"),
        })
        result = await seo_worker.execute(task, shared_context)
        pkg = result.artifacts["seo_optimized_package"]
        internal = pkg.get("internal_link_suggestions", [])
        if internal:
            link = internal[0]
            assert "anchor_text" in link
            assert "target_topic" in link
            assert "rationale" in link


# ===========================================================================
# SEOWorker JSON Parsing Tests
# ===========================================================================


class TestSEOWorkerJSONParsing:
    """Unit tests for SEOWorker._parse_ai_response()."""

    def setup_method(self):
        self.worker = SEOWorker()

    def test_parse_valid_json(self):
        response = json.dumps({"optimized_content": "Content", "meta_title": "Title"})
        result = self.worker._parse_ai_response(response)
        assert result["optimized_content"] == "Content"
        assert result["meta_title"] == "Title"

    def test_parse_json_in_code_block(self):
        response = '```json\n{"optimized_content": "Content"}\n```'
        result = self.worker._parse_ai_response(response)
        assert result["optimized_content"] == "Content"

    def test_parse_json_in_text(self):
        response = 'Here is the result:\n{"optimized_content": "Content"}\nDone.'
        result = self.worker._parse_ai_response(response)
        assert result["optimized_content"] == "Content"

    def test_parse_empty_response(self):
        result = self.worker._parse_ai_response("")
        assert result == {}

    def test_parse_invalid_json(self):
        result = self.worker._parse_ai_response("This is not JSON at all")
        assert result == {}

"""Comprehensive test suite for the Production Publisher Worker subsystem.

Tests cover:
- Publisher Models: PublishStatus, PlatformPayload, PublicationPackage, lineage forwarding.
- Publisher Metrics: PublisherWorkerMetrics defaults, serialization.
- LinkResolver: internal links, external links, route map lookup, fallback routes, empty suggestions.
- SchemaResolver: placeholder replacement ({{AUTHOR}}, {{DATE}}, {{CANONICAL_URL}}, {{IMAGE_URL}}),
  nested dict/list traversal, unhandled placeholder fallbacks.
- PayloadBuilder: Strategy Pattern, LinkedInPayloadStrategy, XPayloadStrategy (single vs thread),
  GenericCMSPayloadStrategy, strategy registration.
- PublishValidator: complete payload pass, empty content failure, missing title,
  unpopulated placeholders failure, X character limit check, link validation.
- PublisherWorker Lifecycle: initialize, shutdown, health_check, capabilities.
- PublisherWorker Execution: full pipeline, package structure, lineage forwarded,
  platform adapter invocation, validation failure path, metrics, events,
  serialization roundtrip.
"""

from unittest.mock import AsyncMock

import pytest

from modules.workforce.bus import MessageBus
from modules.workforce.context import SharedContext
from modules.workforce.models import Task, TaskPriority
from modules.workforce.workers.draft_models import WritingStyle
from modules.workforce.workers.editor_models import EditQualityScores
from modules.workforce.workers.link_resolver import LinkResolver
from modules.workforce.workers.payload_builder import (
    LinkedInPayloadStrategy,
    PayloadBuilder,
)
from modules.workforce.workers.publish_validator import PublishValidator
from modules.workforce.workers.publisher_metrics import PublisherWorkerMetrics
from modules.workforce.workers.publisher_models import (
    PlatformPayload,
    PublicationPackage,
    PublishStatus,
)
from modules.workforce.workers.publisher_worker import PublisherWorker
from modules.workforce.workers.schema_resolver import SchemaResolver
from modules.workforce.workers.seo_models import SEOOptimizedPackage, SEOScores
from modules.workforce.workers.verification_models import (
    ClaimResult,
    VerificationReport,
    VerificationStatus,
)

# ---------------------------------------------------------------------------
# Shared Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_verification_report() -> VerificationReport:
    return VerificationReport(
        overall_status=VerificationStatus.VERIFIED,
        claims_checked=2,
        claims_verified=2,
        overall_confidence=0.92,
        claim_results=[
            ClaimResult(
                claim_text="Python is used by 80% of AI teams",
                category="statistic",
                status=VerificationStatus.VERIFIED,
                confidence=0.95,
            )
        ],
    )


@pytest.fixture
def sample_quality_scores() -> EditQualityScores:
    return EditQualityScores(
        readability_score=0.90,
        grammar_score=0.92,
        style_score=0.88,
        citation_preservation_score=1.0,
        keyword_preservation_score=1.0,
        overall_quality=0.91,
    )


@pytest.fixture
def sample_seo_scores() -> SEOScores:
    return SEOScores(
        keyword_density_score=0.95,
        heading_quality_score=0.90,
        meta_quality_score=0.85,
        citation_preservation_score=1.0,
        keyword_preservation_score=1.0,
        content_structure_score=0.88,
        overall_seo_score=0.92,
    )


@pytest.fixture
def sample_seo_package(
    sample_verification_report: VerificationReport,
    sample_quality_scores: EditQualityScores,
    sample_seo_scores: SEOScores,
) -> SEOOptimizedPackage:
    return SEOOptimizedPackage(
        title="Enterprise AI Trends 2024",
        meta_title="Enterprise AI Trends 2024: Key Guide",
        meta_description="Comprehensive guide covering enterprise AI adoption, frameworks, and statistics in 2024.",
        slug="enterprise-ai-trends-2024",
        focus_keyword="enterprise AI",
        secondary_keywords=["Python", "machine learning"],
        keyword_density=2.1,
        optimized_content=(
            "# Enterprise AI Trends 2024\n\n"
            "Enterprise software teams adopted AI tooling at record rates in 2024.\n\n"
            "## Key Python Frameworks\n\n"
            "Python remains the dominant language for machine learning development.\n"
            "See https://tensorflow.org for more information.\n\n"
            "## Conclusion\n\n"
            "AI adoption will continue to grow exponentially."
        ),
        heading_structure=[
            {"level": 1, "text": "Enterprise AI Trends 2024"},
            {"level": 2, "text": "Key Python Frameworks"},
            {"level": 2, "text": "Conclusion"},
        ],
        faq_section=[
            {"question": "What is the top AI language?", "answer": "Python remains dominant."},
        ],
        internal_link_suggestions=[
            {
                "anchor_text": "Python Memory Management",
                "target_topic": "python-memory-management",
                "rationale": "Related concept",
            }
        ],
        external_link_suggestions=[
            {
                "anchor_text": "TensorFlow Documentation",
                "target_topic": "tensorflow-docs",
                "rationale": "Authoritative reference",
            }
        ],
        schema_markup={
            "@type": "Article",
            "headline": "Enterprise AI Trends 2024",
            "author": "{{AUTHOR}}",
            "datePublished": "{{DATE}}",
            "url": "{{CANONICAL_URL}}",
            "publisher": {
                "@type": "Organization",
                "name": "{{ORGANIZATION}}",
                "logo": {"@type": "ImageObject", "url": "{{IMAGE_URL}}"},
            },
        },
        image_alt_suggestions=[
            {"image_ref": "hero", "alt_text": "Enterprise AI adoption chart"},
        ],
        readability_score=0.90,
        seo_score=0.92,
        seo_scores=sample_seo_scores,
        verification_report=sample_verification_report,
        quality_scores=sample_quality_scores,
        platform="LinkedIn",
        content_format="Article",
        audience="Developers",
        objective="EDUCATIONAL",
        writing_style=WritingStyle.AUTHORITATIVE,
    )


@pytest.fixture
def publisher_worker() -> PublisherWorker:
    bus = MessageBus()
    return PublisherWorker(bus=bus)


@pytest.fixture
def shared_context() -> SharedContext:
    return SharedContext()


def _make_task(payload: dict) -> Task:
    return Task(type="publishing", creator="test_suite", payload=payload, priority=TaskPriority.NORMAL)


# ===========================================================================
# Publisher Models Tests
# ===========================================================================


class TestPublisherModels:
    """Unit tests for publisher data models."""

    def test_publish_status_enum_values(self):
        assert PublishStatus.DRAFT == "DRAFT"
        assert PublishStatus.PENDING_APPROVAL == "PENDING_APPROVAL"
        assert PublishStatus.SCHEDULED == "SCHEDULED"
        assert PublishStatus.PUBLISHED == "PUBLISHED"
        assert PublishStatus.FAILED == "FAILED"

    def test_platform_payload_construction(self):
        payload = PlatformPayload(
            platform="linkedin",
            raw_content="Post text",
            formatted_payload={"text": "Post text"},
            media_urls=["https://example.com/image.png"],
            target_channels=["feed"],
        )
        assert payload.platform == "linkedin"
        assert payload.raw_content == "Post text"
        assert len(payload.media_urls) == 1

    def test_publication_package_creation(
        self,
        sample_verification_report: VerificationReport,
        sample_quality_scores: EditQualityScores,
        sample_seo_scores: SEOScores,
    ):
        pkg = PublicationPackage(
            platform="linkedin",
            title="Test Title",
            content="Final Content",
            slug="test-title",
            final_url="https://linkedin.com/post/123",
            verification_report=sample_verification_report,
            quality_scores=sample_quality_scores,
            seo_scores=sample_seo_scores,
        )
        assert pkg.platform == "linkedin"
        assert pkg.publish_status == PublishStatus.PUBLISHED
        assert pkg.final_url == "https://linkedin.com/post/123"
        assert pkg.verification_report.claims_checked == 2
        assert pkg.quality_scores.readability_score == 0.90
        assert pkg.seo_scores.overall_seo_score == 0.92

    def test_publication_package_serialization(
        self,
        sample_verification_report: VerificationReport,
        sample_quality_scores: EditQualityScores,
        sample_seo_scores: SEOScores,
    ):
        pkg = PublicationPackage(
            platform="x",
            title="X Post",
            content="Content for X",
            verification_report=sample_verification_report,
            quality_scores=sample_quality_scores,
            seo_scores=sample_seo_scores,
            resolved_internal_links=[{"target_topic": "ai", "resolved_url": "https://example.com/ai"}],
        )
        data = pkg.model_dump(mode="json")
        assert data["platform"] == "x"
        assert data["resolved_internal_links"][0]["resolved_url"] == "https://example.com/ai"

        restored = PublicationPackage.model_validate(data)
        assert restored.title == "X Post"
        assert restored.verification_report.claims_checked == 2


# ===========================================================================
# Publisher Worker Metrics Tests
# ===========================================================================


class TestPublisherWorkerMetrics:
    """Unit tests for PublisherWorkerMetrics model."""

    def test_metrics_defaults(self):
        m = PublisherWorkerMetrics()
        assert m.publish_time == 0.0
        assert m.payload_size == 0
        assert m.link_resolution_count == 0
        assert m.schema_resolution_count == 0
        assert m.publish_success is True
        assert m.retry_count == 0
        assert m.total_publications == 1

    def test_metrics_custom_values(self):
        m = PublisherWorkerMetrics(
            publish_time=1.2,
            payload_size=500,
            link_resolution_count=3,
            schema_resolution_count=4,
            adapter_latency=0.8,
        )
        assert m.publish_time == 1.2
        assert m.payload_size == 500
        assert m.link_resolution_count == 3
        assert m.adapter_latency == 0.8


# ===========================================================================
# LinkResolver Tests
# ===========================================================================


class TestLinkResolver:
    """Unit tests for LinkResolver deterministic link resolution."""

    def setup_method(self):
        self.resolver = LinkResolver(base_domain="https://myblog.com")

    def test_resolve_internal_link_with_route_map(
        self,
        sample_seo_package: SEOOptimizedPackage,
    ):
        route_map = {"python-memory-management": "https://myblog.com/posts/python-memory"}
        internal, external, count = self.resolver.resolve_links(
            sample_seo_package, custom_route_map=route_map
        )
        assert count == 2
        assert internal[0]["resolved_url"] == "https://myblog.com/posts/python-memory"

    def test_resolve_internal_link_fallback_domain(
        self,
        sample_seo_package: SEOOptimizedPackage,
    ):
        internal, external, count = self.resolver.resolve_links(sample_seo_package)
        assert internal[0]["resolved_url"] == "https://myblog.com/python-memory-management"

    def test_resolve_external_link_with_route_map(
        self,
        sample_seo_package: SEOOptimizedPackage,
    ):
        route_map = {"tensorflow-docs": "https://tensorflow.org/api_docs"}
        internal, external, count = self.resolver.resolve_links(
            sample_seo_package, custom_route_map=route_map
        )
        assert external[0]["resolved_url"] == "https://tensorflow.org/api_docs"

    def test_resolve_external_link_fallback(
        self,
        sample_seo_package: SEOOptimizedPackage,
    ):
        internal, external, count = self.resolver.resolve_links(sample_seo_package)
        assert external[0]["resolved_url"] == "https://tensorflow-docs.org"

    def test_resolve_already_valid_url(
        self,
        sample_verification_report: VerificationReport,
        sample_quality_scores: EditQualityScores,
        sample_seo_scores: SEOScores,
    ):
        pkg = SEOOptimizedPackage(
            title="URL Test",
            optimized_content="Content",
            verification_report=sample_verification_report,
            quality_scores=sample_quality_scores,
            seo_scores=sample_seo_scores,
            platform="Blog",
            content_format="Article",
            audience="G",
            objective="E",
            internal_link_suggestions=[
                {"anchor_text": "Docs", "target_topic": "https://docs.python.org", "rationale": "Direct URL"}
            ],
        )
        internal, _, _ = self.resolver.resolve_links(pkg)
        assert internal[0]["resolved_url"] == "https://docs.python.org"

    def test_empty_link_suggestions(
        self,
        sample_verification_report: VerificationReport,
        sample_quality_scores: EditQualityScores,
        sample_seo_scores: SEOScores,
    ):
        pkg = SEOOptimizedPackage(
            title="Empty Links",
            optimized_content="Content",
            verification_report=sample_verification_report,
            quality_scores=sample_quality_scores,
            seo_scores=sample_seo_scores,
            platform="Blog",
            content_format="Article",
            audience="G",
            objective="E",
        )
        internal, external, count = self.resolver.resolve_links(pkg)
        assert count == 0
        assert internal == []
        assert external == []


# ===========================================================================
# SchemaResolver Tests
# ===========================================================================


class TestSchemaResolver:
    """Unit tests for SchemaResolver placeholder replacement."""

    def setup_method(self):
        self.resolver = SchemaResolver()

    def test_resolve_top_level_placeholders(self, sample_seo_package: SEOOptimizedPackage):
        context = {
            "AUTHOR": "Alice Smith",
            "DATE": "2024-10-15T12:00:00Z",
            "CANONICAL_URL": "https://myblog.com/enterprise-ai-2024",
        }
        schema, count = self.resolver.resolve_schema(sample_seo_package.schema_markup, context)
        assert count >= 3
        assert schema["author"] == "Alice Smith"
        assert schema["datePublished"] == "2024-10-15T12:00:00Z"
        assert schema["url"] == "https://myblog.com/enterprise-ai-2024"

    def test_resolve_nested_dictionary_placeholders(
        self, sample_seo_package: SEOOptimizedPackage
    ):
        context = {
            "ORGANIZATION": "Acme AI Corp",
            "IMAGE_URL": "https://myblog.com/hero.png",
        }
        schema, _ = self.resolver.resolve_schema(sample_seo_package.schema_markup, context)
        assert schema["publisher"]["name"] == "Acme AI Corp"
        assert schema["publisher"]["logo"]["url"] == "https://myblog.com/hero.png"

    def test_resolve_nested_list_placeholders(self):
        template = {
            "authors": [
                {"name": "{{AUTHOR_1}}"},
                {"name": "{{AUTHOR_2}}"},
            ]
        }
        schema, count = self.resolver.resolve_schema(
            template, {"AUTHOR_1": "Alice", "AUTHOR_2": "Bob"}
        )
        assert count == 2
        assert schema["authors"][0]["name"] == "Alice"
        assert schema["authors"][1]["name"] == "Bob"

    def test_unhandled_placeholders_replaced_with_fallback(self):
        template = {"headline": "{{UNKNOWN_PLACEHOLDER_TAG}}"}
        schema, count = self.resolver.resolve_schema(template, {})
        assert count == 1
        assert "Unassigned" in schema["headline"]

    def test_empty_schema_template_handled(self):
        schema, count = self.resolver.resolve_schema({}, {})
        assert count == 0
        assert schema == {}


# ===========================================================================
# PayloadBuilder Tests
# ===========================================================================


class TestPayloadBuilder:
    """Unit tests for PayloadBuilder strategy engine."""

    def setup_method(self):
        self.builder = PayloadBuilder()

    def test_linkedin_strategy(self, sample_seo_package: SEOOptimizedPackage):
        payload = self.builder.build_payload(
            platform="linkedin",
            seo_pkg=sample_seo_package,
            content=sample_seo_package.optimized_content,
            schema={"author": "Test Author", "url": "https://example.com/post"},
        )
        assert isinstance(payload, PlatformPayload)
        assert payload.platform == "linkedin"
        assert "Enterprise AI Trends 2024" in payload.raw_content
        assert "#enterpriseAI" in payload.raw_content
        assert payload.formatted_payload["visibility"] == "PUBLIC"

    def test_x_strategy_single_post(
        self,
        sample_verification_report: VerificationReport,
        sample_quality_scores: EditQualityScores,
        sample_seo_scores: SEOScores,
    ):
        pkg = SEOOptimizedPackage(
            title="Short Post",
            optimized_content="Brief update on AI.",
            focus_keyword="AI",
            verification_report=sample_verification_report,
            quality_scores=sample_quality_scores,
            seo_scores=sample_seo_scores,
            platform="X",
            content_format="Post",
            audience="General",
            objective="INFORMATIONAL",
        )
        payload = self.builder.build_payload("x", pkg, pkg.optimized_content, {})
        assert payload.platform == "x"
        assert "mode" in payload.formatted_payload
        assert len(payload.formatted_payload["posts"]) >= 1
        assert len(payload.formatted_payload["posts"][0]) <= 280

    def test_x_strategy_thread_splitting(self, sample_seo_package: SEOOptimizedPackage):
        payload = self.builder.build_payload("x", sample_seo_package, sample_seo_package.optimized_content, {})
        assert payload.platform == "x"
        posts = payload.formatted_payload["posts"]
        assert len(posts) > 1  # Should be split into a thread
        for p in posts:
            assert len(p) <= 280

    def test_generic_cms_fallback_strategy(self, sample_seo_package: SEOOptimizedPackage):
        payload = self.builder.build_payload("medium", sample_seo_package, sample_seo_package.optimized_content, {})
        assert payload.platform == "medium"
        assert payload.formatted_payload["title"] == "Enterprise AI Trends 2024"
        assert payload.formatted_payload["slug"] == "enterprise-ai-trends-2024"

    def test_custom_strategy_registration(self):
        class GhostStrategy(LinkedInPayloadStrategy):
            @property
            def platform_name(self) -> str:
                return "ghost"

        self.builder.register_strategy(GhostStrategy())
        assert "ghost" in self.builder.strategies


# ===========================================================================
# PublishValidator Tests
# ===========================================================================


class TestPublishValidator:
    """Unit tests for PublishValidator pre-publish readiness audit."""

    def setup_method(self):
        self.validator = PublishValidator()

    def test_valid_payload_passes_audit(self, sample_seo_package: SEOOptimizedPackage):
        payload = PlatformPayload(
            platform="linkedin",
            raw_content="Post text.",
            formatted_payload={"text": "Post text."},
        )
        resolved_internal = [{"target_topic": "ai", "resolved_url": "https://example.com/ai"}]
        resolved_schema = {"headline": "Title", "author": "Jane"}

        is_valid, errors = self.validator.validate_readiness(
            payload=payload,
            seo_pkg=sample_seo_package,
            resolved_schema=resolved_schema,
            resolved_internal=resolved_internal,
        )
        assert is_valid is True
        assert len(errors) == 0

    def test_empty_content_fails_audit(self, sample_seo_package: SEOOptimizedPackage):
        payload = PlatformPayload(
            platform="linkedin",
            raw_content="",
            formatted_payload={},
        )
        is_valid, errors = self.validator.validate_readiness(payload, sample_seo_package)
        assert is_valid is False
        assert any("raw_content is empty" in e for e in errors)

    def test_unresolved_link_fails_audit(self, sample_seo_package: SEOOptimizedPackage):
        payload = PlatformPayload(platform="linkedin", raw_content="Text", formatted_payload={"t": "t"})
        resolved_internal = [{"target_topic": "broken-topic", "resolved_url": ""}]

        is_valid, errors = self.validator.validate_readiness(
            payload, sample_seo_package, resolved_internal=resolved_internal
        )
        assert is_valid is False
        assert any("lacks resolved_url" in e for e in errors)

    def test_unpopulated_schema_placeholder_fails_audit(
        self, sample_seo_package: SEOOptimizedPackage
    ):
        payload = PlatformPayload(platform="linkedin", raw_content="Text", formatted_payload={"t": "t"})
        unresolved_schema = {"author": "{{UNRESOLVED_AUTHOR_TAG}}"}

        is_valid, errors = self.validator.validate_readiness(
            payload, sample_seo_package, resolved_schema=unresolved_schema
        )
        assert is_valid is False
        assert any("unpopulated placeholders" in e for e in errors)

    def test_single_x_post_exceeds_char_limit(
        self, sample_seo_package: SEOOptimizedPackage
    ):
        long_text = "A" * 300
        payload = PlatformPayload(
            platform="x",
            raw_content=long_text,
            formatted_payload={"mode": "single", "posts": [long_text]},
        )
        is_valid, errors = self.validator.validate_readiness(payload, sample_seo_package)
        assert is_valid is False
        assert any("exceeds 280 character limit" in e for e in errors)


# ===========================================================================
# PublisherWorker Lifecycle Tests
# ===========================================================================


class TestPublisherWorkerLifecycle:
    """Unit tests for PublisherWorker state lifecycle."""

    @pytest.mark.asyncio
    async def test_initialize_transitions_to_ready(self, publisher_worker: PublisherWorker):
        result = await publisher_worker.initialize()
        assert result is True
        from modules.workforce.models import WorkerState
        assert publisher_worker.state == WorkerState.READY

    @pytest.mark.asyncio
    async def test_shutdown_transitions_to_stopped(self, publisher_worker: PublisherWorker):
        await publisher_worker.initialize()
        result = await publisher_worker.shutdown()
        assert result is True
        from modules.workforce.models import WorkerState
        assert publisher_worker.state == WorkerState.STOPPED

    @pytest.mark.asyncio
    async def test_health_check_true_when_ready(self, publisher_worker: PublisherWorker):
        await publisher_worker.initialize()
        assert await publisher_worker.health_check() is True

    @pytest.mark.asyncio
    async def test_health_check_false_when_stopped(self, publisher_worker: PublisherWorker):
        await publisher_worker.initialize()
        await publisher_worker.shutdown()
        assert await publisher_worker.health_check() is False

    def test_worker_attributes(self, publisher_worker: PublisherWorker):
        assert "publishing" in publisher_worker.capabilities
        assert "linkedin_publish" in publisher_worker.capabilities
        assert publisher_worker.worker_name == "Production Publisher Worker"
        assert publisher_worker.role == "Publishing Specialist"


# ===========================================================================
# PublisherWorker Execution Tests
# ===========================================================================


class TestPublisherWorkerExecution:
    """Integration tests for PublisherWorker.execute() pipeline."""

    @pytest.mark.asyncio
    async def test_full_pipeline_completes_successfully(
        self,
        publisher_worker: PublisherWorker,
        sample_seo_package: SEOOptimizedPackage,
        shared_context: SharedContext,
    ):
        await publisher_worker.initialize()
        task = _make_task({
            "platform": "linkedin",
            "topic": "AI Trends",
            "seo_optimized_package": sample_seo_package.model_dump(mode="json"),
        })
        result = await publisher_worker.execute(task, shared_context)

        assert result.status.value == "COMPLETED"
        assert "publication_package" in result.artifacts
        assert result.execution_time >= 0.0

    @pytest.mark.asyncio
    async def test_publication_package_structure(
        self,
        publisher_worker: PublisherWorker,
        sample_seo_package: SEOOptimizedPackage,
        shared_context: SharedContext,
    ):
        await publisher_worker.initialize()
        task = _make_task({
            "platform": "linkedin",
            "seo_optimized_package": sample_seo_package.model_dump(mode="json"),
        })
        result = await publisher_worker.execute(task, shared_context)

        pkg = result.artifacts["publication_package"]
        assert pkg["platform"] == "linkedin"
        assert pkg["title"] == "Enterprise AI Trends 2024"
        assert "resolved_internal_links" in pkg
        assert "resolved_external_links" in pkg
        assert "schema_markup" in pkg
        assert "publish_status" in pkg
        assert "verification_report" in pkg
        assert "quality_scores" in pkg
        assert "seo_scores" in pkg
        assert "publisher_metadata" in pkg

    @pytest.mark.asyncio
    async def test_lineage_forwarded_immutably(
        self,
        publisher_worker: PublisherWorker,
        sample_seo_package: SEOOptimizedPackage,
        shared_context: SharedContext,
    ):
        await publisher_worker.initialize()
        task = _make_task({
            "platform": "linkedin",
            "seo_optimized_package": sample_seo_package.model_dump(mode="json"),
        })
        result = await publisher_worker.execute(task, shared_context)

        pkg = result.artifacts["publication_package"]
        assert pkg["verification_report"]["claims_checked"] == 2
        assert pkg["verification_report"]["overall_confidence"] == 0.92
        assert pkg["quality_scores"]["readability_score"] == 0.90
        assert pkg["seo_scores"]["overall_seo_score"] == 0.92

    @pytest.mark.asyncio
    async def test_custom_route_map_resolution(
        self,
        publisher_worker: PublisherWorker,
        sample_seo_package: SEOOptimizedPackage,
        shared_context: SharedContext,
    ):
        await publisher_worker.initialize()
        task = _make_task({
            "platform": "linkedin",
            "route_map": {"python-memory-management": "https://myblog.com/custom-python-route"},
            "seo_optimized_package": sample_seo_package.model_dump(mode="json"),
        })
        result = await publisher_worker.execute(task, shared_context)

        pkg = result.artifacts["publication_package"]
        assert pkg["resolved_internal_links"][0]["resolved_url"] == "https://myblog.com/custom-python-route"

    @pytest.mark.asyncio
    async def test_missing_seo_package_returns_failed(
        self,
        publisher_worker: PublisherWorker,
        shared_context: SharedContext,
    ):
        await publisher_worker.initialize()
        task = _make_task({"platform": "linkedin", "topic": "Missing input"})
        result = await publisher_worker.execute(task, shared_context)

        assert result.status.value == "FAILED"
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_validation_failure_path(
        self,
        shared_context: SharedContext,
    ):
        from unittest.mock import MagicMock

        # Create worker with validator that rejects
        rejecting_validator = MagicMock()
        rejecting_validator.validate_readiness = MagicMock(return_value=(False, ["Invalid payload format"]))

        worker = PublisherWorker(publish_validator=rejecting_validator, bus=MessageBus())
        await worker.initialize()

        sample_pkg = SEOOptimizedPackage(
            title="T",
            optimized_content="C",
            verification_report=VerificationReport(),
            quality_scores=EditQualityScores(),
            seo_scores=SEOScores(),
            platform="Blog",
            content_format="Article",
            audience="G",
            objective="E",
        )
        task = _make_task({"platform": "linkedin", "seo_optimized_package": sample_pkg.model_dump(mode="json")})
        result = await worker.execute(task, shared_context)

        assert result.status.value == "FAILED"
        assert "Invalid payload format" in result.error

    @pytest.mark.asyncio
    async def test_metrics_populated(
        self,
        publisher_worker: PublisherWorker,
        sample_seo_package: SEOOptimizedPackage,
        shared_context: SharedContext,
    ):
        await publisher_worker.initialize()
        task = _make_task({
            "platform": "linkedin",
            "seo_optimized_package": sample_seo_package.model_dump(mode="json"),
        })
        result = await publisher_worker.execute(task, shared_context)

        metrics = result.metrics
        assert "publish_time" in metrics
        assert "payload_size" in metrics
        assert "link_resolution_count" in metrics
        assert "schema_resolution_count" in metrics
        assert metrics["publish_success"] is True
        assert metrics["total_publications"] == 1

    @pytest.mark.asyncio
    async def test_events_emitted(
        self,
        sample_seo_package: SEOOptimizedPackage,
        shared_context: SharedContext,
    ):
        bus = MessageBus()
        emitted_events: list[str] = []

        async def capture_event(event):
            emitted_events.append(event.event_type)

        bus.add_event_listener("PublishingStarted", capture_event)
        bus.add_event_listener("PayloadBuilt", capture_event)
        bus.add_event_listener("PublishingCompleted", capture_event)

        worker = PublisherWorker(bus=bus)
        await worker.initialize()
        task = _make_task({
            "platform": "linkedin",
            "seo_optimized_package": sample_seo_package.model_dump(mode="json"),
        })
        await worker.execute(task, shared_context)

        assert "PublishingStarted" in emitted_events
        assert "PayloadBuilt" in emitted_events
        assert "PublishingCompleted" in emitted_events

    @pytest.mark.asyncio
    async def test_failure_event_emitted(self, shared_context: SharedContext):
        bus = MessageBus()
        emitted_events: list[str] = []

        async def capture_event(event):
            emitted_events.append(event.event_type)

        bus.add_event_listener("PublishingFailed", capture_event)

        worker = PublisherWorker(bus=bus)
        await worker.initialize()
        task = _make_task({"platform": "linkedin"})  # Missing package
        await worker.execute(task, shared_context)

        assert "PublishingFailed" in emitted_events

    @pytest.mark.asyncio
    async def test_platform_adapter_invocation(
        self,
        sample_seo_package: SEOOptimizedPackage,
        shared_context: SharedContext,
    ):
        mock_adapter = AsyncMock()
        mock_adapter.publish = AsyncMock(return_value=True)

        adapters = {"linkedin": mock_adapter}
        worker = PublisherWorker(platform_adapters=adapters, bus=MessageBus())
        await worker.initialize()

        task = _make_task({
            "platform": "linkedin",
            "seo_optimized_package": sample_seo_package.model_dump(mode="json"),
        })
        result = await worker.execute(task, shared_context)

        assert result.status.value == "COMPLETED"
        assert mock_adapter.publish.called

    @pytest.mark.asyncio
    async def test_serialization_roundtrip(
        self,
        publisher_worker: PublisherWorker,
        sample_seo_package: SEOOptimizedPackage,
        shared_context: SharedContext,
    ):
        await publisher_worker.initialize()
        task = _make_task({
            "platform": "linkedin",
            "seo_optimized_package": sample_seo_package.model_dump(mode="json"),
        })
        result = await publisher_worker.execute(task, shared_context)

        pkg_data = result.artifacts["publication_package"]
        restored = PublicationPackage.model_validate(pkg_data)
        assert restored.title == "Enterprise AI Trends 2024"
        assert restored.platform == "linkedin"
        assert restored.publish_status == PublishStatus.PUBLISHED

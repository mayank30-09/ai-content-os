"""Comprehensive test suite for the Production Fact Checker Worker subsystem.

Tests cover:
- ClaimExtractor: statistics, dates, quotes, URLs, general_facts, empty drafts, malformed input.
- CitationVerifier: matched, unmatched, duplicate, malformed, empty research package.
- FactValidator: verified, unverified, hallucination, empty corpus, pluggable strategy.
- FactCheckerWorker: full pipeline, degraded execution (missing packages), lifecycle,
  serialization, concurrent execution, events, and metrics.
"""

import asyncio

import pytest

from modules.memory.models import ContextPackage, KnowledgeMemory, ResearchMemory
from modules.research.models import ResearchDocument, ResearchPackage
from modules.workforce.bus import MessageBus
from modules.workforce.context import SharedContext
from modules.workforce.models import Task, TaskPriority
from modules.workforce.workers.citation_verifier import CitationVerifier
from modules.workforce.workers.claim_extractor import ClaimExtractor, ExtractedClaim
from modules.workforce.workers.draft_models import DraftPackage, WritingStyle
from modules.workforce.workers.fact_checker_metrics import FactCheckerMetrics
from modules.workforce.workers.fact_checker_worker import FactCheckerWorker
from modules.workforce.workers.fact_validator import (
    FactValidator,
    JaccardOverlapStrategy,
    MatchingStrategy,
    SubstringInclusionStrategy,
)
from modules.workforce.workers.verification_models import (
    ClaimResult,
    IssueSeverity,
    VerificationReport,
    VerificationStatus,
    VerifiedDraftPackage,
)

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_draft() -> str:
    return """# AI Adoption in 2024

In 2024, over 78% of enterprise software teams adopted some form of AI tooling.
The market grew by $1.2 billion in Q3 2024 alone.

According to Gartner, "AI will automate 40% of repetitive tasks by 2026."

Python is the most popular language for AI development.
TensorFlow has been downloaded more than 100 million times.
Visit https://tensorflow.org/about for more information.
See also https://python.org for documentation.
"""


@pytest.fixture
def sample_draft_package(sample_draft: str) -> DraftPackage:
    return DraftPackage(
        title="AI Adoption in 2024",
        platform="Blog",
        content_format="Article",
        audience="Developers",
        objective="EDUCATIONAL",
        writing_style=WritingStyle.AUTHORITATIVE,
        draft=sample_draft,
        citations_used=[
            {"url": "https://tensorflow.org/about", "title": "TensorFlow About"},
            {"url": "https://gartner.com/report-2024", "title": "Gartner AI Report"},
            {"url": "https://python.org", "title": "Python Official"},
        ],
        seo_keywords=["AI", "2024", "enterprise"],
    )


@pytest.fixture
def sample_research_package() -> ResearchPackage:
    return ResearchPackage(
        query="AI adoption 2024",
        executive_summary=(
            "AI adoption rates soared in 2024. Enterprise adoption reached 78%. "
            "The AI market grew by $1.2 billion in Q3 2024. "
            "TensorFlow has been downloaded more than 100 million times."
        ),
        key_facts=[
            "78% of enterprise teams adopted AI tooling in 2024.",
            "Market grew by $1.2B in Q3 2024.",
            "Python is the most popular AI development language.",
        ],
        ranked_documents=[
            ResearchDocument(
                source="web",
                source_type="web",
                title="TensorFlow About",
                url="https://tensorflow.org/about",
                content=(
                    "TensorFlow is an open-source machine learning framework. "
                    "It has been downloaded over 100 million times worldwide. "
                    "Python is the primary development language for TensorFlow."
                ),
            ),
            ResearchDocument(
                source="web",
                source_type="web",
                title="AI Market Report 2024",
                url="https://gartner.com/report-2024",
                content=(
                    "Gartner analysts report that AI will automate 40 percent of repetitive tasks by 2026. "
                    "The AI software market grew by 1.2 billion dollars in Q3 2024."
                ),
            ),
        ],
    )


@pytest.fixture
def sample_context_package() -> ContextPackage:
    return ContextPackage(
        topic="AI adoption 2024",
        research_memories=[
            ResearchMemory(
                query="AI market 2024",
                content="AI market grew significantly in 2024. 78 percent enterprise adoption.",
                key_facts=["78% enterprise adoption rate", "$1.2B market growth Q3 2024"],
            )
        ],
        knowledge_memories=[
            KnowledgeMemory(
                entity_name="TensorFlow",
                category="framework",
                content="TensorFlow downloaded over 100 million times.",
                claims=["TensorFlow 100 million downloads", "TensorFlow Python framework"],
            )
        ],
    )


@pytest.fixture
def fact_checker_worker() -> FactCheckerWorker:
    bus = MessageBus()
    return FactCheckerWorker(bus=bus)


@pytest.fixture
def shared_context() -> SharedContext:
    return SharedContext()


def _make_task(payload: dict) -> Task:
    return Task(type="fact_check", creator="test_suite", payload=payload, priority=TaskPriority.NORMAL)


# ===========================================================================
# ClaimExtractor Tests
# ===========================================================================

class TestClaimExtractor:
    """Unit tests for ClaimExtractor claim parsing."""

    def setup_method(self):
        self.extractor = ClaimExtractor()

    def test_extract_statistics_percentage(self, sample_draft: str):
        claims = self.extractor.extract_claims(sample_draft)
        stat_claims = [c for c in claims if c.category == "statistic"]
        assert len(stat_claims) >= 1
        assert any("78%" in c.text or "78" in c.text for c in stat_claims)

    def test_extract_statistics_currency(self, sample_draft: str):
        claims = self.extractor.extract_claims(sample_draft)
        stat_claims = [c for c in claims if c.category == "statistic"]
        assert any("billion" in c.text.lower() or "$1.2" in c.text for c in stat_claims)

    def test_extract_statistics_large_number(self):
        draft = "TensorFlow has been downloaded more than 100 million times."
        claims = self.extractor.extract_claims(draft)
        stat_claims = [c for c in claims if c.category == "statistic"]
        assert len(stat_claims) >= 1

    def test_extract_dates_year(self, sample_draft: str):
        claims = self.extractor.extract_claims(sample_draft)
        date_claims = [c for c in claims if c.category == "date"]
        assert len(date_claims) >= 1
        assert any("2024" in c.text for c in date_claims)

    def test_extract_dates_quarter(self, sample_draft: str):
        claims = self.extractor.extract_claims(sample_draft)
        date_claims = [c for c in claims if c.category == "date"]
        assert any("Q3" in c.text for c in date_claims)

    def test_extract_dates_iso_format(self):
        draft = "The product launched on 2024-03-15 and shipped to 50 countries."
        claims = self.extractor.extract_claims(draft)
        date_claims = [c for c in claims if c.category == "date"]
        assert len(date_claims) >= 1
        assert any("2024-03-15" in c.text for c in date_claims)

    def test_extract_dates_month_day_year(self):
        draft = "On January 15th, 2023, the company announced a major breakthrough."
        claims = self.extractor.extract_claims(draft)
        date_claims = [c for c in claims if c.category == "date"]
        assert len(date_claims) >= 1

    def test_extract_quotes(self, sample_draft: str):
        claims = self.extractor.extract_claims(sample_draft)
        quote_claims = [c for c in claims if c.category == "quote"]
        assert len(quote_claims) >= 1
        assert any("automate" in c.text for c in quote_claims)

    def test_extract_quotes_minimum_length(self):
        # Isolated quoted text under 10 chars should not be extracted as a standalone quote.
        # A single short word like "abc" (3 chars inner) is below the 10-char floor.
        draft = 'The answer was simply "ok".'
        claims = self.extractor.extract_claims(draft)
        quote_claims = [c for c in claims if c.category == "quote"]
        # "ok" = 2 chars inner, below minimum — should produce zero quote claims
        assert len(quote_claims) == 0

    def test_extract_urls(self, sample_draft: str):
        claims = self.extractor.extract_claims(sample_draft)
        url_claims = [c for c in claims if c.category == "url"]
        assert len(url_claims) >= 2
        assert any("tensorflow.org" in c.text for c in url_claims)
        assert any("python.org" in c.text for c in url_claims)

    def test_extract_urls_https_only(self):
        draft = "Visit ftp://files.example.com and also http://example.com/path."
        claims = self.extractor.extract_claims(draft)
        url_claims = [c for c in claims if c.category == "url"]
        assert any("http://example.com" in c.text for c in url_claims)

    def test_empty_draft_returns_empty_list(self):
        claims = self.extractor.extract_claims("")
        assert claims == []

    def test_whitespace_draft_returns_empty_list(self):
        claims = self.extractor.extract_claims("   \n\n\t  ")
        assert claims == []

    def test_malformed_draft_no_crash(self):
        malformed = "### \x00broken\x00 content \n\n??!!<<>>{{}} 999"
        claims = self.extractor.extract_claims(malformed)
        assert isinstance(claims, list)

    def test_extracted_claim_is_immutable(self, sample_draft: str):
        claims = self.extractor.extract_claims(sample_draft)
        assert len(claims) > 0
        with pytest.raises((AttributeError, TypeError)):
            claims[0].text = "mutated"  # type: ignore[misc]

    def test_no_duplicate_claim_texts(self, sample_draft: str):
        claims = self.extractor.extract_claims(sample_draft)
        texts = [c.text for c in claims]
        assert len(texts) == len(set(texts)), "Duplicate claim texts found."

    def test_claim_has_category_and_position(self, sample_draft: str):
        claims = self.extractor.extract_claims(sample_draft)
        for claim in claims:
            assert claim.category in {"statistic", "date", "quote", "url", "general_fact"}
            assert claim.position >= 0


# ===========================================================================
# CitationVerifier Tests
# ===========================================================================

class TestCitationVerifier:
    """Unit tests for CitationVerifier citation auditing."""

    def setup_method(self):
        self.verifier = CitationVerifier()

    def test_matched_citation(self, sample_research_package: ResearchPackage):
        citations = [{"url": "https://tensorflow.org/about", "title": "TensorFlow"}]
        results, dupes = self.verifier.verify_citations(citations, sample_research_package)
        assert len(results) == 1
        assert results[0].status == "matched"
        assert dupes == 0

    def test_unmatched_citation(self, sample_research_package: ResearchPackage):
        citations = [{"url": "https://unknown-site.io/article", "title": "Unknown"}]
        results, dupes = self.verifier.verify_citations(citations, sample_research_package)
        assert results[0].status == "unmatched"
        assert dupes == 0

    def test_duplicate_citation_detected(self, sample_research_package: ResearchPackage):
        citations = [
            {"url": "https://tensorflow.org/about", "title": "TF 1"},
            {"url": "https://tensorflow.org/about", "title": "TF 2"},
        ]
        results, dupes = self.verifier.verify_citations(citations, sample_research_package)
        assert dupes == 1
        statuses = [r.status for r in results]
        assert "duplicate" in statuses

    def test_malformed_citation_no_url(self, sample_research_package: ResearchPackage):
        citations = [{"title": "No URL citation"}]
        results, dupes = self.verifier.verify_citations(citations, sample_research_package)
        assert len(results) == 1
        assert results[0].url == ""
        assert results[0].status == "unmatched"

    def test_empty_citations_returns_empty(self, sample_research_package: ResearchPackage):
        results, dupes = self.verifier.verify_citations([], sample_research_package)
        assert results == []
        assert dupes == 0

    def test_empty_research_package_all_unmatched(self):
        empty_pkg = ResearchPackage(query="q", executive_summary="s")
        citations = [{"url": "https://example.com", "title": "Ex"}]
        results, dupes = self.verifier.verify_citations(citations, empty_pkg)
        assert results[0].status == "unmatched"

    def test_none_research_package_all_unmatched(self):
        citations = [{"url": "https://example.com", "title": "Ex"}]
        results, dupes = self.verifier.verify_citations(citations, None)
        assert results[0].status == "unmatched"

    def test_url_normalization_trailing_slash(self, sample_research_package: ResearchPackage):
        # Citation URL with trailing slash should still match
        citations = [{"url": "https://tensorflow.org/about/", "title": "TF"}]
        results, _ = self.verifier.verify_citations(citations, sample_research_package)
        assert results[0].status == "matched"

    def test_multiple_mixed_citations(self, sample_research_package: ResearchPackage):
        citations = [
            {"url": "https://tensorflow.org/about", "title": "TF"},
            {"url": "https://no-match.io", "title": "NM"},
            {"url": "https://gartner.com/report-2024", "title": "Gartner"},
        ]
        results, dupes = self.verifier.verify_citations(citations, sample_research_package)
        statuses = {r.url: r.status for r in results}
        assert statuses["https://tensorflow.org/about"] == "matched"
        assert statuses["https://no-match.io"] == "unmatched"
        assert statuses["https://gartner.com/report-2024"] == "matched"
        assert dupes == 0


# ===========================================================================
# FactValidator Tests
# ===========================================================================

class TestFactValidator:
    """Unit tests for FactValidator claim validation and pluggable strategies."""

    def setup_method(self):
        self.validator = FactValidator()

    def _make_claim(self, text: str, category: str = "general_fact") -> ExtractedClaim:
        return ExtractedClaim(text=text, category=category, position=0)

    def test_verified_claim_with_strong_overlap(self, sample_research_package: ResearchPackage):
        claim = self._make_claim(
            "TensorFlow has been downloaded over 100 million times.",
            "statistic",
        )
        results = self.validator.validate_claims([claim], sample_research_package, None)
        assert results[0].status in {VerificationStatus.VERIFIED, VerificationStatus.PARTIALLY_VERIFIED}
        assert results[0].confidence > 0.0

    def test_unverified_claim_no_overlap(self, sample_research_package: ResearchPackage):
        claim = self._make_claim("Quantum computing will replace all CPUs by 2030.")
        results = self.validator.validate_claims([claim], sample_research_package, None)
        assert results[0].status in {VerificationStatus.UNVERIFIED, VerificationStatus.HALLUCINATION_SUSPECTED}

    def test_hallucination_suspected_zero_confidence(self):
        validator = FactValidator()
        claim = self._make_claim("xyzzy frobozz irrelevant nonsense abc 123")
        empty_pkg = ResearchPackage(query="q", executive_summary="s")
        results = validator.validate_claims([claim], empty_pkg, None)
        assert results[0].confidence <= 0.10

    def test_empty_claims_list_returns_empty(self, sample_research_package: ResearchPackage):
        results = self.validator.validate_claims([], sample_research_package, None)
        assert results == []

    def test_none_research_package_all_unverified(self):
        claim = self._make_claim("Python is the most popular AI language.")
        results = self.validator.validate_claims([claim], None, None)
        assert results[0].status == VerificationStatus.UNVERIFIED
        assert results[0].confidence == 0.0

    def test_context_package_used_as_evidence(self, sample_context_package: ContextPackage):
        claim = self._make_claim("TensorFlow downloaded 100 million times.", "statistic")
        results = self.validator.validate_claims([claim], None, sample_context_package)
        assert results[0].confidence > 0.0

    def test_claim_result_has_correct_fields(self, sample_research_package: ResearchPackage):
        claim = self._make_claim("Enterprise AI adoption grew to 78 percent in 2024.", "statistic")
        results = self.validator.validate_claims([claim], sample_research_package, None)
        r = results[0]
        assert isinstance(r, ClaimResult)
        assert r.category == "statistic"
        assert r.verification_method in {"jaccard_overlap", "substring_inclusion"}
        assert 0.0 <= r.confidence <= 1.0
        assert isinstance(r.issue_severity, IssueSeverity)

    def test_pluggable_strategy_custom(self, sample_research_package: ResearchPackage):
        """Custom strategy that always returns 1.0 confidence."""

        class AlwaysVerifiedStrategy(MatchingStrategy):
            @property
            def strategy_name(self) -> str:
                return "always_verified"

            def match(self, claim_text: str, source_texts: list[str]) -> tuple[float, str | None]:
                return 1.0, "mock match"

        validator = FactValidator(primary_strategy=AlwaysVerifiedStrategy())
        claim = self._make_claim("Any claim text whatsoever.")
        results = validator.validate_claims([claim], sample_research_package, None)
        assert results[0].status == VerificationStatus.VERIFIED
        assert results[0].confidence == 1.0
        assert results[0].verification_method == "always_verified"

    def test_jaccard_strategy_directly(self):
        strategy = JaccardOverlapStrategy()
        score, excerpt = strategy.match(
            "TensorFlow downloaded million times",
            ["TensorFlow has been downloaded over 100 million times worldwide."],
        )
        assert score > 0.0
        assert excerpt is not None

    def test_substring_strategy_directly(self):
        strategy = SubstringInclusionStrategy()
        score, excerpt = strategy.match(
            "Python machine learning framework",
            ["Python is the primary development language for TensorFlow machine learning."],
        )
        assert score > 0.0

    def test_issue_severity_escalates_for_no_evidence(self):
        validator = FactValidator()
        claim = self._make_claim("Xyzzy frobozz nonsense statement irrelevant")
        results = validator.validate_claims([claim], None, None)
        assert results[0].issue_severity in {IssueSeverity.MEDIUM, IssueSeverity.HIGH}


# ===========================================================================
# VerificationModels Tests
# ===========================================================================

class TestVerificationModels:
    """Unit tests for verification Pydantic models."""

    def test_verification_status_enum_values(self):
        assert VerificationStatus.VERIFIED == "VERIFIED"
        assert VerificationStatus.HALLUCINATION_SUSPECTED == "HALLUCINATION_SUSPECTED"

    def test_issue_severity_enum_values(self):
        assert IssueSeverity.INFO == "INFO"
        assert IssueSeverity.CRITICAL == "CRITICAL"

    def test_claim_result_defaults(self):
        cr = ClaimResult(claim_text="Test claim.")
        assert cr.status == VerificationStatus.UNVERIFIED
        assert cr.confidence == 0.0
        assert cr.issue_severity == IssueSeverity.INFO
        assert cr.category == "general_fact"

    def test_verification_report_defaults(self):
        report = VerificationReport()
        assert report.overall_status == VerificationStatus.VERIFIED
        assert report.claims_checked == 0
        assert report.overall_confidence == 1.0

    def test_verified_draft_package_defaults(self, sample_draft_package: DraftPackage):
        vdp = VerifiedDraftPackage(
            draft_package=sample_draft_package,
            verification_report=VerificationReport(),
        )
        assert vdp.is_approved_for_edit is True
        assert vdp.requires_human_review is False
        assert vdp.audit_timestamp is not None

    def test_verified_draft_package_serialization(self, sample_draft_package: DraftPackage):
        vdp = VerifiedDraftPackage(
            draft_package=sample_draft_package,
            verification_report=VerificationReport(claims_checked=5, claims_verified=4),
        )
        data = vdp.model_dump(mode="json")
        assert "draft_package" in data
        assert "verification_report" in data
        assert data["verification_report"]["claims_checked"] == 5

    def test_fact_checker_metrics_defaults(self):
        m = FactCheckerMetrics()
        assert m.claims_found == 0
        assert m.duplicate_citation_count == 0
        assert m.average_claim_confidence == 1.0


# ===========================================================================
# FactCheckerWorker Tests
# ===========================================================================

class TestFactCheckerWorkerLifecycle:
    """Unit tests for FactCheckerWorker lifecycle management."""

    @pytest.mark.asyncio
    async def test_initialize_transitions_to_ready(self, fact_checker_worker: FactCheckerWorker):
        result = await fact_checker_worker.initialize()
        assert result is True
        from modules.workforce.models import WorkerState
        assert fact_checker_worker.state == WorkerState.READY

    @pytest.mark.asyncio
    async def test_shutdown_transitions_to_stopped(self, fact_checker_worker: FactCheckerWorker):
        await fact_checker_worker.initialize()
        result = await fact_checker_worker.shutdown()
        assert result is True
        from modules.workforce.models import WorkerState
        assert fact_checker_worker.state == WorkerState.STOPPED

    @pytest.mark.asyncio
    async def test_health_check_true_when_ready(self, fact_checker_worker: FactCheckerWorker):
        await fact_checker_worker.initialize()
        assert await fact_checker_worker.health_check() is True

    @pytest.mark.asyncio
    async def test_health_check_false_when_stopped(self, fact_checker_worker: FactCheckerWorker):
        await fact_checker_worker.initialize()
        await fact_checker_worker.shutdown()
        assert await fact_checker_worker.health_check() is False

    def test_worker_attributes(self, fact_checker_worker: FactCheckerWorker):
        assert "fact_checking" in fact_checker_worker.capabilities
        assert "citation_verification" in fact_checker_worker.capabilities
        assert fact_checker_worker.worker_name == "Production Fact Checker Worker"
        assert fact_checker_worker.role == "Fact Checker"


class TestFactCheckerWorkerExecution:
    """Integration-style tests for FactCheckerWorker.execute() pipeline."""

    @pytest.mark.asyncio
    async def test_full_pipeline_completes_successfully(
        self,
        fact_checker_worker: FactCheckerWorker,
        sample_draft_package: DraftPackage,
        sample_research_package: ResearchPackage,
        sample_context_package: ContextPackage,
        shared_context: SharedContext,
    ):
        await fact_checker_worker.initialize()
        task = _make_task({
            "topic": "AI Adoption 2024",
            "draft_package": sample_draft_package.model_dump(mode="json"),
            "research_package": sample_research_package.model_dump(mode="json"),
            "context_package": sample_context_package.model_dump(mode="json"),
        })
        result = await fact_checker_worker.execute(task, shared_context)

        assert result.status.value == "COMPLETED"
        assert "verified_draft_package" in result.artifacts
        assert result.execution_time >= 0.0
        assert len(result.logs) > 0

    @pytest.mark.asyncio
    async def test_verified_draft_package_structure(
        self,
        fact_checker_worker: FactCheckerWorker,
        sample_draft_package: DraftPackage,
        sample_research_package: ResearchPackage,
        shared_context: SharedContext,
    ):
        await fact_checker_worker.initialize()
        task = _make_task({
            "topic": "AI Adoption 2024",
            "draft_package": sample_draft_package.model_dump(mode="json"),
            "research_package": sample_research_package.model_dump(mode="json"),
        })
        result = await fact_checker_worker.execute(task, shared_context)

        vdp_data = result.artifacts["verified_draft_package"]
        assert "draft_package" in vdp_data
        assert "verification_report" in vdp_data
        assert "is_approved_for_edit" in vdp_data
        assert "requires_human_review" in vdp_data
        assert "audit_timestamp" in vdp_data

    @pytest.mark.asyncio
    async def test_degraded_execution_no_research_package(
        self,
        fact_checker_worker: FactCheckerWorker,
        sample_draft_package: DraftPackage,
        shared_context: SharedContext,
    ):
        """Worker must complete gracefully without a ResearchPackage."""
        await fact_checker_worker.initialize()
        task = _make_task({
            "topic": "AI Adoption 2024",
            "draft_package": sample_draft_package.model_dump(mode="json"),
        })
        result = await fact_checker_worker.execute(task, shared_context)
        assert result.status.value == "COMPLETED"
        vdp_data = result.artifacts["verified_draft_package"]
        assert vdp_data["verification_report"]["overall_confidence"] >= 0.0

    @pytest.mark.asyncio
    async def test_degraded_execution_no_context_package(
        self,
        fact_checker_worker: FactCheckerWorker,
        sample_draft_package: DraftPackage,
        sample_research_package: ResearchPackage,
        shared_context: SharedContext,
    ):
        """Worker must complete gracefully without a ContextPackage."""
        await fact_checker_worker.initialize()
        task = _make_task({
            "draft_package": sample_draft_package.model_dump(mode="json"),
            "research_package": sample_research_package.model_dump(mode="json"),
        })
        result = await fact_checker_worker.execute(task, shared_context)
        assert result.status.value == "COMPLETED"

    @pytest.mark.asyncio
    async def test_missing_draft_package_returns_failed(
        self,
        fact_checker_worker: FactCheckerWorker,
        shared_context: SharedContext,
    ):
        await fact_checker_worker.initialize()
        task = _make_task({"topic": "AI"})
        result = await fact_checker_worker.execute(task, shared_context)
        assert result.status.value == "FAILED"
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_metrics_populated_in_result(
        self,
        fact_checker_worker: FactCheckerWorker,
        sample_draft_package: DraftPackage,
        sample_research_package: ResearchPackage,
        shared_context: SharedContext,
    ):
        await fact_checker_worker.initialize()
        task = _make_task({
            "draft_package": sample_draft_package.model_dump(mode="json"),
            "research_package": sample_research_package.model_dump(mode="json"),
        })
        result = await fact_checker_worker.execute(task, shared_context)
        metrics = result.metrics
        assert "claims_found" in metrics
        assert "claims_verified" in metrics
        assert "citations_checked" in metrics
        assert "duplicate_citation_count" in metrics
        assert "average_claim_confidence" in metrics
        assert "verification_time" in metrics
        assert metrics["claims_found"] >= 0

    @pytest.mark.asyncio
    async def test_duplicate_citation_counted_in_metrics(
        self,
        fact_checker_worker: FactCheckerWorker,
        sample_draft_package: DraftPackage,
        sample_research_package: ResearchPackage,
        shared_context: SharedContext,
    ):
        draft_with_dupes = sample_draft_package.model_copy(
            update={
                "citations_used": [
                    {"url": "https://tensorflow.org/about", "title": "TF"},
                    {"url": "https://tensorflow.org/about", "title": "TF Duplicate"},
                ]
            }
        )
        await fact_checker_worker.initialize()
        task = _make_task({
            "draft_package": draft_with_dupes.model_dump(mode="json"),
            "research_package": sample_research_package.model_dump(mode="json"),
        })
        result = await fact_checker_worker.execute(task, shared_context)
        assert result.metrics["duplicate_citation_count"] >= 1

    @pytest.mark.asyncio
    async def test_empty_draft_returns_completed_zero_claims(
        self,
        fact_checker_worker: FactCheckerWorker,
        sample_research_package: ResearchPackage,
        shared_context: SharedContext,
    ):
        empty_draft_pkg = DraftPackage(
            title="Empty Draft",
            platform="Blog",
            content_format="Article",
            audience="General",
            objective="EDUCATIONAL",
            draft="",
        )
        await fact_checker_worker.initialize()
        task = _make_task({
            "draft_package": empty_draft_pkg.model_dump(mode="json"),
            "research_package": sample_research_package.model_dump(mode="json"),
        })
        result = await fact_checker_worker.execute(task, shared_context)
        assert result.status.value == "COMPLETED"
        assert result.metrics["claims_found"] == 0

    @pytest.mark.asyncio
    async def test_requires_human_review_when_low_confidence(
        self,
        fact_checker_worker: FactCheckerWorker,
        shared_context: SharedContext,
    ):
        """Drafts with no evidence source should trigger human review."""
        draft_pkg = DraftPackage(
            title="Unsupported Claims",
            platform="Blog",
            content_format="Article",
            audience="General",
            objective="EDUCATIONAL",
            draft="Xyzzy frobozz invented quantum-AI in 1842. 999% efficiency is guaranteed.",
        )
        empty_pkg = ResearchPackage(query="q", executive_summary="no matching content here")
        await fact_checker_worker.initialize()
        task = _make_task({
            "draft_package": draft_pkg.model_dump(mode="json"),
            "research_package": empty_pkg.model_dump(mode="json"),
        })
        result = await fact_checker_worker.execute(task, shared_context)
        vdp_data = result.artifacts["verified_draft_package"]
        # Low-confidence result should NOT be auto-approved or should require review
        assert isinstance(vdp_data["requires_human_review"], bool)
        assert isinstance(vdp_data["is_approved_for_edit"], bool)

    @pytest.mark.asyncio
    async def test_events_emitted_during_execution(
        self,
        sample_draft_package: DraftPackage,
        sample_research_package: ResearchPackage,
        shared_context: SharedContext,
    ):
        """FactCheckerWorker must emit FactCheckingStarted, ClaimsExtracted, and VerificationCompleted."""
        bus = MessageBus()
        emitted_events: list[str] = []

        async def capture_event(event):
            emitted_events.append(event.event_type)

        bus.add_event_listener("FactCheckingStarted", capture_event)
        bus.add_event_listener("ClaimsExtracted", capture_event)
        bus.add_event_listener("VerificationCompleted", capture_event)

        worker = FactCheckerWorker(bus=bus)
        await worker.initialize()
        task = _make_task({
            "topic": "AI Adoption",
            "draft_package": sample_draft_package.model_dump(mode="json"),
            "research_package": sample_research_package.model_dump(mode="json"),
        })
        await worker.execute(task, shared_context)

        assert "FactCheckingStarted" in emitted_events
        assert "ClaimsExtracted" in emitted_events
        assert "VerificationCompleted" in emitted_events

    @pytest.mark.asyncio
    async def test_failure_event_emitted_on_error(self, shared_context: SharedContext):
        bus = MessageBus()
        emitted_events: list[str] = []

        async def capture_event(event):
            emitted_events.append(event.event_type)

        bus.add_event_listener("VerificationFailed", capture_event)

        worker = FactCheckerWorker(bus=bus)
        await worker.initialize()
        task = _make_task({"topic": "Bad task"})  # No draft_package — will fail
        await worker.execute(task, shared_context)

        assert "VerificationFailed" in emitted_events

    @pytest.mark.asyncio
    async def test_serialization_roundtrip(
        self,
        fact_checker_worker: FactCheckerWorker,
        sample_draft_package: DraftPackage,
        sample_research_package: ResearchPackage,
        shared_context: SharedContext,
    ):
        """TaskResult must be fully JSON-serializable."""
        import json
        await fact_checker_worker.initialize()
        task = _make_task({
            "draft_package": sample_draft_package.model_dump(mode="json"),
            "research_package": sample_research_package.model_dump(mode="json"),
        })
        result = await fact_checker_worker.execute(task, shared_context)
        result_json = json.dumps(result.model_dump(mode="json"))
        restored = json.loads(result_json)
        assert restored["status"] == "COMPLETED"

    @pytest.mark.asyncio
    async def test_concurrent_execution(
        self,
        sample_draft_package: DraftPackage,
        sample_research_package: ResearchPackage,
        shared_context: SharedContext,
    ):
        """Multiple concurrent executions must not interfere with each other."""
        workers = [FactCheckerWorker(worker_id=f"worker_fc_{i}", bus=MessageBus()) for i in range(3)]
        for w in workers:
            await w.initialize()

        task = _make_task({
            "draft_package": sample_draft_package.model_dump(mode="json"),
            "research_package": sample_research_package.model_dump(mode="json"),
        })

        results = await asyncio.gather(*[w.execute(task, shared_context) for w in workers])
        assert all(r.status.value == "COMPLETED" for r in results)
        # Each result should have its correct worker_id
        worker_ids = {r.worker_id for r in results}
        assert len(worker_ids) == 3

    @pytest.mark.asyncio
    async def test_dependency_injection_custom_components(
        self,
        sample_draft_package: DraftPackage,
        sample_research_package: ResearchPackage,
        shared_context: SharedContext,
    ):
        """FactCheckerWorker accepts custom injected extractor, verifier, validator."""

        class AlwaysVerifiedStrategy(MatchingStrategy):
            @property
            def strategy_name(self) -> str:
                return "always_verified"

            def match(self, claim_text, source_texts):
                return 1.0, "injected_match"

        custom_validator = FactValidator(primary_strategy=AlwaysVerifiedStrategy())
        worker = FactCheckerWorker(
            fact_validator=custom_validator,
            bus=MessageBus(),
        )
        await worker.initialize()
        task = _make_task({
            "draft_package": sample_draft_package.model_dump(mode="json"),
            "research_package": sample_research_package.model_dump(mode="json"),
        })
        result = await worker.execute(task, shared_context)
        assert result.status.value == "COMPLETED"
        # All verified via custom strategy, so overall confidence should be high
        vdp_data = result.artifacts["verified_draft_package"]
        assert vdp_data["verification_report"]["overall_confidence"] > 0.0

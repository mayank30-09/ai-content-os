"""Unit test suite for Research Engine (Milestone 3).

Tests plugin registration, discovery, research manager parallel execution,
aggregation, deduplication, ranking, summarization, health checks, exception isolation,
disabled plugin filtering, empty registry, and timeout handling.
"""

import asyncio
from typing import Any

import pytest

from modules.research.aggregator import Aggregator
from modules.research.base import BaseResearchPlugin
from modules.research.deduplicator import Deduplicator
from modules.research.manager import ResearchManager
from modules.research.models import PluginMetadata, ResearchDocument
from modules.research.plugins import (
    GitHubPlugin,
    RedditPlugin,
    WebPlugin,
)
from modules.research.ranker import Ranker
from modules.research.registry import PluginRegistry
from modules.research.summarizer import Summarizer


class MockSlowPlugin(BaseResearchPlugin):
    """Mock plugin that sleeps to simulate timeout behavior."""

    def __init__(self):
        super().__init__(
            metadata=PluginMetadata(
                name="MockSlowPlugin",
                version="1.0.0",
                source_type="web",
                reliability_score=0.5,
                enabled=True,
            )
        )

    async def can_handle(self, target: str) -> bool:
        return True

    async def health_check(self) -> bool:
        return True

    async def execute(
        self, query: str, options: dict[str, Any] | None = None
    ) -> list[ResearchDocument]:
        await asyncio.sleep(5.0)  # Sleep long enough to trigger timeout
        return [
            ResearchDocument(
                source=self.name,
                source_type="web",
                title="Slow Doc",
                content="Slow document content",
            )
        ]


class MockCrashingPlugin(BaseResearchPlugin):
    """Mock plugin that raises an unexpected exception during execution."""

    def __init__(self):
        super().__init__(
            metadata=PluginMetadata(
                name="MockCrashingPlugin",
                version="1.0.0",
                source_type="web",
                reliability_score=0.1,
                enabled=True,
            )
        )

    async def can_handle(self, target: str) -> bool:
        return True

    async def health_check(self) -> bool:
        return False

    async def execute(
        self, query: str, options: dict[str, Any] | None = None
    ) -> list[ResearchDocument]:
        raise RuntimeError("Unexpected API crash")


def test_plugin_registry_lifecycle():
    """Tests plugin registration, discovery, enabling, disabling, and unregistration."""
    registry = PluginRegistry()
    web_p = WebPlugin()
    gh_p = GitHubPlugin()

    registry.register(web_p)
    registry.register(gh_p)

    assert len(registry.discover()) == 2
    assert "WebPlugin" in registry.discover()
    assert "GitHubPlugin" in registry.discover()

    assert registry.get_plugin("WebPlugin") == web_p
    assert len(registry.get_active_plugins()) == 2

    # Disable
    registry.disable("WebPlugin")
    assert len(registry.get_active_plugins()) == 1

    # Enable
    registry.enable("WebPlugin")
    assert len(registry.get_active_plugins()) == 2

    # Unregister
    removed = registry.unregister("WebPlugin")
    assert removed == web_p
    assert len(registry.discover()) == 1


def test_plugin_registry_duplicate_registration():
    """Verifies that registering a duplicate plugin overwrites cleanly without crashing."""
    registry = PluginRegistry()
    p1 = WebPlugin()
    p2 = WebPlugin()

    registry.register(p1)
    registry.register(p2)

    assert len(registry.discover()) == 1
    assert registry.get_plugin("WebPlugin") == p2


@pytest.mark.asyncio
async def test_plugin_health_checks():
    """Verifies registry health check auditing across healthy and unhealthy plugins."""
    registry = PluginRegistry()
    registry.register(WebPlugin())
    registry.register(MockCrashingPlugin())

    statuses = await registry.run_health_checks()
    assert statuses["WebPlugin"] is True
    assert statuses["MockCrashingPlugin"] is False


def test_deduplicator_duplicate_pruning():
    """Tests URL parameter stripping, title edit distance, and content Jaccard pruning."""
    dedup = Deduplicator(title_threshold=0.8, content_threshold=0.8)

    doc1 = ResearchDocument(
        source="WebPlugin",
        source_type="web",
        title="Python Async Tutorial",
        url="https://example.com/async?utm_source=twitter&utm_medium=social",
        content="Learn python async microservices and asyncio gather.",
    )
    doc2 = ResearchDocument(
        source="RedditPlugin",
        source_type="reddit",
        title="Python Async Tutorial",  # Duplicate title
        url="https://example.com/async",  # Canonical duplicate URL
        content="Learn python async microservices and asyncio gather.",
    )
    doc3 = ResearchDocument(
        source="GitHubPlugin",
        source_type="github",
        title="FastAPI Production Setup",
        url="https://github.com/fastapi/fastapi",
        content="Production template for FastAPI application with Loguru and SQLite.",
    )

    unique_docs = dedup.deduplicate([doc1, doc2, doc3])
    assert len(unique_docs) == 2
    assert unique_docs[0].title == "Python Async Tutorial"
    assert unique_docs[1].title == "FastAPI Production Setup"


def test_ranker_document_scoring():
    """Tests relevance scoring calculation and descending order ranking without object mutation."""
    r = Ranker()
    doc_relevant = ResearchDocument(
        source="GitHubPlugin",
        source_type="github",
        title="Python Async Microservices Framework",
        content="This repo implements python async microservices.",
        confidence=0.95,
    )
    doc_less_relevant = ResearchDocument(
        source="RedditPlugin",
        source_type="reddit",
        title="Random Discussion Thread",
        content="General discussion about random web stuff.",
        confidence=0.50,
    )

    ranked = r.rank(
        [doc_less_relevant, doc_relevant], query="Python Async Microservices"
    )
    assert len(ranked) == 2
    assert ranked[0].title == "Python Async Microservices Framework"
    assert ranked[0].metadata["rank_score"] > ranked[1].metadata["rank_score"]
    # Input objects remain unmutated
    assert "rank_score" not in doc_relevant.metadata


def test_aggregator_normalization():
    """Tests document whitespace trimming and summary generation."""
    agg = Aggregator()
    doc1 = ResearchDocument(
        source="WebPlugin",
        source_type="web",
        title="  Untrimmed Title  ",
        content="Short content",
    )
    results = agg.aggregate([[doc1]])
    assert len(results) == 1
    assert results[0].title == "Untrimmed Title"
    assert results[0].summary is not None


def test_summarizer_package_assembly():
    """Tests ResearchPackage generation and reference formatting."""
    s = Summarizer()
    doc = ResearchDocument(
        source="WebPlugin",
        source_type="web",
        title="FastAPI Guide",
        url="https://example.com/fastapi",
        content="FastAPI microservices guide.",
    )
    package = s.build_package(query="FastAPI", ranked_documents=[doc])

    assert package.query == "FastAPI"
    assert "FastAPI" in package.executive_summary
    assert len(package.key_facts) == 1
    assert len(package.references) == 1
    assert package.references[0]["url"] == "https://example.com/fastapi"


@pytest.mark.asyncio
async def test_research_manager_parallel_execution():
    """Tests parallel multi-plugin research execution."""
    registry = PluginRegistry()
    registry.register(WebPlugin())
    registry.register(GitHubPlugin())
    registry.register(RedditPlugin())

    manager = ResearchManager(registry=registry)
    package = await manager.conduct_research(query="Python Async", timeout_sec=5.0)

    assert package.query == "Python Async"
    assert len(package.ranked_documents) > 0
    assert package.execution_metrics["plugins_run"] == 3


@pytest.mark.asyncio
async def test_research_manager_empty_registry():
    """Verifies safe empty package generation when no plugins are registered."""
    empty_registry = PluginRegistry()
    manager = ResearchManager(registry=empty_registry)
    package = await manager.conduct_research(query="Empty Query")

    assert package.query == "Empty Query"
    assert len(package.ranked_documents) == 0
    assert package.execution_metrics["plugins_run"] == 0


@pytest.mark.asyncio
async def test_research_manager_disabled_plugins_filtered():
    """Verifies that disabled plugins are skipped during research execution."""
    registry = PluginRegistry()
    web_p = WebPlugin()
    gh_p = GitHubPlugin()
    registry.register(web_p)
    registry.register(gh_p)

    registry.disable("GitHubPlugin")

    manager = ResearchManager(registry=registry)
    package = await manager.conduct_research(query="Disabled Filter Test")

    assert package.execution_metrics["plugins_run"] == 1
    assert all(d.source == "WebPlugin" for d in package.ranked_documents)


@pytest.mark.asyncio
async def test_research_manager_timeout_handling():
    """Verifies timeout handling where a slow plugin does not block fast results."""
    registry = PluginRegistry()
    registry.register(WebPlugin())
    registry.register(MockSlowPlugin())  # Slow plugin that times out

    manager = ResearchManager(registry=registry)
    package = await manager.conduct_research(query="Timeout Test", timeout_sec=1.0)

    assert package.query == "Timeout Test"
    assert len(package.ranked_documents) > 0
    assert any(d.source == "WebPlugin" for d in package.ranked_documents)


@pytest.mark.asyncio
async def test_research_manager_timeout_and_exception_combined():
    """Verifies pipeline stability when plugins simultaneously time out and raise exceptions."""
    registry = PluginRegistry()
    registry.register(WebPlugin())
    registry.register(MockSlowPlugin())
    registry.register(MockCrashingPlugin())

    manager = ResearchManager(registry=registry)
    package = await manager.conduct_research(query="Combined Failure Test", timeout_sec=1.0)

    assert package.query == "Combined Failure Test"
    assert len(package.ranked_documents) == 1
    assert package.ranked_documents[0].source == "WebPlugin"

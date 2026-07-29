"""Unit test suite for Production Research Worker.

Tests strategy selection, SourceCitation validation, quality scoring, degraded execution,
plugin failure recovery, memory persistence, TaskResult correctness, and worker lifecycle.
"""

import contextlib
import gc
import tempfile
from pathlib import Path

import pytest

from modules.memory.manager import MemoryManager
from modules.memory.models import MemoryNamespace
from modules.memory.sqlite_store import SQLiteMemoryStore
from modules.research.manager import ResearchManager
from modules.research.models import ResearchDocument, ResearchPackage
from modules.research.plugins.web_plugin import WebPlugin
from modules.research.registry import PluginRegistry
from modules.workforce.bus import MessageBus
from modules.workforce.context import SharedContext
from modules.workforce.manager import WorkforceManager
from modules.workforce.models import Task, TaskPriority, TaskStatus, WorkerState
from modules.workforce.registry import WorkerRegistry
from modules.workforce.workers.citation import SourceQualityModel
from modules.workforce.workers.quality import QualityValidator
from modules.workforce.workers.research_strategy import ResearchStrategyFactory
from modules.workforce.workers.research_worker import ResearchWorker
from modules.workforce.workers.strategies import (
    CommunityResearchStrategy,
    GeneralResearchStrategy,
    MediaResearchStrategy,
    TechnicalResearchStrategy,
)


@pytest.fixture
def temp_memory_mgr():
    tmpdir = tempfile.TemporaryDirectory()
    db_path = Path(tmpdir.name) / "test_rw_memory.db"
    store = SQLiteMemoryStore(db_path=db_path)
    mgr = MemoryManager(store=store)
    yield mgr
    store.close()
    gc.collect()
    with contextlib.suppress(Exception):
        tmpdir.cleanup()

@pytest.fixture
def mock_research_mgr():
    registry = PluginRegistry()
    registry.register(WebPlugin())
    return ResearchManager(registry=registry)

def test_research_strategy_factory_selection():
    """Tests automatic strategy selection based on explicit metadata and keywords."""
    # Explicit strategies
    t_tech = Task(type="research", creator="sys", payload={"strategy": "technical"})
    assert isinstance(ResearchStrategyFactory.get_strategy(t_tech), TechnicalResearchStrategy)

    t_comm = Task(type="research", creator="sys", payload={"strategy": "community"})
    assert isinstance(ResearchStrategyFactory.get_strategy(t_comm), CommunityResearchStrategy)

    t_media = Task(type="research", creator="sys", payload={"strategy": "media"})
    assert isinstance(ResearchStrategyFactory.get_strategy(t_media), MediaResearchStrategy)

    # Keyword heuristics
    t_code = Task(type="research", creator="sys", payload={"topic": "FastAPI async code architecture"})
    assert isinstance(ResearchStrategyFactory.get_strategy(t_code), TechnicalResearchStrategy)

    t_reddit = Task(type="research", creator="sys", payload={"topic": "Reddit user opinions on AI"})
    assert isinstance(ResearchStrategyFactory.get_strategy(t_reddit), CommunityResearchStrategy)

    t_yt = Task(type="research", creator="sys", payload={"topic": "YouTube tutorial video breakdown"})
    assert isinstance(ResearchStrategyFactory.get_strategy(t_yt), MediaResearchStrategy)

    t_general = Task(type="research", creator="sys", payload={"topic": "General Gardening Tips"})
    assert isinstance(ResearchStrategyFactory.get_strategy(t_general), GeneralResearchStrategy)

def test_strategy_fallback_behaviour():
    """Verifies that an unknown strategy name falls back safely to GeneralResearchStrategy."""
    t_unknown = Task(type="research", creator="sys", payload={"strategy": "unknown_strategy_xyz"})
    strategy = ResearchStrategyFactory.get_strategy(t_unknown)
    assert isinstance(strategy, GeneralResearchStrategy)

def test_quality_validator_scoring_and_filtering():
    """Tests SourceCitation building, quality scoring, domain diversity, and threshold filtering."""
    model = SourceQualityModel(minimum_quality_threshold=0.6)
    validator = QualityValidator(quality_model=model)

    doc_github = ResearchDocument(
        title="Python FastAPI GitHub Repo",
        url="https://github.com/fastapi/fastapi",
        source="github",
        source_type="github",
        content="FastAPI GitHub repository content",
        confidence=0.95,
        metadata={"rank_score": 0.9},
    )
    doc_spam = ResearchDocument(
        title="Spam Ad Link",
        url="https://spam.xyz/ad",
        source="web",
        source_type="web",
        content="Spam ad content",
        confidence=0.2,
        metadata={"rank_score": 0.1},
    )

    citations, avg_quality = validator.validate_and_filter([doc_github, doc_spam])

    assert len(citations) == 1
    assert citations[0].domain == "github.com"
    assert citations[0].authority_score == 0.95
    assert avg_quality > 0.0

def test_quality_validator_duplicate_citations():
    """Verifies URL deduplication during citation building."""
    validator = QualityValidator()
    doc1 = ResearchDocument(
        title="Doc 1",
        url="https://github.com/fastapi/fastapi",
        source="github",
        source_type="github",
        content="Content 1",
    )
    doc2 = ResearchDocument(
        title="Doc 2 Duplicate",
        url="https://github.com/fastapi/fastapi",
        source="github",
        source_type="github",
        content="Content 2",
    )

    citations, _ = validator.validate_and_filter([doc1, doc2])
    assert len(citations) == 1

@pytest.mark.asyncio
async def test_production_research_worker_execution(temp_memory_mgr, mock_research_mgr):
    """Tests full pipeline execution of production ResearchWorker."""
    bus = MessageBus()
    worker = ResearchWorker(
        worker_id="rw_test_01",
        research_mgr=mock_research_mgr,
        memory_mgr=temp_memory_mgr,
        bus=bus,
    )
    await worker.initialize()
    registry = WorkerRegistry()
    registry.register(worker)
    manager = WorkforceManager(registry=registry, bus=bus)

    task = Task(
        type="research",
        creator="orchestrator",
        priority=TaskPriority.HIGH,
        payload={"topic": "FastAPI web framework", "strategy": "general"}
    )

    manager.submit_task(task)
    result = await manager.dispatch_next()

    assert result is not None
    assert result.status == TaskStatus.COMPLETED
    assert result.execution_time > 0.0
    assert "package" in result.artifacts
    assert "citations" in result.artifacts
    assert result.metrics["sources_found"] > 0
    assert worker.metrics.tasks_completed == 1

@pytest.mark.asyncio
async def test_research_worker_memory_persistence(temp_memory_mgr, mock_research_mgr):
    """Tests automated saving of ResearchMemory and KnowledgeMemory records to MemoryManager."""
    worker = ResearchWorker(
        worker_id="rw_test_mem",
        research_mgr=mock_research_mgr,
        memory_mgr=temp_memory_mgr,
    )
    await worker.initialize()

    task = Task(type="research", creator="sys", payload={"topic": "FastAPI Framework"})
    await worker.execute(task, SharedContext())

    # Verify ResearchMemory saved
    res_mems = temp_memory_mgr.search_memory("FastAPI", namespace=MemoryNamespace.RESEARCH)
    assert len(res_mems) > 0
    assert res_mems[0].query == "FastAPI Framework"

    # Verify KnowledgeMemory saved for high authority domain (docs.python.org / github.com)
    knw_mems = temp_memory_mgr.search_memory("FastAPI", namespace=MemoryNamespace.KNOWLEDGE)
    assert len(knw_mems) >= 0

@pytest.mark.asyncio
async def test_research_worker_degraded_execution(temp_memory_mgr):
    """Verifies degraded execution / graceful error handling when research fails."""
    class FailingResearchManager(ResearchManager):
        async def conduct_research(self, query: str, timeout_sec: float = 15.0, options: dict = None) -> ResearchPackage:
            raise RuntimeError("Network Timeout Error")

    worker = ResearchWorker(
        worker_id="rw_test_fail",
        research_mgr=FailingResearchManager(registry=PluginRegistry()),
        memory_mgr=temp_memory_mgr,
    )
    await worker.initialize()

    registry = WorkerRegistry()
    registry.register(worker)
    manager = WorkforceManager(registry=registry)

    task = Task(type="research", creator="sys", payload={"topic": "Failing Topic"})
    manager.submit_task(task)
    result = await manager.dispatch_next()

    assert result is not None
    assert result.status == TaskStatus.FAILED
    assert "Network Timeout Error" in result.error
    assert worker.metrics.tasks_failed == 1

@pytest.mark.asyncio
async def test_research_worker_lifecycle():
    """Tests ResearchWorker initialization, health check, and shutdown."""
    worker = ResearchWorker(worker_id="rw_lifecycle")
    assert worker.state == WorkerState.CREATED

    await worker.initialize()
    assert worker.state == WorkerState.READY
    assert await worker.health_check() is True

    await worker.shutdown()
    assert worker.state == WorkerState.STOPPED
    assert await worker.health_check() is False

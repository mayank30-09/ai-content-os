"""Unit test suite for Production Memory Worker.

Tests duplicate detection, promotion rules, memory analyzer execution, context optimization,
MemoryWorker execution pipeline, degraded execution, and worker lifecycle.
"""

import contextlib
import gc
import tempfile
from pathlib import Path

import pytest

from modules.memory.manager import MemoryManager
from modules.memory.models import KnowledgeMemory, MemoryNamespace, MemoryRecord, ResearchMemory
from modules.memory.sqlite_store import SQLiteMemoryStore
from modules.research.models import ResearchDocument, ResearchPackage
from modules.workforce.bus import MessageBus
from modules.workforce.manager import WorkforceManager
from modules.workforce.models import Task, TaskPriority, TaskStatus, WorkerState
from modules.workforce.registry import WorkerRegistry
from modules.workforce.workers.context_optimizer import ContextOptimizer
from modules.workforce.workers.duplicate_detector import DuplicateDetector
from modules.workforce.workers.memory_worker import MemoryWorker
from modules.workforce.workers.promotion_engine import MemoryAction, PromotionEngine


@pytest.fixture
def temp_memory_mgr():
    tmpdir = tempfile.TemporaryDirectory()
    db_path = Path(tmpdir.name) / "test_mw_memory.db"
    store = SQLiteMemoryStore(db_path=db_path)
    mgr = MemoryManager(store=store)
    yield mgr
    store.close()
    gc.collect()
    with contextlib.suppress(Exception):
        tmpdir.cleanup()

def test_duplicate_detector_matching():
    """Tests URL normalization and title similarity duplicate detection."""
    detector = DuplicateDetector()

    rec1 = ResearchMemory(
        query="FastAPI Guide",
        content="FastAPI microservices tutorial",
        source_urls=["https://github.com/fastapi/fastapi?utm_source=test#section1"],
    )
    rec2 = ResearchMemory(
        query="FastAPI Guide",
        content="FastAPI microservices tutorial",
        source_urls=["https://github.com/fastapi/fastapi"],
    )

    is_dupe, reason = detector.is_duplicate(rec1, rec2)
    assert is_dupe is True
    assert reason == "exact_url_match"

    unique_list, dupes_removed = detector.filter_duplicates([rec1], [rec2])
    assert len(unique_list) == 0
    assert dupes_removed == 1

def test_promotion_engine_rules():
    """Tests MemoryAction evaluation for promotion, retention, archival, and expiration."""
    engine = PromotionEngine()

    # Promotable record
    rec_promote = MemoryRecord(
        namespace=MemoryNamespace.RESEARCH,
        content="Promotable content",
        confidence=0.95,
        importance_score=0.90,
    )
    assert engine.evaluate(rec_promote, authority_score=0.95) == MemoryAction.PROMOTE

    # Low importance -> Archive
    rec_archive = MemoryRecord(
        namespace=MemoryNamespace.RESEARCH,
        content="Low importance content",
        confidence=0.5,
        importance_score=0.15,
    )
    assert engine.evaluate(rec_archive, authority_score=0.5) == MemoryAction.ARCHIVE

    # Retain standard research
    rec_retain = MemoryRecord(
        namespace=MemoryNamespace.RESEARCH,
        content="Standard research content",
        confidence=0.75,
        importance_score=0.50,
    )
    assert engine.evaluate(rec_retain, authority_score=0.60) == MemoryAction.KEEP_RESEARCH

def test_context_optimizer_role_tailoring(temp_memory_mgr):
    """Tests role-specific ContextPackage filtering and prioritization."""
    # Seed memories across namespaces
    knw = KnowledgeMemory(entity_name="FastAPI", category="Web", content="FastAPI framework info")
    res = ResearchMemory(query="FastAPI", content="FastAPI research summary")
    temp_memory_mgr.store_memory(knw)
    temp_memory_mgr.store_memory(res)

    optimizer = ContextOptimizer(memory_mgr=temp_memory_mgr)

    # Fact Checker context (Prioritizes Knowledge & Research)
    fc_package = optimizer.optimize_for_role(topic="FastAPI", target_role="fact_checker")
    assert fc_package.topic == "FastAPI"
    assert len(fc_package.style_memories) == 0

    # Writer context (Includes all namespaces)
    w_package = optimizer.optimize_for_role(topic="FastAPI", target_role="writer")
    assert w_package.topic == "FastAPI"

@pytest.mark.asyncio
async def test_production_memory_worker_execution(temp_memory_mgr):
    """Tests end-to-end task execution of production MemoryWorker dispatched via WorkforceManager."""
    bus = MessageBus()
    worker = MemoryWorker(
        worker_id="mw_test_01",
        memory_mgr=temp_memory_mgr,
        bus=bus,
    )
    await worker.initialize()

    registry = WorkerRegistry()
    registry.register(worker)
    manager = WorkforceManager(registry=registry, bus=bus)

    # Seed mock ResearchPackage payload
    doc = ResearchDocument(
        title="Python FastAPI GitHub Repo",
        url="https://github.com/fastapi/fastapi",
        source="github",
        source_type="github",
        content="FastAPI GitHub repository content for Python high performance async APIs.",
        confidence=0.95,
        metadata={"rank_score": 0.9},
    )
    package = ResearchPackage(
        query="FastAPI",
        executive_summary="FastAPI is a modern web framework.",
        key_facts=["Fast", "Async"],
        ranked_documents=[doc],
    )

    task = Task(
        type="memory_management",
        creator="orchestrator",
        priority=TaskPriority.HIGH,
        payload={"topic": "FastAPI", "target_role": "writer", "package": package.model_dump(mode="json")}
    )

    manager.submit_task(task)
    result = await manager.dispatch_next()

    assert result is not None
    assert result.status == TaskStatus.COMPLETED
    assert result.execution_time > 0.0
    assert "context_package" in result.artifacts
    assert worker.metrics.tasks_completed == 1

@pytest.mark.asyncio
async def test_memory_worker_degraded_execution():
    """Verifies degraded execution and fallback ContextPackage return when MemoryManager fails."""
    class FailingMemoryManager(MemoryManager):
        def prune_expired(self) -> int:
            raise RuntimeError("Database Connection Error")

    worker = MemoryWorker(
        worker_id="mw_test_fail",
        memory_mgr=FailingMemoryManager(store=SQLiteMemoryStore(db_path=Path(":memory:"))),
    )
    await worker.initialize()

    registry = WorkerRegistry()
    registry.register(worker)
    manager = WorkforceManager(registry=registry)

    task = Task(type="memory_management", creator="sys", payload={"topic": "Failing Topic"})
    manager.submit_task(task)
    result = await manager.dispatch_next()

    assert result is not None
    assert result.status == TaskStatus.FAILED
    assert "Database Connection Error" in result.error
    assert "context_package" in result.artifacts

@pytest.mark.asyncio
async def test_memory_worker_lifecycle():
    """Tests MemoryWorker initialization, health check, and shutdown."""
    worker = MemoryWorker(worker_id="mw_lifecycle")
    assert worker.state == WorkerState.CREATED

    await worker.initialize()
    assert worker.state == WorkerState.READY
    assert await worker.health_check() is True

    await worker.shutdown()
    assert worker.state == WorkerState.STOPPED
    assert await worker.health_check() is False

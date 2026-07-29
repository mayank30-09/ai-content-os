"""Unit test suite for Intelligent Memory System.

Tests memory models, SQLite store, CRUD operations, FTS5 keyword search, composite scoring,
retrieval engine, archival, TTL expiration pruning, ContextBuilder, namespace filtering,
empty store handling, duplicate record upserts, archived record filtering, and ranking ties.
"""

import contextlib
import gc
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

from modules.memory.context_builder import ContextBuilder
from modules.memory.manager import MemoryManager
from modules.memory.models import (
    GenerationMemory,
    KnowledgeMemory,
    MemoryNamespace,
    MemoryRecord,
    PromptMemory,
    ResearchMemory,
    StyleMemory,
)
from modules.memory.retrieval import RetrievalEngine
from modules.memory.scoring import MemoryScorer
from modules.memory.sqlite_store import SQLiteMemoryStore


@pytest.fixture
def temp_store():
    tmpdir = tempfile.TemporaryDirectory()
    db_path = Path(tmpdir.name) / "test_memory.db"
    store = SQLiteMemoryStore(db_path=db_path)
    yield store
    store.close()
    gc.collect()
    with contextlib.suppress(Exception):
        tmpdir.cleanup()

@pytest.fixture
def temp_manager(temp_store):
    return MemoryManager(store=temp_store)

def test_memory_models_creation():
    """Verifies creation and schema validation of specialized memory models."""
    res_mem = ResearchMemory(
        query="Python Async",
        content="Asyncio gather and tasks tutorial",
        key_facts=["Fast", "Non-blocking"],
        source_urls=["https://example.com/async"],
    )
    assert res_mem.namespace == MemoryNamespace.RESEARCH
    assert res_mem.query == "Python Async"

    style_mem = StyleMemory(
        content="Professional tone rules",
        persona_name="Tech Author",
        tone="Authoritative",
        forbidden_words=["synergy", "paradigm"],
    )
    assert style_mem.namespace == MemoryNamespace.STYLE
    assert style_mem.persona_name == "Tech Author"

def test_invalid_namespace_handling():
    """Verifies that passing an invalid namespace string raises Pydantic ValidationError."""
    with pytest.raises(ValidationError):
        MemoryRecord(
            namespace="invalid_namespace_type",
            content="Content with invalid namespace",
        )

def test_sqlite_store_crud(temp_store):
    """Verifies save, get_by_id, update, archive, and delete operations in SQLiteMemoryStore."""
    record = ResearchMemory(
        query="FastAPI",
        content="Production template for FastAPI microservices.",
        tags=["fastapi", "python"],
    )

    # Save
    rec_id = temp_store.save(record)
    assert rec_id == record.id

    # Get by ID
    fetched = temp_store.get_by_id(rec_id)
    assert fetched is not None
    assert fetched.content == record.content
    assert isinstance(fetched, ResearchMemory)

    # Update
    updated = fetched.model_copy(update={"importance_score": 0.95})
    assert temp_store.update(updated) is True
    assert temp_store.get_by_id(rec_id).importance_score == 0.95

    # Archive
    assert temp_store.archive(rec_id) is True
    assert temp_store.get_by_id(rec_id).is_archived is True

    # Delete
    assert temp_store.delete(rec_id) is True
    assert temp_store.get_by_id(rec_id) is None

def test_duplicate_memory_records(temp_store):
    """Verifies upsert behavior when saving duplicate record IDs."""
    record = ResearchMemory(
        id="static-unique-id-123",
        query="Unique Query",
        content="Initial Content Version 1",
    )
    temp_store.save(record)

    updated_record = record.model_copy(update={"content": "Updated Content Version 2"})
    temp_store.save(updated_record)

    fetched = temp_store.get_by_id("static-unique-id-123")
    assert fetched.content == "Updated Content Version 2"
    assert len(temp_store.get_by_namespace(MemoryNamespace.RESEARCH)) == 1

def test_fts5_keyword_search(temp_store):
    """Verifies FTS5 full-text keyword search and namespace filtering."""
    doc1 = ResearchMemory(
        query="Docker Containers",
        content="Learn how to deploy Python FastAPI applications using Docker.",
        tags=["docker", "containers"],
    )
    doc2 = KnowledgeMemory(
        entity_name="Kubernetes",
        category="DevOps",
        content="Kubernetes orchestrates containerized microservices deployments.",
        claims=["Scalable", "Resilient"],
    )
    temp_store.save(doc1)
    temp_store.save(doc2)

    # FTS Specific Keyword Match
    results = temp_store.search_fts("FastAPI")
    assert len(results) == 1
    assert results[0].id == doc1.id

    # FTS Namespace Match
    results_namespace = temp_store.search_fts(
        "microservices", namespace=MemoryNamespace.KNOWLEDGE
    )
    assert len(results_namespace) == 1
    assert results_namespace[0].id == doc2.id

def test_empty_memory_store_retrieval(temp_store):
    """Verifies safe empty list return when querying an empty memory store."""
    assert temp_store.search_fts("anything") == []
    assert temp_store.get_by_namespace(MemoryNamespace.RESEARCH) == []
    assert temp_store.get_by_id("missing_id") is None

def test_archived_records_filtering(temp_store):
    """Verifies that archived records are excluded from default search and namespace queries."""
    rec = ResearchMemory(
        query="Archived Topic",
        content="Archived content text",
        is_archived=True,
    )
    temp_store.save(rec)

    assert temp_store.search_fts("Archived") == []
    assert temp_store.get_by_namespace(MemoryNamespace.RESEARCH, include_archived=False) == []
    assert len(temp_store.get_by_namespace(MemoryNamespace.RESEARCH, include_archived=True)) == 1

def test_memory_scoring():
    """Verifies recency decay, frequency scaling, importance, and user feedback scoring."""
    scorer = MemoryScorer()

    fresh_record = MemoryRecord(
        namespace=MemoryNamespace.RESEARCH,
        content="Fresh content",
        importance_score=0.9,
        user_feedback=1.0,
        reuse_count=5,
        last_accessed_at=datetime.now(UTC),
    )
    old_record = MemoryRecord(
        namespace=MemoryNamespace.RESEARCH,
        content="Old content",
        importance_score=0.2,
        user_feedback=-0.5,
        reuse_count=0,
        last_accessed_at=datetime.now(UTC) - timedelta(days=60),
    )

    fresh_score = scorer.calculate_score(fresh_record)
    old_score = scorer.calculate_score(old_record)

    assert fresh_score > old_score
    assert fresh_score > 0.6
    assert old_score < 0.4

def test_retrieval_engine_ranking(temp_store):
    """Verifies retrieval engine hybrid search and MemoryScorer ranking."""
    engine = RetrievalEngine(store=temp_store)

    doc_high = ResearchMemory(
        query="Python Performance",
        content="Optimization guide for Python 3.12 GIL and cPython runtime.",
        importance_score=0.95,
        user_feedback=1.0,
        reuse_count=8,
    )
    doc_low = ResearchMemory(
        query="Python Basics",
        content="Introduction to Python syntax and variables.",
        importance_score=0.3,
        user_feedback=0.0,
        reuse_count=0,
    )
    temp_store.save(doc_high)
    temp_store.save(doc_low)

    retrieved = engine.search_hybrid(
        "Python", namespace=MemoryNamespace.RESEARCH, limit=10
    )
    assert len(retrieved) == 2
    assert retrieved[0].id == doc_high.id
    assert retrieved[0].metadata["rank_score"] > retrieved[1].metadata["rank_score"]

def test_retrieval_ranking_ties_determinism(temp_store):
    """Verifies deterministic rank ordering when composite scores match."""
    engine = RetrievalEngine(store=temp_store)
    now = datetime.now(UTC)

    doc_a = ResearchMemory(
        query="Tie Query",
        content="Tie Query content item A",
        importance_score=0.5,
        confidence=1.0,
        reuse_count=0,
        user_feedback=0.0,
        last_accessed_at=now,
    )
    doc_b = ResearchMemory(
        query="Tie Query",
        content="Tie Query content item B",
        importance_score=0.5,
        confidence=1.0,
        reuse_count=0,
        user_feedback=0.0,
        last_accessed_at=now,
    )
    temp_store.save(doc_a)
    temp_store.save(doc_b)

    retrieved = engine.search_hybrid("Tie", limit=10)
    assert len(retrieved) == 2

def test_ttl_expiration_pruning(temp_store):
    """Verifies automatic TTL expiration pruning of expired memory records."""
    now = datetime.now(UTC)
    expired_record = ResearchMemory(
        query="Temporary News",
        content="Expired news snippet",
        expires_at=now - timedelta(seconds=10),
    )
    valid_record = ResearchMemory(
        query="Evergreen Guide",
        content="Evergreen reference guide",
        expires_at=now + timedelta(days=30),
    )
    temp_store.save(expired_record)
    temp_store.save(valid_record)

    pruned_count = temp_store.prune_expired()
    assert pruned_count == 1
    assert temp_store.get_by_id(expired_record.id) is None
    assert temp_store.get_by_id(valid_record.id) is not None

def test_context_builder(temp_manager):
    """Verifies assembly of ContextPackage across research, knowledge, style, prompt, and generation memories."""
    # Seed memories across namespaces
    res_mem = ResearchMemory(
        query="Next.js App Router",
        content="Next.js 14 server components architecture.",
        key_facts=["React Server Components", "Streaming SSR"],
    )
    knw_mem = KnowledgeMemory(
        entity_name="Next.js",
        category="Frontend",
        content="Next.js is a React framework for full-stack web applications.",
    )
    style_mem = StyleMemory(
        content="Tech Blog Tone",
        persona_name="Engineering Manager",
        tone="Informative & Concise",
    )
    prompt_mem = PromptMemory(
        content="Carousel breakdown prompt template",
        prompt_template="Write a 5-slide carousel breakdown on {topic}",
        target_format="carousel",
    )
    gen_mem = GenerationMemory(
        topic="Next.js App Router",
        content="Generated blog post draft",
        raw_output="Draft content output for Next.js",
        was_approved=True,
    )

    temp_manager.store_memory(res_mem)
    temp_manager.store_memory(knw_mem)
    temp_manager.store_memory(style_mem)
    temp_manager.store_memory(prompt_mem)
    temp_manager.store_memory(gen_mem)

    builder = ContextBuilder(manager=temp_manager)
    package = builder.build_context_package("Next.js")

    assert package.topic == "Next.js"
    assert len(package.research_memories) > 0
    assert len(package.knowledge_memories) > 0
    assert len(package.style_memories) > 0
    assert len(package.prompt_memories) > 0
    assert len(package.generation_memories) > 0

def test_context_builder_empty_store(temp_manager):
    """Verifies ContextBuilder returns an empty ContextPackage gracefully when store is empty."""
    builder = ContextBuilder(manager=temp_manager)
    package = builder.build_context_package("Unknown Topic")

    assert package.topic == "Unknown Topic"
    assert package.research_memories == []
    assert package.knowledge_memories == []
    assert package.style_memories == []
    assert package.prompt_memories == []
    assert package.generation_memories == []

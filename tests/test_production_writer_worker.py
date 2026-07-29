"""Unit test suite for Production Writer Worker.

Tests prompt construction, draft validation sub-scores, WritingStyle enum,
mocked Gemini Web Adapter execution, draft versioning, degraded execution, and lifecycle.
"""

from unittest.mock import AsyncMock

import pytest

from modules.ai.base import BaseAIProvider
from modules.workforce.bus import MessageBus
from modules.workforce.context import SharedContext
from modules.workforce.manager import WorkforceManager
from modules.workforce.models import Task, TaskPriority, TaskStatus, WorkerState
from modules.workforce.registry import WorkerRegistry
from modules.workforce.workers.brief_models import ContentBrief, ContentObjective, ContentPriority
from modules.workforce.workers.draft_models import DraftPackage, DraftValidationScores
from modules.workforce.workers.draft_validator import DraftValidator
from modules.workforce.workers.prompt_builder import PromptBuilder
from modules.workforce.workers.writer_worker import WriterWorker


class MockAIProvider(BaseAIProvider):
    """Mock AI Provider simulating GeminiWebProvider for testing."""

    @property
    def name(self) -> str:
        return "MockGeminiWebProvider"

    async def generate(self, prompt: str, system_instruction: str | None = None) -> str:
        return """# Mastering FastAPI Web Architecture

FastAPI is a modern, high-performance web framework for Python.

## 1. Executive Hook
FastAPI brings speed and async capabilities to modern APIs.

## 2. Core Concepts
Utilizes Pydantic for data validation and Starlette for web tooling.

## References
- [FastAPI Docs](https://github.com/fastapi/fastapi)

## Conclusion
Subscribe for updates and star the GitHub repository!
"""

    async def check_health(self) -> bool:
        return True


def test_prompt_builder_structure():
    """Tests PromptBuilder generation prompt formatting with ContentBrief."""
    builder = PromptBuilder()
    brief = ContentBrief(
        title_idea="FastAPI Guide",
        content_goal=ContentObjective.EDUCATIONAL,
        priority=ContentPriority.HIGH,
        audience="Developers",
        platform="Blog",
        content_format="Tutorial",
        tone="Authoritative & Technical",
        complexity="Intermediate",
        estimated_length="1200 words",
        hook_strategy="Start with performance metrics.",
        call_to_action="Subscribe to our newsletter.",
    )

    prompt = builder.build_prompt(brief=brief)
    assert "FastAPI Guide" in prompt
    assert "AUTHORITATIVE" in prompt
    assert "Blog" in prompt
    assert "Subscribe to our newsletter." in prompt


def test_draft_validator_scores():
    """Tests DraftValidator fine-grained sub-scores (length, citation, outline, CTA)."""
    validator = DraftValidator(min_words=20)
    brief = ContentBrief(
        title_idea="FastAPI Guide",
        audience="Developers",
        platform="Blog",
        content_format="Tutorial",
        tone="Authoritative",
        complexity="Intermediate",
        estimated_length="1000 words",
        hook_strategy="Introduction to FastAPI",
        outline=["1. Executive Hook", "2. Core Concepts"],
        supporting_citations=[{"title": "FastAPI Docs", "url": "https://github.com/fastapi/fastapi"}],
        call_to_action="Subscribe for updates.",
    )

    mock_draft = """# FastAPI Guide

## 1. Executive Hook
FastAPI is built for performance. https://github.com/fastapi/fastapi

## 2. Core Concepts
Fast Pydantic validation.

Subscribe for updates.
"""

    is_valid, scores, issues = validator.validate_draft(draft=mock_draft, brief=brief)

    assert is_valid is True
    assert isinstance(scores, DraftValidationScores)
    assert scores.length_score == 1.0
    assert scores.outline_score == 1.0
    assert scores.citation_score == 1.0
    assert scores.cta_score == 1.0
    assert scores.composite_score == 1.0
    assert len(issues) == 0


@pytest.mark.asyncio
async def test_production_writer_worker_execution():
    """Tests end-to-end task execution of production WriterWorker via WorkforceManager with MockAIProvider."""
    bus = MessageBus()
    mock_provider = MockAIProvider()
    worker = WriterWorker(
        worker_id="writer_test_01",
        ai_provider=mock_provider,
        bus=bus,
    )
    await worker.initialize()

    registry = WorkerRegistry()
    registry.register(worker)
    manager = WorkforceManager(registry=registry, bus=bus)

    brief = ContentBrief(
        title_idea="Mastering FastAPI Web Architecture",
        content_goal=ContentObjective.EDUCATIONAL,
        priority=ContentPriority.HIGH,
        audience="Developers",
        platform="Blog",
        content_format="Tutorial",
        tone="Authoritative",
        complexity="Intermediate",
        estimated_length="1000 words",
        hook_strategy="FastAPI async performance.",
        outline=["1. Executive Hook", "2. Core Concepts"],
        supporting_citations=[{"title": "FastAPI Docs", "url": "https://github.com/fastapi/fastapi"}],
        call_to_action="Subscribe for updates",
    )

    task = Task(
        type="content_writing",
        creator="orchestrator",
        priority=TaskPriority.HIGH,
        payload={"topic": "FastAPI Web Architecture", "content_brief": brief.model_dump(mode="json")},
    )

    manager.submit_task(task)
    result = await manager.dispatch_next()

    assert result is not None
    assert result.status == TaskStatus.COMPLETED
    assert result.execution_time >= 0.0
    assert "draft_package" in result.artifacts
    draft_pkg = result.artifacts["draft_package"]
    assert draft_pkg["title"] == "Mastering FastAPI Web Architecture"
    assert draft_pkg["draft_version"] == 1
    assert draft_pkg["writing_style"] == "AUTHORITATIVE"
    assert "generation_number" in draft_pkg["generation_metadata"]
    assert worker.metrics.tasks_completed == 1


@pytest.mark.asyncio
async def test_writer_worker_degraded_execution():
    """Verifies degraded execution / fallback draft generation when AI Provider throws error."""
    failing_provider = AsyncMock(spec=BaseAIProvider)
    failing_provider.generate.side_effect = RuntimeError("Provider Offline")

    worker = WriterWorker(worker_id="writer_degraded", ai_provider=failing_provider)
    await worker.initialize()

    task = Task(type="content_writing", creator="sys", payload={"topic": "Fallback Topic"})
    result = await worker.execute(task, SharedContext())

    assert result.status == TaskStatus.COMPLETED
    assert "draft_package" in result.artifacts
    draft_data = result.artifacts["draft_package"]
    assert "Fallback Topic" in draft_data["title"]


@pytest.mark.asyncio
async def test_writer_worker_lifecycle():
    """Tests WriterWorker initialization, health check, and shutdown."""
    worker = WriterWorker(worker_id="writer_lifecycle")
    assert worker.state == WorkerState.CREATED

    await worker.initialize()
    assert worker.state == WorkerState.READY
    assert await worker.health_check() is True

    await worker.shutdown()
    assert worker.state == WorkerState.STOPPED
    assert await worker.health_check() is False


def test_draft_package_serialization():
    """Verifies complete Pydantic JSON serialization and deserialization of DraftPackage."""
    pkg = DraftPackage(
        title="FastAPI Guide",
        platform="Blog",
        content_format="Tutorial",
        audience="Developers",
        objective="EDUCATIONAL",
        draft="# FastAPI Guide\n\nSample draft.",
        draft_version=1,
    )

    dumped = pkg.model_dump(mode="json")
    assert isinstance(dumped, dict)
    assert dumped["draft_version"] == 1
    assert dumped["writing_style"] == "AUTHORITATIVE"
    assert "generation_number" in dumped["generation_metadata"]

    reconstructed = DraftPackage.model_validate(dumped)
    assert reconstructed.title == pkg.title
    assert reconstructed.draft_version == 1


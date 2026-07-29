"""Unit test suite for Production Content Strategist Worker.

Tests audience classification, platform selection, strategy brief generation, ContentObjective,
ContentPriority, ContentCalendarHint, degraded execution, and worker lifecycle.
"""

import pytest

from modules.research.models import ResearchDocument, ResearchPackage
from modules.workforce.bus import MessageBus
from modules.workforce.context import SharedContext
from modules.workforce.manager import WorkforceManager
from modules.workforce.models import Task, TaskPriority, TaskStatus, WorkerState
from modules.workforce.registry import WorkerRegistry
from modules.workforce.workers.audience_analyzer import AudienceAnalyzer
from modules.workforce.workers.brief_models import (
    ContentBrief,
    ContentCalendarHint,
    ContentObjective,
    ContentPriority,
)
from modules.workforce.workers.platform_selector import PlatformSelector
from modules.workforce.workers.strategist_worker import ContentStrategistWorker
from modules.workforce.workers.strategy_engine import StrategyEngine


def test_audience_analyzer_classification():
    """Tests classification of target audience categories and complexity levels."""
    analyzer = AudienceAnalyzer()

    # Developer classification
    aud, comp, tone = analyzer.classify_audience("FastAPI async python code architecture")
    assert aud == "Developer"
    assert comp == "Intermediate"
    assert "Technical" in tone

    # Founder classification
    aud_f, comp_f, tone_f = analyzer.classify_audience("Startup ARR growth and revenue ROI")
    assert aud_f == "Founder"
    assert comp_f == "High Level"
    assert "Strategic" in tone_f


def test_platform_selector_mapping():
    """Tests platform selection, format structure, and repurposing recommendations."""
    selector = PlatformSelector()

    # Thought leadership -> LinkedIn
    plat_li, fmt_li, repurpose_li = selector.select_platform(
        goal=ContentObjective.THOUGHT_LEADERSHIP, audience="Founder"
    )
    assert plat_li == "LinkedIn"
    assert fmt_li == "Framework"
    assert "X Thread" in repurpose_li

    # Viral awareness -> X
    plat_x, fmt_x, repurpose_x = selector.select_platform(
        goal=ContentObjective.VIRAL_AWARENESS, audience="Creator"
    )
    assert plat_x == "X"
    assert fmt_x == "Thread"
    assert "Instagram Carousel" in repurpose_x


def test_strategy_engine_brief_generation():
    """Tests synthesis of strongly typed ContentBrief with calendar hints and effort estimations."""
    engine = StrategyEngine()

    doc = ResearchDocument(
        title="FastAPI Best Practices",
        url="https://github.com/fastapi/fastapi",
        source="github",
        source_type="github",
        content="FastAPI async framework features.",
    )
    package = ResearchPackage(
        query="FastAPI",
        executive_summary="FastAPI is a fast web framework.",
        key_facts=["Async native", "Fast Pydantic parsing"],
        ranked_documents=[doc],
    )

    brief: ContentBrief = engine.generate_brief(
        topic="FastAPI",
        goal=ContentObjective.EDUCATIONAL,
        priority=ContentPriority.HIGH,
        package=package,
    )

    assert isinstance(brief, ContentBrief)
    assert brief.content_goal == ContentObjective.EDUCATIONAL
    assert brief.priority == ContentPriority.HIGH
    assert brief.estimated_effort == "half-day"
    assert len(brief.repurpose_to) > 0
    assert isinstance(brief.calendar_hint, ContentCalendarHint)
    assert brief.calendar_hint.publish_priority == ContentPriority.HIGH
    assert brief.calendar_hint.recommended_day == "Tuesday"
    assert len(brief.supporting_citations) == 1
    assert brief.supporting_citations[0]["title"] == "FastAPI Best Practices"


@pytest.mark.asyncio
async def test_production_content_strategist_worker_execution():
    """Tests end-to-end task execution of production ContentStrategistWorker via WorkforceManager."""
    bus = MessageBus()
    worker = ContentStrategistWorker(
        worker_id="cs_test_01",
        bus=bus,
    )
    await worker.initialize()

    registry = WorkerRegistry()
    registry.register(worker)
    manager = WorkforceManager(registry=registry, bus=bus)

    task = Task(
        type="content_strategy",
        creator="orchestrator",
        priority=TaskPriority.HIGH,
        payload={
            "topic": "FastAPI Web Architecture",
            "content_goal": "THOUGHT_LEADERSHIP",
            "priority": "HIGH",
        },
    )

    manager.submit_task(task)
    result = await manager.dispatch_next()

    assert result is not None
    assert result.status == TaskStatus.COMPLETED
    assert result.execution_time > 0.0
    assert "content_brief" in result.artifacts
    assert result.artifacts["platform"] == "LinkedIn"
    assert worker.metrics.tasks_completed == 1


@pytest.mark.asyncio
async def test_strategist_worker_degraded_execution():
    """Verifies degraded execution / fallback ContentBrief return when task inputs are minimal."""
    worker = ContentStrategistWorker(worker_id="cs_test_degraded")
    await worker.initialize()

    task = Task(type="content_strategy", creator="sys", payload={})
    result = await worker.execute(task, SharedContext())

    assert result.status == TaskStatus.COMPLETED
    assert "content_brief" in result.artifacts
    brief_data = result.artifacts["content_brief"]
    assert "General Topic" in brief_data["title_idea"]


@pytest.mark.asyncio
async def test_strategist_worker_lifecycle():
    """Tests ContentStrategistWorker initialization, health check, and shutdown."""
    worker = ContentStrategistWorker(worker_id="cs_lifecycle")
    assert worker.state == WorkerState.CREATED

    await worker.initialize()
    assert worker.state == WorkerState.READY
    assert await worker.health_check() is True

    await worker.shutdown()
    assert worker.state == WorkerState.STOPPED
    assert await worker.health_check() is False

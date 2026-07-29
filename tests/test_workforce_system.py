"""Unit test suite for AI Workforce Core subsystem.

Tests models validation, SharedContext cloning, WorkerRegistry lookup, TaskScheduler priority ordering,
MessageBus inbox routing, WorkforceManager task dispatching, retry exhaustion, and worker lifecycle events.
"""

from datetime import UTC, datetime, timedelta

import pytest

from modules.workforce.bus import MessageBus
from modules.workforce.context import SharedContext
from modules.workforce.manager import WorkforceManager
from modules.workforce.models import (
    RetryStrategy,
    Task,
    TaskMessage,
    TaskPriority,
    TaskResult,
    TaskStatus,
    WorkerState,
)
from modules.workforce.registry import WorkerRegistry
from modules.workforce.scheduler import TaskScheduler
from modules.workforce.workers import (
    ResearchWorker,
    ScriptWorker,
)


def test_task_model_validation():
    """Verifies task model field defaults and validation rules."""
    task = Task(
        type="research",
        creator="orchestrator",
        priority=TaskPriority.HIGH,
        payload={"topic": "AI Trends"}
    )
    assert task.type == "research"
    assert task.priority == TaskPriority.HIGH
    assert task.status == TaskStatus.PENDING
    assert task.retry_strategy == RetryStrategy.EXPONENTIAL_BACKOFF
    assert task.retry_count == 0
    assert task.max_retries == 3

def test_shared_context_cloning():
    """Verifies SharedContext cloning functionality."""
    context = SharedContext(runtime_metadata={"session_id": "123"})
    cloned = context.clone()
    assert cloned.runtime_metadata == context.runtime_metadata

    # Verify mutation isolation
    cloned.runtime_metadata["session_id"] = "456"
    assert context.runtime_metadata["session_id"] == "123"

@pytest.mark.asyncio
async def test_worker_registry_lifecycle():
    """Tests worker registration, capability searching, enabling, disabling, and health checks."""
    registry = WorkerRegistry()
    w1 = ResearchWorker(worker_id="worker_research_01")
    w2 = ScriptWorker(worker_id="worker_script_01")

    registry.register(w1)
    registry.register(w2)

    assert len(registry.discover()) == 2
    assert "worker_research_01" in registry.discover()

    # Search capability
    matches = registry.find_by_capability("research")
    assert len(matches) == 1
    assert matches[0].worker_id == "worker_research_01"
    assert matches[0].role == "Research Specialist"

    # Disable & Enable
    registry.disable("worker_research_01")
    assert len(registry.find_by_capability("research")) == 0

    registry.enable("worker_research_01")
    assert len(registry.find_by_capability("research")) == 1

    # Health Checks
    await w1.initialize()
    await w2.initialize()
    health_status = await registry.run_health_checks()
    assert health_status["worker_research_01"] is True
    assert health_status["worker_script_01"] is True

def test_duplicate_worker_registration():
    """Verifies that registering a duplicate worker ID cleanly overwrites the previous registration."""
    registry = WorkerRegistry()
    w1 = ResearchWorker(worker_id="same_id")
    w2 = ScriptWorker(worker_id="same_id")

    registry.register(w1)
    assert registry.get_worker("same_id").role == "Research Specialist"

    registry.register(w2)
    assert registry.get_worker("same_id").role == "Script Writer Specialist"
    assert len(registry.discover()) == 1

def test_get_nonexistent_worker():
    """Verifies safe None return when looking up an unregistered worker ID."""
    registry = WorkerRegistry()
    assert registry.get_worker("missing_worker") is None
    assert registry.is_enabled("missing_worker") is False
    assert registry.unregister("missing_worker") is None

def test_task_scheduler_priority_and_deadline_ordering():
    """Tests task scheduler priority ordering and deadline sorting."""
    scheduler = TaskScheduler()

    now = datetime.now(UTC)
    t_low = Task(type="research", creator="sys", priority=TaskPriority.LOW)
    t_high_late = Task(type="research", creator="sys", priority=TaskPriority.HIGH, deadline=now + timedelta(hours=2))
    t_high_urgent = Task(type="research", creator="sys", priority=TaskPriority.HIGH, deadline=now + timedelta(minutes=30))
    t_urgent = Task(type="research", creator="sys", priority=TaskPriority.URGENT)

    scheduler.enqueue(t_low)
    scheduler.enqueue(t_high_late)
    scheduler.enqueue(t_high_urgent)
    scheduler.enqueue(t_urgent)

    assert scheduler.get_queue_length() == 4

    # 1st pop: URGENT priority
    p1 = scheduler.pop_next()
    assert p1.id == t_urgent.id

    # 2nd pop: HIGH priority with earlier deadline
    p2 = scheduler.pop_next()
    assert p2.id == t_high_urgent.id

    # 3rd pop: HIGH priority with later deadline
    p3 = scheduler.pop_next()
    assert p3.id == t_high_late.id

    # 4th pop: LOW priority
    p4 = scheduler.pop_next()
    assert p4.id == t_low.id

def test_empty_scheduler_dispatch():
    """Verifies safe None pop on an empty scheduler queue."""
    scheduler = TaskScheduler()
    assert scheduler.peek_next() is None
    assert scheduler.pop_next() is None
    assert scheduler.get_queue_length() == 0

def test_retry_exhaustion_behaviour():
    """Verifies that schedule_retry returns False and marks task FAILED when max_retries is reached."""
    scheduler = TaskScheduler()
    task = Task(type="research", creator="sys", max_retries=2)

    assert scheduler.schedule_retry(task) is True
    assert task.retry_count == 1
    assert task.status == TaskStatus.PENDING

    assert scheduler.schedule_retry(task) is True
    assert task.retry_count == 2
    assert task.status == TaskStatus.PENDING

    assert scheduler.schedule_retry(task) is False
    assert task.status == TaskStatus.FAILED

@pytest.mark.asyncio
async def test_message_bus_routing_and_events():
    """Tests MessageBus inbox queue routing, event listeners, unsubscribe, and removal."""
    bus = MessageBus()
    inbox = bus.subscribe("worker_research_01")

    msg = TaskMessage(
        sender="WorkforceManager",
        recipient="worker_research_01",
        task_id="task-123",
        payload={"topic": "Test"}
    )
    assert await bus.publish_message(msg) is True
    assert inbox.qsize() == 1

    received = await inbox.get()
    assert received.task_id == "task-123"

    # Test missing recipient
    msg_missing = TaskMessage(
        sender="WorkforceManager",
        recipient="missing_worker",
        task_id="task-456"
    )
    assert await bus.publish_message(msg_missing) is False

    # Event listening & removal
    received_events = []
    def on_event(event):
        received_events.append(event)

    bus.add_event_listener("TaskCreated", on_event)
    await bus.emit_event("TaskCreated", "WorkforceManager", {"task_id": "task-123"})
    assert len(received_events) == 1

    assert bus.remove_event_listener("TaskCreated", on_event) is True
    await bus.emit_event("TaskCreated", "WorkforceManager", {"task_id": "task-789"})
    assert len(received_events) == 1

    # Test unsubscribe
    assert bus.unsubscribe("worker_research_01") is True
    assert bus.unsubscribe("worker_research_01") is False

@pytest.mark.asyncio
async def test_workforce_manager_task_dispatch():
    """Tests end-to-end task submission, capability worker assignment, and execution metrics."""
    registry = WorkerRegistry()
    r_worker = ResearchWorker()
    await r_worker.initialize()
    registry.register(r_worker)

    manager = WorkforceManager(registry=registry)
    task = Task(type="research", creator="orchestrator", payload={"topic": "Local AI Workforce"})

    task_id = manager.submit_task(task)
    assert task_id == task.id

    # Dispatch task
    result = await manager.dispatch_next()
    assert result is not None
    assert result.status == TaskStatus.COMPLETED
    assert result.artifacts.get("package") is not None or result.artifacts.get("research_summary") is not None
    assert r_worker.metrics.tasks_completed == 1
    assert r_worker.metrics.success_rate == 1.0

@pytest.mark.asyncio
async def test_no_capable_worker_found():
    """Verifies WorkforceManager behaviour when no capable worker is registered."""
    registry = WorkerRegistry()
    manager = WorkforceManager(registry=registry)

    task = Task(type="unsupported_capability", creator="orchestrator", max_retries=1)
    manager.submit_task(task)

    result = await manager.dispatch_next()
    assert result is None
    assert manager.scheduler.get_queue_length() == 1  # Re-queued for retry

@pytest.mark.asyncio
async def test_failed_worker_execution_handling():
    """Verifies handling of worker exceptions during task execution."""
    registry = WorkerRegistry()

    class FailingWorker(ResearchWorker):
        async def execute(self, task: Task, context: SharedContext) -> TaskResult:
            raise RuntimeError("Simulated Worker Failure")

    failing_worker = FailingWorker(worker_id="worker_failing")
    await failing_worker.initialize()
    registry.register(failing_worker)

    manager = WorkforceManager(registry=registry)
    task = Task(type="research", creator="orchestrator", max_retries=1)
    manager.submit_task(task)

    result = await manager.dispatch_next()
    assert result is not None
    assert result.status == TaskStatus.FAILED
    assert result.error == "Simulated Worker Failure"
    assert failing_worker.metrics.tasks_failed == 1

@pytest.mark.asyncio
async def test_workforce_manager_shutdown_all():
    """Tests WorkforceManager graceful shutdown across all registered workers."""
    registry = WorkerRegistry()
    w1 = ResearchWorker()
    w2 = ScriptWorker()
    await w1.initialize()
    await w2.initialize()

    registry.register(w1)
    registry.register(w2)

    manager = WorkforceManager(registry=registry)
    stopped = await manager.shutdown_all()

    assert len(stopped) == 2
    assert w1.state == WorkerState.STOPPED
    assert w2.state == WorkerState.STOPPED

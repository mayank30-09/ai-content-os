"""Task scheduler module for AI Workforce Core subsystem.

Manages task queueing, priority sorting, deadline ordering, and retry scheduling
without direct worker communication.
"""

from loguru import logger

from modules.workforce.models import Task, TaskStatus


class TaskScheduler:
    """Manages task priority queues, deadline ordering, and retry scheduling."""

    def __init__(self):
        self._queue: list[Task] = []

    def enqueue(self, task: Task) -> None:
        """Enqueues a Task into the queue and re-sorts by priority and deadline.

        Args:
            task: Task instance to enqueue.
        """
        task.status = TaskStatus.PENDING
        self._queue.append(task)
        self._sort_queue()
        logger.info(f"Enqueued task '{task.id}' [Type: {task.type}, Priority: {task.priority.name}]")

    def _sort_queue(self) -> None:
        """Sorts tasks in queue descending by priority, then ascending by deadline/creation time."""
        def task_sort_key(t: Task):
            # Sort by Priority descending (-t.priority.value)
            # Then by deadline timestamp ascending (or infinity if no deadline)
            deadline_ts = t.deadline.timestamp() if t.deadline else float("inf")
            created_ts = t.created_at.timestamp()
            return (-t.priority.value, deadline_ts, created_ts)

        self._queue.sort(key=task_sort_key)

    def peek_next(self) -> Task | None:
        """Peeks at the next top-priority Task in queue without removing it.

        Returns:
            Optional[Task]: Highest priority Task if available, None otherwise.
        """
        return self._queue[0] if self._queue else None

    def pop_next(self) -> Task | None:
        """Pops and returns the next highest priority Task from queue.

        Returns:
            Optional[Task]: Next Task if queue non-empty, None otherwise.
        """
        if not self._queue:
            return None
        task = self._queue.pop(0)
        logger.debug(f"Popped task '{task.id}' from scheduler queue.")
        return task

    def schedule_retry(self, task: Task) -> bool:
        """Schedules a retry for a failed task if max_retries has not been exceeded.

        Args:
            task: Failed Task object.

        Returns:
            bool: True if task was re-queued for retry, False if max_retries exceeded.
        """
        if task.retry_count >= task.max_retries:
            logger.warning(f"Task '{task.id}' exceeded max_retries ({task.max_retries}). Marking FAILED.")
            task.status = TaskStatus.FAILED
            return False

        task.retry_count += 1
        task.status = TaskStatus.PENDING
        logger.info(f"Scheduling retry {task.retry_count}/{task.max_retries} for task '{task.id}'")
        self.enqueue(task)
        return True

    def get_queue_length(self) -> int:
        """Returns total count of pending tasks in queue."""
        return len(self._queue)

    def clear(self) -> None:
        """Clears all tasks from queue."""
        self._queue.clear()

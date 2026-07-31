"""Structured AuditLogger module for security and operational compliance logging.

Provides thread-safe, append-only audit event recording and lookup.
"""

import threading
from collections import deque

from loguru import logger

from modules.observability.models import AuditEvent


class AuditLogger:
    """Thread-safe append-only logger for system audit events."""

    def __init__(self, max_audit_events: int = 5000) -> None:
        """Initializes AuditLogger with buffer size limit.

        Args:
            max_audit_events: Maximum audit log events to keep in memory buffer.
        """
        self._audit_events: deque[AuditEvent] = deque(maxlen=max_audit_events)
        self._lock: threading.Lock = threading.Lock()

    def record_audit_event(
        self,
        action: str,
        actor: str = "system",
        target: str = "system",
        status: str = "SUCCESS",
        metadata: dict | None = None,
    ) -> AuditEvent:
        """Records a new structured AuditEvent.

        Args:
            action: Audited action identifier string.
            actor: Entity performing action (default 'system').
            target: Resource target (default 'system').
            status: Outcome status ('SUCCESS', 'FAILURE').
            metadata: Optional additional key-value payload dictionary.

        Returns:
            Recorded AuditEvent model instance.
        """
        event = AuditEvent(
            action=action,
            actor=actor,
            target=target,
            status=status,
            metadata=metadata or {},
        )

        with self._lock:
            self._audit_events.append(event)

        logger.info(f"AuditLogger: recorded audit event '{action}' [actor={actor}, target={target}, status={status}]")
        return event

    def get_audit_events(self) -> list[AuditEvent]:
        """Returns a snapshot list of recorded audit events.

        Returns:
            List of AuditEvent objects.
        """
        with self._lock:
            return list(self._audit_events)

    def clear(self) -> None:
        """Clears stored audit events."""
        with self._lock:
            self._audit_events.clear()

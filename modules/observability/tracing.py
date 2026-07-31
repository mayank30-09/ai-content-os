"""Distributed Tracer engine and span management for AI Content OS.

Provides thread-safe span creation, parent-child trace hierarchy propagation,
and bounded span storage.
"""

import threading
from collections import deque
from typing import Any

from loguru import logger

from modules.observability.models import Span, TraceContext


class Tracer:
    """Distributed tracer engine for managing trace contexts and finished span recordings."""

    def __init__(self, max_finished_spans: int = 10000) -> None:
        """Initializes Tracer with bounded span buffer size.

        Args:
            max_finished_spans: Max capacity for in-memory finished spans buffer.
        """
        self.max_finished_spans: int = max_finished_spans
        self._finished_spans: deque[Span] = deque(maxlen=max_finished_spans)
        self._active_spans: dict[str, Span] = {}
        self._lock: threading.Lock = threading.Lock()

    def start_span(
        self,
        name: str,
        context: TraceContext | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> Span:
        """Starts a new tracing span with given or parent context.

        Args:
            name: Span operation name.
            context: TraceContext header. If None, default context is created.
            attributes: Optional key-value attributes dictionary.

        Returns:
            Newly created Span instance.
        """
        ctx = context or TraceContext()
        span = Span(
            span_id=ctx.span_id,
            name=name,
            context=ctx,
            attributes=attributes or {},
        )

        with self._lock:
            self._active_spans[span.span_id] = span

        logger.debug(f"Tracer: started span '{name}' [span_id={span.span_id}, corr_id={ctx.correlation_id}]")
        return span

    def finish_span(self, span: Span, status: str = "OK") -> None:
        """Finishes a span, computes latency, and records it to buffer.

        Args:
            span: Span instance to finish.
            status: Final span status string ('OK', 'ERROR').
        """
        span.finish(status=status)
        with self._lock:
            self._active_spans.pop(span.span_id, None)
            self._finished_spans.append(span)

        logger.debug(f"Tracer: finished span '{span.name}' in {span.duration_ms:.2f}ms [{status}]")

    def get_finished_spans(self) -> list[Span]:
        """Returns a snapshot list of recorded finished spans.

        Returns:
            List of Span objects.
        """
        with self._lock:
            return list(self._finished_spans)

    def clear(self) -> None:
        """Clears all stored finished and active spans."""
        with self._lock:
            self._finished_spans.clear()
            self._active_spans.clear()

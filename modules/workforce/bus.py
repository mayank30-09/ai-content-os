"""Message bus module for AI Workforce Core subsystem.

Provides decoupled asynchronous messaging via TaskMessage inboxes and workforce
event broadcasting.
"""

import asyncio
import inspect
from collections.abc import Callable
from typing import Any

from loguru import logger

from modules.workforce.models import TaskMessage, WorkforceEvent


class MessageBus:
    """Decoupled message bus routing TaskMessages and emitting workforce events."""

    def __init__(self):
        self._inboxes: dict[str, asyncio.Queue] = {}
        self._event_listeners: dict[str, list[Callable]] = {}

    def subscribe(self, recipient_id: str) -> asyncio.Queue:
        """Subscribes a worker recipient ID to receive inbox TaskMessages.

        Args:
            recipient_id: Worker ID.

        Returns:
            asyncio.Queue: Worker inbox queue.
        """
        if recipient_id not in self._inboxes:
            self._inboxes[recipient_id] = asyncio.Queue()
            logger.debug(f"Subscribed recipient inbox: '{recipient_id}'")
        return self._inboxes[recipient_id]

    async def publish_message(self, message: TaskMessage) -> bool:
        """Publishes a TaskMessage to the recipient's inbox queue.

        Args:
            message: TaskMessage instance.

        Returns:
            bool: True if message was delivered to an active inbox, False otherwise.
        """
        recipient = message.recipient
        logger.info(f"Publishing message '{message.message_id}' from '{message.sender}' to '{recipient}'")

        if recipient == "BROADCAST":
            for inbox in self._inboxes.values():
                await inbox.put(message)
            return True

        if recipient in self._inboxes:
            await self._inboxes[recipient].put(message)
            return True

        logger.warning(f"No active inbox found for recipient: '{recipient}'")
        return False

    def unsubscribe(self, recipient_id: str) -> bool:
        """Unsubscribes and removes a recipient inbox queue.

        Args:
            recipient_id: Worker ID.

        Returns:
            bool: True if inbox existed and was removed, False otherwise.
        """
        if recipient_id in self._inboxes:
            del self._inboxes[recipient_id]
            logger.debug(f"Unsubscribed recipient inbox: '{recipient_id}'")
            return True
        return False

    def add_event_listener(self, event_type: str, callback: Callable) -> None:
        """Registers an asynchronous event listener callback for a workforce event type."""
        if event_type not in self._event_listeners:
            self._event_listeners[event_type] = []
        self._event_listeners[event_type].append(callback)
        logger.debug(f"Added event listener for '{event_type}'")

    def remove_event_listener(self, event_type: str, callback: Callable) -> bool:
        """Removes an event listener callback for a workforce event type."""
        listeners = self._event_listeners.get(event_type, [])
        if callback in listeners:
            listeners.remove(callback)
            logger.debug(f"Removed event listener for '{event_type}'")
            return True
        return False

    async def emit_event(self, event_type: str, source: str, data: dict[str, Any]) -> None:
        """Emits a WorkforceEvent to registered event listeners.

        Args:
            event_type: Event classification string.
            source: Event source origin.
            data: Event payload data details.
        """
        event = WorkforceEvent(event_type=event_type, source=source, data=data)
        logger.info(f"Emitting WorkforceEvent '{event.event_type}' from '{source}'")

        listeners = self._event_listeners.get(event_type, [])
        for callback in listeners:
            try:
                if inspect.iscoroutinefunction(callback):
                    await callback(event)
                else:
                    callback(event)
            except Exception as e:
                logger.error(f"Event listener exception for '{event_type}': {e}")

message_bus = MessageBus()

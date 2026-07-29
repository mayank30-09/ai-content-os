from abc import ABC, abstractmethod
from typing import Any


class BasePublisher(ABC):
    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Social platform identifier."""
        pass

    @abstractmethod
    async def publish(self, content_item: dict[str, Any]) -> bool:
        """Publishes approved content item to target platform using web automation."""
        pass

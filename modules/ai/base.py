from abc import ABC, abstractmethod


class BaseAIProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier name."""
        pass

    @abstractmethod
    async def generate(self, prompt: str, system_instruction: str | None = None) -> str:
        """Sends prompt to AI provider and returns raw text response."""
        pass

    @abstractmethod
    async def check_health(self) -> bool:
        """Verifies if the AI provider session is active and healthy."""
        pass

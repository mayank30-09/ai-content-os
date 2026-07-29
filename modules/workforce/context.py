"""Shared context module for AI Workforce Core subsystem.

Encapsulates shared execution state including Memory Context, Research Context,
Application Configuration, and Runtime Metadata for workforce workers.
"""

from typing import Any

from pydantic import BaseModel, Field

from config.settings import settings
from modules.memory.models import ContextPackage
from modules.research.models import ResearchPackage


class SharedContext(BaseModel):
    """Shared execution context payload passed to AI workforce workers."""
    memory_context: ContextPackage | None = Field(default=None, description="Memory ContextPackage")
    research_context: ResearchPackage | None = Field(default=None, description="ResearchPackage findings")
    config: dict[str, Any] = Field(
        default_factory=lambda: settings.model_dump(mode="json"),
        description="Application configuration parameters"
    )
    runtime_metadata: dict[str, Any] = Field(
        default_factory=dict, description="Arbitrary runtime execution metadata"
    )

    def clone(self) -> "SharedContext":
        """Creates a safe deep copy of SharedContext to prevent state mutation across workers."""
        return self.model_copy(deep=True)

"""Memory worker metrics module for AI Workforce Core subsystem.

Defines Pydantic metrics model for knowledge management telemetry.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class MemoryWorkerMetrics(BaseModel):
    """Telemetry metrics model for Memory Worker operations."""

    memories_created: int = Field(default=0, ge=0, description="Count of newly stored memory records")
    memories_updated: int = Field(default=0, ge=0, description="Count of updated memory records")
    memories_promoted: int = Field(default=0, ge=0, description="Count of promoted KnowledgeMemories")
    memories_archived: int = Field(default=0, ge=0, description="Count of archived memory records")
    memories_expired: int = Field(default=0, ge=0, description="Count of expired/pruned memory records")
    duplicates_removed: int = Field(default=0, ge=0, description="Count of deduplicated memory records")
    context_items_selected: int = Field(default=0, ge=0, description="Items included in ContextPackage")
    average_memory_quality: float = Field(default=0.0, ge=0.0, le=1.0, description="Mean quality score")
    last_analysis: datetime | None = Field(default=None, description="Timestamp of last analysis run")

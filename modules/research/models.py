"""Data models module for Research Engine.

Provides strongly typed Pydantic data contracts for plugin metadata, research documents,
and final research package outputs.
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class PluginMetadata(BaseModel):
    """Metadata specifications for a research plugin."""
    plugin_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique plugin instance ID")
    name: str = Field(..., description="Unique plugin name")
    version: str = Field(default="1.0.0", description="Plugin version string")
    source_type: str = Field(..., description="Source category e.g. web, github, reddit, youtube, docs")
    reliability_score: float = Field(default=0.8, ge=0.0, le=1.0, description="Source reliability score (0.0 - 1.0)")
    enabled: bool = Field(default=True, description="Flag indicating if plugin is active")

class ResearchDocument(BaseModel):
    """Standardized document extracted by a research plugin."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique document ID")
    source: str = Field(..., description="Plugin name that extracted the document")
    source_type: str = Field(..., description="Source category identifier")
    title: str = Field(..., description="Document title")
    url: str | None = Field(default=None, description="Source URL")
    author: str | None = Field(default=None, description="Author or creator name")
    published_at: datetime | None = Field(default=None, description="Publication timestamp")
    content: str = Field(..., description="Extracted cleaned body content")
    summary: str | None = Field(default=None, description="Short content summary")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Extraction confidence score")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Arbitrary source metadata")

class ResearchPackage(BaseModel):
    """Final aggregated, deduplicated, and ranked research output package."""
    query: str = Field(..., description="Original research topic or query string")
    executive_summary: str = Field(..., description="High-level executive summary of findings")
    key_facts: list[str] = Field(default_factory=list, description="Extracted key bullet points")
    references: list[dict[str, str]] = Field(default_factory=list, description="Source attribution list")
    ranked_documents: list[ResearchDocument] = Field(default_factory=list, description="Ranked unique documents")
    execution_metrics: dict[str, Any] = Field(default_factory=dict, description="Execution timing and stats")
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Generation timestamp")

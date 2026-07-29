"""Data models module for Intelligent Memory System.

Defines Pydantic models for memory records across namespaces (Research, Style, Prompt,
Generation, Knowledge) and context packages.
"""

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class MemoryNamespace(StrEnum):
    """Enumeration of memory namespaces."""
    RESEARCH = "research"
    STYLE = "style"
    PROMPT = "prompt"
    GENERATION = "generation"
    KNOWLEDGE = "knowledge"

class MemoryRecord(BaseModel):
    """Base Pydantic model for persistent memory records."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique memory ID")
    namespace: MemoryNamespace = Field(..., description="Memory domain namespace")
    content: str = Field(..., description="Primary indexable text body")
    tags: list[str] = Field(default_factory=list, description="Keywords or topic tags")
    importance_score: float = Field(default=0.5, ge=0.0, le=1.0, description="Base importance score")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Data extraction confidence")
    reuse_count: int = Field(default=0, ge=0, description="Number of times memory was retrieved")
    user_feedback: float = Field(default=0.0, ge=-1.0, le=1.0, description="User rating score (-1.0 to 1.0)")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Creation timestamp")
    last_accessed_at: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Last access timestamp")
    expires_at: datetime | None = Field(default=None, description="Expiration timestamp for automatic TTL pruning")
    is_archived: bool = Field(default=False, description="Archival state flag")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Arbitrary domain metadata payload")

class ResearchMemory(MemoryRecord):
    """Research topic findings memory."""
    namespace: MemoryNamespace = MemoryNamespace.RESEARCH
    query: str = Field(..., description="Original research topic query")
    key_facts: list[str] = Field(default_factory=list)
    source_urls: list[str] = Field(default_factory=list)

class StyleMemory(MemoryRecord):
    """Brand writing style and tone rules memory."""
    namespace: MemoryNamespace = MemoryNamespace.STYLE
    persona_name: str = Field(...)
    tone: str = Field(...)
    forbidden_words: list[str] = Field(default_factory=list)
    preferred_phrases: list[str] = Field(default_factory=list)

class PromptMemory(MemoryRecord):
    """AI prompt performance template memory."""
    namespace: MemoryNamespace = MemoryNamespace.PROMPT
    prompt_template: str = Field(...)
    target_format: str = Field(...)
    performance_rating: float = Field(default=0.5, ge=0.0, le=1.0)

class GenerationMemory(MemoryRecord):
    """History of generated content deliverables."""
    namespace: MemoryNamespace = MemoryNamespace.GENERATION
    topic: str = Field(...)
    raw_output: str = Field(...)
    final_approved_output: str | None = Field(default=None)
    was_approved: bool = Field(default=False)

class KnowledgeMemory(MemoryRecord):
    """Reusable entity claims and domain knowledge memory."""
    namespace: MemoryNamespace = MemoryNamespace.KNOWLEDGE
    entity_name: str = Field(...)
    category: str = Field(...)
    claims: list[str] = Field(default_factory=list)

class ContextPackage(BaseModel):
    """Aggregated context package prepared for AI provider execution."""
    topic: str = Field(..., description="Target content generation topic")
    research_memories: list[ResearchMemory] = Field(default_factory=list)
    knowledge_memories: list[KnowledgeMemory] = Field(default_factory=list)
    style_memories: list[StyleMemory] = Field(default_factory=list)
    prompt_memories: list[PromptMemory] = Field(default_factory=list)
    generation_memories: list[GenerationMemory] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

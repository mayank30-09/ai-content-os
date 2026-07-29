"""Writer worker metrics module for AI Workforce Core subsystem.

Defines Pydantic metrics model for draft generation telemetry.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class WriterWorkerMetrics(BaseModel):
    """Telemetry metrics model for Writer Worker operations."""

    generation_time: float = Field(default=0.0, ge=0.0, description="Duration in seconds of content generation")
    prompt_size: int = Field(default=0, ge=0, description="Character count of input prompt")
    output_size: int = Field(default=0, ge=0, description="Word/character count of generated draft")
    citations_used: int = Field(default=0, ge=0, description="Number of citations preserved in draft")
    validation_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Composite validation score")
    retries: int = Field(default=0, ge=0, description="Count of retry generation attempts")
    drafts_generated: int = Field(default=0, ge=0, description="Total count of drafts generated")
    last_generation_at: datetime | None = Field(default=None, description="Timestamp of last draft generation")

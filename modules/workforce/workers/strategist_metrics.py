"""Strategist worker metrics module for AI Workforce Core subsystem.

Defines Pydantic metrics model for content strategy telemetry.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class ContentStrategistMetrics(BaseModel):
    """Telemetry metrics model for Content Strategist Worker operations."""

    audience_confidence: float = Field(default=0.85, ge=0.0, le=1.0, description="Audience classification confidence")
    platform_confidence: float = Field(default=0.85, ge=0.0, le=1.0, description="Platform match confidence")
    format_confidence: float = Field(default=0.85, ge=0.0, le=1.0, description="Format choice confidence")
    strategy_score: float = Field(default=0.85, ge=0.0, le=1.0, description="Overall strategy viability score")
    research_coverage: float = Field(default=0.0, ge=0.0, le=1.0, description="Ratio of research docs utilized")
    citation_coverage: float = Field(default=0.0, ge=0.0, le=1.0, description="Ratio of key points with citations")
    briefs_generated: int = Field(default=0, ge=0, description="Count of briefs generated")
    last_strategy_at: datetime | None = Field(default=None, description="Timestamp of last strategy execution")

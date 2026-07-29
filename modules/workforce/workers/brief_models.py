"""ContentBrief and supporting data models for Content Strategist subsystem."""

from enum import StrEnum

from pydantic import BaseModel, Field


class ContentObjective(StrEnum):
    """Supported business & content strategic goals."""
    EDUCATIONAL = "EDUCATIONAL"
    THOUGHT_LEADERSHIP = "THOUGHT_LEADERSHIP"
    PRODUCT_PROMOTION = "PRODUCT_PROMOTION"
    COMMUNITY_BUILDING = "COMMUNITY_BUILDING"
    SEO_LEAD_GEN = "SEO_LEAD_GEN"
    VIRAL_AWARENESS = "VIRAL_AWARENESS"

class ContentPriority(StrEnum):
    """Execution priority levels for content production."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"

class ContentCalendarHint(BaseModel):
    """Scheduling & evergreen prioritization telemetry for content calendar."""

    publish_priority: ContentPriority = Field(default=ContentPriority.MEDIUM)
    recommended_day: str = Field(default="Tuesday", description="Recommended day of week for publication")
    recommended_time_window: str = Field(default="09:00 - 11:00 EST", description="Optimal engagement time window")
    evergreen_score: float = Field(default=0.75, ge=0.0, le=1.0, description="Long-term value score")
    trend_score: float = Field(default=0.50, ge=0.0, le=1.0, description="Timeliness / trend score")

class ContentBrief(BaseModel):
    """Strongly-typed strategy brief for downstream creative workers."""

    title_idea: str = Field(description="Catchy working title or headline")
    content_goal: ContentObjective = Field(default=ContentObjective.EDUCATIONAL, description="Primary content objective")
    priority: ContentPriority = Field(default=ContentPriority.MEDIUM, description="Production priority level")
    estimated_effort: str = Field(default="1-2 hours", description="Estimated effort e.g. 1-2 hours, half-day")
    audience: str = Field(description="Target audience category")
    platform: str = Field(description="Target publishing platform")
    content_format: str = Field(description="Target format structure")
    tone: str = Field(description="Tone of voice specification")
    complexity: str = Field(description="Technical or conceptual depth level")
    estimated_length: str = Field(description="Word count or slide/thread length recommendation")
    hook_strategy: str = Field(description="Opening hook approach")
    outline: list[str] = Field(default_factory=list, description="Section-by-section outline")
    key_points: list[str] = Field(default_factory=list, description="Core takeaways to convey")
    supporting_citations: list[dict] = Field(default_factory=list, description="Validated source citations")
    seo_keywords: list[str] = Field(default_factory=list, description="Target search keywords")
    call_to_action: str = Field(description="Clear concluding call to action")
    repurpose_to: list[str] = Field(default_factory=list, description="Platforms/formats recommended for repurposing")
    calendar_hint: ContentCalendarHint = Field(default_factory=ContentCalendarHint, description="Publishing schedule hints")
    risks: list[str] = Field(default_factory=list, description="Potential content risks or sensitivity notes")
    confidence: float = Field(default=0.85, ge=0.0, le=1.0, description="Strategy confidence score")

"""Citation and quality models for Research Worker subsystem.

Defines Pydantic schemas for source citations and source quality scoring metrics.
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class SourceCitation(BaseModel):
    """Strongly typed citation record for verified information sources."""

    citation_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique citation ID",
    )
    title: str = Field(..., description="Document or page title")
    url: str = Field(..., description="Source URL")
    source_type: str = Field(
        ..., description="Source category e.g. web, github, reddit, youtube, documentation"
    )
    domain: str = Field(..., description="Base domain name e.g. github.com")
    retrieved_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Retrieval timestamp",
    )
    authority_score: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Source domain authority score"
    )
    freshness_score: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Recency freshness score"
    )
    relevance_score: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Topic relevance score"
    )
    confidence: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Extraction confidence score"
    )
    citation_metadata: dict[str, Any] = Field(
        default_factory=dict, description="Arbitrary citation metadata"
    )

class SourceQualityModel(BaseModel):
    """Quality scoring configuration model for weighting research sources."""

    authority_weight: float = Field(default=0.30, ge=0.0, le=1.0)
    freshness_weight: float = Field(default=0.20, ge=0.0, le=1.0)
    relevance_weight: float = Field(default=0.25, ge=0.0, le=1.0)
    confidence_weight: float = Field(default=0.15, ge=0.0, le=1.0)
    diversity_weight: float = Field(default=0.10, ge=0.0, le=1.0)
    minimum_quality_threshold: float = Field(default=0.40, ge=0.0, le=1.0)
    high_authority_threshold: float = Field(default=0.80, ge=0.0, le=1.0)

    def calculate_quality_score(
        self, citation: SourceCitation, diversity_score: float = 1.0
    ) -> float:
        """Calculates composite quality score for a SourceCitation.

        Args:
            citation: SourceCitation instance.
            diversity_score: Source domain diversity factor (0.0 to 1.0).

        Returns:
            float: Composite quality score between 0.0 and 1.0.
        """
        score = (
            (self.authority_weight * citation.authority_score)
            + (self.freshness_weight * citation.freshness_score)
            + (self.relevance_weight * citation.relevance_score)
            + (self.confidence_weight * citation.confidence)
            + (self.diversity_weight * diversity_score)
        )
        return round(min(1.0, max(0.0, score)), 3)

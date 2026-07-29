"""Fact Checker Worker telemetry metrics model.

Tracks performance indicators for the FactCheckerWorker pipeline execution.
"""

from pydantic import BaseModel, Field


class FactCheckerMetrics(BaseModel):
    """Telemetry metrics for the FactCheckerWorker execution pipeline.

    Attributes:
        claims_found: Total factual claims extracted from draft.
        claims_verified: Count of claims verified against sources.
        citations_checked: Total citation URLs evaluated.
        duplicate_citation_count: Count of duplicate citations detected.
        unsupported_claims: Count of claims with no supporting evidence.
        hallucination_count: Count of suspected hallucinated statements.
        verification_time: Total pipeline duration in seconds.
        overall_confidence: Composite verification confidence score.
        average_claim_confidence: Mean confidence across individual claims.
    """

    claims_found: int = Field(default=0, ge=0, description="Total claims extracted from draft")
    claims_verified: int = Field(default=0, ge=0, description="Claims verified against research/memory sources")
    citations_checked: int = Field(default=0, ge=0, description="Citation URLs evaluated")
    duplicate_citation_count: int = Field(default=0, ge=0, description="Duplicate citations detected")
    unsupported_claims: int = Field(default=0, ge=0, description="Claims lacking supporting evidence")
    hallucination_count: int = Field(default=0, ge=0, description="Suspected hallucinated statements")
    verification_time: float = Field(default=0.0, ge=0.0, description="Pipeline duration in seconds")
    overall_confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Composite confidence score")
    average_claim_confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Mean per-claim confidence score")

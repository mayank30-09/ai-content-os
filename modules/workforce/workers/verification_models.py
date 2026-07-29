"""Verification models for Fact Checker Worker subsystem.

Defines strongly-typed schemas for claim results, verification reports,
and verified draft packages.
"""

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from modules.workforce.workers.draft_models import DraftPackage


class VerificationStatus(StrEnum):
    """Supported verification outcome statuses."""

    VERIFIED = "VERIFIED"
    PARTIALLY_VERIFIED = "PARTIALLY_VERIFIED"
    UNVERIFIED = "UNVERIFIED"
    CONTRADICTED = "CONTRADICTED"
    HALLUCINATION_SUSPECTED = "HALLUCINATION_SUSPECTED"


class IssueSeverity(StrEnum):
    """Severity levels for verification issues."""

    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ClaimResult(BaseModel):
    """Result of auditing an individual factual claim extracted from a draft.

    Attributes:
        claim_text: The raw extracted claim text.
        category: Claim type (statistic, date, quote, url, general_fact).
        status: Verification outcome for this claim.
        source_reference: Matching source document title or memory ID, if found.
        matched_text: Supporting text from source that matched this claim.
        verification_method: Name of the matching strategy used.
        issue_severity: Severity rating of any detected issue.
        confidence: Per-claim verification confidence score.
    """

    claim_text: str = Field(description="Extracted factual claim text")
    category: str = Field(default="general_fact", description="Claim type: statistic, date, quote, url, general_fact")
    status: VerificationStatus = Field(default=VerificationStatus.UNVERIFIED)
    source_reference: str | None = Field(default=None, description="Matching source doc title or memory ID")
    matched_text: str | None = Field(default=None, description="Supporting text excerpt from source")
    verification_method: str = Field(default="jaccard_overlap", description="Matching strategy identifier")
    issue_severity: IssueSeverity = Field(default=IssueSeverity.INFO, description="Severity of detected issue")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class VerificationReport(BaseModel):
    """Comprehensive fact verification audit report.

    Attributes:
        overall_status: Aggregate verification outcome.
        claims_checked: Total number of extracted claims evaluated.
        claims_verified: Count of fully or partially verified claims.
        unsupported_claims: Count of claims lacking supporting evidence.
        hallucination_count: Count of suspected hallucinations.
        overall_confidence: Weighted composite verification confidence.
        claim_results: Individual ClaimResult items.
        citation_audit: Citation-level audit results.
    """

    overall_status: VerificationStatus = Field(default=VerificationStatus.VERIFIED)
    claims_checked: int = Field(default=0, ge=0)
    claims_verified: int = Field(default=0, ge=0)
    unsupported_claims: int = Field(default=0, ge=0)
    hallucination_count: int = Field(default=0, ge=0)
    overall_confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    claim_results: list[ClaimResult] = Field(default_factory=list)
    citation_audit: list[dict] = Field(default_factory=list)


class VerifiedDraftPackage(BaseModel):
    """Verified production draft package output.

    Attributes:
        draft_package: Original immutable DraftPackage from Writer Worker.
        verification_report: Completed VerificationReport.
        is_approved_for_edit: Downstream approval flag for Editor Worker.
        requires_human_review: Flag for manual review escalation.
        audit_timestamp: ISO timestamp of verification execution.
    """

    draft_package: DraftPackage = Field(description="Input DraftPackage from Writer Worker")
    verification_report: VerificationReport = Field(description="Completed VerificationReport")
    is_approved_for_edit: bool = Field(default=True, description="Approval gate for Editor Worker")
    requires_human_review: bool = Field(default=False, description="Escalation flag for manual review")
    audit_timestamp: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat(),
        description="ISO timestamp of verification run",
    )

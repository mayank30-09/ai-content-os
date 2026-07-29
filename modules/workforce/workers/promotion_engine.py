"""Promotion engine module for Memory Worker subsystem.

Evaluates memory records against promotion, archival, and expiration criteria.
"""

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from modules.memory.models import MemoryRecord


class MemoryAction(StrEnum):
    """Supported memory lifecycle evaluation outcomes."""
    PROMOTE = "PROMOTE"
    KEEP_RESEARCH = "KEEP_RESEARCH"
    ARCHIVE = "ARCHIVE"
    IGNORE = "IGNORE"
    EXPIRE = "EXPIRE"

class PromotionEngine(BaseModel):
    """Rules engine evaluating memory records for promotion, archival, or expiration."""

    promotion_authority_threshold: float = Field(default=0.80, ge=0.0, le=1.0)
    promotion_confidence_threshold: float = Field(default=0.85, ge=0.0, le=1.0)
    promotion_importance_threshold: float = Field(default=0.70, ge=0.0, le=1.0)
    archival_importance_threshold: float = Field(default=0.30, ge=0.0, le=1.0)
    archival_stale_days: int = Field(default=45, ge=1)

    def evaluate(self, record: MemoryRecord, authority_score: float = 0.5) -> MemoryAction:
        """Evaluates a MemoryRecord and determines the appropriate lifecycle action.

        Args:
            record: MemoryRecord instance.
            authority_score: Domain authority score (0.0 to 1.0).

        Returns:
            MemoryAction: Recommended lifecycle outcome.
        """
        now = datetime.now(UTC)

        # 1. Expiration check
        if record.expires_at and record.expires_at <= now:
            return MemoryAction.EXPIRE

        # 2. Promotion check for high authority, high confidence, high importance
        if (
            authority_score >= self.promotion_authority_threshold
            and record.confidence >= self.promotion_confidence_threshold
            and record.importance_score >= self.promotion_importance_threshold
        ):
            return MemoryAction.PROMOTE

        # 3. Archival check for low importance or stale records
        stale_cutoff = now.timestamp() - (self.archival_stale_days * 86400)
        is_stale = record.last_accessed_at.timestamp() < stale_cutoff if record.last_accessed_at else False

        if record.importance_score < self.archival_importance_threshold or (is_stale and record.reuse_count == 0):
            return MemoryAction.ARCHIVE

        # Default retain
        return MemoryAction.KEEP_RESEARCH

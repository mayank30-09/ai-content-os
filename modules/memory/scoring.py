"""Memory scoring module for Intelligent Memory System.

Computes multi-factor relevance and decay scores based on recency, frequency (reuse count),
confidence, importance, and user feedback ratings.
"""

import math
from datetime import UTC, datetime

from loguru import logger

from modules.memory.models import MemoryRecord


class MemoryScorer:
    """Computes composite priority and decay scores for memory records."""

    def __init__(
        self,
        w_recency: float = 0.25,
        w_frequency: float = 0.20,
        w_confidence: float = 0.15,
        w_importance: float = 0.20,
        w_feedback: float = 0.20,
        half_life_days: float = 14.0,
    ):
        self.w_recency: float = w_recency
        self.w_frequency: float = w_frequency
        self.w_confidence: float = w_confidence
        self.w_importance: float = w_importance
        self.w_feedback: float = w_feedback
        self.half_life_days: float = half_life_days

    def score_recency(self, record: MemoryRecord) -> float:
        """Calculates exponential half-life decay score based on last_accessed_at timestamp."""
        now = datetime.now(UTC)
        last_accessed = (
            record.last_accessed_at
            if record.last_accessed_at.tzinfo
            else record.last_accessed_at.replace(tzinfo=UTC)
        )
        age_days = max(0.0, (now - last_accessed).total_seconds() / 86400.0)
        # Exponential half-life decay formula: 2 ^ (-age / half_life)
        return math.pow(2.0, -age_days / self.half_life_days)

    def score_frequency(self, record: MemoryRecord) -> float:
        """Normalizes reuse_count into range [0.0, 1.0]."""
        return min(1.0, record.reuse_count / 10.0)

    def score_feedback(self, record: MemoryRecord) -> float:
        """Maps user_feedback from range [-1.0, 1.0] to normalized range [0.0, 1.0]."""
        return max(0.0, min(1.0, (record.user_feedback + 1.0) / 2.0))

    def calculate_score(self, record: MemoryRecord) -> float:
        """Computes composite priority score for a MemoryRecord.

        Args:
            record: MemoryRecord to evaluate.

        Returns:
            float: Composite score (0.0 to 1.0).
        """
        s_recency = self.score_recency(record)
        s_frequency = self.score_frequency(record)
        s_confidence = max(0.0, min(1.0, record.confidence))
        s_importance = max(0.0, min(1.0, record.importance_score))
        s_feedback = self.score_feedback(record)

        composite = (
            (self.w_recency * s_recency)
            + (self.w_frequency * s_frequency)
            + (self.w_confidence * s_confidence)
            + (self.w_importance * s_importance)
            + (self.w_feedback * s_feedback)
        )

        final_score = round(composite, 4)
        logger.debug(f"Computed composite score {final_score} for memory record '{record.id}'")
        return final_score

memory_scorer = MemoryScorer()

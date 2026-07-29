"""Ranker module for Research Engine.

Calculates composite relevance scores for research documents based on query relevance,
confidence, document freshness, and source reliability weights.
"""

import re
from datetime import UTC, datetime

from loguru import logger

from modules.research.models import ResearchDocument


class Ranker:
    """Computes relevance scores and orders research documents descending by score."""

    DEFAULT_SOURCE_RELIABILITY: dict[str, float] = {
        "github": 0.95,
        "docs": 0.90,
        "web": 0.80,
        "youtube": 0.75,
        "reddit": 0.70,
    }

    def __init__(
        self,
        weight_relevance: float = 0.40,
        weight_confidence: float = 0.30,
        weight_freshness: float = 0.15,
        weight_reliability: float = 0.15,
    ):
        self.w_relevance: float = weight_relevance
        self.w_confidence: float = weight_confidence
        self.w_freshness: float = weight_freshness
        self.w_reliability: float = weight_reliability

    def score_relevance(self, doc: ResearchDocument, query: str) -> float:
        """Calculates keyword match relevance score between query and document text."""
        query_words = set(re.findall(r"\w+", query.lower()))
        if not query_words:
            return 0.5

        title_words = set(re.findall(r"\w+", doc.title.lower()))
        content_words = set(re.findall(r"\w+", doc.content.lower()))

        title_matches = len(query_words.intersection(title_words)) / len(query_words)
        content_matches = len(query_words.intersection(content_words)) / len(query_words)

        # Title match carries 60% weight, content match carries 40%
        return min(1.0, (title_matches * 0.6) + (content_matches * 0.4))

    def score_freshness(self, doc: ResearchDocument) -> float:
        """Calculates freshness score (1.0 for new docs, decaying over days)."""
        if not doc.published_at:
            return 0.5  # Neutral default for unknown age

        now = datetime.now(UTC)
        pub_date = doc.published_at if doc.published_at.tzinfo else doc.published_at.replace(tzinfo=UTC)
        age_days = (now - pub_date).total_seconds() / 86400.0

        if age_days <= 0:
            return 1.0
        # Half-life decay over 30 days
        return max(0.1, 1.0 / (1.0 + (age_days / 30.0)))

    def score_reliability(self, doc: ResearchDocument) -> float:
        """Looks up source reliability score for document source type."""
        s_type = (doc.source_type or "web").lower()
        return self.DEFAULT_SOURCE_RELIABILITY.get(s_type, 0.80)

    def calculate_score(self, doc: ResearchDocument, query: str) -> float:
        """Computes weighted composite score for document."""
        rel_score = self.score_relevance(doc, query)
        conf_score = max(0.0, min(1.0, doc.confidence))
        fresh_score = self.score_freshness(doc)
        relia_score = self.score_reliability(doc)

        composite = (
            (self.w_relevance * rel_score)
            + (self.w_confidence * conf_score)
            + (self.w_freshness * fresh_score)
            + (self.w_reliability * relia_score)
        )
        return round(composite, 4)

    def rank(self, documents: list[ResearchDocument], query: str) -> list[ResearchDocument]:
        """Ranks documents in descending order by composite relevance score.

        Args:
            documents: List of ResearchDocument instances.
            query: User search topic or query.

        Returns:
            List[ResearchDocument]: Ranked list sorted by score descending.
        """
        if not documents:
            return []

        # Calculate scores and construct updated copies without in-place mutation
        scored_docs = []
        for doc in documents:
            score = self.calculate_score(doc, query)
            updated_meta = {**doc.metadata, "rank_score": score}
            scored_doc = doc.model_copy(update={"metadata": updated_meta})
            scored_docs.append((score, scored_doc))

        # Sort descending by composite score
        scored_docs.sort(key=lambda x: x[0], reverse=True)
        ranked = [doc for _, doc in scored_docs]
        logger.info(f"Ranked {len(ranked)} documents for query: '{query}'")
        return ranked

ranker = Ranker()

"""Quality validator module for Research Worker subsystem.

Provides source quality auditing, domain diversity calculations, and threshold filtering.
"""

from urllib.parse import urlparse

from loguru import logger

from modules.research.models import ResearchDocument
from modules.workforce.workers.citation import SourceCitation, SourceQualityModel


class QualityValidator:
    """Audits research documents and citations against quality models."""

    def __init__(self, quality_model: SourceQualityModel = None):
        self.quality_model: SourceQualityModel = quality_model or SourceQualityModel()

    def build_citation(self, doc: ResearchDocument) -> SourceCitation:
        """Converts a ResearchDocument into a SourceCitation.

        Args:
            doc: ResearchDocument instance.

        Returns:
            SourceCitation: Standardized citation model.
        """
        parsed_url = urlparse(str(doc.url))
        domain = parsed_url.netloc or doc.source or "unknown"

        # Domain authority heuristics
        authority_map = {
            "github.com": 0.95,
            "docs.python.org": 0.95,
            "arxiv.org": 0.90,
            "reddit.com": 0.65,
            "youtube.com": 0.60,
        }
        authority = authority_map.get(domain.lower(), 0.70)

        return SourceCitation(
            title=doc.title or "Untitled Document",
            url=str(doc.url),
            source_type=doc.source_type or doc.source or "web",
            domain=domain,
            authority_score=authority,
            freshness_score=0.85,
            relevance_score=float(doc.metadata.get("rank_score", doc.confidence)),
            confidence=doc.confidence,
            citation_metadata=doc.metadata,
        )

    def validate_and_filter(
        self, documents: list[ResearchDocument]
    ) -> tuple[list[SourceCitation], float]:
        """Converts documents to citations, calculates quality, and filters low-quality entries.

        Args:
            documents: List of ResearchDocument instances.

        Returns:
            Tuple[List[SourceCitation], float]: Validated citations and average quality score.
        """
        if not documents:
            logger.warning("QualityValidator received zero documents.")
            return [], 0.0

        seen_urls = set()
        unique_docs = []
        for doc in documents:
            url_str = str(doc.url) if doc.url else f"no_url_{doc.id}"
            if url_str in seen_urls:
                continue
            seen_urls.add(url_str)
            unique_docs.append(doc)

        citations = [self.build_citation(doc) for doc in unique_docs]
        domain_counts = {}
        for c in citations:
            domain_counts[c.domain] = domain_counts.get(c.domain, 0) + 1

        total_citations = len(citations)
        validated = []
        scores = []

        for c in citations:
            # Diversity score penalizes domain over-representation
            diversity = 1.0 - ((domain_counts[c.domain] - 1) / total_citations)
            q_score = self.quality_model.calculate_quality_score(c, diversity_score=diversity)
            scores.append(q_score)

            if q_score >= self.quality_model.minimum_quality_threshold:
                validated.append(c)
            else:
                logger.warning(
                    f"Filtered low-quality citation '{c.title}' [Score: {q_score} < {self.quality_model.minimum_quality_threshold}]"
                )

        avg_quality = round(sum(scores) / len(scores), 3) if scores else 0.0
        logger.info(f"Validated {len(validated)}/{len(documents)} citations [Avg Quality: {avg_quality}]")
        return validated, avg_quality

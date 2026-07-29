"""Aggregator module for Research Engine.

Flattens, normalizes, and consolidates document collections returned by diverse plugins.
"""


from loguru import logger

from modules.research.models import ResearchDocument


class Aggregator:
    """Consolidates and normalizes raw document lists from multiple plugin tasks."""

    def aggregate(self, plugin_results: list[list[ResearchDocument]]) -> list[ResearchDocument]:
        """Flattens list of plugin document lists into a unified list.

        Args:
            plugin_results: List of document lists returned by executed plugins.

        Returns:
            List[ResearchDocument]: Flattened, normalized list of documents.
        """
        flattened: list[ResearchDocument] = []
        for doc_list in plugin_results:
            if not doc_list:
                continue
            for doc in doc_list:
                # Ensure title and content are clean
                normalized_doc = self._normalize_document(doc)
                flattened.append(normalized_doc)

        logger.info(f"Aggregated {len(flattened)} raw documents across {len(plugin_results)} plugin executions.")
        return flattened

    def _normalize_document(self, doc: ResearchDocument) -> ResearchDocument:
        """Normalizes text formatting and guarantees essential metadata fields."""
        doc.title = doc.title.strip() if doc.title else "Untitled Document"
        doc.content = doc.content.strip() if doc.content else ""
        if not doc.summary and doc.content:
            doc.summary = doc.content[:200] + "..." if len(doc.content) > 200 else doc.content
        return doc

aggregator = Aggregator()

"""Summarizer module for Research Engine.

Generates structured ResearchPackage payloads from ranked ResearchDocument lists
using a deterministic offline extraction strategy without calling external LLM APIs.
"""

from typing import Any

from loguru import logger

from modules.research.models import ResearchDocument, ResearchPackage


class Summarizer:
    """Offline placeholder summarization engine assembling structured ResearchPackages."""

    def build_package(
        self,
        query: str,
        ranked_documents: list[ResearchDocument],
        metrics: dict[str, Any] = None
    ) -> ResearchPackage:
        """Assembles a ResearchPackage payload from ranked documents.

        Args:
            query: Original research topic query.
            ranked_documents: Pre-ranked list of ResearchDocument objects.
            metrics: Execution metrics and timing stats.

        Returns:
            ResearchPackage: Structured research package.
        """
        logger.info(f"Building ResearchPackage for query: '{query}' ({len(ranked_documents)} docs)")

        if not ranked_documents:
            return ResearchPackage(
                query=query,
                executive_summary=f"No research content was found for topic: '{query}'.",
                key_facts=[],
                references=[],
                ranked_documents=[],
                execution_metrics=metrics or {}
            )

        # 1. Build Executive Summary from top 3 document summaries
        top_docs = ranked_documents[:3]
        summary_snippets = []
        for d in top_docs:
            snippet = d.summary or (d.content[:150] + "..." if len(d.content) > 150 else d.content)
            summary_snippets.append(f"[{d.source_type.upper()}] {snippet}")
        exec_summary = f"Research synthesis for '{query}':\n" + "\n".join(summary_snippets)

        # 2. Extract Key Facts from top documents
        key_facts = []
        for d in ranked_documents[:5]:
            fact = f"{d.title} (Source: {d.source_type})"
            key_facts.append(fact)

        # 3. Build References list
        references = []
        for d in ranked_documents:
            ref = {
                "title": d.title,
                "url": d.url or "N/A",
                "source_type": d.source_type,
                "author": d.author or "Unknown"
            }
            references.append(ref)

        package = ResearchPackage(
            query=query,
            executive_summary=exec_summary,
            key_facts=key_facts,
            references=references,
            ranked_documents=ranked_documents,
            execution_metrics=metrics or {}
        )
        logger.info(f"ResearchPackage built successfully for '{query}'.")
        return package

summarizer = Summarizer()

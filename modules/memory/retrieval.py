"""Retrieval Engine module for Intelligent Memory System.

Combines FTS5 keyword search, namespace filtering, and composite memory scoring
to retrieve the most relevant past memories.
"""


from loguru import logger

from modules.memory.base_store import BaseMemoryStore
from modules.memory.models import MemoryNamespace, MemoryRecord
from modules.memory.scoring import MemoryScorer, memory_scorer


class RetrievalEngine:
    """Retrieves and ranks memory records for context injection."""

    def __init__(self, store: BaseMemoryStore, scorer: MemoryScorer = memory_scorer):
        self.store: BaseMemoryStore = store
        self.scorer: MemoryScorer = scorer

    def search_keyword(
        self, query: str, namespace: MemoryNamespace | None = None, limit: int = 20
    ) -> list[MemoryRecord]:
        """Executes FTS5 keyword search and ranks results by composite score."""
        records = self.store.search_fts(query, namespace=namespace, limit=limit * 2)
        return self._rank_records(records, limit=limit)

    def retrieve_by_namespace(
        self, namespace: MemoryNamespace, limit: int = 10
    ) -> list[MemoryRecord]:
        """Retrieves top scoring records within a specific namespace."""
        records = self.store.get_by_namespace(namespace, limit=limit * 2)
        return self._rank_records(records, limit=limit)

    def search_hybrid(
        self, query: str, namespace: MemoryNamespace | None = None, limit: int = 20
    ) -> list[MemoryRecord]:
        """Hybrid retrieval interface combining FTS keyword search and scoring (Vector hook ready)."""
        logger.info(f"Executing hybrid search for query: '{query}' [Namespace: {namespace}]")
        keyword_results = self.store.search_fts(query, namespace=namespace, limit=limit * 2)

        # Fallback to namespace search if FTS keyword search returned zero candidates
        if not keyword_results and namespace:
            keyword_results = self.store.get_by_namespace(namespace, limit=limit * 2)

        return self._rank_records(keyword_results, limit=limit)

    def _rank_records(self, records: list[MemoryRecord], limit: int) -> list[MemoryRecord]:
        """Ranks candidate memory records using MemoryScorer composite score descending."""
        if not records:
            return []

        scored: list[tuple[float, MemoryRecord]] = []
        for r in records:
            score = self.scorer.calculate_score(r)
            # Return updated record copy with computed rank_score in metadata
            meta = {**r.metadata, "rank_score": score}
            updated = r.model_copy(update={"metadata": meta})
            scored.append((score, updated))

        scored.sort(key=lambda x: x[0], reverse=True)
        ranked = [rec for _, rec in scored[:limit]]
        logger.debug(f"Retrieved and ranked {len(ranked)} memory records.")
        return ranked

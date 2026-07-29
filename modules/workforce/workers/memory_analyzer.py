"""Memory analyzer module for Memory Worker subsystem.

Coordinates cross-namespace deduplication, promotion rule execution, memory archiving,
TTL expiration pruning, and telemetry metrics assembly.
"""


from loguru import logger

from modules.memory.manager import MemoryManager, memory_manager
from modules.memory.models import KnowledgeMemory, MemoryNamespace, MemoryRecord, ResearchMemory
from modules.research.models import ResearchPackage
from modules.workforce.workers.duplicate_detector import DuplicateDetector
from modules.workforce.workers.memory_metrics import MemoryWorkerMetrics
from modules.workforce.workers.promotion_engine import MemoryAction, PromotionEngine


class MemoryAnalyzer:
    """Orchestrates memory analysis, deduplication, promotion, and health pruning."""

    def __init__(
        self,
        memory_mgr: MemoryManager | None = None,
        dedup: DuplicateDetector | None = None,
        promo: PromotionEngine | None = None,
    ):
        self.memory_manager: MemoryManager = memory_mgr or memory_manager
        self.duplicate_detector: DuplicateDetector = dedup or DuplicateDetector()
        self.promotion_engine: PromotionEngine = promo or PromotionEngine()

    async def analyze_and_process(
        self, query: str, package: ResearchPackage | None = None
    ) -> tuple[MemoryWorkerMetrics, list[str]]:
        """Processes incoming research findings, performs deduplication, promotion, and pruning.

        Args:
            query: Target research query or topic string.
            package: Optional ResearchPackage output from research worker.

        Returns:
            Tuple[MemoryWorkerMetrics, List[str]]: Execution metrics and list of created/updated memory IDs.
        """
        metrics = MemoryWorkerMetrics()
        processed_ids: list[str] = []

        # 1. Prune expired records
        expired_count = self.memory_manager.prune_expired()
        metrics.memories_expired = expired_count
        logger.info(f"Pruned {expired_count} expired memory records from store.")

        # If package provided, extract documents and citations
        if not package or not package.ranked_documents:
            logger.info(f"No documents in ResearchPackage for query '{query}'")
            return metrics, processed_ids

        # Fetch existing research and knowledge records for deduplication check
        existing_res = self.memory_manager.search_memory(query, namespace=MemoryNamespace.RESEARCH, limit=50)
        existing_knw = self.memory_manager.search_memory(query, namespace=MemoryNamespace.KNOWLEDGE, limit=50)
        existing_all = existing_res + existing_knw

        # Convert documents to candidate ResearchMemory records
        candidates: list[MemoryRecord] = [
            ResearchMemory(
                query=query,
                content=doc.content,
                key_facts=[doc.summary] if doc.summary else [doc.title],
                source_urls=[doc.url] if doc.url else [],
                confidence=doc.confidence,
                importance_score=float(doc.metadata.get("rank_score", doc.confidence)),
            )
            for doc in package.ranked_documents
        ]

        # 2. Deduplication check
        unique_candidates, dupes_removed = self.duplicate_detector.filter_duplicates(candidates, existing_all)
        metrics.duplicates_removed = dupes_removed

        # 3. Promotion & Storage evaluation
        for record in unique_candidates:
            authority = 0.85 if any("github.com" in url or "docs." in url for url in record.source_urls) else 0.60
            action = self.promotion_engine.evaluate(record, authority_score=authority)

            if action == MemoryAction.PROMOTE:
                # Promote to KnowledgeMemory
                knw_rec = KnowledgeMemory(
                    entity_name=record.content[:50],
                    category="promoted_knowledge",
                    content=record.content,
                    tags=["promoted", query],
                    claims=record.key_facts,
                    confidence=record.confidence,
                    importance_score=record.importance_score,
                )
                rec_id = self.memory_manager.store_memory(knw_rec)
                processed_ids.append(rec_id)
                metrics.memories_promoted += 1
                metrics.memories_created += 1

            elif action == MemoryAction.KEEP_RESEARCH:
                rec_id = self.memory_manager.store_memory(record)
                processed_ids.append(rec_id)
                metrics.memories_created += 1

            elif action == MemoryAction.ARCHIVE:
                rec_id = self.memory_manager.store_memory(record)
                self.memory_manager.archive_memory(rec_id)
                processed_ids.append(rec_id)
                metrics.memories_archived += 1

        avg_quality = round(
            sum(r.importance_score for r in unique_candidates) / len(unique_candidates), 3
        ) if unique_candidates else 0.0
        metrics.average_memory_quality = avg_quality

        logger.info(
            f"Memory analysis finished [Created: {metrics.memories_created}, "
            f"Promoted: {metrics.memories_promoted}, Archived: {metrics.memories_archived}, "
            f"Dupes Removed: {metrics.duplicates_removed}]"
        )

        return metrics, processed_ids

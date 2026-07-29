"""Memory manager module for Intelligent Memory System.

Coordinates store CRUD actions, namespace retrieval, archival, deletion, scoring,
and TTL expiration lifecycle pruning.
"""


from loguru import logger

from modules.memory.base_store import BaseMemoryStore
from modules.memory.models import MemoryNamespace, MemoryRecord
from modules.memory.retrieval import RetrievalEngine
from modules.memory.sqlite_store import SQLiteMemoryStore


class MemoryManager:
    """Central orchestrator for memory persistence and retrieval lifecycles."""

    def __init__(self, store: BaseMemoryStore | None = None):
        self.store: BaseMemoryStore = store or SQLiteMemoryStore()
        self.retrieval: RetrievalEngine = RetrievalEngine(store=self.store)

    def store_memory(self, record: MemoryRecord) -> str:
        """Stores or updates a MemoryRecord in local persistence.

        Args:
            record: MemoryRecord object.

        Returns:
            str: Saved record ID.
        """
        logger.info(f"Storing memory record '{record.id}' in namespace '{record.namespace.value}'")
        return self.store.save(record)

    def retrieve(self, record_id: str) -> MemoryRecord | None:
        """Retrieves a memory record by ID and increments its reuse count.

        Args:
            record_id: Record ID.

        Returns:
            Optional[MemoryRecord]: MemoryRecord if found, None otherwise.
        """
        record = self.store.get_by_id(record_id)
        if record:
            updated = record.model_copy(update={"reuse_count": record.reuse_count + 1})
            self.store.save(updated)
            return updated
        return None

    def search_memory(
        self, query: str, namespace: MemoryNamespace | None = None, limit: int = 10
    ) -> list[MemoryRecord]:
        """Searches memory records using hybrid retrieval.

        Args:
            query: Search query text.
            namespace: Optional namespace filter.
            limit: Maximum result limit.

        Returns:
            List[MemoryRecord]: Ranked matching memory records.
        """
        return self.retrieval.search_hybrid(query, namespace=namespace, limit=limit)

    def get_by_namespace(
        self, namespace: MemoryNamespace, limit: int = 20
    ) -> list[MemoryRecord]:
        """Retrieves memories strictly scoped to a namespace."""
        return self.retrieval.retrieve_by_namespace(namespace, limit=limit)

    def update_memory(self, record: MemoryRecord) -> bool:
        """Updates an existing memory record."""
        return self.store.update(record)

    def archive_memory(self, record_id: str) -> bool:
        """Soft-deletes/archives a memory record by ID."""
        return self.store.archive(record_id)

    def delete_memory(self, record_id: str) -> bool:
        """Permanently deletes a memory record by ID."""
        return self.store.delete(record_id)

    def prune_expired_memories(self) -> int:
        """Prunes all memory records past their expires_at timestamp."""
        return self.store.prune_expired()

memory_manager = MemoryManager()

"""Base memory store abstract module.

Defines the contract interface for memory persistence storage backends.
"""

from abc import ABC, abstractmethod

from modules.memory.models import MemoryNamespace, MemoryRecord


class BaseMemoryStore(ABC):
    """Abstract interface for memory persistence storage layers."""

    @abstractmethod
    def save(self, record: MemoryRecord) -> str:
        """Saves or inserts a memory record into storage.

        Args:
            record: MemoryRecord instance to store.

        Returns:
            str: Record ID string.
        """
        pass

    @abstractmethod
    def get_by_id(self, record_id: str) -> MemoryRecord | None:
        """Retrieves a memory record by ID.

        Args:
            record_id: Memory ID.

        Returns:
            Optional[MemoryRecord]: Record if found, None otherwise.
        """
        pass

    @abstractmethod
    def get_by_namespace(
        self, namespace: MemoryNamespace, limit: int = 100, include_archived: bool = False
    ) -> list[MemoryRecord]:
        """Retrieves all memory records for a given namespace.

        Args:
            namespace: MemoryNamespace enum filter.
            limit: Max records to return.
            include_archived: Whether to include archived records.

        Returns:
            List[MemoryRecord]: List of matching memory records.
        """
        pass

    @abstractmethod
    def search_fts(
        self, query: str, namespace: MemoryNamespace | None = None, limit: int = 20
    ) -> list[MemoryRecord]:
        """Searches memory records using Full Text Search (FTS).

        Args:
            query: Keyword search string.
            namespace: Optional namespace filter.
            limit: Maximum result limit.

        Returns:
            List[MemoryRecord]: Matching memory records.
        """
        pass

    @abstractmethod
    def update(self, record: MemoryRecord) -> bool:
        """Updates an existing memory record.

        Args:
            record: Updated MemoryRecord instance.

        Returns:
            bool: True if updated, False otherwise.
        """
        pass

    @abstractmethod
    def delete(self, record_id: str) -> bool:
        """Deletes a memory record permanently by ID.

        Args:
            record_id: Memory ID to delete.

        Returns:
            bool: True if deleted, False otherwise.
        """
        pass

    @abstractmethod
    def archive(self, record_id: str) -> bool:
        """Sets is_archived flag to True for a memory record.

        Args:
            record_id: Memory ID to archive.

        Returns:
            bool: True if archived, False otherwise.
        """
        pass

    @abstractmethod
    def prune_expired(self) -> int:
        """Prunes expired memory records past their expires_at timestamp.

        Returns:
            int: Count of pruned records.
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """Closes store and releases database resources."""
        pass

"""Knowledge graph interface stub for Intelligent Memory System.

Defines the abstract interface for future entity-relationship Graph Memory integration.
"""

from abc import ABC, abstractmethod
from typing import Any


class IKnowledgeGraphEngine(ABC):
    """Abstract contract interface for future Knowledge Graph engines."""

    @abstractmethod
    async def add_entity(
        self, entity_id: str, label: str, properties: dict[str, Any]
    ) -> bool:
        """Adds a graph node entity.

        Args:
            entity_id: Unique entity ID.
            label: Category or type label.
            properties: Key-value attributes.

        Returns:
            bool: True if entity was added, False otherwise.
        """
        pass

    @abstractmethod
    async def add_relation(
        self, source_id: str, target_id: str, relation_type: str
    ) -> bool:
        """Adds a directed relation edge between two entities.

        Args:
            source_id: Origin entity ID.
            target_id: Destination entity ID.
            relation_type: Relationship descriptor tag.

        Returns:
            bool: True if relation was added, False otherwise.
        """
        pass

    @abstractmethod
    async def find_related(
        self, entity_id: str, max_depth: int = 2
    ) -> list[dict[str, Any]]:
        """Finds related entities and edges up to max_depth traversal.

        Args:
            entity_id: Target root entity ID.
            max_depth: Maximum graph hop depth.

        Returns:
            List[Dict[str, Any]]: Related graph entities and relation structures.
        """
        pass

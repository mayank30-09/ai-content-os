"""Duplicate detector module for Memory Worker subsystem.

Detects duplicate memory records via URL matching, title similarity, and metadata inspection.
Includes future-ready semantic similarity interface stubs.
"""

from urllib.parse import urlparse

from loguru import logger

from modules.memory.models import MemoryRecord


class DuplicateDetector:
    """Detects duplicate memory records across store namespaces."""

    @staticmethod
    def normalize_url(url: str | None) -> str:
        """Normalizes URL by stripping query parameters and trailing slashes."""
        if not url:
            return ""
        parsed = urlparse(url)
        normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/")
        return normalized.lower()

    @staticmethod
    def calculate_title_similarity(title1: str, title2: str) -> float:
        """Calculates simple token overlap Jaccard similarity between two title strings."""
        if not title1 or not title2:
            return 0.0
        set1 = set(title1.lower().split())
        set2 = set(title2.lower().split())
        intersection = set1.intersection(set2)
        union = set1.union(set2)
        return len(intersection) / len(union) if union else 0.0

    def compute_semantic_similarity(self, record1: MemoryRecord, record2: MemoryRecord) -> float:
        """Future-ready interface stub for vector embedding semantic similarity."""
        # Future sqlite-vss / fastembed vector similarity hook
        return 0.0

    def is_duplicate(
        self, new_record: MemoryRecord, existing_record: MemoryRecord
    ) -> tuple[bool, str]:
        """Audits if a new memory record is a duplicate of an existing record.

        Args:
            new_record: New incoming MemoryRecord.
            existing_record: Pre-existing MemoryRecord in store.

        Returns:
            Tuple[bool, str]: Boolean flag and match reason descriptor string.
        """
        if new_record.id == existing_record.id:
            return True, "exact_id_match"

        # 1. URL Match
        new_url = self.normalize_url(getattr(new_record, "url", None) or getattr(new_record, "source_urls", [""])[0] if getattr(new_record, "source_urls", None) else None)
        existing_url = self.normalize_url(getattr(existing_record, "url", None) or getattr(existing_record, "source_urls", [""])[0] if getattr(existing_record, "source_urls", None) else None)

        if new_url and existing_url and new_url == existing_url:
            return True, "exact_url_match"

        # 2. Title / Query Jaccard Similarity
        new_title = getattr(new_record, "entity_name", None) or getattr(new_record, "query", None) or new_record.content[:50]
        existing_title = getattr(existing_record, "entity_name", None) or getattr(existing_record, "query", None) or existing_record.content[:50]

        sim = self.calculate_title_similarity(new_title, existing_title)
        if sim >= 0.85:
            return True, f"title_similarity_match ({sim:.2f})"

        # 3. Semantic similarity stub check
        sem_sim = self.compute_semantic_similarity(new_record, existing_record)
        if sem_sim >= 0.90:
            return True, f"semantic_similarity_match ({sem_sim:.2f})"

        return False, "unique"

    def filter_duplicates(
        self, new_records: list[MemoryRecord], existing_records: list[MemoryRecord]
    ) -> tuple[list[MemoryRecord], int]:
        """Filters out duplicate records from incoming list.

        Args:
            new_records: List of incoming records to check.
            existing_records: Existing records in store.

        Returns:
            Tuple[List[MemoryRecord], int]: List of unique new records and count of removed duplicates.
        """
        unique_records = []
        duplicate_count = 0

        for new_rec in new_records:
            dupe_found = False
            for exist_rec in existing_records:
                is_dupe, reason = self.is_duplicate(new_rec, exist_rec)
                if is_dupe:
                    logger.info(f"Filtered duplicate memory record '{new_rec.id}' [Reason: {reason}]")
                    duplicate_count += 1
                    dupe_found = True
                    break

            if not dupe_found:
                unique_records.append(new_rec)

        return unique_records, duplicate_count

"""SQLite memory store implementation.

Provides local SQLite + FTS5 full-text indexing, namespace filtering, and TTL expiration
pruning for memory records.
"""

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from loguru import logger

from config.settings import settings
from modules.memory.base_store import BaseMemoryStore
from modules.memory.models import (
    GenerationMemory,
    KnowledgeMemory,
    MemoryNamespace,
    MemoryRecord,
    PromptMemory,
    ResearchMemory,
    StyleMemory,
)


class SQLiteMemoryStore(BaseMemoryStore):
    """SQLite + FTS5 database engine for persistent memory storage."""

    def __init__(self, db_path: Path | None = None):
        self.db_path: Path = db_path or (settings.USER_DATA_DIR / "database" / "memory_system.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Creates and returns a SQLite database connection."""
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Initializes database schema, FTS5 virtual table, and indices."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # 1. Base Records Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS memory_records (
                    id TEXT PRIMARY KEY,
                    namespace TEXT NOT NULL,
                    content TEXT NOT NULL,
                    tags TEXT NOT NULL,
                    importance_score REAL NOT NULL,
                    confidence REAL NOT NULL,
                    reuse_count INTEGER NOT NULL,
                    user_feedback REAL NOT NULL,
                    created_at TEXT NOT NULL,
                    last_accessed_at TEXT NOT NULL,
                    expires_at TEXT,
                    is_archived INTEGER NOT NULL,
                    metadata TEXT NOT NULL
                )
            """)

            # 2. FTS5 Virtual Table for Fast Full-Text Search
            cursor.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(
                    id UNINDEXED,
                    namespace,
                    content,
                    tags
                )
            """)

            # 3. Performance Indices
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_memory_namespace ON memory_records(namespace)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_memory_archived ON memory_records(is_archived)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_memory_expires ON memory_records(expires_at)")
            conn.commit()
            logger.info(f"Initialized SQLite MemoryStore database schema at: {self.db_path}")

    def _row_to_model(self, row: sqlite3.Row) -> MemoryRecord:
        """Converts a SQLite database row into the appropriate typed MemoryRecord model."""
        meta = json.loads(row["metadata"]) if row["metadata"] else {}
        tags = json.loads(row["tags"]) if row["tags"] else []

        created_at = datetime.fromisoformat(row["created_at"])
        last_accessed = datetime.fromisoformat(row["last_accessed_at"])
        expires_at = datetime.fromisoformat(row["expires_at"]) if row["expires_at"] else None
        namespace_val = row["namespace"]

        data = {
            "id": row["id"],
            "namespace": namespace_val,
            "content": row["content"],
            "tags": tags,
            "importance_score": row["importance_score"],
            "confidence": row["confidence"],
            "reuse_count": row["reuse_count"],
            "user_feedback": row["user_feedback"],
            "created_at": created_at,
            "last_accessed_at": last_accessed,
            "expires_at": expires_at,
            "is_archived": bool(row["is_archived"]),
            "metadata": meta,
            **meta
        }

        # Instantiate specialized child models based on namespace
        if namespace_val == MemoryNamespace.RESEARCH.value:
            return ResearchMemory.model_validate(data)
        elif namespace_val == MemoryNamespace.STYLE.value:
            return StyleMemory.model_validate(data)
        elif namespace_val == MemoryNamespace.PROMPT.value:
            return PromptMemory.model_validate(data)
        elif namespace_val == MemoryNamespace.GENERATION.value:
            return GenerationMemory.model_validate(data)
        elif namespace_val == MemoryNamespace.KNOWLEDGE.value:
            return KnowledgeMemory.model_validate(data)

        return MemoryRecord.model_validate(data)

    def save(self, record: MemoryRecord) -> str:
        """Saves a MemoryRecord into SQLite and FTS5 search index."""
        dumped = record.model_dump(mode="json")
        base_keys = {
            "id", "namespace", "content", "tags", "importance_score",
            "confidence", "reuse_count", "user_feedback", "created_at",
            "last_accessed_at", "expires_at", "is_archived", "metadata"
        }
        extra_fields = {k: v for k, v in dumped.items() if k not in base_keys}
        meta_dict = {**record.metadata, **extra_fields}
        meta_json = json.dumps(meta_dict)

        tags_json = json.dumps(record.tags)
        created_str = record.created_at.isoformat()
        accessed_str = record.last_accessed_at.isoformat()
        expires_str = record.expires_at.isoformat() if record.expires_at else None

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO memory_records (
                    id, namespace, content, tags, importance_score, confidence,
                    reuse_count, user_feedback, created_at, last_accessed_at,
                    expires_at, is_archived, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.id, record.namespace.value, record.content, tags_json,
                record.importance_score, record.confidence, record.reuse_count,
                record.user_feedback, created_str, accessed_str, expires_str,
                1 if record.is_archived else 0, meta_json
            ))

            # Sync FTS5 Index
            cursor.execute("DELETE FROM memory_fts WHERE id = ?", (record.id,))
            cursor.execute("""
                INSERT INTO memory_fts (id, namespace, content, tags)
                VALUES (?, ?, ?, ?)
            """, (record.id, record.namespace.value, record.content, " ".join(record.tags)))

            conn.commit()
            logger.debug(f"Saved memory record '{record.id}' [Namespace: {record.namespace.value}]")
            return record.id

    def get_by_id(self, record_id: str) -> MemoryRecord | None:
        """Retrieves record by ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM memory_records WHERE id = ?", (record_id,))
            row = cursor.fetchone()
            if row:
                return self._row_to_model(row)
        return None

    def get_by_namespace(
        self, namespace: MemoryNamespace, limit: int = 100, include_archived: bool = False
    ) -> list[MemoryRecord]:
        """Retrieves all memory records for a given namespace."""
        query_sql = "SELECT * FROM memory_records WHERE namespace = ?"
        params = [namespace.value]

        if not include_archived:
            query_sql += " AND is_archived = 0"
        query_sql += " ORDER BY last_accessed_at DESC LIMIT ?"
        params.append(limit)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query_sql, params)
            rows = cursor.fetchall()
            return [self._row_to_model(row) for row in rows]

    def search_fts(
        self, query: str, namespace: MemoryNamespace | None = None, limit: int = 20
    ) -> list[MemoryRecord]:
        """Performs BM25 keyword search using FTS5 virtual table."""
        if not query or not query.strip():
            return []

        # Sanitize query for FTS5 syntax
        sanitized = " ".join(f'"{token}"*' for token in query.strip().split() if token.isalnum())
        if not sanitized:
            return []

        if namespace:
            fts_sql = """
                SELECT r.* FROM memory_records r
                JOIN memory_fts f ON r.id = f.id
                WHERE memory_fts MATCH ? AND r.namespace = ? AND r.is_archived = 0
                ORDER BY rank LIMIT ?
            """
            params = (sanitized, namespace.value, limit)
        else:
            fts_sql = """
                SELECT r.* FROM memory_records r
                JOIN memory_fts f ON r.id = f.id
                WHERE memory_fts MATCH ? AND r.is_archived = 0
                ORDER BY rank LIMIT ?
            """
            params = (sanitized, limit)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(fts_sql, params)
            rows = cursor.fetchall()
            return [self._row_to_model(row) for row in rows]

    def update(self, record: MemoryRecord) -> bool:
        """Updates an existing record in SQLite and FTS5."""
        if not self.get_by_id(record.id):
            return False
        self.save(record)
        return True

    def delete(self, record_id: str) -> bool:
        """Permanently deletes record from SQLite and FTS5."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM memory_records WHERE id = ?", (record_id,))
            cursor.execute("DELETE FROM memory_fts WHERE id = ?", (record_id,))
            conn.commit()
            deleted = cursor.rowcount > 0
            if deleted:
                logger.info(f"Deleted memory record '{record_id}'")
            return deleted

    def archive(self, record_id: str) -> bool:
        """Sets is_archived to 1 for record."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE memory_records SET is_archived = 1 WHERE id = ?", (record_id,))
            conn.commit()
            archived = cursor.rowcount > 0
            if archived:
                logger.info(f"Archived memory record '{record_id}'")
            return archived

    def prune_expired(self) -> int:
        """Prunes expired memory records past expires_at timestamp."""
        now_str = datetime.now(UTC).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM memory_records WHERE expires_at IS NOT NULL AND expires_at < ?", (now_str,))
            expired_ids = [row["id"] for row in cursor.fetchall()]

            if not expired_ids:
                return 0

            for id_val in expired_ids:
                cursor.execute("DELETE FROM memory_records WHERE id = ?", (id_val,))
                cursor.execute("DELETE FROM memory_fts WHERE id = ?", (id_val,))

            conn.commit()
            logger.info(f"Pruned {len(expired_ids)} expired memory records.")
            return len(expired_ids)

    def close(self) -> None:
        """Closes store connection and forces SQLite garbage collection."""
        try:
            # Force a temporary connection checkpoint to flush write-ahead logs
            with self._get_connection() as conn:
                conn.execute("PRAGMA optimize;")
        except Exception as e:
            logger.debug(f"SQLite store cleanup optimize note: {e}")

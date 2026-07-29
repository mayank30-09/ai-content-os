import sqlite3
import uuid
from typing import Any

from modules.memory.db_client import db_client
from modules.memory.write_queue import async_write_queue


class ContentRepository:
    def create(self, topic: str, format_type: str) -> str:
        content_id = str(uuid.uuid4())
        with db_client.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO content_items (id, topic, format_type, state)
                VALUES (?, ?, ?, 'INITIATED')
                """,
                (content_id, topic, format_type)
            )
            conn.commit()
        return content_id

    async def create_async(self, topic: str, format_type: str) -> str:
        content_id = str(uuid.uuid4())
        def _write(conn: sqlite3.Connection):
            conn.execute(
                "INSERT INTO content_items (id, topic, format_type, state) VALUES (?, ?, ?, 'INITIATED')",
                (content_id, topic, format_type)
            )
        await async_write_queue.execute_write(_write)
        return content_id

    def get_by_id(self, content_id: str) -> dict[str, Any] | None:
        with db_client.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM content_items WHERE id = ?", (content_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def list_all(self, limit: int = 50) -> list[dict[str, Any]]:
        with db_client.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM content_items ORDER BY created_at DESC LIMIT ?", (limit,))
            return [dict(row) for row in cursor.fetchall()]

    def update_research(self, content_id: str, research_summary: str):
        with db_client.get_connection() as conn:
            conn.execute(
                """
                UPDATE content_items
                SET research_summary = ?, state = 'RESEARCHED', updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (research_summary, content_id)
            )
            conn.commit()

    async def update_research_async(self, content_id: str, research_summary: str):
        def _write(conn: sqlite3.Connection):
            conn.execute(
                """
                UPDATE content_items
                SET research_summary = ?, state = 'RESEARCHED', updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (research_summary, content_id)
            )
        await async_write_queue.execute_write(_write)

    def update_ai_outputs(
        self,
        content_id: str,
        ai_raw_output: str,
        reels_script: str | None = None,
        carousel_json: str | None = None,
        stories_json: str | None = None,
        caption_text: str | None = None,
        hashtags: str | None = None,
        image_prompts: str | None = None
    ):
        with db_client.get_connection() as conn:
            conn.execute(
                """
                UPDATE content_items
                SET ai_raw_output = ?, reels_script = ?, carousel_json = ?, stories_json = ?,
                    caption_text = ?, hashtags = ?, image_prompts = ?, state = 'PENDING_APPROVAL',
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    ai_raw_output, reels_script, carousel_json, stories_json,
                    caption_text, hashtags, image_prompts, content_id
                )
            )
            conn.commit()

    async def update_ai_outputs_async(
        self,
        content_id: str,
        ai_raw_output: str,
        reels_script: str | None = None,
        carousel_json: str | None = None,
        stories_json: str | None = None,
        caption_text: str | None = None,
        hashtags: str | None = None,
        image_prompts: str | None = None
    ):
        def _write(conn: sqlite3.Connection):
            conn.execute(
                """
                UPDATE content_items
                SET ai_raw_output = ?, reels_script = ?, carousel_json = ?, stories_json = ?,
                    caption_text = ?, hashtags = ?, image_prompts = ?, state = 'PENDING_APPROVAL',
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    ai_raw_output, reels_script, carousel_json, stories_json,
                    caption_text, hashtags, image_prompts, content_id
                )
            )
        await async_write_queue.execute_write(_write)

    def set_approval(self, content_id: str, is_approved: bool, rejection_reason: str | None = None):
        state = 'APPROVED' if is_approved else 'FAILED'
        with db_client.get_connection() as conn:
            conn.execute(
                """
                UPDATE content_items
                SET is_human_approved = ?, state = ?, rejection_reason = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (1 if is_approved else 0, state, rejection_reason, content_id)
            )
            conn.commit()

    def mark_published(self, content_id: str):
        with db_client.get_connection() as conn:
            conn.execute(
                """
                UPDATE content_items
                SET state = 'PUBLISHED', published_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND is_human_approved = 1
                """,
                (content_id,)
            )
            conn.commit()

class KnowledgeRepository:
    """Compatibility adapter forwarding legacy knowledge base calls to MemoryManager."""

    def add(self, title: str, source_type: str, url: str, content_body: str, tags: str = "") -> str:
        from modules.memory.manager import memory_manager
        from modules.memory.models import KnowledgeMemory

        tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
        record = KnowledgeMemory(
            entity_name=title,
            category=source_type,
            content=content_body,
            tags=tag_list,
            claims=[content_body[:200]]
        )
        return memory_manager.store_memory(record)

    def search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        from modules.memory.manager import memory_manager
        from modules.memory.models import MemoryNamespace

        memories = memory_manager.search_memory(query, namespace=MemoryNamespace.KNOWLEDGE, limit=limit)
        return [
            {
                "id": m.id,
                "title": getattr(m, "entity_name", m.content[:50]),
                "source_type": getattr(m, "category", "knowledge"),
                "url": getattr(m, "url", ""),
                "content_body": m.content,
                "tags": ",".join(m.tags)
            }
            for m in memories
        ]

class LoggerRepository:
    def log(self, job_id: str | None, step_name: str, status: str, message: str, screenshot_path: str | None = None):
        with db_client.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO execution_logs (job_id, step_name, status, message, screenshot_path)
                VALUES (?, ?, ?, ?, ?)
                """,
                (job_id, step_name, status, message, screenshot_path)
            )
            conn.commit()

content_repo = ContentRepository()
knowledge_repo = KnowledgeRepository()
logger_repo = LoggerRepository()

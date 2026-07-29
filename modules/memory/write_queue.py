"""SQLite async write queue module for AI Content OS.

Prevents database locked errors by wrapping SQLite write operations in an asyncio.Lock
and executing BEGIN IMMEDIATE transactions.
"""

import asyncio
import sqlite3
from collections.abc import Callable
from typing import Any

from loguru import logger

from config.settings import settings


class AsyncWriteQueue:
    """Centralized asynchronous write queue for SQLite to prevent lock contention."""

    def __init__(self, db_path: str = str(settings.DB_PATH)):
        self.db_path: str = db_path
        self._lock: asyncio.Lock = asyncio.Lock()

    async def execute_write(self, write_func: Callable[[sqlite3.Connection], Any]) -> Any:
        """Executes write operation inside a thread lock using BEGIN IMMEDIATE transaction.

        Args:
            write_func: Callable accepting an active sqlite3.Connection.

        Returns:
            Any: Result of the write_func callback execution.
        """
        async with self._lock:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self._run_transaction, write_func)

    def _run_transaction(self, write_func: Callable[[sqlite3.Connection], Any]) -> Any:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA foreign_keys=ON;")
            conn.execute("BEGIN IMMEDIATE;")
            result = write_func(conn)
            conn.commit()
            return result
        except Exception as e:
            conn.rollback()
            logger.error(f"SQLite write transaction failed: {e}")
            raise e
        finally:
            conn.close()

async_write_queue = AsyncWriteQueue()

"""SQLite database client module for AI Content OS.

Provides thread-safe SQLite connection management with Write-Ahead Logging (WAL) mode.
"""

import sqlite3
from pathlib import Path

from loguru import logger

from config.settings import settings


class DatabaseClient:
    """Manages thread-safe SQLite connections and schema initialization."""

    def __init__(self, db_path: Path = settings.DB_PATH):
        self.db_path: Path = db_path
        self._init_db()

    def get_connection(self) -> sqlite3.Connection:
        """Returns a configured SQLite connection in WAL mode."""
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        return conn

    def _init_db(self) -> None:
        """Executes schema DDL script if database table structures are missing."""
        schema_path = settings.BASE_DIR / "db" / "schema.sql"
        if not schema_path.exists():
            logger.error(f"Schema DDL file missing at '{schema_path}'")
            return

        with open(schema_path, encoding="utf-8") as f:
            schema_sql = f.read()

        with self.get_connection() as conn:
            conn.executescript(schema_sql)
            conn.commit()
        logger.info(f"SQLite Database initialized at '{self.db_path}' (WAL mode active).")

db_client = DatabaseClient()

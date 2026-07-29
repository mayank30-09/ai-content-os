import logging
import sqlite3
from pathlib import Path

from config.settings import settings

logger = logging.getLogger("AIContentOS.DBClient")

class DatabaseClient:
    def __init__(self, db_path: Path = settings.DB_PATH):
        self.db_path = db_path
        self._init_db()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        # Enable WAL mode for high concurrency
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        return conn

    def _init_db(self):
        schema_path = settings.BASE_DIR / "db" / "schema.sql"
        if not schema_path.exists():
            logger.error(f"Schema file not found at {schema_path}")
            return

        with open(schema_path, encoding="utf-8") as f:
            schema_sql = f.read()

        with self.get_connection() as conn:
            conn.executescript(schema_sql)
            conn.commit()
        logger.info(f"Database initialized at {self.db_path} (WAL mode active)")

db_client = DatabaseClient()

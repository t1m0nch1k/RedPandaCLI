from __future__ import annotations

import sqlite3
import time
from pathlib import Path

from aios.config.settings import DB_FILE

SCHEMA = """
CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    created_at REAL NOT NULL,
    provider TEXT,
    model TEXT
);

CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at REAL NOT NULL,
    duration_ms REAL DEFAULT 0,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
);
"""


class HistoryStore:
    def __init__(self, db_path: Path = DB_FILE) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(SCHEMA)

    def ensure_conversation(self, conversation_id: str, provider: str, model: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO conversations (id, created_at, provider, model) VALUES (?, ?, ?, ?)",
                (conversation_id, time.time(), provider, model),
            )

    def add_message(
        self,
        conversation_id: str,
        message_id: str,
        role: str,
        content: str,
        duration_ms: float = 0.0,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO messages (id, conversation_id, role, content, created_at, duration_ms) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (message_id, conversation_id, role, content, time.time(), duration_ms),
            )

    def recent_conversations(self, limit: int = 20) -> list[sqlite3.Row]:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM conversations ORDER BY created_at DESC LIMIT ?",
                (limit,),
            )
            return cursor.fetchall()

    def messages_for(self, conversation_id: str) -> list[sqlite3.Row]:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at ASC",
                (conversation_id,),
            )
            return cursor.fetchall()


history_store = HistoryStore()

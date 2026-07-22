import json
import logging
import sqlite3
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

class LongTermMemory:
    """
    LongTermMemory provides a persistent SQLite-based knowledge base for the agent.
    It uses FTS5 for full-text search capabilities over facts, events, and insights.
    """
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create main table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
                    updated_at  TEXT,
                    category    TEXT NOT NULL,
                    content     TEXT NOT NULL,
                    metadata    TEXT,
                    importance  INTEGER DEFAULT 5,
                    ttl         TEXT,
                    embedding   BLOB
                )
            """)
            
            # Create indices
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_memories_category ON memories(category)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_memories_importance ON memories(importance DESC)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_memories_created ON memories(created_at DESC)")
            
            # Create FTS5 virtual table
            cursor.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
                    content,
                    metadata,
                    content='memories',
                    content_rowid='id'
                )
            """)
            
            # Create triggers to keep FTS synchronized
            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
                    INSERT INTO memories_fts(rowid, content, metadata)
                    VALUES (new.id, new.content, new.metadata);
                END;
            """)
            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
                    INSERT INTO memories_fts(memories_fts, rowid, content, metadata)
                    VALUES ('delete', old.id, old.content, old.metadata);
                END;
            """)
            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS memories_au AFTER UPDATE ON memories BEGIN
                    INSERT INTO memories_fts(memories_fts, rowid, content, metadata)
                    VALUES ('delete', old.id, old.content, old.metadata);
                    INSERT INTO memories_fts(rowid, content, metadata)
                    VALUES (new.id, new.content, new.metadata);
                END;
            """)
            
            conn.commit()

    def store(self, content: str, category: str = "fact", importance: int = 5, tags: list[str] | None = None) -> int:
        """Stores a new memory."""
        meta = json.dumps({"tags": tags or []})
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO memories (category, content, metadata, importance) VALUES (?, ?, ?, ?)",
                (category, content, meta, importance)
            )
            return cursor.lastrowid or 0

    def recall(self, query: str, limit: int = 10, category: str | None = None) -> list[dict[str, Any]]:
        """Searches memories using FTS5."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            sql = """
                SELECT m.id, m.created_at, m.category, m.content, m.metadata, m.importance
                FROM memories m
                JOIN memories_fts f ON m.id = f.rowid
                WHERE memories_fts MATCH ?
            """
            params = [query]
            if category:
                sql += " AND m.category = ?"
                params.append(category)
                
            sql += " ORDER BY rank LIMIT ?"
            params.append(limit)
            
            cursor.execute(sql, params)
            return [dict(row) for row in cursor.fetchall()]

    def recall_recent(self, limit: int = 10, category: str | None = None) -> list[dict[str, Any]]:
        """Gets most recent memories."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            sql = "SELECT * FROM memories"
            params = []
            if category:
                sql += " WHERE category = ?"
                params.append(category)
                
            sql += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(sql, params)
            return [dict(row) for row in cursor.fetchall()]

    def forget(self, memory_id: int) -> bool:
        """Deletes a memory by ID."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
            return cursor.rowcount > 0

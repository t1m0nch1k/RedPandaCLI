import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

class CalendarEngine:
    """
    CalendarEngine manages calendar events for the user and the agent.
    """
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS calendar_events (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    title        TEXT NOT NULL,
                    description  TEXT,
                    start_time   TEXT NOT NULL,
                    end_time     TEXT,
                    all_day      BOOLEAN DEFAULT 0,
                    recurrence   TEXT,
                    reminder_min INTEGER DEFAULT 15,
                    category     TEXT DEFAULT 'general',
                    color        TEXT DEFAULT '#6366f1',
                    completed    BOOLEAN DEFAULT 0,
                    created_by   TEXT DEFAULT 'user',
                    metadata     TEXT
                )
            """)
            
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_cal_start ON calendar_events(start_time)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_cal_category ON calendar_events(category)")
            
            conn.commit()

    def add_event(self, title: str, start_time: str, end_time: str | None = None, description: str = "",
                  all_day: bool = False, category: str = "general") -> int:
        """Adds a calendar event. start_time and end_time must be ISO 8601 strings."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO calendar_events 
                   (title, description, start_time, end_time, all_day, category) 
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (title, description, start_time, end_time, all_day, category)
            )
            return cursor.lastrowid or 0

    def get_events(self, date_from: str, date_to: str) -> list[dict[str, Any]]:
        """Gets events within a date range."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT * FROM calendar_events WHERE start_time >= ? AND start_time <= ? ORDER BY start_time",
                (date_from, date_to)
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_upcoming(self, hours: int = 24) -> list[dict[str, Any]]:
        """Gets upcoming events."""
        now = datetime.utcnow()
        until = now + timedelta(hours=hours)
        return self.get_events(now.isoformat(), until.isoformat())

    def update_event(self, event_id: int, **kwargs) -> bool:
        """Updates an event."""
        if not kwargs:
            return False
            
        set_clause = ", ".join([f"{k} = ?" for k in kwargs.keys()])
        values = list(kwargs.values())
        values.append(event_id)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(f"UPDATE calendar_events SET {set_clause} WHERE id = ?", tuple(values))
            return cursor.rowcount > 0

    def delete_event(self, event_id: int) -> bool:
        """Deletes an event."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM calendar_events WHERE id = ?", (event_id,))
            return cursor.rowcount > 0

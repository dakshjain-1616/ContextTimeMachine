"""SQLite storage for sessions."""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from context_time_machine.server.session.models import Session


class SessionStorage:
    """Store and retrieve sessions from SQLite."""

    def __init__(self, db_path: str = "sessions.db"):
        """Initialize storage.

        Args:
            db_path: Path to SQLite database
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    source_format TEXT,
                    model_id TEXT,
                    created_at TEXT,
                    turn_count INTEGER,
                    metadata TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions_data (
                    session_id TEXT PRIMARY KEY,
                    data TEXT,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                )
            """)
            conn.commit()

    def save(self, session: Session) -> None:
        """Save a session to storage.

        Args:
            session: Session to save
        """
        with sqlite3.connect(self.db_path) as conn:
            # Save session metadata
            conn.execute("""
                INSERT OR REPLACE INTO sessions
                (session_id, source_format, model_id, created_at, turn_count, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                session.session_id,
                session.source_format,
                session.model_id,
                session.created_at.isoformat(),
                len(session.turns),
                json.dumps(session.metadata),
            ))

            # Save session data as JSON
            session_json = session.model_dump_json()
            conn.execute("""
                INSERT OR REPLACE INTO sessions_data (session_id, data)
                VALUES (?, ?)
            """, (session.session_id, session_json))

            conn.commit()

    def load(self, session_id: str) -> Optional[Session]:
        """Load a session from storage.

        Args:
            session_id: ID of session to load

        Returns:
            Session object or None if not found
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT data FROM sessions_data WHERE session_id = ?",
                (session_id,),
            )
            row = cursor.fetchone()

            if not row:
                return None

            return Session.model_validate_json(row[0])

    def list_sessions(self) -> List[Dict[str, any]]:
        """List all stored sessions.

        Returns:
            List of session metadata dicts
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT session_id, source_format, model_id, created_at, turn_count
                FROM sessions
                ORDER BY created_at DESC
            """)
            return [dict(row) for row in cursor.fetchall()]

    def delete(self, session_id: str) -> bool:
        """Delete a session from storage.

        Args:
            session_id: ID of session to delete

        Returns:
            True if deleted, False if not found
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM sessions WHERE session_id = ?",
                (session_id,),
            )
            conn.execute(
                "DELETE FROM sessions_data WHERE session_id = ?",
                (session_id,),
            )
            conn.commit()
            return cursor.rowcount > 0

    def clear(self) -> None:
        """Clear all sessions from storage."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM sessions")
            conn.execute("DELETE FROM sessions_data")
            conn.commit()

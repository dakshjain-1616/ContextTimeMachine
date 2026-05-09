"""Load sessions from multiple formats."""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import tiktoken

from context_time_machine.server.session.models import (
    MessageRole,
    Session,
    SessionMessage,
    SessionTurn,
)


class SessionLoader:
    """Load sessions from multiple formats."""

    def __init__(self):
        """Initialize the loader."""
        self.encoding = tiktoken.get_encoding("cl100k_base")

    def load(self, source: Union[str, Path, Dict[str, Any]]) -> Session:
        """Load a session from a file or dict.

        Supports:
        - LiveContext SQLite export
        - LangSmith export JSON
        - Generic JSON format
        - Raw conversation JSON
        """
        if isinstance(source, dict):
            return self._load_from_dict(source)

        source_path = Path(source)
        if not source_path.exists():
            raise FileNotFoundError(f"Session source not found: {source}")

        if source_path.suffix == ".db" or source_path.suffix == ".sqlite":
            return self._load_from_livecontext(source_path)
        elif source_path.suffix == ".json":
            with open(source_path) as f:
                data = json.load(f)
            return self._load_from_dict(data)
        else:
            raise ValueError(f"Unsupported file format: {source_path.suffix}")

    def _load_from_livecontext(self, db_path: Path) -> Session:
        """Load from LiveContext SQLite export."""
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            # Get snapshots
            cursor.execute(
                """
                SELECT snapshot_id, session_id, turn_number, timestamp,
                       model_id, total_tokens FROM snapshots
                ORDER BY turn_number
                """
            )
            snapshots = cursor.fetchall()

            if not snapshots:
                raise ValueError("No snapshots found in LiveContext database")

            session_id = snapshots[0]["session_id"]
            turns = []

            for snap in snapshots:
                # Get messages for this snapshot
                cursor.execute(
                    """
                    SELECT role, content, token_count FROM snapshot_messages
                    WHERE snapshot_id = ?
                    """,
                    (snap["snapshot_id"],),
                )
                messages = cursor.fetchall()

                session_messages = [
                    SessionMessage(
                        role=MessageRole(msg["role"]),
                        content=msg["content"],
                        token_count=msg["token_count"],
                    )
                    for msg in messages
                ]

                turn = SessionTurn(
                    turn_number=snap["turn_number"],
                    messages=session_messages,
                    model_id=snap["model_id"],
                    timestamp=datetime.fromisoformat(snap["timestamp"]),
                    total_tokens=snap["total_tokens"],
                )
                turns.append(turn)

            return Session(
                session_id=session_id,
                source_format="livecontext",
                turns=turns,
                model_id=snapshots[0]["model_id"],
                metadata={"source": str(db_path)},
            )
        finally:
            conn.close()

    def _load_from_dict(self, data: Dict[str, Any]) -> Session:
        """Load from generic JSON format or raw conversation."""
        # Auto-detect format
        if "turns" in data:
            return self._load_generic_json(data)
        elif "messages" in data:
            # Raw conversation - single turn
            return self._load_raw_conversation(data)
        elif isinstance(data, list):
            # List of turns
            return self._load_generic_json({"turns": data})
        else:
            raise ValueError("Unrecognized JSON format")

    def _load_generic_json(self, data: Dict[str, Any]) -> Session:
        """Load from generic JSON format (list of turns)."""
        turns_data = data.get("turns", [])
        if not turns_data:
            raise ValueError("No turns found in JSON")

        turns = []
        for turn_data in turns_data:
            messages = turn_data.get("messages", [])
            session_messages = [
                SessionMessage(
                    role=MessageRole(msg.get("role", "user")),
                    content=msg.get("content", ""),
                    token_count=msg.get("token_count", len(msg.get("content", "").split())),
                )
                for msg in messages
            ]

            turn = SessionTurn(
                turn_number=turn_data.get("turn", len(turns)),
                messages=session_messages,
                model_id=turn_data.get("model_id", "unknown"),
                timestamp=datetime.fromisoformat(turn_data["timestamp"])
                if "timestamp" in turn_data
                else datetime.utcnow(),
                agent_name=turn_data.get("agent_name"),
                total_tokens=turn_data.get("total_tokens", sum(m.token_count for m in session_messages)),
            )
            turns.append(turn)

        return Session(
            source_format="generic_json",
            turns=turns,
            model_id=data.get("model_id", "unknown"),
            metadata=data.get("metadata", {}),
        )

    def _load_raw_conversation(self, data: Dict[str, Any]) -> Session:
        """Load from raw conversation (single messages array)."""
        messages_data = data.get("messages", [])
        session_messages = [
            SessionMessage(
                role=MessageRole(msg.get("role", "user")),
                content=msg.get("content", ""),
                token_count=msg.get("token_count", len(msg.get("content", "").split())),
            )
            for msg in messages_data
        ]

        turn = SessionTurn(
            turn_number=0,
            messages=session_messages,
            model_id=data.get("model_id", "unknown"),
            total_tokens=sum(m.token_count for m in session_messages),
        )

        return Session(
            source_format="raw_conversation",
            turns=[turn],
            model_id=data.get("model_id", "unknown"),
            metadata=data.get("metadata", {}),
        )

    def count_tokens(self, text: str) -> int:
        """Count tokens in text using tiktoken."""
        try:
            return len(self.encoding.encode(text))
        except Exception:
            # Fallback to word count
            return len(text.split())

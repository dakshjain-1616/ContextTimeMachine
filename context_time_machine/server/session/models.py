"""Models for session loading and reconstruction."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class MessageRole(str, Enum):
    """Role of a message in the context."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"
    TOOL_RESULT = "tool_result"


class SessionMessage(BaseModel):
    """A single message in a session turn."""
    role: MessageRole
    content: str
    token_count: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SessionTurn(BaseModel):
    """A single turn in a session."""
    turn_number: int
    messages: List[SessionMessage]
    model_id: str = "unknown"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    agent_name: Optional[str] = None
    total_tokens: int = 0


class Session(BaseModel):
    """A complete session with all turns."""
    session_id: str = Field(default_factory=lambda: str(uuid4()))
    source_format: str  # "livecontext", "langsmith", "generic_json", "raw_conversation"
    turns: List[SessionTurn]
    model_id: str = "unknown"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @property
    def turn_count(self) -> int:
        """Total number of turns."""
        return len(self.turns)

    @property
    def max_tokens(self) -> int:
        """Maximum tokens across all turns."""
        return max((turn.total_tokens for turn in self.turns), default=0)


class ReconstructedContext(BaseModel):
    """Reconstructed context window at a specific turn."""
    session_id: str
    turn_number: int
    messages: List[SessionMessage]
    total_tokens: int
    model_limit: int = 128000
    distance_to_limit: int  # tokens remaining

    @property
    def utilization_percent(self) -> float:
        """Context window utilization percentage."""
        return (self.total_tokens / self.model_limit) * 100 if self.model_limit else 0

    @property
    def components(self) -> Dict[str, int]:
        """Token breakdown by component type."""
        breakdown: Dict[str, int] = {
            "system": 0,
            "history": 0,
            "tool_results": 0,
            "current": 0,
        }
        for msg in self.messages:
            if msg.role == MessageRole.SYSTEM:
                breakdown["system"] += msg.token_count
            elif msg.role == MessageRole.TOOL_RESULT:
                breakdown["tool_results"] += msg.token_count
            elif msg.role == MessageRole.ASSISTANT:
                breakdown["current"] += msg.token_count
            else:
                breakdown["history"] += msg.token_count
        return breakdown

"""Reconstruct context window at specific turns."""

from typing import Dict, List

import tiktoken

from context_time_machine.server.session.models import (
    ReconstructedContext,
    Session,
    SessionMessage,
    MessageRole,
)


class EvictionSimulator:
    """Simulate eviction for different model architectures."""

    MODEL_LIMITS: Dict[str, int] = {
        "gemma-2b": 8192,
        "gemma-7b": 8192,
        "gemma-4-e2b": 262144,
        "qwen3-8b": 32768,
        "deepseek-v4": 1000000,
        "deepseek-v4-flash": 1000000,
        "gpt-4": 8192,
        "gpt-4-turbo": 128000,
        "gpt-5": 131072,
        "claude-3-sonnet": 204800,
        "claude-3-opus": 204800,
        "llama-2-70b": 4096,
    }

    EVICTION_STRATEGIES: Dict[str, str] = {
        "gemma-4": "local-global",  # local-global attention, older turns deprioritized
        "qwen": "left-truncate",    # oldest messages evicted first
        "deepseek": "sliding-window",  # recent bias
        "gpt": "left-truncate",
        "claude": "left-truncate",
    }

    @classmethod
    def get_model_limit(cls, model_id: str) -> int:
        """Get context window limit for a model."""
        model_lower = model_id.lower()

        # Exact match
        if model_lower in cls.MODEL_LIMITS:
            return cls.MODEL_LIMITS[model_lower]

        # Fuzzy match
        for key, limit in cls.MODEL_LIMITS.items():
            if key in model_lower or model_lower in key:
                return limit

        # Default
        return 128000

    @classmethod
    def get_strategy(cls, model_id: str) -> str:
        """Get eviction strategy for a model."""
        model_lower = model_id.lower()
        for key, strategy in cls.EVICTION_STRATEGIES.items():
            if key in model_lower:
                return strategy
        return "left-truncate"


class ContextReconstructor:
    """Reconstruct context window at any turn."""

    def __init__(self):
        """Initialize the reconstructor."""
        self.encoding = tiktoken.get_encoding("cl100k_base")

    def reconstruct(self, session: Session, turn_number: int) -> ReconstructedContext:
        """Reconstruct context window at a specific turn.

        Args:
            session: The session to reconstruct
            turn_number: The turn to reconstruct (0-indexed)

        Returns:
            ReconstructedContext with messages and token info
        """
        if turn_number < 0 or turn_number >= len(session.turns):
            raise ValueError(f"Invalid turn number: {turn_number}")

        # Get all messages up to and including this turn
        all_messages: List[SessionMessage] = []
        for i in range(turn_number + 1):
            all_messages.extend(session.turns[i].messages)

        model_limit = EvictionSimulator.get_model_limit(session.model_id)
        total_tokens = self._count_messages_tokens(all_messages)

        # If we exceed the limit, simulate eviction
        if total_tokens > model_limit:
            strategy = EvictionSimulator.get_strategy(session.model_id)
            all_messages = self._apply_eviction(
                all_messages, model_limit, strategy
            )
            total_tokens = self._count_messages_tokens(all_messages)

        return ReconstructedContext(
            session_id=session.session_id,
            turn_number=turn_number,
            messages=all_messages,
            total_tokens=total_tokens,
            model_limit=model_limit,
            distance_to_limit=max(0, model_limit - total_tokens),
        )

    def _count_messages_tokens(self, messages: List[SessionMessage]) -> int:
        """Count total tokens in messages."""
        total = 0
        for msg in messages:
            if msg.token_count > 0:
                total += msg.token_count
            else:
                # Count tokens if not already present
                try:
                    total += len(self.encoding.encode(msg.content))
                except Exception:
                    total += len(msg.content.split())
        return total

    def _apply_eviction(
        self, messages: List[SessionMessage], limit: int, strategy: str
    ) -> List[SessionMessage]:
        """Apply eviction strategy to fit within limit."""
        # Protect system messages - never evict them
        system_messages = [m for m in messages if m.role == MessageRole.SYSTEM]
        other_messages = [m for m in messages if m.role != MessageRole.SYSTEM]

        system_tokens = self._count_messages_tokens(system_messages)

        if strategy == "left-truncate":
            # Remove messages from the beginning until we fit
            while other_messages and (system_tokens + self._count_messages_tokens(other_messages)) > limit:
                other_messages.pop(0)

        elif strategy == "sliding-window":
            # Keep recent messages and some older ones
            total_budget = limit - system_tokens
            recent_idx = len(other_messages) - 1
            window_messages = []
            window_tokens = 0

            # Add from the end backwards
            while recent_idx >= 0 and window_tokens < total_budget:
                msg = other_messages[recent_idx]
                msg_tokens = msg.token_count or len(msg.content.split())
                if window_tokens + msg_tokens <= total_budget:
                    window_messages.insert(0, msg)
                    window_tokens += msg_tokens
                recent_idx -= 1

            other_messages = window_messages

        elif strategy == "local-global":
            # Keep system messages and recent messages, sample from middle
            total_budget = limit - system_tokens

            # Keep recent 30% of other messages
            keep_recent = max(1, len(other_messages) // 3)
            recent_messages = other_messages[-keep_recent:]

            # Try to fit remaining budget with older messages
            remaining_budget = total_budget - self._count_messages_tokens(recent_messages)
            older_messages = other_messages[:-keep_recent]

            # Sample from older messages
            if older_messages:
                sample_interval = max(1, len(older_messages) // max(1, remaining_budget // 100))
                sampled = older_messages[::sample_interval]
                other_messages = sampled + recent_messages
            else:
                other_messages = recent_messages

        return system_messages + other_messages

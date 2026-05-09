"""Analyze token usage across session turns."""

from dataclasses import dataclass
from typing import Dict, List

from context_time_machine.server.session.models import (
    MessageRole,
    Session,
)
from context_time_machine.server.session.reconstructor import ContextReconstructor


@dataclass
class TokenStats:
    """Token statistics for a single turn."""
    turn_number: int
    total_tokens: int
    system_tokens: int
    history_tokens: int
    tool_results_tokens: int
    current_turn_tokens: int
    proximity_to_limit: float  # percentage
    tokens_added_this_turn: int


@dataclass
class SessionTokenProfile:
    """Complete token profile for a session."""
    session_id: str
    per_turn_stats: List[TokenStats]
    peak_turn: int
    peak_tokens: int
    eviction_turns: List[int]
    average_growth_rate: float
    max_tokens: int


class TokenAnalyzer:
    """Analyze token usage across turns."""

    def __init__(self):
        """Initialize the analyzer."""
        self.reconstructor = ContextReconstructor()

    def analyze_session(self, session: Session) -> SessionTokenProfile:
        """Analyze token usage for entire session.

        Args:
            session: Session to analyze

        Returns:
            SessionTokenProfile with per-turn stats
        """
        per_turn_stats: List[TokenStats] = []
        peak_turn = 0
        peak_tokens = 0
        eviction_turns: List[int] = []
        prev_history_tokens = 0

        for turn_num in range(len(session.turns)):
            reconstructed = self.reconstructor.reconstruct(session, turn_num)
            components = reconstructed.components

            system_tokens = components["system"]
            history_tokens = components["history"]
            tool_results_tokens = components["tool_results"]
            current_turn_tokens = components["current"]

            proximity = reconstructed.utilization_percent
            tokens_added = (
                reconstructed.total_tokens
                - (per_turn_stats[turn_num - 1].total_tokens if turn_num > 0 else 0)
            )

            stats = TokenStats(
                turn_number=turn_num,
                total_tokens=reconstructed.total_tokens,
                system_tokens=system_tokens,
                history_tokens=history_tokens,
                tool_results_tokens=tool_results_tokens,
                current_turn_tokens=current_turn_tokens,
                proximity_to_limit=proximity,
                tokens_added_this_turn=tokens_added,
            )
            per_turn_stats.append(stats)

            # Track peak
            if reconstructed.total_tokens > peak_tokens:
                peak_tokens = reconstructed.total_tokens
                peak_turn = turn_num

            # Detect eviction: history tokens decrease
            if turn_num > 0 and history_tokens < prev_history_tokens:
                eviction_turns.append(turn_num)

            prev_history_tokens = history_tokens

        # Calculate average growth rate
        if len(per_turn_stats) > 1:
            total_growth = per_turn_stats[-1].total_tokens - per_turn_stats[0].total_tokens
            avg_growth = total_growth / (len(per_turn_stats) - 1)
        else:
            avg_growth = 0.0

        return SessionTokenProfile(
            session_id=session.session_id,
            per_turn_stats=per_turn_stats,
            peak_turn=peak_turn,
            peak_tokens=peak_tokens,
            eviction_turns=eviction_turns,
            average_growth_rate=avg_growth,
            max_tokens=peak_tokens,
        )

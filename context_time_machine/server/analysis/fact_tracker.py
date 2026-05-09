"""Track fact presence across session turns."""

from dataclasses import dataclass
from typing import List, Optional

from context_time_machine.server.analysis.embedder import EmbeddingService
from context_time_machine.server.session.models import Session
from context_time_machine.server.session.reconstructor import ContextReconstructor


@dataclass
class PresenceEntry:
    """Fact presence at a specific turn."""
    turn_number: int
    is_present: bool
    presence_score: float  # 0-1, based on cosine similarity
    best_matching_message: str  # Preview of best match
    message_position: int  # Position from top of context


@dataclass
class FactTrackResult:
    """Results of fact tracking across a session."""
    session_id: str
    fact_text: str
    presence_entries: List[PresenceEntry]
    first_appeared_turn: Optional[int]
    last_present_turn: Optional[int]
    disappeared_at_turn: Optional[int]


class FactTracker:
    """Track presence of facts across turns."""

    def __init__(self, similarity_threshold: float = 0.75):
        """Initialize the fact tracker.

        Args:
            similarity_threshold: Minimum similarity to consider fact present
        """
        self.embedder = EmbeddingService()
        self.reconstructor = ContextReconstructor()
        self.threshold = similarity_threshold

    def track(self, session: Session, fact_text: str) -> FactTrackResult:
        """Track a fact across all turns in a session.

        Args:
            session: Session to track
            fact_text: Fact text to search for

        Returns:
            FactTrackResult with presence at each turn
        """
        fact_embedding = self.embedder.embed(fact_text)
        presence_entries: List[PresenceEntry] = []

        first_appeared = None
        last_present = None
        disappeared_at = None

        for turn_num in range(len(session.turns)):
            reconstructed = self.reconstructor.reconstruct(session, turn_num)

            # Embed all messages in context
            message_embeddings = [
                self.embedder.embed(msg.content) for msg in reconstructed.messages
            ]

            # Find best match
            if message_embeddings:
                best_idx, similarity = self.embedder.find_most_similar(
                    fact_embedding, message_embeddings
                )
                is_present = similarity > self.threshold
                best_msg = (
                    reconstructed.messages[best_idx].content[:100]
                    if best_idx >= 0
                    else ""
                )
            else:
                best_idx = -1
                similarity = 0.0
                is_present = False
                best_msg = ""

            entry = PresenceEntry(
                turn_number=turn_num,
                is_present=is_present,
                presence_score=similarity,
                best_matching_message=best_msg,
                message_position=best_idx,
            )
            presence_entries.append(entry)

            # Track transitions
            if is_present:
                if first_appeared is None:
                    first_appeared = turn_num
                last_present = turn_num
            elif last_present is not None and disappeared_at is None:
                # Fact was present before, now it's gone
                disappeared_at = turn_num

        return FactTrackResult(
            session_id=session.session_id,
            fact_text=fact_text,
            presence_entries=presence_entries,
            first_appeared_turn=first_appeared,
            last_present_turn=last_present,
            disappeared_at_turn=disappeared_at,
        )

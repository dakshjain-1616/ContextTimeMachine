"""Find divergence points between two sessions."""

from dataclasses import dataclass
from typing import List, Optional

import numpy as np

from context_time_machine.server.analysis.embedder import EmbeddingService
from context_time_machine.server.session.models import Session, SessionMessage
from context_time_machine.server.session.reconstructor import ContextReconstructor


@dataclass
class MessageDiff:
    """Differences between message sets."""
    added_in_a: List[str]
    added_in_b: List[str]
    modified: List[tuple[str, str]]  # (original, modified)


@dataclass
class DivergenceResult:
    """Results of divergence analysis."""
    session_a_id: str
    session_b_id: str
    divergence_turn: Optional[int]
    similarity_scores: List[float]  # Per-turn similarity
    message_diff: Optional[MessageDiff]
    summary: str


class DivergenceFinder:
    """Find divergence points between two sessions."""

    def __init__(self, divergence_threshold: float = 0.85):
        """Initialize divergence finder.

        Args:
            divergence_threshold: Similarity threshold below which sessions diverged
        """
        self.embedder = EmbeddingService()
        self.reconstructor = ContextReconstructor()
        self.threshold = divergence_threshold

    def find(self, session_a: Session, session_b: Session) -> DivergenceResult:
        """Find divergence point between two sessions.

        Args:
            session_a: First session
            session_b: Second session

        Returns:
            DivergenceResult with divergence point and analysis
        """
        similarity_scores: List[float] = []
        divergence_turn = None
        message_diff = None

        min_turns = min(len(session_a.turns), len(session_b.turns))

        for turn_num in range(min_turns):
            # Reconstruct contexts
            ctx_a = self.reconstructor.reconstruct(session_a, turn_num)
            ctx_b = self.reconstructor.reconstruct(session_b, turn_num)

            # Compute similarity
            similarity = self._compute_context_similarity(
                ctx_a.messages, ctx_b.messages
            )
            similarity_scores.append(similarity)

            # Check for divergence
            if divergence_turn is None and similarity < self.threshold:
                divergence_turn = turn_num
                message_diff = self._compute_message_diff(
                    ctx_a.messages, ctx_b.messages
                )

        # Generate summary
        if divergence_turn is not None:
            summary = (
                f"Sessions diverged at turn {divergence_turn}. "
                f"Context similarity dropped from "
                f"{similarity_scores[divergence_turn-1]:.2f} to "
                f"{similarity_scores[divergence_turn]:.2f}. "
                f"{len(message_diff.added_in_a) if message_diff else 0} messages added in A, "
                f"{len(message_diff.added_in_b) if message_diff else 0} in B."
            )
        else:
            summary = (
                f"No significant divergence detected across {min_turns} turns. "
                f"Sessions maintained >85% context similarity."
            )

        return DivergenceResult(
            session_a_id=session_a.session_id,
            session_b_id=session_b.session_id,
            divergence_turn=divergence_turn,
            similarity_scores=similarity_scores,
            message_diff=message_diff,
            summary=summary,
        )

    def _compute_context_similarity(
        self, messages_a: List[SessionMessage], messages_b: List[SessionMessage]
    ) -> float:
        """Compute similarity between two context windows."""
        if not messages_a or not messages_b:
            return 0.0

        # Embed all messages
        embeddings_a = [self.embedder.embed(msg.content) for msg in messages_a]
        embeddings_b = [self.embedder.embed(msg.content) for msg in messages_b]

        # Compute average max similarity: for each A message, find max similarity to any B message
        similarities = []
        for emb_a in embeddings_a:
            max_sim = 0.0
            for emb_b in embeddings_b:
                sim = self.embedder.similarity(emb_a, emb_b)
                max_sim = max(max_sim, sim)
            similarities.append(max_sim)

        if not similarities:
            return 0.0

        return float(np.mean(similarities))

    def _compute_message_diff(
        self, messages_a: List[SessionMessage], messages_b: List[SessionMessage]
    ) -> MessageDiff:
        """Compute differences between message sets."""
        contents_a = {msg.content[:50] for msg in messages_a}
        contents_b = {msg.content[:50] for msg in messages_b}

        added_in_a = list(contents_a - contents_b)
        added_in_b = list(contents_b - contents_a)

        return MessageDiff(
            added_in_a=added_in_a,
            added_in_b=added_in_b,
            modified=[],
        )

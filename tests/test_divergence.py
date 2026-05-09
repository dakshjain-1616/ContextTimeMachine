"""Tests for DivergenceFinder."""

import pytest

from context_time_machine.server.analysis.divergence import DivergenceFinder
from context_time_machine.server.session.models import (
    MessageRole,
    Session,
    SessionMessage,
    SessionTurn,
)


@pytest.fixture
def divergence_finder():
    """Create a DivergenceFinder instance."""
    return DivergenceFinder()


@pytest.fixture
def identical_sessions():
    """Create two identical sessions."""
    def make_session():
        turns = [
            SessionTurn(
                turn_number=0,
                messages=[
                    SessionMessage(
                        role=MessageRole.SYSTEM,
                        content="You are helpful.",
                        token_count=3,
                    ),
                    SessionMessage(
                        role=MessageRole.USER,
                        content="What is 2+2?",
                        token_count=4,
                    ),
                ],
                model_id="gpt-4",
                total_tokens=7,
            ),
        ]
        return Session(source_format="test", turns=turns, model_id="gpt-4")

    return make_session(), make_session()


@pytest.fixture
def divergent_sessions():
    """Create two sessions that diverge."""
    session_a = Session(
        source_format="test",
        turns=[
            SessionTurn(
                turn_number=0,
                messages=[
                    SessionMessage(
                        role=MessageRole.SYSTEM,
                        content="You are helpful.",
                        token_count=3,
                    ),
                    SessionMessage(
                        role=MessageRole.USER,
                        content="What is 2+2?",
                        token_count=4,
                    ),
                ],
                model_id="gpt-4",
                total_tokens=7,
            ),
            SessionTurn(
                turn_number=1,
                messages=[
                    SessionMessage(
                        role=MessageRole.SYSTEM,
                        content="You are helpful.",
                        token_count=3,
                    ),
                    SessionMessage(
                        role=MessageRole.USER,
                        content="What is 2+2?",
                        token_count=4,
                    ),
                    SessionMessage(
                        role=MessageRole.ASSISTANT,
                        content="2+2 equals 4.",
                        token_count=4,
                    ),
                ],
                model_id="gpt-4",
                total_tokens=11,
            ),
        ],
        model_id="gpt-4",
    )

    session_b = Session(
        source_format="test",
        turns=[
            SessionTurn(
                turn_number=0,
                messages=[
                    SessionMessage(
                        role=MessageRole.SYSTEM,
                        content="You are helpful.",
                        token_count=3,
                    ),
                    SessionMessage(
                        role=MessageRole.USER,
                        content="What is 2+2?",
                        token_count=4,
                    ),
                ],
                model_id="gpt-4",
                total_tokens=7,
            ),
            SessionTurn(
                turn_number=1,
                messages=[
                    SessionMessage(
                        role=MessageRole.SYSTEM,
                        content="You are helpful.",
                        token_count=3,
                    ),
                    SessionMessage(
                        role=MessageRole.USER,
                        content="What is 2+2?",
                        token_count=4,
                    ),
                    SessionMessage(
                        role=MessageRole.ASSISTANT,
                        content="The answer is 4.",
                        token_count=4,
                    ),
                ],
                model_id="gpt-4",
                total_tokens=11,
            ),
        ],
        model_id="gpt-4",
    )

    return session_a, session_b


def test_divergence_finder_identical_sessions(divergence_finder, identical_sessions):
    """Test divergence on identical sessions."""
    session_a, session_b = identical_sessions
    result = divergence_finder.find(session_a, session_b)

    assert result.session_a_id == session_a.session_id
    assert result.session_b_id == session_b.session_id
    assert len(result.similarity_scores) > 0
    # Similar sessions should have high similarity
    assert all(score > 0.8 for score in result.similarity_scores)


def test_divergence_finder_divergent_sessions(divergence_finder, divergent_sessions):
    """Test divergence on different sessions."""
    session_a, session_b = divergent_sessions
    result = divergence_finder.find(session_a, session_b)

    assert len(result.similarity_scores) > 0
    # At least one similarity score should be recorded
    assert all(0.0 <= score <= 1.0 for score in result.similarity_scores)


def test_divergence_finder_similarity_scores_length(divergence_finder, divergent_sessions):
    """Test that similarity scores has one per turn."""
    session_a, session_b = divergent_sessions
    result = divergence_finder.find(session_a, session_b)

    min_turns = min(len(session_a.turns), len(session_b.turns))
    assert len(result.similarity_scores) == min_turns


def test_divergence_finder_message_diff(divergence_finder, divergent_sessions):
    """Test message diff calculation."""
    session_a, session_b = divergent_sessions
    result = divergence_finder.find(session_a, session_b)

    # Message diff is only created when divergence is detected
    if result.divergence_turn is not None:
        assert result.message_diff is not None


def test_divergence_finder_summary(divergence_finder, divergent_sessions):
    """Test that summary is generated."""
    session_a, session_b = divergent_sessions
    result = divergence_finder.find(session_a, session_b)

    assert result.summary is not None
    assert len(result.summary) > 0


def test_divergence_finder_different_lengths(divergence_finder):
    """Test divergence with different session lengths."""
    session_a = Session(
        source_format="test",
        turns=[
            SessionTurn(
                turn_number=0,
                messages=[
                    SessionMessage(
                        role=MessageRole.USER,
                        content="Hello",
                        token_count=1,
                    ),
                ],
                model_id="gpt-4",
                total_tokens=1,
            ),
            SessionTurn(
                turn_number=1,
                messages=[
                    SessionMessage(
                        role=MessageRole.ASSISTANT,
                        content="Hi",
                        token_count=1,
                    ),
                ],
                model_id="gpt-4",
                total_tokens=1,
            ),
            SessionTurn(
                turn_number=2,
                messages=[
                    SessionMessage(
                        role=MessageRole.USER,
                        content="How are you?",
                        token_count=3,
                    ),
                ],
                model_id="gpt-4",
                total_tokens=3,
            ),
        ],
        model_id="gpt-4",
    )

    session_b = Session(
        source_format="test",
        turns=[
            SessionTurn(
                turn_number=0,
                messages=[
                    SessionMessage(
                        role=MessageRole.USER,
                        content="Hello",
                        token_count=1,
                    ),
                ],
                model_id="gpt-4",
                total_tokens=1,
            ),
        ],
        model_id="gpt-4",
    )

    result = divergence_finder.find(session_a, session_b)

    # Should only analyze up to min length
    assert len(result.similarity_scores) == 1


def test_divergence_finder_threshold(divergence_finder):
    """Test custom divergence threshold."""
    finder_loose = DivergenceFinder(divergence_threshold=0.7)
    finder_strict = DivergenceFinder(divergence_threshold=0.95)

    assert finder_loose.threshold == 0.7
    assert finder_strict.threshold == 0.95

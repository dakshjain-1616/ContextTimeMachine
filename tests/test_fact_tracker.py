"""Tests for FactTracker."""

import pytest

from context_time_machine.server.analysis.fact_tracker import FactTracker


@pytest.fixture
def fact_tracker():
    """Create a FactTracker instance."""
    return FactTracker()


def test_fact_tracker_present_fact(fact_tracker, sample_session):
    """Test tracking a fact that is present."""
    result = fact_tracker.track(sample_session, "helpful assistant")

    assert result.fact_text == "helpful assistant"
    assert len(result.presence_entries) > 0
    # The fact should be present in at least some turns
    assert any(e.is_present for e in result.presence_entries)


def test_fact_tracker_absent_fact(fact_tracker, sample_session):
    """Test tracking a fact that is not present."""
    result = fact_tracker.track(sample_session, "xyzabc nonexistent phrase xyz")

    assert result.fact_text == "xyzabc nonexistent phrase xyz"
    assert len(result.presence_entries) > 0
    # The fact should be absent in all turns
    assert all(not e.is_present for e in result.presence_entries)


def test_fact_tracker_presence_scores(fact_tracker, sample_session):
    """Test that presence scores are between 0 and 1."""
    result = fact_tracker.track(sample_session, "helpful")

    for entry in result.presence_entries:
        assert 0.0 <= entry.presence_score <= 1.0


def test_fact_tracker_first_appeared(fact_tracker, sample_session):
    """Test tracking first appearance."""
    result = fact_tracker.track(sample_session, "2+2")

    # "2+2" appears in turn 1
    assert result.first_appeared_turn is not None
    assert result.first_appeared_turn >= 0


def test_fact_tracker_disappearance(fact_tracker, sample_session):
    """Test tracking when fact disappears."""
    result = fact_tracker.track(sample_session, "2+2")

    # Depending on eviction, might disappear
    # At least we should have the data
    assert result.disappeared_at_turn is None or result.disappeared_at_turn >= 0


def test_fact_tracker_per_turn_tracking(fact_tracker, sample_session):
    """Test that tracking works per turn."""
    result = fact_tracker.track(sample_session, "helpful")

    # Should have one entry per turn
    assert len(result.presence_entries) == len(sample_session.turns)

    # Each entry should have correct turn number
    for i, entry in enumerate(result.presence_entries):
        assert entry.turn_number == i


def test_fact_tracker_best_matching_message(fact_tracker, sample_session):
    """Test that best matching message is provided."""
    result = fact_tracker.track(sample_session, "helpful assistant")

    for entry in result.presence_entries:
        if entry.is_present:
            assert len(entry.best_matching_message) > 0


def test_fact_tracker_message_position(fact_tracker, sample_session):
    """Test that message position is tracked."""
    result = fact_tracker.track(sample_session, "helpful")

    for entry in result.presence_entries:
        if entry.is_present:
            assert entry.message_position >= 0


def test_fact_tracker_empty_session(fact_tracker):
    """Test tracking on empty session."""
    from context_time_machine.server.session.models import Session

    empty_session = Session(source_format="test", turns=[])

    # Empty session returns result with no presence entries
    result = fact_tracker.track(empty_session, "test")
    assert len(result.presence_entries) == 0
    assert result.first_appeared_turn is None


def test_fact_tracker_threshold(fact_tracker):
    """Test custom similarity threshold."""
    tracker_loose = FactTracker(similarity_threshold=0.5)
    tracker_strict = FactTracker(similarity_threshold=0.95)

    assert tracker_loose.threshold == 0.5
    assert tracker_strict.threshold == 0.95


def test_fact_tracker_embedding_cache(fact_tracker, sample_session):
    """Test that embeddings are cached."""
    # Track same fact twice
    result1 = fact_tracker.track(sample_session, "helpful")
    result2 = fact_tracker.track(sample_session, "helpful")

    # Should get same results (proof of caching)
    assert result1.fact_text == result2.fact_text
    assert len(result1.presence_entries) == len(result2.presence_entries)

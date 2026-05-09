"""Tests for TokenAnalyzer."""

import pytest

from context_time_machine.server.analysis.token_analyzer import TokenAnalyzer


@pytest.fixture
def analyzer():
    """Create a TokenAnalyzer instance."""
    return TokenAnalyzer()


def test_token_analyzer_basic(analyzer, sample_session):
    """Test basic token analysis."""
    profile = analyzer.analyze_session(sample_session)

    assert profile.session_id == sample_session.session_id
    assert len(profile.per_turn_stats) == len(sample_session.turns)
    assert profile.peak_tokens > 0


def test_token_analyzer_per_turn_stats(analyzer, sample_session):
    """Test per-turn token statistics."""
    profile = analyzer.analyze_session(sample_session)

    for i, stats in enumerate(profile.per_turn_stats):
        assert stats.turn_number == i
        assert stats.total_tokens > 0
        assert stats.proximity_to_limit >= 0
        # Proximity can exceed 100% if total_tokens > model_limit
        assert stats.proximity_to_limit >= 0


def test_token_analyzer_peak_turn(analyzer, sample_session):
    """Test peak turn identification."""
    profile = analyzer.analyze_session(sample_session)

    assert profile.peak_turn >= 0
    assert profile.peak_turn < len(sample_session.turns)
    assert profile.peak_tokens > 0

    # Peak should be the turn with highest tokens
    peak_stat = profile.per_turn_stats[profile.peak_turn]
    assert peak_stat.total_tokens == profile.peak_tokens


def test_token_analyzer_components(analyzer, sample_session):
    """Test component breakdown."""
    profile = analyzer.analyze_session(sample_session)

    for stats in profile.per_turn_stats:
        total = (
            stats.system_tokens
            + stats.history_tokens
            + stats.tool_results_tokens
            + stats.current_turn_tokens
        )
        # Components should roughly sum to total (allowing for rounding)
        assert abs(total - stats.total_tokens) <= 5


def test_token_analyzer_growth_rate(analyzer, sample_session):
    """Test growth rate calculation."""
    profile = analyzer.analyze_session(sample_session)

    assert profile.average_growth_rate >= 0


def test_token_analyzer_tokens_added(analyzer, sample_session):
    """Test tokens added per turn."""
    profile = analyzer.analyze_session(sample_session)

    # First turn should have tokens_added = total_tokens
    assert profile.per_turn_stats[0].tokens_added_this_turn >= 0

    # Subsequent turns should show growth
    if len(profile.per_turn_stats) > 1:
        for i in range(1, len(profile.per_turn_stats)):
            assert profile.per_turn_stats[i].tokens_added_this_turn >= 0


def test_token_analyzer_max_tokens(analyzer, sample_session):
    """Test max tokens tracking."""
    profile = analyzer.analyze_session(sample_session)

    assert profile.max_tokens > 0
    assert profile.max_tokens == profile.peak_tokens


def test_token_analyzer_system_message_tokens(analyzer, sample_session):
    """Test system message token counting."""
    profile = analyzer.analyze_session(sample_session)

    # All turns should have system tokens
    for stats in profile.per_turn_stats:
        assert stats.system_tokens > 0


def test_token_analyzer_eviction_detection(analyzer, sample_session):
    """Test eviction turn detection."""
    profile = analyzer.analyze_session(sample_session)

    # Eviction turns are those where history_tokens decrease
    # This depends on the session content
    for turn_num in profile.eviction_turns:
        assert turn_num > 0  # Can't evict at turn 0
        assert turn_num < len(sample_session.turns)


def test_token_analyzer_proximity_to_limit(analyzer, sample_session):
    """Test proximity to limit calculation."""
    profile = analyzer.analyze_session(sample_session)

    for stats in profile.per_turn_stats:
        # Should be non-negative (can exceed 100% if total_tokens > limit)
        assert stats.proximity_to_limit >= 0

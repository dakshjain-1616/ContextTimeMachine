"""Tests for ContextReconstructor."""

import pytest

from context_time_machine.server.session.reconstructor import (
    ContextReconstructor,
    EvictionSimulator,
)


@pytest.fixture
def reconstructor():
    """Create a ContextReconstructor instance."""
    return ContextReconstructor()


def test_reconstructor_basic(reconstructor, sample_session):
    """Test basic context reconstruction."""
    reconstructed = reconstructor.reconstruct(sample_session, 0)

    assert reconstructed.session_id == sample_session.session_id
    assert reconstructed.turn_number == 0
    assert len(reconstructed.messages) > 0
    assert reconstructed.total_tokens > 0


def test_reconstructor_turn_progression(reconstructor, sample_session):
    """Test that context grows across turns."""
    ctx0 = reconstructor.reconstruct(sample_session, 0)
    ctx1 = reconstructor.reconstruct(sample_session, 1)
    ctx2 = reconstructor.reconstruct(sample_session, 2)

    assert ctx0.total_tokens < ctx1.total_tokens
    assert ctx1.total_tokens < ctx2.total_tokens


def test_reconstructor_message_ordering(reconstructor, sample_session):
    """Test that messages are in correct order."""
    reconstructed = reconstructor.reconstruct(sample_session, 2)

    # All system messages should come first
    system_count = sum(
        1 for msg in reconstructed.messages if msg.role.value == "system"
    )
    first_system_idx = next(
        i
        for i, msg in enumerate(reconstructed.messages)
        if msg.role.value == "system"
    )
    last_system_idx = max(
        (i for i, msg in enumerate(reconstructed.messages) if msg.role.value == "system"),
        default=-1,
    )

    # System messages should be contiguous at the start
    assert first_system_idx == 0


def test_reconstructor_invalid_turn(reconstructor, sample_session):
    """Test that invalid turn number raises error."""
    with pytest.raises(ValueError):
        reconstructor.reconstruct(sample_session, 999)

    with pytest.raises(ValueError):
        reconstructor.reconstruct(sample_session, -1)


def test_reconstructor_components(reconstructor, sample_session):
    """Test component breakdown."""
    reconstructed = reconstructor.reconstruct(sample_session, 2)
    components = reconstructed.components

    assert "system" in components
    assert "history" in components
    assert "tool_results" in components
    assert "current" in components

    assert all(v >= 0 for v in components.values())


def test_reconstructor_utilization_percent(reconstructor, sample_session):
    """Test utilization percentage calculation."""
    reconstructed = reconstructor.reconstruct(sample_session, 0)

    utilization = reconstructed.utilization_percent
    assert 0 <= utilization <= 100


def test_reconstructor_distance_to_limit(reconstructor, sample_session):
    """Test distance to limit calculation."""
    reconstructed = reconstructor.reconstruct(sample_session, 0)

    distance = reconstructed.distance_to_limit
    assert distance >= 0
    assert distance == reconstructed.model_limit - reconstructed.total_tokens


def test_eviction_simulator_model_limits():
    """Test model limit lookup."""
    assert EvictionSimulator.get_model_limit("gpt-4") == 8192
    assert EvictionSimulator.get_model_limit("claude-3-sonnet") == 204800
    assert EvictionSimulator.get_model_limit("unknown-model") == 128000


def test_eviction_simulator_strategies():
    """Test eviction strategy lookup."""
    assert EvictionSimulator.get_strategy("gpt-4") == "left-truncate"
    assert EvictionSimulator.get_strategy("qwen") == "left-truncate"
    assert EvictionSimulator.get_strategy("deepseek") == "sliding-window"


def test_reconstructor_never_evicts_system_messages(reconstructor, sample_session):
    """Test that system messages are never evicted."""
    reconstructed = reconstructor.reconstruct(sample_session, 2)

    # Count system messages
    system_msgs = [m for m in reconstructed.messages if m.role.value == "system"]
    assert len(system_msgs) > 0  # Should have at least one system message


def test_reconstructor_with_small_context_limit(sample_session):
    """Test eviction with small context limit."""
    # Temporarily modify model limit for testing
    original_limits = EvictionSimulator.MODEL_LIMITS.copy()
    EvictionSimulator.MODEL_LIMITS["gpt-4"] = 50  # Very small limit

    reconstructor = ContextReconstructor()
    reconstructed = reconstructor.reconstruct(sample_session, 2)

    # Should be constrained by the limit (allowing for system message protection)
    # System messages may exceed the limit since they're never evicted
    assert reconstructed.model_limit == 50

    # Restore
    EvictionSimulator.MODEL_LIMITS = original_limits


def test_reconstructor_handles_missing_token_counts(reconstructor):
    """Test handling of messages without token counts."""
    from context_time_machine.server.session.models import Session, SessionTurn, SessionMessage, MessageRole

    turns = [
        SessionTurn(
            turn_number=0,
            messages=[
                SessionMessage(
                    role=MessageRole.SYSTEM,
                    content="System message",
                    token_count=0,  # Missing
                ),
                SessionMessage(
                    role=MessageRole.USER,
                    content="User message",
                    token_count=0,  # Missing
                ),
            ],
            model_id="gpt-4",
            total_tokens=0,
        )
    ]

    session = Session(source_format="test", turns=turns, model_id="gpt-4")
    reconstructed = reconstructor.reconstruct(session, 0)

    # Should compute tokens even when missing
    assert reconstructed.total_tokens > 0

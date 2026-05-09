"""Tests for SessionStorage."""

import pytest

from context_time_machine.server.session.models import (
    MessageRole,
    Session,
    SessionMessage,
    SessionTurn,
)
from context_time_machine.server.storage.db import SessionStorage


@pytest.fixture
def sample_stored_session():
    """Create a sample session for storage testing."""
    turns = [
        SessionTurn(
            turn_number=0,
            messages=[
                SessionMessage(
                    role=MessageRole.SYSTEM,
                    content="System prompt",
                    token_count=2,
                ),
                SessionMessage(
                    role=MessageRole.USER,
                    content="Hello",
                    token_count=1,
                ),
            ],
            model_id="gpt-4",
            total_tokens=3,
        ),
    ]

    return Session(
        source_format="test",
        turns=turns,
        model_id="gpt-4",
    )


def test_storage_save_and_load(storage_db, sample_stored_session):
    """Test saving and loading a session."""
    session_id = sample_stored_session.session_id

    # Save
    storage_db.save(sample_stored_session)

    # Load
    loaded = storage_db.load(session_id)

    assert loaded is not None
    assert loaded.session_id == session_id
    assert loaded.source_format == sample_stored_session.source_format
    assert len(loaded.turns) == len(sample_stored_session.turns)


def test_storage_list_sessions(storage_db, sample_stored_session):
    """Test listing sessions."""
    storage_db.save(sample_stored_session)

    sessions = storage_db.list_sessions()

    assert len(sessions) > 0
    assert any(s["session_id"] == sample_stored_session.session_id for s in sessions)


def test_storage_list_sessions_metadata(storage_db, sample_stored_session):
    """Test that list includes metadata."""
    storage_db.save(sample_stored_session)

    sessions = storage_db.list_sessions()
    session_meta = next(
        s for s in sessions if s["session_id"] == sample_stored_session.session_id
    )

    assert "session_id" in session_meta
    assert "source_format" in session_meta
    assert "model_id" in session_meta
    assert "turn_count" in session_meta


def test_storage_delete(storage_db, sample_stored_session):
    """Test deleting a session."""
    session_id = sample_stored_session.session_id
    storage_db.save(sample_stored_session)

    # Verify exists
    assert storage_db.load(session_id) is not None

    # Delete
    result = storage_db.delete(session_id)
    assert result is True

    # Verify deleted
    assert storage_db.load(session_id) is None


def test_storage_delete_nonexistent(storage_db):
    """Test deleting nonexistent session."""
    result = storage_db.delete("nonexistent-id")
    assert result is False


def test_storage_clear(storage_db, sample_stored_session):
    """Test clearing all sessions."""
    storage_db.save(sample_stored_session)

    # Verify has data
    assert len(storage_db.list_sessions()) > 0

    # Clear
    storage_db.clear()

    # Verify empty
    assert len(storage_db.list_sessions()) == 0


def test_storage_update_session(storage_db, sample_stored_session):
    """Test updating a session."""
    session_id = sample_stored_session.session_id

    # Save
    storage_db.save(sample_stored_session)

    # Modify and resave
    sample_stored_session.metadata["updated"] = True
    storage_db.save(sample_stored_session)

    # Load and verify
    loaded = storage_db.load(session_id)
    assert loaded.metadata.get("updated") is True


def test_storage_multiple_sessions(storage_db):
    """Test storing multiple sessions."""
    sessions = []
    for i in range(3):
        session = Session(
            source_format="test",
            turns=[
                SessionTurn(
                    turn_number=0,
                    messages=[
                        SessionMessage(
                            role=MessageRole.USER,
                            content=f"Message {i}",
                            token_count=1,
                        ),
                    ],
                    model_id="gpt-4",
                    total_tokens=1,
                ),
            ],
            model_id="gpt-4",
        )
        storage_db.save(session)
        sessions.append(session)

    # List
    stored = storage_db.list_sessions()
    assert len(stored) == 3

    # Load each
    for session in sessions:
        loaded = storage_db.load(session.session_id)
        assert loaded is not None

"""Tests for SessionLoader."""

import json
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from context_time_machine.server.session.loader import SessionLoader
from context_time_machine.server.session.models import MessageRole


@pytest.fixture
def loader():
    """Create a SessionLoader instance."""
    return SessionLoader()


def test_loader_from_generic_json(loader, sample_json_file):
    """Test loading from generic JSON format."""
    session = loader.load(sample_json_file)

    assert session is not None
    assert session.source_format == "generic_json"
    assert session.model_id == "gpt-4"
    assert len(session.turns) == 1
    assert session.turns[0].turn_number == 0


def test_loader_from_dict(loader):
    """Test loading from dictionary."""
    data = {
        "turns": [
            {
                "turn": 0,
                "messages": [
                    {"role": "user", "content": "Hello", "token_count": 1}
                ],
                "model_id": "gpt-4",
            }
        ]
    }

    session = loader.load(data)
    assert session is not None
    assert session.source_format == "generic_json"
    assert len(session.turns) == 1


def test_loader_raw_conversation(loader):
    """Test loading raw conversation format."""
    data = {
        "messages": [
            {"role": "system", "content": "You are helpful.", "token_count": 3},
            {"role": "user", "content": "Hi", "token_count": 1},
            {"role": "assistant", "content": "Hello!", "token_count": 1},
        ]
    }

    session = loader.load(data)
    assert session is not None
    assert session.source_format == "raw_conversation"
    assert len(session.turns) == 1
    assert len(session.turns[0].messages) == 3


def test_loader_message_role_parsing(loader):
    """Test that message roles are parsed correctly."""
    data = {
        "turns": [
            {
                "turn": 0,
                "messages": [
                    {"role": "system", "content": "System prompt"},
                    {"role": "user", "content": "User input"},
                    {"role": "assistant", "content": "Assistant response"},
                    {"role": "tool_result", "content": "Tool output"},
                ],
            }
        ]
    }

    session = loader.load(data)
    turn = session.turns[0]

    assert turn.messages[0].role == MessageRole.SYSTEM
    assert turn.messages[1].role == MessageRole.USER
    assert turn.messages[2].role == MessageRole.ASSISTANT
    assert turn.messages[3].role == MessageRole.TOOL_RESULT


def test_loader_invalid_file(loader):
    """Test that loader raises error for invalid file."""
    with pytest.raises(FileNotFoundError):
        loader.load("/nonexistent/path/file.json")


def test_loader_empty_turns(loader):
    """Test that loader raises error for empty turns."""
    data = {"turns": []}
    with pytest.raises(ValueError):
        loader.load(data)


def test_loader_token_counting(loader):
    """Test token counting fallback."""
    # When token_count is 0, should use word count
    data = {
        "turns": [
            {
                "turn": 0,
                "messages": [
                    {"role": "user", "content": "Hello world test"}
                    # No token_count - should be computed
                ],
            }
        ]
    }

    session = loader.load(data)
    msg = session.turns[0].messages[0]
    assert msg.token_count > 0


def test_loader_multiple_turns(loader):
    """Test loading multiple turns."""
    data = {
        "turns": [
            {"turn": i, "messages": [{"role": "user", "content": f"Turn {i}"}]}
            for i in range(5)
        ]
    }

    session = loader.load(data)
    assert len(session.turns) == 5
    assert all(t.turn_number == i for i, t in enumerate(session.turns))


def test_loader_preserves_metadata(loader):
    """Test that metadata is preserved."""
    data = {
        "turns": [
            {
                "turn": 0,
                "messages": [{"role": "user", "content": "test"}],
            }
        ],
        "metadata": {"source": "test_run", "version": "1.0"},
    }

    session = loader.load(data)
    assert session.metadata["source"] == "test_run"
    assert session.metadata["version"] == "1.0"


def test_loader_handles_missing_fields(loader):
    """Test that loader handles missing optional fields."""
    data = {
        "turns": [
            {
                "turn": 0,
                "messages": [{"role": "user", "content": "Hello"}],
                # model_id and timestamp are missing
            }
        ]
    }

    session = loader.load(data)
    turn = session.turns[0]
    assert turn.model_id == "unknown"
    assert turn.timestamp is not None

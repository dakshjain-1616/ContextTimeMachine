"""Test configuration and fixtures."""

import json
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from context_time_machine.server.session.models import (
    MessageRole,
    Session,
    SessionMessage,
    SessionTurn,
)


@pytest.fixture
def sample_session():
    """Create a sample session for testing."""
    turns = [
        SessionTurn(
            turn_number=0,
            messages=[
                SessionMessage(
                    role=MessageRole.SYSTEM,
                    content="You are a helpful assistant.",
                    token_count=10,
                ),
                SessionMessage(
                    role=MessageRole.USER,
                    content="What is 2+2?",
                    token_count=5,
                ),
            ],
            model_id="gpt-4",
            total_tokens=15,
        ),
        SessionTurn(
            turn_number=1,
            messages=[
                SessionMessage(
                    role=MessageRole.SYSTEM,
                    content="You are a helpful assistant.",
                    token_count=10,
                ),
                SessionMessage(
                    role=MessageRole.USER,
                    content="What is 2+2?",
                    token_count=5,
                ),
                SessionMessage(
                    role=MessageRole.ASSISTANT,
                    content="2+2 equals 4.",
                    token_count=6,
                ),
            ],
            model_id="gpt-4",
            total_tokens=21,
        ),
        SessionTurn(
            turn_number=2,
            messages=[
                SessionMessage(
                    role=MessageRole.SYSTEM,
                    content="You are a helpful assistant.",
                    token_count=10,
                ),
                SessionMessage(
                    role=MessageRole.USER,
                    content="What is 2+2?",
                    token_count=5,
                ),
                SessionMessage(
                    role=MessageRole.ASSISTANT,
                    content="2+2 equals 4.",
                    token_count=6,
                ),
                SessionMessage(
                    role=MessageRole.USER,
                    content="What is 3+3?",
                    token_count=5,
                ),
                SessionMessage(
                    role=MessageRole.ASSISTANT,
                    content="3+3 equals 6.",
                    token_count=6,
                ),
            ],
            model_id="gpt-4",
            total_tokens=32,
        ),
    ]

    return Session(
        source_format="test",
        turns=turns,
        model_id="gpt-4",
    )


@pytest.fixture
def sample_json_file(tmp_path):
    """Create a sample JSON session file."""
    data = {
        "turns": [
            {
                "turn": 0,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are helpful.",
                        "token_count": 3,
                    },
                    {
                        "role": "user",
                        "content": "Hi there",
                        "token_count": 2,
                    },
                ],
                "model_id": "gpt-4",
                "timestamp": datetime.utcnow().isoformat(),
            }
        ],
        "model_id": "gpt-4",
    }

    file_path = tmp_path / "session.json"
    with open(file_path, "w") as f:
        json.dump(data, f)

    return file_path


@pytest.fixture
def storage_db(tmp_path):
    """Create a temporary storage database."""
    from context_time_machine.server.storage.db import SessionStorage

    db_path = tmp_path / "test.db"
    return SessionStorage(str(db_path))

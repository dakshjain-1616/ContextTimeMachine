"""FastAPI server for ContextTimeMachine."""

import json
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from context_time_machine.server.analysis.divergence import DivergenceFinder
from context_time_machine.server.analysis.fact_tracker import FactTracker
from context_time_machine.server.analysis.token_analyzer import TokenAnalyzer
from context_time_machine.server.session.loader import SessionLoader
from context_time_machine.server.session.reconstructor import ContextReconstructor
from context_time_machine.server.storage.db import SessionStorage


# Request/Response models
class LoadSessionRequest(BaseModel):
    """Request to load a session."""
    format: str = "auto"  # auto, livecontext, langsmith, generic_json


class FactTrackingRequest(BaseModel):
    """Request for fact tracking."""
    fact_text: str


class DivergenceRequest(BaseModel):
    """Request for divergence analysis."""
    session_a_id: str
    session_b_id: str


# Initialize app
app = FastAPI(
    title="ContextTimeMachine",
    description="Interactive post-hoc explorer for LLM agent session context history",
    version="0.1.0",
)

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
loader = SessionLoader()
reconstructor = ContextReconstructor()
storage = SessionStorage("sessions.db")
token_analyzer = TokenAnalyzer()
fact_tracker = FactTracker()
divergence_finder = DivergenceFinder()


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "ContextTimeMachine",
        "version": "0.1.0",
        "description": "Interactive post-hoc explorer for LLM agent session context history",
    }


@app.post("/api/session/load")
async def load_session(file: Optional[UploadFile] = None, data: Optional[str] = None):
    """Load a session from file or JSON data.

    Args:
        file: Uploaded file (SQLite or JSON)
        data: JSON data as string

    Returns:
        Session ID and basic stats
    """
    try:
        if file:
            # Save uploaded file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix=file.filename) as tmp:
                content = await file.read()
                tmp.write(content)
                tmp_path = tmp.name

            session = loader.load(tmp_path)
            Path(tmp_path).unlink()  # Clean up
        elif data:
            session = loader.load(json.loads(data))
        else:
            return JSONResponse({"error": "No file or data provided"}, status_code=400)

        # Save to storage
        storage.save(session)

        # Analyze
        profile = token_analyzer.analyze_session(session)

        return {
            "session_id": session.session_id,
            "turn_count": len(session.turns),
            "model": session.model_id,
            "format": session.source_format,
            "max_tokens": profile.max_tokens,
            "peak_turn": profile.peak_turn,
            "eviction_turns": profile.eviction_turns,
        }
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


@app.get("/api/session/{session_id}/profile")
async def get_token_profile(session_id: str):
    """Get token profile for a session."""
    session = storage.load(session_id)
    if not session:
        return JSONResponse({"error": "Session not found"}, status_code=404)

    profile = token_analyzer.analyze_session(session)

    return {
        "session_id": profile.session_id,
        "per_turn_stats": [
            {
                "turn": stat.turn_number,
                "total_tokens": stat.total_tokens,
                "system_tokens": stat.system_tokens,
                "history_tokens": stat.history_tokens,
                "tool_results_tokens": stat.tool_results_tokens,
                "current_turn_tokens": stat.current_turn_tokens,
                "proximity_to_limit": stat.proximity_to_limit,
                "tokens_added": stat.tokens_added_this_turn,
            }
            for stat in profile.per_turn_stats
        ],
        "peak_turn": profile.peak_turn,
        "peak_tokens": profile.peak_tokens,
        "eviction_turns": profile.eviction_turns,
        "average_growth_rate": profile.average_growth_rate,
    }


@app.get("/api/session/{session_id}/turn/{turn_num}")
async def get_turn_context(session_id: str, turn_num: int):
    """Get reconstructed context for a specific turn."""
    session = storage.load(session_id)
    if not session:
        return JSONResponse({"error": "Session not found"}, status_code=404)

    if turn_num < 0 or turn_num >= len(session.turns):
        return JSONResponse({"error": "Invalid turn number"}, status_code=400)

    reconstructed = reconstructor.reconstruct(session, turn_num)

    return {
        "session_id": reconstructed.session_id,
        "turn_number": reconstructed.turn_number,
        "total_tokens": reconstructed.total_tokens,
        "model_limit": reconstructed.model_limit,
        "distance_to_limit": reconstructed.distance_to_limit,
        "utilization_percent": reconstructed.utilization_percent,
        "components": reconstructed.components,
        "messages": [
            {
                "role": msg.role.value,
                "content": msg.content,
                "token_count": msg.token_count,
            }
            for msg in reconstructed.messages
        ],
    }


@app.post("/api/session/{session_id}/fact")
async def track_fact(session_id: str, request: FactTrackingRequest):
    """Track presence of a fact across turns."""
    session = storage.load(session_id)
    if not session:
        return JSONResponse({"error": "Session not found"}, status_code=404)

    result = fact_tracker.track(session, request.fact_text)

    return {
        "session_id": result.session_id,
        "fact_text": result.fact_text,
        "first_appeared_turn": result.first_appeared_turn,
        "last_present_turn": result.last_present_turn,
        "disappeared_at_turn": result.disappeared_at_turn,
        "presence_entries": [
            {
                "turn": entry.turn_number,
                "is_present": entry.is_present,
                "presence_score": entry.presence_score,
                "best_matching_message": entry.best_matching_message,
                "message_position": entry.message_position,
            }
            for entry in result.presence_entries
        ],
    }


@app.post("/api/divergence")
async def find_divergence(request: DivergenceRequest):
    """Find divergence point between two sessions."""
    session_a = storage.load(request.session_a_id)
    session_b = storage.load(request.session_b_id)

    if not session_a or not session_b:
        return JSONResponse({"error": "One or both sessions not found"}, status_code=404)

    result = divergence_finder.find(session_a, session_b)

    return {
        "session_a_id": result.session_a_id,
        "session_b_id": result.session_b_id,
        "divergence_turn": result.divergence_turn,
        "similarity_scores": result.similarity_scores,
        "summary": result.summary,
        "message_diff": (
            {
                "added_in_a": result.message_diff.added_in_a,
                "added_in_b": result.message_diff.added_in_b,
                "modified": result.message_diff.modified,
            }
            if result.message_diff
            else None
        ),
    }


@app.get("/api/sessions")
async def list_sessions():
    """List all stored sessions."""
    sessions = storage.list_sessions()
    return {"sessions": sessions}


@app.delete("/api/session/{session_id}")
async def delete_session(session_id: str):
    """Delete a session."""
    if storage.delete(session_id):
        return {"message": "Session deleted"}
    return JSONResponse({"error": "Session not found"}, status_code=404)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

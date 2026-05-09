"""Command-line interface for ContextTimeMachine."""

import json
import sys
import webbrowser
from pathlib import Path

import click

from context_time_machine.server.analysis.divergence import DivergenceFinder
from context_time_machine.server.analysis.fact_tracker import FactTracker
from context_time_machine.server.analysis.token_analyzer import TokenAnalyzer
from context_time_machine.server.main import app
from context_time_machine.server.session.loader import SessionLoader
from context_time_machine.server.storage.db import SessionStorage


@click.group()
def main():
    """ContextTimeMachine - Interactive context window history explorer."""
    pass


@main.command()
def serve():
    """Start the FastAPI server and open browser."""
    import uvicorn

    click.echo("Starting ContextTimeMachine server...")
    click.echo("Open http://localhost:8000 in your browser")

    try:
        webbrowser.open("http://localhost:8000")
    except Exception:
        pass

    uvicorn.run(app, host="0.0.0.0", port=8000)


@main.command()
@click.option(
    "--file",
    "-f",
    required=True,
    help="Path to session file (JSON, SQLite, etc.)",
)
def load(file: str):
    """Load a session file and display basic info."""
    try:
        loader = SessionLoader()
        session = loader.load(file)

        click.echo(f"\n✓ Loaded session: {session.session_id}")
        click.echo(f"  Format: {session.source_format}")
        click.echo(f"  Model: {session.model_id}")
        click.echo(f"  Turns: {len(session.turns)}")
        click.echo(f"  Created: {session.created_at.isoformat()}")

        # Analyze
        analyzer = TokenAnalyzer()
        profile = analyzer.analyze_session(session)

        click.echo(f"\n📊 Token Analysis:")
        click.echo(f"  Peak tokens: {profile.peak_tokens} at turn {profile.peak_turn}")
        click.echo(f"  Eviction turns: {profile.eviction_turns}")
        click.echo(f"  Avg growth rate: {profile.average_growth_rate:.1f} tokens/turn")

        # Save to storage
        storage = SessionStorage()
        storage.save(session)
        click.echo(f"\n✓ Session saved to database")

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@main.command()
@click.option("--session", "-s", required=True, help="Session ID")
@click.option(
    "--fact",
    "-f",
    required=True,
    help="Fact text to search for",
)
def fact(session: str, fact: str):
    """Track fact presence across session turns."""
    try:
        storage = SessionStorage()
        loaded_session = storage.load(session)

        if not loaded_session:
            click.echo(f"❌ Session {session} not found", err=True)
            sys.exit(1)

        tracker = FactTracker()
        result = tracker.track(loaded_session, fact)

        click.echo(f"\n📍 Fact Tracker Results for: \"{fact}\"")
        click.echo(f"  First appeared: Turn {result.first_appeared_turn}")
        click.echo(f"  Last present: Turn {result.last_present_turn}")

        if result.disappeared_at_turn:
            click.echo(f"  Disappeared: Turn {result.disappeared_at_turn}")
        else:
            click.echo(f"  Status: Still present at end")

        # Show presence chart
        click.echo(f"\nPresence Chart:")
        chart_str = ""
        for entry in result.presence_entries:
            if entry.is_present:
                chart_str += "█"
            else:
                chart_str += "░"
            if (entry.turn_number + 1) % 50 == 0:
                chart_str += "\n"

        click.echo(chart_str)

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@main.command()
@click.option("--session-a", "-a", required=True, help="First session ID")
@click.option("--session-b", "-b", required=True, help="Second session ID")
def diverge(session_a: str, session_b: str):
    """Find divergence point between two sessions."""
    try:
        storage = SessionStorage()
        session_a_obj = storage.load(session_a)
        session_b_obj = storage.load(session_b)

        if not session_a_obj or not session_b_obj:
            click.echo(f"❌ One or both sessions not found", err=True)
            sys.exit(1)

        finder = DivergenceFinder()
        result = finder.find(session_a_obj, session_b_obj)

        click.echo(f"\n🔍 Divergence Analysis")
        click.echo(f"{result.summary}")

        if result.divergence_turn is not None:
            click.echo(f"\nDivergence detected at turn {result.divergence_turn}")

            if result.message_diff:
                click.echo(f"\nMessages in A but not B: {len(result.message_diff.added_in_a)}")
                click.echo(f"Messages in B but not A: {len(result.message_diff.added_in_b)}")

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@main.command()
def sessions():
    """List all stored sessions."""
    try:
        storage = SessionStorage()
        session_list = storage.list_sessions()

        if not session_list:
            click.echo("No sessions stored")
            return

        click.echo(f"\n📚 Stored Sessions ({len(session_list)} total)")
        click.echo("-" * 80)

        for session in session_list:
            click.echo(f"ID: {session['session_id'][:16]}...")
            click.echo(f"  Format: {session['source_format']}")
            click.echo(f"  Model: {session['model_id']}")
            click.echo(f"  Turns: {session['turn_count']}")
            click.echo(f"  Created: {session['created_at']}")
            click.echo()

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@main.command()
def clear():
    """Remove all stored sessions."""
    if click.confirm("Are you sure you want to delete all stored sessions?"):
        storage = SessionStorage()
        storage.clear()
        click.echo("✓ All sessions cleared")
    else:
        click.echo("Cancelled")


if __name__ == "__main__":
    main()

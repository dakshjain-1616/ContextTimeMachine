# ContextTimeMachine

> **Post-hoc forensics for LLM agent context windows.**
> You know the agent forgot something. ContextTimeMachine tells you exactly *when* it forgot, *what* was in context at every turn, and *why* the answer at turn 38 contradicts the decision from turn 12.

---

## 🤖 Autonomously Built with NEO

**Built entirely by [NEO — Your Autonomous AI Engineering Agent](https://heyneo.com)**

[![Get NEO for VS Code](https://img.shields.io/badge/NEO-VS%20Code-007ACC?style=flat&logo=visualstudiocode)](https://marketplace.visualstudio.com/items?itemName=NeoResearchInc.heyneo)
[![Get NEO for Cursor](https://img.shields.io/badge/NEO-Cursor-000000?style=flat&logo=cursor)](https://marketplace.cursorapi.com/items/?itemName=NeoResearchInc.heyneo)

NEO is the autonomous AI engineering agent that orchestrates multi-step development tasks, manages complex codebases, and builds production systems end-to-end. [Learn more →](https://heyneo.com)

---

## The Real Pain Point

Long-running agent sessions fail in a specific, infuriating way:

- The agent runs for 40 turns.
- At turn 38 it ignores a user instruction given at turn 3, or contradicts a fact it retrieved at turn 15.
- You open the logs. Turn 3 is there. Turn 15 is there. Turn 38 is there.
- But you cannot see **what the model actually had in its context window at turn 38**.

Did the turn-3 instruction get truncated? Was it still there but pushed so far up that 25 tool-result blobs drowned it out? Did eviction kick in at turn 22 and silently drop it? Logs do not answer this. Token counters do not answer this. Tracing tools show you spans, not the reconstructed window the model saw.

ContextTimeMachine answers it. The context window at any turn is **deterministic** given the conversation history — so we reconstruct it exactly, render it, and let you query it.

## What You Can Actually Do With It

### 1. Travel to any turn
Load a session, jump to turn N, see the full reconstructed context window the model saw at that moment: every message in order, token counts per message, the truncation line if eviction fired, and the eviction strategy that was applied (left-truncation for GPT/Claude, sliding window for DeepSeek, etc.). Scrub turn-by-turn and watch the window evolve.

### 2. Track when a specific fact left the window
Paste any snippet — *"user prefers JSON output"*, *"the API key is in env var X"*, a decision, an instruction. ContextTimeMachine embeds it locally (`all-MiniLM-L6-v2`), scans every turn's reconstructed context, and gives you a green/red presence chart across the whole session.

Answers the most common debugging question for long agent sessions: **"At what turn did the agent stop knowing X?"**

### 3. Diff two sessions to find the divergence point
You have one run that worked and one that didn't. Same starting prompt. Different outcome. ContextTimeMachine aligns the two sessions turn-by-turn, computes context similarity at each step, and pinpoints the **earliest turn where the two context windows diverged** — usually the root cause of the different outcomes. Side-by-side diff at that turn.

This is the automated version of the manual A/B-the-traces process every team does by hand.

## Quick Start

```bash
git clone https://github.com/dakshjain-1616/ContextTimeMachine.git
cd ContextTimeMachine

python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -e .

timemachine --help
```

### Try it in 30 seconds

```bash
# Load a session (use the example below or your own JSON)
timemachine load --file session.json

# List loaded sessions
timemachine sessions

# Track whether a fact stayed in context
timemachine fact --session <session-id> --fact "user prefers JSON output"

# Find where two sessions diverged
timemachine diverge --session-a <id-a> --session-b <id-b>

# Start the FastAPI server (web UI + REST API)
timemachine serve
```

### Minimal session JSON

```json
{
  "model_id": "gpt-4",
  "turns": [
    {
      "turn": 0,
      "model_id": "gpt-4",
      "timestamp": "2026-05-09T10:00:00Z",
      "messages": [
        {"role": "system", "content": "You are helpful.", "token_count": 3},
        {"role": "user", "content": "Always reply in JSON.", "token_count": 6}
      ]
    },
    {
      "turn": 1,
      "model_id": "gpt-4",
      "timestamp": "2026-05-09T10:01:00Z",
      "messages": [
        {"role": "system", "content": "You are helpful.", "token_count": 3},
        {"role": "user", "content": "Always reply in JSON.", "token_count": 6},
        {"role": "assistant", "content": "Understood.", "token_count": 2},
        {"role": "user", "content": "What is 2+2?", "token_count": 5}
      ]
    }
  ]
}
```

## Python API

```python
from context_time_machine import (
    SessionLoader,
    ContextReconstructor,
    FactTracker,
    DivergenceFinder,
    TokenAnalyzer,
)

session = SessionLoader().load("session.json")

# Reconstruct what the model actually saw at turn 10
ctx = ContextReconstructor().reconstruct(session, turn_number=10)
print(ctx.total_tokens, ctx.utilization_percent, len(ctx.messages))

# Was a specific fact still in context?
result = FactTracker().track(session, "user prefers JSON output")
print(result.first_appeared_turn, result.last_present_turn, result.disappeared_at_turn)

# Token budget profile
profile = TokenAnalyzer().analyze_session(session)
print(profile.peak_tokens, profile.peak_turn, profile.eviction_turns)

# Compare two sessions
divergence = DivergenceFinder().find(session_a, session_b)
print(divergence.divergence_turn, divergence.summary)
```

## CLI Commands

| Command | What it does |
|---|---|
| `timemachine load --file <path>` | Load a session JSON, persist it, print token profile |
| `timemachine sessions` | List all persisted sessions |
| `timemachine fact --session <id> --fact "..."` | Track presence of a fact across all turns |
| `timemachine diverge --session-a <id> --session-b <id>` | Find the earliest divergence turn between two sessions |
| `timemachine serve` | Start FastAPI server + open browser |
| `timemachine clear` | Wipe the local session DB |

## How It Works

### Context reconstruction
For turn N: collect messages from turn 0 → N, count tokens with `tiktoken`, and if the total exceeds the model's context limit, simulate eviction according to the model's strategy:

- **GPT / Claude** — left-truncation (oldest non-system messages drop first)
- **DeepSeek** — sliding window biased to recent turns
- **Gemma** — local-global attention (sample from the middle)

System messages are never evicted.

### Fact tracking
The fact text is embedded once with `sentence-transformers/all-MiniLM-L6-v2`. For each reconstructed turn we compute cosine similarity against every message and mark the turn "fact present" when max similarity ≥ 0.75. Embeddings are cached for the lifetime of the run.

### Divergence detection
We align the two sessions to `min(len_a, len_b)` and, at each turn, compute average max-cosine similarity between the two reconstructed windows. The first turn where similarity drops below 0.85 is reported as the divergence point, plus a message-level diff for that turn.

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│  CLI (click)            timemachine load|fact|diverge|… │
├──────────────────────────────────────────────────────────┤
│  FastAPI server         /api/session/{id}/turn/{n}, …    │
│  + React frontend stub                                   │
├──────────────────────────────────────────────────────────┤
│  Core analysis                                           │
│    SessionLoader         (JSON, raw messages, SQLite)    │
│    ContextReconstructor  (+ EvictionSimulator)           │
│    FactTracker           (sentence-transformers)         │
│    DivergenceFinder                                      │
│    TokenAnalyzer                                         │
│    EmbeddingService      (all-MiniLM-L6-v2, cached)      │
├──────────────────────────────────────────────────────────┤
│  Storage                 SQLite (sessions.db)            │
└──────────────────────────────────────────────────────────┘
```

## Supported Session Formats

| Format | Status |
|---|---|
| Generic JSON (`turns[]` schema above) | ✓ Full |
| Raw conversation (single `messages[]` array) | ✓ Full |
| Snapshot SQLite DB | ✓ Full |
| LangSmith export | Planned |

## REST API

- `POST /api/session/load` — Load a session
- `GET  /api/sessions` — List sessions
- `DELETE /api/session/{id}` — Delete a session
- `GET  /api/session/{id}/profile` — Token profile
- `GET  /api/session/{id}/turn/{n}` — Reconstructed context at turn N
- `POST /api/session/{id}/fact` — Track a fact across turns
- `POST /api/divergence` — Find divergence between two sessions

## Tests

```bash
source venv/bin/activate
pytest tests/ -v
# 58 passed
```

Coverage: loader, reconstructor + eviction simulator, fact tracker, divergence finder, token analyzer, storage.

## Performance

- Context reconstruction: < 100 ms for typical sessions
- Fact tracking: 1–5 s for a full session (includes embedding)
- Divergence detection: 2–10 s for two sessions
- Memory: ~50–200 MB per stored session

## Known Limitations

- React frontend is currently a stub — the CLI, REST API, and Python API are the supported surfaces.
- LangSmith format loader is not yet implemented.
- No streaming for very large sessions (>10k turns).
- The embedding cache is in-memory and clears on restart.

## Requirements

Python 3.10+. Core deps: `fastapi`, `uvicorn`, `pydantic`, `click`, `tiktoken`, `sentence-transformers`, `numpy`, `sqlalchemy`, `aiofiles`.

## License

MIT

---

## Attribution

🤖 **Built with NEO** — Powered by [NEO](https://heyneo.com), the autonomous AI engineering agent.

This project was built using NEO's autonomous development capabilities — scaffolding, all core analysis modules, the 58-test suite, and documentation were generated end-to-end by NEO.

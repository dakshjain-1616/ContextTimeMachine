# ContextTimeMachine

## Goal
Build a production-ready full-stack web application for interactive post-hoc exploration of LLM agent session context window history, including token analysis, fact tracking, and session divergence finding.

## Research Summary
- **Model IDs & Limits (Verified for 2026 context)**:
    - `claude-sonnet-4-5-20250929`: 200,000 tokens
    - `gpt-4o`: 128,000 tokens
    - `gemini-2.0-flash`: 1,000,000 tokens
    - `llama3.3`: 128,000 tokens
    - `gemma3`: 128,000 tokens (standard), 32,000 (small variants)
- **Embeddings**: `all-MiniLM-L6-v2` (384 dimensions).
- **Tech Stack**: FastAPI (Backend), Vite + React + Tailwind (Frontend), SQLite (Storage), Sentence-Transformers (Analysis).

## Approach
- **Backend**: Modular Python package with a FastAPI server and a Click CLI.
- **Session Logic**: Decoupled loaders for multiple formats (LiveContext, LangSmith, JSON).
- **Analysis Engine**: 
    - `ContextReconstructor` for per-turn state.
    - `TokenAnalyzer` for growth/eviction metrics.
    - `FactTracker` using vector similarity (SQLite-cached).
    - `DivergenceFinder` for A/B session comparison.
- **Frontend**: Single Page Application (SPA) with D3/Recharts for visualization and Framer Motion for interactive transitions.
- **Deployment**: Frontend builds to `dist/` and is served statically by FastAPI for a single-binary feel.

## Subtasks
1. **Environment & Scaffolding**: Create `pyproject.toml`, `requirements.txt`, and directory structure. Set up Vite/React frontend. (verify: `pip install -e .` succeeds)
2. **Data Models & Storage**: Define Pydantic schemas for Sessions/Turns and set up SQLite DB with `SQLAlchemy`. (verify: `db.py` initializes schema)
3. **Session Loader**: Implement `loader.py` supporting LiveContext, LangSmith, and Generic JSON. (verify: loads `sample_sessions/` correctly)
4. **Context & Token Analysis**: Implement `reconstructor.py`, `eviction_sim.py`, and `token_analyzer.py` with real model limits. (verify: token counts match `tiktoken` expectations)
5. **Semantic Analysis**: Implement `embedder.py` (all-MiniLM-L6-v2) and `fact_tracker.py`. (verify: similarity > 0.75 for related facts)
6. **Divergence Engine**: Implement `divergence.py` to compare two sessions turn-by-turn. (verify: identifies turn where similarity drops)
7. **FastAPI Endpoints**: Build REST API for session management, analysis, and fact tracking. (verify: `GET /api/sessions` returns data)
8. **Frontend Components (Core)**: Build `TimelineNavigator`, `ContextPanel`, and `TurnDetail`. (verify: renders turn list with token sparklines)
9. **Frontend Components (Advanced)**: Build `FactTracker` UI and `DivergenceFinder` side-by-side view. (verify: diffs highlight changes)
10. **CLI & Integration**: Implement Click CLI `timemachine` and integrate frontend build into FastAPI. (verify: `timemachine serve` boots full app)
11. **Testing & Docs**: Write `pytest` suite and `README.md` with usage instructions. (verify: `pytest` passes 100%)

## Deliverables
| File Path | Description |
|-----------|-------------|
| `/home/daksh/7May/projects/context-time-machine/server/main.py` | FastAPI Entry point |
| `/home/daksh/7May/projects/context-time-machine/server/session/loader.py` | Multi-format session loader |
| `/home/daksh/7May/projects/context-time-machine/server/analysis/fact_tracker.py` | Semantic fact tracking logic |
| `/home/daksh/7May/projects/context-time-machine/frontend/src/App.jsx` | Main React application |
| `/home/daksh/7May/projects/context-time-machine/pyproject.toml` | Project configuration |

## Evaluation Criteria
- **Functional**: Loads all 4 session formats; reconstructs context accurately; tracks facts semantically.
- **Performance**: Semantic search < 200ms for average sessions; UI remains responsive with 100+ turns.
- **Production-Ready**: Full error handling for malformed JSON; CLI for headless operations; clean UI.

## Notes
- Use `tiktoken` for GPT-4o/Llama3 tokenization; fallback to word-count-based estimation for others if specific encoders are missing.
- Ensure `all-MiniLM-L6-v2` is downloaded on first run.

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Danny Toolkit v5.0 ("Project Omega") is a locally-running AI swarm system built in Python. It orchestrates multiple specialized agents via an async engine to handle tasks ranging from code generation and RAG-based knowledge retrieval to OS automation, multi-agent planning, and vision analysis. The primary language for code comments, variable names, and UI text is **Dutch**.

## Commands

### Running the app
```bash
python main.py                 # Launcher menu (central entry point)
python cli.py                  # Rich terminal interface
streamlit run sanctuary_ui.py  # Streamlit web dashboard
python fastapi_server.py       # REST API server (Swagger at localhost:8000/docs)
python telegram_bot.py         # Telegram bot interface
python daemon_heartbeat.py     # Autonomous background daemon
```

### RAG document ingestion
```bash
python ingest.py --batch --method paragraph  # Ingest docs from data/rag/documenten/
python ingest.py --batch --method code       # Code-aware chunking
python ingest.py --stats                     # Show vector DB stats
python ingest.py --reset                     # Reset vector store
```

### Tests
```bash
python test_swarm_engine.py   # Main engine tests (8 tests, 59 checks)
python test_cli.py
python test_proactive.py
python test_singularity.py
python test_neural_hub.py
```
Tests are standalone scripts (not pytest-based). Run them directly with `python`.

### Install
```bash
pip install -r requirements.txt
pip install -e ".[dev]"        # Editable install with dev tools (pytest, black, flake8)
```

## Architecture

### Swarm Engine (`swarm_engine.py`)
The core orchestrator. Uses `asyncio.gather()` to run multiple agents in parallel. Default thread pool is capped at 6 workers (`_swarm_executor`) to limit GIL contention. Key pattern:
- `SwarmPayload` dataclass carries agent responses (agent name, content type, content)
- `SwarmEngine` receives user input, routes via `AdaptiveRouter` (keyword-based multi-intent), dispatches to agent classes
- `run_swarm_sync()` is the synchronous entry point that wraps the async engine
- Fast-track regex (`_fast_track_check`) handles simple greetings/smalltalk without AI

### PrometheusBrain (`danny_toolkit/brain/trinity_omega.py`)
The LLM federation layer. Organizes 17 agent roles across 5 tiers (`NodeTier` / `CosmicRole` enums). Manages the AI fallback chain and coordinates which model handles a request.

### Governor (`danny_toolkit/brain/governor.py`)
Autonomous safety layer (Level 2 in the hierarchy: Danny > Governor > Orchestrator > Agents). Enforces hard-coded limits: rate limiting, circuit breaking, prompt injection detection, input length validation. Its rules cannot be overridden by agents.

### CorticalStack (`danny_toolkit/brain/cortical_stack.py`)
SQLite-based persistent memory (episodic events, semantic facts, system metrics). Thread-safe with WAL mode and `PRAGMA synchronous=NORMAL`. Writes are batched (flush every 20 writes or 5 seconds) for reduced lock contention. Singleton via `get_cortical_stack()`. Call `stack.flush()` to force-commit pending writes.

### Config (`danny_toolkit/core/config.py`)
Central `Config` class with all paths, API keys (from env vars), model settings, and user preferences (theme/language). All data directories are derived from `Config.BASE_DIR`. Call `Config.ensure_dirs()` to auto-create directory structure.

### Apps (`danny_toolkit/apps/`)
~50 standalone mini-applications (calculator, habit tracker, recipe generator, etc.). All inherit from `BaseApp`, which provides shared AI client initialization and JSON data persistence in `data/apps/`.

### Interfaces
Four frontends share the same SwarmEngine backend:
- **CLI** (`cli.py`): Rich-powered terminal with live panels
- **Streamlit** (`sanctuary_ui.py`): Web dashboard
- **FastAPI** (`fastapi_server.py`): REST API with auth via `FASTAPI_SECRET_KEY`
- **Telegram** (`telegram_bot.py`): Admin-only bot

## Subsystems

### MEMEX (Agentic RAG)
- Universal Ingest Protocol (`ingest.py`)
- ChromaDB vector store (`data/rag/chromadb/`)
- PLAN-phase entity extraction
- Research rendering (Ultimate Mode)

### Sanctuary UI
- Glass Box Interface
- Live pipeline visualization
- Rich Media Protocol (CRYPTO -> line_chart, HEALTH -> area_chart, DATA -> bar_chart, CODE -> code block)
- Shared backend with CLI

### PixelEye Vision Engine
- LLaVA-based vision via Ollama
- Visual State Manager
- Logic Gate verification

### OracleAgent & Self-Healing Pipeline
- Diagnose-and-fix
- Repair history
- Autonomous repair hooks

### SingularityEngine (`danny_toolkit/brain/singularity.py`)
- Tier 5 consciousness layer
- 5 modes: SLAAP, WAAK, DROOM, FOCUS, TRANSCEND
- Reflecteert op CorticalStack history
- Cross-tier synthesis

### DigitalDaemon (`danny_toolkit/daemon/daemon_core.py`)
- Always-on symbiotic entity
- Sensorium (event detection), LimbicSystem (mood/energy), Metabolisme (resource management)
- Governed by OmegaGovernor

### Kinesis (`kinesis.py`)
- OS automation via PyAutoGUI
- App whitelist for safety
- FAILSAFE: mouse to top-left corner = emergency stop

### Quest System (I-XIV)
- Diagnostics
- Cognitive mapping
- Bio-digital bridge (Pulse Protocol)

### Launcher
- 57+ apps
- Nexus Terminal v2.0
- Cosmic Console v6.0

## Key Patterns

- **Windows UTF-8**: Nearly every entry point reconfigures `sys.stdout` encoding to UTF-8. Maintain this pattern in new files.
- **Import fallbacks**: Many modules use `try/except ImportError` to gracefully degrade when optional dependencies (chromadb, ollama, pyautogui) are missing.
- **AI fallback chain**: Groq 70b -> Groq 8b -> Ollama local -> Anthropic Claude. Prevents single point of failure.
- **Singleton brain**: Both `fastapi_server.py` and `telegram_bot.py` use a module-level `_brain` singleton for `PrometheusBrain`.
- **CorticalStack logging**: Swarm engine and agents log events via `_log_to_cortical()` when CorticalStack is available. Writes are batched — call `stack.flush()` before shutdown.
- **Fact extraction**: `_learn_from_input()` in `swarm_engine.py` extracts user facts (name, preferences) into semantic memory.

## Environment Variables

Required in `.env` at project root:
- `GROQ_API_KEY` -- Primary LLM provider
- `ANTHROPIC_API_KEY` -- Fallback LLM
- `VOYAGE_API_KEY` -- Embeddings for RAG (voyage-4-large)

Optional:
- `FASTAPI_SECRET_KEY` -- API auth
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_ADMIN_ID` -- Telegram bot
- `ELEVENLABS_API_KEY`, `OPENAI_API_KEY` -- Speech/alternative LLM

## Data Layout

All persistent data lives under `data/`:
- `data/rag/chromadb/` -- ChromaDB vector store
- `data/rag/documenten/` -- Source documents for ingestion
- `data/cortical_stack.db` -- Episodic memory (SQLite)
- `data/apps/` -- Per-app JSON state files
- `data/logs/` -- System logs
- `data/plots/` -- Screenshots and generated media
- `data/backups/` -- Configuration backups
- `data/output/rapporten/` -- Generated reports

## Versioning

### v4.1.0
Last stable pre-v5 release. Includes:
- FastAPI Server + Telegram Bot
- Security Research Engine v2.0
- AdaptiveRouter V6.0
- Sanctuary UI v5.1.1

### v5.0.0 (commit 6c0b437)
- Metadata-only version bump
- 17 files updated (version strings only)
- No logic changes, no new features
- Purpose: major release alignment (COSMIC_OMEGA_V5)

### v5.0.1 (branch fix/v5.0.1)
- PATCH: versie-string consistentie fix in `danny_toolkit/core/config.py`
- PATCH: security warning comment bij default `FASTAPI_SECRET_KEY`

### v5.1.0 (branch upgrade/v5.1.0)
- MINOR: `--version` / `-V` CLI flag in `main.py`
- MINOR: `/ping` command in Telegram bot
- MINOR: `Config.toon_api_status()` in `danny_toolkit/core/config.py`
- MINOR: `/health` endpoint uitgebreid met uptime, memory, active agents
- MINOR: `SwarmEngine.get_stats()` voor query statistieken
- MINOR: 8 extra Nederlandse fast-track patronen in EchoAgent
- MINOR: `danny_toolkit/utils/ensure_directory.py` utility module

### v5.1.1 — Metadata Consistency Update

Deze update synchroniseert alle resterende versie-strings in de codebase met de huidige
v5.1.1 release. Acht bestanden bevatten nog oude referenties naar `v5.1.0` of
`COSMIC_OMEGA_V4`. Deze zijn opgeschoond en vervangen door `v5.1.1` en
`COSMIC_OMEGA_V5`.

Aangepaste onderdelen:
- Agents (base, orchestrator, tool) headers bijgewerkt
- OMEGA_PROTOCOL status geüpdatet naar COSMIC_OMEGA_V5
- MORNING_PROTOCOL reset-regel geüpdatet
- TRINITY_OMEGA systeemnaam geüpdatet
- FastAPI server versie geüpdatet naar 5.1.1
- GUI versie-strings gesynchroniseerd

Deze update bevat geen logische wijzigingen, enkel metadata-correcties.

## Guidelines for Claude Code

Claude should:
- Provide structured, technical answers
- Use project terminology (SwarmEngine, MEMEX, Sanctuary, Payloads, Agents, CorticalStack, Governor)
- Never guess -- rely only on observable facts
- Ask for missing context (file, diff, error, commit ID)
- Respect the existing architecture
- Avoid rewriting subsystems unless explicitly asked
- Produce syntactically correct Python
- Avoid unsolicited alternatives
- Write documentation in Markdown
- Maintain Windows UTF-8 patterns in new entry points
- Preserve `try/except ImportError` fallback patterns

## Developer Onboarding

1. Install dependencies: `pip install -r requirements.txt`
2. Create `.env` with required API keys (`GROQ_API_KEY`, `ANTHROPIC_API_KEY`, `VOYAGE_API_KEY`)
3. Pull Ollama models: `ollama pull llama3.2:3b` and `ollama pull llava`
4. Run `python main.py` to verify launcher works
5. Ingest documents: `python ingest.py --batch --method paragraph`
6. Run tests: `python test_swarm_engine.py`
7. Use Sanctuary UI for visual debugging: `streamlit run sanctuary_ui.py`

## Release Workflow

1. Update version numbers in all relevant files (see commit 6c0b437 for the full list of 17 files)
2. Run all test scripts
3. Generate changelog
4. Commit + tag
5. Publish release

## Forensic Analysis Workflow

1. `git checkout <commit>`
2. `git diff <old> <new>`
3. Generate observed-changes report
4. Perform impact analysis
5. Document in `FORENSIC_REPORT.md`

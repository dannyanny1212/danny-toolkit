# DEVELOPER_GUIDE.md

Developer onboarding guide for Danny Toolkit v5.0 (Project Omega / COSMIC_OMEGA_V5).

---

## Installation

### Prerequisites

- Python 3.10 or higher
- [Ollama](https://ollama.ai) (for local LLM inference and vision)
- Git

### Step 1: Clone and install

```bash
git clone https://github.com/dannyanny1212/danny-toolkit.git
cd danny-toolkit
pip install -r requirements.txt
```

### Step 2: Editable install (for development)

```bash
pip install -e ".[dev]"
```

This installs dev tools: `pytest`, `black`, `flake8`.

### Step 3: Pull Ollama models

```bash
ollama pull llama3.2:3b    # Local LLM fallback
ollama pull llava           # Vision engine (Project Oculus / PixelEye)
```

---

## Environment Variables

Create a `.env` file in the project root:

```ini
# Required
GROQ_API_KEY=gsk_...           # Primary LLM provider (https://console.groq.com/keys)
ANTHROPIC_API_KEY=sk-ant-...   # Fallback LLM
VOYAGE_API_KEY=...             # Embeddings for RAG (voyage-4-large)

# Optional
FASTAPI_SECRET_KEY=...         # API authentication key
TELEGRAM_BOT_TOKEN=...        # Telegram bot token (from @BotFather)
TELEGRAM_ADMIN_ID=...         # Your Telegram user ID (from @userinfobot)
ELEVENLABS_API_KEY=...        # Text-to-speech
OPENAI_API_KEY=...            # Alternative LLM provider
```

The `Config` class (`danny_toolkit/core/config.py`) reads these at import time. You can also call `Config.laad_env_bestand()` to reload.

---

## Running the System

### Launcher (Central Entry Point)

```bash
python main.py
```

This opens the Rich terminal launcher with a menu of 57+ apps. Choose option **42** for Streamlit GUI or **1** for the terminal interface.

### CLI (Rich Terminal)

```bash
python cli.py
```

Interactive terminal with live pipeline visualization. Commands:
- Type any question/task to invoke the SwarmEngine
- `status` -- Show system status
- `boot` -- Boot the federation
- `chain` -- Run chain pipeline
- `clear` -- Clear screen

### Sanctuary UI (Streamlit Dashboard)

```bash
streamlit run sanctuary_ui.py
```

Web-based Glass Box Interface at `localhost:8501`. Features live pipeline log, swarm activity, and system state sidebar.

### FastAPI Server (REST API)

```bash
python fastapi_server.py
```

REST API at `localhost:8000`. Swagger docs at `localhost:8000/docs`. Authenticate with `X-API-Key` header using your `FASTAPI_SECRET_KEY`.

### Telegram Bot

```bash
python telegram_bot.py
```

Setup:
1. Open Telegram, search for `@BotFather`
2. Send `/newbot` and follow the steps
3. Copy the token to `.env` (`TELEGRAM_BOT_TOKEN`)
4. Send `/start` to `@userinfobot` to get your ID
5. Set your ID in `.env` (`TELEGRAM_ADMIN_ID`)

### Heartbeat Daemon (Background Mode)

```bash
python daemon_heartbeat.py
```

Autonomous background process that periodically invokes the SwarmEngine for scheduled tasks. Press `Ctrl+C` to stop.

---

## RAG Ingestion

### Adding documents

1. Place files (PDF, TXT, PY) in `data/rag/documenten/`
2. Run the librarian:

```bash
python ingest.py --batch --method paragraph   # Standard text chunking
python ingest.py --batch --method code         # Code-aware chunking
```

### Useful ingest commands

```bash
python ingest.py --stats    # Show vector DB statistics
python ingest.py --reset    # Reset the entire vector store
```

The ingest process uses the Universal Ingest Protocol, which chunks documents and stores them in ChromaDB with Voyage AI embeddings.

---

## Debugging

### Sanctuary UI

The Streamlit dashboard is the primary debugging tool. It shows:
- **Left panel (The Feed):** Weaver synthesis output -- what the system says
- **Right panel (Swarm Activity):** Live pipeline log -- which agents are running
- **Sidebar (System State):** Governor health, circuit breaker status, active nodes

### Config status

```python
from danny_toolkit.core.config import Config
print(Config.toon_status())
```

This displays API key availability, preferences, and directory paths.

### CorticalStack inspection

```python
from danny_toolkit.brain.cortical_stack import get_cortical_stack
stack = get_cortical_stack()

# Recent events
events = stack.get_recent_events(limit=20)

# Recall a fact
name = stack.recall("user_name")

# System stats
stats = stack.get_stats()
```

### Governor status

The Governor's circuit breaker and rate limiter can be inspected at runtime. Check the sidebar in Sanctuary UI or query via the FastAPI `/health` endpoint.

---

## Tests

Tests are standalone Python scripts (not pytest-based). Run them directly:

```bash
python test_swarm_engine.py    # Main engine tests (8 tests, 59 checks)
python test_cli.py             # CLI interface tests
python test_proactive.py       # Proactive agent tests
python test_singularity.py     # SingularityEngine tests
python test_neural_hub.py      # Neural hub tests
```

Additional test files inside the package:

```bash
python danny_toolkit/test_cosmic_awareness.py
python danny_toolkit/test_full_chain.py
```

### What the tests cover

- `test_swarm_engine.py`:
  1. SwarmPayload dataclass construction
  2. Fast-track regex routing
  3. Multi-intent keyword routing
  4. EchoAgent (no AI)
  5. Agent classes (BrainAgent, Cipher, Vita, etc.)
  6. SwarmEngine orchestrator (without brain)
  7. SwarmEngine orchestrator (with brain, real AI)
  8. Parallel execution (asyncio.gather)

---

## Architecture Concepts

### SwarmPayload

The universal data carrier. Every agent returns one or more `SwarmPayload` objects:

```python
@dataclass
class SwarmPayload:
    agent: str          # Agent name (e.g., "CIPHER", "ECHO")
    type: str           # Content type: "text", "code", "metrics", "area_chart", "bar_chart"
    content: Any        # The actual data
    display_text: str   # What the user sees
    timestamp: float    # Unix timestamp
    metadata: Dict      # Additional context
```

### Agent lifecycle

1. `AdaptiveRouter` analyzes input keywords
2. Router selects one or more agents
3. `SwarmEngine` calls `agent.process(prompt)` via `asyncio.gather()`
4. Each agent returns `List[SwarmPayload]`
5. Payloads are merged and returned to the interface

### AI fallback chain

```
Groq 70b -> Groq 8b -> Ollama local -> Anthropic Claude
```

Each provider is tried in order. The Governor's circuit breaker trips after 3 consecutive failures and enters a 60-second cooldown.

### Memory architecture

| Layer | Storage | Purpose |
|-------|---------|---------|
| CorticalStack | SQLite | Episodic events, semantic facts, system metrics |
| UnifiedMemory | JSON + VectorStore | Cross-app context queries |
| ChromaDB | Vector DB | RAG knowledge base |

### BaseApp pattern

All 50+ apps inherit from `BaseApp`:

```python
class BaseApp:
    def __init__(self, data_bestand: str):
        # Auto-creates data dir, loads JSON state, inits AI client
        ...
```

Data persists in `data/apps/<filename>.json`. AI client (Anthropic) is optional and gracefully degrades.

---

## Best Practices

### Windows UTF-8

Every new entry point must include:

```python
import sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
```

### Import fallbacks

Optional dependencies must be wrapped:

```python
try:
    import chromadb
    HAS_CHROMADB = True
except ImportError:
    HAS_CHROMADB = False
```

### CorticalStack logging

Log significant events through the CorticalStack:

```python
from danny_toolkit.brain.cortical_stack import get_cortical_stack
stack = get_cortical_stack()
stack.log_event(actor="my_module", action="task_complete", details={"result": "ok"})
```

### Governor compliance

Never bypass the Governor's limits. If you need to adjust thresholds, modify the hard-coded constants in `governor.py` directly -- they are intentionally not configurable via external config.

---

## Release Workflow

### Version bump checklist

When releasing a new version, update version strings in all 17 files. See commit `6c0b437` for the complete list:

1. `pyproject.toml` -- `version` field
2. `requirements.txt` -- comment header
3. `danny_toolkit/__init__.py` -- `__version__`
4. `danny_toolkit/brain/__init__.py` -- `__version__`
5. `danny_toolkit/learning/__init__.py` -- `__version__`
6. `danny_toolkit/brain/trinity_omega.py` -- `SYSTEM_NAME`, `VERSION`, docstring
7. `danny_toolkit/core/config.py` -- docstring
8. `danny_toolkit/agents/base.py` -- docstring
9. `danny_toolkit/agents/orchestrator.py` -- docstring
10. `danny_toolkit/agents/tool.py` -- docstring
11. `danny_toolkit/launcher.py` -- `VERSIE`, banners, help text, docstring
12. `danny_toolkit/gui_launcher.py` -- window title, header label, status bar
13. `cli.py` -- docstring, ASCII header
14. `sanctuary_ui.py` -- docstring, HTML label
15. `fastapi_server.py` -- health endpoint version
16. `telegram_bot.py` -- status command version
17. `OMEGA_PROTOCOL.py` -- status field

### Release steps

1. Update all 17 version files
2. Run all test scripts and verify they pass
3. Generate changelog (review `git log` since last tag)
4. Commit with message: `Versie bump naar vX.Y.Z -- CODENAME`
5. Tag: `git tag vX.Y.Z`
6. Push: `git push && git push --tags`

### Forensic analysis (post-release)

1. `git diff <old-tag>..<new-tag>`
2. Generate observed-changes report
3. Perform impact analysis (functional, behavioral, risk)
4. Document in `FORENSIC_REPORT_<VERSION>.md`

# ARCHITECTURE.md

Full technical architecture of Danny Toolkit v5.0 (Project Omega / COSMIC_OMEGA_V5).

---

## High-Level Architecture Diagram

```
                          ┌─────────────────┐
                          │    USER INPUT    │
                          │ (CLI / Streamlit │
                          │  / API / Telegram│
                          │  / Daemon)       │
                          └────────┬────────┘
                                   │
                                   ▼
                    ┌──────────────────────────────┐
                    │      SWARM ENGINE v5.0       │
                    │   (asyncio.gather orchestr.) │
                    │                              │
                    │  ┌────────────────────────┐  │
                    │  │    AdaptiveRouter V6   │  │
                    │  │  (keyword multi-intent │  │
                    │  │   + multi-vector prof.)│  │
                    │  └───────────┬────────────┘  │
                    │              │                │
                    │    ┌─────────┼─────────┐     │
                    │    ▼         ▼         ▼     │
                    │ ┌──────┐ ┌──────┐ ┌──────┐  │
                    │ │Agent │ │Agent │ │Agent │  │
                    │ │  A   │ │  B   │ │  C   │  │
                    │ └──┬───┘ └──┬───┘ └──┬───┘  │
                    │    │        │        │       │
                    │    ▼        ▼        ▼       │
                    │  ┌──────────────────────┐    │
                    │  │  List[SwarmPayload]  │    │
                    │  └──────────────────────┘    │
                    └──────────────┬───────────────┘
                                  │
                    ┌─────────────┼─────────────┐
                    ▼             ▼             ▼
              ┌──────────┐ ┌──────────┐ ┌────────────┐
              │   CLI    │ │Sanctuary │ │  FastAPI /  │
              │ (Rich)   │ │   UI     │ │  Telegram   │
              └──────────┘ └──────────┘ └────────────┘
```

---

## Core Components

### 1. Swarm Engine (`swarm_engine.py`)

The central orchestrator. Receives user input, routes it through the `AdaptiveRouter`, and dispatches to one or more specialized agent classes in parallel via `asyncio.gather()`. The default thread pool is capped at 6 workers (`_swarm_executor`) to limit GIL contention and context switching.

**Key classes and functions:**
- `SwarmPayload` -- Dataclass that carries agent responses (agent name, content type, content, display text, timestamp, metadata)
- `SwarmEngine` -- Main orchestrator class
- `SwarmEngine.get_stats()` -- Returns query count, active agents, average response time
- `AdaptiveRouter` -- Keyword-based multi-intent router with multi-vector profiling
- `run_swarm_sync(prompt, brain)` -- Synchronous wrapper; the primary entry point for all interfaces
- `_fast_track_check(prompt)` -- Regex-based fast path for greetings/smalltalk (no AI needed, 19 patterns)
- `_learn_from_input(prompt)` -- Extracts user facts (name, preferences) into CorticalStack semantic memory

**Agent classes (all async):**
| Class | Agent | Role |
|-------|-------|------|
| `EchoAgent` | ECHO | Fast-track smalltalk (regex, no AI) |
| `BrainAgent` | NEXUS | General LLM routing via PrometheusBrain |
| `CipherAgent` | CIPHER | Crypto/finance metrics and charts |
| `VitaAgent` | VITA | Health/biometrics data and charts |
| `IolaaxAgent` | IOLAAX | Code generation and analysis |
| `AlchemistAgent` | ALCHEMIST | Data processing and ETL |
| `LegionAgent` | LEGION | OS automation via Kinesis |
| `SentinelValidator` | SENTINEL | Security validation |
| `PipelineTuner` | -- | Adaptive pipeline optimization |

**Media generators:**
- `_crypto_metrics()` -- 30-day BTC chart data + market ticker
- `_health_chart()` -- 24-hour HRV + heart rate data
- `_data_chart()` -- Generic data visualization
- `_code_media()` -- Syntax-highlighted code blocks

### 2. PrometheusBrain (`danny_toolkit/brain/trinity_omega.py`)

The LLM federation layer that organizes 17 agent roles across 5 cosmic tiers.

**Tier hierarchy:**

| Tier | Name | Nodes | Purpose |
|------|------|-------|---------|
| 1 | THE TRINITY | Pixel, Iolaax, Nexus | Consciousness (Interface, Reasoning, Bridge) |
| 2 | THE GUARDIANS | Governor, Sentinel, Archivist, Chronos | Protection (Control, Security, Memory, Time) |
| 3 | THE SPECIALISTS | Weaver, Cipher, Vita, Echo, Spark, Oracle | Workers (Code, Finance, Health, Patterns, Creative, Search) |
| 4 | THE INFRASTRUCTURE | Legion, Navigator, Alchemist, Void | Foundation (Swarm, Strategy, Data, Cleanup) |
| 5 | THE SINGULARITY | Anima, Synthesis, Evolution | Self-awareness (Soul, Cross-tier Merge, Self-Evolution) |

**Key enums:**
- `CosmicRole` -- 17 roles with tier classification
- `NodeTier` -- TRINITY, GUARDIANS, SPECIALISTS, INFRASTRUCTURE, SINGULARITY
- `TaskPriority` -- CRITICAL (1) through BACKGROUND (5)

**Key classes:**
- `AgentNode` -- Dataclass representing a single node (name, role, capabilities, tier, status, energy)
- `OmegaSwarm` -- Legion swarm manager (347 micro-agents: 100 miners, 100 testers, 147 indexers)
- `PrometheusBrain` -- Main brain class; `SYSTEM_NAME = "COSMIC_OMEGA_V5"`, `VERSION = "5.0.0"`

### 3. Governor (`danny_toolkit/brain/governor.py`)

Autonomous safety layer. Level 2 in the authority hierarchy.

**Authority hierarchy:**
1. Danny (Architect) -- ABSOLUTE
2. Governor (Omega-0) -- AUTONOMOUS, guards boundaries
3. Orchestrator (Brain) -- OPERATIONAL
4. Agents (Pixel/Iolaax/Weaver) -- EXECUTIVE

**Hard-coded limits (not configurable by agents):**
- `MAX_CONVERSATION_HISTORY = 50`
- `MAX_MEMORY_ENTRIES = 10000`
- `MAX_LEARNING_CYCLES_PER_HOUR = 20`
- `MAX_API_FAILURES = 3`
- `API_COOLDOWN_SECONDS = 60`
- `MAX_BACKUPS_PER_FILE = 3`
- `MAX_INPUT_LENGTH = 5000`

**Protections:**
- Prompt injection detection (regex patterns for jailbreak attempts)
- Circuit breaker for API failures
- Rate limiting per hour
- Input length validation

### 4. Config (`danny_toolkit/core/config.py`)

Central configuration singleton.

**Structure:**
- API keys loaded from environment variables
- Model settings: `CLAUDE_MODEL = "claude-sonnet-4-20250514"`, `VOYAGE_MODEL = "voyage-4-large"`
- RAG settings: `CHUNK_SIZE = 350`, `CHUNK_OVERLAP = 50`, `TOP_K = 5`
- All paths derived from `Config.BASE_DIR` (project root)
- User preferences (language, theme, debug mode) persisted to `data/toolkit_config.json`
- `Thema` class: 4 visual themes (standaard, modern, minimaal, retro)
- `Taal` class: 4 languages (nl, en, de, fr)
- `ConfigValidator`: API key format validation, path validation

---

## Memory Layers

The system uses a three-layer memory architecture:

### Layer 1: CorticalStack (Episodic + Semantic)
- **File:** `danny_toolkit/brain/cortical_stack.py`
- **Storage:** SQLite (`data/cortical_stack.db`)
- **Tables:** `episodic_memory` (timeline events), `semantic_memory` (key-value facts, UNIQUE), `system_stats` (metrics)
- **Access:** Singleton via `get_cortical_stack()`
- **Thread safety:** Lock on writes, WAL mode for lock-free reads
- **Write batching:** Commits are batched (every 20 writes or 5 seconds) to reduce lock contention. `PRAGMA synchronous=NORMAL` for reduced fsync overhead. Call `stack.flush()` to force-commit pending writes before shutdown.

### Layer 2: UnifiedMemory (Cross-App Vector)
- **File:** `danny_toolkit/brain/unified_memory.py`
- **Storage:** VectorStore (JSON-based) + EmbeddingProvider
- **Purpose:** Cross-app context queries via vector similarity
- **Events:** `MemoryEvent` dataclass (app, event_type, data, timestamp)

### Layer 3: ChromaDB (RAG Knowledge)
- **Directory:** `data/rag/chromadb/`
- **Ingestion:** `ingest.py` with batch processing
- **Chunking:** Paragraph-based or code-aware
- **Embeddings:** Voyage AI (`voyage-4-large`)

---

## AI Fallback Chain

```
Groq (llama-3.3-70b)
    │ failure
    ▼
Groq (llama-3.1-8b)
    │ failure
    ▼
Ollama Local (llama3.2:3b)
    │ failure
    ▼
Anthropic Claude (claude-sonnet-4)
```

The Governor's circuit breaker monitors failures. After `MAX_API_FAILURES = 3` consecutive failures, the system enters cooldown (`API_COOLDOWN_SECONDS = 60`).

---

## Interfaces

All four interfaces consume the same `run_swarm_sync()` entry point:

### CLI (`cli.py`)
- Rich-powered terminal with Live panels
- Pipeline log visualization
- Cipher Market Ticker (ASCII table)
- Syntax-highlighted code blocks
- Commands: `status`, `boot`, `chain`, `clear`

### Sanctuary UI (`sanctuary_ui.py`)
- Streamlit web dashboard
- Glass Box Interface with dark theme
- Left panel: The Feed (Weaver synthesis output)
- Right panel: Swarm Activity (live pipeline log)
- Sidebar: System State (Governor, Chronos, Agents)
- Rich Media Protocol: contextual charts based on payload type

### FastAPI Server (`fastapi_server.py`)
- REST API at `localhost:8000`
- Swagger docs at `/docs`
- Auth via `X-API-Key` header (`FASTAPI_SECRET_KEY`)
- Singleton brain instance
- Endpoints for chat, health (with uptime, memory, active agents), document upload

### Telegram Bot (`telegram_bot.py`)
- Admin-only (filtered by `TELEGRAM_ADMIN_ID`)
- Commands: `/start`, `/ping`, `/status`, `/agents`, `/heartbeat`, `/help`
- Commands: `/start`, `/status`, `/help`
- Forwards messages to SwarmEngine
- Setup via BotFather

### Heartbeat Daemon (`daemon_heartbeat.py`)
- Autonomous background process with Rich Live display
- Swarm tasks and security scans run in a 2-worker `ThreadPoolExecutor` (non-blocking UI)
- Swarm schedule checked every 60 pulses (60 seconds); stats logged every 30 pulses
- Scheduled tasks: Ochtend Briefing (08:00), Market Watch (hourly), System Reflect (5 min), Security Scan (hourly, background)
- CorticalStack writes are flushed on daemon shutdown

---

## Subsystem Details

### MEMEX (Agentic RAG)
- **Ingest:** `ingest.py` -> `TheLibrarian` / `BatchProcessor`
- **Vector store:** ChromaDB with Voyage AI embeddings
- **Protocol:** PLAN-phase entity extraction, then search, then cite
- **Source documents:** `data/rag/documenten/` (PDF, TXT, PY)

### SingularityEngine (`danny_toolkit/brain/singularity.py`)
- Tier 5 consciousness layer
- 5 modes: `SLAAP` (night/idle), `WAAK` (default), `DROOM` (idle hypothesis), `FOCUS` (critical task), `TRANSCEND` (convergence)
- Ticked every ~10s from HeartbeatDaemon
- Reflection interval: 5 min; Dream interval: 10 min

### DigitalDaemon (`danny_toolkit/daemon/daemon_core.py`)
- Always-on symbiotic entity
- **Sensorium** (`sensorium.py`): Event detection and classification
- **LimbicSystem** (`limbic_system.py`): Mood states, energy levels, avatar forms
- **Metabolisme** (`metabolisme.py`): Resource management and metabolic states
- Governed by OmegaGovernor for safety

### Kinesis (`kinesis.py`)
- OS automation via PyAutoGUI
- `KineticUnit` class with methods: `launch_app()`, `type_text()`, etc.
- App whitelist for safety (notepad, calc, chrome, code, etc.)
- `pyautogui.FAILSAFE = True`: mouse to (0,0) = emergency stop

### Apps Framework (`danny_toolkit/apps/`)
- ~50 standalone apps inheriting from `BaseApp`
- `BaseApp` provides: AI client init (Anthropic), JSON data persistence, shared utilities
- Data stored in `data/apps/<app_name>.json`
- Categories: productivity, health, creative, coding, finance, games

---

## Data Layout

```
data/
├── apps/                    # Per-app JSON state files
├── backups/                 # Configuration backups
├── cortical_stack.db        # Episodic memory (SQLite)
├── logs/                    # System logs
├── output/
│   └── rapporten/           # Generated reports
├── plots/                   # Screenshots and generated media
├── rag/
│   ├── chromadb/            # ChromaDB vector store
│   └── documenten/          # Source documents for ingestion
└── toolkit_config.json      # User preferences (theme, language, debug)
```

---

## Orchestrator Flow

```
1. User input arrives via interface (CLI/Streamlit/API/Telegram/Daemon)
2. _learn_from_input() extracts facts into CorticalStack
3. _fast_track_check() tests for regex-matchable smalltalk
4. If fast-track: EchoAgent returns immediately (no AI)
5. If not: AdaptiveRouter analyzes keywords for multi-intent routing
6. SwarmEngine dispatches to selected agents via asyncio.gather()
7. Each agent produces SwarmPayload(s) with typed content
8. _log_to_cortical() records the interaction
9. List[SwarmPayload] returned to interface for rendering
10. Interface renders based on payload type (text/code/metrics/chart)
```

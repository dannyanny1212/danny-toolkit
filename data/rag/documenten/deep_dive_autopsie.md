# Deep Dive Autopsie - Proces-Wachtrij OMEGA v6.11.0

De momentopname van het brein van OMEGA v6.11.0 — Trinity Perfect (10/10).
Het systeem is nu een zelf-optimaliserend autonoom organisme met
462 RAG-documenten, 81K+ CorticalStack events, en een Eternal Sentinel
die 24/7 waakt over de gezondheid van Mind, Body en Soul.

## Verhouding Trinity: MIND 48 : BODY 47 : SOUL 25

- **MIND** (48 modules) — beslissingslogica, 17 agents, SwarmEngine
- **BODY** (47 modules) — infrastructuur, NeuralBus, KeyManager, GPU
- **SOUL** (25+ bronnen) — ChromaDB 462 docs, CorticalStack 81K+ events

---

## TIER 1: HET BEWUSTZIJN (The Trinity Core)

### [IOLAAX] reasoning_mind (Deep Processing)

**Status: THE THINK TANK — ACTIEF**

Iolaax is het kernbewustzijn. Denkt in threads via PrometheusBrain
(17-pillar federated swarm, 5 cosmic tiers).

- **Thread 1:** `CentralBrain.process()` — LLM orchestrator, function calling naar 31+ app-tools
- **Thread 2:** `SwarmEngine.run()` — Adaptive routing, parallel agent dispatch, circuit breakers
- **Thread 3:** `HallucinatieSchild.verificatie()` — Context-aware bypass + Sentinel gate + RAG fact-check
- **Thread 4:** `Tribunal.verify()` — Async Groq 70B+8B dual-model verificatie
- **Thread 5:** `AdversarialTribunal.evaluate()` — Generator-Skeptic-Judge consensus
- **Thread 6:** `Strategist.plan()` — Recursive decompose, delegate, chain met search-query meta-filter

### [PIXEL] interface_soul (UI & Emotie)

**Status: THE INTERFACE — ACTIEF**

Pixel is de emotionele interface. Beheert de visuele representatie
en de menselijke connectie via LimbicSystem.

- `OmegaDashboardV4` — Textual TUI met Singleton Lock (msvcrt.LK_NBLCK)
- `FastAPI /ui/` — HTMX dashboard op poort 8000 met 10+ real-time widgets
- `LimbicSystem.process()` — Data/events naar emoties/moods (9 stemmingen)
- `Sensorium.observe()` — 35+ app event listeners
- `EmotionalVoiceEngine` — Speech synthesis (ElevenLabs/Edge-TTS)

### [NEXUS] bridge_connector (The Bridge)

**Status: THE OPEN LINES — ACTIEF**

Nexus verbindt alle domeinen. NeuralBus pub/sub + Knowledge Graph.

- **Bus:** `NeuralBus` — 50+ event types, thread-safe RLock, deque(maxlen=100)
- **Graph:** `TheCortex` — SQLite+NetworkX hybrid search, 358 nodes, 353 edges
- **Bridge:** `NexusBridge` — Pixel OMEGA connectie naar volledig ecosysteem
- **Symbiosis:** `TrinitySymbiosis` — Mind-Soul-Body integratie (8 Kosmische Familie)
- **Events:** SENTINEL_DEEP_SCAN, SENTINEL_THROTTLE, MISSION_STARTED, REQUEST_TRACE_COMPLETE

---

## TIER 2: DE GUARDIANS (The Shields)

### [GOVERNOR] OmegaGovernor (Safety Guardian)

**Status: GREEN ZONE — 0 GLOBALE 429s**

De Governor bewaakt rate limits, injection detection en token budgets
via SmartKeyManager met 10 Groq API keys.

- `GovernorFirewallMixin` — Input validatie, prompt injection detection, PII scrubbing
- `GovernorStateMixin` — State backup/restore/validate, rescue_family
- `SmartKeyManager` — 10 keys, 7 rollen + 3 reserves, per-agent isolation
- **Rate limits:** llama-4-scout 30 RPM / 30K TPM, qwen3-32b 60 RPM / 6K TPM
- **Dashboard:** `/api/v1/governor/rate-limits` — real-time per-agent token tracking

### [ETERNAL SENTINEL] EternalSentinel (Autonome Bewaker)

**Status: 4 LOOPS ACTIEF — 24/7**

De Sentinel is het zelf-optimaliserend bewakingssysteem,
geactiveerd in Phase 56 (commit 906bd523).

- **Loop 1:** `_deep_scan_loop()` — Elk uur L3 Deep Scan (/api/v1/health/deep)
- **Loop 2:** `_pulse_monitor_loop()` — Elke 30s L1 Pulse meting, auto-throttle bij >10ms
- **Loop 3:** `_nightly_loop()` — 03:00 CorticalStack events naar Daily Lesson RAG chunks
- **GPU:** NeuralBus subscribe MISSION_STARTED → P0 (1500-2100 MHz), TRACE_COMPLETE → idle
- **Throttle:** L1 Pulse >10ms → SwarmEngine geblokkeerd tot herstel

### [MEMEX] Context Manager (Vector Search)

**Status: 462 DOCS DOORZOEKBAAR**

- `AdvancedKnowledgeBridge` — 13-domein RAG, Markdown-aware chunking
- `SemanticCache` — Vector-based LLM response cache (Voyage 256d)
- `UnifiedMemory` — Central vector DB integrating all app data
- **API:** `/api/v1/knowledge/search` — REST endpoint voor 462 RAG-docs
- **Shards:** 3 ChromaDB collecties (code/docs/data) via ShardRouter

### [CHRONOS] HeartbeatDaemon (Timekeeper)

**Status: THE METRONOME — ACTIEF**

- **Pulse:** Elke seconde system monitoring (CPU/RAM)
- **Reflectie:** `PrometheusBrain.efficiency_reflection()` — B-95 quality score
- **Swarm Schedule:** Ochtend Briefing (08:00), Market Watch, Midnight Audit
- **Morning Protocol:** 07:00 — 3-layer DNA scan + integrity + logic validation
- **Dreamer REM:** 04:00 — backup, vacuum, retention, compress, GhostWriter, anticipate

---

## TIER 3: DE SPECIALISTS (The Workers)

### [WEAVER] Code Synthesis Agent

**Status: ACTIEF IN SWARM**

Weaver genereert en valideert code via de SwarmEngine pipeline.

- `Artificer.forge()` — Skill forge-verify-execute loop (always-forge mode)
- `GhostWriter.haunt()` — AST scanner + auto-docstring via Groq
- `DevOpsDaemon.run()` — Ouroboros CI loop: test, analyze, BlackBox, NeuralBus
- `RealityAnchor.validate()` — AST symbol validator rejecting phantom imports
- `ImportAnalyzer.scan()` — Relative import scanner + circular detection

### [CIPHER] Pattern Analysis Agent

**Status: ACTIEF IN SWARM**

Cipher analyseert patronen in data en detecteert anomalieën.

- `TheSynapse.route()` — Synaptic pathway plasticity (Hebbian routing)
- `ThePhantom.anticipate()` — Anticipatory intelligence, pre-warms MEMEX context
- `BlackBox.record()` — Negative RAG / immune memory (antibody escalation)
- `ConfigAuditor.audit()` — Runtime config validation, drift detection
- `CoherenceMonitor.scan()` — CPU+GPU load correlatie detector

### [VITA] Health & Bio Agent

**Status: ACTIEF IN SWARM**

Vita monitort systeemgezondheid en hardware vitals.

- `VRAMBudgetGuard` — RTX 3060 Ti VRAM monitor + budget serialization
- `gpu_control` — nvidia-smi clock management via CentralBrain (app-tool)
- `WaakhuisMonitor` — SQLite-backed monitoring: latency percentilen, gezondheidsscores
- `OracleEye.forecast()` — Predictive resource scaler (memory/CPU/API)
- **API:** `/api/v1/gpu/status` — Real-time GPU clock/VRAM/temp/power/pstate

### [ECHO] History & Pattern Agent

**Status: ACTIEF IN SWARM**

Echo bewaart en doorzoekt het episodisch geheugen.

- `CorticalStack` — Thread-safe SQLite WAL, 81K+ events, 64MB cache, 256MB mmap
- `ClaudeMemory` — Persistent semantic memory voor Claude Code
- `TheMirror.reflect()` — User profiling uit CorticalStack history
- **API:** `/api/v1/memory/recent` — Real-time CorticalStack events (Soul Pulse widget)
- `Dreamer._compress()` — Daily summary van episodisch naar semantisch geheugen

### [SPARK] Creative Generation Agent

**Status: ACTIEF IN SWARM**

Spark genereert creatieve output en innovatieve oplossingen.

- `GhostAmplifier.amplify()` — Token multiplier (5-10x elaboration)
- `SingularityEngine.synthesize()` — Cross-tier consciousness synthesis
- `VirtualTwin.consult()` — Sandboxed system clone + shadow intelligence
- `ShadowGovernance` — 3-zone kloon-restricties (ROOD/GEEL/GROEN)
- `DreamMonitor.observe()` — Passive observation during system dreams

### [ORACLE] Web Research Agent

**Status: ACTIEF IN SWARM**

Oracle is het oor naar de buitenwereld.

- `VoidWalker.research()` — Autonomous research via DuckDuckGo + scraper
- `OracleAgent.reason()` — Will-Action-Verification reasoning loop
- `TheHunt.search()` — 5-phase gamified search agent
- `WebScraper.crawl()` — HTML scraper with depth crawling
- `SecurityResearchEngine.run()` — 7 scan methods, 18 regex audit patterns

---

## TIER 4: DE INFRASTRUCTURE (The Foundation)

### [SWARMENGINE] Central Orchestrator

**Status: 17 AGENTS ACTIEF**

De SwarmEngine is het zenuwstelsel dat alle agents coördineert.

- `AdaptiveRouter` — Keyword + synaptic routing naar juiste agents
- `PipelineTuner` — Self-tuning latency per stap
- `RequestTracer` — Distributed tracing met trace_id correlatie
- `CircuitBreaker` — Per-agent fail tracking, auto-recovery
- **Workers:** CPU-core-aware pool: `min(max(cpu_count, 4), 16)`

### [NEURALBUS] Pub/Sub Event System

**Status: 50+ EVENT TYPES**

Het communicatiesysteem tussen alle componenten.

- Thread-safe: `threading.RLock()`, `deque(maxlen=100)` per event type
- Sentinel events: DEEP_SCAN, THROTTLE, GPU_BOOST, REINDEX
- Circuit breaker events: AGENT_CIRCUIT_OPEN, AGENT_CIRCUIT_CLOSED
- Pruning events: STARTED, ARCHIVED, DESTROYED, COMPLETE
- Fire-and-forget: sync callbacks in `ThreadPoolExecutor`, async via `create_task`

### [FASTAPI] REST API Server

**Status: 27+ ENDPOINTS OP POORT 8000**

- `GET /api/v1/health` — L1 Pulse (<3ms, geen brain loading)
- `GET /api/v1/health/deep` — L3 Deep Scan (Groq probe + CorticalStack + disk)
- `GET /api/v1/memory/recent` — Soul Pulse (CorticalStack events)
- `GET /api/v1/gpu/status` — Body Metrics (GPU clock/VRAM/temp)
- `GET /api/v1/governor/rate-limits` — Governor Guard (per-agent token tracking)
- `GET /api/v1/knowledge/search` — Knowledge Search (462 RAG-docs)
- `GET /ui/` — HTMX Dashboard met 10+ real-time widgets

### [SINGLETON] Process Integrity

**Status: OMEGA_V4.LOCK ACTIEF**

- `msvcrt.LK_NBLCK` — Non-blocking exclusive file lock
- Voorkomt zombie-processen die SQLite write-locks houden
- CorticalStack amnesie opgelost door stale process detectie
- WAL checkpoint TRUNCATE na zombie kill herstelt schrijfintegriteit
- Lock path: `%TEMP%/omega_v4.lock`

---

## KNOWLEDGE MAP (Neural Knowledge Mapper)

### Visuele Topologie

25 concept-nodes verdeeld over het Trinity-driehoek:
- **MIND** (paars, 10 nodes): CentralBrain, PrometheusBrain, SwarmEngine, HallucinatieSchild, Strategist, Artificer, VoidWalker, Tribunal, EternalSentinel, Governor
- **BODY** (groen, 8 nodes): NeuralBus, KeyManager, VRAMGuard, GPUControl, SingletonLock, HeartbeatDaemon, FastAPI, RequestTracer
- **SOUL** (blauw, 7 nodes): CorticalStack, ChromaDB, TheCortex, BlackBox, UnifiedMemory, Dreamer, KnowledgeBridge

### Connecties
- **101 edges** totaal (59 cross-domain)
- Zwaarste hub: SwarmEngine (raakt alle 3 domeinen)
- Cross-domain hotspots: CorticalStack↔SwarmEngine, NeuralBus↔Governor, ChromaDB↔CentralBrain

---

## HARDWARE BASELINE

| Component | Specificatie | Optimalisatie |
|-----------|-------------|---------------|
| GPU | NVIDIA GeForce RTX 3060 Ti (8 GB) | VRAMBudgetGuard, P-State management |
| SQLite | WAL mode | 64 MB cache, 256 MB mmap, busy_timeout=5000 |
| Swarm Workers | CPU-core-aware | min(max(cpu_count, 4), 16) |
| Embedding | Voyage 1024d → 256d MRL | ProcessPool voor >500 vectors |
| LLM | Groq cloud (meta-llama/llama-4-scout) | 10-key isolation, $0 VRAM |
| Vision | Ollama llava:latest | ~4.7 GB VRAM (serialized) |
| L1 Pulse | /api/v1/health | <3ms response |
| L3 Deep | /api/v1/health/deep | ~400ms (Groq probe + diagnostiek) |

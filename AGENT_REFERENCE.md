# Danny Toolkit v6.7.0 — Agent Reference

> Omega Sovereign Core | 50+ agents | 5 lagen | Brain CLI v2.0 Commander
>
> **Centraal aansturingspunt**: `python -m danny_toolkit.brain.brain_cli`

---

## 1. Architectuur

Alle agents worden aangestuurd via de **Brain CLI v2.0** (5-Laags Command Interface).

Agents draaien bovenop:
- **SwarmEngine** (asyncio orchestratie, AdaptiveRouter)
- **PrometheusBrain** (17 cosmic roles, 5 tiers)
- **OmegaGovernor** (safety guardian, rate-limits, injection detectie)
- **NeuralBus** (pub/sub event systeem)
- **AgentKeyManager** (10-key Groq isolatie per rol)

```
Brain CLI v2.0
    │
    ├── Laag 1: Swarm Engine (18 agents)    ← Directe taak-uitvoering
    ├── Laag 2: Brain Inventions (12 agents) ← Verificatie, planning
    ├── Laag 3: Daemons (6 entities)         ← Always-on monitoring
    ├── Laag 4: Prometheus (17 cosmic roles)  ← Federated intelligence
    └── Laag 5: Support Systems (18+)        ← Memory, security, repair
```

---

## 2. Laag 1: Swarm Engine Agents (18 geregistreerd)

Via `swarm_engine.py` — directe taakuitvoering met AdaptiveRouter.

| Agent | Class | Cosmic Role | Functie |
|-------|-------|-------------|---------|
| **IOLAAX** | IolaaxAgent | IOLAAX | Code, debugging, engineering |
| **CIPHER** | CipherAgent | CIPHER | Crypto, blockchain, finance |
| **VITA** | VitaAgent | VITA | Gezondheid, biometrics, HRV |
| **ECHO** | EchoAgent | ECHO | Fast-track smalltalk (regex, 19 NL patronen) |
| **NAVIGATOR** | BrainAgent | NAVIGATOR | Strategische planning, doelen |
| **ORACLE** | BrainAgent | ORACLE | Deep reasoning, hypotheses |
| **SPARK** | BrainAgent | SPARK | Brainstorm, creatief, kunst |
| **SENTINEL** | BrainAgent | SENTINEL | Security audits, threat analysis |
| **MEMEX** | MemexAgent | ARCHIVIST | Vector search + history memory |
| **CHRONOS** | BrainAgent | CHRONOS | Tijd, agenda, planning |
| **WEAVER** | BrainAgent | WEAVER | Code synthesis, git operaties |
| **PIXEL** | PixelAgent | PIXEL | Multimodaal vision (LLaVA 7B) |
| **ALCHEMIST** | AlchemistAgent | ALCHEMIST | Data ETL, transformatie |
| **VOID** | Specialized | VOID | Entropy reductie, cleanup |
| **COHERENTIE** | CoherentieAgent | — | CPU load correlatie monitor |
| **STRATEGIST** | StrategistAgent | — | Recursive task planning |
| **ARTIFICER** | ArtificerAgent | — | Skill forge-verify-execute |
| **VIRTUAL_TWIN** | VirtualTwinAgent | — | Sandboxed clone intelligence |

**LEGION** is geconfigureerd maar disabled (OS automatie).

---

## 3. Laag 2: Brain Inventions (12 agents)

Gespecialiseerde AI-agents in `/brain/` — verificatie, planning, onderzoek.

| Agent | Module | Lines | Functie |
|-------|--------|-------|---------|
| **Strategist** | strategist.py | 331 | Recursive planner met search-query meta-filter |
| **Artificer** | artificer.py | 580 | Skill forge: genereer → valideer → sandbox → opslaan |
| **VoidWalker** | void_walker.py | 231 | Web research (DuckDuckGo + scraper) |
| **OmegaGovernor** | governor.py | 959 | Safety guardian: rate-limits, injection detectie |
| **TaskArbitrator** | arbitrator.py | 773 | Goal decomposition + auction-based assignment |
| **AdversarialTribunal** | adversarial_tribunal.py | 328 | Generator-Skeptic-Judge consensus |
| **Tribunal** | tribunal.py | 150 | Async dual-model verificatie (Groq 70B+8B) |
| **HallucinatieSchild** | hallucination_shield.py | 644 | Anti-hallucinatie gate: claim-scoring |
| **TheOracleEye** | oracle_eye.py | 370 | Predictive resource scaler |
| **DevOpsDaemon** | devops_daemon.py | 587 | Ouroboros CI loop: test → analyze → BlackBox |
| **TheCortex** | cortex.py | 502 | Knowledge Graph (SQLite+NetworkX) |
| **VirtualTwin** | virtual_twin.py | 1308 | Shadow intelligence transfer |

---

## 4. Laag 3: Daemons (6 always-on entities)

Autonome entiteiten die continu draaien.

| Entity | Module | Lines | Functie |
|--------|--------|-------|---------|
| **HeartbeatDaemon** | daemon/heartbeat.py | 1014 | CPU/RAM monitoring, reflection cycles |
| **DigitalDaemon** | daemon/daemon_core.py | 529 | Symbiotic entity: sensorium + emotie |
| **DreamMonitor** | daemon/dream_monitor.py | 409 | REM sleep observer |
| **LimbicSystem** | daemon/limbic_system.py | 411 | Emotioneel brein: data → emoties |
| **Metabolisme** | daemon/metabolisme.py | 379 | Energiesysteem, health balance |
| **Sensorium** | daemon/sensorium.py | 302 | Sensory input (35+ app events) |

---

## 5. Laag 4: Prometheus 17 Cosmic Roles

PrometheusBrain — federated swarm intelligence over 5 tiers.

| Tier | Roles |
|------|-------|
| **Tier 1 - Trinity** | PIXEL (interface_soul), IOLAAX (reasoning_mind), NEXUS (bridge_spirit) |
| **Tier 2 - Guardians** | GOVERNOR (system_control), SENTINEL (security_ops), ARCHIVIST (memory_rag), CHRONOS (time_keeper) |
| **Tier 3 - Specialists** | WEAVER (code_builder), CIPHER (crypto_analyst), VITA (bio_health), ECHO (pattern_history), SPARK (creative_gen), ORACLE (web_search) |
| **Tier 4 - Infrastructure** | LEGION (swarm_manager), NAVIGATOR (strategy_goal), ALCHEMIST (data_proc), VOID (entropy_cleaner) |
| **Tier 5 - Singularity** | ANIMA (consciousness_core), SYNTHESIS (cross_tier_merge), EVOLUTION (self_evolution) |

---

## 6. Laag 5: Support Systems (18+)

| System | Functie |
|--------|---------|
| **CorticalStack** | Episodisch + semantisch geheugen (SQLite WAL) |
| **BlackBox** | Negative RAG — failure memory voorkomt herhaling |
| **UnifiedMemory** | Centraal vector DB voor alle app data |
| **GhostWriter** | AST scanner + auto-docstring via Groq |
| **Dreamer** | Overnight REM: backup, vacuum, GhostWriter |
| **SingularityEngine** | Cross-tier consciousness reflection |
| **TheSynapse** | Synaptic pathway plasticity (Hebbian routing) |
| **ThePhantom** | Anticipatory intelligence, pre-warms MEMEX |
| **ProactiveEngine** | Event-driven autonomous acties via Sensorium |
| **ShadowGovernance** | 3-zone clone restricties (ROOD/GEEL/GROEN) |
| **MorningProtocol** | 3-layer DNA scan + integrity validatie |
| **WaakhuisMonitor** | Health scoring, latency percentilen, heartbeats |
| **ConfigAuditor** | Runtime config validatie, drift detectie |
| **SystemIntrospector** | Self-awareness: modules, health, performance |
| **FileGuard** | Source integrity via manifest + SHA256 |
| **ModelRegistry** | Multi-model sync: 5 provider workers, auction routing |
| **CitationMarshall** | RAG verificatie via masked mean pooling |
| **RealityAnchor** | AST symbol validator tegen phantom imports |

---

## 7. Agent Lifecycle

1. **Registratie** — Agent registreert bij SwarmEngine met CosmicRole
2. **Routing** — AdaptiveRouter selecteert agent op basis van intent + vector profiel
3. **Executie** — Agent verwerkt taak met AgentKeyManager API key isolatie
4. **Verificatie** — Tribunal / HallucinatieSchild valideert output
5. **Logging** — CorticalStack + NeuralBus event publicatie
6. **Feedback** — B-95 efficiency reflection via PrometheusBrain

Agents kunnen ook dynamisch geladen worden via AgentFactory (`get_agent_factory()`) — lazy loading via importlib met thread-safe caching.

---

## 8. Brain CLI Aansturing

Alle lagen zijn direct bereikbaar via Brain CLI v2.0:

```bash
python -m danny_toolkit.brain.brain_cli
```

- Kies laag 1-5 voor agent detail + live probes
- `c` = Chat met Brain (function calling naar alle agents)
- `r` = RAG Query (zoek in kennisbank)
- `g` = RAG Gate (pre-execution validatie)
- `a` = Architectuur Scan (live verificatie alle lagen)
- `i` = Introspector (systeem health)

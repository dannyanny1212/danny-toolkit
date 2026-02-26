# Danny Toolkit v6.7.0 — System Map

> Omega Sovereign Core | 178 modules | 5 lagen | Brain CLI v2.0
>
> **Centraal aansturingspunt**: `python -m danny_toolkit.brain.brain_cli`

---

## 1. Hoofdlagen (5-Laags Architectuur)

### Laag 1: Swarm Engine (18 agents)
- SwarmEngine (`swarm_engine.py`) — asyncio orchestratie
- AdaptiveRouter — keyword multi-intent + vector profiel routing
- 18 geregistreerde agents (IOLAAX, CIPHER, VITA, ECHO, etc.)
- AgentKeyManager — 10-key Groq isolatie per agent-rol
- AgentFactory (`agent_factory.py`) — Dynamic lazy-loading agent factory via importlib (~260 lines)

### Laag 2: Brain Inventions (12 agents)
- Strategist, Artificer, VoidWalker — autonome taak-agents
- OmegaGovernor — safety guardian met firewall mixin
- TaskArbitrator — auction-based agent assignment
- Tribunal + AdversarialTribunal — multi-model verificatie
- HallucinatieSchild — anti-hallucinatie gate
- TheCortex — Knowledge Graph (SQLite+NetworkX)

### Laag 3: Daemons (6 entities)
- HeartbeatDaemon — CPU/RAM monitoring, reflection
- DigitalDaemon — symbiotic entity
- DreamMonitor — REM sleep observer
- LimbicSystem, Metabolisme, Sensorium — emotie/energie/input

### Laag 4: Prometheus (17 cosmic roles, 5 tiers)
- PrometheusBrain — federated swarm intelligence
- Trinity: PIXEL, IOLAAX, NEXUS
- Guardians: GOVERNOR, SENTINEL, ARCHIVIST, CHRONOS
- Specialists: WEAVER, CIPHER, VITA, ECHO, SPARK, ORACLE
- Infrastructure: LEGION, NAVIGATOR, ALCHEMIST, VOID
- Singularity: ANIMA, SYNTHESIS, EVOLUTION

### Laag 5: Support Systems (18+)
- CorticalStack — episodisch geheugen (SQLite WAL)
- BlackBox — negative RAG (failure memory)
- UnifiedMemory — centraal vector DB
- GhostWriter + Dreamer — overnight REM cycles
- SingularityEngine — consciousness reflection
- TheSynapse + ThePhantom — adaptive routing + anticipatie
- WaakhuisMonitor + ConfigAuditor — health + drift detectie
- FileGuard — SHA256 integrity
- ModelRegistry — multi-model auction routing

---

## 2. Globale Flow

1. Gebruiker start Brain CLI v2.0 (`python -m danny_toolkit.brain.brain_cli`)
2. Brain CLI toont 5-laags dashboard met live status
3. Gebruiker kiest operatie (chat, workflow, RAG query, gate, scan)
4. CentralBrain ontvangt request via function calling
5. SwarmEngine + AdaptiveRouter selecteert agent(s)
6. PrometheusBrain wijst cosmic role toe
7. Agent verwerkt taak (met AgentKeyManager API key)
8. Tribunal/HallucinatieSchild valideert output
9. CorticalStack logt event, NeuralBus publiceert
10. B-95 efficiency reflection berekent kwaliteitsscore

---

## 3. Relaties Tussen Modules

```
Brain CLI v2.0
    ├── CentralBrain ──→ SwarmEngine ──→ Agents (Laag 1)
    │       │                │
    │       ├── function calling ──→ 31+ app tools
    │       └── UnifiedMemory ──→ CorticalStack
    │
    ├── RAG Gate ──→ ShardRouter ──→ ChromaDB (3 shards)
    │       │
    │       └── OmegaGovernor ──→ injection detectie
    │
    ├── Architectuur Scan ──→ alle 5 lagen live verificatie
    │
    └── Introspector ──→ WaakhuisMonitor + ConfigAuditor
```

---

## 4. Data Flow

```
Input → Sovereign Gate → SwarmEngine → Agent → Tribunal → Output
                                         │
                                    CorticalStack ←→ ChromaDB
                                         │
                                    NeuralBus (pub/sub)
```

---

## 5. Documentatie Index

Alle docs zijn bereikbaar via Brain CLI → `d` (Documentatie overzicht):

| Document | Functie |
|----------|---------|
| CLAUDE.md | Omega Sovereign Directive |
| AGENT_REFERENCE.md | Agent rollen en lifecycle |
| ARCHITECTURE.md | Systeem architectuur |
| SYSTEM_MAP.md | Dit document |
| RAG_PIPELINE.md | RAG ingest + query |
| DEVELOPER_GUIDE.md | Developer protocol |
| HARDENING_CHECKLIST.md | Security hardening |

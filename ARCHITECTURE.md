# Danny Toolkit v6.7.0 — Systeem Architectuur

> Omega Sovereign Core | 178 modules | ~48K lines | Brain CLI v2.0
>
> **Centraal aansturingspunt**: `python -m danny_toolkit.brain.brain_cli`

---

## High-Level Architectuur

```
                          ┌─────────────────┐
                          │    USER INPUT    │
                          │ CLI / Streamlit  │
                          │ API / Brain CLI  │
                          └────────┬────────┘
                                   │
                    ┌──────────────▼──────────────────┐
                    │    BRAIN CLI v2.0 (Commander)    │
                    │  5-Laags Agent Orkestrator       │
                    │  + RAG Gate + Architectuur Scan  │
                    └──────────────┬──────────────────┘
                                   │
              ┌────────────────────┼────────────────────┐
              ▼                    ▼                     ▼
    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
    │ LAAG 1       │    │ LAAG 4       │    │ LAAG 5       │
    │ SwarmEngine  │    │ Prometheus   │    │ Support      │
    │ 18 agents    │◄──►│ 17 roles     │◄──►│ 18 systems   │
    └──────┬───────┘    └──────────────┘    └──────────────┘
           │
    ┌──────┼──────────────────────┐
    ▼                             ▼
┌──────────────┐       ┌──────────────┐
│ LAAG 2       │       │ LAAG 3       │
│ Brain Agents │       │ Daemons      │
│ 12 inventies │       │ 6 entities   │
└──────────────┘       └──────────────┘
```

---

## Domein Scheiding (Airgap Architectuur)

| Domein | Pad | Functie | Beveiliging |
|--------|-----|---------|-------------|
| **/brain/** | danny_toolkit/brain/ | Beslissingslogica, AI agents | Hoge security, cryptografisch |
| **/core/** | danny_toolkit/core/ | Infrastructuur, NeuralBus | Ironclad, geen externe connecties |
| **/apps/** | danny_toolkit/apps/ | Uitvoerende eenheden | Goedkeuring van /brain/ vereist |
| **/data/** | data/ | Persistent state | Alleen via memory_interface |
| **/daemon/** | danny_toolkit/daemon/ | Autonome entiteiten | Heartbeat, atexit handlers |

---

## Sleutelmodules

| Module | Class | Purpose | Lines |
|--------|-------|---------|-------|
| agent_factory.py | AgentFactory | Dynamic lazy-loading agent factory via importlib | ~260 |

---

## Communicatie: NeuralBus

Alle inter-agent communicatie verloopt via `NeuralBus`:
- 100% Non-Blocking (Fire-and-Forget)
- Event Signing: herkomst validatie
- History: `deque(maxlen=100)` per event type
- Singleton: `get_bus()` met `threading.RLock`

---

## Security: Sovereign Gate (7 IJzeren Wetten)

1. Root Integrity — pad moet exact `C:\Users\danny\danny-toolkit` zijn
2. Authority Check — Administrator privileges
3. Terminal Lock — Native PowerShell
4. Physical Console — Geen RDP of verborgen sessies
5. Identity Binding — Git email whitelist
6. Hardware Fingerprint — CPU ID + MAC verificatie
7. Iron Dome Network — Default-Deny uitgaand verkeer

---

## RAG Gate Protocol (3-Tier Validatie)

```
Actie → Tier 1 (Static Rules) → Tier 2 (RAG Query) → Tier 3 (Governor) → Uitvoeren/Blokkeren
```

Toegankelijk via:
- `python patchday.py gate "actie beschrijving"`
- Brain CLI → `g` (RAG Gate menu)

---

## Fallback Chain

```
Groq 70B → Groq 8B → Anthropic → NVIDIA NIM → Ollama → Emergency Offline
```

Per-provider circuit breakers met onafhankelijke fail tracking.

### LLM Providers (6)

- **Groq**: Llama 4 Scout 17B (primair), Qwen3-32B (fallback) — gratis tier
- **Anthropic**: Claude modellen via API key
- **NVIDIA NIM**: Qwen 2.5 Coder 32B (OpenAI-compatible SDK)
- **Ollama**: LLaVA (lokaal, vision only)
- **Voyage**: Embedding provider (1024d → 256d MRL)
- **Gemini**: Google Gemini 2.5 Flash (google.genai SDK, 500 RPM / 1M TPM gratis)

---

## Entry Points

| Entry Point | Pad | Functie |
|-------------|-----|---------|
| **Brain CLI** | `python -m danny_toolkit.brain.brain_cli` | Centraal command interface |
| Launcher | `python danny_toolkit/launcher.py` | Rich dashboard |
| CLI | `python cli.py` | Rich terminal |
| FastAPI | `python fastapi_server.py` | REST API |
| Daemon | `python run_daemon.py` | Heartbeat daemon |
| PatchDay | `python patchday.py` | Release lifecycle |

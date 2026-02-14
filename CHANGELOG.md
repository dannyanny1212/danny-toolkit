# Changelog
Alle belangrijke wijzigingen aan dit project worden hier gedocumenteerd.

---

## [5.2.0-perf] – 2026-02-14

### Performance — Heartbeat Daemon & CorticalStack Optimalisatie

De Heartbeat Daemon en onderliggende systemen zijn geoptimaliseerd om UI-freezes,
overmatige thread-creatie en SQLite lock contention te elimineren.

### Changed
- `danny_toolkit/daemon/heartbeat.py`:
  - Swarm taken draaien nu in een 2-worker `ThreadPoolExecutor` (voorheen blokkeerden ze de main loop via `asyncio.run()`)
  - Security scan (`volledig_rapport()`) draait nu in background thread (voorheen 30-60s UI freeze)
  - Swarm schedule check interval: 10 → 60 pulsen (83% minder checks)
  - Stat logging interval: 5 → 30 pulsen (83% minder DB writes)
  - Worker pool wordt netjes afgesloten bij stop/KeyboardInterrupt
  - CorticalStack wordt geflusht bij daemon shutdown

- `danny_toolkit/brain/cortical_stack.py`:
  - Writes worden nu gebatched (flush elke 20 writes of 5 seconden)
  - `PRAGMA synchronous=NORMAL` toegevoegd (minder fsync overhead)
  - Nieuwe methoden: `_maybe_flush()` (intern), `flush()` (publiek)
  - `close()` flusht nu pending writes voor sluiten

- `swarm_engine.py`:
  - Default thread pool gelimiteerd tot 6 workers (`_swarm_executor`)
  - Voorkomt 34+ threads en GIL contention

### Performance Impact
- Geen UI freezes meer (swarm en security draaien in background)
- ~80% minder DB writes (minder lock contention)
- ~70% minder threads (van ~34 naar ~10)
- ~100-200 MB RAM bespaard door minder thread overhead

---

## [1.2.0-gpu-phi3] – 2026-02-14
### Added
- Volledige GPU‑accelerated RAG‑pipeline (`rag_gpu.py`)
- Ondersteuning voor Phi‑3 Mini Instruct (GGUF) via `llama-cpp-python` 0.3.4 (cu121)
- FAISS GPU/CPU hybrid index logic in `faiss_index.py`
- Automatische CUDA‑detectie en volledige layer‑offload naar RTX 3060 Ti
- Benchmarksectie toegevoegd aan README
- Documentatie voor CUDA‑installatie, GPU‑vereisten en GGUF‑modelgebruik

### Changed
- `rag_chain.py` geüpdatet voor GGUF‑modellen en CUDA‑offload
- Pipeline geoptimaliseerd voor 30 tok / 243 ms op Phi‑3 Q4_K_M

### Performance
- Phi‑3 Mini Instruct Q4_K_M (3.82B params) draait volledig op GPU
- Model VRAM: ~2.2 GiB
- KV‑cache VRAM: ~768 MiB
- Totale latency: ~243 ms voor 30 tokens

---

## v5.1.1 — Metadata Consistency Update (2026-02-14)

Deze release brengt de volledige codebase in lijn met versie `v5.1.1` en
subsystem-label `COSMIC_OMEGA_V5`. Alle resterende referenties naar oudere versies
(`v5.1.0`, `v4.x`, `COSMIC_OMEGA_V4`) zijn opgeschoond.

### Gewijzigde bestanden
- OMEGA_PROTOCOL.py — status naar COSMIC_OMEGA_V5
- agents/base.py — header naar v5.1.1
- agents/orchestrator.py — header naar v5.1.1
- agents/tool.py — header naar v5.1.1
- brain/morning_protocol.py — reset-regel naar COSMIC_OMEGA_V5
- brain/trinity_omega.py — SYSTEM_NAME naar COSMIC_OMEGA_V5
- launcher.py — header naar v5.1.1
- fastapi_server.py — versie naar 5.1.1

### Samenvatting
- Geen functionele wijzigingen
- Volledige metadata-opschoning
- Codebase nu 100% consistent op v5.1.1 // COSMIC_OMEGA_V5

---

## [5.1.0] - 2026-02-13

### Added
- `main.py`: `--version` / `-V` flag — toont versie zonder launcher te starten
- `telegram_bot.py`: `/ping` command — meet response tijd, verifieert bot online
- `danny_toolkit/core/config.py`: `Config.toon_api_status()` — overzicht welke API keys actief zijn met validatie
- `fastapi_server.py`: `/health` endpoint uitgebreid met `uptime_seconds`, `memory_mb`, `active_agents`
- `swarm_engine.py`: `SwarmEngine.get_stats()` — telt verwerkte queries, actieve agents, gemiddelde responstijd
- `swarm_engine.py`: 8 extra Nederlandse fast-track patronen (dag, welterusten, dankjewel, top, oke, prima, etc.)
- `danny_toolkit/utils/ensure_directory.py`: utility functie voor veilig directory aanmaken

---

## [5.0.1] - 2026-02-13

### Fixed
- `danny_toolkit/core/config.py`: Versie-string gecorrigeerd van "Versie 5.0" naar "Versie 5.0.0" (consistent met VERSION = "5.0.0")
- `fastapi_server.py`: Security warning comment toegevoegd bij default `FASTAPI_SECRET_KEY`

### Documentation
- CLAUDE.md: v5.0.1 entry toegevoegd aan Versioning sectie
- MASTER_INDEX.md: Workflow & Governance sectie toegevoegd (UPGRADE_WORKFLOW, BRANCH_STRATEGY, HARDENING_CHECKLIST, RELEASE_NOTES_TEMPLATE)
- CHANGELOG.md: Aangemaakt

---

## [5.0.0] - 2026-02-12

### Changed
- Metadata-only version bump van v4.1.0 naar v5.0.0 (COSMIC_OMEGA_V5)
- 17 bestanden bijgewerkt (alleen versie-strings)
- Geen logica-wijzigingen, geen nieuwe features

---

## [4.1.0] - 2026-02-12

### Added
- FastAPI REST API Server
- Telegram Bot interface
- Security Research Engine v2.0
- AdaptiveRouter V6.0

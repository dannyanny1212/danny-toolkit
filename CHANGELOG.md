# CHANGELOG.md

# Danny Toolkit – Changelog

Alle noemenswaardige wijzigingen worden hier gedocumenteerd.
Format gebaseerd op [Keep a Changelog](https://keepachangelog.com/) en [Semantic Versioning](https://semver.org/).

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

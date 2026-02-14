# SYSTEM_MAP.md

# Danny Toolkit v5 – System Map

Dit document geeft een hoog-niveau overzicht van alle hoofdonderdelen van Danny Toolkit v5 ("Project Omega") en hun relaties.

## 1. Hoofdlagen
- Interface Layer
  - CLI (`cli.py`)
  - Sanctuary UI (`sanctuary_ui.py`)
  - FastAPI (`fastapi_server.py`)
  - Telegram Bot (`telegram_bot.py`)
- Orchestratie Layer
  - SwarmEngine (`swarm_engine.py`)
  - AdaptiveRouter
  - SwarmPayload
- Cognitieve Layer
  - PrometheusBrain (`brain/trinity_omega.py`)
  - Governor (`brain/governor.py`)
  - Quest System
  - OracleAgent
- Geheugen & Data Layer
  - CorticalStack (`brain/cortical_stack.py`)
  - MEMEX / ChromaDB
  - UnifiedMemory
  - `data/` structuur
- Subsystemen
  - MEMEX (RAG)
  - Sanctuary UI
  - PixelEye Vision
  - SingularityEngine / DigitalDaemon / Kinesis
  - Apps (±50 mini‑apps)

## 2. Globale Flow
1. Gebruiker stuurt input via een interface
2. Interface roept SwarmEngine aan
3. SwarmEngine gebruikt AdaptiveRouter
4. Router kiest agents / subsystemen
5. PrometheusBrain kiest modellen en rollen
6. Governor valideert en bewaakt veiligheid
7. Agents roepen MEMEX / PixelEye / tools aan
8. Resultaten worden opgeslagen in CorticalStack
9. Antwoord gaat terug naar interface
10. Logs en state worden in `data/` geschreven

## 3. Belangrijke Relaties
- Alle interfaces → SwarmEngine
- SwarmEngine → PrometheusBrain → Governor
- PrometheusBrain → Agents → MEMEX / PixelEye
- MEMEX → ChromaDB + documenten
- CorticalStack ↔ Orchestrator + Interfaces

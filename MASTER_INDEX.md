# Danny Toolkit v6.7.0 — Master Documentation Index

> Omega Sovereign Core | Centraal documentatie register
>
> **Centraal aansturingspunt**: `python -m danny_toolkit.brain.brain_cli` → kies `d`

---

## Project Documentatie

| Document | Inhoud | Status |
|----------|--------|--------|
| **CLAUDE.md** | Omega Sovereign Directive — alle protocollen, roadmap, 178 modules | GOLD |
| **AGENT_REFERENCE.md** | 50+ agents over 5 lagen, lifecycle, Brain CLI integratie | v6.7.0 |
| **ARCHITECTURE.md** | Systeem architectuur, domein scheiding, security, flow | v6.7.0 |
| **SYSTEM_MAP.md** | Hoofdlagen, globale flow, relaties, data flow | v6.7.0 |
| **RAG_PIPELINE.md** | RAG ingest, MRL truncatie, query pipeline, verificatie | v6.7.0 |
| **DEVELOPER_GUIDE.md** | Diamond Polish regels, workflow, test env, security | v6.7.0 |
| **HARDENING_CHECKLIST.md** | Security hardening: 7 wetten + Sovereign Gate | v6.7.0 |
| **MEMEX_INTERNALS.md** | MEMEX: shard_router, vector store, shadow_airlock | v6.7.0 |
| **UPGRADE_WORKFLOW.md** | Branch strategie, test, deploy, patchday | Actueel |
| **CHANGELOG.md** | Release changelog alle versies | Actueel |
| **README.md** | Project overzicht + Agent Roster | Actueel |

## RAG Kennisbank (data/rag/documenten/)

| Document | Inhoud |
|----------|--------|
| omega_sovereign_security.md | Sovereign security protocol, 7 wetten, PII |
| shadow_rag_token_protocol.md | Shadow RAG staging flow, deduplicatie |
| vector_embedding_learning.md | Vector embedding architectuur, Voyage, MRL |
| rag_security_best_practices.md | RAG security best practices |
| rag_security_ingestion_access_control.md | RAG access control |
| deep_dive_autopsie.md | Systeem analyse |
| MYTHICAL_NEXUS_DESIGN.md | Swarm architectuur design |

## Bron van Waarheid

1. **CLAUDE.md** — Absolute bron van waarheid voor architectuur en protocollen
2. **docs/index.md** — MkDocs Golden Master (publiek)
3. **Brain CLI v2.0** — Live systeem verificatie via Architectuur Scan

## Nieuwe Modules (v6.7.0)

| Module | Locatie | Doel |
|--------|---------|------|
| `agent_factory.py` | brain/ | Agent instantie factory met lazy loading en registry |

---

Alle andere docs zijn afgeleiden en worden gesynchroniseerd via Brain CLI.

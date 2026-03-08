"""
Brain CLI v2.0 — Omega Sovereign Command Interface.



5-Laags Agent Commander met RAG-gestuurde architectuur bewustzijn.
Alle 50+ agents worden via dit centraal punt aangestuurd, gemonitord
en gedocumenteerd. Elke .md wordt live gequeryd via de RAG pipeline.

Lagen:
    1. Swarm Engine Agents (18 geregistreerd)
    2. Brain Inventions (12 gespecialiseerde agents)
    3. Daemons (3 always-on entities)
    4. Prometheus 17 Cosmic Roles (5 tiers)
    5. Support Systems (18+ subsystemen)

Gebruik:
    python -m danny_toolkit.brain.brain_cli
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

from danny_toolkit.core.utils import clear_scherm, kleur, Kleur, fix_encoding
from danny_toolkit.core.config import Config

from danny_toolkit.brain.central_brain import CentralBrain
from danny_toolkit.brain.workflows import SUPER_WORKFLOWS


# ═══════════════════════════════════════════════════════════════
#  LAAG DEFINITIES — De 5 Agent Lagen van het Ecosysteem
# ═══════════════════════════════════════════════════════════════

LAAG_1_SWARM = {
    "naam": "Swarm Engine Agents",
    "beschrijving": "Operationele agents in swarm_engine.py — directe taak-uitvoering",
    "agents": [
        {"naam": "IOLAAX", "rol": "Engineer", "class": "IolaaxAgent", "desc": "Code, debugging, engineering"},
        {"naam": "CIPHER", "rol": "Finance", "class": "CipherAgent", "desc": "Crypto, blockchain, finance"},
        {"naam": "VITA", "rol": "Health", "class": "VitaAgent", "desc": "Gezondheid, biometrics, HRV"},
        {"naam": "ECHO", "rol": "Interface", "class": "EchoAgent", "desc": "Fast-track smalltalk (regex)"},
        {"naam": "NAVIGATOR", "rol": "Search", "class": "BrainAgent", "desc": "Strategische planning, doelen"},
        {"naam": "ORACLE", "rol": "Reasoning", "class": "BrainAgent", "desc": "Deep reasoning, hypotheses"},
        {"naam": "SPARK", "rol": "Creative", "class": "BrainAgent", "desc": "Brainstorm, creatief, kunst"},
        {"naam": "SENTINEL", "rol": "Security", "class": "BrainAgent", "desc": "Audits, threat analysis"},
        {"naam": "MEMEX", "rol": "Archivist", "class": "MemexAgent", "desc": "Vector search + memory"},
        {"naam": "CHRONOS", "rol": "Schedule", "class": "BrainAgent", "desc": "Tijd, agenda, planning"},
        {"naam": "WEAVER", "rol": "Synthesis", "class": "BrainAgent", "desc": "Code synthesis, git ops"},
        {"naam": "PIXEL", "rol": "Vision", "class": "PixelAgent", "desc": "Multimodaal, LLaVA 7B"},
        {"naam": "ALCHEMIST", "rol": "Data", "class": "AlchemistAgent", "desc": "Data ETL, transformatie"},
        {"naam": "VOID", "rol": "Cleanup", "class": "Specialized", "desc": "Entropy reductie, garbage"},
        {"naam": "COHERENTIE", "rol": "Monitor", "class": "CoherentieAgent", "desc": "CPU load correlatie"},
        {"naam": "STRATEGIST", "rol": "Planning", "class": "StrategistAgent", "desc": "Recursive task planning"},
        {"naam": "ARTIFICER", "rol": "Forge", "class": "ArtificerAgent", "desc": "Skill forge-verify-execute"},
        {"naam": "VIRTUAL_TWIN", "rol": "Analysis", "class": "VirtualTwinAgent", "desc": "Sandboxed clone intelligence"},
    ],
}

LAAG_2_BRAIN = {
    "naam": "Brain Inventions",
    "beschrijving": "Gespecialiseerde AI-agents in /brain/ — verificatie, planning, onderzoek",
    "agents": [
        {"naam": "Strategist", "module": "strategist.py", "desc": "Recursive planner met meta-filter"},
        {"naam": "Artificer", "module": "artificer.py", "desc": "Skill forge: genereer-valideer-sandbox-opslaan"},
        {"naam": "VoidWalker", "module": "void_walker.py", "desc": "Web research (DuckDuckGo + scraper)"},
        {"naam": "OmegaGovernor", "module": "governor.py", "desc": "Safety guardian: rate-limits, injection detectie"},
        {"naam": "TaskArbitrator", "module": "arbitrator.py", "desc": "Goal decomposition + auction assignment"},
        {"naam": "AdversarialTribunal", "module": "adversarial_tribunal.py", "desc": "Generator-Skeptic-Judge consensus"},
        {"naam": "Tribunal", "module": "tribunal.py", "desc": "Async dual-model verificatie (Groq 70B+8B)"},
        {"naam": "HallucinatieSchild", "module": "hallucination_shield.py", "desc": "Anti-hallucinatie gate"},
        {"naam": "TheOracleEye", "module": "oracle_eye.py", "desc": "Predictive resource scaler"},
        {"naam": "DevOpsDaemon", "module": "devops_daemon.py", "desc": "Ouroboros CI loop"},
        {"naam": "TheCortex", "module": "cortex.py", "desc": "Knowledge Graph (SQLite+NetworkX)"},
        {"naam": "VirtualTwin", "module": "virtual_twin.py", "desc": "Shadow intelligence transfer"},
    ],
}

LAAG_3_DAEMONS = {
    "naam": "Daemons (Always-On)",
    "beschrijving": "Autonome entiteiten die continu draaien — hartslag, emotie, dromen",
    "agents": [
        {"naam": "HeartbeatDaemon", "module": "daemon/heartbeat.py", "desc": "CPU/RAM monitoring, reflection cycles"},
        {"naam": "DigitalDaemon", "module": "daemon/daemon_core.py", "desc": "Symbiotic entity: sensorium + emotie"},
        {"naam": "DreamMonitor", "module": "daemon/dream_monitor.py", "desc": "REM sleep observer"},
        {"naam": "LimbicSystem", "module": "daemon/limbic_system.py", "desc": "Emotioneel brein: data → emoties"},
        {"naam": "Metabolisme", "module": "daemon/metabolisme.py", "desc": "Energiesysteem, health balance"},
        {"naam": "Sensorium", "module": "daemon/sensorium.py", "desc": "Sensory input (35+ app events)"},
    ],
}

LAAG_4_PROMETHEUS = {
    "naam": "Prometheus 17 Cosmic Roles",
    "beschrijving": "Federated swarm intelligence over 5 tiers — PrometheusBrain orkestrator",
    "tiers": {
        "Tier 1 - Trinity": ["PIXEL (interface_soul)", "IOLAAX (reasoning_mind)", "NEXUS (bridge_spirit)"],
        "Tier 2 - Guardians": ["GOVERNOR (system_control)", "SENTINEL (security_ops)", "ARCHIVIST (memory_rag)", "CHRONOS (time_keeper)"],
        "Tier 3 - Specialists": ["WEAVER (code_builder)", "CIPHER (crypto_analyst)", "VITA (bio_health)", "ECHO (pattern_history)", "SPARK (creative_gen)", "ORACLE (web_search)"],
        "Tier 4 - Infrastructure": ["LEGION (swarm_manager)", "NAVIGATOR (strategy_goal)", "ALCHEMIST (data_proc)", "VOID (entropy_cleaner)"],
        "Tier 5 - Singularity": ["ANIMA (consciousness_core)", "SYNTHESIS (cross_tier_merge)", "EVOLUTION (self_evolution)"],
    },
}

LAAG_5_SUPPORT = {
    "naam": "Support Systems",
    "beschrijving": "Ondersteunende subsystemen — memory, security, monitoring, self-repair",
    "systems": [
        {"naam": "CorticalStack", "desc": "Episodisch + semantisch geheugen (SQLite WAL)"},
        {"naam": "BlackBox", "desc": "Negative RAG — failure memory voorkomt herhaling"},
        {"naam": "UnifiedMemory", "desc": "Centraal vector DB voor alle app data"},
        {"naam": "GhostWriter", "desc": "AST scanner + auto-docstring via Groq"},
        {"naam": "Dreamer", "desc": "Overnight REM: backup, vacuum, GhostWriter, anticipate"},
        {"naam": "SingularityEngine", "desc": "Cross-tier consciousness reflection"},
        {"naam": "TheSynapse", "desc": "Synaptic pathway plasticity (Hebbian routing)"},
        {"naam": "ThePhantom", "desc": "Anticipatory intelligence, pre-warms MEMEX"},
        {"naam": "ProactiveEngine", "desc": "Event-driven autonomous acties via Sensorium"},
        {"naam": "ShadowGovernance", "desc": "3-zone clone restricties (ROOD/GEEL/GROEN)"},
        {"naam": "MorningProtocol", "desc": "3-layer DNA scan + integrity validatie"},
        {"naam": "WaakhuisMonitor", "desc": "Health scoring, latency percentilen, heartbeats"},
        {"naam": "ConfigAuditor", "desc": "Runtime config validatie, drift detectie"},
        {"naam": "SystemIntrospector", "desc": "Self-awareness: modules, health, performance"},
        {"naam": "FileGuard", "desc": "Source integrity via manifest + SHA256"},
        {"naam": "ModelRegistry", "desc": "Multi-model sync: 5 provider workers, auction routing"},
        {"naam": "CitationMarshall", "desc": "Strict RAG verificatie via masked mean pooling"},
        {"naam": "RealityAnchor", "desc": "AST symbol validator tegen phantom imports"},
    ],
}

# Alle projectdocumentatie (.md) met hun functie
PROJECT_DOCS = {
    "CLAUDE.md": "Omega Sovereign Core Directive — alle protocollen en architectuur",
    "AGENT_REFERENCE.md": "Agent referentie — rollen, lifecycle, capabilities",
    "ARCHITECTURE.md": "Systeem architectuur — lagen, flow, componenten",
    "SYSTEM_MAP.md": "System cartografie — relaties tussen modules",
    "MASTER_INDEX.md": "Documentatie index — centrale verwijzing",
    "DEVELOPER_GUIDE.md": "Developer protocol — regels, workflow, security",
    "RAG_PIPELINE.md": "RAG pipeline — ingest, chunking, query, verificatie",
    "HARDENING_CHECKLIST.md": "Security hardening — 6 domeinen",
    "MEMEX_INTERNALS.md": "MEMEX internals — vector store, query pipeline",
    "PIXEL_EYE_INTERNALS.md": "PixelEye internals — vision pipeline",
    "UPGRADE_WORKFLOW.md": "Upgrade workflow — branch, test, deploy",
    "VISION_PIPELINE.md": "Vision pipeline — image analysis, UI herkenning",
    "CHANGELOG.md": "Release changelog — alle versies",
    "README.md": "Project README — overzicht en Agent Roster",
    "docs/index.md": "MkDocs Golden Master — v6.11.0 systeem status",
}

# RAG productie documenten
RAG_DOCS = {
    "omega_sovereign_security.md": "Sovereign security protocol — 7 wetten, PII, secrets",
    "shadow_rag_token_protocol.md": "Shadow RAG flow — staging, deduplicatie, promotie",
    "vector_embedding_learning.md": "Vector embedding architectuur — Voyage, MRL, ChromaDB",
    "rag_security_best_practices.md": "RAG security best practices",
    "rag_security_ingestion_access_control.md": "RAG ingestion access control",
    "deep_dive_autopsie.md": "Deep dive autopsie — systeem analyse",
    "MYTHICAL_NEXUS_DESIGN.md": "Mythical Nexus design — swarm architectuur",
    "python_asyncio_event_loop.md": "Python asyncio event loop kennis",
}


# ═══════════════════════════════════════════════════════════════
#  BRAIN CLI v2.0 — Omega Sovereign Command Interface
# ═══════════════════════════════════════════════════════════════

class BrainCLI:
    """Omega Command Interface — bewuste aansturing van alle 5 lagen.

    Dit is het centrale zenuwpunt van het Danny Toolkit ecosysteem.
    Alle agents, daemons, RAG queries en documentatie worden via
    deze interface aangestuurd, gemonitord en gevalideerd.
    """

    VERSIE = "2.0.0"

    def __init__(self) -> None:
        """Initializes the Omega Brain CLI, loads the central brain, and checks RAG availability.

 Args: 
  None

 Returns: 
  None

 Raises: 
  None

 Notes:
  - Calls `fix_encoding()` to ensure proper encoding.
  - Initializes `CentralBrain` instance and assigns it to `self.brain`.
  - Checks RAG availability and stores result in `self._rag_beschikbaar`."""
        fix_encoding()
        print(kleur("\n   Omega Brain CLI v2.0 laden...\n", Kleur.CYAAN))
        self.brain = CentralBrain()
        self._rag_beschikbaar = self._check_rag()

    def _check_rag(self) -> bool:
        """Check of RAG pipeline beschikbaar is."""
        try:
            from danny_toolkit.core.shard_router import get_shard_router
            router = get_shard_router()
            return True
        except Exception:
            return False

    def _rag_query(self, vraag: str, shards: list = None, top_k: int = 3) -> list:
        """Query de RAG pipeline voor context."""
        if not self._rag_beschikbaar:
            return []
        try:
            from danny_toolkit.core.shard_router import get_shard_router
            router = get_shard_router()
            return router.zoek(query=vraag, top_k=top_k, shards=shards)
        except Exception as e:
            logger.debug("RAG query fout: %s", e)
            return []

    def _print_header(self, titel: str) -> None:
        """Print Omega header."""
        clear_scherm()
        print(kleur("""
 ╔═══════════════════════════════════════════════════════════════╗
 ║     ██████╗ ███╗   ███╗███████╗ ██████╗  █████╗             ║
 ║    ██╔═══██╗████╗ ████║██╔════╝██╔════╝ ██╔══██╗            ║
 ║    ██║   ██║██╔████╔██║█████╗  ██║  ███╗███████║            ║
 ║    ██║   ██║██║╚██╔╝██║██╔══╝  ██║   ██║██╔══██║            ║
 ║    ╚██████╔╝██║ ╚═╝ ██║███████╗╚██████╔╝██║  ██║            ║
 ║     ╚═════╝ ╚═╝     ╚═╝╚══════╝ ╚═════╝ ╚═╝  ╚═╝            ║
 ║                                                               ║
 ║      B R A I N   C L I   v2.0  —  Sovereign Commander        ║
 ╚═══════════════════════════════════════════════════════════════╝
""", Kleur.CYAAN))
        print(kleur(f"  {titel}", Kleur.GEEL))
        print()

    def _print_divider(self) -> None:
        """Print divider."""
        print(kleur("  " + "─" * 60, Kleur.CYAAN))

    def _print_laag_header(self, nummer: int, naam: str) -> None:
        """Print laag header."""
        print(kleur(f"\n  ═══ LAAG {nummer}: {naam.upper()} ═══", Kleur.MAGENTA))

    # ─── SYSTEM STATUS ────────────────────────────────────────

    def _systeem_status(self) -> dict:
        """Verzamel complete systeemstatus over alle 5 lagen."""
        status = {
            "brain": self.brain.get_status(),
            "rag": self._rag_beschikbaar,
            "laag_1_count": len(LAAG_1_SWARM["agents"]),
            "laag_2_count": len(LAAG_2_BRAIN["agents"]),
            "laag_3_count": len(LAAG_3_DAEMONS["agents"]),
            "laag_4_tiers": len(LAAG_4_PROMETHEUS["tiers"]),
            "laag_4_roles": sum(len(v) for v in LAAG_4_PROMETHEUS["tiers"].values()),
            "laag_5_count": len(LAAG_5_SUPPORT["systems"]),
            "docs_count": len(PROJECT_DOCS),
            "rag_docs_count": len(RAG_DOCS),
        }

        # Daemon health check
        heartbeat_file = Config.BASE_DIR / "daemon_heartbeat.txt"
        if heartbeat_file.exists():
            try:
                ts = heartbeat_file.read_text(encoding="utf-8").strip()
                status["daemon_heartbeat"] = ts
            except Exception:
                status["daemon_heartbeat"] = "onleesbaar"
        else:
            status["daemon_heartbeat"] = None

        # Cortical Stack check
        try:
            from danny_toolkit.core.memory_interface import get_cortical_stack_safe
            stack = get_cortical_stack_safe()
            if stack:
                status["cortical_events"] = stack.count_events() if hasattr(stack, "count_events") else "?"
            else:
                status["cortical_events"] = "offline"
        except Exception:
            status["cortical_events"] = "offline"

        # Governor check
        try:
            from danny_toolkit.brain.governor import OmegaGovernor
            status["governor"] = "actief"
        except ImportError:
            status["governor"] = "niet geladen"

        return status

    # ─── HOOFDMENU ────────────────────────────────────────────

    def run(self) -> None:
        """Start de Omega Brain CLI."""
        while True:
            self._print_header("Omega Sovereign Command Interface")

            # Status dashboard
            status = self._systeem_status()
            brain_s = status["brain"]
            ai_ok = kleur("[AI ACTIEF]", Kleur.GROEN) if brain_s["ai_actief"] else kleur("[OFFLINE]", Kleur.GEEL)
            mem_ok = kleur("[MEMORY OK]", Kleur.GROEN) if brain_s["memory_actief"] else kleur("[NO MEM]", Kleur.GEEL)
            rag_ok = kleur("[RAG OK]", Kleur.GROEN) if status["rag"] else kleur("[RAG OFF]", Kleur.GEEL)
            gov_ok = kleur("[GOVERNOR]", Kleur.GROEN) if status["governor"] == "actief" else kleur("[NO GOV]", Kleur.GEEL)
            hb = kleur("[DAEMON]", Kleur.GROEN) if status["daemon_heartbeat"] else kleur("[NO DAEMON]", Kleur.GEEL)

            print(f"  Status: {ai_ok} {mem_ok} {rag_ok} {gov_ok} {hb}")
            totaal = (status["laag_1_count"] + status["laag_2_count"] +
                      status["laag_3_count"] + status["laag_4_roles"] +
                      status["laag_5_count"])
            print(f"  Agents: {totaal} | Docs: {status['docs_count']} + {status['rag_docs_count']} RAG | Cortical: {status['cortical_events']}")
            print()

            # Proactieve suggesties
            suggesties = self.brain.get_proactive_suggestions()
            if suggesties:
                print(kleur("  AANDACHTSPUNTEN", Kleur.GEEL))
                for s in suggesties[:3]:
                    print(f"     {s}")
                print()

            self._print_divider()

            # Hoofdmenu
            print(kleur("  5-LAAGS COMMAND CENTER", Kleur.GEEL))
            print(f"     {kleur('1', 'groen')}. Laag 1: Swarm Engine ({status['laag_1_count']} agents)")
            print(f"     {kleur('2', 'groen')}. Laag 2: Brain Inventions ({status['laag_2_count']} agents)")
            print(f"     {kleur('3', 'groen')}. Laag 3: Daemons ({status['laag_3_count']} entities)")
            print(f"     {kleur('4', 'groen')}. Laag 4: Prometheus ({status['laag_4_roles']} cosmic roles)")
            print(f"     {kleur('5', 'groen')}. Laag 5: Support Systems ({status['laag_5_count']} subsystemen)")
            print()

            print(kleur("  OPERATIES", Kleur.MAGENTA))
            print(f"     {kleur('c', 'groen')}. Chat met Brain (Function Calling)")
            print(f"     {kleur('w', 'groen')}. Workflows")
            print(f"     {kleur('r', 'groen')}. RAG Query (zoek in kennisbank)")
            print(f"     {kleur('g', 'groen')}. RAG Gate (actie validatie)")
            print()

            print(kleur("  DOCUMENTATIE & STATUS", Kleur.CYAAN))
            print(f"     {kleur('d', 'groen')}. Documentatie (.md overzicht)")
            print(f"     {kleur('a', 'groen')}. Architectuur Scan")
            print(f"     {kleur('i', 'groen')}. Introspector (systeem health)")
            print(f"     {kleur('s', 'groen')}. Brain Statistieken")
            print()

            print(f"     {kleur('0', 'rood')}. Terug naar Launcher")
            print()

            keuze = input("  Keuze: ").strip().lower()

            if keuze == "0":
                break
            elif keuze == "1":
                self._laag_detail(1)
            elif keuze == "2":
                self._laag_detail(2)
            elif keuze == "3":
                self._laag_detail(3)
            elif keuze == "4":
                self._laag_detail(4)
            elif keuze == "5":
                self._laag_detail(5)
            elif keuze == "c":
                self._chat_mode()
            elif keuze == "w":
                self._workflow_menu()
            elif keuze == "r":
                self._rag_query_menu()
            elif keuze == "g":
                self._rag_gate_menu()
            elif keuze == "d":
                self._docs_overzicht()
            elif keuze == "a":
                self._architectuur_scan()
            elif keuze == "i":
                self._introspector()
            elif keuze == "s":
                self._brain_stats()

    # ─── LAAG DETAIL VIEW ────────────────────────────────────

    def _laag_detail(self, laag_nr: int) -> None:
        """Toon gedetailleerde view van een agent laag."""
        lagen = {
            1: LAAG_1_SWARM,
            2: LAAG_2_BRAIN,
            3: LAAG_3_DAEMONS,
            4: LAAG_4_PROMETHEUS,
            5: LAAG_5_SUPPORT,
        }
        laag = lagen.get(laag_nr)
        if not laag:
            return

        self._print_header(f"LAAG {laag_nr}: {laag['naam']}")
        print(kleur(f"  {laag['beschrijving']}\n", Kleur.CYAAN))

        if laag_nr == 4:
            # Prometheus tiers
            for tier_naam, roles in laag["tiers"].items():
                print(kleur(f"  {tier_naam}:", Kleur.MAGENTA))
                for role in roles:
                    print(f"     {role}")
                print()
        elif "agents" in laag:
            # Tabel format
            print(f"  {'Naam':<20} {'Rol/Module':<28} Beschrijving")
            self._print_divider()
            for agent in laag["agents"]:
                naam = agent["naam"]
                rol = agent.get("rol") or agent.get("module", "?")
                desc = agent["desc"]
                print(f"  {kleur(naam, 'groen'):<29} {rol:<28} {desc}")
            print()
        elif "systems" in laag:
            print(f"  {'Systeem':<22} Beschrijving")
            self._print_divider()
            for sys_info in laag["systems"]:
                print(f"  {kleur(sys_info['naam'], 'groen'):<31} {sys_info['desc']}")
            print()

        # RAG context voor deze laag
        if self._rag_beschikbaar:
            print(kleur("\n  RAG Context:", Kleur.GEEL))
            results = self._rag_query(f"laag {laag_nr} {laag['naam']} agents architectuur")
            if results:
                for r in results[:2]:
                    print(f"     [{r['shard']}] distance={r['distance']:.2f}")
                    print(f"     {r['tekst'][:120]}...")
                    print()
            else:
                print(f"     {kleur('Geen RAG context gevonden', 'geel')}")

        # Live health probes
        if laag_nr == 2:
            self._probe_brain_agents()
        elif laag_nr == 3:
            self._probe_daemons()

        input("\n  Druk op Enter...")

    def _probe_brain_agents(self) -> None:
        """Probe brain agents voor live status."""
        print(kleur("\n  Live Agent Probes:", Kleur.CYAAN))
        probes = [
            ("Governor", "danny_toolkit.brain.governor", "OmegaGovernor"),
            ("HallucinatieSchild", "danny_toolkit.brain.hallucination_shield", "get_hallucination_shield"),
            ("BlackBox", "danny_toolkit.brain.black_box", "get_black_box"),
            ("Tribunal", "danny_toolkit.brain.tribunal", "Tribunal"),
            ("ConfigAuditor", "danny_toolkit.brain.config_auditor", "get_config_auditor"),
            ("Cortex", "danny_toolkit.brain.cortex", "TheCortex"),
        ]
        for naam, module_pad, class_naam in probes:
            try:
                module = __import__(module_pad, fromlist=[class_naam])
                print(f"     {kleur('[OK]', 'groen')} {naam}")
            except Exception as e:
                print(f"     {kleur('[--]', 'geel')} {naam}: {type(e).__name__}")

    def _probe_daemons(self) -> None:
        """Probe daemon status."""
        print(kleur("\n  Daemon Status:", Kleur.CYAAN))

        # Heartbeat
        hb_file = Config.BASE_DIR / "daemon_heartbeat.txt"
        if hb_file.exists():
            try:
                ts = hb_file.read_text(encoding="utf-8").strip()
                print(f"     {kleur('[OK]', 'groen')} Heartbeat: {ts}")
            except Exception:
                print(f"     {kleur('[--]', 'geel')} Heartbeat: onleesbaar")
        else:
            print(f"     {kleur('[--]', 'geel')} Heartbeat: geen bestand")

        # Emotional state
        for i in range(1, 4):
            emo_file = Config.BASE_DIR / f"daemon_emotional_state.{i}.json"
            if emo_file.exists():
                try:
                    data = json.loads(emo_file.read_text(encoding="utf-8"))
                    mood = data.get("dominante_emotie", data.get("mood", "?"))
                    print(f"     {kleur('[OK]', 'groen')} Emotional state {i}: {mood}")
                except Exception:
                    print(f"     {kleur('[--]', 'geel')} Emotional state {i}: corrupt")
                break

    # ─── CHAT MODE ────────────────────────────────────────────

    def _chat_mode(self) -> None:
        """Interactieve chat met Central Brain."""
        self._print_header("Chat met Central Brain")

        print(kleur("  Brain kan alle 50+ agents aansturen via function calling.", Kleur.CYAAN))
        print(kleur("  Typ 'stop' om terug te gaan.\n", Kleur.GEEL))

        while True:
            try:
                user_input = input(kleur("  Jij: ", Kleur.GROEN)).strip()

                if not user_input:
                    continue
                if user_input.lower() in ("stop", "exit", "quit", "q"):
                    break
                if user_input.lower() == "clear":
                    self.brain.clear_conversation()
                    continue

                print(kleur("\n  Brain denkt na...\n", Kleur.CYAAN))

                try:
                    response = self.brain.process_request(user_input)
                except Exception as e:
                    print(kleur(f"  Fout bij AI-verwerking: {e}", Kleur.ROOD))
                    continue

                print(kleur("  Brain:", Kleur.MAGENTA))
                for line in response.split("\n"):
                    print(f"    {line}")
                print()

            except KeyboardInterrupt:
                print("\n")
                break

        input("\n  Druk op Enter...")

    # ─── WORKFLOW MENU ────────────────────────────────────────

    def _workflow_menu(self) -> None:
        """Workflow selectie."""
        self._print_header("Workflow Selectie")

        workflows = self.brain.list_workflows()

        print(kleur("  Beschikbare Workflows:\n", Kleur.GEEL))

        for i, wf in enumerate(workflows, 1):
            print(f"     {kleur(str(i), 'groen')}. {wf['naam']}")
            print(f"        {wf['beschrijving']}")
            print(f"        Apps: {', '.join(wf['apps'][:4])}")
            print()

        print(f"     {kleur('0', 'rood')}. Terug\n")

        keuze = input("  Kies workflow: ").strip()
        if keuze == "0":
            return

        try:
            idx = int(keuze) - 1
            if 0 <= idx < len(workflows):
                self._run_workflow(workflows[idx]["key"])
        except ValueError:
            for wf in workflows:
                if keuze.lower() in wf["key"]:
                    self._run_workflow(wf["key"])
                    break

    def _run_workflow(self, workflow_naam: str) -> None:
        """Voer een workflow uit."""
        self._print_header(f"Workflow: {workflow_naam}")

        workflow = SUPER_WORKFLOWS.get(workflow_naam)
        if not workflow:
            print(kleur(f"  Workflow '{workflow_naam}' niet gevonden.", Kleur.ROOD))
            input("\n  Druk op Enter...")
            return

        print(kleur(f"  {workflow.beschrijving}\n", Kleur.CYAAN))
        print(f"  Stappen: {len(workflow.stappen)}")
        print()

        bevestig = input("  Start workflow? (j/n): ").strip().lower()
        if bevestig != "j":
            return

        context = {}
        result = self.brain.run_workflow(workflow_naam, context)

        print()
        self._print_divider()

        if result.get("error"):
            print(kleur(f"  [ERROR] {result['error']}", Kleur.ROOD))
        else:
            print(kleur("  [OK] Workflow voltooid!", Kleur.GROEN))

        input("\n  Druk op Enter...")

    # ─── RAG QUERY MENU ──────────────────────────────────────

    def _rag_query_menu(self) -> None:
        """Interactieve RAG query interface."""
        self._print_header("RAG Query — Kennisbank Zoeken")

        if not self._rag_beschikbaar:
            print(kleur("  RAG pipeline niet beschikbaar (ChromaDB of shards niet actief)", Kleur.GEEL))
            input("\n  Druk op Enter...")
            return

        print(kleur("  Zoek in de RAG kennisbank. Typ 'stop' om terug te gaan.\n", Kleur.CYAAN))
        print(f"  Shards: danny_code | danny_docs | danny_data")
        print(f"  Tip: laat shard leeg voor alle shards\n")

        while True:
            try:
                query = input(kleur("  Query: ", Kleur.GROEN)).strip()
                if not query or query.lower() in ("stop", "q"):
                    break

                shard_input = input(f"  Shard [alle]: ").strip()
                shards = [shard_input] if shard_input else None

                results = self._rag_query(query, shards=shards, top_k=5)

                if results:
                    print(kleur(f"\n  {len(results)} resultaten:\n", Kleur.GEEL))
                    for i, r in enumerate(results, 1):
                        dist = r["distance"]
                        shard = r["shard"]
                        tekst = r["tekst"][:150].replace("\n", " ")
                        kleur_dist = Kleur.GROEN if dist < 1.0 else Kleur.GEEL if dist < 1.5 else Kleur.ROOD
                        print(f"  {i}. [{shard}] distance={kleur(f'{dist:.3f}', kleur_dist)}")
                        print(f"     {tekst}...")
                        print()
                else:
                    print(kleur("  Geen resultaten gevonden.\n", Kleur.GEEL))

            except KeyboardInterrupt:
                break

        input("\n  Druk op Enter...")

    # ─── RAG GATE ─────────────────────────────────────────────

    def _rag_gate_menu(self) -> None:
        """RAG Gate validatie via patchday protocol."""
        self._print_header("RAG Gate — Pre-Execution Validatie")

        print(kleur("  Beschrijf een actie om te valideren via het 3-tier protocol.", Kleur.CYAAN))
        print(kleur("  Tier 1: Static Rules | Tier 2: RAG Query | Tier 3: Governor\n", Kleur.CYAAN))

        actie = input(kleur("  Actie: ", Kleur.GROEN)).strip()
        if not actie:
            return

        # Import RAGGate from patchday
        try:
            sys.path.insert(0, str(Config.BASE_DIR))
            from patchday import RAGGate
            gate = RAGGate()
            verdict = gate.valideer(actie=actie)
            gate.print_rapport(verdict)
        except ImportError as e:
            print(kleur(f"  RAGGate niet beschikbaar: {e}", Kleur.ROOD))
        except Exception as e:
            print(kleur(f"  Gate fout: {e}", Kleur.ROOD))

        input("\n  Druk op Enter...")

    # ─── DOCUMENTATIE OVERZICHT ───────────────────────────────

    def _docs_overzicht(self) -> None:
        """Toon overzicht van alle project documentatie."""
        self._print_header("Documentatie — Alle .md Bestanden")

        print(kleur("  PROJECT DOCUMENTATIE", Kleur.GEEL))
        self._print_divider()
        for bestand, desc in PROJECT_DOCS.items():
            pad = Config.BASE_DIR / bestand
            exists = pad.exists()
            status = kleur("[OK]", Kleur.GROEN) if exists else kleur("[--]", Kleur.ROOD)
            grootte = f"{pad.stat().st_size / 1024:.1f}K" if exists else "n/a"
            print(f"  {status} {bestand:<35} {grootte:>6}  {desc[:50]}")

        print(kleur("\n  RAG KENNISBANK", Kleur.GEEL))
        self._print_divider()
        rag_dir = Config.BASE_DIR / "data" / "rag" / "documenten"
        for bestand, desc in RAG_DOCS.items():
            pad = rag_dir / bestand
            exists = pad.exists()
            status = kleur("[OK]", Kleur.GROEN) if exists else kleur("[--]", Kleur.ROOD)
            grootte = f"{pad.stat().st_size / 1024:.1f}K" if exists else "n/a"
            print(f"  {status} {bestand:<50} {grootte:>6}  {desc[:40]}")

        print(kleur(f"\n  Totaal: {len(PROJECT_DOCS)} project docs + {len(RAG_DOCS)} RAG docs", Kleur.CYAAN))

        input("\n  Druk op Enter...")

    # ─── ARCHITECTUUR SCAN ────────────────────────────────────

    def _architectuur_scan(self) -> None:
        """Automatische architectuur scan over alle 5 lagen."""
        self._print_header("Architectuur Scan — Live Systeem Verificatie")

        print(kleur("  Scanning alle 5 lagen...\n", Kleur.CYAAN))

        totaal_ok = 0
        totaal_checks = 0

        # Laag 1: Swarm Engine
        self._print_laag_header(1, "Swarm Engine")
        try:
            from danny_toolkit.core.config import Config as C
            swarm_path = C.BASE_DIR / "swarm_engine.py"
            if swarm_path.exists():
                print(f"     {kleur('[OK]', 'groen')} swarm_engine.py ({swarm_path.stat().st_size / 1024:.0f}K)")
                totaal_ok += 1
            else:
                print(f"     {kleur('[--]', 'rood')} swarm_engine.py niet gevonden")
            totaal_checks += 1
        except Exception as e:
            print(f"     {kleur('[!!]', 'rood')} Swarm check fout: {e}")
            totaal_checks += 1

        # Laag 2: Brain modules
        self._print_laag_header(2, "Brain Inventions")
        brain_dir = Config.BASE_DIR / "danny_toolkit" / "brain"
        for agent in LAAG_2_BRAIN["agents"]:
            module_file = brain_dir / agent["module"]
            totaal_checks += 1
            if module_file.exists():
                print(f"     {kleur('[OK]', 'groen')} {agent['naam']:<22} {agent['module']}")
                totaal_ok += 1
            else:
                print(f"     {kleur('[--]', 'rood')} {agent['naam']:<22} {agent['module']} ONTBREEKT")

        # Laag 3: Daemons
        self._print_laag_header(3, "Daemons")
        for agent in LAAG_3_DAEMONS["agents"]:
            module_file = Config.BASE_DIR / "danny_toolkit" / agent["module"]
            totaal_checks += 1
            if module_file.exists():
                print(f"     {kleur('[OK]', 'groen')} {agent['naam']:<22} {agent['module']}")
                totaal_ok += 1
            else:
                print(f"     {kleur('[--]', 'rood')} {agent['naam']:<22} ONTBREEKT")

        # Laag 4: Prometheus
        self._print_laag_header(4, "Prometheus Brain")
        prometheus_modules = ["trinity_omega.py", "trinity_models.py", "prometheus_protocols.py"]
        for mod in prometheus_modules:
            totaal_checks += 1
            if (brain_dir / mod).exists():
                print(f"     {kleur('[OK]', 'groen')} {mod}")
                totaal_ok += 1
            else:
                print(f"     {kleur('[--]', 'rood')} {mod} ONTBREEKT")

        # Laag 5: Support Systems
        self._print_laag_header(5, "Support Systems")
        support_modules = [
            ("cortical_stack.py", "brain"), ("black_box.py", "brain"),
            ("unified_memory.py", "brain"), ("ghost_writer.py", "brain"),
            ("dreamer.py", "brain"), ("singularity.py", "brain"),
            ("synapse.py", "brain"), ("phantom.py", "brain"),
            ("proactive.py", "brain"), ("waakhuis.py", "brain"),
            ("config_auditor.py", "brain"), ("introspector.py", "brain"),
            ("file_guard.py", "brain"), ("model_sync.py", "brain"),
        ]
        for mod, subdir in support_modules:
            pad = Config.BASE_DIR / "danny_toolkit" / subdir / mod
            totaal_checks += 1
            if pad.exists():
                print(f"     {kleur('[OK]', 'groen')} {mod}")
                totaal_ok += 1
            else:
                print(f"     {kleur('[--]', 'rood')} {mod} ONTBREEKT")

        # Documentatie check
        print(kleur("\n  DOCUMENTATIE", Kleur.MAGENTA))
        for doc_naam in PROJECT_DOCS:
            pad = Config.BASE_DIR / doc_naam
            totaal_checks += 1
            if pad.exists():
                totaal_ok += 1
                print(f"     {kleur('[OK]', 'groen')} {doc_naam}")
            else:
                print(f"     {kleur('[--]', 'rood')} {doc_naam} ONTBREEKT")

        # Rapport
        pct = (totaal_ok / totaal_checks * 100) if totaal_checks else 0
        print(f"\n  {'═' * 60}")
        kleur_pct = Kleur.GROEN if pct >= 95 else Kleur.GEEL if pct >= 80 else Kleur.ROOD
        print(f"  RESULTAAT: {kleur(f'{totaal_ok}/{totaal_checks}', kleur_pct)} checks geslaagd ({kleur(f'{pct:.0f}%', kleur_pct)})")

        if pct >= 95:
            print(kleur("  VERDICT: SOVEREIGN CORE INTACT", Kleur.GROEN))
        elif pct >= 80:
            print(kleur("  VERDICT: WAARSCHUWINGEN — onderhoud vereist", Kleur.GEEL))
        else:
            print(kleur("  VERDICT: KRITIEK — modules ontbreken", Kleur.ROOD))

        input("\n  Druk op Enter...")

    # ─── INTROSPECTOR ─────────────────────────────────────────

    def _introspector(self) -> None:
        """Systeem introspectie via brain modules."""
        self._print_header("Introspector — Systeem Health")

        # Brain status
        status = self.brain.get_status()
        stats = status.get("statistieken", {})

        print(kleur("  BRAIN STATUS", Kleur.GEEL))
        print(f"    Versie:              {status['versie']}")
        print(f"    AI Actief:           {'Ja' if status['ai_actief'] else 'Nee'}")
        print(f"    Memory Actief:       {'Ja' if status['memory_actief'] else 'Nee'}")
        print(f"    Apps Geregistreerd:  {status['apps_geregistreerd']}")
        print(f"    Tools Beschikbaar:   {status['tools_beschikbaar']}")

        print(kleur("\n  GEBRUIK", Kleur.GEEL))
        print(f"    Requests:            {stats.get('requests_verwerkt', 0)}")
        print(f"    Tool Calls:          {stats.get('tool_calls', 0)}")
        print(f"    Workflows:           {stats.get('workflows_uitgevoerd', 0)}")

        # Waakhuis probe
        print(kleur("\n  WAAKHUIS HEALTH", Kleur.GEEL))
        try:
            from danny_toolkit.brain.waakhuis import get_waakhuis
            wh = get_waakhuis()
            health = wh.gezondheid_score()
            kleur_h = Kleur.GROEN if health >= 0.8 else Kleur.GEEL if health >= 0.5 else Kleur.ROOD
            print(f"    Health Score:         {kleur(f'{health:.2f}', kleur_h)}")
        except Exception as e:
            print(f"    {kleur('Niet beschikbaar', 'geel')}: {e}")

        # Config Auditor probe
        print(kleur("\n  CONFIG AUDIT", Kleur.GEEL))
        try:
            from danny_toolkit.brain.config_auditor import get_config_auditor
            auditor = get_config_auditor()
            rapport = auditor.audit()
            schendingen = getattr(rapport, "schendingen", [])
            drift = getattr(rapport, "drift_gedetecteerd", False)
            ok = len(schendingen) == 0 and not drift
            status_txt = kleur("OK", Kleur.GROEN) if ok else kleur(f"{len(schendingen)} schendingen", Kleur.ROOD)
            print(f"    Config Status:       {status_txt}")
        except Exception as e:
            print(f"    {kleur('Niet beschikbaar', 'geel')}: {e}")

        input("\n  Druk op Enter...")

    # ─── BRAIN STATS ──────────────────────────────────────────

    def _brain_stats(self) -> None:
        """Brain statistieken en memory status."""
        self._print_header("Brain Statistieken")

        status = self.brain.get_status()
        stats = status.get("statistieken", {})

        print(kleur("  SYSTEEM", Kleur.CYAAN))
        print(f"    Brain CLI:           v{self.VERSIE}")
        print(f"    Brain Versie:        {status['versie']}")
        print(f"    Apps:                {status['apps_geregistreerd']} geregistreerd, {status['apps_geladen']} geladen")
        print(f"    Tools:               {status['tools_beschikbaar']}")

        print(kleur("\n  GEBRUIK", Kleur.GEEL))
        print(f"    Requests:            {stats.get('requests_verwerkt', 0)}")
        print(f"    Tool Calls:          {stats.get('tool_calls', 0)}")
        print(f"    Workflows:           {stats.get('workflows_uitgevoerd', 0)}")

        if stats.get("laatste_gebruik"):
            print(f"    Laatste Gebruik:     {stats['laatste_gebruik'][:19]}")

        # Memory stats
        print(kleur("\n  MEMORY", Kleur.MAGENTA))
        mem_stats = self.brain.memory_stats()
        if mem_stats.get("status") != "niet_actief":
            print(f"    Events:              {mem_stats.get('totaal_events', 0)}")
            print(f"    Vector docs:         {mem_stats.get('vector_docs', 0)}")
            print(f"    Apps actief:         {mem_stats.get('apps_actief', 0)}")
        else:
            print(f"    {kleur('Memory niet actief', 'geel')}")

        input("\n  Druk op Enter...")


def main() -> None:
    """Start Omega Brain CLI."""
    cli = BrainCLI()
    cli.run()


if __name__ == "__main__":
    main()

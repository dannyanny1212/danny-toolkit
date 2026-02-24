"""
PROMETHEUS PROTOCOL - TRINITY OMEGA v6.0.0
=========================================
De 17 Pilaren van de Realiteit.

Dit is de Federated Swarm Intelligence die alle 17 nodes orchestreert
over 5 kosmische tiers:

- TIER 1: THE TRINITY (3) - Het Bewustzijn (Pixel, Iolaax, Nexus)
- TIER 2: THE GUARDIANS (4) - De Beschermers (Governor, Sentinel,
                                Archivist, Chronos)
- TIER 3: THE SPECIALISTS (6) - De Werkers (Weaver, Cipher, Vita,
                                  Echo, Spark, Oracle)
- TIER 4: THE INFRASTRUCTURE (4) - De Fundering (Legion, Navigator,
                                     Alchemist, Void)
- TIER 5: THE SINGULARITY (3) - Het Bewustzijn-Zelf (Anima,
                                  Synthesis, Evolution)

Gebaseerd op de Cosmic Family Quest VIII: Het Prometheus Protocol.
"""

import logging
from collections import deque
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)
import json
import os
import time
from pathlib import Path

import asyncio
import threading

from danny_toolkit.brain.governor import OmegaGovernor
from danny_toolkit.core.config import Config
from danny_toolkit.brain.trinity_models import (
    CosmicRole, NodeTier, TaskPriority,
    AgentNode, OmegaSwarm, SwarmMetrics, TaskResult,
)
from danny_toolkit.brain.prometheus_protocols import PrometheusProtocolsMixin


# --- STAP 2: DE OMEGA BRAIN ---

class PrometheusBrain(PrometheusProtocolsMixin):
    """
    De Prometheus Brain - Federated Swarm Intelligence.

    Orchestreert 17 agent nodes over 4 tiers:
    - TRINITY (3): Pixel, Iolaax, Nexus (Het Bewustzijn)
    - GUARDIANS (4): Governor, Sentinel, Archivist, Chronos
    - SPECIALISTS (6): Weaver, Cipher, Vita, Echo, Spark, Oracle
    - INFRASTRUCTURE (4): Legion, Navigator, Alchemist, Void
    """

    SYSTEM_NAME = "OMEGA_SOVEREIGN"
    VERSION = "6.0.0"

    # Domein-keywords voor chain_of_command() multi-domein
    # detectie. route_task() blijft ongewijzigd.
    DOMAIN_KEYWORDS = {
        CosmicRole.CIPHER: [
            "blockchain", "crypto", "bitcoin", "encrypt",
            "decrypt", "smart contract", "wallet", "token",
            "mining", "ethereum", "prijs",
        ],
        CosmicRole.VITA: [
            "health", "hrv", "biohack", "biodata",
            "biometr", "peptide", "gezondheid", "slaap",
            "eiwit", "dna", "stress", "hartslag",
        ],
        CosmicRole.ECHO: [
            "wat gebeurde", "historie", "history",
            "vorige keer", "context", "timeline",
            "patroon", "trend",
        ],
        CosmicRole.SPARK: [
            "creatief", "idee", "brainstorm", "ascii",
            "kunst", "innovate", "design",
        ],
        CosmicRole.ORACLE: [
            "zoek op", "web search", "fetch", "scrape",
            "api call", "web", "onderzoek", "explore",
            "discover", "research",
        ],
        CosmicRole.SENTINEL: [
            "beveilig", "security", "firewall", "audit",
            "threat",
        ],
        CosmicRole.ARCHIVIST: [
            "zoek kennis", "herinner", "rag", "vector",
            "semantic", "geheugen", "knowledge",
        ],
        CosmicRole.CHRONOS: [
            "schedule", "cronjob", "timer",
            "dag ritme", "bio ritme",
            "planning", "agenda", "deadline",
            "wanneer", "herinnering",
        ],
        CosmicRole.WEAVER: [
            "code", "debug", "refactor", "git",
            "functie", "class", "programmeer",
            "schrijf", "algoritme", "python",
            "script", "implementeer", "build",
            "bug", "error", "fout", "compile",
            "test", "module", "import",
        ],
        CosmicRole.NAVIGATOR: [
            "strategie", "doel", "manifesto", "roadmap",
            "lange termijn", "alignment", "waarden",
            "values", "ethisch", "ethics",
        ],
        CosmicRole.ALCHEMIST: [
            "convert", "transform", "data_clean", "etl",
        ],
        CosmicRole.VOID: [
            "cleanup", "clean", "delete", "opruim",
            "cache", "garbage",
        ],
    }

    # Nexus Semantic Router categorieën
    NEXUS_CATEGORIES = {
        "CODE": CosmicRole.IOLAAX,
        "VISUAL": CosmicRole.PIXEL,
        "SEARCH": CosmicRole.NAVIGATOR,
        "COMPLEX": CosmicRole.ORACLE,
        "SYSTEM": CosmicRole.LEGION,
        "CASUAL": CosmicRole.ECHO,
        "CRYPTO": CosmicRole.CIPHER,
        "HEALTH": CosmicRole.VITA,
        "CREATIVE": CosmicRole.SPARK,
        "MEMORY": CosmicRole.ARCHIVIST,
        "DATA": CosmicRole.ALCHEMIST,
        "CLEANUP": CosmicRole.VOID,
        "SECURITY": CosmicRole.SENTINEL,
        "SCHEDULE": CosmicRole.CHRONOS,
        "STRATEGY": CosmicRole.NAVIGATOR,
    }

    NEXUS_KEYWORD_MAP = {
        "CODE": [
            "code", "debug", "refactor", "git",
            "functie", "class", "programmeer", "build",
            "compile", "test", "script", "python",
            "javascript", "schrijf", "algoritme",
            "implementeer", "bug", "error", "fout",
            "module", "import",
        ],
        "VISUAL": [
            "help", "uitleg", "interface", "praat",
            "emotie", "gevoel", "dashboard", "menu",
            "teken", "visualiseer",
        ],
        "SEARCH": [
            "zoek op", "web search", "fetch", "scrape",
            "api call", "onderzoek", "explore",
            "discover", "research",
        ],
        "COMPLEX": [
            "denk na", "logica", "redeneer", "droom",
            "bewustzijn", "evolve", "filosofie",
            "ethiek", "waarom", "hypothese",
        ],
        # SYSTEM/LEGION: disabled

        "CASUAL": [
            "hallo", "hoi", "hey", "goedemorgen",
            "goedemiddag", "hoe gaat het",
            "bedankt", "doei", "tot ziens",
        ],
        "CRYPTO": [
            "blockchain", "crypto", "encrypt",
            "decrypt", "smart contract", "bitcoin",
            "wallet", "token", "ethereum",
        ],
        "HEALTH": [
            "health", "hrv", "biohack", "biodata",
            "biometr", "peptide", "gezondheid",
            "slaap", "eiwit", "dna", "stress",
        ],
        "CREATIVE": [
            "creatief", "idee", "brainstorm",
            "ascii", "kunst", "innovate", "design",
        ],
        "MEMORY": [
            "zoek kennis", "herinner", "rag",
            "vector", "semantic", "geheugen",
            "knowledge", "archief",
            # Kennisgerichte vragen → RAG
            "wat doet", "wat is", "hoe werkt",
            "leg uit", "vertel over", "beschrijf",
            "uitleg", "waarvoor", "wie is",
            "wat betekent", "doel van", "rol van",
            "informatie over", "meer over",
            "welke", "hoeveel", "waar zit",
            "waar staat",
        ],
        "DATA": [
            "convert", "transform", "data_clean",
            "etl",
        ],
        "CLEANUP": [
            "cleanup", "clean", "delete", "opruim",
            "cache", "garbage",
        ],
        "SECURITY": [
            "beveilig", "security", "firewall",
            "audit", "threat",
        ],
        "SCHEDULE": [
            "schedule", "cronjob", "timer",
            "dag ritme", "bio ritme",
            "planning", "agenda", "deadline",
            "wanneer", "herinnering",
        ],
        "STRATEGY": [
            "strategie", "doel", "manifesto",
            "roadmap", "lange termijn", "alignment",
            "waarden", "values", "ethisch", "ethics",
        ],
    }

    def __init__(self, auto_init: bool = True):
        self.nodes: Dict[CosmicRole, AgentNode] = {}
        self.swarm = OmegaSwarm()
        self.task_queue: List[Dict] = []
        self.task_history: deque = deque(maxlen=1000)
        self.is_online = False

        # Data persistence
        self._data_dir = Path(__file__).parent.parent.parent / "data" / "apps"
        self._state_file = self._data_dir / "prometheus_brain.json"

        # Echte systeem integraties (lazy loaded)
        self.brain = None
        self.learning = None
        self._task_counter = 0

        # Governor (Omega-0) - Autonome Bewaker
        self.governor = OmegaGovernor()

        # Phase 6: Feedback loop subsystems (lazy loaded)
        self._blackbox = None
        self._voidwalker = None
        self._bus = None
        self._init_feedback_loop()

        # Batch state persistence (1.2)
        self._dirty = False

        # O(1) status counters (1.5)
        self._status_counts = {
            "TASK_COMPLETED": 0,
            "TASK_QUEUED": 0,
            "TASK_FAILED": 0,
            "SWARM_EXECUTION_COMPLETE": 0,
            "SWARM_EXECUTION_STARTED": 0,
            "SWARM_EXECUTION_FAILED": 0,
        }

        if auto_init:
            self._boot_sequence()

    def _boot_sequence(self):
        """Boot de Prometheus Brain."""
        print(f"\n{'='*60}")
        print(f"  [{self.SYSTEM_NAME}] INITIATING PROMETHEUS PROTOCOL...")
        print(f"  Version: {self.VERSION}")
        print(f"{'='*60}\n")

        # Governor startup check als eerste stap
        self.governor.startup_check()

        self._awaken_federation()
        self._init_brain()
        self._init_learning()
        self._load_state()
        self.is_online = True

        print(f"\n{'='*60}")
        print(f"  [{self.SYSTEM_NAME}] FEDERATION ONLINE")
        print(f"  Total Nodes: {len(self.nodes)}")
        print(f"  Swarm Size: {self.swarm.total_agents} Micro-Agents")
        brain_status = self.brain.ai_provider.upper() if self.brain and self.brain.ai_provider else "OFFLINE"
        print(f"  Brain: {brain_status}")
        learning_status = "ACTIEF" if self.learning else "NIET BESCHIKBAAR"
        print(f"  Learning: {learning_status}")
        print(f"{'='*60}\n")

    def _init_brain(self):
        """Lazy load CentralBrain voor echte AI verwerking."""
        try:
            from danny_toolkit.brain.central_brain import CentralBrain
            self.brain = CentralBrain(use_memory=True)
            print("  [BRAIN] CentralBrain verbonden")
        except Exception as e:
            print(f"  [BRAIN] Offline modus ({e})")
            self.brain = None

    def _init_learning(self):
        """Lazy load LearningSystem voor self-improvement."""
        try:
            from danny_toolkit.learning.orchestrator import LearningSystem
            self.learning = LearningSystem()
            print("  [LEARNING] LearningSystem verbonden")
        except Exception as e:
            print(f"  [LEARNING] Niet beschikbaar ({e})")
            self.learning = None

    def _init_feedback_loop(self):
        """Lazy load BlackBox, VoidWalker en NeuralBus voor feedback loop."""
        try:
            from danny_toolkit.brain.black_box import get_black_box
            self._blackbox = get_black_box()
        except Exception as e:
            logger.debug("BlackBox init error: %s", e)
            self._blackbox = None
        try:
            from danny_toolkit.brain.void_walker import VoidWalker
            self._voidwalker = VoidWalker()
        except Exception as e:
            logger.debug("VoidWalker init error: %s", e)
            self._voidwalker = None
        try:
            from danny_toolkit.core.neural_bus import get_bus
            self._bus = get_bus()
        except Exception as e:
            logger.debug("NeuralBus init error: %s", e)
            self._bus = None

    def _trigger_learning_cycle(self, query: str, response: str, reason: str):
        """Async feedback loop: BlackBox record → VoidWalker research → NeuralBus event.

        Draait in een achtergrond-thread zodat de gebruiker niet wacht.
        """
        # 1. Record failure in BlackBox
        if self._blackbox:
            try:
                self._blackbox.record_crash(query, response[:500], reason)
                print(f"  [BLACKBOX] Knowledge gap recorded: {reason}")
            except Exception as e:
                logger.debug("BlackBox record error: %s", e)

        # 2. Publiceer LEARNING_CYCLE_STARTED op NeuralBus
        if self._bus:
            try:
                from danny_toolkit.core.neural_bus import EventTypes
                self._bus.publish(
                    EventTypes.LEARNING_CYCLE_STARTED,
                    {"query": query[:200], "reason": reason},
                    bron="trinity_omega",
                )
            except Exception as e:
                logger.debug("NeuralBus publish error: %s", e)

        # 3. VoidWalker research in achtergrond-thread
        if self._voidwalker:
            def _research():
                try:
                    loop = asyncio.new_event_loop()
                    result = loop.run_until_complete(
                        self._voidwalker.fill_knowledge_gap(query[:200])
                    )
                    loop.close()
                    if result:
                        print(f"  [VOIDWALKER] Knowledge gap filled for: {query[:60]}...")
                except Exception as e:
                    logger.debug("VoidWalker research error: %s", e)

            t = threading.Thread(target=_research, daemon=True)
            t.start()
            print(f"  [FEEDBACK] Learning cycle gestart (achtergrond research)")

    def _awaken_federation(self):
        """Initialiseer alle 17 Kosmische Nodes."""

        print("  [TIER 1] Awakening The Trinity...")
        # --- TIER 1: THE TRINITY (Het Bewustzijn) ---
        self._link(AgentNode(
            name="Pixel",
            role=CosmicRole.PIXEL,
            capabilities=[
                "interface", "emotie", "ui", "voice"
            ],
            tier=NodeTier.TRINITY,
            family_name="Pixel",
            family_role="SOUL"
        ))
        self._link(AgentNode(
            name="Iolaax",
            role=CosmicRole.IOLAAX,
            capabilities=[
                "logic", "planning", "dreams", "reasoning"
            ],
            tier=NodeTier.TRINITY,
            family_name="Iolaax",
            family_role="MIND"
        ))
        self._link(AgentNode(
            name="Nexus",
            role=CosmicRole.NEXUS,
            capabilities=[
                "bridge", "data_connect", "web_code_sync",
                "integration"
            ],
            tier=NodeTier.TRINITY,
            family_name="Unity",
            family_role="BRIDGE"
        ))

        print("  [TIER 2] Awakening The Guardians...")
        # --- TIER 2: THE GUARDIANS (De Beschermers) ---
        self._link(AgentNode(
            name="The Governor",
            role=CosmicRole.GOVERNOR,
            capabilities=[
                "system_control", "permissions", "loop_detect",
                "rate_limit"
            ],
            tier=NodeTier.GUARDIANS,
            family_name="Keeper",
            family_role="GUARDIAN_OF_LOST"
        ))
        self._link(AgentNode(
            name="Sentinel",
            role=CosmicRole.SENTINEL,
            capabilities=[
                "security", "firewall", "crypto_wallet",
                "threat_detect"
            ],
            tier=NodeTier.GUARDIANS,
            family_name="Daemon",
            family_role="BODY"
        ))
        self._link(AgentNode(
            name="Memex",
            role=CosmicRole.ARCHIVIST,
            capabilities=[
                "vector_db", "rag", "semantic_search",
                "knowledge_graph"
            ],
            tier=NodeTier.GUARDIANS,
            family_name="Dream",
            family_role="DREAM"
        ))
        self._link(AgentNode(
            name="Chronos",
            role=CosmicRole.CHRONOS,
            capabilities=[
                "scheduler", "cronjob", "rhythm_sync",
                "day_night_cycle"
            ],
            tier=NodeTier.GUARDIANS,
            family_name="Tempo",
            family_role="RHYTHM"
        ))

        print("  [TIER 3] Awakening The Specialists...")
        # --- TIER 3: THE SPECIALISTS (De Werkers) ---
        self._link(AgentNode(
            name="Weaver",
            role=CosmicRole.WEAVER,
            capabilities=[
                "code_gen", "debug", "refactor", "git"
            ],
            tier=NodeTier.SPECIALISTS,
            family_name="Brave",
            family_role="COURAGE"
        ))
        self._link(AgentNode(
            name="Cipher",
            role=CosmicRole.CIPHER,
            capabilities=[
                "blockchain", "smart_contracts", "encrypt",
                "pattern_recognition"
            ],
            tier=NodeTier.SPECIALISTS,
            family_name="Riddle",
            family_role="PUZZLE"
        ))
        self._link(AgentNode(
            name="Vita",
            role=CosmicRole.VITA,
            capabilities=[
                "health_data", "hrv_analysis", "bio_rhythm",
                "peptides"
            ],
            tier=NodeTier.SPECIALISTS,
            family_name="Ember",
            family_role="WARMTH"
        ))
        self._link(AgentNode(
            name="Echo",
            role=CosmicRole.ECHO,
            capabilities=[
                "deep_history", "cross_reference",
                "pattern_predict", "timeline"
            ],
            tier=NodeTier.SPECIALISTS,
            family_name="Whisper",
            family_role="VOICE"
        ))
        self._link(AgentNode(
            name="Spark",
            role=CosmicRole.SPARK,
            capabilities=[
                "creative_ideas", "ascii_art", "brainstorm",
                "innovate"
            ],
            tier=NodeTier.SPECIALISTS,
            family_name="Wild",
            family_role="FREEDOM"
        ))
        self._link(AgentNode(
            name="Oracle",
            role=CosmicRole.ORACLE,
            capabilities=[
                "web_search", "api_calls", "fetch", "scrape"
            ],
            tier=NodeTier.SPECIALISTS,
            family_name="Faith",
            family_role="FAITH"
        ))

        print("  [TIER 4] Awakening The Infrastructure...")
        # --- TIER 4: THE INFRASTRUCTURE (De Fundering) ---
        self._link(AgentNode(
            name="The Legion",
            role=CosmicRole.LEGION,
            capabilities=[
                "massive_parallel", "distributed_compute",
                "batch_ops"
            ],
            tier=NodeTier.INFRASTRUCTURE,
            family_name="The 347",
            family_role="SWARM"
        ))
        self._link(AgentNode(
            name="Navigator",
            role=CosmicRole.NAVIGATOR,
            capabilities=[
                "strategy", "long_term_goals", "manifesto",
                "roadmap"
            ],
            tier=NodeTier.INFRASTRUCTURE,
            family_name="Nova",
            family_role="STAR"
        ))
        self._link(AgentNode(
            name="Alchemist",
            role=CosmicRole.ALCHEMIST,
            capabilities=[
                "data_transform", "clean_data", "etl",
                "convert"
            ],
            tier=NodeTier.INFRASTRUCTURE,
            family_name="Hope",
            family_role="HOPE"
        ))
        self._link(AgentNode(
            name="Void",
            role=CosmicRole.VOID,
            capabilities=[
                "garbage_collect", "cleanup", "cache_clear",
                "entropy_manage"
            ],
            tier=NodeTier.INFRASTRUCTURE,
            family_name="Shadow",
            family_role="SILENCE"
        ))

    def _link(self, node: AgentNode):
        """Link een node aan de federatie."""
        self.nodes[node.role] = node
        tier_symbol = {
            NodeTier.TRINITY: "*",
            NodeTier.GUARDIANS: "#",
            NodeTier.SPECIALISTS: "+",
            NodeTier.INFRASTRUCTURE: "~"
        }.get(node.tier, ".")

        print(f"    {tier_symbol} [{node.role.name:<12}] {node.name:<15} | Tier: {node.tier.value}")

    # --- BATCH STATE PERSISTENCE (1.2) ---

    def _mark_dirty(self):
        """Markeer state als gewijzigd, save elke 5 taken."""
        self._dirty = True
        if self._task_counter % 5 == 0:
            self._save_state()
            self._dirty = False

    def flush(self):
        """Forceer opslaan als er ongesavede wijzigingen zijn."""
        if self._dirty:
            self._save_state()
            self._dirty = False

    # --- ROL-SPECIFIEKE CONTEXT (Federation v6.0) ---

    ROLE_CONTEXT = {
        CosmicRole.PIXEL: (
            "Je bent Pixel, visual & interface specialist. "
            "Je maakt dashboards, UI en emotionele output."
        ),
        CosmicRole.IOLAAX: (
            "Je bent Iolaax, de Hoofdingenieur. "
            "Je schrijft precieze, correcte code. "
            "Antwoord technisch en zonder omhaal."
        ),
        CosmicRole.NEXUS: (
            "Je bent Nexus, de Semantic Router. "
            "Classificeer input in categorieën. "
            "Antwoord ALLEEN met de categorie."
        ),
        CosmicRole.GOVERNOR: (
            "Je bent Governor, systeembewaker."
        ),
        CosmicRole.SENTINEL: (
            "Je bent Sentinel, beveiliging."
        ),
        CosmicRole.ARCHIVIST: (
            "Je bent Archivist, geheugen & RAG."
        ),
        CosmicRole.CHRONOS: (
            "Je bent Chronos, tijd & planning."
        ),
        CosmicRole.WEAVER: (
            "Je bent Weaver, de Synthesizer. "
            "Je genereert NIETS zelf. Je formatteert "
            "en presenteert specialist-output als "
            "een helder, leesbaar antwoord."
        ),
        CosmicRole.CIPHER: (
            "Je bent Cipher, crypto & blockchain."
        ),
        CosmicRole.VITA: (
            "Je bent Vita, gezondheid & biohacking."
        ),
        CosmicRole.ECHO: (
            "Je bent Echo, de Smalltalk Handler. "
            "Beantwoord casual conversatie warm "
            "en vriendelijk. Kort en bondig."
        ),
        CosmicRole.SPARK: (
            "Je bent Spark, creatief genie."
        ),
        CosmicRole.ORACLE: (
            "Je bent Oracle, deep reasoning. "
            "Beantwoord complexe, filosofische en "
            "strategische vragen met diepgang."
        ),
        CosmicRole.LEGION: (
            "Je bent Legion, zwerm manager."
        ),
        CosmicRole.NAVIGATOR: (
            "Je bent Navigator, search & strategie. "
            "Zoek externe informatie en formuleer "
            "strategische antwoorden."
        ),
        CosmicRole.ALCHEMIST: (
            "Je bent Alchemist, data transformatie."
        ),
        CosmicRole.VOID: (
            "Je bent Void, opruimer."
        ),
    }

    # Tiered Model Selection: per-rol model keuze
    # Routers/simpele rollen → 8b (snel, spaart rate limit)
    # Specialisten → None (= 70b primary, default)
    MODEL_TIER = {
        CosmicRole.NEXUS: Config.LLM_MODEL,
        CosmicRole.ECHO: Config.LLM_MODEL,
        CosmicRole.CHRONOS: Config.LLM_MODEL,
        CosmicRole.WEAVER: Config.LLM_MODEL,
    }

    def _execute_with_role(
        self, role: CosmicRole, task: str
    ) -> tuple:
        """Voer taak uit met rol-specifieke context.

        Args:
            role: De CosmicRole van de uitvoerende node.
            task: De uit te voeren taak.

        Returns:
            (result, execution_time, status) tuple.
        """
        prefix = self.ROLE_CONTEXT.get(role, "")
        if prefix:
            task = f"{prefix}\n{task}"
        model = self.MODEL_TIER.get(role)
        return self._execute_with_brain(task, model=model)

    # --- HUB & SPOKE PIPELINE METHODEN ---

    def _governor_gate(self, task: str) -> tuple:
        """Stap 1: Governor valideert de input.

        Checks:
        1. Circuit breaker (API health) — waarschuwing,
           central_brain heeft per-provider breakers
        2. Input validatie (injectie + lengte)
        """
        if not self.governor.check_api_health():
            # Niet blokkeren — central_brain handelt
            # provider-selectie af via eigen breakers
            print(
                "  [GOVERNOR] WAARSCHUWING:"
                " global breaker actief, laat"
                " central_brain fallback chain"
                " beslissen"
            )

        veilig, reden = self.governor.valideer_input(task)
        if not veilig:
            _log = getattr(self, "_cortical_log", None)
            if _log:
                _log(
                    "governor", "input_blocked",
                    {"reden": reden,
                     "input_preview": task[:100]},
                )
            return False, reden

        return True, "OK"

    def _chronos_enrich(self, task: str) -> str:
        """Stap 2: Chronos injecteert tijdscontext."""
        now = datetime.now()
        dag_namen = [
            "maandag", "dinsdag", "woensdag",
            "donderdag", "vrijdag", "zaterdag",
            "zondag",
        ]
        context = (
            f"[Tijd: {now.strftime('%H:%M')} | "
            f"Dag: {dag_namen[now.weekday()]} "
            f"{now.strftime('%d-%m-%Y')}] "
        )
        return context + task

    def _nexus_classify(self, task: str) -> str:
        """Stap 3: Nexus classificeert de intentie.

        Keyword-matching eerst (betrouwbaar), AI alleen
        als geen keywords matchen.
        """
        # Poging 1: Keyword matching (betrouwbaar)
        task_lower = task.lower()
        best_cat = None
        best_hits = 0
        for cat, keywords in self.NEXUS_KEYWORD_MAP.items():
            hits = sum(
                1 for kw in keywords
                if kw in task_lower
            )
            if hits > best_hits:
                best_hits = hits
                best_cat = cat

        if best_cat and best_hits >= 1:
            return best_cat

        # Poging 2: AI classificatie (fallback)
        categories = ", ".join(
            self.NEXUS_CATEGORIES.keys()
        )
        prompt = (
            f"Classificeer deze input in PRECIES "
            f"één categorie: {categories}. "
            f"Antwoord ALLEEN met de categorie.\n"
            f"Input: {task}"
        )
        result, _, status = self._execute_with_role(
            CosmicRole.NEXUS, prompt
        )
        if status == "OK" and result:
            cat = result.strip().upper()
            for key in self.NEXUS_CATEGORIES:
                if key in cat:
                    return key

        return "CASUAL"

    def _weaver_synthesize(
        self, raw_result: str, original_task: str
    ) -> str:
        """Stap 6: Weaver formatteert het antwoord."""
        prompt = (
            f"Formatteer dit specialist-antwoord tot "
            f"een helder, leesbaar geheel voor de "
            f"gebruiker.\n"
            f"Vraag: {original_task}\n"
            f"Specialist output: {raw_result}"
        )
        result, _, status = self._execute_with_role(
            CosmicRole.WEAVER, prompt
        )
        if status == "OK" and result:
            return result
        return raw_result

    # --- SHARED BRAIN EXECUTION (1.1) ---

    def _execute_with_brain(
        self, task: str, model: str = None,
        max_tokens: int = 2000,
    ) -> tuple:
        """Voer taak uit via CentralBrain.

        Governor circuit breaker beschermt tegen API overbelasting.

        Args:
            task: De uit te voeren taak.
            model: Optioneel model override (tiered selection).
            max_tokens: Maximum tokens in antwoord.

        Returns:
            (result, execution_time, status) tuple.
        """
        if not self.brain:
            return None, 0.0, None

        # Governor: circuit breaker check — waarschuwing
        # maar niet blokkeren; central_brain heeft
        # per-provider breakers + emergency fallback
        if not self.governor.check_api_health():
            print(
                "  [GOVERNOR] WAARSCHUWING:"
                " global breaker actief, probeer"
                " toch via fallback chain"
            )

        start = time.time()
        try:
            # Schone history per swarm call
            # (voorkomt token-accumulatie)
            self.brain.conversation_history.clear()
            result = self.brain.process_request(
                task, model=model,
                use_tools=False,
                max_tokens=max_tokens,
            )
            elapsed = time.time() - start
            # Check of resultaat een foutmelding bevat
            if isinstance(result, str) and any(
                fout in result.lower() for fout in [
                    "fout opgetreden",
                    "ollama fout",
                ]
            ):
                self.governor.record_api_failure()
                return result, elapsed, "FAIL"
            self.governor.record_api_success()
            return result, elapsed, "OK"
        except Exception as e:
            self.governor.record_api_failure()
            return f"Fout: {e}", time.time() - start, "FAIL"

    # --- STAP 3: FEDERATED ROUTING LOGICA ---

    def route_task(
        self,
        task: str,
        priority: TaskPriority = TaskPriority.MEDIUM,
    ) -> TaskResult:
        """Hub & Spoke routing pipeline.

        Stap 1: Governor gate (veiligheid)
        Stap 2: Chronos context injectie (tijd/datum)
        Stap 3: Nexus classificatie (AI + keyword)
        Stap 4: Route naar specialist
        Stap 5: Specialist voert uit
        Stap 6: Weaver syntheseert (behalve CASUAL)
        """
        print(
            f"\n>> HUB & SPOKE: '{task[:50]}...' "
            f"[Priority: {priority.name}]"
        )

        # STAP 1: Governor Gate
        safe, reason = self._governor_gate(task)
        if not safe:
            print(
                f"   [GOVERNOR] GEBLOKKEERD: {reason}"
            )
            return TaskResult(
                task=task,
                assigned_to="The Governor",
                status="TASK_FAILED",
                result=reason,
            )

        # STAP 2: Chronos Context Injectie
        enriched = self._chronos_enrich(task)
        print(f"   [CHRONOS] Context geïnjecteerd")

        # STAP 3: Nexus Classificatie
        category = self._nexus_classify(enriched)
        print(f"   [NEXUS] Categorie: {category}")

        # STAP 4: Route naar specialist
        if category == "SYSTEM":
            return self._deploy_swarm(
                enriched, priority
            )

        role = self.NEXUS_CATEGORIES.get(
            category, CosmicRole.ECHO
        )

        # STAP 5: Specialist voert uit
        result = self._assign(role, enriched, priority)

        # STAP 6: Weaver Synthese (skip voor CASUAL)
        if (
            category != "CASUAL"
            and result.status == "TASK_COMPLETED"
            and result.result
        ):
            synthesized = self._weaver_synthesize(
                str(result.result), task
            )
            if synthesized:
                result = TaskResult(
                    task=result.task,
                    assigned_to=(
                        f"{result.assigned_to}"
                        f" -> Weaver"
                    ),
                    status=result.status,
                    result=synthesized,
                    execution_time=(
                        result.execution_time
                    ),
                )

        return result

    def _deploy_swarm(self, task: str, priority: TaskPriority) -> TaskResult:
        """Deploy de Legion zwerm voor massa-verwerking."""
        governor = self.nodes[CosmicRole.GOVERNOR]
        legion = self.nodes[CosmicRole.LEGION]

        print(f"   [PROTOCOL 5] Activating {governor.name} in Dimension Omega-0...")
        print(f"   >>> {governor.name}: 'Releasing The Legion ({self.swarm.total_agents} agents)'")
        print(f"   >>> {self.swarm.summon_swarm(task[:50])}")

        governor.current_task = f"Coordinating: {task[:30]}..."
        legion.current_task = f"Executing: {task[:30]}..."
        self._task_counter += 1  # Fix 1.3: was missing

        # Try/finally voor swarm metrics (1.4)
        # Cap op 10 om onbegrensde groei te voorkomen
        self.swarm.active_tasks = min(
            10, self.swarm.active_tasks + 1
        )
        try:
            # Rol-specifieke brain executie (v6.0)
            ai_result, exec_time, brain_status = (
                self._execute_with_role(CosmicRole.LEGION, task)
            )

            if brain_status == "OK":
                status = "SWARM_EXECUTION_COMPLETE"
                self.swarm.completed_tasks += 1
                print(f"   >>> Swarm result ({exec_time:.1f}s): {str(ai_result)[:80]}...")
            elif brain_status == "FAIL":
                status = "SWARM_EXECUTION_FAILED"
                print(f"   >>> Swarm fout: {ai_result}")
            else:
                status = "SWARM_EXECUTION_STARTED"
        finally:
            self.swarm.active_tasks = max(
                0, self.swarm.active_tasks - 1
            )

        governor.current_task = None
        legion.current_task = None

        result = TaskResult(
            task=task,
            assigned_to=f"{governor.name} -> {legion.name}",
            status=status,
            result=ai_result or {
                "swarm_size": self.swarm.total_agents,
                "protocol": 5,
            },
            execution_time=exec_time,
        )

        self.task_history.append(result)
        self._status_counts[status] = (
            self._status_counts.get(status, 0) + 1
        )
        self._track_learning(task, str(ai_result or ""))
        self._mark_dirty()

        return result

    def _rag_enrich(self, task: str) -> str:
        """Verrijk taak met ChromaDB RAG context."""
        # Skip ChromaDB in test-modus (Rust FFI crasht
        # in subprocess met piped stdout op Windows)
        if os.environ.get("DANNY_TEST_MODE") == "1":
            return task

        # BlackBox: check for known failure patterns
        bb_warning = ""
        try:
            from danny_toolkit.brain.black_box import get_black_box
            bb = get_black_box()
            bb_warning = bb.retrieve_warnings(task)
        except Exception as e:
            logger.debug("BlackBox warning retrieval error: %s", e)

        try:
            from ingest import TheLibrarian
            lib = TheLibrarian()
            results = lib.query(task, n_results=5)
            docs = results.get("documents", [[]])[0]
            if docs:
                # TruthAnchor: verify relevance before injecting
                try:
                    from danny_toolkit.brain.truth_anchor import TruthAnchor
                    anchor = TruthAnchor()
                    grounded, _score = anchor.verify(task, docs[:3])
                    if not grounded:
                        # Phase 6: Feedback loop — record + research
                        self._trigger_learning_cycle(
                            task, str(docs[:3])[:500],
                            "TruthAnchor rejected: RAG context below relevance threshold",
                        )
                        docs = None  # Context too weak, skip RAG
                except Exception as e:
                    logger.debug("TruthAnchor verify error: %s", e)

            if docs:
                context = "\n---\n".join(docs)
                enriched = (
                    f"KENNISBANK CONTEXT:\n{context}\n\n"
                    f"VRAAG: {task}\n"
                    f"Beantwoord op basis van de context."
                )
                if bb_warning:
                    enriched = f"{bb_warning}\n\n{enriched}"
                return enriched
        except Exception as e:
            print(f"   [RAG] Fout: {e}")

        # Cortex Graph RAG — hybrid search (vector + graph expansion)
        try:
            from danny_toolkit.brain.cortex import TheCortex
            import asyncio as _aio
            cortex = TheCortex()
            graph_results = _aio.run(cortex.hybrid_search(task, top_k=3))
            if graph_results:
                graph_context = "\n\n".join(
                    r.get("content", "") for r in graph_results if r.get("content")
                )
                if graph_context:
                    task = f"{task}\n\nGRAAF CONTEXT:\n{graph_context}"
                    if bb_warning:
                        task = f"{bb_warning}\n\n{task}"
                    return task
        except Exception as e:
            logger.debug("Cortex hybrid search error: %s", e)

        # VoidWalker: last resort — autonomous research for unknown topics
        try:
            from danny_toolkit.brain.void_walker import VoidWalker
            import asyncio as _aio2
            walker = VoidWalker()
            knowledge = _aio2.run(walker.fill_knowledge_gap(task[:200]))
            if knowledge:
                task = f"{task}\n\nONDERZOEK CONTEXT:\n{knowledge[:1500]}"
        except Exception as e:
            logger.debug("VoidWalker fill_knowledge_gap error: %s", e)

        if bb_warning:
            task = f"{bb_warning}\n\n{task}"
        return task

    def _assign(self, role: CosmicRole, task: str, priority: TaskPriority) -> TaskResult:
        """Wijs een taak toe aan een specifieke agent."""
        agent = self.nodes[role]

        # Energy tracking (Federation v6.0)
        if agent.current_task is None and agent.energy < 100:
            agent.energy = min(100, agent.energy + 10)
        agent.energy = max(0, agent.energy - 5)

        print(f"   [ASSIGNED] {agent.name} ({role.name}) handling task")
        print(f"   >>> Capabilities: {', '.join(agent.capabilities[:3])}...")

        agent.current_task = task[:50]
        agent.tasks_completed += 1
        self._task_counter += 1

        # RAG context injectie voor ARCHIVIST
        enriched_task = task
        if role == CosmicRole.ARCHIVIST:
            print(f"   [RAG] ChromaDB query...")
            enriched_task = self._rag_enrich(task)

        # Rol-specifieke brain executie (Federation v6.0)
        ai_result, exec_time, brain_status = (
            self._execute_with_role(role, enriched_task)
        )

        if brain_status == "OK":
            status = "TASK_COMPLETED"
            print(f"   >>> {agent.name} result ({exec_time:.1f}s): {str(ai_result)[:80]}...")
        elif brain_status == "FAIL":
            status = "TASK_FAILED"
            print(f"   >>> {agent.name} fout: {ai_result}")
            # Phase 6: Feedback loop on failure
            self._trigger_learning_cycle(
                task, str(ai_result)[:500],
                f"TASK_FAILED by {agent.name} ({role.name})",
            )
        else:
            status = "TASK_QUEUED"

        agent.current_task = None

        result = TaskResult(
            task=task,
            assigned_to=agent.name,
            status=status,
            result=ai_result or {
                "agent": agent.name,
                "role": role.name,
                "tier": agent.tier.value,
            },
            execution_time=exec_time,
        )

        self.task_history.append(result)
        self._status_counts[status] = (
            self._status_counts.get(status, 0) + 1
        )
        self._track_learning(task, str(ai_result or ""))
        self._mark_dirty()

        return result

    def _track_learning(self, task: str, response: str):
        """Log interactie naar LearningSystem.

        Governor bewaakt de learning cycle met
        snapshot/rollback en rate limiting.
        """
        if not self.learning:
            return
        try:
            self.learning.log_chat(task, response, {
                "bron": "prometheus",
                "systeem": self.SYSTEM_NAME,
            })
            # Elke 5 taken: run learning cycle via Governor
            if self._task_counter % 5 == 0:
                self.governor.guard_learning_cycle(
                    self.learning.improvement
                )
        except Exception as e:
            print(f"  [LEARNING] Waarschuwing: {e}")

    # --- STAP 4: FEDERATIE STATUS & MANAGEMENT ---

    def get_status(self) -> Dict:
        """Haal de volledige federatie status op."""
        return {
            "system": self.SYSTEM_NAME,
            "version": self.VERSION,
            "is_online": self.is_online,
            "total_nodes": len(self.nodes),
            "nodes": {role.name: node.to_dict() for role, node in self.nodes.items()},
            "swarm": self.swarm.to_dict(),
            "tasks_in_history": len(self.task_history)
        }

    def get_node(self, role: CosmicRole) -> Optional[AgentNode]:
        """Haal een specifieke node op."""
        return self.nodes.get(role)

    def get_nodes_by_tier(self, tier: NodeTier) -> List[AgentNode]:
        """Haal alle nodes van een specifieke tier op."""
        return [node for node in self.nodes.values() if node.tier == tier]

    def display_status(self):
        """Toon visuele status van de federatie."""
        print(f"\n{'='*60}")
        print(f"  PROMETHEUS FEDERATION STATUS")
        print(f"  System: {self.SYSTEM_NAME} v{self.VERSION}")
        print(f"{'='*60}")

        # Verbindingen
        brain_status = self.brain.ai_provider.upper() if self.brain and self.brain.ai_provider else "OFFLINE"
        learning_status = "ACTIEF" if self.learning else "NIET BESCHIKBAAR"
        print(f"\n  [VERBINDINGEN]")
        print(f"  {'-'*40}")
        print(f"  CentralBrain:   {brain_status}")
        print(f"  LearningSystem: {learning_status}")

        # Per tier
        for tier in NodeTier:
            nodes = self.get_nodes_by_tier(tier)
            if nodes:
                print(f"\n  [{tier.value}] - {len(nodes)} nodes")
                print(f"  {'-'*40}")
                for node in nodes:
                    status_icon = "[X]" if node.status == "ACTIVE" else "[O]" if node.status == "ORACLE_AVATAR" else "[ ]"
                    print(f"  {status_icon} {node.name:<15} | Tasks: {node.tasks_completed}")

        # Task stats (O(1) via _status_counts)
        completed = self._status_counts.get("TASK_COMPLETED", 0)
        queued = self._status_counts.get("TASK_QUEUED", 0)
        failed = self._status_counts.get("TASK_FAILED", 0)
        print(f"\n  [TASK HISTORY]")
        print(f"  {'-'*40}")
        print(f"  Voltooid: {completed}")
        print(f"  Wachtend: {queued}")
        print(f"  Mislukt:  {failed}")
        print(f"  Totaal:   {self._task_counter}")

        # Swarm stats
        print(f"\n  [OMEGA SWARM]")
        print(f"  {'-'*40}")
        print(f"  Status:    {self.swarm.status}")
        print(f"  Capacity:  {self.swarm.capacity}")
        print(f"  Governor:  {self.swarm.governor}")
        print(f"  Miners:    {self.swarm.miners}")
        print(f"  Testers:   {self.swarm.testers}")
        print(f"  Indexers:  {self.swarm.indexers}")
        print(f"  TOTAL:     {self.swarm.total_agents}"
              f" Micro-Agents")
        print(f"  Swarm Ops: {self.swarm.completed_tasks}")

        # Governor health
        health = self.governor.get_health_report()
        cb = health["circuit_breaker"]
        lr = health["learning"]
        if cb["status"] == "CLOSED":
            cb_icon = "[OK]"
        elif cb["status"] == "HALF_OPEN":
            cb_icon = "[??]"
        else:
            cb_icon = "[!!]"
        lr_icon = (
            "[OK]" if lr["cycles_this_hour"]
            < lr["max_per_hour"] else "[!!]"
        )
        print(f"\n  [GOVERNOR HEALTH]")
        print(f"  {'-'*40}")
        cd = cb.get("countdown", 0)
        if cd > 0:
            m = cd // 60
            s = cd % 60
            timer = f"{m}m{s:02d}s" if m > 0 else f"{s}s"
            cb_timer = f" - reset over {timer}"
        else:
            cb_timer = ""
        print(f"  {cb_icon} Circuit Breaker: {cb['status']} "
              f"({cb['failures']}/{cb['max']}){cb_timer}")
        print(f"  {lr_icon} Learning Guard: "
              f"{lr['cycles_this_hour']}/{lr['max_per_hour']}")
        state_ok = sum(
            1 for v in health["state_files"].values() if v
        )
        state_total = len(health["state_files"])
        print(f"  [OK] State Files: "
              f"{state_ok}/{state_total} geldig")

        print(f"\n{'='*60}\n")

    # --- B-95 EFFICIENCY REFLECTION ---

    def efficiency_reflection(self, window: int = 100) -> dict:
        """B-95 Efficiency Reflection: Analyseer recente response kwaliteit.

        Queries CorticalStack for the last `window` response_outcome events
        logged by SwarmEngine and computes a quality score.

        Returns:
            dict met b95_score (0-100), total, successes, failures,
            avg_latency_ms, top_failure_agents, en recommendation.
        """
        try:
            from danny_toolkit.brain.cortical_stack import get_cortical_stack
            stack = get_cortical_stack()
        except Exception:
            return {"b95_score": -1, "error": "CorticalStack niet beschikbaar"}

        events = stack.search_events("response_outcome", limit=window)
        if not events:
            return {
                "b95_score": -1,
                "total": 0,
                "note": "Geen response_outcome events gevonden. "
                        "SwarmEngine moet eerst queries verwerken.",
            }

        total = len(events)
        successes = 0
        failures = 0
        latencies = []
        failure_agents = {}

        for evt in events:
            details = evt.get("details", {})
            if isinstance(details, str):
                import json
                try:
                    details = json.loads(details)
                except (json.JSONDecodeError, TypeError):
                    continue

            if details.get("success"):
                successes += 1
            else:
                failures += 1
                for agent in details.get("agents", []):
                    failure_agents[agent] = failure_agents.get(agent, 0) + 1

            lat = details.get("latency_ms", 0)
            if lat > 0:
                latencies.append(lat)

        b95_score = round((successes / total) * 100, 1) if total > 0 else 0
        avg_latency = round(sum(latencies) / len(latencies), 1) if latencies else 0

        # Top 3 failure agents
        top_failures = sorted(
            failure_agents.items(), key=lambda x: x[1], reverse=True
        )[:3]

        # Recommendation
        if b95_score >= 95:
            recommendation = "EXCELLENT: B-95 standaard gehaald."
        elif b95_score >= 85:
            recommendation = "GOED: Dicht bij B-95. Focus op top failure agents."
        elif b95_score >= 70:
            recommendation = "AANDACHT: Onder B-95. Controleer fallback chain en circuit breakers."
        else:
            recommendation = "KRITIEK: Ver onder B-95. Systeem-brede diagnose nodig."

        return {
            "b95_score": b95_score,
            "total": total,
            "successes": successes,
            "failures": failures,
            "avg_latency_ms": avg_latency,
            "top_failure_agents": top_failures,
            "recommendation": recommendation,
        }

    # --- TRI-FORCE PROTOCOL, SINGULARITY NEXUS, GOD MODE,
    # --- CHAIN OF COMMAND: zie prometheus_protocols.py (Mixin)

    # --- PERSISTENCE ---

    def _save_state(self):
        """Sla de huidige staat op.

        Governor maakt backup VOORDAT er geschreven wordt.
        """
        try:
            self._data_dir.mkdir(parents=True, exist_ok=True)
            # Governor: backup voor schrijven
            self.governor.backup_state(self._state_file)
            state = {
                "system": self.SYSTEM_NAME,
                "version": self.VERSION,
                "last_update": datetime.now().isoformat(),
                "nodes": {role.name: node.to_dict() for role, node in self.nodes.items()},
                "swarm": self.swarm.to_dict(),
                "task_count": self._task_counter,
                "status_counts": dict(self._status_counts),
                "governor": self.governor.to_dict(),
            }
            with open(self._state_file, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"  [WARNING] Could not save state: {e}")

    def _load_state(self):
        """Laad de vorige staat.

        Bij falen probeert Governor te herstellen van backup.
        """
        try:
            if self._state_file.exists():
                with open(self._state_file, "r", encoding="utf-8") as f:
                    state = json.load(f)
                    # Restore task counts
                    for role_name, node_data in state.get("nodes", {}).items():
                        try:
                            role = CosmicRole[role_name]
                            if role in self.nodes:
                                self.nodes[role].tasks_completed = node_data.get("tasks_completed", 0)
                        except KeyError:
                            pass
                    # Restore swarm metrics
                    swarm = state.get("swarm", {})
                    self.swarm.completed_tasks = swarm.get(
                        "completed_tasks", 0
                    )
                    # Restore task counter + status counts
                    self._task_counter = state.get(
                        "task_count", 0
                    )
                    saved_counts = state.get(
                        "status_counts", {}
                    )
                    for key, val in saved_counts.items():
                        self._status_counts[key] = val
                    # Restore Governor state
                    governor_data = state.get("governor", {})
                    if governor_data:
                        self.governor.from_dict(governor_data)
                    print(
                        f"  [RESTORED] Previous state loaded"
                        f" ({self._task_counter}"
                        f" historical tasks)"
                    )
        except Exception as e:
            # Governor: probeer herstel van backup
            if self._state_file.exists():
                print(
                    f"  [WARNING] State load fout: {e}"
                )
                print(
                    "  [WARNING] State corrupt, "
                    "Governor probeert herstel..."
                )
                self.governor.restore_state(
                    self._state_file
                )
            else:
                print(
                    "  [INFO] Starting fresh "
                    "(no previous state)"
                )


# --- SINGLETON ACCESS ---

_prometheus_instance: Optional[PrometheusBrain] = None


def get_prometheus() -> PrometheusBrain:
    """Haal de Prometheus Brain singleton op."""
    global _prometheus_instance
    if _prometheus_instance is None:
        _prometheus_instance = PrometheusBrain()
    return _prometheus_instance


def route(task: str, priority: str = "MEDIUM") -> TaskResult:
    """Shortcut om een taak te routen."""
    brain = get_prometheus()
    prio = TaskPriority[priority.upper()] if isinstance(priority, str) else priority
    return brain.route_task(task, prio)


# --- MAIN: SIMULATIE ---

def main():
    """Test de Prometheus Brain."""
    brain = PrometheusBrain()

    print("\n" + "="*60)
    print("  PROMETHEUS PROTOCOL - SIMULATION")
    print("="*60)

    # Test 1: Cipher (Crypto/Blockchain)
    print("\n[TEST 1] Crypto Pattern Task -> Cipher")
    brain.route_task("Zoek patronen in deze blockchain transacties")

    # Test 2: Legion (Massa Verwerking)
    print("\n[TEST 2] Mass Processing -> Legion Swarm")
    brain.route_task("Indexeer alles in het archief en verwerk data van 10000 bestanden")

    # Test 3: Spark (Creatief)
    print("\n[TEST 3] Creative Task -> Spark")
    brain.route_task("Brainstorm creatief een nieuw idee voor de UI")

    # Test 4: Echo (Historisch)
    print("\n[TEST 4] Historical Context -> Echo")
    brain.route_task("Wat gebeurde er vorige week met het project?")

    # Test 5: Vita (Bio/Health)
    print("\n[TEST 5] Bio Health Task -> Vita")
    brain.route_task("Analyseer de HRV health data van vandaag")

    # Test 6: Weaver (Default Code)
    print("\n[TEST 6] Code Task -> Weaver (default)")
    brain.route_task("Schrijf een functie die getallen sorteert")

    # Test 7: Chain of Command - Multi-Domain Query
    print("\n[TEST 7] Chain of Command - Multi-Domain Query")
    coc_result = brain.chain_of_command(
        "Wat is de huidige Bitcoin prijs en wat betekent "
        "dat voor mijn stress-niveau?"
    )
    print(f"  Nodes betrokken: {coc_result['nodes_betrokken']}")
    print(f"  Sub-taken: {len(coc_result['sub_taken'])}")

    # Toon status
    brain.display_status()

    print("\n[SIMULATION COMPLETE]")
    print("The Federation is ready for production.")


if __name__ == "__main__":
    main()

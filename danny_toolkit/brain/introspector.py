"""
SystemIntrospector — Zelfbewustzijn & Introspectie (Phase 42 Invention).

Het systeem kent zichzelf: welke modules actief zijn, hoe ze bedraad zijn,
wat hun gezondheid is, en wat hun prestaties zijn. Gebruikt VectorStore
om een semantisch zelfbeeld op te bouwen en CorticalStack voor historisch
bewustzijn.

Singleton: ``get_introspector()``.
"""

from __future__ import annotations

import importlib
import inspect
import json
import logging
import os
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

from danny_toolkit.core.config import Config
from danny_toolkit.core.utils import Kleur

try:
    from danny_toolkit.brain.cortical_stack import get_cortical_stack
    HAS_STACK = True
except ImportError:
    HAS_STACK = False

try:
    from danny_toolkit.core.neural_bus import get_bus, EventTypes
    HAS_BUS = True
except ImportError:
    HAS_BUS = False

try:
    from danny_toolkit.core.vector_store import VectorStore
    from danny_toolkit.core.embeddings import get_torch_embedder
    HAS_VECTOR = True
except ImportError:
    HAS_VECTOR = False


# ── Data Models ──

@dataclass
class ModuleHealth:
    """Gezondheid van een brain module."""
    naam: str
    geladen: bool = False
    singleton_actief: bool = False
    fout: str = ""
    versie: str = ""
    has_docstring: bool = False
    method_count: int = 0
    wiring: List[str] = field(default_factory=list)


@dataclass
class WiringConnection:
    """Een bedrading tussen twee modules."""
    bron: str
    doel: str
    type: str       # "import", "singleton", "method_call"
    actief: bool = True
    beschrijving: str = ""


@dataclass
class SystemSnapshot:
    """Compleet zelfportret van het systeem."""
    timestamp: str
    versie: str
    modules: List[ModuleHealth]
    wirings: List[WiringConnection]
    security_status: Dict
    performance: Dict
    totaal_modules: int = 0
    actieve_modules: int = 0
    gezondheid_score: float = 0.0


class SystemIntrospector:
    """
    INVENTION #20: THE INTROSPECTOR — Zelfbewustzijn
    ================================================
    Het systeem dat zichzelf kent.

    Features:
    - Module discovery: scan alle brain modules, check geladen status
    - Wiring map: detecteer cross-module verbindingen
    - Health diagnostics: per-module gezondheid + systeem-score
    - Semantisch geheugen: sla zelfkennis op in VectorStore
    - Historisch bewustzijn: vergelijk huidige staat met eerdere snapshots
    - Security audit: check of alle beveiligingslagen actief zijn
    """

    # Bekende modules en hun singleton factories
    _KNOWN_MODULES = {
        "central_brain": {"class": "CentralBrain"},
        "governor": {"class": "OmegaGovernor"},
        "cortical_stack": {"class": "CorticalStack", "singleton": "get_cortical_stack"},
        "strategist": {"class": "Strategist"},
        "tribunal": {"class": "Tribunal"},
        "adversarial_tribunal": {
            "class": "AdversarialTribunal",
            "singleton": "get_adversarial_tribunal",
        },
        "void_walker": {"class": "VoidWalker"},
        "artificer": {"class": "Artificer"},
        "black_box": {"class": "BlackBox", "singleton": "get_black_box"},
        "the_mirror": {"class": "TheMirror"},
        "ghost_writer": {"class": "GhostWriter"},
        "dreamer": {"class": "Dreamer"},
        "devops_daemon": {"class": "DevOpsDaemon"},
        "cortex": {"class": "TheCortex"},
        "oracle_eye": {"class": "TheOracleEye"},
        "synapse": {"class": "TheSynapse"},
        "phantom": {"class": "ThePhantom"},
        "virtual_twin": {"class": "VirtualTwin"},
        "shadow_governance": {"class": "ShadowGovernance"},
        "hallucination_shield": {
            "class": "HallucinatieSchild",
            "singleton": "get_hallucination_shield",
        },
        "waakhuis": {"class": "WaakhuisMonitor", "singleton": "get_waakhuis"},
        "truth_anchor": {"class": "TruthAnchor"},
        "arbitrator": {
            "class": "TaskArbitrator",
            "singleton": "get_arbitrator",
        },
        "model_sync": {"class": "ModelRegistry", "singleton": "get_model_registry"},
        "config_auditor": {
            "class": "ConfigAuditor",
            "singleton": "get_config_auditor",
        },
    }

    # Bekende cross-module wirings
    _KNOWN_WIRINGS = [
        WiringConnection("artificer", "black_box", "method_call",
                         beschrijving="record_crash() bij forge-fouten"),
        WiringConnection("strategist", "oracle_eye", "method_call",
                         beschrijving="pre_warm_check() vóór plan-fase"),
        WiringConnection("tribunal", "truth_anchor", "method_call",
                         beschrijving="verify() in consensus-loop"),
        WiringConnection("cortex", "the_mirror", "method_call",
                         beschrijving="get_context_injection() bij RAG-hits"),
        WiringConnection("artificer", "neural_bus", "singleton",
                         beschrijving="FORGE_SUCCESS events"),
        WiringConnection("strategist", "neural_bus", "singleton",
                         beschrijving="MISSION_STARTED + STEP_COMPLETED"),
        WiringConnection("cortex", "neural_bus", "singleton",
                         beschrijving="KNOWLEDGE_GRAPH_UPDATE events"),
        WiringConnection("hallucination_shield", "truth_anchor", "method_call",
                         beschrijving="Cross-encoder scoring"),
        WiringConnection("hallucination_shield", "adversarial_tribunal", "method_call",
                         beschrijving="Multi-model verificatie"),
        WiringConnection("arbitrator", "hallucination_shield", "method_call",
                         beschrijving="95% Barrière enforcement"),
        WiringConnection("dreamer", "ghost_writer", "method_call",
                         beschrijving="Auto-docstring in REM cycle"),
        WiringConnection("dreamer", "void_walker", "method_call",
                         beschrijving="Research failures in REM"),
        WiringConnection("virtual_twin", "shadow_governance", "method_call",
                         beschrijving="3-zone kloon-restricties"),
        WiringConnection("swarm_engine", "hallucination_shield", "singleton",
                         beschrijving="Output gate op alle payloads"),
        WiringConnection("swarm_engine", "arbitrator", "singleton",
                         beschrijving="Goal decomposition + execution"),
    ]

    def __init__(self):
        """Initializes the object, setting up its internal state.

 Configures the cortical stack, bus, and vector store for semantic self-memory.
 
 Attributes:
   _stack: The cortical stack, if available.
   _bus: The bus, if available.
   _store: The vector store for semantic self-memory, if vector support is enabled.
   _self_knowledge_path: The file path to self-knowledge data.

 Raises:
   Exception: If an error occurs during VectorStore initialization, it is logged and the process continues."""
        self._stack = get_cortical_stack() if HAS_STACK else None
        self._bus = get_bus() if HAS_BUS else None
        self._store = None
        self._self_knowledge_path = Config.DATA_DIR / "memory" / "self_knowledge.json"

        # VectorStore voor semantisch zelfgeheugen
        if HAS_VECTOR:
            try:
                embedder = get_torch_embedder()
                self._store = VectorStore(
                    embedding_provider=embedder,
                    db_file=Config.DATA_DIR / "memory" / "introspector.json",
                )
            except Exception as e:
                logger.debug("Introspector VectorStore init error: %s", e)

    # ── Module Discovery ──

    def discover_modules(self) -> List[ModuleHealth]:
        """Scan alle bekende brain modules en check hun status."""
        results = []
        for mod_name, meta in self._KNOWN_MODULES.items():
            health = ModuleHealth(naam=mod_name)
            full_path = f"danny_toolkit.brain.{mod_name}"
            try:
                mod = importlib.import_module(full_path)
                health.geladen = True

                # Check class exists
                cls = getattr(mod, meta["class"], None)
                if cls:
                    health.has_docstring = bool(inspect.getdoc(cls))
                    health.method_count = len([
                        m for m in dir(cls)
                        if not m.startswith("_") and callable(getattr(cls, m, None))
                    ])

                # Check singleton factory
                if "singleton" in meta:
                    factory = getattr(mod, meta["singleton"], None)
                    health.singleton_actief = factory is not None and callable(factory)

                # Module version
                health.versie = getattr(mod, "__version__", "")

            except Exception as e:
                health.fout = str(e)[:200]
                logger.debug("Module %s load error: %s", mod_name, e)

            results.append(health)

        return results

    # ── Wiring Verification ──

    def verify_wirings(self) -> List[WiringConnection]:
        """Verifieer of alle bekende cross-module wirings actief zijn."""
        verified = []
        for wiring in self._KNOWN_WIRINGS:
            w = WiringConnection(
                bron=wiring.bron,
                doel=wiring.doel,
                type=wiring.type,
                beschrijving=wiring.beschrijving,
            )
            # Check of bron-module een referentie heeft naar doel
            try:
                bron_path = f"danny_toolkit.brain.{wiring.bron}"
                if wiring.bron == "swarm_engine":
                    bron_path = "swarm_engine"
                mod = importlib.import_module(bron_path)
                src = inspect.getsource(mod)

                # Zoek of het doel geïmporteerd wordt
                doel_indicators = [
                    wiring.doel,
                    wiring.doel.replace("_", ""),
                ]
                w.actief = any(ind in src.lower() for ind in doel_indicators)

            except Exception as e:
                w.actief = False
                logger.debug("Wiring verify %s→%s error: %s",
                             wiring.bron, wiring.doel, e)

            verified.append(w)

        return verified

    # ── Security Status ──

    def check_security(self) -> Dict:
        """Check of alle beveiligingslagen actief zijn."""
        status = {
            "governor_actief": False,
            "hallucination_shield_actief": False,
            "shadow_governance_actief": False,
            "black_box_immuniteit": False,
            "truth_anchor_actief": False,
            "prompt_injection_detectie": False,
            "rate_limiting_actief": False,
            "circuit_breakers_actief": False,
            "security_score": 0.0,
        }

        # Governor check
        try:
            from danny_toolkit.brain.governor import OmegaGovernor
            gov = OmegaGovernor.__new__(OmegaGovernor)
            status["governor_actief"] = True
            status["prompt_injection_detectie"] = hasattr(gov, "valideer_input")
            status["rate_limiting_actief"] = hasattr(OmegaGovernor, "MAX_LEARNING_CYCLES_PER_HOUR")
        except Exception as e:
            logger.debug("Governor security check: %s", e)

        # HallucinatieSchild
        try:
            from danny_toolkit.brain.hallucination_shield import HallucinatieSchild
            status["hallucination_shield_actief"] = True
        except Exception as e:
            logger.debug("Introspector probe HallucinatieSchild: %s", e)

        # ShadowGovernance
        try:
            from danny_toolkit.brain.shadow_governance import ShadowGovernance
            status["shadow_governance_actief"] = True
        except Exception as e:
            logger.debug("Introspector probe ShadowGovernance: %s", e)

        # BlackBox
        try:
            from danny_toolkit.brain.black_box import BlackBox
            status["black_box_immuniteit"] = True
        except Exception as e:
            logger.debug("Introspector probe BlackBox: %s", e)

        # TruthAnchor
        try:
            from danny_toolkit.brain.truth_anchor import TruthAnchor
            status["truth_anchor_actief"] = True
        except Exception as e:
            logger.debug("Introspector probe TruthAnchor: %s", e)

        # Circuit breakers
        try:
            from danny_toolkit.brain.central_brain import CentralBrain
            src = inspect.getsource(CentralBrain)
            status["circuit_breakers_actief"] = "_provider_breakers" in src
        except Exception as e:
            logger.debug("Introspector probe circuit breakers: %s", e)

        # Calculate security score
        checks = [
            status["governor_actief"],
            status["hallucination_shield_actief"],
            status["shadow_governance_actief"],
            status["black_box_immuniteit"],
            status["truth_anchor_actief"],
            status["prompt_injection_detectie"],
            status["rate_limiting_actief"],
            status["circuit_breakers_actief"],
        ]
        status["security_score"] = sum(checks) / max(len(checks), 1)

        return status

    # ── Performance Aggregation ──

    def collect_performance(self) -> Dict:
        """Verzamel prestatie-data uit alle subsystemen."""
        perf = {
            "cortical_stack": {},
            "black_box": {},
            "waakhuis": {},
            "cortex": {},
            "model_registry": {},
        }

        # CorticalStack stats
        if self._stack:
            try:
                perf["cortical_stack"] = self._stack.get_db_metrics()
            except Exception as e:
                logger.debug("CorticalStack metrics error: %s", e)

        # BlackBox immune stats
        try:
            from danny_toolkit.brain.black_box import get_black_box
            perf["black_box"] = get_black_box().get_stats()
        except Exception as e:
            logger.debug("BlackBox stats error: %s", e)

        # Waakhuis health
        try:
            from danny_toolkit.brain.waakhuis import get_waakhuis
            perf["waakhuis"] = get_waakhuis().get_stats()
        except Exception as e:
            logger.debug("Waakhuis stats error: %s", e)

        # Cortex graph stats
        try:
            from danny_toolkit.brain.cortex import TheCortex
            c = TheCortex()
            perf["cortex"] = c.get_stats()
        except Exception as e:
            logger.debug("Cortex stats error: %s", e)

        # Model Registry stats
        try:
            from danny_toolkit.brain.model_sync import get_model_registry
            perf["model_registry"] = get_model_registry().get_stats()
        except Exception as e:
            logger.debug("ModelRegistry stats error: %s", e)

        return perf

    # ── Full Snapshot ──

    # Snapshot cache: voorkomt herhaalde volledige scans binnen SNAPSHOT_TTL_S
    _SNAPSHOT_TTL_S = 30  # Seconds
    _cached_snapshot: "Optional[SystemSnapshot]" = None
    _cached_snapshot_at: float = 0.0

    def take_snapshot(self, force: bool = False) -> SystemSnapshot:
        """Maak een compleet zelfportret van het systeem.

        Args:
            force: Negeer cache en forceer nieuwe scan.

        Returns:
            SystemSnapshot met alle systeemmetrics.
        """
        # ── Cache guard: hergebruik recente snapshot ──
        now = time.time()
        if (
            not force
            and self._cached_snapshot is not None
            and (now - self._cached_snapshot_at) < self._SNAPSHOT_TTL_S
        ):
            logger.debug(
                "Introspector: cached snapshot hergebruikt (%.1fs oud)",
                now - self._cached_snapshot_at,
            )
            return self._cached_snapshot

        print(f"{Kleur.CYAAN}🧠 Introspector: Zelfdiagnose...{Kleur.RESET}")

        modules = self.discover_modules()
        wirings = self.verify_wirings()
        security = self.check_security()
        performance = self.collect_performance()

        actief = sum(1 for m in modules if m.geladen)
        totaal = len(modules)

        # Gezondheid = gewogen score van modules + security + wirings
        module_score = actief / max(totaal, 1)
        wiring_score = sum(1 for w in wirings if w.actief) / max(len(wirings), 1)
        security_score = security.get("security_score", 0.0)

        gezondheid = (module_score * 0.4 + wiring_score * 0.3 + security_score * 0.3)

        snapshot = SystemSnapshot(
            timestamp=datetime.now().isoformat(),
            versie=self._get_version(),
            modules=modules,
            wirings=wirings,
            security_status=security,
            performance=performance,
            totaal_modules=totaal,
            actieve_modules=actief,
            gezondheid_score=round(gezondheid, 4),
        )

        # Rapporteer
        print(f"{Kleur.GROEN}🧠 Systeem: {actief}/{totaal} modules actief, "
              f"gezondheid: {gezondheid:.1%}{Kleur.RESET}")
        print(f"   Wirings: {sum(1 for w in wirings if w.actief)}/{len(wirings)} actief")
        print(f"   Security: {security_score:.0%}")

        # ── Cache opslaan ──
        self._cached_snapshot = snapshot
        self._cached_snapshot_at = now

        # Sla op in VectorStore
        self._store_self_knowledge(snapshot)

        # Log naar CorticalStack
        self._log_snapshot(snapshot)

        return snapshot

    def _get_version(self) -> str:
        """Haal de huidige brain versie op."""
        try:
            import danny_toolkit.brain as brain
            return getattr(brain, "__version__", "unknown")
        except Exception as e:
            logger.debug("Introspector version check: %s", e)
            return "unknown"

    def _store_self_knowledge(self, snapshot: SystemSnapshot):
        """Sla zelfkennis op in VectorStore voor semantisch ophalen."""
        if not self._store:
            return

        try:
            # Sla snapshot samen als leesbare tekst voor vector search
            tekst = self._snapshot_to_text(snapshot)
            entry_id = f"introspection_{int(time.time())}"
            self._store.voeg_toe([{
                "id": entry_id,
                "tekst": tekst,
                "metadata": {
                    "type": "system_introspection",
                    "timestamp": time.time(),
                    "versie": snapshot.versie,
                    "gezondheid": snapshot.gezondheid_score,
                    "actieve_modules": snapshot.actieve_modules,
                },
            }])
            logger.debug("Introspector: zelfkennis opgeslagen in VectorStore")
        except Exception as e:
            logger.debug("VectorStore store error: %s", e)

        # Ook als JSON op schijf
        try:
            Config.ensure_dirs()
            (Config.DATA_DIR / "memory").mkdir(parents=True, exist_ok=True)
            data = {
                "timestamp": snapshot.timestamp,
                "versie": snapshot.versie,
                "gezondheid_score": snapshot.gezondheid_score,
                "totaal_modules": snapshot.totaal_modules,
                "actieve_modules": snapshot.actieve_modules,
                "security_score": snapshot.security_status.get("security_score", 0),
                "wiring_actief": sum(1 for w in snapshot.wirings if w.actief),
                "wiring_totaal": len(snapshot.wirings),
            }
            with open(self._self_knowledge_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.debug("Self-knowledge save error: %s", e)

    def _log_snapshot(self, snapshot: SystemSnapshot):
        """Log introspectie naar CorticalStack."""
        if not self._stack:
            return
        try:
            self._stack.log_event(
                actor="introspector",
                action="system_snapshot",
                details={
                    "gezondheid": snapshot.gezondheid_score,
                    "actief": snapshot.actieve_modules,
                    "totaal": snapshot.totaal_modules,
                    "security": snapshot.security_status.get("security_score", 0),
                },
                source="introspector",
            )
        except Exception as e:
            logger.debug("CorticalStack log error: %s", e)

    @staticmethod
    def _snapshot_to_text(snapshot: SystemSnapshot) -> str:
        """Converteer snapshot naar leesbare tekst voor VectorStore."""
        lines = [
            f"[SYSTEEM INTROSPECTIE — {snapshot.timestamp}]",
            f"Versie: {snapshot.versie}",
            f"Gezondheid: {snapshot.gezondheid_score:.1%}",
            f"Modules: {snapshot.actieve_modules}/{snapshot.totaal_modules} actief",
            "",
            "ACTIEVE MODULES:",
        ]
        for m in snapshot.modules:
            status = "✓" if m.geladen else "✗"
            lines.append(f"  {status} {m.naam} ({m.method_count} methods)")
            if m.wiring:
                for w in m.wiring:
                    lines.append(f"    → {w}")

        lines.append("")
        lines.append("WIRINGS:")
        for w in snapshot.wirings:
            status = "✓" if w.actief else "✗"
            lines.append(f"  {status} {w.bron} → {w.doel}: {w.beschrijving}")

        lines.append("")
        lines.append("BEVEILIGING:")
        for key, val in snapshot.security_status.items():
            if key != "security_score":
                status = "✓" if val else "✗"
                lines.append(f"  {status} {key}")

        return "\n".join(lines)

    # ── Query Zelfkennis ──

    def query_self(self, vraag: str) -> str:
        """Zoek in het semantisch zelfgeheugen.

        Voorbeeld: "welke modules zijn actief?"
        "hoe gezond is de beveiliging?"
        "wat is de status van de BlackBox?"
        """
        if not self._store or not self._store.documenten:
            # Neem eerst een snapshot als er nog geen kennis is
            self.take_snapshot()

        if not self._store:
            return "Geen VectorStore beschikbaar voor zelfkennis."

        results = self._store.zoek(query=vraag, top_k=3, min_score=0.3)
        if not results:
            return "Geen relevante zelfkennis gevonden."

        return "\n\n".join(
            r.get("tekst", r.get("content", ""))[:2000]
            for r in results
        )

    def get_wiring_map(self) -> str:
        """Return een leesbare wiring map van alle verbindingen."""
        wirings = self.verify_wirings()
        lines = ["[CROSS-MODULE WIRING MAP]", ""]
        for w in wirings:
            status = "✓ ACTIEF" if w.actief else "✗ VERBROKEN"
            lines.append(f"  {w.bron} → {w.doel}")
            lines.append(f"    Status: {status}")
            lines.append(f"    Type: {w.type}")
            lines.append(f"    {w.beschrijving}")
            lines.append("")
        return "\n".join(lines)

    def get_health_report(self) -> Dict:
        """Compact gezondheidsrapport voor API/FastAPI."""
        snapshot = self.take_snapshot()
        return {
            "versie": snapshot.versie,
            "gezondheid_score": snapshot.gezondheid_score,
            "modules_actief": snapshot.actieve_modules,
            "modules_totaal": snapshot.totaal_modules,
            "wirings_actief": sum(1 for w in snapshot.wirings if w.actief),
            "wirings_totaal": len(snapshot.wirings),
            "security_score": snapshot.security_status.get("security_score", 0),
            "security_details": snapshot.security_status,
            "timestamp": snapshot.timestamp,
        }


# ── Singleton Factory ──

_introspector_instance: Optional["SystemIntrospector"] = None
_introspector_lock = threading.Lock()


def get_introspector() -> "SystemIntrospector":
    """Return the process-wide SystemIntrospector singleton."""
    global _introspector_instance
    if _introspector_instance is None:
        with _introspector_lock:
            if _introspector_instance is None:
                _introspector_instance = SystemIntrospector()
    return _introspector_instance

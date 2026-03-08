"""
Dynamic Agent Factory — Lazy Loading via importlib.

Thread-safe class loading + agent instantiatie voor het hele ecosysteem.
God Mode Error Handling — fouten worden gelogd, nooit bare except:pass.

Features:
    - importlib-based safe imports (geen harde dependencies)
    - Dict cache (geen lru_cache op instance methods — voorkomt memory leaks)
    - Thread-safe met double-checked locking (project conventie)
    - DRY loops voor agent registratie vanuit blueprints
    - Graceful degradation — ontbrekende modules worden overgeslagen

Lagen:
    1. Swarm Agents  → build_swarm_agents() / get_swarm_agent()
    2. Brain Modules  → load_brain_class()
    3. Daemon Modules → load_daemon_class()
    4-5: Info-only (Prometheus roles + Support systems via brain_cli.py)

Gebruik:
    factory = get_agent_factory()
    agent = factory.get_swarm_agent("IOLAAX")
    alle = factory.build_swarm_agents()
    StrategistCls = factory.load_brain_class("Strategist")
"""

from __future__ import annotations

import importlib
import logging
import threading
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
#  SWARM AGENT BLUEPRINTS — Laag 1 (swarm_engine.py)
#  Exact match met SwarmEngine._build_agents() constructors
# ═══════════════════════════════════════════════════════════════

_SWARM_MODULE = "swarm_engine"

SWARM_BLUEPRINTS: Dict[str, Dict[str, str]] = {
    # --- BrainAgent subclasses (name, role, cosmic_role) ---
    "IOLAAX":        {"class": "IolaaxAgent",    "name": "Iolaax",         "role": "Engineer",   "cosmic": "IOLAAX"},
    "CIPHER":        {"class": "CipherAgent",    "name": "Cipher",         "role": "Finance",    "cosmic": "CIPHER"},
    "VITA":          {"class": "VitaAgent",       "name": "Vita",           "role": "Health",     "cosmic": "VITA"},
    "MEMEX":         {"class": "MemexAgent",      "name": "Memex",          "role": "Memory",     "cosmic": "ARCHIVIST"},
    "ALCHEMIST":     {"class": "AlchemistAgent",  "name": "Alchemist",      "role": "Data",       "cosmic": "ALCHEMIST"},
    "NAVIGATOR":     {"class": "BrainAgent",      "name": "Navigator",      "role": "Search",     "cosmic": "NAVIGATOR"},
    "ORACLE":        {"class": "BrainAgent",      "name": "Oracle",         "role": "Reasoning",  "cosmic": "ORACLE"},
    "SPARK":         {"class": "BrainAgent",      "name": "Spark",          "role": "Creative",   "cosmic": "SPARK"},
    "SENTINEL":      {"class": "BrainAgent",      "name": "Sentinel",       "role": "Security",   "cosmic": "SENTINEL"},
    "CHRONOS_AGENT": {"class": "BrainAgent",      "name": "Chronos",        "role": "Schedule",   "cosmic": "CHRONOS"},
    "WEAVER":        {"class": "BrainAgent",      "name": "Weaver",         "role": "Synthesis",  "cosmic": "WEAVER"},
    "VOID":          {"class": "BrainAgent",      "name": "Void",           "role": "Cleanup",    "cosmic": "VOID"},
    # --- Agent subclasses (name, role) — geen cosmic_role ---
    "ECHO":          {"class": "EchoAgent",       "name": "Echo",           "role": "Interface"},
    "PIXEL":         {"class": "PixelAgent",      "name": "Pixel",          "role": "Vision"},
    "COHERENTIE":    {"class": "CoherentieAgent",  "name": "Coherentie",    "role": "Hardware"},
    "STRATEGIST":    {"class": "StrategistAgent",  "name": "Strategist",    "role": "Planning"},
    "ARTIFICER":     {"class": "ArtificerAgent",   "name": "Artificer",     "role": "Forge"},
    "VIRTUAL_TWIN":  {"class": "VirtualTwinAgent", "name": "#@*VirtualTwin", "role": "Analysis"},
}


# ═══════════════════════════════════════════════════════════════
#  BRAIN MODULE REGISTRY — Laag 2 (danny_toolkit.brain.*)
#  Tuple: (module_path, class_name)
# ═══════════════════════════════════════════════════════════════

BRAIN_MODULES: Dict[str, tuple] = {
    "Strategist":          ("danny_toolkit.brain.strategist",            "Strategist"),
    "Artificer":           ("danny_toolkit.brain.artificer",             "Artificer"),
    "VoidWalker":          ("danny_toolkit.brain.void_walker",           "VoidWalker"),
    "OmegaGovernor":       ("danny_toolkit.brain.governor",              "OmegaGovernor"),
    "TaskArbitrator":      ("danny_toolkit.brain.arbitrator",            "TaskArbitrator"),
    "AdversarialTribunal": ("danny_toolkit.brain.adversarial_tribunal",  "AdversarialTribunal"),
    "Tribunal":            ("danny_toolkit.brain.tribunal",              "Tribunal"),
    "HallucinatieSchild":  ("danny_toolkit.brain.hallucination_shield",  "HallucinatieSchild"),
    "TheOracleEye":        ("danny_toolkit.brain.oracle_eye",            "TheOracleEye"),
    "DevOpsDaemon":        ("danny_toolkit.brain.devops_daemon",         "DevOpsDaemon"),
    "TheCortex":           ("danny_toolkit.brain.cortex",                "TheCortex"),
    "VirtualTwin":         ("danny_toolkit.brain.virtual_twin",          "VirtualTwin"),
}


# ═══════════════════════════════════════════════════════════════
#  DAEMON MODULE REGISTRY — Laag 3 (danny_toolkit.daemon.*)
# ═══════════════════════════════════════════════════════════════

DAEMON_MODULES: Dict[str, tuple] = {
    "HeartbeatDaemon": ("danny_toolkit.daemon.heartbeat",     "HeartbeatDaemon"),
    "DigitalDaemon":   ("danny_toolkit.daemon.daemon_core",   "DigitalDaemon"),
    "DreamMonitor":    ("danny_toolkit.brain.dream_monitor",  "DreamMonitor"),
    "LimbicSystem":    ("danny_toolkit.daemon.limbic_system", "LimbicSystem"),
    "Metabolisme":     ("danny_toolkit.daemon.metabolisme",   "Metabolisme"),
    "Sensorium":       ("danny_toolkit.daemon.sensorium",     "Sensorium"),
}


# ═══════════════════════════════════════════════════════════════
#  AGENT FACTORY CLASS
# ═══════════════════════════════════════════════════════════════

class AgentFactory:
    """Dynamic Agent Factory met Lazy Loading.

    Thread-safe importlib class loading + agent instantiatie.
    Gebruikt dict caches (geen lru_cache op instance methods).
    God Mode Error Handling — fouten naar logger, nooit bare except:pass.
    """

    def __init__(self) -> None:
        """`Initializes the object, setting up caches for modules, classes, and agents, as well as a lock for thread safety and a placeholder for cosmic roles.

 Args:
  None

 Returns:
  None

 Attributes:
  _module_cache (Dict[str, Any]): Cache for loaded modules.
  _class_cache (Dict[str, type]): Cache for loaded classes.
  _agent_cache (Dict[str, Any]): Cache for loaded agents.
  _lock (threading.Lock): Lock for ensuring thread safety.
  _cosmic_roles (Any): Placeholder for cosmic roles, initially set to None.`"""
        self._module_cache: Dict[str, Any] = {}
        self._class_cache: Dict[str, type] = {}
        self._agent_cache: Dict[str, Any] = {}
        self._lock = threading.Lock()
        self._cosmic_roles = None  # Lazy CosmicRole enum

    # ── Safe Import ──────────────────────────────────────────

    def _safe_import(self, module_path: str) -> Optional[Any]:
        """Import module via importlib met caching. Thread-safe."""
        cached = self._module_cache.get(module_path)
        if cached is not None:
            return cached if cached is not False else None

        with self._lock:
            cached = self._module_cache.get(module_path)
            if cached is not None:
                return cached if cached is not False else None
            try:
                mod = importlib.import_module(module_path)
                self._module_cache[module_path] = mod
                logger.debug("AgentFactory: module %s geladen", module_path)
                return mod
            except ImportError as e:
                logger.debug("AgentFactory: import fout %s: %s", module_path, e)
                self._module_cache[module_path] = False  # Sentinel: import gefaald
                return None

    def _load_class(self, module_path: str, class_name: str) -> Optional[type]:
        """Laad een class uit een module. Thread-safe + cached."""
        cache_key = f"{module_path}:{class_name}"
        cached = self._class_cache.get(cache_key)
        if cached is not None:
            return cached if cached is not False else None

        with self._lock:
            cached = self._class_cache.get(cache_key)
            if cached is not None:
                return cached if cached is not False else None

        mod = self._safe_import(module_path)
        if mod is None:
            self._class_cache[cache_key] = False
            return None

        cls = getattr(mod, class_name, None)
        if cls is None:
            logger.debug("AgentFactory: class %s niet in %s", class_name, module_path)
            self._class_cache[cache_key] = False
            return None

        self._class_cache[cache_key] = cls
        return cls

    # ── CosmicRole Lazy Resolver ─────────────────────────────

    def _get_cosmic_role(self, role_name: str) -> None:
        """Resolve CosmicRole enum — lazy import van trinity_omega."""
        if self._cosmic_roles is None:
            try:
                from danny_toolkit.brain.trinity_omega import CosmicRole
                self._cosmic_roles = CosmicRole
            except ImportError as e:
                logger.debug("AgentFactory: CosmicRole import fout: %s", e)
                self._cosmic_roles = False
        if self._cosmic_roles is False:
            return None
        return getattr(self._cosmic_roles, role_name, None)

    # ── Laag 1: Swarm Agents ────────────────────────────────

    def get_swarm_agent(self, key: str) -> None:
        """Haal een swarm agent op — lazy load + cache.

        Args:
            key: Agent sleutel uit SWARM_BLUEPRINTS (bv. "IOLAAX", "ECHO")

        Returns:
            Agent instance of None bij fout.
        """
        if key in self._agent_cache:
            return self._agent_cache[key]

        bp = SWARM_BLUEPRINTS.get(key)
        if bp is None:
            logger.debug("AgentFactory: onbekende swarm agent '%s'", key)
            return None

        cls = self._load_class(_SWARM_MODULE, bp["class"])
        if cls is None:
            return None

        try:
            cosmic_name = bp.get("cosmic")
            if cosmic_name:
                # BrainAgent subclass: (name, role, cosmic_role)
                cosmic_enum = self._get_cosmic_role(cosmic_name)
                if cosmic_enum is None:
                    logger.debug(
                        "AgentFactory: cosmic role %s niet gevonden, skip %s",
                        cosmic_name, key,
                    )
                    return None
                agent = cls(bp["name"], bp["role"], cosmic_enum)
            else:
                # Agent subclass: (name, role)
                agent = cls(bp["name"], bp["role"])

            self._agent_cache[key] = agent
            return agent
        except Exception as e:
            logger.debug("AgentFactory: instantiatie fout %s: %s", key, e)
            return None

    def build_swarm_agents(self) -> Dict[str, Any]:
        """Bouw alle 18 swarm agents — DRY loop over SWARM_BLUEPRINTS.

        Drop-in alternatief voor SwarmEngine._build_agents().
        Agents die niet laden worden overgeslagen (graceful degradation).

        Returns:
            Dict van agent_key → agent instance.
        """
        result = {}
        for key in SWARM_BLUEPRINTS:
            agent = self.get_swarm_agent(key)
            if agent is not None:
                result[key] = agent
            else:
                logger.debug("AgentFactory: agent %s niet geladen", key)
        logger.debug("AgentFactory: %d/%d swarm agents gebouwd", len(result), len(SWARM_BLUEPRINTS))
        return result

    # ── Laag 2: Brain Modules ────────────────────────────────

    def load_brain_class(self, naam: str) -> Optional[type]:
        """Laad een brain invention class (Laag 2).

        Args:
            naam: Module naam uit BRAIN_MODULES (bv. "Strategist", "OmegaGovernor")

        Returns:
            De class, of None bij ImportError.
        """
        entry = BRAIN_MODULES.get(naam)
        if entry is None:
            logger.debug("AgentFactory: onbekende brain module '%s'", naam)
            return None
        module_path, class_name = entry
        return self._load_class(module_path, class_name)

    # ── Laag 3: Daemon Modules ───────────────────────────────

    def load_daemon_class(self, naam: str) -> Optional[type]:
        """Laad een daemon class (Laag 3).

        Args:
            naam: Module naam uit DAEMON_MODULES (bv. "HeartbeatDaemon")

        Returns:
            De class, of None bij ImportError.
        """
        entry = DAEMON_MODULES.get(naam)
        if entry is None:
            logger.debug("AgentFactory: onbekende daemon '%s'", naam)
            return None
        module_path, class_name = entry
        return self._load_class(module_path, class_name)

    # ── Generieke Class Loader ───────────────────────────────

    def load_any_class(self, module_path: str, class_name: str) -> Optional[type]:
        """Laad een willekeurige class via importlib.

        Bruikbaar voor Laag 4/5 of custom modules.
        """
        return self._load_class(module_path, class_name)

    # ── Introspectie ─────────────────────────────────────────

    def beschikbaar(self) -> Dict[str, List[str]]:
        """Lijst alle geregistreerde namen per laag."""
        return {
            "laag_1_swarm": sorted(SWARM_BLUEPRINTS.keys()),
            "laag_2_brain": sorted(BRAIN_MODULES.keys()),
            "laag_3_daemon": sorted(DAEMON_MODULES.keys()),
        }

    def geladen(self) -> Dict[str, Any]:
        """Status van alle caches — voor diagnostiek."""
        return {
            "agents": sorted(self._agent_cache.keys()),
            "modules_ok": sorted(
                k for k, v in self._module_cache.items() if v is not False
            ),
            "modules_fout": sorted(
                k for k, v in self._module_cache.items() if v is False
            ),
            "classes_ok": sorted(
                k for k, v in self._class_cache.items() if v is not False
            ),
        }

    def agent_count(self) -> Dict[str, int]:
        """Tellingen per laag."""
        return {
            "laag_1_blueprint": len(SWARM_BLUEPRINTS),
            "laag_2_brain": len(BRAIN_MODULES),
            "laag_3_daemon": len(DAEMON_MODULES),
            "cached_agents": len(self._agent_cache),
            "cached_modules": sum(1 for v in self._module_cache.values() if v is not False),
        }

    def clear_cache(self) -> None:
        """Verwijder alle caches — forceert hernieuwde import."""
        with self._lock:
            self._agent_cache.clear()
            self._class_cache.clear()
            self._module_cache.clear()
            self._cosmic_roles = None
        logger.debug("AgentFactory: alle caches gewist")


# ═══════════════════════════════════════════════════════════════
#  SINGLETON — Double-checked locking (project conventie)
# ═══════════════════════════════════════════════════════════════

_factory: Optional[AgentFactory] = None
_factory_lock = threading.Lock()


def get_agent_factory() -> AgentFactory:
    """Singleton AgentFactory — double-checked locking."""
    global _factory
    if _factory is None:
        with _factory_lock:
            if _factory is None:
                _factory = AgentFactory()
    return _factory

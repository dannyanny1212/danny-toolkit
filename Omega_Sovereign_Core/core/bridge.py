"""
Omega Sovereign Core — BackendBridge
=====================================
Brug naar de danny-toolkit backend voor live dashboard data.
Alle calls zijn sync (Streamlit-compatible).
Graceful degradation: als een module niet beschikbaar is → default waarden.

Gebruik:
    from Omega_Sovereign_Core.core.bridge import BackendBridge

    bridge = BackendBridge()
    data = bridge.get_dashboard_data()
"""

import logging
import os
import sys
import time

logger = logging.getLogger(__name__)

# Zorg dat danny-toolkit importeerbaar is
_PARENT = os.path.join(os.path.dirname(__file__), "..", "..")
if _PARENT not in sys.path:
    sys.path.insert(0, _PARENT)


# ── Lazy imports met graceful degradation ──

def _get_waakhuis():
    try:
        from danny_toolkit.brain.waakhuis import get_waakhuis
        return get_waakhuis()
    except Exception as e:
        logger.debug("Waakhuis niet beschikbaar: %s", e)
        return None


def _get_cortical_stack():
    try:
        from danny_toolkit.brain.cortical_stack import get_cortical_stack
        return get_cortical_stack()
    except Exception as e:
        logger.debug("CorticalStack niet beschikbaar: %s", e)
        return None


def _get_bus():
    try:
        from danny_toolkit.core.neural_bus import get_bus
        return get_bus()
    except Exception as e:
        logger.debug("NeuralBus niet beschikbaar: %s", e)
        return None


def _get_key_manager():
    try:
        from danny_toolkit.core.key_manager import get_key_manager
        return get_key_manager()
    except Exception as e:
        logger.debug("KeyManager niet beschikbaar: %s", e)
        return None


# ── BackendBridge ──

class BackendBridge:
    """
    Live data brug naar het danny-toolkit ecosysteem.

    Elke methode retourneert een dict met default waarden
    als de backend niet beschikbaar is.
    """

    def __init__(self):
        self._waakhuis = None
        self._stack = None
        self._bus = None
        self._km = None
        self._initialized = False

    def _init_backends(self):
        """Lazy initialisatie van alle backends."""
        if not self._initialized:
            self._waakhuis = _get_waakhuis()
            self._stack = _get_cortical_stack()
            self._bus = _get_bus()
            self._km = _get_key_manager()
            self._initialized = True

    # ── Dashboard Data (all-in-one) ──

    def get_dashboard_data(self) -> dict:
        """Haal alle dashboard data op in één call.

        Returns:
            Dict met events, agents, failures, vectors, en meer.
        """
        self._init_backends()

        events = 0
        agents = 0
        failures = 0
        vectors = 0

        # CorticalStack: event count
        if self._stack:
            try:
                stats = self._stack.get_stats()
                events = stats.get("episodic_events", 0)
                vectors = stats.get("semantic_facts", 0)
            except Exception as e:
                logger.debug("Stack stats: %s", e)

        # Waakhuis: agent count en failures
        if self._waakhuis:
            try:
                rapport = self._waakhuis.gezondheidsrapport()
                agent_data = rapport.get("agents", {})
                agents = len(agent_data)
                sys_data = rapport.get("systeem", {})
                failures = sys_data.get("totaal_fouten", 0)
            except Exception as e:
                logger.debug("Waakhuis rapport: %s", e)

        return {
            "events": events,
            "agents": agents,
            "failures": failures,
            "vectors": vectors,
            "timestamp": time.time(),
        }

    # ── Agent Health ──

    def get_agent_health(self) -> dict:
        """Haal per-agent health scores op voor de radar chart.

        Returns:
            Dict met agent namen als keys, scores (0-100) als values.
        """
        self._init_backends()

        if not self._waakhuis:
            return {}

        try:
            rapport = self._waakhuis.gezondheidsrapport()
            return {
                naam: info.get("score", 50.0)
                for naam, info in rapport.get("agents", {}).items()
            }
        except Exception as e:
            logger.debug("Agent health: %s", e)
            return {}

    # ── System Metrics ──

    def get_system_metrics(self) -> dict:
        """Haal hardware en systeem metrics op.

        Returns:
            Dict met cpu_percent, ram_percent, gpu_percent, db metrics.
        """
        self._init_backends()

        result = {
            "cpu_percent": -1,
            "ram_percent": -1,
            "gpu_percent": -1,
            "gpu_used_mb": 0,
            "gpu_total_mb": 0,
            "db_size_mb": 0,
            "pending_writes": 0,
        }

        # Hardware via Waakhuis
        if self._waakhuis:
            try:
                hw = self._waakhuis.hardware_status()
                result["cpu_percent"] = hw.get("cpu_percent", -1)
                result["ram_percent"] = hw.get("ram_percent", -1)
                result["gpu_percent"] = hw.get("gpu_percent", -1)
                result["gpu_used_mb"] = hw.get("gpu_used_mb", 0)
                result["gpu_total_mb"] = hw.get("gpu_total_mb", 0)
            except Exception as e:
                logger.debug("Hardware status: %s", e)

        # DB metrics via CorticalStack
        if self._stack:
            try:
                db = self._stack.get_db_metrics()
                result["db_size_mb"] = db.get("db_size_mb", 0)
                result["pending_writes"] = db.get("pending_writes", 0)
            except Exception as e:
                logger.debug("DB metrics: %s", e)

        return result

    # ── Event Feed ──

    def get_event_feed(self, count: int = 20) -> list:
        """Haal recente events op voor de terminal/feed.

        Returns:
            Lijst van event dicts (newest first).
        """
        self._init_backends()

        if not self._stack:
            return []

        try:
            return self._stack.get_recent_events(count=count)
        except Exception as e:
            logger.debug("Event feed: %s", e)
            return []

    # ── API Fuel (Key Manager) ──

    def get_api_fuel(self) -> dict:
        """Haal API quota verbruik op voor de fuel gauge.

        Returns:
            Dict met percentage, keys_beschikbaar, agents_in_cooldown.
        """
        self._init_backends()

        result = {
            "percentage": 0,
            "keys_beschikbaar": 0,
            "agents_in_cooldown": [],
            "totaal_requests": 0,
        }

        if not self._km:
            return result

        try:
            status = self._km.get_status()
            result["keys_beschikbaar"] = status.get("keys_beschikbaar", 0)

            # Bereken fuel percentage op basis van dagelijks token gebruik
            totaal_tokens = 0
            totaal_requests = 0
            for agent_info in status.get("agents", {}).values():
                totaal_tokens += agent_info.get("tpd_huidig", 0)
                totaal_requests += agent_info.get("totaal_requests", 0)

            result["totaal_requests"] = totaal_requests

            # Groq free tier: 500K tokens per dag per key
            max_tokens_dag = result["keys_beschikbaar"] * 500_000
            if max_tokens_dag > 0:
                gebruikt_pct = (totaal_tokens / max_tokens_dag) * 100
                result["percentage"] = min(100, round(100 - gebruikt_pct))
            else:
                result["percentage"] = 0

            # Cooldown agents
            cooldown = self._km.get_agents_in_cooldown()
            result["agents_in_cooldown"] = list(cooldown)

        except Exception as e:
            logger.debug("API fuel: %s", e)

        return result

    # ── NeuralBus Stats ──

    def get_bus_stats(self) -> dict:
        """Haal NeuralBus statistieken op.

        Returns:
            Dict met subscribers, events_gepubliceerd, etc.
        """
        self._init_backends()

        if not self._bus:
            return {}

        try:
            return self._bus.statistieken()
        except Exception as e:
            logger.debug("Bus stats: %s", e)
            return {}

    # ── Stale Agents ──

    def get_stale_agents(self) -> list:
        """Check welke agents niet meer reageren (>60s geen heartbeat).

        Returns:
            Lijst van agent namen.
        """
        self._init_backends()

        if not self._waakhuis:
            return []

        try:
            return self._waakhuis.check_heartbeats()
        except Exception as e:
            logger.debug("Stale agents: %s", e)
            return []

    # ── Full Export (voor debug) ──

    def export_all(self) -> dict:
        """Exporteer alle beschikbare data in één dict."""
        return {
            "dashboard": self.get_dashboard_data(),
            "health": self.get_agent_health(),
            "metrics": self.get_system_metrics(),
            "fuel": self.get_api_fuel(),
            "bus": self.get_bus_stats(),
            "stale": self.get_stale_agents(),
            "events": self.get_event_feed(count=10),
        }

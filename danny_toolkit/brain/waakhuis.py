"""
WaakhuisMonitor — Uitgebreide monitoring wachttoren.
=====================================================
Phase 30 Invention #24: "De VRIEND" — comprehensive monitoring
with persistent storage, health scoring, and hardware metrics.

Singleton via get_waakhuis(). Slaat metrics op in SQLite via
CorticalStack DB. Detecteert stale agents, berekent gezondheidsscores,
en publiceert health events op NeuralBus.

Gebruik:
    from danny_toolkit.brain.waakhuis import get_waakhuis

    waakhuis = get_waakhuis()
    waakhuis.registreer_dispatch("CentralBrain", 245.3)
    waakhuis.registreer_fout("CentralBrain", "TimeoutError", "API timeout na 30s")
    rapport = waakhuis.gezondheidsrapport()
"""

import logging
import math
import os
import sqlite3
import threading
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    from danny_toolkit.core.config import Config
    HAS_CONFIG = True
except ImportError:
    HAS_CONFIG = False

try:
    from danny_toolkit.core.neural_bus import get_bus, EventTypes
    HAS_BUS = True
except ImportError:
    HAS_BUS = False

try:
    from danny_toolkit.core.alerter import get_alerter, AlertLevel
    HAS_ALERTER = True
except ImportError:
    HAS_ALERTER = False


# ── Ernst classificatie ──

ERNST_CLASSIFICATIE = {
    "TimeoutError": "voorbijgaand",
    "asyncio.TimeoutError": "voorbijgaand",
    "ConnectionError": "voorbijgaand",
    "ConnectionResetError": "voorbijgaand",
    "OSError": "voorbijgaand",
    "ValueError": "herstelbaar",
    "KeyError": "herstelbaar",
    "TypeError": "herstelbaar",
    "AttributeError": "herstelbaar",
    "RuntimeError": "kritiek",
    "PermissionError": "kritiek",
    "MemoryError": "kritiek",
}


class WaakhuisMonitor:
    """
    Uitgebreide monitoring wachttoren.

    Houdt per-agent dispatch latencies bij, classificeert fouten,
    berekent gezondheidscores, en detecteert stale agents.
    SQLite-backed persistent opslag.
    """

    HEARTBEAT_TIMEOUT = 60  # seconden — agent is stale na 60s zonder dispatch
    _MAX_LATENCIES = 500    # max latencies per agent in-memory

    def __init__(self, db_path: Optional[str] = None):
        self._lock = threading.Lock()

        # In-memory tracking
        self._latencies: Dict[str, List[float]] = defaultdict(list)
        self._fouten: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self._heartbeats: Dict[str, float] = {}
        self._dispatch_counts: Dict[str, int] = defaultdict(int)
        self._error_counts: Dict[str, int] = defaultdict(int)

        # Stats
        self._stats = {
            "totaal_dispatches": 0,
            "totaal_fouten": 0,
            "alerts_verstuurd": 0,
        }

        # SQLite persistentie
        self._db_path = db_path
        if not db_path and HAS_CONFIG:
            self._db_path = str(Config.DATA_DIR / "waakhuis_metrics.db")
        elif not db_path:
            self._db_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "..", "..", "data", "waakhuis_metrics.db",
            )

        self._conn: Optional[sqlite3.Connection] = None
        self._init_db()

    def _init_db(self):
        """Initialiseer SQLite tabel voor metrics."""
        try:
            self._conn = sqlite3.connect(
                self._db_path,
                check_same_thread=False,
                timeout=5,
            )
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA synchronous=NORMAL")
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS waakhuis_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    agent TEXT NOT NULL,
                    metric_type TEXT NOT NULL,
                    latency_ms REAL,
                    error_type TEXT,
                    error_ernst TEXT,
                    details TEXT
                )
            """)
            self._conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_waakhuis_agent_time
                ON waakhuis_metrics(agent, timestamp)
            """)
            self._conn.commit()
        except Exception as e:
            logger.debug("WaakhuisMonitor DB init fout: %s", e)
            self._conn = None

    def registreer_dispatch(self, agent_naam: str, latency_ms: float):
        """Registreer een succesvolle agent dispatch.

        Args:
            agent_naam: Naam van de agent.
            latency_ms: Uitvoertijd in milliseconden.
        """
        with self._lock:
            self._latencies[agent_naam].append(latency_ms)
            # Begrens in-memory latencies
            if len(self._latencies[agent_naam]) > self._MAX_LATENCIES:
                self._latencies[agent_naam] = self._latencies[agent_naam][-self._MAX_LATENCIES:]
            self._heartbeats[agent_naam] = time.time()
            self._dispatch_counts[agent_naam] += 1
            self._stats["totaal_dispatches"] += 1

        # Persist naar SQLite
        if self._conn:
            try:
                self._conn.execute(
                    "INSERT INTO waakhuis_metrics (timestamp, agent, metric_type, latency_ms) "
                    "VALUES (?, ?, 'dispatch', ?)",
                    (time.time(), agent_naam, latency_ms),
                )
                self._conn.commit()
            except Exception as e:
                logger.debug("WaakhuisMonitor persist dispatch fout: %s", e)

    def registreer_fout(self, agent_naam: str, fout_type: str, beschrijving: str = ""):
        """Registreer een agent fout met ernst classificatie.

        Args:
            agent_naam: Naam van de agent.
            fout_type: Type van de fout (bijv. "TimeoutError").
            beschrijving: Optionele beschrijving.
        """
        ernst = ERNST_CLASSIFICATIE.get(fout_type, "herstelbaar")

        with self._lock:
            self._fouten[agent_naam][fout_type] += 1
            self._error_counts[agent_naam] += 1
            self._stats["totaal_fouten"] += 1

        # Persist naar SQLite
        if self._conn:
            try:
                self._conn.execute(
                    "INSERT INTO waakhuis_metrics "
                    "(timestamp, agent, metric_type, error_type, error_ernst, details) "
                    "VALUES (?, ?, 'error', ?, ?, ?)",
                    (time.time(), agent_naam, fout_type, ernst, beschrijving[:500]),
                )
                self._conn.commit()
            except Exception as e:
                logger.debug("WaakhuisMonitor persist fout: %s", e)

        # Alert bij kritieke fouten
        if ernst == "kritiek":
            self._escaleer_alert(
                f"fout_{agent_naam}_{fout_type}",
                f"Kritieke fout in {agent_naam}: {fout_type} — {beschrijving[:200]}",
            )

    def bereken_percentiel(self, agent_naam: str, percentiel: float) -> float:
        """Bereken latency percentiel voor een agent (pure stdlib).

        Args:
            agent_naam: Naam van de agent.
            percentiel: Gewenst percentiel (0-100).

        Returns:
            Latency in ms op het gevraagde percentiel, of 0.0.
        """
        with self._lock:
            data = sorted(self._latencies.get(agent_naam, []))

        if not data:
            return 0.0

        n = len(data)
        if n == 1:
            return data[0]

        # Lineaire interpolatie (geen numpy nodig)
        k = (percentiel / 100.0) * (n - 1)
        floor_k = math.floor(k)
        ceil_k = min(math.ceil(k), n - 1)

        if floor_k == ceil_k:
            return data[floor_k]

        fractie = k - floor_k
        return data[floor_k] + fractie * (data[ceil_k] - data[floor_k])

    def latency_rapport(self, agent_naam: str) -> dict:
        """Latency rapport met p50/p95/p99 voor een agent.

        Args:
            agent_naam: Naam van de agent.

        Returns:
            Dict met p50, p95, p99, count, gem.
        """
        with self._lock:
            data = list(self._latencies.get(agent_naam, []))
            count = self._dispatch_counts.get(agent_naam, 0)

        if not data:
            return {"p50": 0.0, "p95": 0.0, "p99": 0.0, "count": 0, "gem": 0.0}

        return {
            "p50": round(self.bereken_percentiel(agent_naam, 50), 1),
            "p95": round(self.bereken_percentiel(agent_naam, 95), 1),
            "p99": round(self.bereken_percentiel(agent_naam, 99), 1),
            "count": count,
            "gem": round(sum(data) / len(data), 1),
        }

    def fout_rapport(self, agent_naam: str) -> dict:
        """Fout rapport met error buckets per type.

        Args:
            agent_naam: Naam van de agent.

        Returns:
            Dict met fout tellingen per type en totaal.
        """
        with self._lock:
            fouten = dict(self._fouten.get(agent_naam, {}))
            totaal = self._error_counts.get(agent_naam, 0)

        return {
            "per_type": fouten,
            "totaal": totaal,
        }

    def gezondheidscore(self, agent_naam: str) -> float:
        """Bereken gezondheidsscore (0-100) voor een agent.

        Factoren:
        - Error rate: 40% gewicht (minder fouten = hoger)
        - P95 latency: 35% gewicht (lager = hoger, max 5000ms)
        - Throughput: 25% gewicht (meer dispatches = hoger, max 100)

        Args:
            agent_naam: Naam van de agent.

        Returns:
            Score van 0.0 tot 100.0.
        """
        with self._lock:
            dispatches = self._dispatch_counts.get(agent_naam, 0)
            errors = self._error_counts.get(agent_naam, 0)

        if dispatches == 0:
            return 50.0  # Geen data — neutraal

        # Error rate factor (0-1, lager is beter)
        error_rate = errors / max(dispatches + errors, 1)
        error_score = max(0.0, 1.0 - error_rate * 2)  # 50% errors = 0

        # P95 latency factor (0-1, lager is beter)
        p95 = self.bereken_percentiel(agent_naam, 95)
        latency_score = max(0.0, 1.0 - (p95 / 5000.0))  # 5s = 0

        # Throughput factor (0-1, meer is beter)
        throughput_score = min(1.0, dispatches / 100.0)

        # Gewogen aggregatie
        score = (
            error_score * 0.40
            + latency_score * 0.35
            + throughput_score * 0.25
        ) * 100.0

        return round(max(0.0, min(100.0, score)), 1)

    def gezondheidsrapport(self) -> dict:
        """Volledig gezondheidsrapport voor alle agents.

        Returns:
            Dashboard-ready dict met per-agent scores en systeemstatus.
        """
        with self._lock:
            agent_namen = set(self._dispatch_counts.keys()) | set(self._error_counts.keys())

        rapport = {
            "timestamp": time.time(),
            "agents": {},
            "systeem": dict(self._stats),
        }

        for naam in sorted(agent_namen):
            rapport["agents"][naam] = {
                "score": self.gezondheidscore(naam),
                "latency": self.latency_rapport(naam),
                "fouten": self.fout_rapport(naam),
            }

        # Publiceer gezondheid op NeuralBus
        self._publiceer_gezondheid(rapport)

        return rapport

    def check_heartbeats(self) -> List[str]:
        """Detecteer stale agents (>HEARTBEAT_TIMEOUT zonder dispatch).

        Returns:
            Lijst van stale agent namen.
        """
        now = time.time()
        stale = []
        with self._lock:
            for agent_naam, last_seen in self._heartbeats.items():
                if now - last_seen > self.HEARTBEAT_TIMEOUT:
                    stale.append(agent_naam)

        for agent_naam in stale:
            self._escaleer_alert(
                f"heartbeat_{agent_naam}",
                f"Agent {agent_naam} geen dispatch voor >{self.HEARTBEAT_TIMEOUT}s",
            )

        return stale

    def hardware_status(self) -> dict:
        """Hardware status metrics (CPU, RAM, optioneel GPU).

        Returns:
            Dict met cpu_percent, ram_percent, optioneel gpu info.
        """
        status = {}

        try:
            import psutil
            status["cpu_percent"] = psutil.cpu_percent(interval=0.1)
            mem = psutil.virtual_memory()
            status["ram_percent"] = mem.percent
            status["ram_beschikbaar_mb"] = round(mem.available / (1024 * 1024), 1)
        except ImportError:
            status["cpu_percent"] = -1
            status["ram_percent"] = -1
            status["psutil_beschikbaar"] = False
        except Exception as e:
            logger.debug("psutil error: %s", e)
            status["cpu_percent"] = -1
            status["ram_percent"] = -1

        # GPU via pynvml (optioneel)
        try:
            import pynvml
            pynvml.nvmlInit()
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
            status["gpu_used_mb"] = round(mem_info.used / (1024 * 1024), 1)
            status["gpu_total_mb"] = round(mem_info.total / (1024 * 1024), 1)
            status["gpu_percent"] = round(mem_info.used / mem_info.total * 100, 1)
            pynvml.nvmlShutdown()
        except Exception:
            status["gpu_beschikbaar"] = False

        return status

    def _escaleer_alert(self, alert_key: str, bericht: str):
        """Verstuur en escaleer alerts bij herhaalde problemen."""
        self._stats["alerts_verstuurd"] += 1

        if HAS_ALERTER:
            try:
                get_alerter().alert(
                    AlertLevel.WAARSCHUWING,
                    bericht,
                    bron="waakhuis",
                )
            except Exception as e:
                logger.debug("Waakhuis alerter fout: %s", e)

        if HAS_BUS:
            try:
                get_bus().publish(
                    EventTypes.WAAKHUIS_ALERT,
                    {"key": alert_key, "bericht": bericht},
                    bron="waakhuis",
                )
            except Exception as e:
                logger.debug("Waakhuis NeuralBus publish fout: %s", e)

    def _publiceer_gezondheid(self, rapport: dict):
        """Publiceer gezondheidsrapport op NeuralBus."""
        if HAS_BUS:
            try:
                # Compact summary voor NeuralBus
                scores = {
                    naam: info["score"]
                    for naam, info in rapport.get("agents", {}).items()
                }
                get_bus().publish(
                    EventTypes.WAAKHUIS_HEALTH,
                    {"scores": scores, "systeem": rapport.get("systeem", {})},
                    bron="waakhuis",
                )
            except Exception as e:
                logger.debug("Waakhuis health publish fout: %s", e)

    def opruimen(self, dagen: int = 30):
        """Verwijder metrics ouder dan N dagen uit SQLite.

        Args:
            dagen: Aantal dagen te bewaren (standaard 30).
        """
        if not self._conn:
            return

        cutoff = time.time() - (dagen * 86400)
        try:
            cursor = self._conn.execute(
                "DELETE FROM waakhuis_metrics WHERE timestamp < ?",
                (cutoff,),
            )
            self._conn.commit()
            logger.info("WaakhuisMonitor: %d oude metrics verwijderd", cursor.rowcount)
        except Exception as e:
            logger.debug("WaakhuisMonitor opruimen fout: %s", e)

    def export_dashboard(self) -> dict:
        """Extended stats voor dashboard export.

        Returns:
            Dict met gezondheidsrapport + hardware + heartbeats.
        """
        return {
            "gezondheid": self.gezondheidsrapport(),
            "hardware": self.hardware_status(),
            "stale_agents": self.check_heartbeats(),
            "stats": dict(self._stats),
        }

    def get_stats(self) -> dict:
        """Retourneer Waakhuis statistieken."""
        with self._lock:
            return dict(self._stats)

    def reset_stats(self):
        """Reset alle in-memory tracking (voor tests)."""
        with self._lock:
            self._latencies.clear()
            self._fouten.clear()
            self._heartbeats.clear()
            self._dispatch_counts.clear()
            self._error_counts.clear()
            self._stats = {
                "totaal_dispatches": 0,
                "totaal_fouten": 0,
                "alerts_verstuurd": 0,
            }

    def close(self):
        """Sluit SQLite connectie."""
        if self._conn:
            try:
                self._conn.close()
            except Exception as e:
                logger.debug("WaakhuisMonitor close fout: %s", e)
            self._conn = None


# ── Singleton ──

_waakhuis_instance: Optional[WaakhuisMonitor] = None
_waakhuis_lock = threading.Lock()


def get_waakhuis() -> WaakhuisMonitor:
    """Verkrijg de singleton WaakhuisMonitor instantie."""
    global _waakhuis_instance
    if _waakhuis_instance is None:
        with _waakhuis_lock:
            if _waakhuis_instance is None:
                _waakhuis_instance = WaakhuisMonitor()
    return _waakhuis_instance

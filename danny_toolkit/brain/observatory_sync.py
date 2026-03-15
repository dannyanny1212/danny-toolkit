# danny_toolkit/brain/observatory_sync.py
"""
ObservatorySync -- Generaal Controlekamer (Phase 42, Invention #26).
=====================================================================
Aggregeert real-time statistieken van de Generaal (ModelRegistry + TaskArbitrator)
tot een unified observatory view. Welk model kost hoeveel tokens, wie faalt het
vaakst, en hoe presteren de veilingen?

Singleton: ``get_observatory_sync()``.

Gebruik:
    from danny_toolkit.brain.observatory_sync import get_observatory_sync

    obs = get_observatory_sync()
    dashboard = obs.get_dashboard_data()
    leaderboard = obs.get_model_leaderboard()
    auction_log = obs.get_auction_history()
"""

from __future__ import annotations

import logging
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from danny_toolkit.core.config import Config
from danny_toolkit.core.utils import Kleur

logger = logging.getLogger(__name__)

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
    from danny_toolkit.brain.model_sync import get_model_registry, ModelWorker
    HAS_REGISTRY = True
except ImportError:
    HAS_REGISTRY = False

try:
    from danny_toolkit.brain.arbitrator import get_arbitrator
    HAS_ARBITRATOR = True
except ImportError:
    HAS_ARBITRATOR = False


# -- Data Models --

@dataclass
class ModelObservatoryEntry:
    """Per-model statistiek snapshot."""
    provider: str
    model_id: str
    calls: int = 0
    successes: int = 0
    failures: int = 0
    barrier_rejections: int = 0
    total_tokens: int = 0
    total_latency_ms: float = 0.0
    avg_latency_ms: float = 0.0
    success_rate: float = 0.0
    cost_tier: int = 1
    latency_class: int = 1
    circuit_open: bool = False
    beschikbaar: bool = True

    def to_dict(self) -> dict:
        """Serialiseer naar dict voor JSON/API."""
        return {
            "provider": self.provider,
            "model_id": self.model_id,
            "calls": self.calls,
            "successes": self.successes,
            "failures": self.failures,
            "barrier_rejections": self.barrier_rejections,
            "total_tokens": self.total_tokens,
            "total_latency_ms": round(self.total_latency_ms, 1),
            "avg_latency_ms": round(self.avg_latency_ms, 1),
            "success_rate": round(self.success_rate, 3),
            "cost_tier": self.cost_tier,
            "latency_class": self.latency_class,
            "circuit_open": self.circuit_open,
            "beschikbaar": self.beschikbaar,
        }


@dataclass
class AuctionLogEntry:
    """Log van een model-veiling."""
    timestamp: float
    task_id: str
    task_categorie: str
    winnaar_provider: str
    winnaar_model_id: str
    winnaar_score: float
    deelnemers: int
    barrier_pass: Optional[bool] = None

    def to_dict(self) -> dict:
        """Returns a dictionary representation of the object.

* timestamp: The timestamp associated with the object.
* task_id: The ID of the task.
* task_categorie: The category of the task.
* winnaar_provider: The provider of the winning model.
* winnaar_model_id: The ID of the winning model.
* winnaar_score: The score of the winning model, rounded to 4 decimal places.
* deelnemers: A list of participants.
* barrier_pass: A flag indicating whether a barrier was passed.

Returns:
  dict: A dictionary containing the object's attributes."""
        return {
            "timestamp": self.timestamp,
            "task_id": self.task_id,
            "task_categorie": self.task_categorie,
            "winnaar_provider": self.winnaar_provider,
            "winnaar_model_id": self.winnaar_model_id,
            "winnaar_score": round(self.winnaar_score, 4),
            "deelnemers": self.deelnemers,
            "barrier_pass": self.barrier_pass,
        }


@dataclass
class ObservatoryDashboard:
    """Samengevatte dashboard data."""
    totaal_modellen: int = 0
    beschikbare_modellen: int = 0
    totaal_calls: int = 0
    totaal_tokens: int = 0
    totaal_successen: int = 0
    totaal_failures: int = 0
    totaal_barrier_rejections: int = 0
    gemiddelde_latency_ms: float = 0.0
    gemiddelde_success_rate: float = 0.0
    # Arbitrator stats
    goals_processed: int = 0
    tasks_decomposed: int = 0
    model_auctions_held: int = 0
    model_tasks_completed: int = 0
    model_tasks_failed: int = 0
    barrier_rejections_arbitrator: int = 0
    # Per-model breakdown
    modellen: List[Dict] = field(default_factory=list)
    # Recent auctions
    recente_veilingen: List[Dict] = field(default_factory=list)
    timestamp: str = ""

    def to_dict(self) -> dict:
        return {
            "totaal_modellen": self.totaal_modellen,
            "beschikbare_modellen": self.beschikbare_modellen,
            "totaal_calls": self.totaal_calls,
            "totaal_tokens": self.totaal_tokens,
            "totaal_successen": self.totaal_successen,
            "totaal_failures": self.totaal_failures,
            "totaal_barrier_rejections": self.totaal_barrier_rejections,
            "gemiddelde_latency_ms": round(self.gemiddelde_latency_ms, 1),
            "gemiddelde_success_rate": round(self.gemiddelde_success_rate, 3),
            "goals_processed": self.goals_processed,
            "tasks_decomposed": self.tasks_decomposed,
            "model_auctions_held": self.model_auctions_held,
            "model_tasks_completed": self.model_tasks_completed,
            "model_tasks_failed": self.model_tasks_failed,
            "barrier_rejections_arbitrator": self.barrier_rejections_arbitrator,
            "modellen": self.modellen,
            "recente_veilingen": self.recente_veilingen,
            "timestamp": self.timestamp,
        }


class ObservatorySync:
    """
    OBSERVATORY SYNC -- Generaal Controlekamer (Invention #26)
    ===========================================================
    Live controlekamer voor je API's. Aggregeert statistieken van:
    - ModelRegistry: per-model calls, tokens, latency, success rate
    - TaskArbitrator: goals, auctions, barrier rejections
    - AuctionLog: recente veilingresultaten

    Features:
    - Model leaderboard (wie presteert het best?)
    - Cost analysis (wie verbruikt de meeste tokens?)
    - Failure tracking (wie faalt het vaakst?)
    - Auction history (welke veilingen zijn gehouden?)
    - CorticalStack logging voor historische trends
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._auction_log: deque = deque(maxlen=200)
        self._snapshot_history: deque = deque(maxlen=50)
        self._stats = {
            "snapshots_taken": 0,
            "leaderboard_queries": 0,
            "auction_logs_recorded": 0,
        }

    # -- Model Observatory --

    def _collect_model_entries(self) -> List[ModelObservatoryEntry]:
        """Verzamel per-model statistieken uit de ModelRegistry."""
        if not HAS_REGISTRY:
            return []

        entries = []
        try:
            registry = get_model_registry()
            workers = registry.get_all_workers()
            for worker in workers:
                perf = worker.get_perf()
                entry = ModelObservatoryEntry(
                    provider=perf.get("provider", "unknown"),
                    model_id=perf.get("model_id", "unknown"),
                    calls=perf.get("calls", 0),
                    successes=perf.get("successes", 0),
                    failures=perf.get("failures", 0),
                    barrier_rejections=perf.get("barrier_rejections", 0),
                    total_tokens=perf.get("total_tokens", 0),
                    total_latency_ms=perf.get("total_latency_ms", 0.0),
                    avg_latency_ms=perf.get("avg_latency_ms", 0.0),
                    success_rate=perf.get("success_rate", 0.0),
                    cost_tier=getattr(worker.profile, "cost_tier", 1),
                    latency_class=getattr(worker.profile, "latency_class", 1),
                    circuit_open=perf.get("circuit_open", False),
                    beschikbaar=worker.is_available(),
                )
                entries.append(entry)
        except Exception as e:
            logger.debug("ObservatorySync model collect error: %s", e)

        return entries

    def _collect_arbitrator_stats(self) -> Dict[str, Any]:
        """Verzamel TaskArbitrator statistieken."""
        if not HAS_ARBITRATOR:
            return {}

        try:
            arb = get_arbitrator()
            return arb.get_stats()
        except Exception as e:
            logger.debug("ObservatorySync arbitrator collect error: %s", e)
            return {}

    # -- Dashboard --

    def get_dashboard_data(self) -> ObservatoryDashboard:
        """Genereer een compleet dashboard snapshot.

        Returns:
            ObservatoryDashboard met alle actuele data.
        """
        entries = self._collect_model_entries()
        arb_stats = self._collect_arbitrator_stats()

        # Aggregeer model stats
        totaal_calls = sum(e.calls for e in entries)
        totaal_tokens = sum(e.total_tokens for e in entries)
        totaal_successen = sum(e.successes for e in entries)
        totaal_failures = sum(e.failures for e in entries)
        totaal_barrier = sum(e.barrier_rejections for e in entries)
        totaal_latency = sum(e.total_latency_ms for e in entries)

        gem_latency = totaal_latency / max(totaal_calls, 1)
        gem_success = totaal_successen / max(totaal_calls, 1) if totaal_calls > 0 else 0.0

        dashboard = ObservatoryDashboard(
            totaal_modellen=len(entries),
            beschikbare_modellen=sum(1 for e in entries if e.beschikbaar),
            totaal_calls=totaal_calls,
            totaal_tokens=totaal_tokens,
            totaal_successen=totaal_successen,
            totaal_failures=totaal_failures,
            totaal_barrier_rejections=totaal_barrier,
            gemiddelde_latency_ms=gem_latency,
            gemiddelde_success_rate=gem_success,
            # Arbitrator
            goals_processed=arb_stats.get("goals_processed", 0),
            tasks_decomposed=arb_stats.get("tasks_decomposed", 0),
            model_auctions_held=arb_stats.get("model_auctions_held", 0),
            model_tasks_completed=arb_stats.get("model_tasks_completed", 0),
            model_tasks_failed=arb_stats.get("model_tasks_failed", 0),
            barrier_rejections_arbitrator=arb_stats.get("barrier_rejections", 0),
            # Per-model
            modellen=[e.to_dict() for e in entries],
            # Recente veilingen
            recente_veilingen=[a.to_dict() for a in list(self._auction_log)[-20:]],
            timestamp=datetime.now().isoformat(),
        )

        # Track snapshot
        with self._lock:
            self._stats["snapshots_taken"] += 1
            self._snapshot_history.append({
                "timestamp": time.time(),
                "totaal_calls": totaal_calls,
                "totaal_tokens": totaal_tokens,
                "gem_latency_ms": round(gem_latency, 1),
                "gem_success_rate": round(gem_success, 3),
            })

        return dashboard

    # -- Leaderboard --

    def get_model_leaderboard(self, sort_by: str = "success_rate") -> List[Dict]:
        """Genereer een model leaderboard.

        Args:
            sort_by: Sorteercriterium. Opties: 'success_rate', 'calls',
                     'avg_latency_ms', 'total_tokens', 'failures'.

        Returns:
            Gesorteerde lijst van model entries met rank.
        """
        with self._lock:
            self._stats["leaderboard_queries"] += 1

        entries = self._collect_model_entries()
        if not entries:
            return []

        # Sorteer
        reverse = sort_by != "avg_latency_ms"  # Lagere latency = beter
        if sort_by == "failures":
            reverse = False  # Minder failures = beter

        entries.sort(
            key=lambda e: getattr(e, sort_by, 0),
            reverse=reverse,
        )

        result = []
        for rank, entry in enumerate(entries, 1):
            d = entry.to_dict()
            d["rank"] = rank
            result.append(d)

        return result

    # -- Auction History --

    def record_auction(
        self,
        task_id: str,
        task_categorie: str,
        winnaar_provider: str,
        winnaar_model_id: str,
        winnaar_score: float,
        deelnemers: int,
        barrier_pass: Optional[bool] = None,
    ):
        """Registreer een model-veiling in de history log.

        Args:
            task_id: ID van de taak.
            task_categorie: Categorie (code, research, etc.).
            winnaar_provider: Provider van het winnende model.
            winnaar_model_id: Model ID van de winnaar.
            winnaar_score: Auction score.
            deelnemers: Aantal deelnemende modellen.
            barrier_pass: Resultaat van 95% Barrier (None = niet getest).
        """
        entry = AuctionLogEntry(
            timestamp=time.time(),
            task_id=task_id,
            task_categorie=task_categorie,
            winnaar_provider=winnaar_provider,
            winnaar_model_id=winnaar_model_id,
            winnaar_score=winnaar_score,
            deelnemers=deelnemers,
            barrier_pass=barrier_pass,
        )

        with self._lock:
            self._auction_log.append(entry)
            self._stats["auction_logs_recorded"] += 1

        # Log naar CorticalStack
        self._log_auction(entry)

        # Publiceer op NeuralBus
        self._publiceer_auction(entry)

    def get_auction_history(self, count: int = 50) -> List[Dict]:
        """Haal recente veiling-logs op.

        Args:
            count: Aantal recente veilingen (max 200).

        Returns:
            Lijst van AuctionLogEntry dicts, nieuwste eerst.
        """
        with self._lock:
            items = list(self._auction_log)
        items.reverse()  # Nieuwste eerst
        return [a.to_dict() for a in items[:min(count, 200)]]

    # -- Cost Analysis --

    def get_cost_analysis(self) -> Dict[str, Any]:
        """Analyseer token-verbruik per provider en per model.

        Returns:
            Dict met per-provider en per-model token-verbruik,
            plus aanbevelingen.
        """
        entries = self._collect_model_entries()
        if not entries:
            return {"per_provider": {}, "per_model": [], "aanbevelingen": []}

        per_provider: Dict[str, Dict[str, Any]] = {}
        for e in entries:
            if e.provider not in per_provider:
                per_provider[e.provider] = {
                    "tokens": 0, "calls": 0, "cost_tier": e.cost_tier,
                }
            per_provider[e.provider]["tokens"] += e.total_tokens
            per_provider[e.provider]["calls"] += e.calls

        per_model = sorted(
            [e.to_dict() for e in entries],
            key=lambda m: m["total_tokens"],
            reverse=True,
        )

        # Aanbevelingen
        aanbevelingen = []
        for e in entries:
            if e.cost_tier >= 3 and e.success_rate < 0.7:
                aanbevelingen.append(
                    f"{e.provider}/{e.model_id}: duur (tier {e.cost_tier}) maar lage "
                    f"success rate ({e.success_rate:.0%}). Overweeg vervanging."
                )
            if e.circuit_open:
                aanbevelingen.append(
                    f"{e.provider}/{e.model_id}: circuit open. "
                    f"Model is tijdelijk onbeschikbaar ({e.failures} failures)."
                )
            if e.calls > 10 and e.avg_latency_ms > 5000:
                aanbevelingen.append(
                    f"{e.provider}/{e.model_id}: hoge gemiddelde latency "
                    f"({e.avg_latency_ms:.0f}ms). Overweeg sneller alternatief."
                )

        return {
            "per_provider": per_provider,
            "per_model": per_model,
            "aanbevelingen": aanbevelingen,
        }

    # -- Failure Analysis --

    def get_failure_analysis(self) -> Dict[str, Any]:
        """Analyseer faal-patronen per model.

        Returns:
            Dict met failure breakdown en probleemmodellen.
        """
        entries = self._collect_model_entries()
        if not entries:
            return {"modellen": [], "probleemmodellen": [], "totaal_failures": 0}

        # Sorteer op failures (meeste eerst)
        sorted_entries = sorted(entries, key=lambda e: e.failures, reverse=True)

        probleemmodellen = [
            e.to_dict() for e in sorted_entries
            if e.failures > 0 or e.barrier_rejections > 0 or e.circuit_open
        ]

        return {
            "modellen": [e.to_dict() for e in sorted_entries],
            "probleemmodellen": probleemmodellen,
            "totaal_failures": sum(e.failures for e in entries),
            "totaal_barrier_rejections": sum(e.barrier_rejections for e in entries),
            "circuit_open_count": sum(1 for e in entries if e.circuit_open),
        }

    # -- Trend Data --

    def get_trend_data(self) -> List[Dict]:
        """Haal historische snapshot trends op voor grafieken.

        Returns:
            Lijst van snapshot-punten (timestamp, calls, tokens, latency, success_rate).
        """
        with self._lock:
            return list(self._snapshot_history)

    # -- Stats --

    def get_stats(self) -> dict:
        """ObservatorySync interne statistieken."""
        with self._lock:
            return {
                **self._stats,
                "auction_log_size": len(self._auction_log),
                "snapshot_history_size": len(self._snapshot_history),
            }

    # -- Logging --

    def _log_auction(self, entry: AuctionLogEntry) -> None:
        """Log veiling naar CorticalStack."""
        if not HAS_STACK:
            return
        try:
            stack = get_cortical_stack()
            stack.log_event(
                actor="observatory_sync",
                action="model_auction_recorded",
                details={
                    "task_id": entry.task_id,
                    "winnaar": f"{entry.winnaar_provider}/{entry.winnaar_model_id}",
                    "score": entry.winnaar_score,
                    "deelnemers": entry.deelnemers,
                    "barrier_pass": entry.barrier_pass,
                },
                source="observatory_sync",
            )
        except Exception as e:
            logger.debug("ObservatorySync CorticalStack log error: %s", e)

    def _publiceer_auction(self, entry: AuctionLogEntry) -> None:
        """Publiceer veiling-event op NeuralBus."""
        if not HAS_BUS:
            return
        try:
            event_type = getattr(
                EventTypes, "MODEL_AUCTION_COMPLETED", EventTypes.SYSTEM_EVENT,
            )
            get_bus().publish(
                event_type,
                {
                    "task_id": entry.task_id,
                    "winnaar": f"{entry.winnaar_provider}/{entry.winnaar_model_id}",
                    "score": round(entry.winnaar_score, 4),
                },
                bron="observatory_sync",
            )
        except Exception as e:
            logger.debug("ObservatorySync NeuralBus publish error: %s", e)


# -- Singleton Factory --

_observatory_instance: Optional["ObservatorySync"] = None
_observatory_lock = threading.Lock()


def get_observatory_sync() -> "ObservatorySync":
    """Return the process-wide ObservatorySync singleton (double-checked locking)."""
    global _observatory_instance
    if _observatory_instance is None:
        with _observatory_lock:
            if _observatory_instance is None:
                _observatory_instance = ObservatorySync()
    return _observatory_instance

"""
Sovereign Engine — De Generaal van de Swarm.

Orkesreert het hele agent-netwerk. Beheert de Swarm Snapshot Protocol
voor veilige shutdowns zonder Boundary Violations.

De Engine leeft in /core/ (Body). Hij kan NIET direct:
- De gedachten van /brain/ (Mind) lezen
- Naar /data/ (Soul) schrijven
Hij communiceert uitsluitend via NeuralBus events en de
Universal Save Protocol (lifecycle.py).

Swarm Snapshot Protocol:
    1. CEASEFIRE  — Stop nieuwe inputs, broadcast SWARM_SUSPEND
    2. ROLL-CALL  — Verzamel state van elke actieve agent
    3. SEAL       — Onderteken de snapshot met EventSigner
    4. HAND-OFF   — Route naar SecureMemoryInterface via lifecycle

Gebruik:
    from danny_toolkit.omega_sovereign_core.sovereign_engine import (
        get_sovereign_engine, SovereignEngine
    )
    engine = get_sovereign_engine()
    engine.register_agent("oracle", oracle_instance)
    engine.run()  # of: await engine.run_async()
"""

import asyncio
import logging
import queue
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Deque, Dict, List, Optional, Protocol, Tuple

logger = logging.getLogger(__name__)

try:
    from danny_toolkit.core.utils import Kleur
except ImportError:
    class Kleur:
        GROEN = ROOD = GEEL = CYAAN = RESET = ""


# ── Agent Protocol ──

class SwarmAgent(Protocol):
    """Protocol dat elke agent in de swarm moet implementeren."""

    def get_state(self) -> dict:
        """Retourneer de huidige state voor snapshot."""
        ...

    @property
    def name(self) -> str:
        """Unieke agent naam."""
        ...


# ── Async Violation Queue (Phase 1: Decoupling) ──

class ViolationSweeper:
    """
    Fire-and-forget achtergrond thread die violations uit een queue
    naar de CorticalStack schrijft. Voorkomt deadlocks tussen
    EventSigner ↔ NeuralBus ↔ CorticalStack.
    """

    def __init__(self, max_queue_size: int = 10000):
        self._queue: queue.Queue = queue.Queue(maxsize=max_queue_size)
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._stats = {"processed": 0, "dropped": 0}

    def start(self) -> None:
        """Start de sweeper thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._sweep_loop,
            name="ViolationSweeper",
            daemon=True,
        )
        self._thread.start()
        logger.debug("ViolationSweeper gestart")

    def stop(self) -> None:
        """Stop de sweeper (drains de queue eerst)."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._queue.put(None)  # Sentinel
            self._thread.join(timeout=5.0)

    def submit(self, event_type: str, data: dict, bron: str = "unknown") -> bool:
        """
        Submit een violation voor achtergrond-verwerking.
        Non-blocking: retourneert False als de queue vol is.
        """
        try:
            self._queue.put_nowait({
                "event_type": event_type,
                "data": data,
                "bron": bron,
                "timestamp": datetime.now().isoformat(),
            })
            return True
        except queue.Full:
            self._stats["dropped"] += 1
            logger.debug("ViolationSweeper queue vol — event gedropt")
            return False

    def _sweep_loop(self) -> None:
        """Achtergrond loop: drain queue → CorticalStack."""
        stack = None
        try:
            from danny_toolkit.brain.cortical_stack import get_cortical_stack
            stack = get_cortical_stack()
        except (ImportError, Exception) as e:
            logger.debug("ViolationSweeper: CorticalStack niet beschikbaar: %s", e)

        while self._running:
            try:
                item = self._queue.get(timeout=1.0)
                if item is None:  # Sentinel
                    break
                if stack:
                    try:
                        stack.log_event(
                            bron=item.get("bron", "sweeper"),
                            event_type=item.get("event_type", "violation"),
                            data=item.get("data", {}),
                        )
                    except Exception as e:
                        logger.debug("Sweeper write fout: %s", e)
                self._stats["processed"] += 1
                self._queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                logger.debug("Sweeper loop fout: %s", e)

    def get_stats(self) -> dict:
        return {
            **self._stats,
            "queue_size": self._queue.qsize(),
            "running": self._running,
        }


# ── Swarm Snapshot ──

@dataclass
class SwarmSnapshot:
    """Volledige snapshot van de swarm-state op één moment."""
    timestamp: str
    engine_status: str
    agents: Dict[str, dict] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    signature: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "engine_status": self.engine_status,
            "agent_count": len(self.agents),
            "agents": self.agents,
            "metadata": self.metadata,
            "signature": self.signature,
        }


class SovereignEngine:
    """
    De Generaal — orkestrator van de agent-swarm.

    Beheert:
    - Agent registratie en health tracking
    - Swarm Snapshot Protocol (veilige shutdowns)
    - ViolationSweeper (async decoupling)
    - NeuralBus event broadcasting
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._agents: Dict[str, Any] = {}  # naam -> agent instance
        self._agent_health: Dict[str, dict] = {}  # naam -> health info
        self._status = "initializing"
        self._sweeper = ViolationSweeper()
        self._bus = None
        self._signer = None
        self._backends_loaded = False
        self._stats = {
            "agents_registered": 0,
            "snapshots_taken": 0,
            "shutdowns_executed": 0,
        }

    def _ensure_backends(self) -> None:
        """Lazy backend verbindingen — pas laden bij eerste gebruik."""
        if self._backends_loaded:
            return
        self._backends_loaded = True
        try:
            from danny_toolkit.core.neural_bus import get_bus
            self._bus = get_bus()
        except (ImportError, Exception) as e:
            logger.debug("NeuralBus niet beschikbaar voor SovereignEngine: %s", e)
        try:
            from danny_toolkit.omega_sovereign_core.event_signing import get_event_signer
            self._signer = get_event_signer()
        except (ImportError, Exception) as e:
            logger.debug("EventSigner niet beschikbaar voor SovereignEngine: %s", e)

    # ══════════════════════════════════════════════════════════
    #  AGENT MANAGEMENT
    # ══════════════════════════════════════════════════════════

    def register_agent(self, name: str, agent: Any) -> None:
        """Registreer een agent in de swarm."""
        with self._lock:
            self._agents[name] = agent
            self._agent_health[name] = {
                "registered_at": datetime.now().isoformat(),
                "last_heartbeat": datetime.now().isoformat(),
                "status": "active",
            }
            self._stats["agents_registered"] += 1
        logger.debug("Agent '%s' geregistreerd in swarm", name)

    def unregister_agent(self, name: str) -> None:
        """Verwijder een agent uit de swarm."""
        with self._lock:
            self._agents.pop(name, None)
            self._agent_health.pop(name, None)

    def get_active_agents(self) -> List[str]:
        """Lijst van actieve agent-namen."""
        with self._lock:
            return list(self._agents.keys())

    def agent_heartbeat(self, name: str) -> None:
        """Update de heartbeat timestamp voor een agent."""
        with self._lock:
            if name in self._agent_health:
                self._agent_health[name]["last_heartbeat"] = datetime.now().isoformat()

    # ══════════════════════════════════════════════════════════
    #  SWARM SNAPSHOT PROTOCOL
    # ══════════════════════════════════════════════════════════

    def generate_swarm_snapshot(self) -> SwarmSnapshot:
        """
        Genereer een volledige snapshot van de swarm.

        Stap 1 (ROLL-CALL): Vraag elke agent om zijn state
        Stap 2 (SEAL): Onderteken de snapshot
        """
        self._ensure_backends()
        now = datetime.now().isoformat()

        # ── Roll-Call: verzamel agent states ──
        agent_states = {}
        with self._lock:
            for name, agent in self._agents.items():
                try:
                    if hasattr(agent, "get_state") and callable(agent.get_state):
                        agent_states[name] = agent.get_state()
                    else:
                        agent_states[name] = {
                            "status": "no_get_state",
                            "type": type(agent).__name__,
                        }
                except Exception as e:
                    agent_states[name] = {
                        "status": "error",
                        "error": str(e),
                    }
                    logger.debug("Snapshot fout voor agent '%s': %s", name, e)

        snapshot = SwarmSnapshot(
            timestamp=now,
            engine_status=self._status,
            agents=agent_states,
            metadata={
                "total_agents": len(self._agents),
                "responding_agents": sum(
                    1 for s in agent_states.values()
                    if s.get("status") != "error"
                ),
                "sweeper": self._sweeper.get_stats(),
            },
        )

        # ── Seal: onderteken ──
        if self._signer:
            try:
                snapshot.signature = self._signer.sign(
                    event_type="swarm_snapshot",
                    data={"agent_count": len(agent_states), "timestamp": now},
                    bron="sovereign_engine",
                )
            except Exception as e:
                logger.debug("Snapshot signing mislukt: %s", e)

        with self._lock:
            self._stats["snapshots_taken"] += 1

        return snapshot

    # ══════════════════════════════════════════════════════════
    #  SHUTDOWN PROTOCOL
    # ══════════════════════════════════════════════════════════

    def execute_shutdown(self) -> bool:
        """
        Voer het volledige Swarm Snapshot Protocol uit.

        1. CEASEFIRE  — Broadcast SWARM_SUSPEND
        2. ROLL-CALL  — Genereer snapshot
        3. SEAL       — Onderteken
        4. HAND-OFF   — Route naar Universal Save Protocol
        """
        self._ensure_backends()
        print(f"\n{Kleur.CYAAN}{'═' * 50}")
        print(f"  SWARM SNAPSHOT PROTOCOL")
        print(f"{'═' * 50}{Kleur.RESET}")

        self._status = "shutting_down"

        # ── 1. CEASEFIRE ──
        print(f"{Kleur.GEEL}  [1/4] CEASEFIRE — Broadcasting SWARM_SUSPEND...{Kleur.RESET}")
        if self._bus:
            try:
                self._bus.publish(
                    event_type="system_event",
                    data={
                        "action": "SWARM_SUSPEND",
                        "timestamp": datetime.now().isoformat(),
                    },
                    bron="sovereign_engine",
                )
            except Exception as e:
                logger.debug("SWARM_SUSPEND broadcast mislukt: %s", e)

        # ── 2. ROLL-CALL ──
        print(f"{Kleur.GEEL}  [2/4] ROLL-CALL — Collecting agent states...{Kleur.RESET}")
        snapshot = self.generate_swarm_snapshot()
        responding = snapshot.metadata.get("responding_agents", 0)
        total = snapshot.metadata.get("total_agents", 0)
        print(f"         {responding}/{total} agents responded")

        # ── 3. SEAL (al gedaan in generate_swarm_snapshot) ──
        if snapshot.signature:
            print(f"{Kleur.GROEN}  [3/4] SEAL — Snapshot ondertekend{Kleur.RESET}")
        else:
            print(f"{Kleur.GEEL}  [3/4] SEAL — Geen signer beschikbaar{Kleur.RESET}")

        # ── 4. HAND-OFF ──
        print(f"{Kleur.GEEL}  [4/4] HAND-OFF — Routing naar Universal Save Protocol...{Kleur.RESET}")
        try:
            from danny_toolkit.omega_sovereign_core.lifecycle import safe_shutdown
            safe_shutdown(
                component_name="sovereign_engine",
                state_data=snapshot.to_dict(),
                do_exit=False,  # Engine beheert eigen exit
            )
            print(f"{Kleur.GROEN}  Swarm state veilig opgeslagen{Kleur.RESET}")
        except Exception as e:
            logger.error("Hand-off mislukt: %s", e)
            print(f"{Kleur.ROOD}  Hand-off MISLUKT: {e}{Kleur.RESET}")

        # ── Stop sweeper ──
        self._sweeper.stop()
        self._status = "offline"

        with self._lock:
            self._stats["shutdowns_executed"] += 1

        print(f"\n{Kleur.GROEN}  Sovereign Engine offline.{Kleur.RESET}")
        print(f"{Kleur.CYAAN}{'═' * 50}{Kleur.RESET}\n")

        return True

    # ══════════════════════════════════════════════════════════
    #  RUN
    # ══════════════════════════════════════════════════════════

    def start(self) -> None:
        """Start de engine en de ViolationSweeper."""
        self._ensure_backends()
        self._status = "online"
        self._sweeper.start()
        print(f"{Kleur.GROEN}[ENGINE] Sovereign Swarm Online. "
              f"Agents: {len(self._agents)}{Kleur.RESET}")

    def get_sweeper(self) -> ViolationSweeper:
        """Geeft de ViolationSweeper voor externe modules."""
        return self._sweeper

    # ── Stats ──

    def get_stats(self) -> Dict[str, Any]:
        """Haal engine statistieken op."""
        with self._lock:
            return {
                **self._stats,
                "status": self._status,
                "active_agents": len(self._agents),
                "agent_names": list(self._agents.keys()),
                "sweeper": self._sweeper.get_stats(),
            }

    def get_agent_health(self) -> Dict[str, dict]:
        """Haal health info op voor alle agents."""
        with self._lock:
            return dict(self._agent_health)


# ── Singleton ──

_engine_instance: Optional[SovereignEngine] = None
_engine_lock = threading.Lock()


def get_sovereign_engine() -> SovereignEngine:
    """Verkrijg de singleton SovereignEngine."""
    global _engine_instance
    if _engine_instance is None:
        with _engine_lock:
            if _engine_instance is None:
                _engine_instance = SovereignEngine()
    return _engine_instance

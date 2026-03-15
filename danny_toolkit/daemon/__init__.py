"""Digital Daemon — Het Levende Organisme van Omega Sovereign.

Subsystemen:
    Sensorium        — Zintuigen: events van 35+ apps
    LimbicSystem     — Emotioneel brein: data → emoties/moods
    Metabolisme      — Energie: consumptie/verbranding/balans
    CoherentieMonitor — CPU/GPU correlatie anomalie detectie
    DigitalDaemon    — Always-on symbiotische entiteit (finale vorm)
    HeartbeatDaemon  — Autonome achtergrond-daemon (lazy, zware deps)

Omega Sovereign integratie:
    HeartbeatDaemon.start()          — standalone met Rich Live terminal
    HeartbeatDaemon.start_headless() — als daemon thread in boot_sovereign()
"""

from __future__ import annotations

from danny_toolkit.daemon.sensorium import Sensorium, EventType, SensoryEvent
from danny_toolkit.daemon.limbic_system import LimbicSystem, Mood, EnergyState, AvatarForm
from danny_toolkit.daemon.metabolisme import Metabolisme, MetabolicState
from danny_toolkit.daemon.coherentie import CoherentieMonitor
from danny_toolkit.daemon.daemon_core import DigitalDaemon

__all__ = [
    # Zintuigen
    "Sensorium",
    "EventType",
    "SensoryEvent",
    # Emoties
    "LimbicSystem",
    "Mood",
    "EnergyState",
    "AvatarForm",
    # Energie
    "Metabolisme",
    "MetabolicState",
    # Hardware
    "CoherentieMonitor",
    # Core
    "DigitalDaemon",
    # Heartbeat (lazy)
    "HeartbeatDaemon",
]


def __getattr__(name: str) -> type:
    """Lazy import voor HeartbeatDaemon (zware deps: Rich, psutil)."""
    if name == "HeartbeatDaemon":
        try:
            from danny_toolkit.daemon.heartbeat import HeartbeatDaemon
        except ImportError:
            raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
        return HeartbeatDaemon
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

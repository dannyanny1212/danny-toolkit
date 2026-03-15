"""Digital Daemon — De Levende Interface.

Het Virtuele Huisdier als Always-On Symbiotische Entiteit.
"""

from __future__ import annotations

from danny_toolkit.daemon.sensorium import Sensorium
from danny_toolkit.daemon.limbic_system import LimbicSystem
from danny_toolkit.daemon.metabolisme import Metabolisme
from danny_toolkit.daemon.daemon_core import DigitalDaemon

__all__ = [
    "Sensorium",
    "LimbicSystem",
    "Metabolisme",
    "DigitalDaemon",
    "HeartbeatDaemon",
]

def __getattr__(name: str) -> type:
    """Lazy import voor HeartbeatDaemon (zware deps)."""
    if name == "HeartbeatDaemon":
        try:
            from danny_toolkit.daemon.heartbeat import HeartbeatDaemon
        except ImportError:
            raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
        return HeartbeatDaemon
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

"""
Digital Daemon - De Levende Interface.

Het Virtuele Huisdier als Always-On Symbiotische Entiteit.
"""

from __future__ import annotations

from .sensorium import Sensorium
from .limbic_system import LimbicSystem
from .metabolisme import Metabolisme
from .daemon_core import DigitalDaemon

def __getattr__(name):
    """Dynamic attribute accessor. 
Returns the specified attribute if it exists, otherwise raises an AttributeError. 
Currently supports:
  - HeartbeatDaemon: A daemon for handling heartbeats."""
    if name == "HeartbeatDaemon":
        from .heartbeat import HeartbeatDaemon
        return HeartbeatDaemon
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

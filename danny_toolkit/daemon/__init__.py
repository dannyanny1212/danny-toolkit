"""
Digital Daemon - De Levende Interface.

Het Virtuele Huisdier als Always-On Symbiotische Entiteit.
"""

from .sensorium import Sensorium
from .limbic_system import LimbicSystem
from .metabolisme import Metabolisme
from .daemon_core import DigitalDaemon

def __getattr__(name):
    if name == "HeartbeatDaemon":
        from .heartbeat import HeartbeatDaemon
        return HeartbeatDaemon
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

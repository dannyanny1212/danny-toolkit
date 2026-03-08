"""Cosmic Family Quests - Prototypes en Experimenten."""

from __future__ import annotations

from danny_toolkit.quests.core_protocol import CoreProtocol
from danny_toolkit.quests.daemon_protocol import DaemonProtocol
from danny_toolkit.quests.mind_protocol import MindProtocol
from danny_toolkit.quests.senses_protocol import SensesProtocol
from danny_toolkit.quests.body_protocol import BodyProtocol
from danny_toolkit.quests.brain_protocol import BrainProtocol
from danny_toolkit.quests.trinity_protocol import TrinityProtocol
from danny_toolkit.quests.bridge_protocol import BridgeProtocol
from danny_toolkit.quests.pulse_protocol import PulseProtocol
from danny_toolkit.quests.voice_protocol import VoiceProtocol
from danny_toolkit.quests.listener_protocol import ListenerProtocol
from danny_toolkit.quests.dialogue_protocol import DialogueProtocol
from danny_toolkit.quests.will_protocol import WillProtocol
from danny_toolkit.quests.memory_protocol import MemoryProtocol
import logging

logger = logging.getLogger(__name__)

__all__ = [
    "CoreProtocol",
    "DaemonProtocol",
    "MindProtocol",
    "SensesProtocol",
    "BodyProtocol",
    "BrainProtocol",
    "TrinityProtocol",
    "BridgeProtocol",
    "PulseProtocol",
    "VoiceProtocol",
    "ListenerProtocol",
    "DialogueProtocol",
    "WillProtocol",
    "MemoryProtocol",
]

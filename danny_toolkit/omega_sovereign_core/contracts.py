"""
OmegaSwarm Contracts — Immutable Dataclasses voor Agent Communicatie.
=====================================================================

SwarmPayload: Frozen dataclass voor inter-agent data. Onwijzigbaar.
SwarmEvent:   Telemetrie event voor realtime dashboard monitoring.
AgentState:   Enum voor agent lifecycle states.

Gebruik:
    from danny_toolkit.omega_sovereign_core.contracts import (
        SwarmPayload, SwarmEvent, AgentState,
    )
    payload = SwarmPayload(agent_name="Iolaax", task="code schrijven")
    event = SwarmEvent(agent_name="Iolaax", state=AgentState.RUNNING)

    # Immutable — gebruik replace() voor nieuwe versie:
    from dataclasses import replace
    new_payload = replace(payload, result="functie geschreven")
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class AgentState(Enum):
    """Lifecycle states van een Swarm agent."""
    IDLE = "idle"             # Wachtend op werk
    QUEUED = "queued"         # In de wachtrij
    RUNNING = "running"       # Bezig met verwerking
    SUCCESS = "success"       # Succesvol afgerond
    ERROR = "error"           # Fout opgetreden
    TIMEOUT = "timeout"       # Timeout bereikt
    BLOCKED = "blocked"       # Geblokkeerd door Governor/Gate
    CIRCUIT_OPEN = "circuit_open"  # Circuit breaker open


@dataclass(frozen=True)
class SwarmPayload:
    """Immutable payload voor inter-agent communicatie.

    Frozen: eenmaal aangemaakt, nooit gewijzigd.
    Gebruik dataclasses.replace() voor een nieuwe versie.

    Attributes:
        agent_name: Naam van de verantwoordelijke agent.
        task: De taak/prompt die verwerkt moet worden.
        result: Het resultaat na verwerking (None = onverwerkt).
        trace_id: Unieke trace ID voor request correlation.
        metadata: Extra context (bron, scores, flags).
        timestamp: Aanmaak timestamp (automatisch).
    """
    agent_name: str = ""
    task: str = ""
    result: Optional[str] = None
    trace_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass(frozen=True)
class SwarmEvent:
    """Telemetrie event voor realtime dashboard monitoring.

    Wordt gepusht naar een asyncio.Queue door BaseAgent._emit().
    Het dashboard leest deze events voor live status updates.

    Attributes:
        agent_name: Naam van de agent die het event genereert.
        state: Huidige AgentState.
        message: Optioneel context bericht.
        timestamp: Event timestamp (automatisch).
    """
    agent_name: str = ""
    state: AgentState = AgentState.IDLE
    message: str = ""
    timestamp: float = field(default_factory=time.time)

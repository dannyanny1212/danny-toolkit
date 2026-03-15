"""
OmegaSwarm Agent Blauwdruk — BaseAgent (ABC)
=============================================

De abstracte basisklasse voor elk lid van het Legioen.
Elke agent werkt autonoom en communiceert uitsluitend
via immutable payloads (SwarmPayload) en events (SwarmEvent).

Gebruik:
    class MijnAgent(BaseAgent):
        async def process(self, payload: SwarmPayload) -> SwarmPayload:
            await self._emit(AgentState.RUNNING, "Bezig...")
            # ... verwerk payload ...
            await self._emit(AgentState.SUCCESS, "Klaar")
            return replace(payload, agent_name=self.name, result="nieuw")
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from typing import Optional

from danny_toolkit.omega_sovereign_core.contracts import (
    SwarmPayload,
    SwarmEvent,
    AgentState,
)


class BaseAgent(ABC):
    """
    De Blauwdruk voor elk lid van het Legioen.

    Elke agent werkt autonoom en communiceert uitsluitend via
    immutable payloads en events. De telemetry_queue is optioneel:
    zonder queue is _emit() een stille no-op (backward compatible).

    Attributen:
        name: Unieke identificatie van de agent.
        telemetry_queue: Optionele asyncio.Queue voor realtime dashboard-events.
    """

    def __init__(
        self,
        name: str,
        telemetry_queue: Optional[asyncio.Queue] = None,
    ) -> None:
        self.name = name
        self.telemetry_queue = telemetry_queue

    async def _emit(
        self,
        state: AgentState,
        message: str = "",
    ) -> None:
        """
        Pusht een status-event naar de telemetrie-wachtrij.

        No-op als er geen queue is geconfigureerd — agents functioneren
        identiek met of zonder telemetrie (Zero Overhead Principle).

        Args:
            state: De nieuwe AgentState.
            message: Optioneel context-bericht.
        """
        if self.telemetry_queue is not None:
            event = SwarmEvent(
                agent_name=self.name,
                state=state,
                message=message,
            )
            await self.telemetry_queue.put(event)

    @abstractmethod
    async def process(self, payload: SwarmPayload) -> SwarmPayload:
        """
        De kern-executiemethode. Moet door sub-agents worden geimplementeerd.

        Retourneert ALTIJD een nieuwe (geevolueerde) SwarmPayload via replace().
        Het originele payload-object blijft ongewijzigd (frozen garantie).

        Args:
            payload: De immutable input-payload.

        Returns:
            Een nieuwe SwarmPayload met het verwerkte resultaat.
        """
        ...

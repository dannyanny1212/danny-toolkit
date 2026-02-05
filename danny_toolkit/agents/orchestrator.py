"""
Multi-Agent Orchestrator.
"""

import asyncio
from datetime import datetime
from .base import Agent


class Orchestrator:
    """
    Coordineert meerdere agents voor complexe taken.
    """

    def __init__(self):
        self.agents: dict[str, Agent] = {}
        self.taak_log: list[dict] = []

    def registreer(self, agent: Agent):
        """Registreer een agent."""
        self.agents[agent.naam] = agent
        print(f"   [OK] Agent '{agent.naam}' geregistreerd")

    async def delegeer(self, agent_naam: str, taak: str) -> str:
        """Delegeer een taak aan een specifieke agent."""
        agent = self.agents.get(agent_naam)
        if not agent:
            return f"Agent '{agent_naam}' niet gevonden"

        self.taak_log.append({
            "agent": agent_naam,
            "taak": taak,
            "start": datetime.now().isoformat()
        })

        result = await agent.run(taak)

        self.taak_log[-1]["eind"] = datetime.now().isoformat()
        self.taak_log[-1]["result"] = (
            result[:100] + "..." if len(result) > 100 else result
        )

        return result

    async def pipeline(self, taken: list[tuple[str, str]]) -> list[str]:
        """
        Voer taken sequentieel uit.

        Args:
            taken: List van (agent_naam, taak) tuples
        """
        resultaten = []

        for agent_naam, taak in taken:
            print(f"\n{'='*50}")
            print(f"[STAP] {agent_naam}")
            print(f"{'='*50}")

            result = await self.delegeer(agent_naam, taak)
            resultaten.append(result)

        return resultaten

    async def parallel(self, taken: list[tuple[str, str]]) -> list[str]:
        """
        Voer taken parallel uit.

        Args:
            taken: List van (agent_naam, taak) tuples
        """
        print(f"\n[PARALLEL] {len(taken)} taken starten...")

        coroutines = [
            self.delegeer(agent_naam, taak)
            for agent_naam, taak in taken
        ]

        resultaten = await asyncio.gather(*coroutines)
        return list(resultaten)

    def toon_log(self):
        """Toon de taak log."""
        print("\n[TAAK LOG]")
        for log in self.taak_log:
            print(f"   - {log['agent']}: {log['taak'][:40]}...")

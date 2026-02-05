"""
Tool system voor agents.
"""

import asyncio
from dataclasses import dataclass
from typing import Optional, Callable


@dataclass
class Tool:
    """Definitie van een tool die agents kunnen gebruiken."""
    naam: str
    beschrijving: str
    parameters: dict
    functie: Callable

    def to_anthropic_format(self) -> dict:
        """Convert naar Anthropic tool format."""
        return {
            "name": self.naam,
            "description": self.beschrijving,
            "input_schema": {
                "type": "object",
                "properties": self.parameters,
                "required": list(self.parameters.keys())
            }
        }


class ToolRegistry:
    """Beheert alle beschikbare tools."""

    def __init__(self):
        self.tools: dict[str, Tool] = {}

    def register(self, tool: Tool):
        """Registreer een tool."""
        self.tools[tool.naam] = tool

    def get(self, naam: str) -> Optional[Tool]:
        """Haal een tool op."""
        return self.tools.get(naam)

    def lijst(self) -> list[dict]:
        """Lijst alle tools in Anthropic format."""
        return [t.to_anthropic_format() for t in self.tools.values()]

    async def execute(self, naam: str, params: dict) -> str:
        """Voer een tool uit."""
        tool = self.tools.get(naam)
        if not tool:
            return f"Tool '{naam}' niet gevonden"

        try:
            result = tool.functie(**params)
            if asyncio.iscoroutine(result):
                result = await result
            return str(result)
        except Exception as e:
            return f"Tool error: {e}"

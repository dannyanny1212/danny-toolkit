"""
Base Agent class voor het agent framework.
"""

import os
import json
import asyncio
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional

from ..core.config import Config
from .tool import ToolRegistry


@dataclass
class AgentConfig:
    """Configuratie voor agents."""
    model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 2048
    temperature: float = 0.7


@dataclass
class AgentMessage:
    """Bericht in agent conversatie."""
    role: str  # "user", "assistant", "tool_result"
    content: str
    tool_use_id: Optional[str] = None


class Agent:
    """
    Productie-klare Agent met:
    - Tool gebruik
    - Geheugen
    - Async execution
    - Logging
    """

    def __init__(
        self,
        naam: str,
        systeem_prompt: str,
        tools: ToolRegistry = None,
        config: AgentConfig = None
    ):
        self.naam = naam
        self.systeem_prompt = systeem_prompt
        self.tools = tools or ToolRegistry()
        self.config = config or AgentConfig()

        import anthropic
        self.client = anthropic.Anthropic(
            api_key=os.environ.get("ANTHROPIC_API_KEY")
        )

        self.geheugen: list[dict] = []
        self.logs: list[str] = []

    def log(self, bericht: str):
        """Log een bericht."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] [{self.naam}] {bericht}"
        self.logs.append(log_entry)
        print(log_entry)

    async def run(self, taak: str, max_iteraties: int = 10) -> str:
        """
        Voer een taak uit met de Agentic Loop.

        Returns:
            Het finale antwoord van de agent.
        """
        self.log(f"Start taak: {taak[:50]}...")

        # Voeg taak toe aan geheugen
        self.geheugen.append({"role": "user", "content": taak})

        for i in range(max_iteraties):
            self.log(f"Iteratie {i+1}/{max_iteraties}")

            # Roep Claude aan
            response = self.client.messages.create(
                model=self.config.model,
                max_tokens=self.config.max_tokens,
                system=self.systeem_prompt,
                tools=self.tools.lijst() if self.tools.tools else None,
                messages=self.geheugen
            )

            # Verwerk response
            assistant_content = []
            tool_calls = []

            for block in response.content:
                if block.type == "text":
                    assistant_content.append({
                        "type": "text",
                        "text": block.text
                    })
                elif block.type == "tool_use":
                    tool_calls.append(block)
                    assistant_content.append({
                        "type": "tool_use",
                        "id": block.id,
                        "name": block.name,
                        "input": block.input
                    })

            # Voeg assistant response toe aan geheugen
            self.geheugen.append({
                "role": "assistant",
                "content": assistant_content
            })

            # Als er tool calls zijn, voer ze uit
            if tool_calls:
                tool_results = []

                for tool_call in tool_calls:
                    input_str = json.dumps(tool_call.input, ensure_ascii=False)
                    self.log(f"Tool: {tool_call.name}({input_str[:50]}...)")

                    result = await self.tools.execute(
                        tool_call.name,
                        tool_call.input
                    )

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_call.id,
                        "content": result
                    })

                # Voeg tool results toe aan geheugen
                self.geheugen.append({
                    "role": "user",
                    "content": tool_results
                })

                # Ga door naar volgende iteratie
                continue

            # Geen tool calls meer = taak compleet
            if response.stop_reason == "end_turn":
                final_text = ""
                for block in response.content:
                    if block.type == "text":
                        final_text += block.text

                self.log("Taak voltooid!")
                return final_text

        self.log("Max iteraties bereikt")
        return "Taak niet voltooid binnen max iteraties."

    def reset(self):
        """Reset agent geheugen."""
        self.geheugen = []
        self.logs = []

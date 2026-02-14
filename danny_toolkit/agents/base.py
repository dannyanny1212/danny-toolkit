"""
Base Agent class voor het agent framework.
Versie 5.1.1 - COSMIC_OMEGA_V5. Met multi-provider, memory system, reflection en meer!
"""

import os
import json
import asyncio
import time
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Callable, Any
from enum import Enum

from ..core.config import Config
from ..core.utils import kleur, Kleur
from .tool import ToolRegistry


class AgentProvider(Enum):
    """Beschikbare AI providers."""
    CLAUDE = "claude"
    GROQ = "groq"
    LOCAL = "local"


class AgentState(Enum):
    """Agent staten."""
    IDLE = "idle"
    THINKING = "thinking"
    EXECUTING = "executing"
    WAITING = "waiting"
    ERROR = "error"


@dataclass
class AgentConfig:
    """Configuratie voor agents."""
    model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 2048
    temperature: float = 0.7
    max_iteraties: int = 10
    timeout: float = 60.0
    retry_attempts: int = 3
    retry_delay: float = 1.0


@dataclass
class AgentMessage:
    """Bericht in agent conversatie."""
    role: str  # "user", "assistant", "tool_result"
    content: str
    tool_use_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    tokens: int = 0


@dataclass
class AgentMemory:
    """Geheugen structuur voor agents."""
    korte_termijn: list = field(default_factory=list)  # Huidige conversatie
    lange_termijn: list = field(default_factory=list)  # Belangrijke feiten
    vaardigheden: dict = field(default_factory=dict)   # Geleerde skills
    context: dict = field(default_factory=dict)        # Huidige context


@dataclass
class AgentStats:
    """Statistieken voor een agent."""
    totaal_taken: int = 0
    succesvolle_taken: int = 0
    gefaalde_taken: int = 0
    totaal_tokens: int = 0
    totaal_tijd_sec: float = 0.0
    tool_gebruik: dict = field(default_factory=dict)
    laatste_activiteit: Optional[datetime] = None


class Agent:
    """
    Productie-klare Agent met:
    - Multi-provider ondersteuning (Claude, Groq, Local)
    - Geavanceerd geheugen systeem
    - Tool gebruik
    - Performance tracking
    - Event hooks
    - State persistence
    - Reflection capabilities
    """

    def __init__(
        self,
        naam: str,
        systeem_prompt: str,
        tools: ToolRegistry = None,
        config: AgentConfig = None,
        personality: dict = None,
        persist: bool = False
    ):
        self.naam = naam
        self.systeem_prompt = systeem_prompt
        self.tools = tools or ToolRegistry()
        self.config = config or AgentConfig()
        self.personality = personality or {}
        self.persist = persist

        # Provider setup
        self.provider = None
        self.client = None
        self.model = None
        self._init_provider()

        # Memory en state
        self.memory = AgentMemory()
        self.stats = AgentStats()
        self.state = AgentState.IDLE
        self.logs: list[str] = []

        # Event hooks
        self.on_start: list[Callable] = []
        self.on_complete: list[Callable] = []
        self.on_error: list[Callable] = []
        self.on_tool_use: list[Callable] = []

        # Data persistence
        Config.ensure_dirs()
        self.data_dir = Config.DATA_DIR / "agents"
        self.data_dir.mkdir(exist_ok=True)
        self.state_file = self.data_dir / f"{naam.lower().replace(' ', '_')}_state.json"

        # Laad opgeslagen state indien persist=True
        if self.persist and self.state_file.exists():
            self._laad_state()

    def _init_provider(self):
        """Initialiseer de AI provider."""
        # TODO: Groq verwijderd — direct naar Claude

        # Probeer Claude
        if Config.has_anthropic_key():
            try:
                import anthropic
                self.client = anthropic.Anthropic(
                    api_key=Config.ANTHROPIC_API_KEY
                )
                self.provider = AgentProvider.CLAUDE
                self.model = self.config.model
                return
            except Exception:
                pass

        # Fallback: local mode (geen AI)
        self.provider = AgentProvider.LOCAL
        self.client = None
        self.model = "local"

    def _laad_state(self):
        """Laad opgeslagen agent state."""
        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.memory.lange_termijn = data.get("lange_termijn", [])
            self.memory.vaardigheden = data.get("vaardigheden", {})
            self.memory.context = data.get("context", {})

            stats = data.get("stats", {})
            self.stats.totaal_taken = stats.get("totaal_taken", 0)
            self.stats.succesvolle_taken = stats.get("succesvolle_taken", 0)
            self.stats.gefaalde_taken = stats.get("gefaalde_taken", 0)
            self.stats.totaal_tokens = stats.get("totaal_tokens", 0)
            self.stats.totaal_tijd_sec = stats.get("totaal_tijd_sec", 0.0)
            self.stats.tool_gebruik = stats.get("tool_gebruik", {})

            self.log(f"State geladen van {self.state_file.name}")
        except Exception as e:
            self.log(f"Kon state niet laden: {e}", Kleur.ROOD)

    def _sla_state_op(self):
        """Sla agent state op."""
        if not self.persist:
            return

        try:
            data = {
                "naam": self.naam,
                "lange_termijn": self.memory.lange_termijn[-50:],  # Max 50 items
                "vaardigheden": self.memory.vaardigheden,
                "context": self.memory.context,
                "stats": {
                    "totaal_taken": self.stats.totaal_taken,
                    "succesvolle_taken": self.stats.succesvolle_taken,
                    "gefaalde_taken": self.stats.gefaalde_taken,
                    "totaal_tokens": self.stats.totaal_tokens,
                    "totaal_tijd_sec": self.stats.totaal_tijd_sec,
                    "tool_gebruik": self.stats.tool_gebruik,
                },
                "opgeslagen": datetime.now().isoformat(),
            }

            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.log(f"Kon state niet opslaan: {e}", Kleur.ROOD)

    def log(self, bericht: str, kleur_naam: str = Kleur.CYAAN):
        """Log een bericht met kleur."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] [{self.naam}] {bericht}"
        self.logs.append(log_entry)
        print(kleur(log_entry, kleur_naam))

    def _trigger_hook(self, hook_list: list, *args):
        """Trigger event hooks."""
        for hook in hook_list:
            try:
                hook(self, *args)
            except Exception as e:
                self.log(f"Hook error: {e}", Kleur.ROOD)

    def add_hook(self, event: str, callback: Callable):
        """Voeg een event hook toe."""
        hooks = {
            "start": self.on_start,
            "complete": self.on_complete,
            "error": self.on_error,
            "tool_use": self.on_tool_use,
        }
        if event in hooks:
            hooks[event].append(callback)

    def remember(self, feit: str, categorie: str = "algemeen"):
        """Voeg iets toe aan lange-termijn geheugen."""
        self.memory.lange_termijn.append({
            "feit": feit,
            "categorie": categorie,
            "timestamp": datetime.now().isoformat(),
        })
        self.log(f"Onthouden: {feit[:50]}...")

    def recall(self, categorie: str = None, limit: int = 10) -> list:
        """Haal feiten op uit lange-termijn geheugen."""
        feiten = self.memory.lange_termijn

        if categorie:
            feiten = [f for f in feiten if f.get("categorie") == categorie]

        return feiten[-limit:]

    def learn_skill(self, skill_naam: str, beschrijving: str,
                    success_rate: float = 0.0):
        """Leer een nieuwe vaardigheid."""
        self.memory.vaardigheden[skill_naam] = {
            "beschrijving": beschrijving,
            "geleerd": datetime.now().isoformat(),
            "success_rate": success_rate,
            "gebruik_count": 0,
        }
        self.log(f"Vaardigheid geleerd: {skill_naam}")

    def _build_system_prompt(self) -> str:
        """Bouw de volledige system prompt."""
        prompt = self.systeem_prompt

        # Voeg personality toe
        if self.personality:
            prompt += "\n\nJe persoonlijkheid:\n"
            for key, value in self.personality.items():
                prompt += f"- {key}: {value}\n"

        # Voeg relevante lange-termijn geheugen toe
        if self.memory.lange_termijn:
            recente = self.memory.lange_termijn[-5:]
            prompt += "\n\nBelangrijke context die je onthoudt:\n"
            for item in recente:
                prompt += f"- {item['feit']}\n"

        # Voeg vaardigheden toe
        if self.memory.vaardigheden:
            prompt += "\n\nJe beschikbare vaardigheden:\n"
            for naam, info in self.memory.vaardigheden.items():
                prompt += f"- {naam}: {info['beschrijving']}\n"

        return prompt

    async def _call_api(self, messages: list) -> dict:
        """Roep de AI API aan met retry logic."""
        system_prompt = self._build_system_prompt()

        for attempt in range(self.config.retry_attempts):
            try:
                if self.provider == AgentProvider.CLAUDE:
                    response = self.client.messages.create(
                        model=self.model,
                        max_tokens=self.config.max_tokens,
                        system=system_prompt,
                        tools=self.tools.lijst() if self.tools.tools else None,
                        messages=messages
                    )
                    return {
                        "content": response.content,
                        "stop_reason": response.stop_reason,
                        "usage": {
                            "input": response.usage.input_tokens,
                            "output": response.usage.output_tokens,
                        }
                    }

                # TODO: Groq provider verwijderd

                else:
                    # Local fallback
                    return {
                        "content": [{
                            "type": "text",
                            "text": "[LOCAL MODE] Geen AI provider beschikbaar. "
                                   "Stel ANTHROPIC_API_KEY in."
                        }],
                        "stop_reason": "end_turn",
                        "usage": {"input": 0, "output": 0}
                    }

            except Exception as e:
                self.log(f"API error (poging {attempt + 1}): {e}", Kleur.GEEL)
                if attempt < self.config.retry_attempts - 1:
                    await asyncio.sleep(self.config.retry_delay * (attempt + 1))
                else:
                    raise

    async def run(self, taak: str, max_iteraties: int = None) -> str:
        """
        Voer een taak uit met de Agentic Loop.

        Returns:
            Het finale antwoord van de agent.
        """
        max_iteraties = max_iteraties or self.config.max_iteraties
        start_time = time.time()

        self.state = AgentState.THINKING
        self.stats.totaal_taken += 1
        self.stats.laatste_activiteit = datetime.now()

        self.log(f"Start taak: {taak[:50]}...", Kleur.CYAAN)
        self._trigger_hook(self.on_start, taak)

        # Voeg taak toe aan geheugen
        self.memory.korte_termijn.append({"role": "user", "content": taak})

        try:
            for i in range(max_iteraties):
                self.log(f"Iteratie {i+1}/{max_iteraties}", Kleur.GEEL)

                # Roep AI aan
                response = await self._call_api(self.memory.korte_termijn)

                # Track tokens
                usage = response.get("usage", {})
                tokens = usage.get("input", 0) + usage.get("output", 0)
                self.stats.totaal_tokens += tokens

                # Verwerk response
                assistant_content = []
                tool_calls = []

                for block in response["content"]:
                    if isinstance(block, dict):
                        if block.get("type") == "text":
                            assistant_content.append(block)
                        elif block.get("type") == "tool_use":
                            tool_calls.append(block)
                            assistant_content.append(block)
                    else:
                        # Anthropic object
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
                self.memory.korte_termijn.append({
                    "role": "assistant",
                    "content": assistant_content
                })

                # Als er tool calls zijn, voer ze uit
                if tool_calls and self.provider == AgentProvider.CLAUDE:
                    self.state = AgentState.EXECUTING
                    tool_results = []

                    for tool_call in tool_calls:
                        # Handle both dict and object
                        if isinstance(tool_call, dict):
                            tool_name = tool_call["name"]
                            tool_input = tool_call["input"]
                            tool_id = tool_call["id"]
                        else:
                            tool_name = tool_call.name
                            tool_input = tool_call.input
                            tool_id = tool_call.id

                        input_str = json.dumps(tool_input, ensure_ascii=False)
                        self.log(f"Tool: {tool_name}({input_str[:50]}...)", Kleur.MAGENTA)

                        # Track tool gebruik
                        if tool_name not in self.stats.tool_gebruik:
                            self.stats.tool_gebruik[tool_name] = 0
                        self.stats.tool_gebruik[tool_name] += 1

                        self._trigger_hook(self.on_tool_use, tool_name, tool_input)

                        result = await self.tools.execute(tool_name, tool_input)

                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_id,
                            "content": result
                        })

                    # Voeg tool results toe aan geheugen
                    self.memory.korte_termijn.append({
                        "role": "user",
                        "content": tool_results
                    })

                    self.state = AgentState.THINKING
                    continue

                # Geen tool calls meer = taak compleet
                if response.get("stop_reason") == "end_turn":
                    final_text = ""
                    for block in response["content"]:
                        if isinstance(block, dict):
                            if block.get("type") == "text":
                                final_text += block.get("text", "")
                        elif block.type == "text":
                            final_text += block.text

                    # Success!
                    elapsed = time.time() - start_time
                    self.stats.succesvolle_taken += 1
                    self.stats.totaal_tijd_sec += elapsed
                    self.state = AgentState.IDLE

                    self.log(f"Taak voltooid in {elapsed:.2f}s!", Kleur.GROEN)
                    self._trigger_hook(self.on_complete, final_text)
                    self._sla_state_op()

                    return final_text

            # Max iteraties bereikt
            self.log("Max iteraties bereikt", Kleur.ROOD)
            self.stats.gefaalde_taken += 1
            self.state = AgentState.IDLE
            self._sla_state_op()
            return "Taak niet voltooid binnen max iteraties."

        except Exception as e:
            self.state = AgentState.ERROR
            self.stats.gefaalde_taken += 1
            self.log(f"Error: {e}", Kleur.ROOD)
            self._trigger_hook(self.on_error, e)
            self._sla_state_op()
            raise

    async def reflect(self, vraag: str = None) -> str:
        """
        Laat de agent reflecteren op zijn acties.

        Args:
            vraag: Optionele vraag om over te reflecteren
        """
        self.log("Reflecteren...", Kleur.MAGENTA)

        reflection_prompt = f"""Reflecteer op je recente acties en ervaringen.

Je statistieken:
- Totaal taken: {self.stats.totaal_taken}
- Succesvol: {self.stats.succesvolle_taken}
- Gefaald: {self.stats.gefaalde_taken}
- Tokens gebruikt: {self.stats.totaal_tokens}

Je recente geheugen bevat {len(self.memory.korte_termijn)} berichten.
Je hebt {len(self.memory.lange_termijn)} feiten onthouden.
Je beheerst {len(self.memory.vaardigheden)} vaardigheden.

{"Vraag: " + vraag if vraag else "Wat heb je geleerd? Wat zou je anders doen?"}

Geef een korte, inzichtelijke reflectie."""

        # Tijdelijk nieuw geheugen voor reflectie
        temp_memory = self.memory.korte_termijn
        self.memory.korte_termijn = [{"role": "user", "content": reflection_prompt}]

        try:
            response = await self._call_api(self.memory.korte_termijn)
            reflection = ""
            for block in response["content"]:
                if isinstance(block, dict) and block.get("type") == "text":
                    reflection += block.get("text", "")
                elif hasattr(block, "type") and block.type == "text":
                    reflection += block.text

            return reflection
        finally:
            self.memory.korte_termijn = temp_memory

    def reset(self):
        """Reset agent geheugen."""
        self.memory.korte_termijn = []
        self.logs = []
        self.state = AgentState.IDLE
        self.log("Geheugen gereset", Kleur.GEEL)

    def reset_all(self):
        """Reset alles inclusief lange-termijn geheugen."""
        self.memory = AgentMemory()
        self.stats = AgentStats()
        self.logs = []
        self.state = AgentState.IDLE

        if self.state_file.exists():
            self.state_file.unlink()

        self.log("Volledig gereset", Kleur.GEEL)

    def toon_status(self):
        """Toon agent status."""
        print(kleur(f"\n{'='*50}", Kleur.CYAAN))
        print(kleur(f"AGENT: {self.naam}", Kleur.CYAAN))
        print(kleur("=" * 50, Kleur.CYAAN))
        print(f"  Provider:     {self.provider.value} ({self.model})")
        print(f"  State:        {self.state.value}")
        print(f"  Geheugen:     {len(self.memory.korte_termijn)} berichten")
        print(f"  Lang-termijn: {len(self.memory.lange_termijn)} feiten")
        print(f"  Vaardigheden: {len(self.memory.vaardigheden)}")
        print(f"  Tools:        {len(self.tools.tools)}")
        print(kleur("\nStatistieken:", Kleur.GEEL))
        print(f"  Taken:        {self.stats.totaal_taken} "
              f"({self.stats.succesvolle_taken} ok, "
              f"{self.stats.gefaalde_taken} failed)")
        print(f"  Tokens:       {self.stats.totaal_tokens}")
        print(f"  Tijd:         {self.stats.totaal_tijd_sec:.1f}s totaal")
        if self.stats.tool_gebruik:
            print(kleur("\nTool gebruik:", Kleur.GEEL))
            for tool, count in self.stats.tool_gebruik.items():
                print(f"  {tool}: {count}x")

    def export_logs(self) -> str:
        """Exporteer logs als string."""
        return "\n".join(self.logs)

    def get_summary(self) -> dict:
        """Krijg een samenvatting van de agent."""
        return {
            "naam": self.naam,
            "provider": self.provider.value,
            "model": self.model,
            "state": self.state.value,
            "stats": {
                "taken": self.stats.totaal_taken,
                "succesvol": self.stats.succesvolle_taken,
                "gefaald": self.stats.gefaalde_taken,
                "tokens": self.stats.totaal_tokens,
            },
            "memory": {
                "korte_termijn": len(self.memory.korte_termijn),
                "lange_termijn": len(self.memory.lange_termijn),
                "vaardigheden": list(self.memory.vaardigheden.keys()),
            },
            "tools": list(self.tools.tools.keys()) if self.tools.tools else [],
        }

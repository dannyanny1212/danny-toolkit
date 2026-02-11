"""
Tool system voor agents.
Versie 2.0 - Met categorieën, permissions, caching, metrics en meer!
"""

import asyncio
import json
import time
import hashlib
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Optional, Callable, Any, Union
from enum import Enum
from pathlib import Path

from ..core.config import Config
from ..core.utils import kleur, Kleur


class ToolCategory(Enum):
    """Categorieën voor tools."""
    ALGEMEEN = "algemeen"
    DATA = "data"
    BESTAND = "bestand"
    NETWERK = "netwerk"
    BEREKENING = "berekening"
    TEKST = "tekst"
    SYSTEEM = "systeem"
    AI = "ai"
    DATABASE = "database"
    CUSTOM = "custom"


class ToolPermission(Enum):
    """Permissie niveaus voor tools."""
    READ = "read"           # Alleen lezen
    WRITE = "write"         # Mag schrijven
    EXECUTE = "execute"     # Mag uitvoeren
    NETWORK = "network"     # Mag netwerk gebruiken
    DANGEROUS = "dangerous" # Gevaarlijke operaties


class ToolStatus(Enum):
    """Status van een tool."""
    ACTIVE = "active"
    DISABLED = "disabled"
    DEPRECATED = "deprecated"
    EXPERIMENTAL = "experimental"


@dataclass
class ToolResult:
    """Gestructureerd resultaat van een tool uitvoering."""
    success: bool
    data: Any
    error: Optional[str] = None
    execution_time: float = 0.0
    cached: bool = False
    timestamp: datetime = field(default_factory=datetime.now)

    def __str__(self) -> str:
        if self.success:
            return str(self.data)
        return f"Error: {self.error}"

    def to_dict(self) -> dict:
        """Converteer naar dictionary."""
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "execution_time": self.execution_time,
            "cached": self.cached,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class ToolMetrics:
    """Performance metrics voor een tool."""
    totaal_calls: int = 0
    succesvolle_calls: int = 0
    gefaalde_calls: int = 0
    totaal_tijd: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0
    laatste_call: Optional[datetime] = None
    snelste_call: Optional[float] = None
    langzaamste_call: Optional[float] = None

    def registreer_call(self, execution_time: float, success: bool, cached: bool):
        """Registreer een tool call."""
        self.totaal_calls += 1
        self.laatste_call = datetime.now()

        if success:
            self.succesvolle_calls += 1
        else:
            self.gefaalde_calls += 1

        if cached:
            self.cache_hits += 1
        else:
            self.cache_misses += 1
            self.totaal_tijd += execution_time

            if self.snelste_call is None or execution_time < self.snelste_call:
                self.snelste_call = execution_time
            if self.langzaamste_call is None or execution_time > self.langzaamste_call:
                self.langzaamste_call = execution_time

    @property
    def gemiddelde_tijd(self) -> float:
        """Bereken gemiddelde execution time."""
        non_cached = self.totaal_calls - self.cache_hits
        if non_cached == 0:
            return 0.0
        return self.totaal_tijd / non_cached

    @property
    def success_rate(self) -> float:
        """Bereken success rate."""
        if self.totaal_calls == 0:
            return 0.0
        return self.succesvolle_calls / self.totaal_calls

    @property
    def cache_hit_rate(self) -> float:
        """Bereken cache hit rate."""
        if self.totaal_calls == 0:
            return 0.0
        return self.cache_hits / self.totaal_calls

    def to_dict(self) -> dict:
        """Converteer naar dictionary."""
        return {
            "totaal_calls": self.totaal_calls,
            "succesvolle_calls": self.succesvolle_calls,
            "gefaalde_calls": self.gefaalde_calls,
            "success_rate": f"{self.success_rate:.1%}",
            "gemiddelde_tijd": f"{self.gemiddelde_tijd:.3f}s",
            "snelste_call": f"{self.snelste_call:.3f}s" if self.snelste_call else "N/A",
            "langzaamste_call": f"{self.langzaamste_call:.3f}s" if self.langzaamste_call else "N/A",
            "cache_hit_rate": f"{self.cache_hit_rate:.1%}",
        }


class ToolCache:
    """Cache systeem voor tool resultaten."""

    def __init__(self, max_size: int = 100, default_ttl: int = 300):
        self.cache: dict[str, dict] = {}
        self.max_size = max_size
        self.default_ttl = default_ttl  # seconds

    def _maak_key(self, tool_naam: str, params: dict) -> str:
        """Maak een cache key van tool naam en parameters."""
        param_str = json.dumps(params, sort_keys=True, default=str)
        hash_input = f"{tool_naam}:{param_str}"
        return hashlib.md5(hash_input.encode()).hexdigest()

    def get(self, tool_naam: str, params: dict) -> Optional[Any]:
        """Haal resultaat uit cache."""
        key = self._maak_key(tool_naam, params)

        if key not in self.cache:
            return None

        entry = self.cache[key]
        if datetime.now() > entry["expires"]:
            del self.cache[key]
            return None

        return entry["data"]

    def set(self, tool_naam: str, params: dict, data: Any, ttl: int = None):
        """Sla resultaat op in cache."""
        # Verwijder oudste entries als cache vol is
        while len(self.cache) >= self.max_size:
            oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k]["created"])
            del self.cache[oldest_key]

        key = self._maak_key(tool_naam, params)
        ttl = ttl or self.default_ttl

        self.cache[key] = {
            "data": data,
            "created": datetime.now(),
            "expires": datetime.now() + timedelta(seconds=ttl),
        }

    def invalidate(self, tool_naam: str = None):
        """Invalideer cache entries."""
        if tool_naam is None:
            self.cache.clear()
        else:
            keys_to_delete = [
                k for k in self.cache.keys()
                if k.startswith(hashlib.md5(f"{tool_naam}:".encode()).hexdigest()[:8])
            ]
            for key in keys_to_delete:
                del self.cache[key]

    def stats(self) -> dict:
        """Geef cache statistieken."""
        now = datetime.now()
        valid_entries = sum(1 for e in self.cache.values() if now < e["expires"])

        return {
            "totaal_entries": len(self.cache),
            "valid_entries": valid_entries,
            "expired_entries": len(self.cache) - valid_entries,
            "max_size": self.max_size,
        }


@dataclass
class ToolHistoryEntry:
    """Een entry in de tool history."""
    tool_naam: str
    parameters: dict
    result: ToolResult
    agent_naam: Optional[str] = None
    metadata: dict = field(default_factory=dict)
    timestamp: datetime = field(
        default_factory=datetime.now
    )

    def to_dict(self) -> dict:
        """Converteer naar dictionary."""
        return {
            "tool": self.tool_naam,
            "parameters": self.parameters,
            "success": self.result.success,
            "execution_time":
                self.result.execution_time,
            "cached": self.result.cached,
            "agent": self.agent_naam,
            "metadata": self.metadata,
            "timestamp":
                self.timestamp.isoformat(),
        }


class ToolHistory:
    """Bijhouden van tool gebruik geschiedenis."""

    def __init__(self, max_entries: int = 1000):
        self.entries: list[ToolHistoryEntry] = []
        self.max_entries = max_entries

    def add(self, entry: ToolHistoryEntry):
        """Voeg entry toe aan history."""
        self.entries.append(entry)

        # Trim als te groot
        if len(self.entries) > self.max_entries:
            self.entries = self.entries[-self.max_entries:]

    def get_recent(self, count: int = 10) -> list[ToolHistoryEntry]:
        """Haal recente entries op."""
        return list(reversed(self.entries[-count:]))

    def get_by_tool(self, tool_naam: str, count: int = 10) -> list[ToolHistoryEntry]:
        """Haal entries op voor specifieke tool."""
        tool_entries = [e for e in self.entries if e.tool_naam == tool_naam]
        return list(reversed(tool_entries[-count:]))

    def get_by_agent(self, agent_naam: str, count: int = 10) -> list[ToolHistoryEntry]:
        """Haal entries op voor specifieke agent."""
        agent_entries = [e for e in self.entries if e.agent_naam == agent_naam]
        return list(reversed(agent_entries[-count:]))

    def get_failures(self, count: int = 10) -> list[ToolHistoryEntry]:
        """Haal gefaalde calls op."""
        failures = [e for e in self.entries if not e.result.success]
        return list(reversed(failures[-count:]))

    def get_repair_tagged(self, count=100):
        """Haal repair-tagged entries op."""
        tagged = [
            e for e in self.entries
            if e.metadata.get("repair_triggered")
        ]
        return list(reversed(tagged[-count:]))

    def repair_stats(self):
        """Statistieken over repair-tagged calls."""
        tagged = [
            e for e in self.entries
            if e.metadata.get("repair_triggered")
        ]
        if not tagged:
            return {
                "totaal": 0, "geslaagd": 0,
                "gefaald": 0,
            }
        geslaagd = sum(
            1 for e in tagged if e.result.success
        )
        return {
            "totaal": len(tagged),
            "geslaagd": geslaagd,
            "gefaald": len(tagged) - geslaagd,
        }

    def stats(self) -> dict:
        """Geef history statistieken."""
        if not self.entries:
            return {"totaal": 0}

        successes = sum(1 for e in self.entries if e.result.success)
        tools_used = len(set(e.tool_naam for e in self.entries))

        return {
            "totaal": len(self.entries),
            "successes": successes,
            "failures": len(self.entries) - successes,
            "unique_tools": tools_used,
        }

    def clear(self):
        """Wis history."""
        self.entries.clear()


class ToolValidator:
    """Validatie van tool parameters."""

    # Ondersteunde types
    TYPES = {
        "string": str,
        "integer": int,
        "number": (int, float),
        "boolean": bool,
        "array": list,
        "object": dict,
    }

    @classmethod
    def validate(cls, parameters: dict, schema: dict) -> tuple[bool, Optional[str]]:
        """
        Valideer parameters tegen een schema.

        Returns:
            Tuple van (is_valid, error_message)
        """
        properties = schema.get("properties", {})
        required = schema.get("required", [])

        # Check required parameters
        for param in required:
            if param not in parameters:
                return False, f"Verplichte parameter '{param}' ontbreekt"

        # Validate each parameter
        for param_name, param_value in parameters.items():
            if param_name not in properties:
                continue  # Sta extra parameters toe

            param_schema = properties[param_name]
            param_type = param_schema.get("type")

            # Type check
            if param_type and param_type in cls.TYPES:
                expected_type = cls.TYPES[param_type]
                if not isinstance(param_value, expected_type):
                    return False, f"Parameter '{param_name}' moet type '{param_type}' zijn"

            # Enum check
            if "enum" in param_schema:
                if param_value not in param_schema["enum"]:
                    return False, f"Parameter '{param_name}' moet een van {param_schema['enum']} zijn"

            # Min/max voor numbers
            if param_type in ("integer", "number"):
                if "minimum" in param_schema and param_value < param_schema["minimum"]:
                    return False, f"Parameter '{param_name}' moet >= {param_schema['minimum']} zijn"
                if "maximum" in param_schema and param_value > param_schema["maximum"]:
                    return False, f"Parameter '{param_name}' moet <= {param_schema['maximum']} zijn"

            # Min/max length voor strings
            if param_type == "string":
                if "minLength" in param_schema and len(param_value) < param_schema["minLength"]:
                    return False, f"Parameter '{param_name}' moet minimaal {param_schema['minLength']} tekens zijn"
                if "maxLength" in param_schema and len(param_value) > param_schema["maxLength"]:
                    return False, f"Parameter '{param_name}' mag maximaal {param_schema['maxLength']} tekens zijn"
                if "pattern" in param_schema:
                    import re
                    if not re.match(param_schema["pattern"], param_value):
                        return False, f"Parameter '{param_name}' voldoet niet aan patroon"

        return True, None


@dataclass
class Tool:
    """Definitie van een tool die agents kunnen gebruiken."""
    naam: str
    beschrijving: str
    parameters: dict
    functie: Callable
    categorie: ToolCategory = ToolCategory.ALGEMEEN
    permissions: list[ToolPermission] = field(default_factory=list)
    status: ToolStatus = ToolStatus.ACTIVE
    aliases: list[str] = field(default_factory=list)
    cacheable: bool = False
    cache_ttl: int = 300
    timeout: float = 30.0
    retry_count: int = 0
    version: str = "1.0"
    author: str = ""
    help_text: str = ""
    examples: list[dict] = field(default_factory=list)

    # Hooks
    pre_execute: Optional[Callable] = None
    post_execute: Optional[Callable] = None

    def __post_init__(self):
        """Initialisatie na dataclass creatie."""
        if not self.permissions:
            self.permissions = [ToolPermission.READ]
        if not self.help_text:
            self.help_text = self.beschrijving

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

    def to_dict(self) -> dict:
        """Converteer naar dictionary."""
        return {
            "naam": self.naam,
            "beschrijving": self.beschrijving,
            "categorie": self.categorie.value,
            "permissions": [p.value for p in self.permissions],
            "status": self.status.value,
            "aliases": self.aliases,
            "cacheable": self.cacheable,
            "version": self.version,
        }

    def get_help(self) -> str:
        """Genereer help tekst voor de tool."""
        help_str = f"\n{kleur('Tool:', 'cyaan')} {self.naam} (v{self.version})\n"
        help_str += f"{kleur('Categorie:', 'grijs')} {self.categorie.value}\n"
        help_str += f"{kleur('Status:', 'grijs')} {self.status.value}\n"
        help_str += f"\n{kleur('Beschrijving:', 'geel')}\n  {self.help_text}\n"

        if self.aliases:
            help_str += f"\n{kleur('Aliases:', 'grijs')} {', '.join(self.aliases)}\n"

        help_str += f"\n{kleur('Parameters:', 'geel')}\n"
        for param_name, param_info in self.parameters.items():
            param_type = param_info.get("type", "any")
            param_desc = param_info.get("description", "")
            help_str += f"  - {param_name} ({param_type}): {param_desc}\n"

        if self.examples:
            help_str += f"\n{kleur('Voorbeelden:', 'geel')}\n"
            for example in self.examples:
                help_str += f"  {example.get('beschrijving', '')}\n"
                help_str += f"    Input: {example.get('input', {})}\n"

        return help_str


class ToolRegistry:
    """Beheert alle beschikbare tools met uitgebreide features."""

    def __init__(self, enable_cache: bool = True, enable_history: bool = True):
        self.tools: dict[str, Tool] = {}
        self.aliases: dict[str, str] = {}
        self.metrics: dict[str, ToolMetrics] = {}

        # Cache
        self.cache_enabled = enable_cache
        self.cache = ToolCache() if enable_cache else None

        # History
        self.history_enabled = enable_history
        self.history = ToolHistory() if enable_history else None

        # Event hooks
        self.on_execute: list[Callable] = []
        self.on_success: list[Callable] = []
        self.on_error: list[Callable] = []

        # Data persistence
        Config.ensure_dirs()
        self.data_dir = Config.DATA_DIR / "tools"
        self.data_dir.mkdir(exist_ok=True)

    def register(self, tool: Tool):
        """Registreer een tool."""
        self.tools[tool.naam] = tool
        self.metrics[tool.naam] = ToolMetrics()

        # Registreer aliases
        for alias in tool.aliases:
            self.aliases[alias] = tool.naam

        self._log(f"Tool geregistreerd: {tool.naam}")

    def unregister(self, naam: str) -> bool:
        """Verwijder een tool."""
        if naam not in self.tools:
            return False

        tool = self.tools[naam]

        # Verwijder aliases
        for alias in tool.aliases:
            if alias in self.aliases:
                del self.aliases[alias]

        del self.tools[naam]
        if naam in self.metrics:
            del self.metrics[naam]

        self._log(f"Tool verwijderd: {naam}")
        return True

    def get(self, naam: str) -> Optional[Tool]:
        """Haal een tool op (ook via alias)."""
        # Check directe naam
        if naam in self.tools:
            return self.tools[naam]

        # Check alias
        if naam in self.aliases:
            return self.tools.get(self.aliases[naam])

        return None

    def lijst(self) -> list[dict]:
        """Lijst alle tools in Anthropic format."""
        return [
            t.to_anthropic_format()
            for t in self.tools.values()
            if t.status == ToolStatus.ACTIVE
        ]

    def lijst_per_categorie(self) -> dict[str, list[Tool]]:
        """Lijst tools gegroepeerd per categorie."""
        result: dict[str, list[Tool]] = {}

        for tool in self.tools.values():
            cat = tool.categorie.value
            if cat not in result:
                result[cat] = []
            result[cat].append(tool)

        return result

    def zoek(self, query: str) -> list[Tool]:
        """Zoek tools op naam of beschrijving."""
        query_lower = query.lower()
        results = []

        for tool in self.tools.values():
            if (query_lower in tool.naam.lower() or
                query_lower in tool.beschrijving.lower() or
                any(query_lower in alias.lower() for alias in tool.aliases)):
                results.append(tool)

        return results

    async def execute(
        self,
        naam: str,
        params: dict,
        agent_naam: str = None,
        skip_cache: bool = False,
        skip_validation: bool = False,
        metadata: dict = None
    ) -> Union[str, ToolResult]:
        """
        Voer een tool uit met alle features.

        Args:
            naam: Tool naam of alias
            params: Parameters voor de tool
            agent_naam: Naam van de aanroepende agent
            skip_cache: Skip cache lookup
            skip_validation: Skip parameter validatie

        Returns:
            ToolResult of string (voor backwards compatibility)
        """
        start_time = time.time()

        # Resolve alias
        tool_naam = self.aliases.get(naam, naam)
        tool = self.tools.get(tool_naam)

        if not tool:
            error_result = ToolResult(
                success=False,
                data=None,
                error=f"Tool '{naam}' niet gevonden"
            )
            return str(error_result)

        # Check status
        if tool.status == ToolStatus.DISABLED:
            return f"Tool '{naam}' is uitgeschakeld"
        if tool.status == ToolStatus.DEPRECATED:
            self._log(f"Waarschuwing: Tool '{naam}' is deprecated", Kleur.GEEL)

        # Trigger on_execute hooks
        self._trigger_hooks(self.on_execute, tool, params)

        # Parameter validatie
        if not skip_validation:
            schema = {
                "type": "object",
                "properties": tool.parameters,
                "required": list(tool.parameters.keys())
            }
            is_valid, error_msg = ToolValidator.validate(params, schema)
            if not is_valid:
                error_result = ToolResult(
                    success=False,
                    data=None,
                    error=f"Validatie error: {error_msg}"
                )
                self._record_execution(tool_naam, params, error_result, agent_naam, metadata)
                return str(error_result)

        # Check cache
        cached = False
        if self.cache_enabled and tool.cacheable and not skip_cache:
            cached_result = self.cache.get(tool_naam, params)
            if cached_result is not None:
                cached = True
                result = ToolResult(
                    success=True,
                    data=cached_result,
                    cached=True,
                    execution_time=time.time() - start_time
                )
                self._record_execution(tool_naam, params, result, agent_naam, metadata)
                return str(result)

        # Pre-execute hook
        if tool.pre_execute:
            try:
                tool.pre_execute(tool, params)
            except Exception as e:
                self._log(f"Pre-execute hook error: {e}", Kleur.ROOD)

        # Execute met retry
        last_error = None
        for attempt in range(max(1, tool.retry_count + 1)):
            try:
                # Execute functie
                func_result = tool.functie(**params)

                # Await als het een coroutine is
                if asyncio.iscoroutine(func_result):
                    func_result = await asyncio.wait_for(
                        func_result,
                        timeout=tool.timeout
                    )

                execution_time = time.time() - start_time

                result = ToolResult(
                    success=True,
                    data=func_result,
                    execution_time=execution_time,
                    cached=False
                )

                # Cache resultaat
                if self.cache_enabled and tool.cacheable:
                    self.cache.set(tool_naam, params, func_result, tool.cache_ttl)

                # Post-execute hook
                if tool.post_execute:
                    try:
                        tool.post_execute(tool, params, result)
                    except Exception as e:
                        self._log(f"Post-execute hook error: {e}", Kleur.ROOD)

                # Trigger success hooks
                self._trigger_hooks(self.on_success, tool, params, result)

                self._record_execution(tool_naam, params, result, agent_naam, metadata)
                return str(result)

            except asyncio.TimeoutError:
                last_error = f"Timeout na {tool.timeout}s"
                self._log(f"Tool '{naam}' timeout (poging {attempt + 1})", Kleur.GEEL)

            except Exception as e:
                last_error = str(e)
                self._log(f"Tool '{naam}' error (poging {attempt + 1}): {e}", Kleur.ROOD)

            if attempt < tool.retry_count:
                await asyncio.sleep(0.5 * (attempt + 1))

        # Alle pogingen gefaald
        execution_time = time.time() - start_time
        error_result = ToolResult(
            success=False,
            data=None,
            error=last_error,
            execution_time=execution_time
        )

        # Trigger error hooks
        self._trigger_hooks(self.on_error, tool, params, error_result)

        self._record_execution(tool_naam, params, error_result, agent_naam, metadata)
        return f"Tool error: {last_error}"

    def _record_execution(
        self,
        tool_naam: str,
        params: dict,
        result: ToolResult,
        agent_naam: str = None,
        metadata: dict = None
    ):
        """Registreer een tool execution."""
        # Update metrics
        if tool_naam in self.metrics:
            self.metrics[tool_naam].registreer_call(
                result.execution_time,
                result.success,
                result.cached
            )

        # Add to history
        if self.history_enabled and self.history:
            entry = ToolHistoryEntry(
                tool_naam=tool_naam,
                parameters=params,
                result=result,
                agent_naam=agent_naam,
                metadata=metadata or {},
            )
            self.history.add(entry)

    def _trigger_hooks(self, hooks: list[Callable], *args):
        """Trigger event hooks."""
        for hook in hooks:
            try:
                hook(*args)
            except Exception as e:
                self._log(f"Hook error: {e}", Kleur.ROOD)

    def _log(self, bericht: str, kleur_naam: str = Kleur.CYAAN):
        """Log een bericht."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"{kleur(f'[{timestamp}] [ToolRegistry]', kleur_naam)} {bericht}")

    def add_hook(self, event: str, callback: Callable):
        """Voeg een event hook toe."""
        hooks = {
            "execute": self.on_execute,
            "success": self.on_success,
            "error": self.on_error,
        }
        if event in hooks:
            hooks[event].append(callback)

    def get_metrics(self, tool_naam: str = None) -> Union[dict, ToolMetrics]:
        """Haal metrics op."""
        if tool_naam:
            return self.metrics.get(tool_naam, ToolMetrics())

        return {name: m.to_dict() for name, m in self.metrics.items()}

    def get_history(self, count: int = 10) -> list[dict]:
        """Haal recente history op."""
        if not self.history:
            return []
        return [e.to_dict() for e in self.history.get_recent(count)]

    def clear_cache(self, tool_naam: str = None):
        """Wis cache."""
        if self.cache:
            self.cache.invalidate(tool_naam)
            self._log(f"Cache gewist{f' voor {tool_naam}' if tool_naam else ''}")

    def clear_history(self):
        """Wis history."""
        if self.history:
            self.history.clear()
            self._log("History gewist")

    def disable_tool(self, naam: str) -> bool:
        """Schakel tool uit."""
        tool = self.get(naam)
        if tool:
            tool.status = ToolStatus.DISABLED
            self._log(f"Tool uitgeschakeld: {naam}")
            return True
        return False

    def enable_tool(self, naam: str) -> bool:
        """Schakel tool in."""
        tool = self.get(naam)
        if tool:
            tool.status = ToolStatus.ACTIVE
            self._log(f"Tool ingeschakeld: {naam}")
            return True
        return False

    def toon_overzicht(self):
        """Toon een overzicht van alle tools."""
        print(kleur("\n" + "=" * 60, Kleur.CYAAN))
        print(kleur("TOOL REGISTRY OVERZICHT", Kleur.GEEL))
        print(kleur("=" * 60, Kleur.CYAAN))

        print(f"\nTotaal tools: {len(self.tools)}")
        print(f"Actieve tools: {sum(1 for t in self.tools.values() if t.status == ToolStatus.ACTIVE)}")

        # Per categorie
        per_cat = self.lijst_per_categorie()
        print(kleur("\nPer categorie:", Kleur.GEEL))
        for cat, tools in per_cat.items():
            print(f"  {cat}: {len(tools)} tools")

        # Cache stats
        if self.cache:
            cache_stats = self.cache.stats()
            print(kleur("\nCache:", Kleur.GEEL))
            print(f"  Entries: {cache_stats['valid_entries']}/{cache_stats['max_size']}")

        # History stats
        if self.history:
            hist_stats = self.history.stats()
            print(kleur("\nHistory:", Kleur.GEEL))
            print(f"  Totaal calls: {hist_stats['totaal']}")
            if hist_stats['totaal'] > 0:
                print(f"  Succes: {hist_stats['successes']}, Failures: {hist_stats['failures']}")

    def toon_tool_help(self, naam: str):
        """Toon help voor een specifieke tool."""
        tool = self.get(naam)
        if tool:
            print(tool.get_help())
        else:
            print(kleur(f"Tool '{naam}' niet gevonden.", Kleur.ROOD))

    def export_stats(self) -> dict:
        """Exporteer alle statistieken."""
        return {
            "tools": {name: tool.to_dict() for name, tool in self.tools.items()},
            "metrics": {name: m.to_dict() for name, m in self.metrics.items()},
            "cache": self.cache.stats() if self.cache else None,
            "history": self.history.stats() if self.history else None,
            "timestamp": datetime.now().isoformat(),
        }

    def save_stats(self):
        """Sla statistieken op naar bestand."""
        stats_file = self.data_dir / "tool_stats.json"
        try:
            with open(stats_file, "w", encoding="utf-8") as f:
                json.dump(self.export_stats(), f, indent=2, ensure_ascii=False)
            self._log(f"Stats opgeslagen naar {stats_file.name}")
        except Exception as e:
            self._log(f"Kon stats niet opslaan: {e}", Kleur.ROOD)


# Helper functies voor het maken van tools
def maak_tool(
    naam: str,
    beschrijving: str,
    functie: Callable,
    parameters: dict = None,
    categorie: ToolCategory = ToolCategory.ALGEMEEN,
    **kwargs
) -> Tool:
    """
    Helper functie om snel een tool te maken.

    Args:
        naam: Naam van de tool
        beschrijving: Korte beschrijving
        functie: De functie die uitgevoerd wordt
        parameters: Parameter schema (optional)
        categorie: Tool categorie
        **kwargs: Extra Tool attributen

    Returns:
        Tool instance
    """
    if parameters is None:
        # Probeer parameters af te leiden uit functie signature
        import inspect
        sig = inspect.signature(functie)
        parameters = {}
        for param_name, param in sig.parameters.items():
            param_type = "string"
            if param.annotation != inspect.Parameter.empty:
                if param.annotation == int:
                    param_type = "integer"
                elif param.annotation == float:
                    param_type = "number"
                elif param.annotation == bool:
                    param_type = "boolean"
                elif param.annotation == list:
                    param_type = "array"
                elif param.annotation == dict:
                    param_type = "object"

            parameters[param_name] = {
                "type": param_type,
                "description": f"Parameter {param_name}"
            }

    return Tool(
        naam=naam,
        beschrijving=beschrijving,
        parameters=parameters,
        functie=functie,
        categorie=categorie,
        **kwargs
    )


def tool_decorator(
    naam: str = None,
    beschrijving: str = None,
    categorie: ToolCategory = ToolCategory.ALGEMEEN,
    **kwargs
):
    """
    Decorator om een functie als tool te registreren.

    Usage:
        @tool_decorator(naam="mijn_tool", beschrijving="Doet iets")
        def mijn_functie(param1: str) -> str:
            return f"Resultaat: {param1}"
    """
    def decorator(func: Callable) -> Tool:
        tool_naam = naam or func.__name__
        tool_beschrijving = beschrijving or func.__doc__ or "Geen beschrijving"

        return maak_tool(
            naam=tool_naam,
            beschrijving=tool_beschrijving,
            functie=func,
            categorie=categorie,
            **kwargs
        )

    return decorator

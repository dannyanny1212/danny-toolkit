"""
Central Brain - De orkestrator die alle apps als tools aanstuurt.

Het hart van Danny's AI Ecosysteem met:
- Function Calling naar 31+ apps
- Unified Memory integratie
- Super-Workflow uitvoering
- Proactieve suggesties
"""

import os
import json
import asyncio
import importlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable

from ..core.config import Config
from ..core.utils import kleur, Kleur

from .app_tools import (
    APP_TOOLS,
    AppDefinition,
    get_all_tools,
    get_priority_tools,
    parse_tool_call,
    get_app_definition
)
from .unified_memory import UnifiedMemory
from .workflows import WorkflowEngine, SUPER_WORKFLOWS, get_workflow_by_intent

# AI Integration
try:
    from anthropic import Anthropic
    ANTHROPIC_BESCHIKBAAR = True
except ImportError:
    ANTHROPIC_BESCHIKBAAR = False

try:
    from groq import Groq
    GROQ_BESCHIKBAAR = True
except ImportError:
    GROQ_BESCHIKBAAR = False


class CentralBrain:
    """
    De orkestrator die alle apps als tools aanstuurt.

    Features:
    - App Registry: Alle 31+ apps als callable tools
    - Function Calling: Claude roept automatisch de juiste apps aan
    - Unified Memory: Gedeeld geheugen voor cross-app context
    - Workflow Engine: Super-workflows uitvoeren
    """

    VERSIE = "1.0.0"

    def __init__(self, use_memory: bool = True):
        """
        Initialiseer Central Brain.

        Args:
            use_memory: Of unified memory gebruikt moet worden
        """
        Config.ensure_dirs()

        # Data directory
        self.data_dir = Config.DATA_DIR / "brain"
        self.data_dir.mkdir(exist_ok=True)
        self.data_file = self.data_dir / "brain_data.json"

        # AI Client - probeer GROQ eerst (gratis), dan Anthropic
        self.client = None
        self.ai_provider = None
        self._fallback_client = None
        self._fallback_provider = None

        if GROQ_BESCHIKBAAR and Config.has_groq_key():
            self.client = Groq()
            self.ai_provider = "groq"
            print(kleur(
                "   [OK] Central Brain AI actief (GROQ)",
                Kleur.GROEN,
            ))
            # Anthropic als fallback bij rate limit
            if ANTHROPIC_BESCHIKBAAR and Config.has_anthropic_key():
                self._fallback_client = Anthropic()
                self._fallback_provider = "anthropic"
                print(kleur(
                    "   [OK] Fallback: Anthropic beschikbaar",
                    Kleur.GROEN,
                ))
        elif ANTHROPIC_BESCHIKBAAR and Config.has_anthropic_key():
            self.client = Anthropic()
            self.ai_provider = "anthropic"
            print(kleur(
                "   [OK] Central Brain AI actief (Anthropic)",
                Kleur.GROEN,
            ))
        else:
            print(kleur(
                "   [!] Central Brain in offline modus",
                Kleur.GEEL,
            ))

        # App Registry
        self.app_registry: Dict[str, Any] = {}
        self.app_instances: Dict[str, Any] = {}
        self._register_all_apps()

        # Unified Memory
        self.unified_memory = None
        if use_memory:
            try:
                self.unified_memory = UnifiedMemory()
            except Exception as e:
                print(kleur(f"   [!] Memory init failed: {e}", Kleur.GEEL))

        # Workflow Engine
        self.workflow_engine = WorkflowEngine(
            app_executor=self._execute_app_action
        )

        # Tool definitions voor Claude
        self.tool_definitions = get_all_tools()

        # Conversation history voor context
        self.conversation_history: List[dict] = []

        # Statistieken
        self.stats = self._laad_stats()

        print(kleur(f"   [OK] {len(self.app_registry)} apps geregistreerd", Kleur.GROEN))

    def _laad_stats(self) -> dict:
        """Laad statistieken."""
        if self.data_file.exists():
            try:
                with open(self.data_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {
            "requests_verwerkt": 0,
            "tool_calls": 0,
            "workflows_uitgevoerd": 0,
            "laatste_gebruik": None
        }

    def _sla_stats_op(self):
        """Sla statistieken op."""
        with open(self.data_file, "w", encoding="utf-8") as f:
            json.dump(self.stats, f, indent=2, ensure_ascii=False)

    def _register_all_apps(self):
        """Registreer alle apps uit APP_TOOLS."""
        for app_naam, app_def in APP_TOOLS.items():
            self.app_registry[app_naam] = app_def

    def _get_app_instance(self, app_naam: str) -> Optional[Any]:
        """
        Haal of maak app instance.

        Lazy loading - apps worden pas geïnstantieerd wanneer nodig.
        """
        if app_naam in self.app_instances:
            return self.app_instances[app_naam]

        app_def = self.app_registry.get(app_naam)
        if not app_def:
            return None

        try:
            # Dynamisch importeren
            module = importlib.import_module(app_def.module_path)
            app_class = getattr(module, app_def.class_name)
            instance = app_class()
            self.app_instances[app_naam] = instance
            return instance
        except Exception as e:
            print(kleur(f"   [!] Kon {app_naam} niet laden: {e}", Kleur.ROOD))
            return None

    async def _execute_app_action(
        self,
        app_naam: str,
        actie_naam: str,
        params: Dict[str, Any]
    ) -> Any:
        """
        Voer een app actie uit.

        Args:
            app_naam: Naam van de app
            actie_naam: Naam van de actie
            params: Parameters voor de actie

        Returns:
            Resultaat van de actie
        """
        app = self._get_app_instance(app_naam)
        if not app:
            return {"error": f"App '{app_naam}' niet beschikbaar"}

        # Zoek de methode
        method_name = actie_naam
        method = getattr(app, method_name, None)

        # Probeer alternatieve namen
        if not method:
            method = getattr(app, f"_{method_name}", None)
        if not method:
            method = getattr(app, f"do_{method_name}", None)

        if not method:
            # Fallback: probeer data direct te lezen
            return self._get_app_data(app_naam, actie_naam, params)

        try:
            # Voer de methode uit
            if asyncio.iscoroutinefunction(method):
                result = await method(**params)
            else:
                result = method(**params)

            # Log in unified memory
            if self.unified_memory:
                self.unified_memory.store_event(
                    app=app_naam,
                    event_type=actie_naam,
                    data={
                        "params": params,
                        "result_type": type(result).__name__
                    }
                )

            self.stats["tool_calls"] += 1
            return result

        except TypeError as e:
            # Methode verwacht andere parameters
            return self._get_app_data(app_naam, actie_naam, params)
        except Exception as e:
            return {"error": f"Actie {actie_naam} gefaald: {e}"}

    def _get_app_data(
        self,
        app_naam: str,
        actie_naam: str,
        params: Dict[str, Any]
    ) -> Any:
        """
        Haal app data op als directe methode niet werkt.

        Leest data direct uit app data bestanden.
        """
        # Bepaal data bestand
        data_paths = [
            Config.APPS_DATA_DIR / app_naam / "data.json",
            Config.APPS_DATA_DIR / f"{app_naam}.json",
            Config.APPS_DATA_DIR / app_naam / f"{app_naam}_data.json",
        ]

        for data_path in data_paths:
            if data_path.exists():
                try:
                    with open(data_path, "r", encoding="utf-8") as f:
                        data = json.load(f)

                    # Filter data op basis van actie
                    if actie_naam.startswith("get_"):
                        key = actie_naam[4:]  # Remove "get_"
                        if key in data:
                            return data[key]
                        # Zoek verwante keys
                        for k, v in data.items():
                            if key in k.lower():
                                return v

                    return data
                except (json.JSONDecodeError, IOError):
                    pass

        return {"status": "geen_data", "app": app_naam, "actie": actie_naam}

    def process_request(
        self,
        user_input: str,
        use_tools: bool = True,
        max_turns: int = 5
    ) -> str:
        """
        Verwerk gebruikersverzoek via Function Calling.

        Args:
            user_input: De vraag/opdracht van de gebruiker
            use_tools: Of tools gebruikt mogen worden
            max_turns: Maximum aantal tool-use rondes

        Returns:
            Het antwoord
        """
        if not self.client:
            return self._process_offline(user_input)

        self.stats["requests_verwerkt"] += 1
        self.stats["laatste_gebruik"] = datetime.now().isoformat()

        # Bouw context
        context = self._build_context()

        # System message
        system_message = f"""Je bent Danny's Central Brain - een AI assistent die alle apps in de toolkit kan aansturen.

Je hebt toegang tot {len(self.app_registry)} apps via function calling.
Gebruik de juiste tools om taken uit te voeren.

Context over de gebruiker:
{json.dumps(context, ensure_ascii=False, indent=2)}

Belangrijke regels:
1. Antwoord altijd in het Nederlands
2. Gebruik tools om acties uit te voeren, niet alleen om informatie te geven
3. Wees proactief - als je ziet dat iets relevant is, meld het
4. Combineer informatie uit meerdere apps voor een compleet antwoord"""

        # Voeg user message toe aan history
        self.conversation_history.append({
            "role": "user",
            "content": user_input
        })

        # Route naar juiste provider
        if self.ai_provider == "groq":
            return self._process_groq(system_message, use_tools, max_turns)
        else:
            return self._process_anthropic(system_message, use_tools, max_turns)

    # Groq modellen: primair (groot) en fallback (klein)
    GROQ_MODEL_PRIMARY = "llama-3.3-70b-versatile"
    GROQ_MODEL_FALLBACK = "llama-3.1-8b-instant"

    def _process_groq(
        self,
        system_message: str,
        use_tools: bool,
        max_turns: int,
        _model: str = None,
    ) -> str:
        """Verwerk request via GROQ API."""
        model = _model or self.GROQ_MODEL_PRIMARY
        messages = [{"role": "system", "content": system_message}]
        messages.extend(self.conversation_history)

        # Converteer tools naar OpenAI format voor GROQ
        tools = None
        if use_tools and self.tool_definitions:
            tools = []
            for tool in self.tool_definitions:
                # Clean up schema - verwijder 'required' boolean uit properties
                schema = tool["input_schema"].copy()
                if "properties" in schema:
                    clean_props = {}
                    required_fields = []
                    for prop_name, prop_def in schema["properties"].items():
                        clean_prop = {k: v for k, v in prop_def.items()
                                     if k != "required"}
                        clean_props[prop_name] = clean_prop
                        if prop_def.get("required"):
                            required_fields.append(prop_name)
                    schema["properties"] = clean_props
                    if required_fields:
                        schema["required"] = required_fields

                tools.append({
                    "type": "function",
                    "function": {
                        "name": tool["name"],
                        "description": tool["description"],
                        "parameters": schema
                    }
                })

        for turn in range(max_turns):
            try:
                kwargs = {
                    "model": model,
                    "messages": messages,
                    "max_tokens": 2000,
                }
                if tools:
                    kwargs["tools"] = tools
                    kwargs["tool_choice"] = "auto"
                response = (
                    self.client.chat.completions.create(
                        **kwargs
                    )
                )

                choice = response.choices[0]
                message = choice.message

                # Check voor tool calls
                if message.tool_calls:
                    # Voeg assistant message toe
                    messages.append({
                        "role": "assistant",
                        "content": message.content,
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments
                                }
                            }
                            for tc in message.tool_calls
                        ]
                    })

                    # Voer tools uit
                    for tool_call in message.tool_calls:
                        tool_name = tool_call.function.name
                        try:
                            tool_input = json.loads(tool_call.function.arguments)
                        except json.JSONDecodeError:
                            tool_input = {}

                        # Parse tool name
                        app_naam, actie_naam = parse_tool_call(tool_name)

                        if app_naam and actie_naam:
                            print(kleur(
                                f"   [TOOL] {app_naam}.{actie_naam}",
                                Kleur.CYAAN
                            ))

                            result = asyncio.run(
                                self._execute_app_action(
                                    app_naam, actie_naam, tool_input
                                )
                            )
                        else:
                            result = {"error": f"Tool '{tool_name}' niet gevonden"}

                        # Voeg tool result toe
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": json.dumps(
                                result, ensure_ascii=False, default=str
                            )[:5000]
                        })

                else:
                    # Geen tool calls, return antwoord
                    final_response = message.content or ""

                    self.conversation_history.append({
                        "role": "assistant",
                        "content": final_response
                    })

                    self._sla_stats_op()
                    return final_response

            except Exception as e:
                # Fallback bij rate limit (429)
                if "429" in str(e) or "rate_limit" in str(e):
                    # Stap 1: probeer kleiner Groq model
                    if model == self.GROQ_MODEL_PRIMARY:
                        print(kleur(
                            "   [FALLBACK] Groq 70b rate"
                            " limit -> 8b model",
                            Kleur.GEEL,
                        ))
                        return self._process_groq(
                            system_message,
                            use_tools,
                            max_turns,
                            _model=self.GROQ_MODEL_FALLBACK,
                        )
                    # Stap 2: probeer Anthropic
                    if self._fallback_client:
                        print(kleur(
                            "   [FALLBACK] Groq rate limit"
                            " -> Anthropic",
                            Kleur.GEEL,
                        ))
                        self.client = self._fallback_client
                        self.ai_provider = (
                            self._fallback_provider
                        )
                        self._fallback_client = None
                        self._fallback_provider = None
                        return self._process_anthropic(
                            system_message,
                            use_tools,
                            max_turns,
                        )
                self._sla_stats_op()
                return f"Er is een fout opgetreden: {e}"

        self._sla_stats_op()
        return "Maximum aantal rondes bereikt. Probeer een specifiekere vraag."

    def _process_anthropic(
        self,
        system_message: str,
        use_tools: bool,
        max_turns: int
    ) -> str:
        """Verwerk request via Anthropic API."""
        messages = self.conversation_history.copy()

        for turn in range(max_turns):
            try:
                response = self.client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=2000,
                    system=system_message,
                    tools=self.tool_definitions if use_tools else [],
                    messages=messages
                )

                # Check voor tool use
                if response.stop_reason == "tool_use":
                    tool_results = []

                    for block in response.content:
                        if block.type == "tool_use":
                            tool_name = block.name
                            tool_input = block.input

                            app_naam, actie_naam = parse_tool_call(tool_name)

                            if app_naam and actie_naam:
                                print(kleur(
                                    f"   [TOOL] {app_naam}.{actie_naam}",
                                    Kleur.CYAAN
                                ))

                                result = asyncio.run(
                                    self._execute_app_action(
                                        app_naam, actie_naam, tool_input
                                    )
                                )

                                tool_results.append({
                                    "type": "tool_result",
                                    "tool_use_id": block.id,
                                    "content": json.dumps(
                                        result, ensure_ascii=False, default=str
                                    )[:5000]
                                })
                            else:
                                tool_results.append({
                                    "type": "tool_result",
                                    "tool_use_id": block.id,
                                    "content": f"Tool '{tool_name}' niet gevonden",
                                    "is_error": True
                                })

                    messages.append({
                        "role": "assistant",
                        "content": response.content
                    })
                    messages.append({
                        "role": "user",
                        "content": tool_results
                    })

                else:
                    final_response = ""
                    for block in response.content:
                        if hasattr(block, "text"):
                            final_response += block.text

                    self.conversation_history.append({
                        "role": "assistant",
                        "content": final_response
                    })

                    self._sla_stats_op()
                    return final_response

            except Exception as e:
                self._sla_stats_op()
                return f"Er is een fout opgetreden: {e}"

        self._sla_stats_op()
        return "Maximum aantal rondes bereikt. Probeer een specifiekere vraag."

    def _process_offline(self, user_input: str) -> str:
        """Verwerk request zonder AI (offline modus)."""
        user_lower = user_input.lower()

        # Check voor workflow triggers
        workflow = get_workflow_by_intent(user_input)
        if workflow:
            return f"Workflow gevonden: {workflow}. Start met 'run_workflow(\"{workflow}\")'"

        # Eenvoudige keyword matching
        if "fitness" in user_lower or "workout" in user_lower:
            data = self._get_app_data("fitness_tracker", "get_stats", {})
            return f"Fitness data: {json.dumps(data, ensure_ascii=False)}"

        if "mood" in user_lower or "stemming" in user_lower:
            data = self._get_app_data("mood_tracker", "get_mood_trend", {})
            return f"Mood data: {json.dumps(data, ensure_ascii=False)}"

        if "goal" in user_lower or "doel" in user_lower:
            data = self._get_app_data("goals_tracker", "get_active_goals", {})
            return f"Goals data: {json.dumps(data, ensure_ascii=False)}"

        return ("Central Brain is in offline modus (geen API key). "
                "Basis data queries zijn beschikbaar.")

    def _build_context(self) -> dict:
        """Bouw context voor AI requests."""
        context = {
            "timestamp": datetime.now().isoformat(),
            "available_apps": list(self.app_registry.keys())
        }

        if self.unified_memory:
            try:
                user_context = self.unified_memory.get_user_context()
                context.update(user_context)
            except Exception:
                pass

        return context

    def run_workflow(
        self,
        workflow_naam: str,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Voer een super-workflow uit.

        Args:
            workflow_naam: Naam van de workflow
            context: Initiële context variabelen

        Returns:
            Workflow resultaten
        """
        print(kleur(f"\n[BRAIN] Starting workflow: {workflow_naam}", Kleur.MAGENTA))

        result = asyncio.run(
            self.workflow_engine.run_workflow(workflow_naam, context)
        )

        self.stats["workflows_uitgevoerd"] += 1
        self._sla_stats_op()

        return result

    def get_proactive_suggestions(self) -> List[str]:
        """
        Genereer proactieve suggesties op basis van context.

        Returns:
            Lijst van suggesties
        """
        suggesties = []

        if not self.unified_memory:
            return suggesties

        context = self.unified_memory.get_user_context()

        # Fitness streak warning
        fitness = context.get("fitness", {})
        if fitness.get("streak_about_to_break"):
            dagen = fitness.get("dagen_sinds_workout", 0)
            suggesties.append(
                f"Je workout streak staat op het spel! ({dagen} dagen sinds workout)"
            )

        # Mood trending down
        mood = context.get("mood", {})
        if mood.get("trending_down"):
            suggesties.append(
                "Je mood lijkt te dalen. Wil je erover praten of iets leuks doen?"
            )

        # Budget check
        expenses = context.get("expenses", {})
        if expenses.get("uitgaven_deze_maand", 0) > 500:
            suggesties.append(
                f"Je hebt €{expenses['uitgaven_deze_maand']:.2f} uitgegeven deze maand. "
                "Wil je een budget check?"
            )

        # Upcoming events
        agenda = context.get("agenda", {})
        if agenda.get("upcoming_event_needs_budget"):
            komende = agenda.get("komende_events", [])
            if komende:
                suggesties.append(
                    f"Je hebt '{komende[0].get('titel')}' gepland. "
                    "Zal ik helpen met planning?"
                )

        return suggesties

    def list_apps(self) -> List[dict]:
        """Lijst alle beschikbare apps."""
        return [
            {
                "naam": app_def.naam,
                "beschrijving": app_def.beschrijving,
                "categorie": app_def.categorie.value,
                "prioriteit": app_def.prioriteit,
                "acties": [a.naam for a in app_def.acties]
            }
            for app_def in self.app_registry.values()
        ]

    def list_workflows(self) -> List[dict]:
        """Lijst alle beschikbare workflows."""
        return self.workflow_engine.list_workflows()

    def get_status(self) -> dict:
        """Haal brain status op."""
        return {
            "versie": self.VERSIE,
            "ai_actief": self.client is not None,
            "ai_provider": self.ai_provider or "offline",
            "memory_actief": self.unified_memory is not None,
            "apps_geregistreerd": len(self.app_registry),
            "apps_geladen": len(self.app_instances),
            "tools_beschikbaar": len(self.tool_definitions),
            "workflows_beschikbaar": len(SUPER_WORKFLOWS),
            "statistieken": self.stats
        }

    def clear_conversation(self):
        """Wis conversation history."""
        self.conversation_history = []
        print(kleur("   [OK] Conversatie gewist", Kleur.GROEN))

    def memory_stats(self) -> dict:
        """Haal memory statistieken op."""
        if not self.unified_memory:
            return {"status": "niet_actief"}
        return self.unified_memory.statistieken()

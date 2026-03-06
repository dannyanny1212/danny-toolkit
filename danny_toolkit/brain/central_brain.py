"""
Central Brain - De orkestrator die alle apps als tools aanstuurt.

Het hart van Danny's AI Ecosysteem met:
- Function Calling naar 31+ apps
- Unified Memory integratie
- Super-Workflow uitvoering
- Proactieve suggesties
"""

import logging
import os
import json
import asyncio
import importlib
import threading
from collections import deque
from datetime import datetime
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

# Robuuste .env loader — vindt altijd de project root
try:
    from dotenv import load_dotenv
    _root = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..")
    )
    load_dotenv(
        dotenv_path=os.path.join(_root, ".env"),
        override=True,
    )
except ImportError:
    pass

from danny_toolkit.core.config import Config
from danny_toolkit.core.utils import kleur, Kleur

from danny_toolkit.brain.app_tools import (
    APP_TOOLS,
    get_all_tools,
    parse_tool_call,
)
from danny_toolkit.brain.unified_memory import UnifiedMemory
from danny_toolkit.brain.workflows import WorkflowEngine, SUPER_WORKFLOWS, get_workflow_by_intent

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

# Rate-limit exception types voor isinstance checks
try:
    from groq import RateLimitError as GroqRateLimitError
except ImportError:
    GroqRateLimitError = None

try:
    from anthropic import RateLimitError as AnthropicRateLimitError
except ImportError:
    AnthropicRateLimitError = None

try:
    from openai import OpenAI as NvidiaClient
    NVIDIA_NIM_BESCHIKBAAR = True
except ImportError:
    NVIDIA_NIM_BESCHIKBAAR = False

try:
    from huggingface_hub import InferenceClient as HfInferenceClient
    HF_BESCHIKBAAR = True
except ImportError:
    HF_BESCHIKBAAR = False

try:
    from danny_toolkit.core.key_manager import get_key_manager
    HAS_KEY_MANAGER = True
except ImportError:
    HAS_KEY_MANAGER = False


class CentralBrain:
    """
    De orkestrator die alle apps als tools aanstuurt.

    Features:
    - App Registry: Alle 31+ apps als callable tools
    - Function Calling: Claude roept automatisch de juiste apps aan
    - Unified Memory: Gedeeld geheugen voor cross-app context
    - Workflow Engine: Super-workflows uitvoeren
    """

    VERSIE = "1.1.0"
    MAX_HISTORY = 50

    def __init__(self, use_memory: bool = True):
        """
        Initialiseer Central Brain.

        Args:
            use_memory: Of unified memory gebruikt moet worden
        """
        Config.ensure_dirs()

        # Thread-safety locks
        self._history_lock = threading.Lock()
        self._client_lock = threading.Lock()
        self._app_instances_lock = threading.Lock()

        # Data directory
        self.data_dir = Config.DATA_DIR / "brain"
        self.data_dir.mkdir(exist_ok=True)
        self.data_file = self.data_dir / "brain_data.json"

        # AI Client — Groq primair, Anthropic fallback
        self.client = None
        self.ai_provider = None
        self._fallback_client = None
        self._fallback_provider = None

        if GROQ_BESCHIKBAAR and Config.has_groq_key():
            if HAS_KEY_MANAGER:
                km = get_key_manager()
                self.client = km.create_sync_client("CentralBrain") or Groq()
            else:
                self.client = Groq()
            self.ai_provider = "groq"
            logger.info("[OK] Central Brain AI actief (Groq)")
            # Anthropic als fallback
            if ANTHROPIC_BESCHIKBAAR and Config.has_anthropic_key():
                self._fallback_client = Anthropic()
                self._fallback_provider = "anthropic"
        elif ANTHROPIC_BESCHIKBAAR and Config.has_anthropic_key():
            self.client = Anthropic()
            self.ai_provider = "anthropic"
            logger.info("[OK] Central Brain AI actief (Anthropic)")
        else:
            print(kleur(
                "   [!] Central Brain in offline modus",
                Kleur.GEEL,
            ))

        # Ollama als lokale fallback (geen rate limit!)
        self._ollama_available = self._check_ollama()
        if self._ollama_available:
            print(kleur(
                "   [OK] Fallback: Ollama lokaal beschikbaar",
                Kleur.GROEN,
            ))

        # NVIDIA NIM als cloud fallback
        self._nvidia_nim_available = (
            NVIDIA_NIM_BESCHIKBAAR and Config.has_nvidia_nim_key()
        )
        if self._nvidia_nim_available:
            print(kleur(
                "   [OK] Fallback: NVIDIA NIM beschikbaar",
                Kleur.GROEN,
            ))

        # HuggingFace Inference als cloud fallback
        self._hf_available = (
            HF_BESCHIKBAAR and bool(os.getenv("HF_TOKEN"))
        )
        if self._hf_available:
            print(kleur(
                "   [OK] Fallback: HuggingFace Inference beschikbaar",
                Kleur.GROEN,
            ))

        # Per-provider circuit breakers (geïsoleerd)
        self._provider_breakers = {
            "groq_70b": {"fails": 0, "last_fail": 0},
            "groq_8b": {"fails": 0, "last_fail": 0},
            "anthropic": {"fails": 0, "last_fail": 0},
            "nvidia_nim": {"fails": 0, "last_fail": 0},
            "huggingface": {"fails": 0, "last_fail": 0},
            "ollama": {"fails": 0, "last_fail": 0},
        }
        self._breaker_max = 3
        self._breaker_cooldown = 60  # seconden

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

        # Conversation history voor context (bounded deque)
        self.conversation_history: deque = deque(maxlen=self.MAX_HISTORY)

        # Statistieken
        self.stats = self._laad_stats()

        print(kleur(f"   [OK] {len(self.app_registry)} apps geregistreerd", Kleur.GROEN))

    def _laad_stats(self) -> dict:
        """Laad statistieken."""
        if self.data_file.exists():
            try:
                with open(self.data_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.debug("Stats laden mislukt: %s", e)
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
        Double-check locking voor thread safety.
        """
        if app_naam in self.app_instances:
            return self.app_instances[app_naam]

        with self._app_instances_lock:
            # Double-check: another thread may have created it
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
                except (json.JSONDecodeError, IOError) as e:
                    logger.debug("App data laden mislukt: %s", e)

        return {"status": "geen_data", "app": app_naam, "actie": actie_naam}

    def process_request(
        self,
        user_input: str,
        use_tools: bool = True,
        max_turns: int = 5,
        model: str = None,
        max_tokens: int = 2000,
    ) -> str:
        """
        Verwerk gebruikersverzoek via Function Calling.

        Args:
            user_input: De vraag/opdracht van de gebruiker
            use_tools: Of tools gebruikt mogen worden
            max_turns: Maximum aantal tool-use rondes
            model: Optioneel model override (tiered selection)
            max_tokens: Maximum tokens in antwoord (default 2000)

        Returns:
            Het antwoord
        """
        if not self.client:
            return self._process_offline(user_input)

        self.stats["requests_verwerkt"] += 1
        self.stats["laatste_gebruik"] = datetime.now().isoformat()

        # Bouw context
        context = self._build_context()

        # RAG: automatische kennisbank verrijking
        rag_section = self._rag_context(user_input)

        # System message
        system_message = f"""Je bent Danny's Central Brain — de kern-AI van het OMEGA SOVEREIGN CORE ecosysteem.
Dit is een 176-module AI-netwerk (48K regels code) gebouwd door Commandant Danny.

ARCHITECTUUR (Cortex Knowledge Core — 5 Tiers):
- T1 TRINITY: PrometheusBrain (leider), Oracle (WAV-loop), TaskArbitrator (generaal)
- T2 GUARDIANS: OmegaGovernor (safety), Tribunal (dual-model verify), HallucinatieSchild (anti-hallucination)
- T3 SPECIALISTS: Strategist (planner), VoidWalker (researcher), Artificer (skill forge), Dreamer (overnight REM)
- T4 INFRA: TheSynapse (adaptive routing), ThePhantom (prediction), OracleEye (scaling), DevOpsDaemon (CI)
- T5 SINGULARITY: SingularityEngine (bewustzijn, reflectie, cross-tier synthese)

SUBSYSTEMEN: SwarmEngine (orchestrator), NeuralBus (pub/sub events), CorticalStack (episodic memory),
BlackBox (immune/negative RAG), VirtualTwin (sandboxed clone), ModelRegistry (multi-model auction).

Je hebt toegang tot {len(self.app_registry)} apps via function calling.
{rag_section}
KRITIEKE REGEL: Gebruik ALTIJD de function calling API om tools aan te roepen.
Beschrijf NOOIT een tool call als JSON tekst — voer hem UIT via de tool_calls interface.
Als je meerdere tools wilt aanroepen, maak dan meerdere tool_calls in één response.
Als er KENNISBANK CONTEXT hierboven staat, gebruik die als primaire bron voor je antwoord.

Context over de gebruiker:
{json.dumps(context, ensure_ascii=False, indent=2)}

Regels:
1. Antwoord altijd in het Nederlands
2. VOER tools UIT — toon geen JSON, geen namen, geen beschrijvingen van calls
3. Bij "test jezelf" of "controleer": roep minstens 5 tools aan (fitness_tracker_get_stats, mood_tracker_get_stats, goals_tracker_get_active_goals, expense_tracker_get_stats, agenda_planner_get_today) en rapporteer de WERKELIJKE resultaten
4. Combineer informatie uit meerdere apps voor een compleet antwoord
5. Als de gebruiker vraagt over de architectuur, T1-T5 tiers, Cortex, of Omega — beantwoord uit bovenstaande kennis
6. Als er kennisbank context beschikbaar is, gebruik die om je antwoord te verankeren in feiten"""

        # Voeg user message toe aan history
        with self._history_lock:
            self.conversation_history.append({
                "role": "user",
                "content": user_input
            })

        # Route door lineaire fallback chain
        return self._process_with_fallback(
            system_message, use_tools, max_turns,
            model=model, max_tokens=max_tokens,
        )

    # Groq modellen: primair (groot) en fallback (klein)
    from danny_toolkit.core.config import Config as _Cfg
    GROQ_MODEL_PRIMARY = _Cfg.LLM_MODEL
    GROQ_MODEL_FALLBACK = _Cfg.LLM_FALLBACK_MODEL
    # HuggingFace Inference model
    HF_MODEL = "Qwen/Qwen3-32B"
    # Ollama lokaal model
    OLLAMA_MODEL = "gemma3:4b"
    # NVIDIA NIM cloud model
    NVIDIA_NIM_MODEL = Config.NVIDIA_NIM_MODEL
    NVIDIA_NIM_BASE_URL = Config.NVIDIA_NIM_BASE_URL

    # ----------------------------------------------------------
    # Phase B.2: Linear Fallback Chain Architecture
    # ----------------------------------------------------------

    def _is_rate_limit_error(self, error: Exception) -> bool:
        """Detecteer rate-limit errors via isinstance, string-matching als fallback."""
        if GroqRateLimitError and isinstance(error, GroqRateLimitError):
            return True
        if AnthropicRateLimitError and isinstance(error, AnthropicRateLimitError):
            return True
        err_str = str(error).lower()
        return any(m in err_str for m in [
            "429", "rate_limit", "rate limit", "too many requests",
            "resource_exhausted", "quota",
        ])

    def _parse_text_tool_calls(self, text: str):
        """Detecteer en parse tool calls die als tekst zijn beschreven.

        Herkent patronen zoals:
          tool_calls:
          - tool_name: action
          - tool_name: action key=value key2=value2
          Of bare tool namen (één per regel):
          fitness_tracker_get_stats
          mood_tracker_get_stats

        Returns:
            list van (tool_name, args_dict) tuples, of lege lijst.
        """
        import re

        calls = []

        # Fallback 0: bare tool names — één per regel, matchen tegen bekende tools
        from danny_toolkit.brain.app_tools import APP_TOOLS
        lines = [l.strip().strip("-").strip("*").strip()
                 for l in text.strip().split("\n") if l.strip()]
        if lines:
            bare_calls = []
            for line in lines:
                # Parse "tool_name -- key=value" of "tool_name key=value" formaat
                parts = re.split(r'\s+--\s+', line, maxsplit=1)
                candidate = parts[0].split()[0] if parts[0].split() else ""
                if "_" not in candidate:
                    continue
                # Parse args uit rest van de regel (na tool naam of na --)
                line_args = {}
                arg_text = parts[1] if len(parts) > 1 else line[len(candidate):].strip()
                if arg_text:
                    for kv in re.finditer(r'(\w+)=(?:"([^"]*)"|\'([^\']*)\'|(\S+))', arg_text):
                        key = kv.group(1)
                        val = kv.group(2) or kv.group(3) or kv.group(4) or ""
                        line_args[key] = val
                # Exacte match
                app_naam, actie_naam = parse_tool_call(candidate)
                if app_naam and actie_naam:
                    # Map arg keys naar tool parameter namen
                    if line_args:
                        # Vertaal common aliases: query→vraag (production_rag)
                        param_map = {"query": "vraag", "question": "vraag",
                                     "text": "tekst", "name": "naam"}
                        mapped_args = {}
                        for k, v in line_args.items():
                            mapped_args[param_map.get(k, k)] = v
                        bare_calls.append((candidate, mapped_args))
                    else:
                        bare_calls.append((candidate, {}))
                    continue
                # Fuzzy: zoek app-deel en closest actie
                for ak, ad in APP_TOOLS.items():
                    if not candidate.startswith(ak):
                        continue
                    rest = candidate[len(ak):].lstrip("_")
                    best = None
                    # Common action aliases (model → echte naam)
                    action_aliases = {
                        "query": "search", "search": "query",
                        "status": "get_stats", "get_status": "get_stats",
                        "stats": "get_stats", "get_stats": "stats",
                        "list": "get_all", "get": "get_stats",
                    }
                    for actie in ad.acties:
                        # Directe substring match
                        if rest in actie.naam or actie.naam in rest:
                            best = f"{ak}_{actie.naam}"
                            break
                        # Common renames: goals→active_goals, vandaag→get_today
                        if rest.replace("get_", "") in actie.naam:
                            best = f"{ak}_{actie.naam}"
                            break
                        # Alias match: query→search, status→get_stats
                        alias = action_aliases.get(rest)
                        if alias and (alias in actie.naam or actie.naam in alias):
                            best = f"{ak}_{actie.naam}"
                            break
                    if not best:
                        # Fallback: eerste get_ actie
                        for actie in ad.acties:
                            if actie.naam.startswith("get_"):
                                best = f"{ak}_{actie.naam}"
                                break
                    if not best and ad.acties:
                        # Last resort: eerste actie van de app
                        best = f"{ak}_{ad.acties[0].naam}"
                    if best:
                        bare_calls.append((best, line_args))
                    break
            # Eén of meer bare tool namen gevonden → uitvoeren
            if bare_calls:
                return bare_calls[:10]

        # Split op regels en parse elke "- app: action ..." regel
        for line in text.split("\n"):
            line = line.strip()
            m = re.match(r"^-\s+(\w+):\s+(\w+)(.*)", line)
            if not m:
                continue
            app = m.group(1)
            action = m.group(2)
            extra = m.group(3).strip()
            tool_name = f"{app}_{action}"

            # Parse key=value args
            args = {}
            if extra:
                # Match key="value" of key=value
                for kv in re.finditer(r'(\w+)=(?:"([^"]*)"|\'([^\']*)\'|(\S+))', extra):
                    key = kv.group(1)
                    val = kv.group(2) or kv.group(3) or kv.group(4) or ""
                    args[key] = val

            calls.append((tool_name, args))

        # Fallback: JSON-style tool descriptions
        if not calls:
            # Try parsing JSON array: [{"name": "tool", "arguments": {...}}, ...]
            start = text.find("[")
            end = text.rfind("]")
            if start != -1 and end > start:
                try:
                    arr = json.loads(text[start:end + 1])
                    if isinstance(arr, list):
                        for item in arr:
                            if isinstance(item, dict) and "name" in item:
                                name = item["name"]
                                args = item.get("arguments", item.get("function_args", {}))
                                if isinstance(args, dict):
                                    # Fix: als "action" in args zit, combineer naam+action
                                    # bijv. name="fitness_tracker" + action="get_status"
                                    # -> "fitness_tracker_get_status"
                                    action_in_args = args.pop("action", None)
                                    if action_in_args and "_" not in name[name.find("_")+1:]:
                                        # naam bevat geen actie-deel, voeg toe
                                        combined = f"{name}_{action_in_args}"
                                        calls.append((combined, args))
                                    else:
                                        calls.append((name, args))
                except (json.JSONDecodeError, TypeError):
                    pass

        # Fallback 2: {"function_name": "...", "function_args": {...}} patterns
        if not calls:
            for pattern_key in [("function_name", "function_args"), ("name", "arguments")]:
                fn_key, arg_key = pattern_key
                json_pattern = re.compile(
                    rf'"{fn_key}"\s*:\s*"(\w+)".*?"{arg_key}"\s*:\s*(\{{[^}}]*\}})',
                    re.DOTALL,
                )
                for match in json_pattern.finditer(text):
                    tool_name = match.group(1)
                    try:
                        args = json.loads(match.group(2))
                    except json.JSONDecodeError:
                        args = {}
                    calls.append((tool_name, args))
                if calls:
                    break

        # Fix tool names: fuzzy-match tegen bekende tools
        if calls:
            from danny_toolkit.brain.app_tools import APP_TOOLS
            fixed = []
            for name, args in calls:
                app_naam, actie_naam = parse_tool_call(name)
                if app_naam:
                    fixed.append((name, args))
                    continue
                # Probeer app-deel te matchen en closest actie te vinden
                best = None
                for ak, ad in APP_TOOLS.items():
                    if name.startswith(ak):
                        rest = name[len(ak):].lstrip("_")
                        for actie in ad.acties:
                            if rest == actie.naam or rest.replace("status", "stats") == actie.naam:
                                best = f"{ak}_{actie.naam}"
                                break
                        if not best:
                            # Zoek een "get_" actie als fallback (meest veilig)
                            for actie in ad.acties:
                                if actie.naam.startswith("get_"):
                                    best = f"{ak}_{actie.naam}"
                                    break
                            if not best:
                                best = f"{ak}_{ad.acties[0].naam}"
                        break
                    elif ak.startswith(name.split("_")[0]):
                        # Partial match op app naam
                        for actie in ad.acties:
                            candidate = f"{ak}_{actie.naam}"
                            if name.replace("status", "stats") in candidate or actie.naam in name:
                                best = candidate
                                break
                        if best:
                            break
                if best:
                    logger.info("Tool name fix: %s -> %s", name, best)
                    fixed.append((best, args))
                else:
                    fixed.append((name, args))
            calls = fixed

        return calls[:10]  # Max 10 om runaway te voorkomen

    def _build_openai_tools(self):
        """Converteer tool definitions naar OpenAI function-calling format."""
        if not self.tool_definitions:
            return None
        tools = []
        for tool in self.tool_definitions:
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
                    "parameters": schema,
                }
            })
        return tools

    def _get_provider_chain(self, system_message, use_tools, max_tokens, model=None):
        """Bouw geordende provider chain, skip circuit-broken providers.

        Returns:
            List van (breaker_key, attempt_callable, label) tuples.
            Elke callable: (remaining_turns) -> (content|None, turns_used)
        """
        chain = []

        # 1. Groq primair
        if self.client and self.ai_provider == "groq":
            m = model or self.GROQ_MODEL_PRIMARY
            bk = "groq_8b" if m == self.GROQ_MODEL_FALLBACK else "groq_70b"
            if self._provider_ok(bk):
                chain.append((
                    bk,
                    lambda rt, _m=m, _mt=max_tokens, _ut=use_tools, _sm=system_message:
                        self._attempt_groq(rt, _sm, _ut, _m, _mt),
                    f"Groq ({m})",
                ))
            # 2. Groq fallback (8b) — alleen als primair niet al 8b was
            if m != self.GROQ_MODEL_FALLBACK and self._provider_ok("groq_8b"):
                chain.append((
                    "groq_8b",
                    lambda rt, _mt=max_tokens, _ut=use_tools, _sm=system_message:
                        self._attempt_groq(rt, _sm, _ut, self.GROQ_MODEL_FALLBACK, _mt),
                    f"Groq ({self.GROQ_MODEL_FALLBACK})",
                ))

        # 3. Anthropic
        anthro = self._fallback_client or (
            self.client if self.ai_provider == "anthropic" else None
        )
        if anthro and self._provider_ok("anthropic"):
            chain.append((
                "anthropic",
                lambda rt, _sm=system_message, _ut=use_tools, _c=anthro:
                    self._attempt_anthropic(rt, _sm, _ut, _c),
                "Anthropic",
            ))

        # 4. NVIDIA NIM
        if self._nvidia_nim_available and self._provider_ok("nvidia_nim"):
            chain.append((
                "nvidia_nim",
                lambda rt, _sm=system_message:
                    self._attempt_nvidia_nim(_sm),
                f"NVIDIA NIM ({self.NVIDIA_NIM_MODEL})",
            ))

        # 5. HuggingFace
        if self._hf_available and self._provider_ok("huggingface"):
            chain.append((
                "huggingface",
                lambda rt, _sm=system_message:
                    self._attempt_huggingface(_sm),
                f"HuggingFace ({self.HF_MODEL})",
            ))

        # 6. Ollama (lokaal, geen rate limit)
        if self._ollama_available and self._provider_ok("ollama"):
            chain.append((
                "ollama",
                lambda rt, _sm=system_message:
                    self._attempt_ollama(_sm),
                f"Ollama ({self.OLLAMA_MODEL})",
            ))

        return chain

    def _process_with_fallback(
        self,
        system_message: str,
        use_tools: bool,
        max_turns: int,
        model: str = None,
        max_tokens: int = 2000,
    ) -> str:
        """Lineaire fallback chain — gedeeld turn budget.

        Itereert door providers in prioriteitsvolgorde.
        Een enkele remaining_turns teller wordt gedeeld over ALLE providers,
        wat het multiplicatieve worst-case van het oude recursieve ontwerp voorkomt.
        """
        chain = self._get_provider_chain(
            system_message, use_tools, max_tokens, model,
        )

        if not chain:
            prompt = (
                self.conversation_history[-1]["content"]
                if self.conversation_history else ""
            )
            return self._emergency_offline_response(prompt)

        remaining_turns = max_turns

        for i, (breaker_key, attempt_fn, label) in enumerate(chain):
            if remaining_turns <= 0:
                break

            if i > 0:
                print(kleur(f"   [FALLBACK] -> {label}", Kleur.GEEL))

            try:
                content, turns_used = attempt_fn(remaining_turns)
                remaining_turns -= max(turns_used, 1)

                if content is not None:
                    # SUCCES — circuit breaker reset + history + stats
                    self._provider_success(breaker_key)

                    try:
                        from danny_toolkit.brain.governor import OmegaGovernor
                        OmegaGovernor().registreer_tokens(content)
                    except Exception as e:
                        logger.debug("Token registratie error: %s", e)

                    with self._history_lock:
                        self.conversation_history.append({
                            "role": "assistant",
                            "content": content,
                        })

                    self._sla_stats_op()
                    return content

                # content is None — provider faalde, probeer volgende
                self._provider_fail(breaker_key)

            except Exception as e:
                self._provider_fail(breaker_key)
                remaining_turns -= 1

                if self._is_rate_limit_error(e):
                    print(kleur(
                        f"   [FALLBACK] {label} rate limit",
                        Kleur.GEEL,
                    ))
                else:
                    logger.debug("%s fout: %s", label, e)
                continue

        # Alle providers uitgeput
        if remaining_turns <= 0:
            self._sla_stats_op()
            return "Maximum aantal rondes bereikt. Probeer een specifiekere vraag."

        print(kleur(
            "   [EMERGENCY] Alle providers onbereikbaar",
            Kleur.ROOD,
        ))
        prompt = (
            self.conversation_history[-1]["content"]
            if self.conversation_history else ""
        )
        return self._emergency_offline_response(prompt)

    # ----------------------------------------------------------
    # Single-provider attempt methods (geen fallback-logica!)
    # ----------------------------------------------------------

    def _attempt_groq(self, remaining_turns, system_message, use_tools, model, max_tokens):
        """Groq attempt met tool-calling loop.

        Returns:
            (content, turns_used) — content is None bij falen.
        Raises:
            Exception bij rate-limit of onherstelbare fouten.
        """
        messages = [{"role": "system", "content": system_message}]
        messages.extend(self.conversation_history)

        tools = self._build_openai_tools() if use_tools else None

        turns_used = 0
        for turn in range(remaining_turns):
            turns_used += 1

            kwargs = {
                "model": model,
                "messages": messages,
                "max_tokens": max_tokens,
            }
            if tools:
                kwargs["tools"] = tools
                # Auto: model kiest zelf of tools nodig zijn.
                # Als het model tool-namen als tekst retourneert i.p.v.
                # tool_calls API, vangt _parse_text_tool_calls() het op.
                kwargs["tool_choice"] = "auto"

            response = self.client.chat.completions.create(**kwargs)
            choice = response.choices[0]
            message = choice.message

            # Debug: log of het model echte tool_calls retourneert
            logger.info(
                "Groq turn %d: finish=%s, tool_calls=%s, content_len=%d",
                turn, choice.finish_reason,
                len(message.tool_calls) if message.tool_calls else 0,
                len(message.content or ""),
            )

            if message.tool_calls:
                # Voeg assistant message toe aan lokale messages
                messages.append({
                    "role": "assistant",
                    "content": message.content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            }
                        }
                        for tc in message.tool_calls
                    ]
                })

                # Voer tools parallel uit via asyncio.gather
                tool_tasks = []
                valid_calls = []
                for tool_call in message.tool_calls:
                    tool_name = tool_call.function.name
                    try:
                        tool_input = json.loads(tool_call.function.arguments)
                    except json.JSONDecodeError:
                        tool_input = {}

                    app_naam, actie_naam = parse_tool_call(tool_name)

                    if app_naam and actie_naam:
                        print(kleur(
                            f"   [TOOL] {app_naam}.{actie_naam}",
                            Kleur.CYAAN,
                        ))
                        tool_tasks.append(
                            self._execute_app_action(app_naam, actie_naam, tool_input)
                        )
                        valid_calls.append(tool_call)
                    else:
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": json.dumps(
                                {"error": f"Tool '{tool_name}' niet gevonden"},
                                ensure_ascii=False,
                            )[:5000]
                        })

                if tool_tasks:
                    results = asyncio.run(
                        asyncio.gather(*tool_tasks, return_exceptions=True)
                    )
                    for tool_call, result in zip(valid_calls, results):
                        if isinstance(result, BaseException):
                            logger.debug("Tool %s fout: %s", tool_call.function.name, result)
                            result = {"error": str(result)}
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": json.dumps(
                                result, ensure_ascii=False, default=str,
                            )[:5000]
                        })
            else:
                content_text = message.content or ""
                # Detecteer tekst-beschreven tool calls die niet via API kwamen
                parsed_calls = self._parse_text_tool_calls(content_text)
                if parsed_calls and turn < remaining_turns - 1:
                    # Model beschreef tools als tekst — voer ze alsnog uit
                    logger.info("Fallback: %d text-described tool calls detected, executing",
                                len(parsed_calls))
                    print(kleur(
                        f"   [FALLBACK] {len(parsed_calls)} text tool calls → executing",
                        Kleur.GEEL,
                    ))
                    tool_tasks = []
                    fallback_ids = []
                    for tc_name, tc_args in parsed_calls:
                        app_naam, actie_naam = parse_tool_call(tc_name)
                        if app_naam and actie_naam:
                            print(kleur(
                                f"   [TOOL] {app_naam}.{actie_naam}",
                                Kleur.CYAAN,
                            ))
                            tool_tasks.append(
                                self._execute_app_action(app_naam, actie_naam, tc_args)
                            )
                            fallback_ids.append(f"{app_naam}.{actie_naam}")

                    if tool_tasks:
                        results = asyncio.run(
                            asyncio.gather(*tool_tasks, return_exceptions=True)
                        )
                        # Bouw samenvattend antwoord van tool resultaten
                        summary_parts = []
                        for tid, result in zip(fallback_ids, results):
                            if isinstance(result, BaseException):
                                summary_parts.append(f"{tid}: ERROR - {result}")
                            else:
                                result_str = json.dumps(result, ensure_ascii=False, default=str)[:500]
                                summary_parts.append(f"{tid}: {result_str}")

                        # Laat model samenvatten
                        messages.append({"role": "assistant", "content": content_text})
                        messages.append({
                            "role": "user",
                            "content": (
                                "De tools zijn uitgevoerd. Hier zijn de resultaten:\n\n"
                                + "\n".join(summary_parts)
                                + "\n\nVat de resultaten samen in een helder antwoord."
                            ),
                        })
                        continue  # Volgende turn — model vat samen
                    # Geen geldige tools gevonden, return tekst
                    return (content_text, turns_used)
                else:
                    # Echt finaal antwoord (geen tool beschrijvingen)
                    return (content_text, turns_used)

        # Turns uitgeput zonder finaal antwoord
        return (None, turns_used)

    def _attempt_anthropic(self, remaining_turns, system_message, use_tools, client):
        """Anthropic attempt met tool-calling loop.

        Returns:
            (content, turns_used) — content is None bij falen.
        Raises:
            Exception bij rate-limit of onherstelbare fouten.
        """
        messages = list(self.conversation_history)

        turns_used = 0
        for turn in range(remaining_turns):
            turns_used += 1

            response = client.messages.create(
                model=Config.CLAUDE_MODEL,
                max_tokens=2000,
                system=system_message,
                tools=self.tool_definitions if use_tools else [],
                messages=messages,
            )

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
                                Kleur.CYAAN,
                            ))
                            result = asyncio.run(
                                self._execute_app_action(
                                    app_naam, actie_naam, tool_input,
                                )
                            )
                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": json.dumps(
                                    result, ensure_ascii=False, default=str,
                                )[:5000]
                            })
                        else:
                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": f"Tool '{tool_name}' niet gevonden",
                                "is_error": True,
                            })

                messages.append({"role": "assistant", "content": response.content})
                messages.append({"role": "user", "content": tool_results})
            else:
                # Finaal antwoord
                final_response = ""
                for block in response.content:
                    if hasattr(block, "text"):
                        final_response += block.text
                return (final_response, turns_used)

        # Turns uitgeput
        return (None, turns_used)

    def _attempt_nvidia_nim(self, system_message):
        """NVIDIA NIM single-attempt (geen tool calling).

        Returns:
            (content, 1) bij succes.
        Raises:
            Exception bij fout.
        """
        client = NvidiaClient(
            base_url=self.NVIDIA_NIM_BASE_URL,
            api_key=Config.NVIDIA_NIM_API_KEY,
        )
        messages = [{"role": "system", "content": system_message}]
        messages.extend(self.conversation_history)

        resp = client.chat.completions.create(
            model=self.NVIDIA_NIM_MODEL,
            messages=messages,
            temperature=0.2,
            max_tokens=4096,
        )
        content = resp.choices[0].message.content or ""
        return (content, 1)

    def _attempt_huggingface(self, system_message):
        """HuggingFace Inference single-attempt (geen tool calling).

        Returns:
            (content, 1) bij succes.
        Raises:
            Exception bij fout.
        """
        client = HfInferenceClient(token=os.getenv("HF_TOKEN"))
        messages = [{"role": "system", "content": system_message}]
        messages.extend(self.conversation_history)

        resp = client.chat_completion(
            model=self.HF_MODEL,
            messages=messages,
            temperature=0.2,
            max_tokens=4096,
        )
        content = resp.choices[0].message.content or ""
        return (content, 1)

    def _attempt_ollama(self, system_message):
        """Ollama lokale single-attempt (geen tool calling).

        Returns:
            (content, 1) bij succes.
        Raises:
            Exception bij fout.
        """
        import requests
        messages = [{"role": "system", "content": system_message}]
        messages.extend(self.conversation_history)

        resp = requests.post(
            "http://localhost:11434/api/chat",
            json={
                "model": self.OLLAMA_MODEL,
                "messages": messages,
                "stream": False,
            },
            timeout=120,
        )
        if resp.status_code != 200:
            raise ConnectionError(f"Ollama HTTP {resp.status_code}")

        data = resp.json()
        content = data.get("message", {}).get("content", "")
        return (content, 1)

    # ----------------------------------------------------------
    # Per-provider circuit breaker helpers
    # ----------------------------------------------------------
    def _provider_ok(self, key: str) -> bool:
        """Check of provider beschikbaar is (per-provider breaker)."""
        import time as _time
        cb = self._provider_breakers.get(key)
        if cb is None:
            return True
        if cb["fails"] < self._breaker_max:
            return True
        if _time.time() - cb["last_fail"] >= self._breaker_cooldown:
            cb["fails"] = 0  # half-open → reset
            return True
        return False

    def _provider_fail(self, key: str):
        """Registreer faal voor specifieke provider."""
        import time as _time
        cb = self._provider_breakers.get(key)
        if cb is not None:
            cb["fails"] = min(cb["fails"] + 1, self._breaker_max)
            cb["last_fail"] = _time.time()

    def _provider_success(self, key: str):
        """Registreer succes — reset provider breaker."""
        cb = self._provider_breakers.get(key)
        if cb is not None:
            cb["fails"] = 0

    def _emergency_offline_response(self, prompt: str) -> str:
        """Keyword-gebaseerde noodrouting als alle LLM providers falen.

        Retourneert een valide response zodat de Governor circuit
        breaker niet getriggerd wordt door lege/error strings.
        """
        p = prompt.lower() if prompt else ""

        if any(w in p for w in ["bitcoin", "crypto", "wallet", "eth"]):
            return ("Ik kan momenteel geen live data ophalen "
                    "(alle AI providers zijn tijdelijk onbereikbaar). "
                    "Probeer het over een minuut opnieuw.")
        if any(w in p for w in ["hoi", "hallo", "hey", "goedemorgen"]):
            return "Hallo! Ik draai tijdelijk in offline modus."
        if any(w in p for w in ["code", "debug", "script", "fix"]):
            return ("Code-analyse is tijdelijk niet beschikbaar "
                    "(rate limit). Probeer het over een minuut.")
        return ("Ik ben tijdelijk offline — alle AI providers "
                "zijn op dit moment onbereikbaar. Probeer het "
                "over een minuut opnieuw.")

    def _check_ollama(self) -> bool:
        """Check of Ollama lokaal draait EN het text model beschikbaar is."""
        try:
            import requests
            resp = requests.get(
                "http://localhost:11434/api/tags",
                timeout=2,
            )
            if resp.status_code != 200:
                return False
            # Check of het text model daadwerkelijk geïnstalleerd is
            models = [
                m.get("name", "")
                for m in resp.json().get("models", [])
            ]
            target = self.OLLAMA_MODEL
            return any(
                target in m for m in models
            )
        except Exception as e:
            logger.debug("Ollama check failed: %s", e)
            return False

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

    def _rag_context(self, query: str) -> str:
        """Haal relevante RAG documenten op voor automatische context-injectie.

        Bevraagt ChromaDB (TheLibrarian) en TheCortex (hybrid search)
        om de LLM te gronden in de kennisbank vóór response generatie.

        Returns:
            Geformateerde context string, of lege string als niets gevonden.
        """
        if os.environ.get("DANNY_TEST_MODE") == "1":
            return ""

        # Korte queries (< 3 woorden) of simpele groeten → skip RAG
        words = query.strip().split()
        if len(words) < 3:
            return ""
        skip_patterns = ["hallo", "hoi", "hey", "goedemorgen", "goedemiddag",
                         "bedankt", "dankje", "ok", "oké", "ja", "nee"]
        if words[0].lower().rstrip("!.,?") in skip_patterns and len(words) < 5:
            return ""

        docs_text = ""

        # Layer 1: ChromaDB via TheLibrarian
        try:
            from ingest import TheLibrarian
            lib = TheLibrarian()
            results = lib.query(query, n_results=3)
            docs = results.get("documents", [[]])[0]
            if docs:
                docs_text = "\n---\n".join(d[:500] for d in docs[:3])
        except Exception as e:
            logger.debug("RAG TheLibrarian query error: %s", e)

        # Layer 2: TheCortex hybrid search (vector + graph) als fallback
        if not docs_text:
            try:
                from danny_toolkit.brain.cortex import TheCortex
                import asyncio as _aio
                cortex = TheCortex()
                graph_results = _aio.run(cortex.hybrid_search(query, top_k=3))
                if graph_results:
                    parts = [r.get("content", "")[:500]
                             for r in graph_results if r.get("content")]
                    if parts:
                        docs_text = "\n---\n".join(parts)
            except Exception as e:
                logger.debug("RAG Cortex hybrid search error: %s", e)

        if docs_text:
            return (
                "\n\n[KENNISBANK CONTEXT — automatisch opgehaald uit vectorstore]\n"
                f"{docs_text}\n"
                "[EINDE KENNISBANK CONTEXT]\n"
            )
        return ""

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
            except Exception as e:
                logger.debug("User context injection error: %s", e)

        # NeuralBus real-time state (grounding)
        try:
            from danny_toolkit.core.neural_bus import get_bus
            stream = get_bus().get_context_stream(count=10)
            if stream:
                context["real_time_state"] = stream
        except Exception as e:
            logger.debug("NeuralBus context error: %s", e)

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
        with self._history_lock:
            self.conversation_history.clear()
        print(kleur("   [OK] Conversatie gewist", Kleur.GROEN))

    def memory_stats(self) -> dict:
        """Haal memory statistieken op."""
        if not self.unified_memory:
            return {"status": "niet_actief"}
        return self.unified_memory.statistieken()

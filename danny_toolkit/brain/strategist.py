"""
Strategist — Recursive Task Planner (v6.0 Invention).

Decomponeert complexe taken via LLM in sub-stappen, delegeert naar
de juiste swarm agents, en chaint resultaten. Bevat search-query
meta-filter om tool name leakage in LLM-plannen te voorkomen.
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Dict, Optional

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
    logger.debug("dotenv not available, skipping .env load")

try:
    from groq import AsyncGroq
    HAS_GROQ = True
except ImportError:
    HAS_GROQ = False

from danny_toolkit.core.config import Config
from danny_toolkit.core.utils import Kleur

try:
    from danny_toolkit.core.key_manager import get_key_manager
    HAS_KEY_MANAGER = True
except ImportError:
    HAS_KEY_MANAGER = False

try:
    from danny_toolkit.core.groq_retry import groq_call_async
    HAS_RETRY = True
except ImportError:
    HAS_RETRY = False

try:
    from danny_toolkit.brain.void_walker import VoidWalker
    HAS_WALKER = True
except ImportError:
    HAS_WALKER = False

try:
    from danny_toolkit.brain.artificer import Artificer
    HAS_ARTIFICER = True
except ImportError:
    HAS_ARTIFICER = False

HAS_GUARD = False
try:
    from auto_refactor_guard import audit_file as guard_audit_file
    HAS_GUARD = True
except ImportError:
    logger.debug("AutoRefactorGuard not available for Strategist")

HAS_BUS = False
try:
    from danny_toolkit.core.neural_bus import get_bus, EventTypes
    HAS_BUS = True
except ImportError:
    logger.debug("NeuralBus not available for Strategist")

HAS_STACK = False
try:
    from danny_toolkit.brain.cortical_stack import get_cortical_stack
    HAS_STACK = True
except ImportError:
    logger.debug("CorticalStack not available for Strategist")

HAS_ORACLE = False
try:
    from danny_toolkit.brain.oracle_eye import TheOracleEye
    HAS_ORACLE = True
except ImportError:
    logger.debug("OracleEye not available for Strategist")


class Strategist:
    """
    INVENTION #15: THE STRATEGIST
    -----------------------------
    The Manager. It turns vague goals into executed workflows.
    It manages the workforce: Walker (Research), Artificer (Code),
    Brain (Analysis), Tribunal (Safety).

    Flow:
        1. Decompose — breaks objective into dependency graph
        2. Assign — delegates steps to the right organ
        3. Route — passes output of step N into input of step N+1
        4. Synthesize — presents final result
    """
    def __init__(self) -> None:
        """Initializes the instance with required clients and components.

 Args:
  None

 Returns:
  None

 Notes:
  Initializes the Groq API client, either through the Key Manager or directly with an API key.
  Configures the LLM model and conditionally initializes the Void Walker, Artificer, Bus, Cortical Stack, and Oracle Eye components based on environment flags."""
        if not HAS_GROQ:
            self.client = None
        elif HAS_KEY_MANAGER:
            km = get_key_manager()
            self.client = km.create_async_client("Strategist")
            if not self.client:
                self.client = AsyncGroq(api_key=km.get_key("Strategist"))
        else:
            self.client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))
        self.model = Config.LLM_MODEL
        self.walker = VoidWalker() if HAS_WALKER else None
        self.artificer = Artificer() if HAS_ARTIFICER else None
        self._bus = get_bus() if HAS_BUS else None
        self._stack = get_cortical_stack() if HAS_STACK else None
        self._oracle = TheOracleEye() if HAS_ORACLE else None

    MAX_STEPS = 5
    MAX_CONTEXT_CHARS = 8000

    def _check_resources(self) -> Optional[str]:
        """Raadpleeg OracleEye voor resource-status vóór plan-fase.

        Returns advies-string als er een piek verwacht wordt, anders None.
        Voorkomt overbelasting van API-quota door preventief naar een
        lichter model te switchen.
        """
        if not self._oracle:
            return None
        try:
            advies = self._oracle.pre_warm_check()
            if advies:
                print(f"{Kleur.GEEL}👁️  OracleEye advies: {advies}{Kleur.RESET}")
                # Switch model als OracleEye dat aanbeveelt
                suggested = self._oracle.suggest_model(
                    {"cpu": 0.0, "queries_last_hour": 0}
                )
                if suggested != self.model:
                    print(f"{Kleur.GEEL}👁️  Strategist schakelt over naar "
                          f"{suggested.split('/')[-1]}{Kleur.RESET}")
                    self.model = suggested
            return advies
        except Exception as e:
            logger.debug("OracleEye check error: %s", e)
            return None

    async def execute_mission(self, user_objective: str) -> str:
        """
        Full mission loop: plan → execute steps → synthesize.
        """
        print(f"{Kleur.CYAAN}♟️  Strategist: Analyzing mission "
              f"'{user_objective}'...{Kleur.RESET}")

        # 0. RESOURCE CHECK — OracleEye voorkomt overbelasting
        self._check_resources()

        # 1. THE PLAN
        plan = await self._formulate_plan(user_objective)
        if not plan or "steps" not in plan:
            return "Mission Aborted: Could not formulate plan."

        steps = plan["steps"][:self.MAX_STEPS]
        context_buffer = ""

        # Publish mission started
        self._publish_event(EventTypes.MISSION_STARTED if HAS_BUS else None, {
            "objective": user_objective,
            "steps": len(steps),
        })
        self._log_event("mission_started", {
            "objective": user_objective,
            "steps": len(steps),
        })

        # 2. THE EXECUTION LOOP
        for i, step in enumerate(steps):
            tool = step.get("tool", "brain")
            action = step.get("action", "")
            details = step.get("details", "")

            print(f"\n{Kleur.GEEL}▶ Step {i+1}/{len(steps)}: "
                  f"{action}{Kleur.RESET}")

            result = ""

            if tool == "void_walker" and self.walker:
                result = await self.walker.fill_knowledge_gap(details) or ""

            elif tool == "artificer" and self.artificer:
                prompt = f"{details}\n\nCONTEXT FROM RESEARCH:\n{context_buffer}"
                result = await self.artificer.execute_task(prompt)

            elif tool == "refactor_guard" and HAS_GUARD:
                result = self._run_guard_scan(details)

            elif tool == "brain":
                prompt = f"{details}\n\nDATA:\n{context_buffer}"
                result = await self._ask_groq(prompt) or ""

            else:
                print(f"{Kleur.ROOD}♟️  Tool '{tool}' niet "
                      f"beschikbaar.{Kleur.RESET}")
                result = f"[Skipped: {tool} unavailable]"

            context_buffer += f"\n[Result of Step {i+1}]:\n{result}\n"

            # Cap context buffer om geheugengroei te voorkomen
            if len(context_buffer) > self.MAX_CONTEXT_CHARS:
                context_buffer = context_buffer[-self.MAX_CONTEXT_CHARS:]

            # Publish step completed
            self._publish_event(EventTypes.STEP_COMPLETED if HAS_BUS else None, {
                "step": i + 1,
                "total": len(steps),
                "tool": tool,
                "action": action,
            })

        # 3. THE REPORT
        print(f"\n{Kleur.GROEN}🏁 Mission Accomplished.{Kleur.RESET}")
        return context_buffer

    @staticmethod
    def _extract_json(raw: str) -> Optional[str]:
        """
        JSON Sniper — extracts the first valid JSON object from LLM output.

        Handles: markdown fences, chatty intro/outro text, nested braces.
        """
        # 1. Try markdown ```json ... ``` block first (most reliable)
        fence = re.search(r"```(?:json)?\s*\n?(.*?)```", raw, re.DOTALL)
        if fence:
            raw = fence.group(1).strip()

        # 2. Find first { and match its closing } via brace counting
        start = raw.find("{")
        if start == -1:
            return None

        depth = 0
        in_string = False
        escape = False
        for i in range(start, len(raw)):
            ch = raw[i]
            if escape:
                escape = False
                continue
            if ch == "\\":
                escape = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return raw[start:i + 1]

        return None

    async def _formulate_plan(self, objective: str) -> Optional[Dict]:
        """Asks Groq to decompose the objective into a JSON plan."""
        prompt = f"""
        You are The Strategist. Break this objective into 3-5 sequential steps.
        Objective: "{objective}"

        Available Tools:
        - "void_walker": for researching unknown topics, libraries, or documentation.
        - "artificer": for writing and running Python scripts or file operations.
        - "refactor_guard": for scanning Python files for code quality (type hints, docstrings, imports). Returns a quality score 0-10.
        - "brain": for summarization, analysis, or writing text.

        CRITICAL RULE for "details" field:
        When a step uses "void_walker" (internet research), write the "details" field
        as a natural human search query — exactly how someone would type it into Google.
        NEVER include internal tool names like "Void Walker", "Artificer", "brain",
        "void_walker", "Python script", or any system-internal terminology in the
        search query. The search engine does not know these names.
        BAD:  "Use Void Walker to search for Python crypto API"
        GOOD: "cryptocurrency price API with JSON response"

        Return ONLY the raw JSON object below. NO markdown fences, NO intro text, NO outro text.
        {{
            "steps": [
                {{"step": 1, "tool": "void_walker", "action": "Research...", "details": "cryptocurrency price API with JSON response"}},
                {{"step": 2, "tool": "artificer", "action": "Code...", "details": "Write a script to..."}}
            ]
        }}
        """
        try:
            response = await self._ask_groq(prompt)
            if not response:
                return None
            extracted = self._extract_json(response)
            if not extracted:
                print(f"{Kleur.ROOD}♟️  Planning failed: no JSON found "
                      f"in response{Kleur.RESET}")
                return None
            return json.loads(extracted)
        except (json.JSONDecodeError, Exception) as e:
            print(f"{Kleur.ROOD}♟️  Planning failed: {e}{Kleur.RESET}")
            return None

    async def _ask_groq(self, prompt: str) -> Optional[str]:
        """Direct Groq call met retry + throttle."""
        if HAS_RETRY:
            return await groq_call_async(
                self.client, "Strategist", self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4,
            )
        try:
            chat = await self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=self.model,
                temperature=0.4,
            )
            return chat.choices[0].message.content
        except Exception as e:
            print(f"{Kleur.ROOD}♟️  Groq error: {e}{Kleur.RESET}")
            return None

    def _run_guard_scan(self, details: str) -> str:
        """Voer een Auto Refactor Guard scan uit op het opgegeven pad.

        Extraheert een Python-bestandspad uit de details string en scant
        het met de AST-gebaseerde kwaliteitschecker.

        Args:
            details: Beschrijving met pad naar het te scannen bestand.

        Returns:
            Scan resultaat als leesbare tekst met score en issues.
        """

        # Probeer een .py pad te extraheren uit de details
        words = details.replace("\\", "/").split()
        target = None
        for w in words:
            clean = w.strip("'\"`,;")
            if clean.endswith(".py") and Path(clean).exists():
                target = Path(clean)
                break

        if not target:
            # Fallback: probeer als relatief pad vanaf project root
            for w in words:
                clean = w.strip("'\"`,;")
                if clean.endswith(".py"):
                    candidate = Config.BASE_DIR / clean
                    if candidate.exists():
                        target = candidate
                        break

        if not target:
            return f"[refactor_guard] Geen geldig .py bestand gevonden in: {details[:200]}"

        try:
            result = guard_audit_file(target)
            report = (
                f"[refactor_guard] {target.name}: "
                f"{result.quality}/10 [{result.grade}] — "
                f"{len(result.issues)} issues\n"
            )
            for issue in result.issues[:10]:
                report += f"  L{issue.line}: [{issue.rule}] {issue.message}\n"
            if len(result.issues) > 10:
                report += f"  ... en {len(result.issues) - 10} meer\n"

            # Log naar CorticalStack
            self._log_event("guard_scan", {
                "file": str(target),
                "quality": result.quality,
                "grade": result.grade,
                "issues": len(result.issues),
            })

            return report
        except Exception as e:
            logger.warning("Guard scan failed for %s: %s", target, e)
            return f"[refactor_guard] Scan failed: {e}"

    def _publish_event(self, event_type: object, data: dict) -> None:
        """Publiceer event op NeuralBus als beschikbaar."""
        if self._bus and event_type:
            try:
                self._bus.publish(event_type, data, bron="strategist")
            except Exception as e:
                logger.debug("NeuralBus publish error: %s", e)

    def _log_event(self, action: str, details: Optional[dict] = None) -> None:
        """Log naar CorticalStack als beschikbaar."""
        if self._stack:
            try:
                self._stack.log_event(
                    actor="strategist",
                    action=action,
                    details=details,
                    source="strategist",
                )
            except Exception as e:
                logger.debug("CorticalStack log error: %s", e)

from pathlib import Path

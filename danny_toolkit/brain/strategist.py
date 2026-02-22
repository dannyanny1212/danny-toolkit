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
    pass

from groq import AsyncGroq
from danny_toolkit.core.utils import Kleur

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

HAS_BUS = False
try:
    from danny_toolkit.core.neural_bus import get_bus, EventTypes
    HAS_BUS = True
except ImportError:
    pass

HAS_STACK = False
try:
    from danny_toolkit.brain.cortical_stack import get_cortical_stack
    HAS_STACK = True
except ImportError:
    pass


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
    def __init__(self):
        self.client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))
        self.model = "meta-llama/llama-4-scout-17b-16e-instruct"
        self.walker = VoidWalker() if HAS_WALKER else None
        self.artificer = Artificer() if HAS_ARTIFICER else None
        self._bus = get_bus() if HAS_BUS else None
        self._stack = get_cortical_stack() if HAS_STACK else None

    async def execute_mission(self, user_objective: str) -> str:
        """
        Full mission loop: plan → execute steps → synthesize.
        """
        print(f"{Kleur.CYAAN}♟️  Strategist: Analyzing mission "
              f"'{user_objective}'...{Kleur.RESET}")

        # 1. THE PLAN
        plan = await self._formulate_plan(user_objective)
        if not plan or "steps" not in plan:
            return "Mission Aborted: Could not formulate plan."

        steps = plan["steps"]
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

            elif tool == "brain":
                prompt = f"{details}\n\nDATA:\n{context_buffer}"
                result = await self._ask_groq(prompt) or ""

            else:
                print(f"{Kleur.ROOD}♟️  Tool '{tool}' niet "
                      f"beschikbaar.{Kleur.RESET}")
                result = f"[Skipped: {tool} unavailable]"

            context_buffer += f"\n[Result of Step {i+1}]:\n{result}\n"

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
        """Direct Groq call for brain-type tasks."""
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

    def _publish_event(self, event_type, data: dict):
        """Publiceer event op NeuralBus als beschikbaar."""
        if self._bus and event_type:
            try:
                self._bus.publish(event_type, data, bron="strategist")
            except Exception as e:
                logger.debug("NeuralBus publish error: %s", e)

    def _log_event(self, action: str, details: Optional[dict] = None):
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

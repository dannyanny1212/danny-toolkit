import asyncio
import json
import os
from typing import Dict, List, Optional

from groq import AsyncGroq
from danny_toolkit.core.config import Config
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
        self.model = "llama-3.3-70b-versatile"
        self.walker = VoidWalker() if HAS_WALKER else None
        self.artificer = Artificer() if HAS_ARTIFICER else None

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

        # 3. THE REPORT
        print(f"\n{Kleur.GROEN}🏁 Mission Accomplished.{Kleur.RESET}")
        return context_buffer

    async def _formulate_plan(self, objective: str) -> Optional[Dict]:
        """Asks Groq to decompose the objective into a JSON plan."""
        prompt = f"""
        You are The Strategist. Break this objective into 3-5 sequential steps.
        Objective: "{objective}"

        Available Tools:
        - "void_walker": for researching unknown topics, libraries, or documentation.
        - "artificer": for writing and running Python scripts or file operations.
        - "brain": for summarization, analysis, or writing text.

        Return strictly JSON format:
        {{
            "steps": [
                {{"step": 1, "tool": "void_walker", "action": "Research...", "details": "Search for..."}},
                {{"step": 2, "tool": "artificer", "action": "Code...", "details": "Write a script to..."}}
            ]
        }}
        """
        try:
            response = await self._ask_groq(prompt)
            if not response:
                return None
            # Extract JSON from response (handle markdown fences)
            text = response.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text
                if text.endswith("```"):
                    text = text[:-3]
                text = text.strip()
            start = text.find("{")
            end = text.rfind("}") + 1
            if start == -1 or end == 0:
                return None
            return json.loads(text[start:end])
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

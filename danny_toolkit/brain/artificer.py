import ast
import json
import logging
import os
import subprocess
from datetime import datetime
from typing import Optional, Dict

logger = logging.getLogger(__name__)

from groq import AsyncGroq
from danny_toolkit.core.config import Config
from danny_toolkit.core.utils import Kleur

HAS_BUS = False
try:
    from danny_toolkit.core.neural_bus import get_bus, EventTypes
    HAS_BUS = True
except ImportError:
    pass


# Forbidden patterns — static analysis blocklist
_FORBIDDEN = [
    "shutil.rmtree", "os.remove", "os.rmdir", "os.unlink",
    "subprocess.call", "subprocess.Popen", "os.system",
    "format_drive", "rm -rf", "deltree",
    "__import__", "eval(", "exec(",
]


class Artificer:
    """
    THE ARTIFICER (Invention #11)
    -----------------------------
    Turns the toolkit into a self-expanding system.
    If a tool is missing, it is forged, verified, and cataloged.
    """
    def __init__(self):
        self.skills_dir = Config.BASE_DIR / "danny_toolkit" / "skills" / "forge"
        self.registry_path = self.skills_dir / "registry.json"
        self.client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))
        self.model = "gemma2-9b-it"
        self._bus = get_bus() if HAS_BUS else None
        self._ensure_setup()

    def _ensure_setup(self):
        self.skills_dir.mkdir(parents=True, exist_ok=True)
        if not self.registry_path.exists():
            with open(self.registry_path, "w", encoding="utf-8") as f:
                json.dump({}, f)

    async def execute_task(self, request: str) -> str:
        """
        Full Artificer loop: forge → verify → execute → learn.

        Always forges a fresh script — keyword matching was too loose
        and caused stale skill reuse for unrelated tasks.
        """
        registry = self._load_registry()

        # Always forge — each task gets its own script
        print(f"{Kleur.GEEL}🔥 Artificer: Forging new tool for "
              f"'{request[:80]}'...{Kleur.RESET}")
        code = await self._write_script(request)

        if not code:
            return "❌ Artificer: Failed to generate code."

        # Verify (safety + syntax)
        if not self._safety_check(code):
            return "❌ Artificer blocked unsafe code."

        if not self._syntax_check(code):
            return "❌ Artificer blocked code with syntax errors."

        # Save & Register (incrementing skill number)
        skill_name = f"skill_{len(registry) + 1}.py"
        self._save_script(skill_name, code, request)

        # 5. Execute
        print(f"{Kleur.GROEN}🚀 Artificer: Executing...{Kleur.RESET}")
        result = self._run_script(skill_name)

        # Publish forge success
        self._publish_event(EventTypes.FORGE_SUCCESS if HAS_BUS else None, {
            "skill": skill_name,
            "request": request[:200],
        })

        return result

    async def _write_script(self, task: str) -> Optional[str]:
        prompt = (
            f"Write a STANDALONE Python script to: {task}.\n"
            "Rules:\n"
            "- Use ONLY standard library modules when possible.\n"
            "- If external packages are needed, prefer: requests, pillow, pandas.\n"
            "- Print the final result to stdout.\n"
            "- Do NOT use input().\n"
            "- CRITICAL: If the task requires a loop that runs forever "
            "(e.g. while True), ALWAYS add a safety limit so it exits "
            "after at most 5 iterations. Your code is executed immediately "
            "to verify it works; infinite loops cause a 30s timeout.\n"
            "- Return ONLY raw Python source code.\n"
            "- Do NOT wrap in markdown fences (no ```python, no ```).\n"
            "- Do NOT add explanations, comments about the code, or text before/after.\n"
            "- The very first character must be a Python statement (import, def, etc)."
        )
        try:
            chat = await self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=self.model,
                temperature=0.4,
            )
            code = self._clean_generated_code(chat.choices[0].message.content)
            return code
        except Exception as e:
            print(f"{Kleur.ROOD}🔥 Forge error: {e}{Kleur.RESET}")
            return None

    @staticmethod
    def _clean_generated_code(raw: str) -> str:
        """Strip markdown fences, language tags, and surrounding prose."""
        import re
        code = raw.strip()
        # Remove opening fence (```python, ```py, ```)
        code = re.sub(r'^```(?:python|py)?\s*\n?', '', code)
        # Remove closing fence
        code = re.sub(r'\n?```\s*$', '', code)
        # Strip any remaining leading/trailing backticks or quotes
        code = code.strip('`\'"')
        # Drop lines before the first Python statement
        lines = code.split('\n')
        start = 0
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped and (
                stripped.startswith(('import ', 'from ', 'def ', 'class ',
                                    '#', 'if ', 'for ', 'while ', 'try:',
                                    'with ', 'print(', 'async '))
                or '=' in stripped
            ):
                start = i
                break
        return '\n'.join(lines[start:]).strip()

    def _safety_check(self, code: str) -> bool:
        """Static analysis to prevent destructive operations."""
        for pattern in _FORBIDDEN:
            if pattern in code:
                print(f"{Kleur.ROOD}⚠️  SAFETY ALERT: Forbidden pattern "
                      f"'{pattern}' detected.{Kleur.RESET}")
                return False
        return True

    def _syntax_check(self, code: str) -> bool:
        """Verify the generated code is valid Python."""
        try:
            ast.parse(code)
            return True
        except SyntaxError as e:
            print(f"{Kleur.ROOD}⚠️  Syntax error: {e}{Kleur.RESET}")
            return False

    def _save_script(self, filename: str, code: str, description: str):
        path = self.skills_dir / filename
        with open(path, "w", encoding="utf-8") as f:
            f.write(code)

        # Update Registry
        reg = self._load_registry()
        words = description.lower().split()
        reg[filename] = {
            "description": description,
            "created_at": datetime.now().isoformat(),
            "keywords": words[:5],
        }
        with open(self.registry_path, "w", encoding="utf-8") as f:
            json.dump(reg, f, indent=2, ensure_ascii=False)

        print(f"{Kleur.GROEN}🛠️  Skill '{filename}' saved to registry.{Kleur.RESET}")

    def _run_script(self, filename: str) -> str:
        path = str(self.skills_dir / filename)
        try:
            result = subprocess.run(
                ["python", path],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                self._mark_skill_status(filename, error=None)
                return result.stdout or "(no output)"
            error_msg = result.stderr
            self._mark_skill_status(filename, error=error_msg[:500])
            return f"Script error:\n{error_msg}"
        except subprocess.TimeoutExpired:
            self._mark_skill_status(filename, error="timeout")
            return "❌ Script timed out (30s limit)."
        except Exception as e:
            self._mark_skill_status(filename, error=str(e))
            return f"❌ Execution error: {e}"

    def _publish_event(self, event_type, data: dict):
        """Publiceer event op NeuralBus als beschikbaar."""
        if self._bus and event_type:
            try:
                self._bus.publish(event_type, data, bron="artificer")
            except Exception as e:
                logger.debug("NeuralBus publish error: %s", e)

    def _mark_skill_status(self, filename: str, error: Optional[str]):
        """Record success/failure in the registry so stale skills get re-forged."""
        reg = self._load_registry()
        if filename in reg:
            reg[filename]["last_error"] = error
            try:
                with open(self.registry_path, "w", encoding="utf-8") as f:
                    json.dump(reg, f, indent=2, ensure_ascii=False)
            except (IOError, OSError):
                pass

    def _load_registry(self) -> Dict:
        try:
            with open(self.registry_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}

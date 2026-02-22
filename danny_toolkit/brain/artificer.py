import ast
import json
import logging
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict

logger = logging.getLogger(__name__)

from groq import AsyncGroq
from danny_toolkit.core.config import Config
from danny_toolkit.core.utils import Kleur

try:
    from danny_toolkit.core.key_manager import get_key_manager
    HAS_KEY_MANAGER = True
except ImportError:
    HAS_KEY_MANAGER = False

HAS_BUS = False
try:
    from danny_toolkit.core.neural_bus import get_bus, EventTypes
    HAS_BUS = True
except ImportError:
    pass


# Forbidden patterns — static analysis blocklist
_FORBIDDEN = [
    "shutil.rmtree", "os.remove", "os.rmdir", "os.unlink",
    "subprocess.call", "subprocess.Popen", "subprocess.run", "os.system",
    "format_drive", "rm -rf", "deltree",
    "__import__", "eval(", "exec(",
    "importlib", "getattr(os", "setattr(",
    "open('/", 'open("/', "open('C:", 'open("C:',
]

try:
    from danny_toolkit.core.output_sanitizer import sanitize_for_llm
    HAS_SANITIZER = True
except ImportError:
    HAS_SANITIZER = False

try:
    from danny_toolkit.core.env_bootstrap import VENV_PYTHON as _VENV_PYTHON
    from danny_toolkit.core.env_bootstrap import get_subprocess_env as _get_env
    _sandbox_env = lambda: _get_env(test_mode=False)  # noqa: E731
except ImportError:
    _VENV_PYTHON = sys.executable
    def _sandbox_env():
        env = os.environ.copy()
        env.update({"CUDA_VISIBLE_DEVICES": "-1",
                     "ANONYMIZED_TELEMETRY": "False", "PYTHONIOENCODING": "utf-8"})
        return env

try:
    from danny_toolkit.core.sandbox import get_sandbox
    HAS_SANDBOX = True
except ImportError:
    HAS_SANDBOX = False

try:
    from danny_toolkit.core.groq_retry import groq_call_async
    HAS_RETRY = True
except ImportError:
    HAS_RETRY = False

try:
    from danny_toolkit.core.document_forge import DocumentForge
    HAS_FORGE = True
except ImportError:
    HAS_FORGE = False


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
        self.workspace_dir = Config.BASE_DIR / "danny_toolkit" / "workspace"
        if HAS_KEY_MANAGER:
            km = get_key_manager()
            self.client = km.create_async_client("Artificer") or AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))
        else:
            self.client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))
        self.model = Config.LLM_MODEL
        self._bus = get_bus() if HAS_BUS else None
        self._ensure_setup()

    def _ensure_setup(self):
        self.skills_dir.mkdir(parents=True, exist_ok=True)
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
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

        # Pre-flight: check of alle imports beschikbaar zijn
        missing = self._preflight_imports(code)
        if missing:
            print(f"{Kleur.ROOD}⚠️  Missing modules: {', '.join(missing)}{Kleur.RESET}")
            return f"❌ Artificer: ontbrekende modules: {', '.join(missing)}. Installeer met: pip install {' '.join(missing)}"

        # Save & Register (incrementing skill number)
        skill_name = f"skill_{len(registry) + 1}.py"
        self._save_script(skill_name, code, request)

        # 5. Execute
        print(f"{Kleur.GROEN}🚀 Artificer: Executing...{Kleur.RESET}")
        result = self._run_script(skill_name)

        # 6. Promoveer .md bestanden uit workspace naar DocumentForge staging
        self._promoveer_workspace_docs(skill_name)

        # Publish forge success
        self._publish_event(EventTypes.FORGE_SUCCESS if HAS_BUS else None, {
            "skill": skill_name,
            "request": request[:200],
        })

        return result

    async def forge_document(self, onderwerp: str, categorie: str = "research",
                             tags: Optional[list] = None) -> str:
        """Genereer een RAG-document via LLM en sla op via DocumentForge.

        In tegenstelling tot execute_task() (dat scripts smeedt en uitvoert),
        genereert forge_document() direct een markdown-document en routeert
        het door de Shadow Airlock pipeline.

        Agenten mogen NIET meer met open() naar de RAG-map schrijven.
        Alle documenten gaan via DocumentForge → staging → airlock → productie.

        Args:
            onderwerp: Het onderwerp/de opdracht voor het document.
            categorie: DocumentForge categorie (research, rapport, etc.).
            tags: Optionele tags voor metadata.

        Returns:
            Statusmelding met pad naar staging-bestand.
        """
        if not HAS_FORGE:
            return "❌ DocumentForge niet beschikbaar (import mislukt)."

        print(f"{Kleur.GEEL}📄 Artificer: Document smeden over "
              f"'{onderwerp[:60]}'...{Kleur.RESET}")

        # LLM-prompt: genereer alleen de body (DocumentForge maakt de header)
        prompt = (
            f"Schrijf een beknopt, feitelijk document over: {onderwerp}\n\n"
            "REGELS:\n"
            "- Schrijf in het Nederlands.\n"
            "- Gebruik Markdown-opmaak (headers, lijsten, code blocks).\n"
            "- Focus op feiten, namen, cijfers en technische details.\n"
            "- Geen YAML-frontmatter toevoegen (wordt automatisch gegenereerd).\n"
            "- Geen inleidende tekst als 'Hier is het document'.\n"
            "- Begin direct met een ## header.\n"
            "- Maximaal 500 woorden.\n"
        )

        # Genereer via LLM
        ruwe_tekst = None
        if HAS_RETRY:
            ruwe_tekst = await groq_call_async(
                self.client, "Artificer", self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4,
            )
        else:
            try:
                chat = await self.client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt}],
                    model=self.model,
                    temperature=0.4,
                )
                ruwe_tekst = chat.choices[0].message.content
            except Exception as e:
                print(f"{Kleur.ROOD}📄 Forge document fout: {e}{Kleur.RESET}")
                return f"❌ LLM-generatie mislukt: {e}"

        if not ruwe_tekst or not ruwe_tekst.strip():
            return "❌ LLM genereerde lege tekst."

        # Bestandsnaam afleiden uit onderwerp
        naam = onderwerp.lower().strip()[:60]
        naam = "".join(c if c.isalnum() or c in " _-" else "_" for c in naam)
        naam = "_".join(naam.split()) + ".md"

        # Opslaan via DocumentForge → staging (shadow_rag)
        try:
            pad = DocumentForge.sla_document_op(
                bestandsnaam=naam,
                ruwe_tekst=ruwe_tekst,
                auteur="Artificer",
                categorie=categorie,
                tags=tags or [],
            )
            print(f"{Kleur.GROEN}📄 Document gesmeed: {pad.name}{Kleur.RESET}")
            print(f"   → Staging: {pad}")
            print(f"   → ShadowAirlock zal valideren en promoveren naar productie.")

            # NeuralBus event
            self._publish_event(EventTypes.FORGE_SUCCESS if HAS_BUS else None, {
                "type": "document",
                "bestand": pad.name,
                "onderwerp": onderwerp[:200],
                "categorie": categorie,
            })

            return f"📄 Document '{pad.name}' opgeslagen in staging. ShadowAirlock zal valideren."

        except Exception as e:
            print(f"{Kleur.ROOD}📄 DocumentForge opslag mislukt: {e}{Kleur.RESET}")
            return f"❌ DocumentForge fout: {e}"

    def _promoveer_workspace_docs(self, skill_name: str):
        """Scan workspace voor .md bestanden en routeer via DocumentForge.

        Na script-executie kunnen er .md bestanden in de workspace staan
        die door het script zijn gegenereerd. Deze worden automatisch
        opgepakt en via de Shadow Airlock pipeline gerouteerd.

        Args:
            skill_name: Naam van het uitgevoerde script (voor tags).
        """
        if not HAS_FORGE:
            return

        try:
            for pad in self.workspace_dir.iterdir():
                if not pad.is_file():
                    continue
                if pad.suffix.lower() not in (".md", ".txt"):
                    continue
                if pad.stat().st_size == 0:
                    continue

                # Lees de inhoud
                with open(pad, "r", encoding="utf-8") as f:
                    inhoud = f.read()

                # Routeer door DocumentForge
                staging_pad = DocumentForge.sla_document_op(
                    bestandsnaam=pad.name,
                    ruwe_tekst=inhoud,
                    auteur="Artificer",
                    categorie="intern",
                    tags=["forge", skill_name.replace(".py", "")],
                )

                # Verwijder origineel uit workspace (nu veilig in staging)
                pad.unlink()

                print(f"{Kleur.CYAAN}   📋 Workspace doc → staging: "
                      f"{staging_pad.name}{Kleur.RESET}")
                logger.info(
                    "Artificer: workspace doc '%s' gerouteerd via DocumentForge",
                    pad.name,
                )
        except Exception as e:
            logger.debug("Workspace doc promotie fout: %s", e)

    async def _write_script(self, task: str) -> Optional[str]:
        workspace = str(self.workspace_dir).replace("\\", "/")
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
            f"- FILE I/O: If you need to read or write files, you may use open(). "
            f"ALL file output MUST go to the workspace directory: {workspace}/ — "
            f"use os.path.join(\"{workspace}\", \"filename\") for every file path. "
            f"NEVER write files outside this directory.\n"
            "- FORBIDDEN: os.remove, os.rmdir, shutil.rmtree, subprocess, "
            "os.system, eval(), exec(), __import__.\n"
            "- Return ONLY raw Python source code.\n"
            "- Do NOT wrap in markdown fences (no ```python, no ```).\n"
            "- Do NOT add explanations, comments about the code, or text before/after.\n"
            "- The very first character must be a Python statement (import, def, etc)."
        )
        if HAS_RETRY:
            raw = await groq_call_async(
                self.client, "Artificer", self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4,
            )
            return self._clean_generated_code(raw) if raw else None
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

    @staticmethod
    def _preflight_imports(code: str) -> list[str]:
        """
        Pre-flight check: extract imports en controleer beschikbaarheid.
        Returns lijst van ontbrekende modules.
        """
        import importlib
        missing = []
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return missing

        stdlib_always = {
            "os", "sys", "json", "re", "math", "time", "datetime",
            "pathlib", "collections", "itertools", "functools",
            "hashlib", "random", "string", "io", "csv", "logging",
            "threading", "subprocess", "ast", "textwrap", "shutil",
            "typing", "dataclasses", "enum", "abc", "copy",
            "urllib", "http", "socket", "email", "html",
        }

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    mod = alias.name.split(".")[0]
                    if mod in stdlib_always:
                        continue
                    try:
                        importlib.import_module(mod)
                    except ImportError:
                        missing.append(mod)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    mod = node.module.split(".")[0]
                    if mod in stdlib_always:
                        continue
                    try:
                        importlib.import_module(mod)
                    except ImportError:
                        missing.append(mod)
        return missing

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
        workspace = str(self.workspace_dir)

        if HAS_SANDBOX:
            sandbox = get_sandbox()
            result = sandbox.run_script(path, workspace, timeout=30)

            # Publiceer sandbox event
            self._publish_event(
                EventTypes.SANDBOX_EXECUTION if HAS_BUS else None,
                {
                    "skill": filename,
                    "sandbox_type": type(sandbox).__name__,
                    "returncode": result.returncode,
                    "timed_out": result.timed_out,
                },
            )

            if result.timed_out:
                self._mark_skill_status(filename, error="timeout")
                return "❌ Script timed out (30s limit)."
            if result.returncode == 0:
                self._mark_skill_status(filename, error=None)
                output = result.stdout or "(no output)"
                if HAS_SANITIZER:
                    output = sanitize_for_llm(output, max_chars=3000)
                return output
            self._mark_skill_status(filename, error=result.stderr[:500])
            return f"Script error:\n{result.stderr}"

        # Fallback: direct subprocess.run (als sandbox import faalt)
        try:
            result = subprocess.run(
                [_VENV_PYTHON, path],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=workspace,
                env=_sandbox_env(),
            )
            if result.returncode == 0:
                self._mark_skill_status(filename, error=None)
                output = result.stdout or "(no output)"
                if HAS_SANITIZER:
                    output = sanitize_for_llm(output, max_chars=3000)
                return output
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

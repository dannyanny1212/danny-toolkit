"""
Titanium Sandbox v7.1 — Geharde isolatie-laag voor Artificer code-executie.

Security gates (defense-in-depth):
  Gate -1: HARDWARE SEAL — VM detection + CPU fingerprint (runtime_hardware_guard)
            VM's krijgen ZERO access. Alleen Danny's fysieke machine is geautoriseerd.
  Gate 0:  Caller verification — alleen SwarmEngine/Artificer/DevOpsDaemon
  Gate 1:  AST import guard — 30+ verboden modules (network, keyboard, system)
  Gate 2:  AST builtin guard — input(), exec(), eval(), breakpoint() geblokkeerd
  Gate 3:  sys.stdin/stdout/stderr access geblokkeerd
  Gate 4:  Credential stripping uit subprocess environment
  Gate 5:  stdin=DEVNULL — runtime keyboard input geblokkeerd
  Gate 6:  Output sanitizer — 3-laags credential scrub (GhostWriter + Shadow)

Alleen LocalSandbox. Docker is permanent verwijderd (escape-risico).
VM's worden gedetecteerd en permanent geblokkeerd — geen uitzonderingen.

Gebruik:
    from danny_toolkit.core.sandbox import get_sandbox
    sandbox = get_sandbox()
    result = sandbox.run_script(script_path, workspace, timeout=5)
"""

from __future__ import annotations

import logging
import os
import re
import subprocess
import sys
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Centralized env bootstrap — single source of truth
from danny_toolkit.core.env_bootstrap import VENV_PYTHON as _VENV_PYTHON
from danny_toolkit.core.env_bootstrap import get_subprocess_env


# ═══════════════════════════════════════════════════════════════
#  GATE 4: CREDENTIAL STRIPPING
# ═══════════════════════════════════════════════════════════════

def _sandbox_env() -> dict:
    """Bouw een schone env dict — strip ALLE credentials.

    Het sandbox-proces mag NOOIT toegang hebben tot API keys,
    tokens, of andere gevoelige environment variabelen.
    """
    env = get_subprocess_env(test_mode=False)
    _STRIP_PREFIXES = (
        "GROQ_API_KEY", "ANTHROPIC_API_KEY", "VOYAGE_API_KEY",
        "NVIDIA_NIM_API_KEY", "HF_TOKEN", "GOOGLE_API_KEY",
        "FASTAPI_SECRET_KEY", "OMEGA_BUS_SIGNING_KEY",
        "GITHUB_TOKEN", "GH_TOKEN", "AWS_", "AZURE_",
        "OPENAI_API_KEY", "TELEGRAM_BOT_TOKEN",
    )
    for key in list(env.keys()):
        for prefix in _STRIP_PREFIXES:
            if key.startswith(prefix):
                del env[key]
                break
    return env


# Titanium timeout (5s hard limit)
TITANIUM_TIMEOUT = 5

# ═══════════════════════════════════════════════════════════════
#  GATE 1: FORBIDDEN IMPORTS (30+ modules)
# ═══════════════════════════════════════════════════════════════

TITANIUM_FORBIDDEN_IMPORTS = frozenset({
    # Process/system escape
    "subprocess", "ctypes", "multiprocessing",
    "shutil", "signal", "importlib",
    "pty", "fcntl", "termios",
    # Network escape
    "socket", "http", "urllib", "ftplib",
    "smtplib", "telnetlib", "xmlrpc",
    "requests", "paramiko", "aiohttp",
    # Browser/GUI escape
    "webbrowser", "antigravity",
    "pyautogui", "keyboard", "mouse",
    "pynput", "pyperclip", "clipboard",
    # Windows API escape
    "win32api", "win32com", "wmi",
    # Project internals
    "danny_toolkit", "chromadb", "dotenv",
})

# ═══════════════════════════════════════════════════════════════
#  GATE 2: FORBIDDEN BUILTINS
# ═══════════════════════════════════════════════════════════════

TITANIUM_FORBIDDEN_BUILTINS = frozenset({
    "input", "breakpoint", "exec", "eval", "compile", "__import__",
})

# ═══════════════════════════════════════════════════════════════
#  GATE 0: CALLER VERIFICATION
# ═══════════════════════════════════════════════════════════════

_AUTHORIZED_CALLERS = frozenset({
    "swarm_engine",
    "danny_toolkit.core.sandbox",
    "danny_toolkit.brain.artificer",
    "danny_toolkit.brain.devops_daemon",
})

_INTRUSION_LOG: list[dict] = []


def _verify_caller() -> bool:
    """Verificeer dat de aanroeper een geautoriseerd Swarm-component is.

    Bij ongeautoriseerde toegang: volledig forensisch rapport naar
    logger, CorticalStack, en NeuralBus.
    """
    import inspect
    import time as _time

    stack = inspect.stack()
    caller_chain = []

    for frame_info in stack[2:]:
        module = frame_info.frame.f_globals.get("__name__", "")
        filename = os.path.basename(frame_info.filename)
        lineno = frame_info.lineno
        func = frame_info.function
        caller_chain.append({
            "module": module,
            "file": filename,
            "line": lineno,
            "function": func,
        })
        basename = filename.replace(".py", "")
        if module in _AUTHORIZED_CALLERS or basename in {"swarm_engine", "artificer", "devops_daemon"}:
            return True

    # === INTRUSION DETECTED ===
    pid = os.getpid()
    ppid = os.getppid()
    user = os.environ.get("USERNAME", os.environ.get("USER", "unknown"))
    cwd = os.getcwd()

    proc_name = "unknown"
    parent_name = "unknown"
    try:
        import psutil
        proc_name = psutil.Process(pid).name()
        parent_name = psutil.Process(ppid).name()
    except Exception as _ps_err:
        logger.debug("psutil intrusion info: %s", _ps_err)

    intrusion = {
        "timestamp": _time.strftime("%Y-%m-%dT%H:%M:%S"),
        "severity": "CRITICAL",
        "pid": pid,
        "ppid": ppid,
        "process": proc_name,
        "parent_process": parent_name,
        "user": user,
        "cwd": cwd,
        "caller_chain": caller_chain[:10],
        "top_caller": caller_chain[0] if caller_chain else {},
        "entry_point": caller_chain[-1] if caller_chain else {},
    }

    _INTRUSION_LOG.append(intrusion)
    if len(_INTRUSION_LOG) > 50:
        _INTRUSION_LOG.pop(0)

    top = intrusion["top_caller"]
    entry = intrusion["entry_point"]
    logger.warning(
        "INTRUSION DETECTED | pid=%d | user=%s | process=%s | "
        "caller=%s:%s()@L%s | entry=%s:%s()@L%s | parent=%s",
        pid, user, proc_name,
        top.get("file", "?"), top.get("function", "?"), top.get("line", "?"),
        entry.get("file", "?"), entry.get("function", "?"), entry.get("line", "?"),
        parent_name,
    )

    # CorticalStack (fire-and-forget)
    try:
        from danny_toolkit.brain.cortical_stack import get_cortical_stack
        get_cortical_stack().log_event(
            actor="titanium_gate",
            action="intrusion_blocked",
            details=intrusion,
            source="sandbox_security",
        )
    except Exception as _cs_err:
        logger.debug("CorticalStack intrusion log: %s", _cs_err)

    # NeuralBus (fire-and-forget)
    try:
        from danny_toolkit.core.neural_bus import get_bus, EventTypes
        get_bus().publish(
            EventTypes.ERROR_CLASSIFIED,
            {
                "type": "sandbox_intrusion",
                "severity": "CRITICAL",
                "caller": f"{top.get('module', '?')}:{top.get('function', '?')}",
                "pid": pid,
            },
            bron="titanium_gate",
        )
    except Exception as _nb_err:
        logger.debug("NeuralBus intrusion publish: %s", _nb_err)

    return False


def get_intrusion_log() -> list[dict]:
    """Haal forensische intrusion log op."""
    return list(_INTRUSION_LOG)


# ═══════════════════════════════════════════════════════════════
#  GATE 1+2+3: AST IMPORT & BUILTIN GUARD
# ═══════════════════════════════════════════════════════════════

def titanium_import_guard(script_path: str) -> str | None:
    """Pre-flight AST scan op verboden imports, builtins, en I/O access.

    Returns:
        None als veilig, anders foutmelding string.
    """
    try:
        import ast as _ast
        with open(script_path, "r", encoding="utf-8") as f:
            source = f.read()
        tree = _ast.parse(source)

        for node in _ast.walk(tree):
            # Gate 1: verboden imports
            if isinstance(node, _ast.Import):
                for alias in node.names:
                    root_mod = alias.name.split(".")[0]
                    if root_mod in TITANIUM_FORBIDDEN_IMPORTS:
                        return f"Titanium Guard: verboden import '{alias.name}'"
            elif isinstance(node, _ast.ImportFrom):
                if node.module:
                    root_mod = node.module.split(".")[0]
                    if root_mod in TITANIUM_FORBIDDEN_IMPORTS:
                        return f"Titanium Guard: verboden import '{node.module}'"

            # Gate 2: verboden builtins
            if isinstance(node, _ast.Call):
                if isinstance(node.func, _ast.Name):
                    if node.func.id in TITANIUM_FORBIDDEN_BUILTINS:
                        return (
                            f"Titanium Guard: verboden builtin '{node.func.id}()' "
                            f"— sandbox mag niet met buitenwereld communiceren"
                        )

            # Gate 3: sys.stdin/stdout/stderr access
            if isinstance(node, _ast.Attribute):
                if (node.attr in ("stdin", "stdout", "stderr")
                        and isinstance(node.value, _ast.Name)
                        and node.value.id == "sys"):
                    return (
                        f"Titanium Guard: verboden sys.{node.attr} access "
                        f"— sandbox is volledig geisoleerd"
                    )

    except SyntaxError as e:
        return f"Titanium Guard: syntax error in script — {e}"
    except Exception as e:
        logger.debug("Titanium import guard scan failed: %s", e)
    return None


# ═══════════════════════════════════════════════════════════════
#  GATE 6: OUTPUT SANITIZER (3-laags credential scrub)
# ═══════════════════════════════════════════════════════════════

_CREDENTIAL_PATTERNS = re.compile(
    r"(?:"
    r"gsk_[A-Za-z0-9]{20,}"           # Groq API keys
    r"|sk-[A-Za-z0-9\-]{20,}"         # Anthropic/OpenAI keys
    r"|pa-[A-Za-z0-9]{20,}"           # Voyage keys
    r"|nvapi-[A-Za-z0-9]{20,}"        # NVIDIA NIM keys
    r"|hf_[A-Za-z0-9]{20,}"           # HuggingFace tokens
    r"|ghp_[A-Za-z0-9]{20,}"          # GitHub PAT
    r"|xoxb-[A-Za-z0-9\-]{20,}"       # Slack bot tokens
    r"|AKIA[A-Z0-9]{12,}"             # AWS access keys
    r"|(?:Bearer|Authorization:)\s+[A-Za-z0-9+/]{40,}={0,2}"  # Bearer tokens
    r"|(?:api[_-]?key|secret|token|password|credential)"
    r"\s*[:=]\s*['\"]?[A-Za-z0-9_]{32,}['\"]?"  # key=value (min 32, excludes UUIDs)
    r")",
    re.IGNORECASE,
)

_SHADOW_QUARANTINE_LOG: list[dict] = []


def _ghostwriter_scrub(text: str) -> tuple[str, int]:
    """Laag 1+2: Detecteer en vervang credential patronen."""
    if not text:
        return text, 0

    count = 0

    def _redact(match: re.Match) -> str:
        nonlocal count
        count += 1
        return "[CREDENTIAL_REDACTED]"

    scrubbed = _CREDENTIAL_PATTERNS.sub(_redact, text)
    return scrubbed, count


def _shadow_quarantine(original: str, scrubbed: str, redactions: int, script_path: str) -> None:
    """Laag 3: Audit log (metadata only, GEEN credentials opgeslagen)."""
    if redactions == 0:
        return

    import time as _time
    entry = {
        "timestamp": _time.strftime("%Y-%m-%dT%H:%M:%S"),
        "script": os.path.basename(script_path) if script_path else "unknown",
        "redactions": redactions,
        "output_length": len(original),
        "scrubbed_length": len(scrubbed),
        "severity": "CRITICAL" if redactions >= 3 else "WARNING",
    }
    _SHADOW_QUARANTINE_LOG.append(entry)
    if len(_SHADOW_QUARANTINE_LOG) > 100:
        _SHADOW_QUARANTINE_LOG.pop(0)

    logger.warning(
        "SHADOW QUARANTINE: %d credential(s) redacted from sandbox output [%s]",
        redactions, entry["script"],
    )


def sanitize_sandbox_output(result: SandboxResult, script_path: str = "") -> SandboxResult:
    """3-laags output sanitizer: DuplicationGuard -> GhostWriter -> Shadow."""
    stdout_clean, stdout_count = _ghostwriter_scrub(result.stdout)
    stderr_clean, stderr_count = _ghostwriter_scrub(result.stderr)

    total = stdout_count + stderr_count
    if total > 0:
        _shadow_quarantine(
            result.stdout + result.stderr,
            stdout_clean + stderr_clean,
            total,
            script_path,
        )

    return SandboxResult(
        stdout=stdout_clean,
        stderr=stderr_clean,
        returncode=result.returncode,
        timed_out=result.timed_out,
    )


def get_quarantine_log() -> list[dict]:
    """Haal Shadow Quarantine audit log op."""
    return list(_SHADOW_QUARANTINE_LOG)


# ═══════════════════════════════════════════════════════════════
#  SANDBOX RESULT
# ═══════════════════════════════════════════════════════════════

@dataclass
class SandboxResult:
    """Resultaat van een sandbox executie."""
    stdout: str
    stderr: str
    returncode: int
    timed_out: bool


# ═══════════════════════════════════════════════════════════════
#  LOCAL SANDBOX — Enige toegestane executie-omgeving
# ═══════════════════════════════════════════════════════════════

class LocalSandbox:
    """Titanium LocalSandbox v7.1 — 8-gate geharde subprocess executie.

    Gates:
     -1: HARDWARE SEAL (VM detection + CPU fingerprint — VM = ZERO access)
      0: Caller verification (stack inspection)
      1: Forbidden import scan (AST)
      2: Forbidden builtin scan (AST)
      3: sys.stdin/stdout/stderr block (AST)
      4: Credential stripping (env)
      5: stdin=DEVNULL (runtime)
      6: Output sanitizer (credential scrub)
    """

    def run_script(
        self,
        script_path: str,
        workspace: str,
        timeout: int = TITANIUM_TIMEOUT,
    ) -> SandboxResult:
        """Voer een script uit met 8-gate Titanium isolatie."""
        # Gate -1: HARDWARE SEAL — VM's krijgen ZERO access
        try:
            from danny_toolkit.core.hardware_anchor import runtime_hardware_guard
            hw_ok, hw_reason = runtime_hardware_guard(agent_name="sandbox")
            if not hw_ok:
                logger.critical("SANDBOX HARDWARE SEAL DENIED: %s", hw_reason)
                return SandboxResult(
                    stdout="",
                    stderr=f"Titanium Gate -1: HARDWARE DENIED | {hw_reason}",
                    returncode=-1,
                    timed_out=False,
                )
        except ImportError:
            logger.critical("hardware_anchor module niet gevonden — sandbox LOCKED")
            return SandboxResult(
                stdout="",
                stderr="Titanium Gate -1: hardware_anchor MISSING — sandbox locked",
                returncode=-1,
                timed_out=False,
            )

        # Gate 0: caller verification
        if not _verify_caller():
            intruder = _INTRUSION_LOG[-1] if _INTRUSION_LOG else {}
            top = intruder.get("top_caller", {})
            return SandboxResult(
                stdout="",
                stderr=(
                    f"Titanium Gate: INTRUSION BLOCKED | "
                    f"caller={top.get('module', '?')}:{top.get('function', '?')}() "
                    f"@ {top.get('file', '?')}:L{top.get('line', '?')} | "
                    f"pid={intruder.get('pid', '?')} | "
                    f"process={intruder.get('process', '?')} | "
                    f"parent={intruder.get('parent_process', '?')}"
                ),
                returncode=-1,
                timed_out=False,
            )

        # Gates 1+2+3: AST pre-flight scan
        guard_result = titanium_import_guard(script_path)
        if guard_result is not None:
            return SandboxResult(
                stdout="",
                stderr=guard_result,
                returncode=-1,
                timed_out=False,
            )

        # Gate 5: process isolation flags
        creation_flags = 0
        if os.name == "nt":
            creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP

        try:
            result = subprocess.run(
                [_VENV_PYTHON, script_path],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=workspace,
                env=_sandbox_env(),              # Gate 4: credential stripping
                creationflags=creation_flags,
                stdin=subprocess.DEVNULL,         # Gate 5: stdin blocked
            )
            raw = SandboxResult(
                stdout=result.stdout or "",
                stderr=result.stderr or "",
                returncode=result.returncode,
                timed_out=False,
            )
            return sanitize_sandbox_output(raw, script_path)  # Gate 6
        except subprocess.TimeoutExpired as exc:
            if hasattr(exc, "args") and exc.args:
                try:
                    import signal
                    os.kill(exc.args[0] if isinstance(exc.args[0], int) else 0, signal.SIGTERM)
                except (OSError, ProcessLookupError) as _kill_err:
                    logger.debug("Process kill cleanup: %s", _kill_err)
            return SandboxResult(
                stdout="",
                stderr=f"Titanium timeout ({timeout}s limit).",
                returncode=-1,
                timed_out=True,
            )
        except Exception as e:
            return SandboxResult(
                stdout="",
                stderr=str(e),
                returncode=-1,
                timed_out=False,
            )


# ═══════════════════════════════════════════════════════════════
#  SINGLETON FACTORY
# ═══════════════════════════════════════════════════════════════

_sandbox = None
_sandbox_lock = __import__("threading").Lock()


def get_sandbox() -> LocalSandbox:
    """Factory singleton — retourneert ALTIJD LocalSandbox (Titanium hardened)."""
    global _sandbox
    if _sandbox is not None:
        return _sandbox

    with _sandbox_lock:
        if _sandbox is not None:
            return _sandbox
        logger.info("Sandbox: LocalSandbox v7.0 (Titanium 7-gate) — alleen lokale agents.")
        _sandbox = LocalSandbox()
        return _sandbox

"""Sandboxed tools voor SwarmEngine agents.

File Scribe: bestanden schrijven ALLEEN in danny_toolkit/sandbox/.
Terminal Exec: read-only commando's draaien in de sandbox.

Agents importeren deze tools om veilig met het bestandssysteem
en terminal te interacteren. Pad-traversal en gevaarlijke
commando's worden gehard geblokkeerd.
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

from danny_toolkit.core.config import Config

logger = logging.getLogger(__name__)

# ── Sandbox directory (hardcoded, NIET configureerbaar) ──────────
SANDBOX_DIR: Path = Config.BASE_DIR / "danny_toolkit" / "sandbox"

# Allowed extensions for File Scribe
_ALLOWED_EXTENSIONS = {
    ".py", ".txt", ".md", ".json", ".csv", ".yaml", ".yml",
    ".toml", ".xml", ".html", ".css", ".js", ".log",
}

# Whitelisted commands for Terminal Exec
_ALLOWED_COMMANDS = {
    "pytest", "python", "ls", "dir", "cat", "head", "tail",
    "wc", "find", "type", "echo", "pip",
}

# Blocked substrings in arguments (prevent escape)
_BLOCKED_ARGS = [
    "..", "~", "$", "`", "|", ";", "&&", "||", ">", "<",
    "rm ", "del ", "rmdir", "shutil", "format",
    "powershell", "cmd.exe", "bash -c",
]

# Venv python for subprocess
try:
    from danny_toolkit.core.env_bootstrap import (
        VENV_PYTHON as _VENV_PYTHON,
    )
    from danny_toolkit.core.env_bootstrap import (
        get_subprocess_env as _get_env,
    )
except ImportError:
    _VENV_PYTHON = sys.executable

    def _get_env(**_kwargs) -> Optional[dict]:
        return None


def _ensure_sandbox() -> Path:
    """Maak sandbox directory aan als die niet bestaat."""
    SANDBOX_DIR.mkdir(parents=True, exist_ok=True)
    return SANDBOX_DIR


def _validate_sandbox_path(filepath: str) -> Path:
    """Valideer dat het pad BINNEN de sandbox valt.

    Raises:
        PermissionError: Als het pad buiten de sandbox wijst.
        ValueError: Als de extensie niet is toegestaan.
    """
    _ensure_sandbox()
    target = Path(filepath).resolve()
    sandbox_resolved = SANDBOX_DIR.resolve()

    # Path traversal check — moet BINNEN sandbox vallen
    if not str(target).startswith(str(sandbox_resolved)):
        raise PermissionError(
            f"SANDBOX VIOLATION: pad '{target}' valt buiten "
            f"sandbox '{sandbox_resolved}'. Schrijven geblokkeerd."
        )

    # Extension check
    if target.suffix and target.suffix.lower() not in _ALLOWED_EXTENSIONS:
        raise ValueError(
            f"Extensie '{target.suffix}' niet toegestaan. "
            f"Allowed: {sorted(_ALLOWED_EXTENSIONS)}"
        )

    return target


# ═══════════════════════════════════════════════════════════════════
# FILE SCRIBE — veilig bestanden schrijven in de sandbox
# ═══════════════════════════════════════════════════════════════════


def file_scribe_write(
    filename: str,
    content: str,
    subdirectory: str = "",
) -> str:
    """Schrijf een bestand naar de sandbox.

    Args:
        filename: Bestandsnaam (bijv. "output.py").
        content: Inhoud van het bestand.
        subdirectory: Optionele subdirectory binnen sandbox.

    Returns:
        Bevestigingsbericht met het volledige pad.

    Raises:
        PermissionError: Als het pad buiten de sandbox valt.
        ValueError: Als de extensie niet is toegestaan.
    """
    sandbox = _ensure_sandbox()

    if subdirectory:
        target_dir = sandbox / subdirectory
        # Validate subdirectory doesn't escape
        if ".." in subdirectory:
            raise PermissionError(
                "SANDBOX VIOLATION: '..' niet toegestaan in subdirectory."
            )
        target_dir.mkdir(parents=True, exist_ok=True)
    else:
        target_dir = sandbox

    full_path = target_dir / filename
    validated = _validate_sandbox_path(str(full_path))

    validated.write_text(content, encoding="utf-8")
    logger.info("File Scribe: %s geschreven (%d bytes)", validated, len(content))

    return f"Bestand geschreven: {validated} ({len(content)} bytes)"


def file_scribe_read(filename: str, subdirectory: str = "") -> str:
    """Lees een bestand uit de sandbox.

    Args:
        filename: Bestandsnaam.
        subdirectory: Optionele subdirectory binnen sandbox.

    Returns:
        Inhoud van het bestand.
    """
    sandbox = _ensure_sandbox()
    target = sandbox / subdirectory / filename if subdirectory else sandbox / filename
    validated = _validate_sandbox_path(str(target))

    if not validated.exists():
        return f"Bestand niet gevonden: {validated}"

    return validated.read_text(encoding="utf-8")


def file_scribe_list(subdirectory: str = "") -> str:
    """Lijst bestanden in de sandbox.

    Args:
        subdirectory: Optionele subdirectory binnen sandbox.

    Returns:
        Lijst van bestanden met grootte.
    """
    sandbox = _ensure_sandbox()
    target = sandbox / subdirectory if subdirectory else sandbox
    validated = _validate_sandbox_path(str(target))

    if not validated.is_dir():
        return f"Directory niet gevonden: {validated}"

    entries = []
    for item in sorted(validated.iterdir()):
        if item.is_file():
            size = item.stat().st_size
            entries.append(f"  {item.name} ({size} bytes)")
        elif item.is_dir():
            entries.append(f"  {item.name}/")

    if not entries:
        return "Sandbox is leeg."

    return f"Sandbox ({validated}):\n" + "\n".join(entries)


# ═══════════════════════════════════════════════════════════════════
# TERMINAL EXEC — veilig commando's draaien in de sandbox
# ═══════════════════════════════════════════════════════════════════


def terminal_exec(
    command: str,
    timeout: int = 30,
) -> str:
    """Voer een commando uit in de sandbox directory.

    Alleen whitelisted commando's zijn toegestaan. Output wordt
    afgekapt op 5000 tekens.

    Args:
        command: Het commando (bijv. "pytest test_x.py" of "ls").
        timeout: Maximale uitvoertijd in seconden.

    Returns:
        Gecombineerde stdout + stderr output.

    Raises:
        PermissionError: Als het commando niet is toegestaan.
    """
    sandbox = _ensure_sandbox()

    # Parse command
    parts = command.strip().split()
    if not parts:
        return "Leeg commando."

    base_cmd = parts[0].lower()

    # Whitelist check
    if base_cmd not in _ALLOWED_COMMANDS:
        raise PermissionError(
            f"SANDBOX VIOLATION: commando '{base_cmd}' niet toegestaan. "
            f"Allowed: {sorted(_ALLOWED_COMMANDS)}"
        )

    # Argument sanitization
    full_cmd = " ".join(parts)
    for blocked in _BLOCKED_ARGS:
        if blocked in full_cmd:
            raise PermissionError(
                f"SANDBOX VIOLATION: geblokkeerd patroon '{blocked}' "
                f"in commando '{full_cmd}'."
            )

    # Build actual command
    if base_cmd == "python":
        # Force venv python, script must be in sandbox
        if len(parts) > 1:
            script = parts[1]
            script_path = (sandbox / script).resolve()
            if not str(script_path).startswith(str(sandbox.resolve())):
                raise PermissionError(
                    f"SANDBOX VIOLATION: script '{script}' "
                    f"valt buiten sandbox."
                )
            cmd_list = [str(_VENV_PYTHON), str(script_path)] + parts[2:]
        else:
            return "Usage: python <script.py> [args]"

    elif base_cmd == "pytest":
        cmd_list = [str(_VENV_PYTHON), "-m", "pytest"] + parts[1:]

    elif base_cmd == "pip":
        # Only allow pip list/show/freeze (read-only)
        if len(parts) < 2 or parts[1] not in ("list", "show", "freeze"):
            raise PermissionError(
                "SANDBOX VIOLATION: alleen 'pip list/show/freeze' toegestaan."
            )
        cmd_list = [str(_VENV_PYTHON), "-m", "pip"] + parts[1:]

    else:
        cmd_list = parts

    # Execute
    env = _get_env(test_mode=False) if callable(_get_env) else None
    try:
        result = subprocess.run(
            cmd_list,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(sandbox),
            env=env,
        )

        output = ""
        if result.stdout:
            output += result.stdout
        if result.stderr:
            if output:
                output += "\n--- STDERR ---\n"
            output += result.stderr

        if not output:
            output = "(geen output)"

        # Truncate
        if len(output) > 5000:
            output = output[:5000] + "\n... (afgekapt op 5000 tekens)"

        exit_info = f"\n[exit code: {result.returncode}]"
        logger.info(
            "Terminal Exec: '%s' → exit %d (%d bytes output)",
            command, result.returncode, len(output),
        )
        return output + exit_info

    except subprocess.TimeoutExpired:
        logger.warning("Terminal Exec: timeout na %ds voor '%s'", timeout, command)
        return f"Timeout na {timeout}s voor commando '{command}'."
    except FileNotFoundError:
        return f"Commando '{base_cmd}' niet gevonden op dit systeem."
    except Exception as e:
        logger.error("Terminal Exec error: %s", e)
        return f"Uitvoeringsfout: {e}"

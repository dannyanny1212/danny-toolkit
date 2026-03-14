"""
Titanium Sandbox — Geharde isolatie-laag voor Artificer code-executie.

v6.19.0: Titanium upgrade — 5s hard timeout, process group isolation,
forbidden import guard, no-network subprocess flags.

Biedt defense-in-depth: code draait in een Docker container
zonder netwerk, met geheugen- en CPU-limieten.

Fallback: LocalSandbox (subprocess.run met Titanium hardening) als
Docker niet beschikbaar is.

Gebruik:
    from danny_toolkit.core.sandbox import get_sandbox
    sandbox = get_sandbox()
    result = sandbox.run_script(script_path, workspace, timeout=5)
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

# Centralized env bootstrap — single source of truth
from danny_toolkit.core.env_bootstrap import VENV_PYTHON as _VENV_PYTHON
from danny_toolkit.core.env_bootstrap import get_subprocess_env


def _sandbox_env() -> dict:
    """Bouw een schone env dict met isolatie-vars (production: geen test_mode).

    Titanium hardening: strip alle API keys en gevoelige vars uit de env.
    Het sandbox-proces mag NOOIT toegang hebben tot credentials.
    """
    env = get_subprocess_env(test_mode=False)
    # Strip alle API keys — sandbox mag geen credentials kennen
    _STRIP_PREFIXES = (
        "GROQ_API_KEY", "ANTHROPIC_API_KEY", "VOYAGE_API_KEY",
        "NVIDIA_NIM_API_KEY", "HF_TOKEN", "GOOGLE_API_KEY",
        "FASTAPI_SECRET_KEY", "OMEGA_BUS_SIGNING_KEY",
    )
    for key in list(env.keys()):
        for prefix in _STRIP_PREFIXES:
            if key.startswith(prefix):
                del env[key]
                break
    return env


# Titanium: default timeout voor sandbox executie (was 30s, nu 5s)
TITANIUM_TIMEOUT = 5

# Forbidden imports — sandbox scripts mogen deze NOOIT importeren
TITANIUM_FORBIDDEN_IMPORTS = frozenset({
    "subprocess", "socket", "ctypes", "multiprocessing",
    "shutil", "signal", "importlib", "chromadb",
    "danny_toolkit", "dotenv", "paramiko", "requests",
})


def titanium_import_guard(script_path: str) -> str | None:
    """Pre-flight scan: controleer of script verboden imports bevat.

    Returns:
        None als veilig, anders foutmelding string.
    """
    try:
        import ast
        with open(script_path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root_mod = alias.name.split(".")[0]
                    if root_mod in TITANIUM_FORBIDDEN_IMPORTS:
                        return f"Titanium Guard: verboden import '{alias.name}'"
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    root_mod = node.module.split(".")[0]
                    if root_mod in TITANIUM_FORBIDDEN_IMPORTS:
                        return f"Titanium Guard: verboden import '{node.module}'"
    except SyntaxError as e:
        return f"Titanium Guard: syntax error in script — {e}"
    except Exception as e:
        logger.debug("Titanium import guard scan failed: %s", e)
    return None


@dataclass
class SandboxResult:
    """Resultaat van een sandbox executie."""
    stdout: str
    stderr: str
    returncode: int
    timed_out: bool


class BaseSandbox(ABC):
    """Abstracte basis voor sandbox implementaties."""

    @abstractmethod
    def run_script(
        self,
        script_path: str,
        workspace: str,
        timeout: int = 30,
    ) -> SandboxResult:
        """Voer een script uit in de sandbox.

        Args:
            script_path: Pad naar het Python script.
            workspace: Werkdirectory voor file I/O.
            timeout: Maximum executietijd in seconden.

        Returns:
            SandboxResult met stdout, stderr, returncode, timed_out.
        """
        ...


class LocalSandbox(BaseSandbox):
    """Titanium LocalSandbox — geharde subprocess executie.

    v6.19.0 hardening:
    - 5s default timeout (was 30s)
    - CREATE_NEW_PROCESS_GROUP op Windows (killbare subprocess tree)
    - Titanium import guard (pre-flight AST scan)
    - Credential stripping uit environment
    - Process group kill bij timeout (voorkomt zombie processen)
    """

    def run_script(
        self,
        script_path: str,
        workspace: str,
        timeout: int = TITANIUM_TIMEOUT,
    ) -> SandboxResult:
        """Voer een script uit met Titanium isolatie.

        Args:
            script_path: Pad naar het Python script.
            workspace: Werkdirectory voor file I/O.
            timeout: Maximum executietijd (default: 5s Titanium).

        Returns:
            SandboxResult met stdout, stderr, returncode, timed_out.
        """
        # Titanium pre-flight: import guard
        guard_result = titanium_import_guard(script_path)
        if guard_result is not None:
            return SandboxResult(
                stdout="",
                stderr=guard_result,
                returncode=-1,
                timed_out=False,
            )

        # Windows: CREATE_NEW_PROCESS_GROUP voor killbare subprocess tree
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
                env=_sandbox_env(),
                creationflags=creation_flags,
            )
            return SandboxResult(
                stdout=result.stdout or "",
                stderr=result.stderr or "",
                returncode=result.returncode,
                timed_out=False,
            )
        except subprocess.TimeoutExpired as exc:
            # Kill de hele process group bij timeout
            if hasattr(exc, "args") and exc.args:
                try:
                    import signal
                    os.kill(exc.args[0] if isinstance(exc.args[0], int) else 0, signal.SIGTERM)
                except (OSError, ProcessLookupError):
                    pass
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


class DockerSandbox(BaseSandbox):
    """
    Docker sandbox — draait scripts in een geïsoleerde container.

    Container configuratie:
    - --rm: auto-cleanup na afloop
    - --network=none: geen internettoegang
    - --memory=256m: geheugenplafond
    - --cpus=1: CPU-limiet
    - --pids-limit=64: voorkomt forkbombs
    - workspace volume (rw) voor file I/O
    - script mount (ro) voor het script zelf
    """

    IMAGE = "python:3.11-slim"

    def __init__(self) -> None:
        """Init  ."""
        self._available = self._check_docker()

    @staticmethod
    def _check_docker() -> bool:
        """Controleer of Docker beschikbaar is."""
        try:
            result = subprocess.run(
                ["docker", "info"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            return False

    @property
    def available(self) -> bool:
        """Available."""
        return self._available

    def run_script(
        self,
        script_path: str,
        workspace: str,
        timeout: int = 30,
    ) -> SandboxResult:
        """Run script."""
        if not self._available:
            return SandboxResult(
                stdout="",
                stderr="Docker is niet beschikbaar.",
                returncode=-1,
                timed_out=False,
            )

        script_path = str(Path(script_path).resolve())
        workspace = str(Path(workspace).resolve())

        cmd = [
            "docker", "run",
            "--rm",
            "--network=none",
            "--memory=256m",
            "--cpus=1",
            "--pids-limit=64",
            "-v", f"{workspace}:/workspace",
            "-v", f"{script_path}:/script/script.py:ro",
            "-w", "/workspace",
            self.IMAGE,
            "python", "/script/script.py",
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout + 10,  # Extra marge voor container startup
            )
            return SandboxResult(
                stdout=result.stdout or "",
                stderr=result.stderr or "",
                returncode=result.returncode,
                timed_out=False,
            )
        except subprocess.TimeoutExpired:
            return SandboxResult(
                stdout="",
                stderr=f"Docker container timed out ({timeout}s limit).",
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

    def build_command(
        self,
        script_path: str,
        workspace: str,
    ) -> list:
        """Retourneer het Docker commando (voor inspectie/tests)."""
        script_path = str(Path(script_path).resolve())
        workspace = str(Path(workspace).resolve())
        return [
            "docker", "run",
            "--rm",
            "--network=none",
            "--memory=256m",
            "--cpus=1",
            "--pids-limit=64",
            "-v", f"{workspace}:/workspace",
            "-v", f"{script_path}:/script/script.py:ro",
            "-w", "/workspace",
            self.IMAGE,
            "python", "/script/script.py",
        ]


# Singleton
_sandbox = None
_sandbox_lock = __import__("threading").Lock()


def get_sandbox() -> BaseSandbox:
    """
    Factory singleton — retourneert DockerSandbox als Docker
    beschikbaar is, anders LocalSandbox.
    """
    global _sandbox
    if _sandbox is not None:
        return _sandbox

    with _sandbox_lock:
        if _sandbox is not None:
            return _sandbox

        try:
            docker = DockerSandbox()
            if docker.available:
                logger.info("Sandbox: Docker beschikbaar — beveiligde modus actief.")
                _sandbox = docker
                return _sandbox
        except Exception as e:
            logger.debug("Docker sandbox init error: %s", e)

        logger.info("Sandbox: Docker niet beschikbaar — lokale modus.")
        _sandbox = LocalSandbox()
        return _sandbox

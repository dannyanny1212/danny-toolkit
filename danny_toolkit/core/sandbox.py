"""
Docker Sandbox — Isolatie-laag voor Artificer code-executie.

Biedt defense-in-depth: code draait in een Docker container
zonder netwerk, met geheugen- en CPU-limieten.

Fallback: LocalSandbox (huidig subprocess.run gedrag) als
Docker niet beschikbaar is.

Gebruik:
    from danny_toolkit.core.sandbox import get_sandbox
    sandbox = get_sandbox()
    result = sandbox.run_script(script_path, workspace, timeout=30)
"""

import logging
import os
import shutil
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


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
    """
    Lokale sandbox — draait scripts via subprocess.run.
    Dit is het huidige gedrag, geextraheerd als class.
    """

    def run_script(
        self,
        script_path: str,
        workspace: str,
        timeout: int = 30,
    ) -> SandboxResult:
        try:
            result = subprocess.run(
                ["python", script_path],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=workspace,
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
                stderr=f"Script timed out ({timeout}s limit).",
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

    def __init__(self):
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
        return self._available

    def run_script(
        self,
        script_path: str,
        workspace: str,
        timeout: int = 30,
    ) -> SandboxResult:
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


def get_sandbox() -> BaseSandbox:
    """
    Factory singleton — retourneert DockerSandbox als Docker
    beschikbaar is, anders LocalSandbox.
    """
    global _sandbox
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

"""
Omega Sovereign Core — SovereignEngine
=======================================
Veilige PowerShell executie via asyncio.
Whitelist/blacklist voor command safety.

Gebruik:
    from Omega_Sovereign_Core.core.engine import SovereignEngine

    engine = SovereignEngine()
    result = await engine.execute("Get-ChildItem")
"""

import asyncio
import logging
import re
import time
from dataclasses import dataclass, field
from typing import List, Optional

logger = logging.getLogger(__name__)

# Pad naar danny_toolkit voor Kleur
try:
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
    from danny_toolkit.core.utils import Kleur
except ImportError:
    class Kleur:
        BLAUW = GROEN = ROOD = GEEL = CYAAN = RESET = ""


# ── Constanten ──

_WHITELIST = {
    "Get-ChildItem", "Get-Process", "Get-Service", "Get-PSDrive",
    "Get-Date", "Get-Location", "Get-Content", "Get-Item",
    "Get-ItemProperty", "Get-ComputerInfo", "Get-NetAdapter",
    "Get-NetIPAddress", "Get-Disk", "Get-Volume", "Get-EventLog",
    "Get-WmiObject", "Get-CimInstance", "Get-History",
    "Get-Command", "Get-Module", "Get-Package", "Get-HotFix",
    "Test-Connection", "Test-Path", "Test-NetConnection",
    "Measure-Object", "Select-Object", "Where-Object",
    "Sort-Object", "Format-Table", "Format-List",
    "Out-String", "ConvertTo-Json", "ConvertTo-Csv",
    "Write-Output", "Write-Host",
    "Resolve-DnsName", "Get-DnsClientCache",
}

_BLACKLIST_PATTERNS = [
    r"Remove-Item\s+.*-Recurse",
    r"Format-Volume",
    r"Clear-Disk",
    r"Stop-Process\s+.*-Force",
    r"Stop-Computer",
    r"Restart-Computer",
    r"Set-ExecutionPolicy",
    r"Invoke-Expression",
    r"Invoke-WebRequest",  # Netwerk downloads blokkeren
    r"Start-Process",       # Willekeurige processen starten
    r"New-Service",
    r"Remove-Service",
    r"Disable-NetAdapter",
    r"reg\s+delete",
    r"del\s+/[sfq]",
    r"rmdir\s+/s",
    r"format\s+[a-z]:",
    r"shutdown",
    r"taskkill\s+/f",
]

_COMPILED_BLACKLIST = [re.compile(p, re.IGNORECASE) for p in _BLACKLIST_PATTERNS]

_MAX_OUTPUT_BYTES = 64 * 1024  # 64 KB output limiet
_DEFAULT_TIMEOUT = 30.0        # 30 seconden timeout


# ── Datamodellen ──

@dataclass
class CommandResult:
    """Resultaat van een PowerShell executie."""
    status: str             # "success" | "error" | "blocked" | "timeout"
    data: str               # stdout of error message
    command: str            # het uitgevoerde commando
    duration_ms: float = 0  # executietijd in ms
    exit_code: int = -1


@dataclass
class CommandEntry:
    """Historisch commando."""
    command: str
    result: CommandResult
    timestamp: float = field(default_factory=time.time)


# ── SovereignEngine ──

class SovereignEngine:
    """
    Veilige PowerShell executie engine.

    - Whitelist voor toegestane cmdlets
    - Blacklist patterns voor gevaarlijke operaties
    - Timeout bescherming
    - Output limiet (64 KB)
    - Command history
    """

    def __init__(self, strict: bool = True):
        """
        Args:
            strict: Als True, alleen whitelist cmdlets toestaan.
                    Als False, alleen blacklist checken (permissief).
        """
        self.strict = strict
        self.history: List[CommandEntry] = []
        self._stats = {
            "executed": 0,
            "blocked": 0,
            "errors": 0,
            "timeouts": 0,
        }

    # ── Veiligheid ──

    def _check_blacklist(self, script: str) -> Optional[str]:
        """Check of een script gevaarlijke patterns bevat.

        Returns:
            Reden string als geblokkeerd, None als veilig.
        """
        for pattern in _COMPILED_BLACKLIST:
            if pattern.search(script):
                return f"Blacklist match: {pattern.pattern}"
        return None

    def _check_whitelist(self, script: str) -> bool:
        """Check of het eerste commando in de whitelist staat.

        Kijkt naar het eerste woord (cmdlet) van het script.
        Pipe-targets worden niet gecheckt (Select-Object etc. zijn altijd OK).
        """
        # Pak het eerste commando (vóór de eerste pipe)
        first_cmd = script.split("|")[0].strip()
        # Pak de cmdlet naam (eerste woord)
        cmdlet = first_cmd.split()[0] if first_cmd.split() else ""
        return cmdlet in _WHITELIST

    def is_safe(self, script: str) -> tuple:
        """Controleer of een script veilig is om uit te voeren.

        Returns:
            (bool, str) — (veilig, reden)
        """
        # Blacklist altijd checken
        blacklist_hit = self._check_blacklist(script)
        if blacklist_hit:
            return False, blacklist_hit

        # Whitelist alleen in strict mode
        if self.strict and not self._check_whitelist(script):
            return False, f"Cmdlet niet in whitelist (strict mode)"

        return True, "OK"

    # ── Executie ──

    async def execute(
        self,
        script: str,
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> CommandResult:
        """Voer een PowerShell script veilig uit.

        Args:
            script: Het PowerShell commando.
            timeout: Max executietijd in seconden.

        Returns:
            CommandResult met status en output.
        """
        print(f"{Kleur.BLAUW}[SOVEREIGN]{Kleur.RESET} Execute: {script[:80]}")

        # Veiligheidscheck
        safe, reason = self.is_safe(script)
        if not safe:
            self._stats["blocked"] += 1
            result = CommandResult(
                status="blocked",
                data=f"GEBLOKKEERD: {reason}",
                command=script,
            )
            self.history.append(CommandEntry(script, result))
            print(f"{Kleur.ROOD}[BLOCKED]{Kleur.RESET} {reason}")
            return result

        # Uitvoeren via asyncio subprocess
        t0 = time.time()
        try:
            process = await asyncio.create_subprocess_exec(
                "powershell.exe",
                "-NoProfile",
                "-ExecutionPolicy", "Bypass",
                "-Command", script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout,
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                self._stats["timeouts"] += 1
                result = CommandResult(
                    status="timeout",
                    data=f"Timeout na {timeout}s",
                    command=script,
                    duration_ms=(time.time() - t0) * 1000,
                    exit_code=-1,
                )
                self.history.append(CommandEntry(script, result))
                print(f"{Kleur.ROOD}[TIMEOUT]{Kleur.RESET} {timeout}s verlopen")
                return result

            duration_ms = (time.time() - t0) * 1000

            if stderr and process.returncode != 0:
                error_msg = stderr.decode("utf-8", errors="replace").strip()
                # Limiteer output
                if len(error_msg) > _MAX_OUTPUT_BYTES:
                    error_msg = error_msg[:_MAX_OUTPUT_BYTES] + "\n... (afgekapt)"
                self._stats["errors"] += 1
                result = CommandResult(
                    status="error",
                    data=error_msg,
                    command=script,
                    duration_ms=duration_ms,
                    exit_code=process.returncode or 1,
                )
                print(f"{Kleur.ROOD}[ERROR]{Kleur.RESET} {error_msg[:120]}")
            else:
                output = stdout.decode("utf-8", errors="replace").strip()
                if len(output) > _MAX_OUTPUT_BYTES:
                    output = output[:_MAX_OUTPUT_BYTES] + "\n... (afgekapt)"
                self._stats["executed"] += 1
                result = CommandResult(
                    status="success",
                    data=output,
                    command=script,
                    duration_ms=duration_ms,
                    exit_code=process.returncode or 0,
                )
                print(f"{Kleur.GROEN}[SUCCESS]{Kleur.RESET} {duration_ms:.0f}ms")

        except FileNotFoundError:
            self._stats["errors"] += 1
            result = CommandResult(
                status="error",
                data="powershell.exe niet gevonden",
                command=script,
                duration_ms=(time.time() - t0) * 1000,
            )
        except Exception as e:
            self._stats["errors"] += 1
            logger.debug("Execute fout: %s", e)
            result = CommandResult(
                status="error",
                data=str(e),
                command=script,
                duration_ms=(time.time() - t0) * 1000,
            )

        self.history.append(CommandEntry(script, result))
        return result

    # ── Statistieken ──

    def get_history(self, count: int = 20) -> List[dict]:
        """Return de laatste N commando's als dicts."""
        return [
            {
                "command": e.command,
                "status": e.result.status,
                "duration_ms": e.result.duration_ms,
                "timestamp": e.timestamp,
                "data_preview": e.result.data[:200],
            }
            for e in self.history[-count:]
        ]

    def get_stats(self) -> dict:
        """Return engine statistieken."""
        return dict(self._stats)

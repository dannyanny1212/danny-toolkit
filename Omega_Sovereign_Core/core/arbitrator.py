"""
Omega Sovereign Core — SovereignArbitrator
==========================================
Vertaalt high-level goals naar PowerShell commando's.
Fase 1: hardcoded mapping. Fase 60: LLM schrijft scripts.

Gebruik:
    from Omega_Sovereign_Core.core.arbitrator import SovereignArbitrator

    arb = SovereignArbitrator()
    result = await arb.handle_goal("bestanden lijst")
"""

import logging
import time
from typing import Dict, List, Optional

from Omega_Sovereign_Core.core.engine import SovereignEngine, CommandResult

logger = logging.getLogger(__name__)

try:
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
    from danny_toolkit.core.utils import Kleur
except ImportError:
    class Kleur:
        BLAUW = GROEN = ROOD = GEEL = CYAAN = RESET = ""


# ── Goal → Command Mapping ──

_GOAL_MAP: Dict[str, dict] = {
    # Bestandsbeheer
    "bestanden lijst": {
        "script": "Get-ChildItem | Select-Object Name, Length, LastWriteTime",
        "beschrijving": "Toon bestanden in huidige map",
    },
    "bestanden details": {
        "script": "Get-ChildItem -Recurse | Measure-Object -Property Length -Sum -Average",
        "beschrijving": "Statistieken over bestanden",
    },
    "grote bestanden": {
        "script": "Get-ChildItem -Recurse | Sort-Object Length -Descending | Select-Object -First 10 Name, @{N='MB';E={[math]::Round($_.Length/1MB,2)}}",
        "beschrijving": "Top 10 grootste bestanden",
    },

    # Processen
    "processen": {
        "script": "Get-Process | Sort-Object CPU -Descending | Select-Object -First 15 Name, CPU, WorkingSet64, Id",
        "beschrijving": "Top 15 processen op CPU",
    },
    "geheugen gebruik": {
        "script": "Get-Process | Sort-Object WorkingSet64 -Descending | Select-Object -First 10 Name, @{N='MB';E={[math]::Round($_.WorkingSet64/1MB,1)}}, Id",
        "beschrijving": "Top 10 processen op geheugen",
    },

    # Services
    "services": {
        "script": "Get-Service | Where-Object {$_.Status -eq 'Running'} | Select-Object Name, DisplayName, Status | Sort-Object DisplayName",
        "beschrijving": "Draaiende services",
    },
    "gestopte services": {
        "script": "Get-Service | Where-Object {$_.Status -eq 'Stopped'} | Select-Object -First 20 Name, DisplayName",
        "beschrijving": "Gestopte services (eerste 20)",
    },

    # Schijf / Opslag
    "schijfruimte": {
        "script": "Get-PSDrive -PSProvider FileSystem | Select-Object Name, @{N='Used_GB';E={[math]::Round($_.Used/1GB,1)}}, @{N='Free_GB';E={[math]::Round($_.Free/1GB,1)}}, @{N='Total_GB';E={[math]::Round(($_.Used+$_.Free)/1GB,1)}}",
        "beschrijving": "Schijfruimte per drive",
    },
    "volumes": {
        "script": "Get-Volume | Where-Object {$_.DriveLetter} | Select-Object DriveLetter, FileSystemLabel, @{N='Size_GB';E={[math]::Round($_.Size/1GB,1)}}, @{N='Free_GB';E={[math]::Round($_.SizeRemaining/1GB,1)}}, HealthStatus",
        "beschrijving": "Volume informatie",
    },

    # Netwerk
    "netwerk": {
        "script": "Get-NetAdapter | Where-Object {$_.Status -eq 'Up'} | Select-Object Name, InterfaceDescription, LinkSpeed, MacAddress",
        "beschrijving": "Actieve netwerkadapters",
    },
    "ip adressen": {
        "script": "Get-NetIPAddress -AddressFamily IPv4 | Where-Object {$_.IPAddress -ne '127.0.0.1'} | Select-Object InterfaceAlias, IPAddress, PrefixLength",
        "beschrijving": "IPv4 adressen",
    },
    "dns cache": {
        "script": "Get-DnsClientCache | Select-Object -First 20 Entry, Data, TimeToLive",
        "beschrijving": "DNS cache (eerste 20)",
    },
    "ping": {
        "script": "Test-Connection -ComputerName 8.8.8.8 -Count 3 | Select-Object Address, Latency, Status",
        "beschrijving": "Ping naar Google DNS",
    },

    # Systeem
    "systeem info": {
        "script": "Get-ComputerInfo | Select-Object CsName, OsName, OsVersion, CsProcessors, CsTotalPhysicalMemory, OsUptime",
        "beschrijving": "Systeeminformatie",
    },
    "uptime": {
        "script": "(Get-Date) - (Get-CimInstance Win32_OperatingSystem).LastBootUpTime | Select-Object Days, Hours, Minutes",
        "beschrijving": "Systeem uptime",
    },
    "updates": {
        "script": "Get-HotFix | Sort-Object InstalledOn -Descending | Select-Object -First 10 HotFixID, Description, InstalledOn",
        "beschrijving": "Laatste 10 Windows updates",
    },
    "events": {
        "script": "Get-EventLog -LogName System -Newest 10 | Select-Object TimeGenerated, EntryType, Source, Message",
        "beschrijving": "Laatste 10 systeem events",
    },

    # Python / Dev
    "python versie": {
        "script": "python --version; pip --version",
        "beschrijving": "Python en pip versie",
    },
    "pip lijst": {
        "script": "pip list --format=columns | Select-Object -First 30",
        "beschrijving": "Geinstalleerde pip packages (eerste 30)",
    },

    # GPU
    "gpu info": {
        "script": "Get-CimInstance Win32_VideoController | Select-Object Name, DriverVersion, @{N='VRAM_MB';E={[math]::Round($_.AdapterRAM/1MB,0)}}, Status",
        "beschrijving": "GPU informatie",
    },
}


# ── SovereignArbitrator ──

class SovereignArbitrator:
    """
    THE SOVEREIGN ARBITRATOR — Goal → OS Command Vertaler.

    Fase 1: Hardcoded mapping van Nederlandse goals naar PowerShell scripts.
    Fase 60 (toekomstig): LLM genereert de scripts autonoom.
    """

    def __init__(self, engine: SovereignEngine = None):
        self.engine = engine or SovereignEngine()
        self._stats = {
            "goals_handled": 0,
            "goals_matched": 0,
            "goals_unmatched": 0,
        }

    def get_command_map(self) -> Dict[str, str]:
        """Return alle beschikbare goal → beschrijving mappings."""
        return {
            goal: info["beschrijving"]
            for goal, info in _GOAL_MAP.items()
        }

    def match_goal(self, goal: str) -> Optional[dict]:
        """Zoek de beste match voor een goal string.

        Probeert exact match, dan substring match.

        Returns:
            Dict met 'script' en 'beschrijving', of None.
        """
        goal_lower = goal.lower().strip()

        # Exacte match
        if goal_lower in _GOAL_MAP:
            return _GOAL_MAP[goal_lower]

        # Substring match — langste match wint
        best_match = None
        best_len = 0
        for key, info in _GOAL_MAP.items():
            if key in goal_lower and len(key) > best_len:
                best_match = info
                best_len = len(key)

        return best_match

    async def handle_goal(self, goal: str) -> dict:
        """Vertaal een goal naar een PowerShell commando en voer uit.

        Args:
            goal: Nederlandse beschrijving van wat de gebruiker wil.

        Returns:
            Dict met status, data, command, en beschrijving.
        """
        self._stats["goals_handled"] += 1

        print(f"\n{Kleur.BLAUW}[ARBITRATOR]{Kleur.RESET} Goal: {goal}")

        match = self.match_goal(goal)

        if not match:
            self._stats["goals_unmatched"] += 1
            print(f"{Kleur.GEEL}[ARBITRATOR]{Kleur.RESET} Geen match gevonden")
            return {
                "status": "unmatched",
                "data": f"Geen commando gevonden voor: {goal}",
                "command": None,
                "beschrijving": None,
                "beschikbaar": list(self.get_command_map().keys()),
            }

        self._stats["goals_matched"] += 1
        print(f"{Kleur.CYAAN}[ARBITRATOR]{Kleur.RESET} Match: {match['beschrijving']}")

        result = await self.engine.execute(match["script"])

        return {
            "status": result.status,
            "data": result.data,
            "command": result.command,
            "beschrijving": match["beschrijving"],
            "duration_ms": result.duration_ms,
        }

    def get_stats(self) -> dict:
        """Return arbitrator statistieken."""
        return {
            **self._stats,
            "engine": self.engine.get_stats(),
            "beschikbare_goals": len(_GOAL_MAP),
        }

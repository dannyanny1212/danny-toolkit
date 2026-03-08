"""
WATCHTOWER — Continuous Process Monitor & Ghost Detector
=========================================================

Daemon thread die periodiek het proceslandschap scant en
verdachte activiteit detecteert:

  1. Ghost Processes: Onbekende Python/cmd processen die
     danny-toolkit bestanden benaderen
  2. RDP/Remote: Actieve remote desktop sessies
  3. Suspicious Parents: Processen met onverwachte parent chains
  4. Port Listeners: Onverwachte luisterende poorten
  5. File Watchers: Processen die /data/ of .env monitoren

Rapporteert via NeuralBus + CorticalStack. Geen automatische
actie — alleen detectie en alertering.

Start:
    from danny_toolkit.apps.watchtower import get_watchtower
    wt = get_watchtower()
    wt.start()

Stop:
    wt.stop()
"""

from __future__ import annotations

import atexit
import logging
import os
import re
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional, Set

logger = logging.getLogger(__name__)

try:
    from danny_toolkit.core.utils import Kleur
except ImportError:
    class Kleur:
        GROEN = ROOD = GEEL = CYAAN = RESET = ""

try:
    from danny_toolkit.core.config import Config
    _BASE_DIR = str(Config.BASE_DIR).lower()
    _DATA_DIR = str(Config.DATA_DIR).lower()
except ImportError:
    _BASE_DIR = str(Path(__file__).parent.parent.parent).lower()
    _DATA_DIR = str(Path(_BASE_DIR) / "data").lower()

# ── Constanten ──

_DEFAULT_INTERVAL_SEC = 60       # Scan elke 60 seconden
_MIN_INTERVAL_SEC = 10           # Minimum 10 seconden
_MAX_ALERT_HISTORY = 200         # Ring buffer grootte

# Processen die altijd veilig zijn
_SAFE_PROCESS_NAMES = frozenset({
    "python.exe", "python3.exe", "pythonw.exe", "python",
    "code.exe", "code",
    "powershell.exe", "pwsh.exe",
    "windowsterminal.exe", "wt.exe",
    "cmd.exe", "conhost.exe",
    "git.exe", "git",
    "node.exe", "npm.exe",
    "streamlit.exe", "streamlit",
    "claude.exe", "claude",
    "explorer.exe", "taskmgr.exe",
    "svchost.exe", "csrss.exe", "lsass.exe",
    "system", "system idle process",
    "wininit.exe", "winlogon.exe",
    "dwm.exe", "sihost.exe",
    "searchhost.exe", "runtimebroker.exe",
    "smartscreen.exe", "securityhealthservice.exe",
})

# Verdachte process namen (heuristiek)
_SUSPICIOUS_NAMES = frozenset({
    "mimikatz", "meterpreter", "cobalt",
    "keylogger", "stealer", "inject",
    "rat.exe", "backdoor", "rootkit",
    "nc.exe", "ncat.exe", "netcat",
})

# Poorten die NIET mogen luisteren (behalve onze eigen services)
_OUR_PORTS = frozenset({8000, 8501, 8502, 11434})  # FastAPI, Streamlit, Prism, Ollama


@dataclass
class Alert:
    """Eén Watchtower alert."""
    timestamp: str
    severity: str          # "CRITICAL", "WARNING", "INFO"
    category: str          # "ghost", "rdp", "port", "suspicious", "file_access"
    message: str
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """To dict."""
        return {
            "timestamp": self.timestamp,
            "severity": self.severity,
            "category": self.category,
            "message": self.message,
            "details": self.details,
        }


class Watchtower:
    """Continuous process monitor en ghost detector.

    Scant periodiek het proceslandschap en genereert alerts
    voor verdachte activiteit. Daemon thread — sterft
    automatisch bij proces-exit.

    Args:
        interval_sec: Scan interval in seconden (default 60).
    """

    def __init__(self, interval_sec: int = _DEFAULT_INTERVAL_SEC) -> None:
        """Init  ."""
        self._interval = max(interval_sec, _MIN_INTERVAL_SEC)
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._alerts: Deque[Alert] = deque(maxlen=_MAX_ALERT_HISTORY)
        self._known_pids: Set[int] = set()
        self._our_pid = os.getpid()
        self._stats = {
            "scans": 0,
            "alerts_total": 0,
            "alerts_critical": 0,
            "alerts_warning": 0,
            "ghosts_detected": 0,
            "rdp_detected": 0,
            "suspicious_ports": 0,
            "last_scan": None,
            "last_alert": None,
        }

        # Lazy backends
        self._bus = None
        self._stack = None
        self._backends_loaded = False

    # ── Backend Loading ──

    def _ensure_backends(self) -> None:
        """Lazy-load NeuralBus en CorticalStack."""
        if self._backends_loaded:
            return
        self._backends_loaded = True

        if os.environ.get("DANNY_TEST_MODE") == "1":
            return

        try:
            from danny_toolkit.core.neural_bus import get_bus
            self._bus = get_bus()
        except ImportError:
            logger.debug("Watchtower: NeuralBus niet beschikbaar")

        try:
            from danny_toolkit.brain.cortical_stack import get_cortical_stack
            self._stack = get_cortical_stack()
        except ImportError:
            logger.debug("Watchtower: CorticalStack niet beschikbaar")

    # ── Alert Helpers ──

    def _emit_alert(self, severity: str, category: str,
                    message: str, details: Optional[Dict] = None) -> None:
        """Maak alert aan en publiceer naar bus + stack."""
        alert = Alert(
            timestamp=datetime.now().isoformat(),
            severity=severity,
            category=category,
            message=message,
            details=details or {},
        )

        self._alerts.append(alert)
        self._stats["alerts_total"] += 1
        self._stats["last_alert"] = alert.timestamp

        if severity == "CRITICAL":
            self._stats["alerts_critical"] += 1
        elif severity == "WARNING":
            self._stats["alerts_warning"] += 1

        logger.warning(
            "Watchtower [%s] %s: %s", severity, category, message
        )

        self._ensure_backends()

        # NeuralBus
        if self._bus:
            try:
                from danny_toolkit.core.neural_bus import EventTypes
                self._bus.publish(
                    EventTypes.SYSTEM_EVENT,
                    {
                        "type": "watchtower_alert",
                        "severity": severity,
                        "category": category,
                        "message": message,
                        **alert.details,
                    },
                    bron="watchtower",
                )
            except Exception as e:
                logger.debug("Watchtower bus publish: %s", e)

        # CorticalStack
        if self._stack:
            try:
                self._stack.log_event(
                    actor="watchtower",
                    action=f"alert_{category}",
                    details=alert.to_dict(),
                    source="watchtower",
                )
            except Exception as e:
                logger.debug("Watchtower cortical log: %s", e)

    # ── Scan Modules ──

    def _scan_rdp(self) -> None:
        """Detecteer actieve RDP/remote sessies."""
        session = os.environ.get("SESSIONNAME", "")
        if session.upper().startswith("RDP"):
            self._stats["rdp_detected"] += 1
            self._emit_alert(
                "CRITICAL", "rdp",
                f"RDP sessie gedetecteerd: {session}",
                {"session_name": session},
            )

    def _scan_processes(self) -> None:
        """Scan proceslijst voor ghosts en verdachte processen."""
        try:
            import psutil
        except ImportError:
            logger.debug("Watchtower: psutil niet beschikbaar")
            return

        new_pids: Set[int] = set()
        toolkit_path = _BASE_DIR.replace("\\", "/")

        for proc in psutil.process_iter(
            attrs=["pid", "name", "cmdline", "ppid", "create_time"]
        ):
            try:
                info = proc.info
                pid = info["pid"]
                name = (info["name"] or "").lower()
                cmdline = info["cmdline"] or []
                cmdline_str = " ".join(cmdline).lower().replace("\\", "/")

                new_pids.add(pid)

                # Skip ons eigen proces en children
                if pid == self._our_pid:
                    continue

                # Check 1: Verdachte procesnamen
                for susp in _SUSPICIOUS_NAMES:
                    if susp in name:
                        self._emit_alert(
                            "CRITICAL", "suspicious",
                            f"Verdacht proces: {name} (PID {pid})",
                            {"pid": pid, "name": name,
                             "cmdline": cmdline_str[:300]},
                        )

                # Check 2: Ghost Python processen
                # Python processen die danny-toolkit referenties bevatten
                # maar niet door ons gestart zijn
                if "python" in name and toolkit_path in cmdline_str:
                    if pid not in self._known_pids and pid != self._our_pid:
                        # Nieuw Python proces dat onze code raakt
                        ppid = info.get("ppid", 0)
                        # Check of het parent ons kent
                        try:
                            parent = psutil.Process(ppid)
                            parent_name = parent.name().lower()
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            parent_name = "unknown"

                        # Veilige parents: onze eigen shell/IDE
                        safe_parents = {
                            "python.exe", "python", "code.exe",
                            "powershell.exe", "pwsh.exe", "cmd.exe",
                            "wt.exe", "windowsterminal.exe",
                            "conhost.exe", "claude.exe",
                            "bash.exe", "streamlit.exe",
                            "streamlit", "bash",
                        }
                        if parent_name not in safe_parents:
                            self._stats["ghosts_detected"] += 1
                            self._emit_alert(
                                "WARNING", "ghost",
                                f"Ghost Python proces: PID {pid}"
                                f" (parent: {parent_name}/{ppid})",
                                {
                                    "pid": pid,
                                    "ppid": ppid,
                                    "parent_name": parent_name,
                                    "cmdline": cmdline_str[:300],
                                },
                            )

                # Check 3: Processen die .env of data/ benaderen
                if (".env" in cmdline_str and toolkit_path in cmdline_str
                        and pid != self._our_pid):
                    self._emit_alert(
                        "CRITICAL", "file_access",
                        f"Proces leest .env: {name} (PID {pid})",
                        {"pid": pid, "name": name,
                         "cmdline": cmdline_str[:300]},
                    )

            except (psutil.NoSuchProcess, psutil.AccessDenied,
                    psutil.ZombieProcess):
                continue

        self._known_pids = new_pids

    def _scan_ports(self) -> None:
        """Detecteer onverwachte luisterende poorten."""
        try:
            import psutil
        except ImportError:
            return

        try:
            for conn in psutil.net_connections(kind="tcp"):
                if conn.status == "LISTEN":
                    port = conn.laddr.port
                    # Skip bekende OS-poorten en onze services
                    if port in _OUR_PORTS or port > 49152:
                        continue
                    # Skip standaard Windows services
                    if port in {135, 139, 445, 5040, 7680}:
                        continue

                    pid = conn.pid
                    try:
                        proc = psutil.Process(pid)
                        name = proc.name().lower()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        name = "unknown"

                    # Bekende veilige luisteraars
                    safe_listeners = {
                        "svchost.exe", "system", "lsass.exe",
                        "spoolsv.exe", "wininit.exe",
                        "searchhost.exe", "node.exe",
                        "python.exe", "python3.exe",
                        # Bekende desktop applicaties
                        "steam.exe", "steamwebhelper.exe",
                        "battle.net.exe", "ollama.exe",
                        "onedrive.exe",
                        "onedrive.sync.service.exe",
                        "msi.centralserver.exe",
                        "msi.terminalserver.exe",
                    }
                    if name not in safe_listeners:
                        self._stats["suspicious_ports"] += 1
                        self._emit_alert(
                            "WARNING", "port",
                            f"Onverwachte listener: {name}"
                            f" op poort {port} (PID {pid})",
                            {"pid": pid, "name": name, "port": port},
                        )
        except (psutil.AccessDenied, OSError) as e:
            logger.debug("Watchtower port scan: %s", e)

    # ── Main Scan Cycle ──

    def _scan_cycle(self) -> Dict[str, Any]:
        """Eén volledige scan cycle.

        Returns:
            Dict met scan resultaten.
        """
        t0 = time.time()
        alerts_before = self._stats["alerts_total"]

        self._scan_rdp()
        self._scan_processes()
        self._scan_ports()

        elapsed_ms = (time.time() - t0) * 1000
        new_alerts = self._stats["alerts_total"] - alerts_before
        self._stats["scans"] += 1
        self._stats["last_scan"] = datetime.now().isoformat()

        return {
            "timestamp": self._stats["last_scan"],
            "elapsed_ms": round(elapsed_ms, 1),
            "new_alerts": new_alerts,
            "total_alerts": self._stats["alerts_total"],
        }

    # ── Thread Loop ──

    def _loop(self) -> None:
        """Daemon thread main loop."""
        logger.info(
            "Watchtower gestart (interval=%ds)", self._interval
        )
        try:
            print(
                f"{Kleur.CYAAN}[Watchtower] actief"
                f" (scan elke {self._interval}s){Kleur.RESET}",
                flush=True,
            )
        except UnicodeEncodeError:
            logger.debug("Suppressed error")

        # Eerste scan onmiddellijk
        try:
            result = self._scan_cycle()
            if result["new_alerts"] > 0:
                logger.warning(
                    "Watchtower initial scan: %d alerts",
                    result["new_alerts"],
                )
        except Exception as e:
            logger.error("Watchtower initial scan fout: %s", e)

        while not self._stop_event.is_set():
            if self._stop_event.wait(timeout=self._interval):
                break

            try:
                self._scan_cycle()
            except Exception as e:
                logger.error("Watchtower scan cycle fout: %s", e)

        logger.info(
            "Watchtower gestopt na %d scans (%d alerts)",
            self._stats["scans"], self._stats["alerts_total"],
        )

    # ── Public API ──

    def start(self) -> None:
        """Start de Watchtower daemon thread."""
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                logger.info("Watchtower draait al")
                return

            self._stop_event.clear()
            self._thread = threading.Thread(
                target=self._loop,
                name="Watchtower",
                daemon=True,
            )
            self._thread.start()

    def stop(self) -> None:
        """Stop de daemon thread (graceful)."""
        with self._lock:
            if self._thread is None or not self._thread.is_alive():
                return

            self._stop_event.set()
            self._thread.join(timeout=5)
            self._thread = None

    def force_scan(self) -> Dict[str, Any]:
        """Voer onmiddellijk een scan uit (handmatig).

        Returns:
            Dict met scan resultaten.
        """
        return self._scan_cycle()

    def get_alerts(self, count: int = 50) -> List[Dict[str, Any]]:
        """Recente alerts (nieuwste eerst).

        Args:
            count: Maximaal aantal alerts.

        Returns:
            Lijst van alert dicts.
        """
        alerts = list(self._alerts)
        alerts.reverse()
        return [a.to_dict() for a in alerts[:count]]

    def statistieken(self) -> Dict[str, Any]:
        """Huidige Watchtower statistieken.

        Returns:
            Dict met scans, alerts, running status.
        """
        return {
            **self._stats,
            "interval_sec": self._interval,
            "running": self.running,
            "known_pids": len(self._known_pids),
            "alert_buffer_size": len(self._alerts),
        }

    @property
    def running(self) -> bool:
        """Of de daemon thread draait."""
        return self._thread is not None and self._thread.is_alive()


# ── Singleton ──

_instance: Optional[Watchtower] = None
_singleton_lock = threading.Lock()


def get_watchtower(interval_sec: int = _DEFAULT_INTERVAL_SEC) -> Watchtower:
    """Thread-safe singleton factory.

    Args:
        interval_sec: Scan interval (alleen bij eerste aanroep).

    Returns:
        Watchtower singleton.
    """
    global _instance
    if _instance is not None:
        return _instance
    with _singleton_lock:
        if _instance is None:
            _instance = Watchtower(interval_sec=interval_sec)
    return _instance

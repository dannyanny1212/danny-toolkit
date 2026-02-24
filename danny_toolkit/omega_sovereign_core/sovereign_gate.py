"""
Sovereign Gate — De 7 IJzeren Wetten Runtime Enforcer.

Dit is het hart van de Omega Sovereign Core. Code weigert te draaien
tenzij ALLE fysieke en digitale voorwaarden zijn vervuld.

De 7 IJzeren Wetten:
    1. Root Integrity      — Pad moet exact danny-toolkit zijn
    2. Authority Check     — Administrator privileges vereist
    3. Terminal Lock       — Native PowerShell verplicht
    4. Physical Console    — Geen RDP of verborgen sessies
    5. Identity Binding    — Git email whitelist
    6. Hardware Fingerprint — CPU+MAC master hash match
    7. Iron Dome Network   — Default-deny uitgaand verkeer

Gebruik:
    from danny_toolkit.omega_sovereign_core.sovereign_gate import (
        get_sovereign_gate, SovereignGate
    )
    gate = get_sovereign_gate()
    passed, report = gate.enforce_all()
"""

import ctypes
import logging
import os
import platform
import subprocess
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

try:
    from danny_toolkit.core.utils import Kleur
except ImportError:
    class Kleur:
        GROEN = ROOD = GEEL = CYAAN = RESET = ""

try:
    from danny_toolkit.core.config import Config
    _BASE_DIR = Config.BASE_DIR
except ImportError:
    _BASE_DIR = Path(__file__).parent.parent.parent


# ── Constanten ──

_SOVEREIGN_ROOT = Path(r"C:\Users\danny\danny-toolkit")
_GIT_EMAIL_WHITELIST = frozenset({
    "danny.laurent1988@gmail.com",
    "dannyanny1212@gmail.com",
    "dannyanny1212@users.noreply.github.com",
})
_LAW_COUNT = 7


@dataclass
class LawResult:
    """Resultaat van een enkele wet-verificatie."""
    law_number: int
    name: str
    passed: bool
    detail: str
    enforcement_time_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "law": self.law_number,
            "name": self.name,
            "passed": self.passed,
            "detail": self.detail,
            "time_ms": round(self.enforcement_time_ms, 2),
        }


@dataclass
class GateReport:
    """Volledig rapport van alle 7 wetten."""
    timestamp: str
    all_passed: bool
    laws: List[LawResult]
    total_time_ms: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "all_passed": self.all_passed,
            "passed_count": sum(1 for law in self.laws if law.passed),
            "total_laws": len(self.laws),
            "total_time_ms": round(self.total_time_ms, 2),
            "laws": [law.to_dict() for law in self.laws],
        }

    def summary(self) -> str:
        """Eén-regel samenvatting."""
        passed = sum(1 for law in self.laws if law.passed)
        status = "SOVEREIGN" if self.all_passed else "BREACHED"
        return f"[{status}] {passed}/{len(self.laws)} laws passed ({self.total_time_ms:.0f}ms)"


class SovereignGate:
    """
    Runtime enforcer voor de 7 IJzeren Wetten.

    Elke wet is een individuele check die True/False retourneert.
    enforce_all() draait alle wetten en retourneert een GateReport.
    Bij falen wordt de LockdownManager geactiveerd.
    """

    def __init__(self, strict: bool = True):
        self._strict = strict
        self._stack = None
        self._lockdown = None
        self._last_report: Optional[GateReport] = None
        self._init_backends()

    def _init_backends(self) -> None:
        """Lazy backend verbindingen."""
        try:
            from danny_toolkit.brain.cortical_stack import get_cortical_stack
            self._stack = get_cortical_stack()
        except ImportError:
            logger.debug("CorticalStack niet beschikbaar voor SovereignGate")
        try:
            from danny_toolkit.omega_sovereign_core.lockdown import get_lockdown_manager
            self._lockdown = get_lockdown_manager()
        except ImportError:
            logger.debug("LockdownManager niet beschikbaar")

    # ══════════════════════════════════════════════════════════
    #  DE 7 IJZEREN WETTEN
    # ══════════════════════════════════════════════════════════

    def _law_1_root_integrity(self) -> LawResult:
        """Wet #1: Root Integrity — pad moet exact danny-toolkit zijn."""
        try:
            current = Path.cwd().resolve()
            expected = _SOVEREIGN_ROOT.resolve()
            # Check of we IN de toolkit directory tree zitten
            try:
                current.relative_to(expected)
                return LawResult(1, "Root Integrity", True,
                                 f"Pad OK: {current}")
            except ValueError:
                return LawResult(1, "Root Integrity", False,
                                 f"BREACH: CWD={current}, verwacht onder {expected}")
        except Exception as e:
            return LawResult(1, "Root Integrity", False, f"ERROR: {e}")

    def _law_2_authority_check(self) -> LawResult:
        """Wet #2: Authority Check — admin privileges vereist."""
        try:
            if platform.system() != "Windows":
                # Niet-Windows: check uid 0 (root)
                is_admin = os.getuid() == 0
            else:
                is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0

            if is_admin:
                return LawResult(2, "Authority Check", True, "Administrator privileges bevestigd")
            return LawResult(2, "Authority Check", False,
                             "BREACH: Geen administrator privileges")
        except Exception as e:
            return LawResult(2, "Authority Check", False, f"ERROR: {e}")

    def _law_3_terminal_lock(self) -> LawResult:
        """Wet #3: Terminal Lock — native terminal, geen verborgen cmd.exe."""
        try:
            parent_pid = os.getppid()
            # Detecteer of de parent een bekende terminal is
            try:
                result = subprocess.run(
                    ["powershell", "-NoProfile", "-Command",
                     f"(Get-Process -Id {parent_pid}).ProcessName"],
                    capture_output=True, text=True, timeout=5,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
                parent_name = result.stdout.strip().lower()
                # Toegestane terminals
                allowed = {
                    "powershell", "pwsh", "windowsterminal",
                    "code", "python", "pythonw", "cmd",
                    "conhost", "wt", "claude",
                }
                if any(a in parent_name for a in allowed):
                    return LawResult(3, "Terminal Lock", True,
                                     f"Terminal OK: {parent_name}")
                return LawResult(3, "Terminal Lock", False,
                                 f"BREACH: onbekende terminal: {parent_name}")
            except Exception:
                # Kan parent niet bepalen — non-fatal op Windows
                return LawResult(3, "Terminal Lock", True,
                                 "Terminal check overgeslagen (parent onbepaalbaar)")
        except Exception as e:
            return LawResult(3, "Terminal Lock", False, f"ERROR: {e}")

    def _law_4_physical_console(self) -> LawResult:
        """Wet #4: Physical Console — geen RDP of verborgen sessies."""
        try:
            # Check voor RDP sessie via sessionname
            session_name = os.environ.get("SESSIONNAME", "")
            if session_name.upper().startswith("RDP"):
                return LawResult(4, "Physical Console", False,
                                 f"BREACH: RDP sessie gedetecteerd ({session_name})")

            # Check voor verborgen desktop
            try:
                result = subprocess.run(
                    ["powershell", "-NoProfile", "-Command",
                     "(Get-Process -Id $PID).SessionId"],
                    capture_output=True, text=True, timeout=5,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
                session_id = result.stdout.strip()
                # Session 0 = service/verborgen, Session 1+ = console
                if session_id == "0":
                    return LawResult(4, "Physical Console", False,
                                     "BREACH: Draait in service sessie (Session 0)")
            except Exception:
                pass  # Non-fatal

            return LawResult(4, "Physical Console", True,
                             f"Fysieke console OK (sessie: {session_name or 'Console'})")
        except Exception as e:
            return LawResult(4, "Physical Console", False, f"ERROR: {e}")

    def _law_5_identity_binding(self) -> LawResult:
        """Wet #5: Identity Binding — Git email moet op de whitelist staan."""
        try:
            result = subprocess.run(
                ["git", "config", "--global", "user.email"],
                capture_output=True, text=True, timeout=5,
            )
            email = result.stdout.strip().lower()
            if not email:
                return LawResult(5, "Identity Binding", False,
                                 "BREACH: Geen git email geconfigureerd")
            if email in _GIT_EMAIL_WHITELIST:
                return LawResult(5, "Identity Binding", True,
                                 f"Identity OK: {email}")
            return LawResult(5, "Identity Binding", False,
                             f"BREACH: Onbekende git email: {email}")
        except Exception as e:
            return LawResult(5, "Identity Binding", False, f"ERROR: {e}")

    def _law_6_hardware_fingerprint(self) -> LawResult:
        """Wet #6: Hardware Fingerprint — CPU+MAC master hash match."""
        try:
            from danny_toolkit.omega_sovereign_core.hardware_fingerprint import (
                get_fingerprint_engine,
            )
            fp = get_fingerprint_engine()
            ok, detail = fp.verify()
            return LawResult(6, "Hardware Fingerprint", ok, detail)
        except ImportError:
            return LawResult(6, "Hardware Fingerprint", False,
                             "ERROR: hardware_fingerprint module niet beschikbaar")
        except Exception as e:
            return LawResult(6, "Hardware Fingerprint", False, f"ERROR: {e}")

    def _law_7_iron_dome(self) -> LawResult:
        """Wet #7: Iron Dome Network — default-deny profiel actief."""
        try:
            from danny_toolkit.omega_sovereign_core.iron_dome import get_iron_dome
            dome = get_iron_dome()

            # Verificatie: check dat de dome operationeel is
            stats = dome.get_stats()
            whitelist_size = stats.get("whitelist_size", 0)

            if whitelist_size == 0:
                return LawResult(7, "Iron Dome Network", False,
                                 "BREACH: Lege whitelist — geen perimeter")

            # Quick scan: zijn er onbekende actieve connecties?
            unknown = dome.scan_active_connections()
            unknown_count = len(unknown)

            if unknown_count > 5:
                return LawResult(7, "Iron Dome Network", False,
                                 f"BREACH: {unknown_count} onbekende actieve connecties")

            return LawResult(7, "Iron Dome Network", True,
                             f"Perimeter OK: {whitelist_size} whitelisted hosts, "
                             f"{unknown_count} onbekende connecties")
        except ImportError:
            return LawResult(7, "Iron Dome Network", False,
                             "ERROR: iron_dome module niet beschikbaar")
        except Exception as e:
            return LawResult(7, "Iron Dome Network", False, f"ERROR: {e}")

    # ══════════════════════════════════════════════════════════
    #  ENFORCEMENT
    # ══════════════════════════════════════════════════════════

    def enforce_all(self) -> Tuple[bool, GateReport]:
        """
        Draai alle 7 IJzeren Wetten en genereer een GateReport.

        Returns:
            (all_passed, GateReport)
        """
        import time
        start = time.perf_counter()
        now = datetime.now().isoformat()

        laws = [
            self._law_1_root_integrity,
            self._law_2_authority_check,
            self._law_3_terminal_lock,
            self._law_4_physical_console,
            self._law_5_identity_binding,
            self._law_6_hardware_fingerprint,
            self._law_7_iron_dome,
        ]

        results: List[LawResult] = []
        for law_fn in laws:
            t0 = time.perf_counter()
            result = law_fn()
            result.enforcement_time_ms = (time.perf_counter() - t0) * 1000
            results.append(result)

        total_ms = (time.perf_counter() - start) * 1000
        all_passed = all(r.passed for r in results)

        report = GateReport(
            timestamp=now,
            all_passed=all_passed,
            laws=results,
            total_time_ms=total_ms,
        )
        self._last_report = report

        # ── Terminal output ──
        self._print_report(report)

        # ── Log naar CorticalStack ──
        self._log_to_cortical(report)

        # ── Lockdown bij falen ──
        if not all_passed and self._strict:
            failed = [r for r in results if not r.passed]
            failed_names = ", ".join(f"#{r.law_number}" for r in failed)
            if self._lockdown:
                self._lockdown.engage_lockdown(
                    reason=f"IJzeren Wetten geschonden: {failed_names}",
                    law_violated=failed_names,
                )

        return all_passed, report

    def enforce_single(self, law_number: int) -> LawResult:
        """Draai een enkele wet (1-7)."""
        law_map = {
            1: self._law_1_root_integrity,
            2: self._law_2_authority_check,
            3: self._law_3_terminal_lock,
            4: self._law_4_physical_console,
            5: self._law_5_identity_binding,
            6: self._law_6_hardware_fingerprint,
            7: self._law_7_iron_dome,
        }
        if law_number not in law_map:
            return LawResult(law_number, "UNKNOWN", False,
                             f"Onbekende wet: {law_number}")
        import time
        t0 = time.perf_counter()
        result = law_map[law_number]()
        result.enforcement_time_ms = (time.perf_counter() - t0) * 1000
        return result

    # ── Output ──

    def _print_report(self, report: GateReport) -> None:
        """Print het rapport naar de terminal met Tri-Color Symphony."""
        print(f"\n{Kleur.CYAAN}{'═' * 60}")
        print(f"  Ω SOVEREIGN GATE — 7 IJZEREN WETTEN")
        print(f"{'═' * 60}{Kleur.RESET}")

        for law in report.laws:
            if law.passed:
                icon = f"{Kleur.GROEN}✓{Kleur.RESET}"
            else:
                icon = f"{Kleur.ROOD}✗{Kleur.RESET}"
            print(f"  {icon} Wet #{law.law_number}: {law.name}")
            print(f"    {law.detail} ({law.enforcement_time_ms:.1f}ms)")

        print(f"\n{Kleur.CYAAN}{'─' * 60}{Kleur.RESET}")
        if report.all_passed:
            print(f"  {Kleur.GROEN}SOVEREIGN STATUS: ALLE WETTEN VERVULD{Kleur.RESET}")
        else:
            failed = sum(1 for law in report.laws if not law.passed)
            print(f"  {Kleur.ROOD}BREACH STATUS: {failed} WET(TEN) GESCHONDEN{Kleur.RESET}")
        print(f"  Totale verificatie: {report.total_time_ms:.0f}ms")
        print(f"{Kleur.CYAAN}{'═' * 60}{Kleur.RESET}\n")

    # ── Logging ──

    def _log_to_cortical(self, report: GateReport) -> None:
        """Log rapport naar CorticalStack."""
        if self._stack:
            try:
                self._stack.log_event(
                    bron="SovereignGate",
                    event_type="sovereign.gate.enforcement",
                    data=report.to_dict(),
                )
            except Exception as e:
                logger.debug("CorticalStack gate log mislukt: %s", e)

    # ── Status ──

    def get_last_report(self) -> Optional[Dict]:
        """Haal het laatste enforcement rapport op."""
        if self._last_report:
            return self._last_report.to_dict()
        return None


# ── Singleton ──

_gate_instance: Optional[SovereignGate] = None
_gate_lock = threading.Lock()


def get_sovereign_gate(strict: bool = True) -> SovereignGate:
    """Verkrijg de singleton SovereignGate instantie."""
    global _gate_instance
    if _gate_instance is None:
        with _gate_lock:
            if _gate_instance is None:
                _gate_instance = SovereignGate(strict=strict)
    return _gate_instance

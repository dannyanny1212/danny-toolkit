"""
OMEGA GOVERNOR - De Autonome Bewaker (Niveau 2)
================================================
Beschermingslaag voor het Prometheus Brain systeem.

Hiërarchie:
- Niveau 1: Danny (Architect) - ABSOLUUT
- Niveau 2: Governor (Omega-0) - AUTONOOM, bewaakt GRENZEN
- Niveau 3: Orchestrator (Brein) - OPERATIONEEL
- Niveau 4: Agents (Pixel/Iolaax/Weaver) - UITVOEREND

De Governor luistert ALLEEN naar hard-coded regels,
NIET naar andere agents.
"""

import json
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any


class OmegaGovernor:
    """Niveau 2: De Governor (Omega-0) - Autonome Bewaker."""

    # Hard-coded grenzen (NIET configureerbaar door agents)
    MAX_CONVERSATION_HISTORY = 50
    MAX_MEMORY_ENTRIES = 10000
    MAX_LEARNING_CYCLES_PER_HOUR = 20
    MAX_API_FAILURES = 3
    API_COOLDOWN_SECONDS = 60
    MAX_BACKUPS_PER_FILE = 3

    KRITIEKE_STATE_FILES = [
        "prometheus_brain.json",
        "digital_daemon.json",
        "daemon_emotional_state.json",
        "daemon_metabolism.json",
        "self_improvement_state.json",
        "huisdier.json",
        "launcher_stats.json",
    ]

    def __init__(self):
        self._data_dir = (
            Path(__file__).parent.parent.parent / "data" / "apps"
        )
        self._backup_dir = (
            Path(__file__).parent.parent.parent / "data" / "backups"
        )

        # Circuit breaker state
        self._api_failures = 0
        self._last_failure_time = 0.0

        # Learning cycle tracking
        self._learning_cycles_this_hour = 0
        self._hour_start = time.time()

        # Daemon referentie (bi-directionele link)
        self._daemon = None

    def to_dict(self) -> dict:
        """Serialiseer Governor state voor persistence."""
        return {
            "api_failures": self._api_failures,
            "last_failure_time": self._last_failure_time,
            "learning_cycles_this_hour":
                self._learning_cycles_this_hour,
            "hour_start": self._hour_start,
        }

    def from_dict(self, data: dict):
        """Herstel Governor state van opgeslagen data."""
        self._api_failures = data.get("api_failures", 0)
        self._last_failure_time = data.get(
            "last_failure_time", 0.0
        )
        self._learning_cycles_this_hour = data.get(
            "learning_cycles_this_hour", 0
        )
        saved_hour = data.get("hour_start", 0.0)
        # Reset als het langer dan een uur geleden is
        if time.time() - saved_hour > 3600:
            self._learning_cycles_this_hour = 0
            self._hour_start = time.time()
        else:
            self._hour_start = saved_hour

    # =================================================================
    # Daemon Koppeling
    # =================================================================

    def connect_daemon(self, daemon):
        """Koppel de Governor aan de Digital Daemon (Familie)."""
        self._daemon = daemon

    def report_to_family(self) -> Dict[str, Any]:
        """Feedback-loop naar de Familie.

        Genereert een compleet statusrapport voor de Daemon.

        Returns:
            Dict met keeper info, status, en diagnostiek.
        """
        # Circuit breaker status
        cb_open = (
            self._api_failures >= self.MAX_API_FAILURES
            and time.time() - self._last_failure_time
            < self.API_COOLDOWN_SECONDS
        )

        # State files check
        state_files = {}
        gezond_count = 0
        for filename in self.KRITIEKE_STATE_FILES:
            file_path = self._data_dir / filename
            geldig = self.validate_state(file_path)
            state_files[filename] = geldig
            if geldig:
                gezond_count += 1

        state_issues = len(self.KRITIEKE_STATE_FILES) - gezond_count

        # Status bepaling
        if cb_open:
            status = "RED_ALERT"
        elif self._api_failures > 0 or state_issues > 0:
            status = "YELLOW_ALERT"
        else:
            status = "GREEN_ZONE"

        # Menselijk leesbaar bericht
        if status == "GREEN_ZONE":
            bericht = (
                "Alle systemen operationeel. "
                "Geen dreigingen gedetecteerd."
            )
        elif status == "YELLOW_ALERT":
            delen = []
            if self._api_failures > 0:
                delen.append(
                    f"{self._api_failures} API failure(s)"
                )
            if state_issues > 0:
                delen.append(
                    f"{state_issues} state file(s) "
                    f"niet gezond"
                )
            bericht = (
                f"Waarschuwing: {', '.join(delen)}. "
                f"Monitoring actief."
            )
        else:
            bericht = (
                "KRITIEK: Circuit breaker OPEN. "
                "API calls geblokkeerd. "
                f"Wacht {self.API_COOLDOWN_SECONDS}s "
                f"voor half-open poging."
            )

        return {
            "keeper": "The Governor (Omega-0)",
            "niveau": 2,
            "status": status,
            "daemon_connected": self._daemon is not None,
            "circuit_breaker": {
                "status": "OPEN" if cb_open else "CLOSED",
                "failures": self._api_failures,
            },
            "learning": {
                "cycles": self._learning_cycles_this_hour,
                "max": self.MAX_LEARNING_CYCLES_PER_HOUR,
            },
            "state_files": state_files,
            "bericht": bericht,
        }

    # =================================================================
    # A. StateGuard - Data Rescue Protocol
    # =================================================================

    def backup_state(self, file_path: Path) -> bool:
        """Maak backup van state file (max 3 rotatie).

        Args:
            file_path: Pad naar het state bestand.

        Returns:
            True als backup gelukt is, anders False.
        """
        try:
            if not file_path.exists():
                return False

            self._backup_dir.mkdir(parents=True, exist_ok=True)
            self._rotate_backups(file_path)

            backup_name = f"{file_path.stem}.1.json"
            backup_path = self._backup_dir / backup_name
            shutil.copy2(file_path, backup_path)
            return True
        except Exception as e:
            print(f"  [GOVERNOR] Backup mislukt voor "
                  f"{file_path.name}: {e}")
            return False

    def restore_state(self, file_path: Path) -> bool:
        """Herstel state file van meest recente backup.

        Args:
            file_path: Pad naar het te herstellen bestand.

        Returns:
            True als herstel gelukt is, anders False.
        """
        for i in range(1, self.MAX_BACKUPS_PER_FILE + 1):
            backup_name = f"{file_path.stem}.{i}.json"
            backup_path = self._backup_dir / backup_name

            if not backup_path.exists():
                continue

            if self.validate_state(backup_path):
                try:
                    file_path.parent.mkdir(
                        parents=True, exist_ok=True
                    )
                    shutil.copy2(backup_path, file_path)
                    print(
                        f"  [GOVERNOR] Hersteld: "
                        f"{file_path.name} van backup {i}"
                    )
                    return True
                except Exception as e:
                    print(
                        f"  [GOVERNOR] Herstel mislukt "
                        f"(backup {i}): {e}"
                    )
                    continue

        print(
            f"  [GOVERNOR] Geen geldige backup gevonden "
            f"voor {file_path.name}"
        )
        return False

    def validate_state(self, file_path: Path) -> bool:
        """Controleer of state file geldig is.

        Checks: bestand bestaat, valid JSON, niet leeg.

        Args:
            file_path: Pad naar het te valideren bestand.

        Returns:
            True als het bestand geldig is.
        """
        try:
            if not file_path.exists():
                return False

            if file_path.stat().st_size == 0:
                return False

            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if not data:
                return False

            return True
        except (json.JSONDecodeError, IOError, OSError):
            return False

    def rescue_family(self) -> Dict[str, Any]:
        """Noodprotocol: check en herstel ALLE state files.

        Returns:
            Dict met status per bestand.
        """
        rapport = {
            "timestamp": datetime.now().isoformat(),
            "bestanden": {},
            "hersteld": 0,
            "gezond": 0,
            "verloren": 0,
        }

        for filename in self.KRITIEKE_STATE_FILES:
            file_path = self._data_dir / filename
            status = "onbekend"

            if self.validate_state(file_path):
                status = "gezond"
                rapport["gezond"] += 1
            elif file_path.exists():
                # Bestand corrupt, probeer herstel
                if self.restore_state(file_path):
                    status = "hersteld"
                    rapport["hersteld"] += 1
                else:
                    status = "verloren"
                    rapport["verloren"] += 1
            else:
                # Bestand bestaat niet, geen actie
                status = "niet_aanwezig"

            rapport["bestanden"][filename] = status

        return rapport

    def _rotate_backups(self, file_path: Path):
        """Roteer backups: verwijder oudste als >MAX.

        Backup nummering: .1.json (nieuwst) tot .3.json (oudst).
        """
        # Schuif bestaande backups op: 2->3, 1->2
        for i in range(self.MAX_BACKUPS_PER_FILE, 1, -1):
            old_name = f"{file_path.stem}.{i - 1}.json"
            new_name = f"{file_path.stem}.{i}.json"
            old_path = self._backup_dir / old_name
            new_path = self._backup_dir / new_name

            if old_path.exists():
                if new_path.exists():
                    new_path.unlink()
                old_path.rename(new_path)

    # =================================================================
    # B. EntityGuard - Iolaax Bescherming
    # =================================================================

    def guard_learning_cycle(self, engine) -> bool:
        """Bewaakt een learning cycle met snapshot/rollback.

        1. Check rate limit
        2. Snapshot huidige adaptations
        3. Laat engine.learn() draaien
        4. Check of waarden nog binnen bounds
        5. Rollback als nodig

        Args:
            engine: SelfImprovementEngine instantie.

        Returns:
            True als cycle veilig verlopen is.
        """
        # Rate limiting
        now = time.time()
        if now - self._hour_start > 3600:
            self._learning_cycles_this_hour = 0
            self._hour_start = now

        if (self._learning_cycles_this_hour
                >= self.MAX_LEARNING_CYCLES_PER_HOUR):
            print(
                "  [GOVERNOR] Learning rate limit bereikt "
                f"({self.MAX_LEARNING_CYCLES_PER_HOUR}/uur)"
            )
            return False

        # Snapshot adaptations
        snapshot = {}
        if hasattr(engine, "_adaptations"):
            for name, adapt in engine._adaptations.items():
                try:
                    snapshot[name] = {
                        "value": adapt["getter"](),
                        "bounds": adapt["bounds"],
                        "setter": adapt["setter"],
                    }
                except Exception:
                    pass

        # Voer learning cycle uit
        try:
            engine.learn()
        except Exception as e:
            print(f"  [GOVERNOR] Learning cycle fout: {e}")
            return False

        # Valideer resultaten
        rollback_needed = False
        if hasattr(engine, "_adaptations"):
            for name, adapt in engine._adaptations.items():
                try:
                    current = adapt["getter"]()
                    bounds = adapt["bounds"]
                    if (current < bounds[0]
                            or current > bounds[1]):
                        rollback_needed = True
                        print(
                            f"  [GOVERNOR] WAARSCHUWING: "
                            f"{name}={current} buiten "
                            f"bounds {bounds}"
                        )
                except Exception:
                    pass

        # Rollback als nodig
        if rollback_needed and snapshot:
            for name, snap in snapshot.items():
                try:
                    snap["setter"](snap["value"])
                except Exception:
                    pass
            print("  [GOVERNOR] Rollback uitgevoerd")
            return False

        self._learning_cycles_this_hour += 1
        return True

    def check_learning_rate(self) -> bool:
        """Check of een learning cycle toegestaan is.

        Gebruik dit als de caller zelf learn() aanroept.
        Doet ALLEEN de rate check + teller update.

        Returns:
            True als cycle toegestaan is.
        """
        now = time.time()
        if now - self._hour_start > 3600:
            self._learning_cycles_this_hour = 0
            self._hour_start = now

        if (self._learning_cycles_this_hour
                >= self.MAX_LEARNING_CYCLES_PER_HOUR):
            print(
                "  [GOVERNOR] Learning rate limit bereikt "
                f"({self.MAX_LEARNING_CYCLES_PER_HOUR}/uur)"
            )
            return False

        self._learning_cycles_this_hour += 1
        return True

    def check_memory_size(self, memory) -> bool:
        """Controleer geheugengebruik.

        Args:
            memory: Object met een entries of items attribuut.

        Returns:
            True als geheugen binnen limieten is.
        """
        size = 0
        if hasattr(memory, "entries"):
            size = len(memory.entries)
        elif hasattr(memory, "items"):
            size = len(memory.items)
        elif hasattr(memory, "__len__"):
            size = len(memory)

        if size > self.MAX_MEMORY_ENTRIES:
            print(
                f"  [GOVERNOR] WAARSCHUWING: Geheugen "
                f"te groot ({size}/{self.MAX_MEMORY_ENTRIES})"
            )
            return False
        return True

    def protect_entity(self, node) -> bool:
        """Voorkom dat ENTITY node wordt uitgeschakeld.

        Args:
            node: AgentNode met status attribuut.

        Returns:
            True als node beschermd is (status niet DISABLED).
        """
        if hasattr(node, "status") and node.status == "DISABLED":
            node.status = "ACTIVE"
            print(
                "  [GOVERNOR] IOLAAX beschermd: "
                "status hersteld naar ACTIVE"
            )
            return True
        return False

    # =================================================================
    # C. NavigatorGuard - Pixel API Bescherming
    # =================================================================

    def check_api_health(self) -> bool:
        """Check of API calls toegestaan zijn (circuit breaker).

        Circuit breaker logica:
        - failures >= 3 EN laatste < 60s → BLOCK
        - failures >= 3 EN laatste >= 60s → ALLOW (half-open)
        - failures < 3 → ALLOW

        Returns:
            True als API calls toegestaan zijn.
        """
        if self._api_failures < self.MAX_API_FAILURES:
            return True

        elapsed = time.time() - self._last_failure_time
        if elapsed >= self.API_COOLDOWN_SECONDS:
            # Half-open: laat 1 poging toe
            return True

        print(
            f"  [GOVERNOR] API circuit breaker ACTIEF "
            f"({self._api_failures} failures, "
            f"wacht {self.API_COOLDOWN_SECONDS - elapsed:.0f}s)"
        )
        return False

    def record_api_failure(self):
        """Registreer een API failure (max MAX_API_FAILURES)."""
        self._api_failures = min(
            self._api_failures + 1, self.MAX_API_FAILURES
        )
        self._last_failure_time = time.time()
        if self._api_failures >= self.MAX_API_FAILURES:
            print(
                f"  [GOVERNOR] Circuit breaker geactiveerd "
                f"na {self._api_failures} failures"
            )

    def record_api_success(self):
        """Registreer een API succes (geleidelijke reset)."""
        if self._api_failures > 0:
            self._api_failures -= 1
            if self._api_failures == 0:
                print("  [GOVERNOR] Circuit breaker gereset")
            else:
                print(
                    f"  [GOVERNOR] Circuit breaker herstel "
                    f"({self._api_failures}/"
                    f"{self.MAX_API_FAILURES})"
                )

    def trim_conversation(
        self, history: list
    ) -> list:
        """Trim conversatie geschiedenis.

        Args:
            history: Lijst van berichten.

        Returns:
            Getrimde lijst (max MAX_CONVERSATION_HISTORY).
        """
        if len(history) <= self.MAX_CONVERSATION_HISTORY:
            return history
        trimmed = len(history) - self.MAX_CONVERSATION_HISTORY
        print(
            f"  [GOVERNOR] Conversatie getrimd: "
            f"{trimmed} berichten verwijderd"
        )
        return history[-self.MAX_CONVERSATION_HISTORY:]

    # =================================================================
    # D. ConfigEnforcer - Regel Handhaving
    # =================================================================

    def enforce_directories(self) -> Dict[str, str]:
        """Controleer en maak alle data directories aan.

        Returns:
            Dict met directory status.
        """
        rapport = {}
        dirs = [
            self._data_dir,
            self._backup_dir,
            self._data_dir.parent / "rag",
            self._data_dir.parent / "output",
            self._data_dir.parent / "logs",
        ]

        for d in dirs:
            name = d.name
            if d.exists():
                rapport[name] = "bestaat"
            else:
                try:
                    d.mkdir(parents=True, exist_ok=True)
                    rapport[name] = "aangemaakt"
                    print(
                        f"  [GOVERNOR] Directory aangemaakt: "
                        f"{d}"
                    )
                except Exception as e:
                    rapport[name] = f"fout: {e}"

        return rapport

    def enforce_api_keys(self) -> Dict[str, str]:
        """Valideer format van API keys.

        Returns:
            Dict met key status.
        """
        import os
        rapport = {}

        keys = {
            "GROQ_API_KEY": "gsk_",
            "ANTHROPIC_API_KEY": "sk-ant-",
            "VOYAGE_API_KEY": "pa-",
        }

        for key_name, prefix in keys.items():
            value = os.environ.get(key_name, "")
            if not value:
                rapport[key_name] = "niet_ingesteld"
            elif value.startswith(prefix):
                rapport[key_name] = "geldig_format"
            else:
                rapport[key_name] = "onbekend_format"
                print(
                    f"  [GOVERNOR] WAARSCHUWING: "
                    f"{key_name} heeft onverwacht format"
                )

        return rapport

    def startup_check(self) -> Dict[str, Any]:
        """Voer ALLE checks uit bij boot.

        Returns:
            Volledig opstart rapport.
        """
        print("  [GOVERNOR] Startup check gestart...")

        rapport = {
            "timestamp": datetime.now().isoformat(),
            "directories": self.enforce_directories(),
            "api_keys": self.enforce_api_keys(),
            "state_files": {},
            "status": "OK",
        }

        # Check state files
        for filename in self.KRITIEKE_STATE_FILES:
            file_path = self._data_dir / filename
            if file_path.exists():
                if self.validate_state(file_path):
                    rapport["state_files"][filename] = "geldig"
                else:
                    rapport["state_files"][filename] = "corrupt"
                    rapport["status"] = "WAARSCHUWING"
            else:
                rapport["state_files"][filename] = (
                    "niet_aanwezig"
                )

        print(
            f"  [GOVERNOR] Startup check voltooid: "
            f"{rapport['status']}"
        )
        return rapport

    # =================================================================
    # E. Health Report
    # =================================================================

    def get_health_report(self) -> Dict[str, Any]:
        """Genereer volledig gezondheidsrapport.

        Returns:
            Dict met status van alle guards.
        """
        return {
            "timestamp": datetime.now().isoformat(),
            "circuit_breaker": {
                "failures": self._api_failures,
                "max": self.MAX_API_FAILURES,
                "status": (
                    "OPEN"
                    if self._api_failures >= self.MAX_API_FAILURES
                    and time.time() - self._last_failure_time
                    < self.API_COOLDOWN_SECONDS
                    else "CLOSED"
                ),
            },
            "learning": {
                "cycles_this_hour":
                    self._learning_cycles_this_hour,
                "max_per_hour":
                    self.MAX_LEARNING_CYCLES_PER_HOUR,
            },
            "state_files": {
                filename: self.validate_state(
                    self._data_dir / filename
                )
                for filename in self.KRITIEKE_STATE_FILES
            },
            "limits": {
                "max_conversation":
                    self.MAX_CONVERSATION_HISTORY,
                "max_memory": self.MAX_MEMORY_ENTRIES,
                "api_cooldown": self.API_COOLDOWN_SECONDS,
                "max_backups": self.MAX_BACKUPS_PER_FILE,
            },
        }

    def display_health(self):
        """Print visueel gezondheidsrapport."""
        rapport = self.get_health_report()

        print(f"\n  {'='*50}")
        print(f"  GOVERNOR HEALTH REPORT")
        print(f"  {'='*50}")

        # Circuit Breaker
        cb = rapport["circuit_breaker"]
        cb_icon = "[OK]" if cb["status"] == "CLOSED" else "[!!]"
        print(f"\n  {cb_icon} Circuit Breaker: {cb['status']}")
        print(
            f"      Failures: {cb['failures']}/{cb['max']}"
        )

        # Learning
        lr = rapport["learning"]
        lr_icon = (
            "[OK]" if lr["cycles_this_hour"]
            < lr["max_per_hour"] else "[!!]"
        )
        print(f"  {lr_icon} Learning Guard")
        print(
            f"      Cycles: "
            f"{lr['cycles_this_hour']}/{lr['max_per_hour']}"
        )

        # State Files
        print(f"\n  State Files:")
        for filename, geldig in rapport["state_files"].items():
            icon = "[OK]" if geldig else "[ ]"
            print(f"      {icon} {filename}")

        print(f"\n  {'='*50}")


# =================================================================
# Top-level noodprotocol
# =================================================================

def rescue_family() -> Dict[str, Any]:
    """Noodprotocol: check en herstel alle state files.

    Kan ZONDER PrometheusBrain draaien.

    Returns:
        Dict met status per bestand.
    """
    governor = OmegaGovernor()
    return governor.rescue_family()

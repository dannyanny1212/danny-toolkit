"""
Governor State Mixin — Backup, restore en state validatie.


Bevat GovernorStateMixin met:
- backup_state()      — Backup met rotatie
- restore_state()     — Herstel van backup
- validate_state()    — JSON validatie
- rescue_family()     — Noodprotocol alle state files
- _rotate_backups()   — Backup rotatie

Plus top-level rescue_family() functie (backward compat).

Geëxtraheerd uit governor.py (Fase C.2 monoliet split).
Mixin leest constanten via self.* (OmegaGovernor attributen).
"""

from __future__ import annotations

import json
import logging
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)


class GovernorStateMixin:
    """Mixin voor state backup, restore en validatie.

    Vereist dat de host-klasse de volgende attributen heeft:
    - self._data_dir, self._backup_dir (Path)
    - self.MAX_BACKUPS_PER_FILE (int)
    - self.KRITIEKE_STATE_FILES (list)
    - self._log(action, details)
    """

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

            # Retry bij Windows file lock (WinError 32)
            for poging in range(3):
                try:
                    shutil.copy2(file_path, backup_path)
                    return True
                except PermissionError:
                    if poging < 2:
                        time.sleep(0.1)
                    else:
                        raise
        except Exception as e:
            print(f"  [GOVERNOR] Backup mislukt voor "
                  f"{file_path.name}: {e}")
            self._log("backup_mislukt", {
                "bestand": file_path.name,
            })
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
                    self._log("state_hersteld", {
                        "bestand": file_path.name,
                        "backup": i,
                    })
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

    def _rotate_backups(self, file_path: Path) -> None:
        """Roteer backups: verwijder oudste als >MAX.

        Backup nummering: .1.json (nieuwst) tot .3.json (oudst).
        """
        # Schuif bestaande backups op: 2->3, 1->2
        for i in range(self.MAX_BACKUPS_PER_FILE, 1, -1):
            old_name = f"{file_path.stem}.{i - 1}.json"
            new_name = f"{file_path.stem}.{i}.json"
            old_path = self._backup_dir / old_name
            new_path = self._backup_dir / new_name

            if not old_path.exists():
                continue

            try:
                if new_path.exists():
                    new_path.unlink()
                shutil.move(str(old_path), str(new_path))
            except OSError as e:
                logger.debug("Governor backup rotation failed: %s", e)


# =================================================================
# Top-level noodprotocol (backward compat)
# =================================================================

def rescue_family() -> Dict[str, Any]:
    """Noodprotocol: check en herstel alle state files.

    Kan ZONDER PrometheusBrain draaien.

    Returns:
        Dict met status per bestand.
    """
    from danny_toolkit.brain.governor import OmegaGovernor
    governor = OmegaGovernor()
    return governor.rescue_family()

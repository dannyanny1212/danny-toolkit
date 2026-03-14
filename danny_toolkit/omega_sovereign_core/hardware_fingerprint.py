"""
Hardware Fingerprint — Sovereign Identity Binding (IJzeren Wet #6).

Genereert en verifieert een unieke hardware-identiteit op basis van
CPU-ID, MAC-adres en moederbord-serial. Voorkomt Digital Twin hijack
en ongeautoriseerde kloon-executie.

Gebruik:
    from danny_toolkit.omega_sovereign_core.hardware_fingerprint import (
        get_fingerprint_engine, HardwareFingerprint
    )
    fp = get_fingerprint_engine()
    ok, detail = fp.verify()
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import platform
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)

try:
    from danny_toolkit.core.config import Config
    _DATA_DIR = Config.DATA_DIR
except ImportError:
    _DATA_DIR = Path(__file__).parent.parent.parent / "data"

try:
    from danny_toolkit.core.utils import Kleur
except ImportError:
    class Kleur:
        GROEN = ROOD = GEEL = CYAAN = RESET = ""


# ── Constanten ──

_MASTER_HASH_FILE = "sovereign_master.hash"
_HASH_ALGORITHM = "sha256"


@dataclass
class FingerprintComponents:
    """Ruwe hardware-componenten voor de fingerprint."""
    cpu_id: str = ""
    mac_address: str = ""
    machine_name: str = ""
    platform_node: str = ""
    processor: str = ""
    motherboard_serial: str = ""
    collected_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, str]:
        """To dict."""
        return {
            "cpu_id": self.cpu_id,
            "mac_address": self.mac_address,
            "machine_name": self.machine_name,
            "platform_node": self.platform_node,
            "processor": self.processor,
            "motherboard_serial": self.motherboard_serial,
            "collected_at": self.collected_at,
        }


class HardwareFingerprint:
    """
    Verzamelt en verifieert hardware-identiteit.

    Bij eerste run wordt een master hash opgeslagen.
    Elke volgende run vergelijkt de huidige hardware met de master.
    Mismatch = potentiële kloon of VM-migratie → lockdown.
    """

    def __init__(self, data_dir: Optional[Path] = None) -> None:
        """Init  ."""
        self._data_dir = Path(data_dir) if data_dir else Path(_DATA_DIR)
        self._master_path = self._data_dir / _MASTER_HASH_FILE
        self._components: Optional[FingerprintComponents] = None
        self._current_hash: Optional[str] = None
        self._stack = None
        self._backends_loaded = False

    def _ensure_backends(self) -> None:
        """Lazy CorticalStack verbinding — pas laden bij eerste gebruik."""
        if self._backends_loaded:
            return
        self._backends_loaded = True
        if not os.environ.get("DANNY_TEST_MODE"):
            try:
                self._stack = get_cortical_stack()
            except ImportError:
                logger.debug("CorticalStack niet beschikbaar voor fingerprint logging")

    # ── Collectie ──

    def _collect_cpu_id(self) -> str:
        """Verzamel CPU identifier (Windows-specifiek via WMI, fallback naar platform)."""
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "(Get-CimInstance Win32_Processor).ProcessorId"],
                capture_output=True, text=True, timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            cpu_id = result.stdout.strip()
            if cpu_id:
                return cpu_id
        except Exception as e:
            logger.debug("WMI CPU-ID fallback: %s", e)
        return platform.processor() or "unknown_cpu"

    def _collect_mac(self) -> str:
        """Verzamel primaire MAC-adres."""
        try:
            mac_int = uuid.getnode()
            # uuid.getnode() retourneert random als geen MAC gevonden
            if (mac_int >> 40) % 2:
                return "random_mac"
            return ":".join(
                f"{(mac_int >> i) & 0xFF:02x}"
                for i in range(40, -1, -8)
            )
        except Exception as e:
            logger.debug("MAC-collectie fout: %s", e)
            return "unknown_mac"

    def _collect_motherboard_serial(self) -> str:
        """Verzamel moederbord serial (Windows WMI)."""
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "(Get-CimInstance Win32_BaseBoard).SerialNumber"],
                capture_output=True, text=True, timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            serial = result.stdout.strip()
            if serial and serial.lower() not in ("default string", "to be filled by o.e.m.", "none"):
                return serial
        except Exception as e:
            logger.debug("Moederbord serial fallback: %s", e)
        return "no_serial"

    def collect(self) -> FingerprintComponents:
        """Verzamel alle hardware-componenten."""
        self._components = FingerprintComponents(
            cpu_id=self._collect_cpu_id(),
            mac_address=self._collect_mac(),
            machine_name=os.environ.get("COMPUTERNAME", "unknown"),
            platform_node=platform.node(),
            processor=platform.processor(),
            motherboard_serial=self._collect_motherboard_serial(),
        )
        logger.debug("Hardware componenten verzameld: %s", self._components.machine_name)
        return self._components

    # ── Hashing ──

    def _compute_hash(self, components: FingerprintComponents) -> str:
        """Bereken deterministische SHA-256 hash van hardware-componenten."""
        # Sorteer keys voor determinisme
        canonical = "|".join([
            components.cpu_id,
            components.mac_address,
            components.machine_name,
            components.processor,
            components.motherboard_serial,
        ])
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def get_current_hash(self) -> str:
        """Bereken de huidige hardware hash."""
        if self._components is None:
            self.collect()
        self._current_hash = self._compute_hash(self._components)
        return self._current_hash

    # ── Master Hash Opslag ──

    def _load_master_hash(self) -> Optional[str]:
        """Laad de opgeslagen master hash."""
        try:
            if self._master_path.exists():
                data = json.loads(self._master_path.read_text(encoding="utf-8"))
                return data.get("master_hash")
        except Exception as e:
            logger.debug("Master hash laden mislukt: %s", e)
        return None

    def _save_master_hash(self, hash_value: str) -> bool:
        """Sla de master hash op (eerste run enrollment)."""
        try:
            self._data_dir.mkdir(parents=True, exist_ok=True)
            data = {
                "master_hash": hash_value,
                "enrolled_at": datetime.now().isoformat(),
                "machine_name": self._components.machine_name if self._components else "unknown",
                "components": self._components.to_dict() if self._components else {},
            }
            self._master_path.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            logger.info("Sovereign Master Hash enrolled: %s...%s",
                         hash_value[:8], hash_value[-8:])
            return True
        except Exception as e:
            logger.error("Master hash opslaan mislukt: %s", e)
            return False

    # ── Verificatie ──

    def verify(self) -> Tuple[bool, str]:
        """
        Verifieer de huidige hardware tegen de master hash.

        Returns:
            (True, "OK") bij match
            (True, "ENROLLED") bij eerste run (master hash aangemaakt)
            (False, "MISMATCH: ...") bij hardware wijziging
            (False, "ERROR: ...") bij technische fout
        """
        try:
            current = self.get_current_hash()
            master = self._load_master_hash()

            if master is None:
                # Eerste run — enrollment
                if self._save_master_hash(current):
                    self._log_event("ENROLLMENT", f"Master hash: {current[:16]}...")
                    return True, "ENROLLED"
                return False, "ERROR: Kon master hash niet opslaan"

            if current == master:
                self._log_event("VERIFY_OK", "Hardware fingerprint match")
                return True, "OK"

            # MISMATCH — potentiële kloon of hardware wijziging
            detail = (
                f"MISMATCH: verwacht={master[:16]}... "
                f"actueel={current[:16]}..."
            )
            self._log_event("VERIFY_FAIL", detail)
            print(f"{Kleur.ROOD}[SOVEREIGN] Hardware fingerprint MISMATCH!{Kleur.RESET}")
            return False, detail

        except Exception as e:
            err = f"ERROR: Fingerprint verificatie fout: {e}"
            logger.error(err)
            return False, err

    def get_enrollment_info(self) -> Optional[Dict]:
        """Haal enrollment informatie op (als beschikbaar)."""
        try:
            if self._master_path.exists():
                return json.loads(self._master_path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.debug("Enrollment info laden mislukt: %s", e)
        return None

    def re_enroll(self) -> Tuple[bool, str]:
        """
        Herregistreer de hardware (vereist expliciete Commandant-actie).
        Overschrijft de master hash met de huidige hardware.
        """
        current = self.get_current_hash()
        if self._save_master_hash(current):
            self._log_event("RE_ENROLLMENT", f"Nieuwe master: {current[:16]}...")
            return True, f"RE-ENROLLED: {current[:16]}..."
        return False, "ERROR: Re-enrollment mislukt"

    # ── Logging ──

    def _log_event(self, event_type: str, detail: str) -> None:
        """Log naar CorticalStack."""
        self._ensure_backends()
        if self._stack:
            try:
                self._stack.log_event(
                    bron="HardwareFingerprint",
                    event_type=f"sovereign.fingerprint.{event_type.lower()}",
                    data={"detail": detail, "timestamp": datetime.now().isoformat()},
                )
            except Exception as e:
                logger.debug("CorticalStack log mislukt: %s", e)

try:
    from danny_toolkit.brain.cortical_stack import get_cortical_stack
except ImportError:
    logger.debug("Optional import not available: danny_toolkit.brain.cortical_stack")
import subprocess


# ── Singleton ──

_fp_instance: Optional[HardwareFingerprint] = None
_fp_lock = threading.Lock()


def get_fingerprint_engine(data_dir: Optional[Path] = None) -> HardwareFingerprint:
    """Verkrijg de singleton HardwareFingerprint instantie."""
    global _fp_instance
    if _fp_instance is None:
        with _fp_lock:
            if _fp_instance is None:
                _fp_instance = HardwareFingerprint(data_dir=data_dir)
    return _fp_instance

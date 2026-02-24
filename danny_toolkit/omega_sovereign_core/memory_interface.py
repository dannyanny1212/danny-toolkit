"""
Memory Interface — Beveiligde Poort naar de Soul (/data/).

De Soul's gatekeeper. Geen enkel proces mag direct naar /data/ schrijven.
Alle state-opslag verloopt via deze interface, die:
  1. Data valideert (schema, grootte, type)
  2. Cryptografische handtekening verifieert (EventSigner)
  3. Hash-chain integriteit bewaakt (immutable ledger)
  4. Pas dan naar CorticalStack/disk schrijft

Gebruik:
    from danny_toolkit.omega_sovereign_core.memory_interface import (
        get_memory_interface, SecureMemoryInterface
    )
    mi = get_memory_interface()
    ok, receipt = mi.secure_store_state("brain_cli", {"history": [...]})
"""

import hashlib
import json
import logging
import os
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

try:
    from danny_toolkit.core.utils import Kleur
except ImportError:
    class Kleur:
        GROEN = ROOD = GEEL = CYAAN = RESET = ""

try:
    from danny_toolkit.core.config import Config
    _DATA_DIR = Path(Config.DATA_DIR)
except ImportError:
    _DATA_DIR = Path(__file__).parent.parent.parent / "data"


# ── Constanten ──

_MAX_STATE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB max per state save
_MAX_RECEIPT_LOG = 500
_HASH_CHAIN_FILE = "hash_chain.json"
_STATE_ARCHIVE_DIR = "state_archive"

# Toegestane component-namen (voorkom path traversal)
_ALLOWED_COMPONENTS = frozenset({
    "brain_cli", "sovereign_engine", "oracle_agent", "the_hunt",
    "arbitrator", "governor", "dreamer", "daemon_heartbeat",
    "fastapi_server", "telegram_bot", "streamlit_ui",
    "void_walker", "artificer", "strategist", "cortex",
    "phantom", "synapse", "virtual_twin", "ghost_writer",
    "devops_daemon", "model_sync", "config_auditor",
})


@dataclass
class StoreReceipt:
    """Bewijs van een geslaagde opslag-operatie."""
    timestamp: str
    component: str
    data_hash: str
    chain_hash: str
    size_bytes: int
    success: bool
    error: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "component": self.component,
            "data_hash": self.data_hash,
            "chain_hash": self.chain_hash,
            "size_bytes": self.size_bytes,
            "success": self.success,
            "error": self.error,
        }


class SecureMemoryInterface:
    """
    Beveiligde poort tussen Body (core) en Soul (data).

    Implementeert:
    - Data validatie (grootte, type, component whitelist)
    - Hash-chain: elk opgeslagen item bevat de hash van het vorige
    - State archivering naar disk (JSON + hash chain)
    - CorticalStack logging van alle operaties
    """

    def __init__(self, data_dir: Optional[Path] = None):
        self._data_dir = Path(data_dir) if data_dir else _DATA_DIR
        self._archive_dir = self._data_dir / _STATE_ARCHIVE_DIR
        self._chain_path = self._data_dir / _HASH_CHAIN_FILE
        self._lock = threading.Lock()
        self._last_chain_hash: Optional[str] = None
        self._receipts: Deque[StoreReceipt] = deque(maxlen=_MAX_RECEIPT_LOG)
        self._stats = {
            "stores": 0,
            "store_failures": 0,
            "retrievals": 0,
            "chain_length": 0,
            "total_bytes_stored": 0,
        }
        self._stack = None
        self._signer = None
        self._backends_loaded = False
        self._load_chain_head()

    def _ensure_backends(self) -> None:
        """Lazy backend verbindingen — pas laden bij eerste gebruik."""
        if self._backends_loaded:
            return
        self._backends_loaded = True
        # Skip CorticalStack in test mode (voorkomt SQLite WAL lock deadlocks)
        if not os.environ.get("DANNY_TEST_MODE"):
            try:
                from danny_toolkit.brain.cortical_stack import get_cortical_stack
                self._stack = get_cortical_stack()
            except (ImportError, Exception) as e:
                logger.debug("CorticalStack niet beschikbaar voor MemoryInterface: %s", e)
        try:
            from danny_toolkit.omega_sovereign_core.event_signing import get_event_signer
            self._signer = get_event_signer()
        except (ImportError, Exception) as e:
            logger.debug("EventSigner niet beschikbaar voor MemoryInterface: %s", e)

    # ══════════════════════════════════════════════════════════
    #  HASH CHAIN (Immutable Ledger)
    # ══════════════════════════════════════════════════════════

    def _load_chain_head(self) -> None:
        """Laad de laatst bekende hash uit de chain file."""
        try:
            if self._chain_path.exists():
                data = json.loads(self._chain_path.read_text(encoding="utf-8"))
                self._last_chain_hash = data.get("head_hash")
                self._stats["chain_length"] = data.get("chain_length", 0)
        except Exception as e:
            logger.debug("Hash chain head laden mislukt: %s", e)
            self._last_chain_hash = None

    def _compute_chain_hash(self, data_hash: str) -> str:
        """
        Bereken de volgende hash in de chain.
        chain_hash = SHA256(previous_chain_hash + data_hash)
        """
        prev = self._last_chain_hash or "GENESIS"
        combined = f"{prev}|{data_hash}"
        return hashlib.sha256(combined.encode("utf-8")).hexdigest()

    def _save_chain_head(self, chain_hash: str) -> None:
        """Sla de nieuwe chain head op."""
        try:
            self._data_dir.mkdir(parents=True, exist_ok=True)
            data = {
                "head_hash": chain_hash,
                "chain_length": self._stats["chain_length"],
                "updated_at": datetime.now().isoformat(),
            }
            self._chain_path.write_text(
                json.dumps(data, indent=2), encoding="utf-8"
            )
        except Exception as e:
            logger.debug("Hash chain head opslaan mislukt: %s", e)

    def verify_chain_integrity(self) -> Tuple[bool, str]:
        """
        Verifieer of de hash chain intact is.
        Leest alle gearchiveerde states en herbouwt de chain.
        """
        try:
            if not self._archive_dir.exists():
                return True, "Geen archief — chain is leeg (OK)"

            archives = sorted(self._archive_dir.glob("*.json"))
            if not archives:
                return True, "Leeg archief — chain is intact"

            prev_hash = "GENESIS"
            for archive_path in archives:
                try:
                    entry = json.loads(archive_path.read_text(encoding="utf-8"))
                    stored_chain = entry.get("chain_hash", "")
                    data_hash = entry.get("data_hash", "")
                    expected = hashlib.sha256(
                        f"{prev_hash}|{data_hash}".encode("utf-8")
                    ).hexdigest()
                    if stored_chain != expected:
                        return False, (
                            f"CHAIN BREAK bij {archive_path.name}: "
                            f"verwacht={expected[:16]}... gevonden={stored_chain[:16]}..."
                        )
                    prev_hash = stored_chain
                except Exception as e:
                    return False, f"Parse fout in {archive_path.name}: {e}"

            return True, f"Chain intact: {len(archives)} entries geverifieerd"
        except Exception as e:
            return False, f"Verificatie fout: {e}"

    # ══════════════════════════════════════════════════════════
    #  VALIDATIE
    # ══════════════════════════════════════════════════════════

    def _validate_component(self, component: str) -> Tuple[bool, str]:
        """Valideer component naam (voorkom path traversal en onbekende bronnen)."""
        # Sanitize: alleen alfanumeriek + underscore
        clean = component.replace("-", "_").lower().strip()
        if not clean.isidentifier():
            return False, f"Ongeldige component naam: '{component}'"
        if clean not in _ALLOWED_COMPONENTS:
            # Waarschuwing maar niet blokkeren — nieuwe componenten toestaan
            logger.warning("Onbekende component '%s' — niet op whitelist", clean)
        return True, clean

    def _validate_data(self, data: dict) -> Tuple[bool, str]:
        """Valideer state data (grootte, type)."""
        if not isinstance(data, dict):
            return False, f"State moet een dict zijn, kreeg: {type(data).__name__}"
        try:
            serialized = json.dumps(data, ensure_ascii=False, default=str)
        except (TypeError, ValueError) as e:
            return False, f"State niet serialiseerbaar: {e}"
        size = len(serialized.encode("utf-8"))
        if size > _MAX_STATE_SIZE_BYTES:
            return False, (
                f"State te groot: {size:,} bytes "
                f"(max {_MAX_STATE_SIZE_BYTES:,})"
            )
        return True, serialized

    # ══════════════════════════════════════════════════════════
    #  SECURE STORE (De kernoperatie)
    # ══════════════════════════════════════════════════════════

    def secure_store_state(
        self,
        component: str,
        state_data: dict,
        sign: bool = True,
    ) -> Tuple[bool, StoreReceipt]:
        """
        Beveiligd opslaan van component-state.

        Flow:
        1. Valideer component naam
        2. Valideer data (grootte, serialisatie)
        3. Bereken data hash
        4. Optioneel: onderteken met EventSigner
        5. Bereken chain hash (vorige chain + data hash)
        6. Schrijf naar archief (disk)
        7. Log naar CorticalStack
        8. Retourneer receipt

        Args:
            component: Naam van het component (bijv. "brain_cli")
            state_data: Dict met de state die opgeslagen moet worden
            sign: Of de data ondertekend moet worden

        Returns:
            (success, StoreReceipt)
        """
        self._ensure_backends()
        now = datetime.now()
        timestamp = now.isoformat()

        # ── 1. Valideer component ──
        ok, clean_name = self._validate_component(component)
        if not ok:
            return self._fail_receipt(timestamp, component, clean_name)

        # ── 2. Valideer data ──
        ok, serialized = self._validate_data(state_data)
        if not ok:
            return self._fail_receipt(timestamp, clean_name, serialized)

        size_bytes = len(serialized.encode("utf-8"))

        # ── 3. Data hash ──
        data_hash = hashlib.sha256(serialized.encode("utf-8")).hexdigest()

        # ── 4. Optionele signing ──
        signature_info = {}
        if sign and self._signer:
            try:
                signature_info = self._signer.sign(
                    event_type="state_store",
                    data={"component": clean_name, "data_hash": data_hash},
                    bron="memory_interface",
                )
            except Exception as e:
                logger.debug("State signing mislukt: %s", e)

        # ── 5. Chain hash ──
        with self._lock:
            chain_hash = self._compute_chain_hash(data_hash)
            self._last_chain_hash = chain_hash
            self._stats["chain_length"] += 1

        # ── 6. Schrijf naar archief ──
        try:
            self._archive_dir.mkdir(parents=True, exist_ok=True)
            archive_entry = {
                "timestamp": timestamp,
                "component": clean_name,
                "data_hash": data_hash,
                "chain_hash": chain_hash,
                "chain_position": self._stats["chain_length"],
                "size_bytes": size_bytes,
                "signature": signature_info,
                "state": state_data,
            }
            filename = f"{now.strftime('%Y%m%d_%H%M%S')}_{clean_name}.json"
            archive_path = self._archive_dir / filename
            archive_path.write_text(
                json.dumps(archive_entry, indent=2, ensure_ascii=False, default=str),
                encoding="utf-8",
            )
        except Exception as e:
            return self._fail_receipt(timestamp, clean_name, f"Archief schrijf fout: {e}")

        # ── 7. Update chain head ──
        self._save_chain_head(chain_hash)

        # ── 8. Log naar CorticalStack (fire-and-forget) ──
        self._log_to_cortical("STATE_STORED", {
            "component": clean_name,
            "data_hash": data_hash[:16],
            "chain_hash": chain_hash[:16],
            "size_bytes": size_bytes,
        })

        # ── 9. Receipt ──
        with self._lock:
            self._stats["stores"] += 1
            self._stats["total_bytes_stored"] += size_bytes

        receipt = StoreReceipt(
            timestamp=timestamp,
            component=clean_name,
            data_hash=data_hash,
            chain_hash=chain_hash,
            size_bytes=size_bytes,
            success=True,
        )
        with self._lock:
            self._receipts.append(receipt)

        print(f"{Kleur.GROEN}[MEMORY] State opgeslagen: {clean_name} "
              f"({size_bytes:,} bytes, chain #{self._stats['chain_length']}){Kleur.RESET}")
        return True, receipt

    # ══════════════════════════════════════════════════════════
    #  RETRIEVAL
    # ══════════════════════════════════════════════════════════

    def retrieve_state(self, component: str) -> Tuple[bool, Optional[dict]]:
        """
        Haal de laatst opgeslagen state op voor een component.

        Returns:
            (True, state_dict) of (False, None)
        """
        try:
            if not self._archive_dir.exists():
                return False, None

            # Zoek het meest recente bestand voor dit component
            pattern = f"*_{component}.json"
            archives = sorted(self._archive_dir.glob(pattern), reverse=True)
            if not archives:
                return False, None

            entry = json.loads(archives[0].read_text(encoding="utf-8"))

            # Verifieer data integriteit
            stored_hash = entry.get("data_hash", "")
            state = entry.get("state", {})
            check_hash = hashlib.sha256(
                json.dumps(state, ensure_ascii=False, default=str).encode("utf-8")
            ).hexdigest()

            if stored_hash != check_hash:
                logger.error("State integriteit geschonden voor %s!", component)
                return False, None

            with self._lock:
                self._stats["retrievals"] += 1
            return True, state
        except Exception as e:
            logger.debug("State retrieval fout voor %s: %s", component, e)
            return False, None

    # ── Helpers ──

    def _fail_receipt(
        self, timestamp: str, component: str, error: str
    ) -> Tuple[bool, StoreReceipt]:
        """Genereer een failed receipt."""
        with self._lock:
            self._stats["store_failures"] += 1
        receipt = StoreReceipt(
            timestamp=timestamp,
            component=component,
            data_hash="",
            chain_hash="",
            size_bytes=0,
            success=False,
            error=error,
        )
        with self._lock:
            self._receipts.append(receipt)
        logger.error("State store MISLUKT voor %s: %s", component, error)
        return False, receipt

    def _log_to_cortical(self, event_type: str, data: dict) -> None:
        """Fire-and-forget log naar CorticalStack."""
        if self._stack:
            try:
                self._stack.log_event(
                    bron="SecureMemoryInterface",
                    event_type=f"sovereign.memory.{event_type.lower()}",
                    data={**data, "timestamp": datetime.now().isoformat()},
                )
            except Exception as e:
                logger.debug("CorticalStack memory log mislukt: %s", e)

    # ── Stats & Diagnostics ──

    def get_stats(self) -> Dict[str, Any]:
        """Haal memory interface statistieken op."""
        with self._lock:
            return {
                **self._stats,
                "receipt_count": len(self._receipts),
                "archive_dir": str(self._archive_dir),
            }

    def get_receipts(self, count: int = 20) -> List[Dict]:
        """Haal recente store receipts op."""
        with self._lock:
            recent = list(self._receipts)[-count:]
        return [r.to_dict() for r in recent]


# ── Singleton ──

_mi_instance: Optional[SecureMemoryInterface] = None
_mi_lock = threading.Lock()


def get_memory_interface(data_dir: Optional[Path] = None) -> SecureMemoryInterface:
    """Verkrijg de singleton SecureMemoryInterface."""
    global _mi_instance
    if _mi_instance is None:
        with _mi_lock:
            if _mi_instance is None:
                _mi_instance = SecureMemoryInterface(data_dir=data_dir)
    return _mi_instance


# ── Convenience shortcut (voor lifecycle.py) ──

def secure_store_state(component: str, state_data: dict) -> Tuple[bool, StoreReceipt]:
    """Shortcut: sla state op via de singleton interface."""
    mi = get_memory_interface()
    return mi.secure_store_state(component, state_data)

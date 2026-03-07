"""
Event Signing — HMAC-SHA256 Integriteitslaag voor de NeuralBus.

Ondertekent elk event dat over de bus reist met een geheim.
Verifieert herkomst bij ontvangst. Spoofed events worden
genegeerd en gelogd als aanval.

Gebruik:
    from danny_toolkit.omega_sovereign_core.event_signing import (
        get_event_signer, EventSigner
    )
    signer = get_event_signer()
    signature = signer.sign(event_type, data, bron)
    is_valid  = signer.verify(event_type, data, bron, signature)
"""

import hashlib
import hmac
import json
import logging
import os
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Deque, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

try:
    from danny_toolkit.core.utils import Kleur
except ImportError:
    class Kleur:
        GROEN = ROOD = GEEL = CYAAN = RESET = ""


# ── Constanten ──

_ENV_SIGNING_KEY = "OMEGA_BUS_SIGNING_KEY"
_DEFAULT_KEY = "omega-sovereign-default-key-CHANGE-ME"  # Fallback — .env moet overriden
_MAX_VIOLATION_LOG = 500
_REPLAY_WINDOW_SECONDS = 30  # Events ouder dan dit worden geweigerd


@dataclass
class SigningViolation:
    """Record van een gedetecteerde signing violation."""
    timestamp: str
    event_type: str
    bron: str
    reason: str
    signature_fragment: str = ""

    def to_dict(self) -> Dict[str, str]:
        return {
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "bron": self.bron,
            "reason": self.reason,
            "signature_fragment": self.signature_fragment,
        }


class EventSigner:
    """
    HMAC-SHA256 signing engine voor NeuralBus events.

    Features:
    - Sign: genereert HMAC over (event_type, data, bron, nonce)
    - Verify: valideert HMAC + replay-detectie via nonce window
    - Violation log: houdt aanvallen bij (deque maxlen=500)
    - Nonce tracking: voorkomt replay attacks
    """

    def __init__(self, signing_key: Optional[str] = None):
        self._key = (signing_key or os.environ.get(_ENV_SIGNING_KEY, _DEFAULT_KEY)).encode("utf-8")
        self._lock = threading.Lock()
        self._violations: Deque[SigningViolation] = deque(maxlen=_MAX_VIOLATION_LOG)
        self._seen_nonces: Dict[str, float] = {}  # nonce -> timestamp
        self._stats = {
            "signed": 0,
            "verified_ok": 0,
            "rejected": 0,
            "replay_blocked": 0,
        }
        self._sweeper = None  # ViolationSweeper (lazy, voorkomt import deadlock)
        self._stack = None    # CorticalStack (lazy, fire-and-forget)

        if self._key == _DEFAULT_KEY.encode("utf-8"):
            logger.warning(
                "EventSigner draait met DEFAULT key! "
                "Stel %s in via .env voor productie.", _ENV_SIGNING_KEY
            )

    def _get_stack(self):
        """Lazy CorticalStack — alleen laden bij eerste gebruik, niet in __init__."""
        if self._stack is None and not os.environ.get("DANNY_TEST_MODE"):
            try:
                from danny_toolkit.brain.cortical_stack import get_cortical_stack
                self._stack = get_cortical_stack()
            except (ImportError, Exception) as e:
                logger.debug("CorticalStack lazy-load failed: %s", e)
        return self._stack

    def attach_sweeper(self, sweeper) -> None:
        """Koppel een ViolationSweeper voor fire-and-forget logging."""
        self._sweeper = sweeper
        logger.debug("EventSigner: ViolationSweeper gekoppeld")

    # ── Canonicalisatie ──

    @staticmethod
    def _canonicalize(event_type: str, data: Dict[str, Any], bron: str, nonce: str) -> bytes:
        """
        Deterministische serialisatie van event-inhoud.
        Sorteer keys, gebruik JSON voor reproduceerbaarheid.
        """
        canonical = json.dumps({
            "event_type": event_type,
            "data": data,
            "bron": bron,
            "nonce": nonce,
        }, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
        return canonical.encode("utf-8")

    @staticmethod
    def _generate_nonce() -> str:
        """Genereer een uniek nonce (timestamp + random)."""
        return f"{time.time_ns()}-{os.urandom(8).hex()}"

    # ── Sign ──

    def sign(
        self,
        event_type: str,
        data: Dict[str, Any],
        bron: str,
    ) -> Dict[str, str]:
        """
        Onderteken een event.

        Returns:
            Dict met 'signature' en 'nonce' — voeg deze toe aan het event.
        """
        nonce = self._generate_nonce()
        payload = self._canonicalize(event_type, data, bron, nonce)
        sig = hmac.new(self._key, payload, hashlib.sha256).hexdigest()

        with self._lock:
            self._stats["signed"] += 1
            # Nonce wordt NIET aan _seen_nonces toegevoegd bij sign().
            # Alleen verify() registreert nonces (anti-replay voor INKOMENDE events).

        return {"signature": sig, "nonce": nonce}

    # ── Verify ──

    def verify(
        self,
        event_type: str,
        data: Dict[str, Any],
        bron: str,
        signature: str,
        nonce: str,
    ) -> Tuple[bool, str]:
        """
        Verifieer een event-handtekening.

        Returns:
            (True, "OK") bij geldige handtekening
            (False, "reden") bij ongeldige of replay
        """
        now = time.time()

        # ── Replay detectie ──
        is_replay = False
        with self._lock:
            if nonce in self._seen_nonces:
                self._stats["replay_blocked"] += 1
                is_replay = True
        if is_replay:
            self._record_violation(event_type, bron, "REPLAY", signature[:16])
            return False, "REPLAY: nonce al eerder gezien"

        # ── Nonce leeftijd check ──
        try:
            nonce_ts = int(nonce.split("-")[0]) / 1e9
            age = now - nonce_ts
            if age > _REPLAY_WINDOW_SECONDS:
                with self._lock:
                    self._stats["rejected"] += 1
                self._record_violation(event_type, bron, f"EXPIRED: {age:.1f}s oud", signature[:16])
                return False, f"EXPIRED: nonce is {age:.1f}s oud (max {_REPLAY_WINDOW_SECONDS}s)"
        except (ValueError, IndexError) as e:
            logger.debug("Nonce timestamp parse skipped: %s", e)

        # ── HMAC verificatie ──
        payload = self._canonicalize(event_type, data, bron, nonce)
        expected = hmac.new(self._key, payload, hashlib.sha256).hexdigest()

        if hmac.compare_digest(signature, expected):
            with self._lock:
                self._stats["verified_ok"] += 1
                self._seen_nonces[nonce] = now
            return True, "OK"

        # ── INVALID signature ──
        with self._lock:
            self._stats["rejected"] += 1
        self._record_violation(event_type, bron, "INVALID_SIGNATURE", signature[:16])
        print(f"{Kleur.ROOD}[SOVEREIGN] Spoofed event gedetecteerd: "
              f"{event_type} van '{bron}'{Kleur.RESET}")
        return False, "INVALID: handtekening komt niet overeen"

    # ── Nonce Cleanup ──

    def cleanup_nonces(self, max_age: float = 120.0) -> int:
        """Verwijder verlopen nonces uit het geheugen. Returns: aantal verwijderd."""
        now = time.time()
        with self._lock:
            expired = [n for n, ts in self._seen_nonces.items() if now - ts > max_age]
            for n in expired:
                del self._seen_nonces[n]
        return len(expired)

    # ── Violation Logging ──

    def _record_violation(self, event_type: str, bron: str, reason: str, sig_frag: str) -> None:
        """
        Registreer een signing violation.

        Gebruikt de ViolationSweeper (fire-and-forget) als beschikbaar,
        anders direct CorticalStack. Voorkomt deadlocks.
        """
        violation = SigningViolation(
            timestamp=datetime.now().isoformat(),
            event_type=event_type,
            bron=bron,
            reason=reason,
            signature_fragment=sig_frag,
        )
        with self._lock:
            self._violations.append(violation)

        # Fire-and-forget via sweeper (voorkomt deadlock)
        if self._sweeper:
            self._sweeper.submit(
                event_type="sovereign.signing.violation",
                data=violation.to_dict(),
                bron="EventSigner",
            )
        else:
            # Fallback: lazy direct CorticalStack (enkel als geen sweeper)
            stack = self._get_stack()
            if stack:
                try:
                    stack.log_event(
                        bron="EventSigner",
                        event_type="sovereign.signing.violation",
                        data=violation.to_dict(),
                    )
                except Exception as e:
                    logger.debug("CorticalStack violation log mislukt: %s", e)

        logger.warning("Signing violation: %s | %s | %s", event_type, bron, reason)

    # ── Stats & Diagnostics ──

    def get_stats(self) -> Dict[str, Any]:
        """Haal signing statistieken op."""
        with self._lock:
            return {
                **self._stats,
                "active_nonces": len(self._seen_nonces),
                "violations_total": len(self._violations),
                "using_default_key": self._key == _DEFAULT_KEY.encode("utf-8"),
            }

    def get_violations(self, count: int = 20) -> List[Dict]:
        """Haal recente violations op."""
        with self._lock:
            recent = list(self._violations)[-count:]
        return [v.to_dict() for v in recent]


# ── Singleton ──

_signer_instance: Optional[EventSigner] = None
_signer_lock = threading.Lock()


def get_event_signer(signing_key: Optional[str] = None) -> EventSigner:
    """Verkrijg de singleton EventSigner instantie."""
    global _signer_instance
    if _signer_instance is None:
        with _signer_lock:
            if _signer_instance is None:
                _signer_instance = EventSigner(signing_key=signing_key)
    return _signer_instance

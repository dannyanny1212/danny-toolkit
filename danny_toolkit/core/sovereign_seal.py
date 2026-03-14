"""
SOVEREIGN SEAL — Cryptografische Sessie-Handdruk.

S-Tier sandbox lockdown: elke actieve PrometheusBrain sessie
krijgt een uniek, cryptografisch veilig zegel. Agents en sandbox
processen moeten dit zegel verifiëren voordat data de sandbox
mag verlaten.

Regels:
    - Data MAG altijd IN de sandbox
    - Data UIT de sandbox ALLEEN met geldig sovereign seal
    - FakeBrain / Shadow entities → geen seal → geen exit
    - Verificatie via secrets.compare_digest (timing-attack safe)

Singleton: één seal per proces-sessie. Wordt gegenereerd bij
eerste import en is daarna immutable.
"""

from __future__ import annotations

import logging
import secrets
import threading

logger = logging.getLogger(__name__)

# ── Singleton State ──
_LOCK = threading.Lock()
_INSTANCE: "SovereignSeal | None" = None


class SovereignSeal:
    """Cryptografische sessie-singleton voor sandbox isolatie.

    Genereert een 64-karakter hex token (256-bit entropy) bij
    eerste instantiatie. Verificatie gebruikt constant-time
    comparison om timing side-channels te elimineren.
    """

    __slots__ = ("_seal", "_created_at", "_verify_count", "_reject_count")

    def __init__(self) -> None:
        """Genereer een nieuw cryptografisch zegel."""
        import time
        self._seal: str = secrets.token_hex(32)
        self._created_at: float = time.time()
        self._verify_count: int = 0
        self._reject_count: int = 0
        logger.info(
            "SovereignSeal gegenereerd: %s...%s (256-bit)",
            self._seal[:8], self._seal[-4:],
        )

    @property
    def key(self) -> str:
        """Het actieve sessie-zegel (64 hex chars)."""
        return self._seal

    @property
    def fingerprint(self) -> str:
        """Korte fingerprint voor logging (geen volledige key)."""
        return f"{self._seal[:8]}...{self._seal[-4:]}"

    def verify(self, provided_seal: str) -> bool:
        """Verifieer een aangeboden zegel tegen het actieve zegel.

        Gebruikt secrets.compare_digest voor constant-time
        vergelijking — immuun voor timing attacks.

        Args:
            provided_seal: Het zegel dat geverifieerd moet worden.

        Returns:
            True als het zegel exact overeenkomt.
        """
        if not provided_seal or not isinstance(provided_seal, str):
            self._reject_count += 1
            logger.warning(
                "SovereignSeal REJECT: leeg of ongeldig zegel "
                "(rejects: %d)", self._reject_count,
            )
            return False

        valid = secrets.compare_digest(self._seal, provided_seal)
        if valid:
            self._verify_count += 1
        else:
            self._reject_count += 1
            logger.warning(
                "SovereignSeal REJECT: ongeldig zegel %s...%s "
                "(rejects: %d)",
                provided_seal[:4], provided_seal[-2:],
                self._reject_count,
            )
        return valid

    def stats(self) -> dict:
        """Statistieken voor monitoring."""
        import time
        return {
            "fingerprint": self.fingerprint,
            "uptime_s": round(time.time() - self._created_at, 1),
            "verifications": self._verify_count,
            "rejections": self._reject_count,
        }


def get_sovereign_seal() -> SovereignSeal:
    """Singleton factory — één seal per proces.

    Thread-safe double-checked locking.
    """
    global _INSTANCE
    if _INSTANCE is None:
        with _LOCK:
            if _INSTANCE is None:
                _INSTANCE = SovereignSeal()
    return _INSTANCE

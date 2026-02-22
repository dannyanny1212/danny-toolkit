"""
Alerter — Gecentraliseerd waarschuwingssysteem.

Verstuurt alerts via Telegram, logt naar CorticalStack,
en publiceert op NeuralBus. Ingebouwde deduplicatie
voorkomt alertstormen.

Gebruik:
    from danny_toolkit.core.alerter import get_alerter, AlertLevel
    alerter = get_alerter()
    alerter.alert(AlertLevel.KRITIEK, "Circuit breaker OPEN", bron="governor")
"""

import hashlib
import logging
import threading
import time
from collections import OrderedDict

logger = logging.getLogger(__name__)


class AlertLevel:
    """Alert niveaus."""
    INFO = "info"
    WAARSCHUWING = "waarschuwing"
    KRITIEK = "kritiek"


_LEVEL_ICONS = {
    AlertLevel.INFO: "INFO",
    AlertLevel.WAARSCHUWING: "WAARSCHUWING",
    AlertLevel.KRITIEK: "KRITIEK",
}


class Alerter:
    """
    Gecentraliseerde alert dispatcher met deduplicatie.

    - Hash-based dedup: zelfde (niveau, bericht) binnen DEDUP_INTERVAL wordt geskipt
    - Telegram: notify_sync() / notify() voor bezorging
    - CorticalStack: audit trail
    - NeuralBus: cross-module awareness
    """

    DEDUP_INTERVAL = 300  # 5 minuten tussen identieke alerts
    _MAX_DEDUP_ENTRIES = 200

    def __init__(self):
        self._lock = threading.Lock()
        # OrderedDict: dedup_key -> timestamp van laatste verzending
        self._dedup: OrderedDict[str, float] = OrderedDict()

    def _dedup_key(self, niveau: str, bericht: str) -> str:
        """Genereer dedup hash van (niveau, bericht)."""
        raw = f"{niveau}:{bericht}"
        return hashlib.md5(raw.encode("utf-8")).hexdigest()

    def _is_duplicate(self, key: str) -> bool:
        """Check of alert recent al verzonden is."""
        now = time.time()
        with self._lock:
            if key in self._dedup:
                last_sent = self._dedup[key]
                if now - last_sent < self.DEDUP_INTERVAL:
                    return True
            # Registreer als verzonden
            self._dedup[key] = now
            # FIFO eviction als te groot
            while len(self._dedup) > self._MAX_DEDUP_ENTRIES:
                self._dedup.popitem(last=False)
        return False

    def alert(self, niveau: str, bericht: str, bron: str = "systeem") -> bool:
        """
        Verstuur een alert (sync).

        Returns:
            True als verzonden, False als gededupliceerd.
        """
        key = self._dedup_key(niveau, bericht)
        if self._is_duplicate(key):
            logger.debug("Alert gededupliceerd: %s", bericht[:80])
            return False

        label = _LEVEL_ICONS.get(niveau, niveau.upper())
        formatted = f"[{label}] [{bron}] {bericht}"

        # 1. Telegram notificatie
        try:
            from telegram_bot import notify_sync
            notify_sync(formatted)
        except Exception as e:
            logger.debug("Telegram alert mislukt: %s", e)

        # 2. CorticalStack audit
        try:
            from danny_toolkit.brain.cortical_stack import get_cortical_stack
            stack = get_cortical_stack()
            stack.log_event(
                actor="alerter",
                action="alert_sent",
                details={"niveau": niveau, "bericht": bericht, "bron": bron},
                source="alerter",
            )
        except Exception as e:
            logger.debug("CorticalStack alert log mislukt: %s", e)

        # 3. NeuralBus broadcast
        try:
            from danny_toolkit.core.neural_bus import get_bus, EventTypes
            get_bus().publish(
                EventTypes.SYSTEM_EVENT,
                {"sub_type": "alert", "niveau": niveau, "bericht": bericht, "bron": bron},
                bron="alerter",
            )
        except Exception as e:
            logger.debug("NeuralBus alert publish mislukt: %s", e)

        logger.info("Alert verzonden: %s", formatted)
        return True

    async def alert_async(self, niveau: str, bericht: str, bron: str = "systeem") -> bool:
        """
        Verstuur een alert (async).

        Returns:
            True als verzonden, False als gededupliceerd.
        """
        key = self._dedup_key(niveau, bericht)
        if self._is_duplicate(key):
            logger.debug("Alert gededupliceerd: %s", bericht[:80])
            return False

        label = _LEVEL_ICONS.get(niveau, niveau.upper())
        formatted = f"[{label}] [{bron}] {bericht}"

        # 1. Telegram notificatie (async)
        try:
            from telegram_bot import notify
            await notify(formatted)
        except Exception as e:
            logger.debug("Telegram alert mislukt: %s", e)

        # 2. CorticalStack audit
        try:
            from danny_toolkit.brain.cortical_stack import get_cortical_stack
            stack = get_cortical_stack()
            stack.log_event(
                actor="alerter",
                action="alert_sent",
                details={"niveau": niveau, "bericht": bericht, "bron": bron},
                source="alerter",
            )
        except Exception as e:
            logger.debug("CorticalStack alert log mislukt: %s", e)

        # 3. NeuralBus broadcast
        try:
            from danny_toolkit.core.neural_bus import get_bus, EventTypes
            get_bus().publish(
                EventTypes.SYSTEM_EVENT,
                {"sub_type": "alert", "niveau": niveau, "bericht": bericht, "bron": bron},
                bron="alerter",
            )
        except Exception as e:
            logger.debug("NeuralBus alert publish mislukt: %s", e)

        logger.info("Alert verzonden: %s", formatted)
        return True


# ------------------------------------------------------------------
# Singleton
# ------------------------------------------------------------------

_alerter_instance = None
_alerter_lock = threading.Lock()


def get_alerter() -> Alerter:
    """Singleton accessor voor Alerter."""
    global _alerter_instance
    if _alerter_instance is None:
        with _alerter_lock:
            if _alerter_instance is None:
                _alerter_instance = Alerter()
    return _alerter_instance

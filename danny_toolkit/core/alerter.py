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
from collections import OrderedDict, deque

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
    Gecentraliseerde alert dispatcher met deduplicatie en escalatie.

    - Hash-based dedup: zelfde (niveau, bericht) binnen DEDUP_INTERVAL wordt geskipt
    - Escalatie: herhaalde identieke alerts binnen ESCALATIE_VENSTER escaleren in severity
    - Telegram: notify_sync() / notify() voor bezorging
    - CorticalStack: audit trail
    - NeuralBus: cross-module awareness
    """

    DEDUP_INTERVAL = 300  # 5 minuten tussen identieke alerts
    _MAX_DEDUP_ENTRIES = 200

    ESCALATIE_VENSTER = 600  # 10 minuten
    ESCALATIE_DREMPEL = 3   # 3 keer zelfde alert → escalatie

    # Escalatie volgorde
    _ESCALATIE_KETEN = [
        AlertLevel.INFO,
        AlertLevel.WAARSCHUWING,
        AlertLevel.KRITIEK,
    ]

    def __init__(self):
        self._lock = threading.Lock()
        # OrderedDict: dedup_key -> timestamp van laatste verzending
        self._dedup: OrderedDict[str, float] = OrderedDict()
        # Alert history voor query/analyse
        self._history: deque = deque(maxlen=500)
        self._alert_stats = {
            "info": 0,
            "waarschuwing": 0,
            "kritiek": 0,
            "mislukt": 0,
        }
        # Escalatie tracking: alert_key -> [timestamps]
        self._escalatie_log: dict = {}
        self._escalatie_count: int = 0

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

    def _check_escalatie(self, alert_key: str, huidig_niveau: str) -> str:
        """Check of een alert geëscaleerd moet worden.

        Bij herhaalde identieke alerts binnen ESCALATIE_VENSTER
        wordt het niveau verhoogd (info→waarschuwing→kritiek).

        Args:
            alert_key: Dedup hash van de alert.
            huidig_niveau: Huidig alert niveau.

        Returns:
            Geëscaleerd niveau (of ongewijzigd).
        """
        now = time.time()
        with self._lock:
            if alert_key not in self._escalatie_log:
                self._escalatie_log[alert_key] = []

            # Voeg huidige timestamp toe
            timestamps = self._escalatie_log[alert_key]
            timestamps.append(now)

            # Filter op venster
            timestamps[:] = [
                t for t in timestamps
                if now - t <= self.ESCALATIE_VENSTER
            ]

            if len(timestamps) < self.ESCALATIE_DREMPEL:
                return huidig_niveau

            # Escaleer naar volgend niveau
            try:
                idx = self._ESCALATIE_KETEN.index(huidig_niveau)
                if idx < len(self._ESCALATIE_KETEN) - 1:
                    nieuw_niveau = self._ESCALATIE_KETEN[idx + 1]
                    self._escalatie_count += 1
                    logger.info(
                        "Alert geëscaleerd: %s → %s (key=%s)",
                        huidig_niveau, nieuw_niveau, alert_key[:8],
                    )
                    # Publiceer escalatie event op NeuralBus
                    try:
                        from danny_toolkit.core.neural_bus import get_bus, EventTypes
                        get_bus().publish(
                            EventTypes.ERROR_ESCALATED,
                            {
                                "van": huidig_niveau,
                                "naar": nieuw_niveau,
                                "count": len(timestamps),
                            },
                            bron="alerter",
                        )
                    except Exception as e:
                        logger.debug("NeuralBus escalatie publish mislukt: %s", e)
                    return nieuw_niveau
            except ValueError:
                pass

            return huidig_niveau

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

        # Escalatie check
        niveau = self._check_escalatie(key, niveau)

        label = _LEVEL_ICONS.get(niveau, niveau.upper())
        formatted = f"[{label}] [{bron}] {bericht}"

        # 1. Telegram notificatie
        try:
            from telegram_bot import notify_sync
            notify_sync(formatted)
        except Exception as e:
            logger.debug("Telegram alert mislukt: %s", e)
            with self._lock:
                self._alert_stats["mislukt"] += 1

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

        # Record in history
        with self._lock:
            self._history.append({
                "timestamp": time.time(),
                "niveau": niveau,
                "bericht": bericht,
                "bron": bron,
            })
            if niveau in self._alert_stats:
                self._alert_stats[niveau] += 1

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
            with self._lock:
                self._alert_stats["mislukt"] += 1

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

        # Record in history
        with self._lock:
            self._history.append({
                "timestamp": time.time(),
                "niveau": niveau,
                "bericht": bericht,
                "bron": bron,
            })
            if niveau in self._alert_stats:
                self._alert_stats[niveau] += 1

        return True


    # ─── Query Methods ─────────────────────────────────

    def get_history(
        self, count: int = 50, niveau: str = None,
    ) -> list:
        """Haal recente alerts op.

        Args:
            count: Maximum aantal alerts.
            niveau: Optioneel filter op niveau.

        Returns:
            Lijst van alert dicts (nieuwste eerst).
        """
        with self._lock:
            items = list(self._history)
        # Nieuwste eerst
        items.reverse()
        if niveau:
            items = [a for a in items if a["niveau"] == niveau]
        return items[:count]

    def get_alert_stats(self) -> dict:
        """Retourneer alert tellingen per niveau.

        Returns:
            Dict met info, waarschuwing, kritiek, mislukt, escalation_count.
        """
        with self._lock:
            stats = dict(self._alert_stats)
            stats["escalation_count"] = self._escalatie_count
            return stats

    def clear_history(self):
        """Wis alert history en reset stats."""
        with self._lock:
            self._history.clear()
            for key in self._alert_stats:
                self._alert_stats[key] = 0


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

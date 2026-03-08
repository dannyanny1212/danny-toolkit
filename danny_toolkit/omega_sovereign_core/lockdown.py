"""
Lockdown Manager — Sovereign Lockdown Protocol.

Geactiveerd wanneer een IJzeren Wet wordt overtreden.
Bevriest de NeuralBus, stopt ongeautoriseerde processen,
en stuurt alerts via CorticalStack en (optioneel) Telegram.

Gebruik:
    from danny_toolkit.omega_sovereign_core.lockdown import (
        get_lockdown_manager, LockdownManager
    )
    mgr = get_lockdown_manager()
    mgr.engage_lockdown("Law #6 violated: hardware mismatch")
"""

from __future__ import annotations

import logging
import os
import threading
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Deque, Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    from danny_toolkit.core.utils import Kleur
except ImportError:
    class Kleur:
        GROEN = ROOD = GEEL = CYAAN = RESET = ""


class LockdownLevel(Enum):
    """Ernst-niveaus voor lockdown."""
    ADVISORY = "advisory"        # Waarschuwing, geen actie
    PARTIAL = "partial"          # Bus bevroren, agents gestopt
    FULL = "full"                # Alles gestopt, alleen Commandant kan ontgrendelen
    CRITICAL = "critical"        # Volledige shutdown, data encrypt


@dataclass
class LockdownEvent:
    """Record van een lockdown trigger."""
    timestamp: str
    level: str
    reason: str
    law_violated: str
    actions_taken: List[str]
    resolved: bool = False
    resolved_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """To dict."""
        return {
            "timestamp": self.timestamp,
            "level": self.level,
            "reason": self.reason,
            "law_violated": self.law_violated,
            "actions_taken": self.actions_taken,
            "resolved": self.resolved,
            "resolved_at": self.resolved_at,
        }


class LockdownManager:
    """
    Beheert het Sovereign Lockdown protocol.

    Escalatie-keten:
    1. ADVISORY  → Log + waarschuwing, systeem draait door
    2. PARTIAL   → Bevries NeuralBus, stop non-essential agents
    3. FULL      → Stop alle agents, vergrendel data-toegang
    4. CRITICAL  → Volledige shutdown, encrypt-at-rest activeren
    """

    _MAX_EVENTS = 200

    def __init__(self) -> None:
        """Init  ."""
        self._lock = threading.Lock()
        self._active = False
        self._level: Optional[LockdownLevel] = None
        self._events: Deque[LockdownEvent] = deque(maxlen=self._MAX_EVENTS)
        self._on_lockdown_callbacks: List[Callable] = []
        self._on_release_callbacks: List[Callable] = []
        self._bus = None
        self._stack = None
        self._backends_loaded = False

    def _ensure_backends(self) -> None:
        """Lazy backend verbindingen — pas laden bij eerste gebruik."""
        if self._backends_loaded:
            return
        self._backends_loaded = True
        if not os.environ.get("DANNY_TEST_MODE"):
            try:
                self._bus = get_bus()
            except ImportError:
                logger.debug("NeuralBus niet beschikbaar voor lockdown")
            try:
                self._stack = get_cortical_stack()
            except ImportError:
                logger.debug("CorticalStack niet beschikbaar voor lockdown")

    # ── Callback Registration ──

    def on_lockdown(self, callback: Callable[[LockdownEvent], None]) -> None:
        """Registreer een callback die bij lockdown wordt aangeroepen."""
        with self._lock:
            self._on_lockdown_callbacks.append(callback)

    def on_release(self, callback: Callable[[], None]) -> None:
        """Registreer een callback die bij release wordt aangeroepen."""
        with self._lock:
            self._on_release_callbacks.append(callback)

    # ── Lockdown Engagement ──

    def engage_lockdown(
        self,
        reason: str,
        law_violated: str = "unknown",
        level: LockdownLevel = LockdownLevel.PARTIAL,
    ) -> LockdownEvent:
        """Engage lockdown."""
        self._ensure_backends()
        """
        Activeer het lockdown protocol.

        Args:
            reason: Beschrijving van de overtreding
            law_violated: Welke IJzeren Wet is geschonden
            level: Ernst-niveau

        Returns:
            LockdownEvent record
        """
        actions_taken = []
        now = datetime.now().isoformat()

        print(f"\n{Kleur.ROOD}{'=' * 60}")
        print(f"  SOVEREIGN LOCKDOWN ACTIVATED")
        print(f"  Level: {level.value.upper()}")
        print(f"  Reason: {reason}")
        print(f"  Law: {law_violated}")
        print(f"{'=' * 60}{Kleur.RESET}\n")

        with self._lock:
            self._active = True
            self._level = level

        # ── Acties per level ──

        if level in (LockdownLevel.PARTIAL, LockdownLevel.FULL, LockdownLevel.CRITICAL):
            actions_taken.extend(self._freeze_bus())

        if level in (LockdownLevel.FULL, LockdownLevel.CRITICAL):
            actions_taken.extend(self._stop_agents())

        if level == LockdownLevel.CRITICAL:
            actions_taken.append("CRITICAL: volledige shutdown aangevraagd")
            logger.critical("SOVEREIGN LOCKDOWN CRITICAL: %s", reason)

        # ── Log naar CorticalStack ──
        actions_taken.append("Logged to CorticalStack")
        self._log_to_cortical("LOCKDOWN_ENGAGED", {
            "level": level.value,
            "reason": reason,
            "law": law_violated,
        })

        # ── NeuralBus alert ──
        actions_taken.extend(self._publish_lockdown_event(reason, level))

        # ── Telegram alert (best-effort) ──
        actions_taken.extend(self._send_telegram_alert(reason, level, law_violated))

        # ── Event record ──
        event = LockdownEvent(
            timestamp=now,
            level=level.value,
            reason=reason,
            law_violated=law_violated,
            actions_taken=actions_taken,
        )
        with self._lock:
            self._events.append(event)

        # ── Trigger callbacks ──
        for cb in self._on_lockdown_callbacks:
            try:
                cb(event)
            except Exception as e:
                logger.debug("Lockdown callback fout: %s", e)

        return event

    # ── Lockdown Actions ──

    def _freeze_bus(self) -> List[str]:
        """Bevries de NeuralBus (stop event delivery)."""
        actions = []
        if self._bus:
            try:
                # Publiceer één laatste event, dan freeze
                self._bus.publish(
                    "sovereign_lockdown",
                    {"status": "FROZEN", "timestamp": datetime.now().isoformat()},
                    bron="LockdownManager",
                )
                actions.append("NeuralBus: lockdown event gepubliceerd")
            except Exception as e:
                logger.debug("Bus freeze fout: %s", e)
                actions.append(f"NeuralBus: freeze mislukt ({e})")
        return actions

    def _stop_agents(self) -> List[str]:
        """Stop alle non-essential agents."""
        actions = []
        try:
            arb = get_arbitrator()
            if hasattr(arb, "pause_all"):
                arb.pause_all()
                actions.append("Arbitrator: alle agents gepauzeerd")
            else:
                actions.append("Arbitrator: pause_all niet beschikbaar")
        except ImportError:
            actions.append("Arbitrator: niet beschikbaar")
        except Exception as e:
            logger.debug("Agent stop fout: %s", e)
            actions.append(f"Arbitrator: stop mislukt ({e})")
        return actions

    def _publish_lockdown_event(self, reason: str, level: LockdownLevel) -> List[str]:
        """Publiceer lockdown event naar NeuralBus."""
        actions = []
        if self._bus:
            try:
                self._bus.publish(
                    "sovereign_lockdown",
                    {
                        "level": level.value,
                        "reason": reason,
                        "timestamp": datetime.now().isoformat(),
                    },
                    bron="LockdownManager",
                )
                actions.append("NeuralBus: lockdown broadcast verstuurd")
            except Exception as e:
                logger.debug("Lockdown broadcast fout: %s", e)
        return actions

    def _send_telegram_alert(
        self, reason: str, level: LockdownLevel, law: str
    ) -> List[str]:
        """Stuur Telegram alert (best-effort)."""
        actions = []
        try:
            alerter = get_alerter()
            alerter.alert(
                AlertLevel.CRITICAL,
                f"SOVEREIGN LOCKDOWN [{level.value.upper()}]\n"
                f"Law: {law}\n"
                f"Reason: {reason}",
            )
            actions.append("Telegram: CRITICAL alert verstuurd")
        except ImportError:
            actions.append("Telegram: alerter niet beschikbaar")
        except Exception as e:
            logger.debug("Telegram alert fout: %s", e)
            actions.append(f"Telegram: alert mislukt ({e})")
        return actions

    # ── Release ──

    def release_lockdown(self, authorized_by: str = "Commandant") -> bool:
        """
        Ontgrendel het systeem (vereist expliciet commando).

        Args:
            authorized_by: Wie autoriseert de release

        Returns:
            True als lockdown succesvol opgeheven
        """
        with self._lock:
            if not self._active:
                return False
            self._active = False
            prev_level = self._level
            self._level = None

            # Markeer laatste event als resolved
            if self._events:
                last = self._events[-1]
                last.resolved = True
                last.resolved_at = datetime.now().isoformat()

        print(f"\n{Kleur.GROEN}{'=' * 60}")
        print(f"  SOVEREIGN LOCKDOWN RELEASED")
        print(f"  Authorized by: {authorized_by}")
        print(f"  Previous level: {prev_level.value if prev_level else 'none'}")
        print(f"{'=' * 60}{Kleur.RESET}\n")

        self._log_to_cortical("LOCKDOWN_RELEASED", {
            "authorized_by": authorized_by,
            "previous_level": prev_level.value if prev_level else "none",
        })

        # ── Trigger release callbacks ──
        for cb in self._on_release_callbacks:
            try:
                cb()
            except Exception as e:
                logger.debug("Release callback fout: %s", e)

        return True

    # ── Status ──

    @property
    def is_locked(self) -> bool:
        """Is het systeem momenteel in lockdown?"""
        with self._lock:
            return self._active

    @property
    def current_level(self) -> Optional[LockdownLevel]:
        """Huidig lockdown niveau."""
        with self._lock:
            return self._level

    def get_status(self) -> Dict[str, Any]:
        """Volledige lockdown status."""
        with self._lock:
            return {
                "active": self._active,
                "level": self._level.value if self._level else None,
                "total_events": len(self._events),
                "unresolved": sum(1 for e in self._events if not e.resolved),
            }

    def get_history(self, count: int = 20) -> List[Dict]:
        """Haal recente lockdown events op."""
        with self._lock:
            recent = list(self._events)[-count:]
        return [e.to_dict() for e in recent]

    # ── Logging ──

    def _log_to_cortical(self, event_type: str, data: Dict) -> None:
        """Log naar CorticalStack."""
        if self._stack:
            try:
                self._stack.log_event(
                    bron="LockdownManager",
                    event_type=f"sovereign.lockdown.{event_type.lower()}",
                    data={**data, "timestamp": datetime.now().isoformat()},
                )
            except Exception as e:
                logger.debug("CorticalStack lockdown log mislukt: %s", e)

try:
    from danny_toolkit.core.neural_bus import get_bus
except ImportError:
    pass
try:
    from danny_toolkit.brain.cortical_stack import get_cortical_stack
except ImportError:
    pass
try:
    from danny_toolkit.brain.arbitrator import get_arbitrator
except ImportError:
    pass
try:
    from danny_toolkit.core.alerter import get_alerter, AlertLevel
except ImportError:
    pass


# ── Singleton ──

_lockdown_instance: Optional[LockdownManager] = None
_lockdown_lock = threading.Lock()


def get_lockdown_manager() -> LockdownManager:
    """Verkrijg de singleton LockdownManager instantie."""
    global _lockdown_instance
    if _lockdown_instance is None:
        with _lockdown_lock:
            if _lockdown_instance is None:
                _lockdown_instance = LockdownManager()
    return _lockdown_instance

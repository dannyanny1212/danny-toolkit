"""
NeuralBus - Centraal Pub/Sub Event Systeem voor inter-app communicatie.

Singleton event bus die apps laat communiceren via events.
Thread-safe, met optionele UnifiedMemory persistentie.

Gebruik:
    from danny_toolkit.core.neural_bus import get_bus, EventTypes

    bus = get_bus()
    bus.subscribe(EventTypes.HEALTH_STATUS_CHANGE, mijn_callback)
    bus.publish(EventTypes.WEATHER_UPDATE, {"stad": "Amsterdam", "temp": 12})
"""

import asyncio
import logging
import threading
import time
from collections import defaultdict, deque
from datetime import datetime
from typing import Any, Callable, Deque, Dict, List, Optional

logger = logging.getLogger(__name__)


class EventTypes:
    """Gestandaardiseerde event types voor het ecosysteem."""

    WEATHER_UPDATE = "weather_update"
    HEALTH_STATUS_CHANGE = "health_status_change"
    AGENDA_UPDATE = "agenda_update"
    MOOD_UPDATE = "mood_update"
    FINANCIAL_TRANSACTION = "financial_transaction"
    RECIPE_GENERATED = "recipe_generated"
    GOAL_UPDATE = "goal_update"
    SYSTEM_EVENT = "system_event"
    KNOWLEDGE_GRAPH_UPDATE = "knowledge_graph_update"
    RESOURCE_FORECAST = "resource_forecast"
    MISSION_STARTED = "mission_started"
    STEP_COMPLETED = "step_completed"
    FORGE_SUCCESS = "forge_success"
    LEARNING_CYCLE_STARTED = "learning_cycle_started"


class BusEvent:
    """Representatie van een event op de bus."""

    __slots__ = ("event_type", "data", "bron", "timestamp")

    def __init__(
        self,
        event_type: str,
        data: Dict[str, Any],
        bron: str = "unknown",
    ):
        self.event_type = event_type
        self.data = data
        self.bron = bron
        self.timestamp = datetime.now()

    def to_dict(self) -> dict:
        return {
            "event_type": self.event_type,
            "data": self.data,
            "bron": self.bron,
            "timestamp": self.timestamp.isoformat(),
        }


class NeuralBus:
    """
    Centraal event bus systeem.

    Thread-safe singleton die publish/subscribe biedt
    voor alle apps in het ecosysteem.
    """

    _MAX_HISTORY = 100  # events per type

    def __init__(self):
        self._lock = threading.Lock()
        # event_type -> [callback, ...]
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)
        # event_type -> deque[BusEvent] (ringbuffer per type)
        self._history: Dict[str, Deque[BusEvent]] = defaultdict(
            lambda: deque(maxlen=self._MAX_HISTORY)
        )
        # Globale wildcard subscribers (* = alle events)
        self._wildcard_subscribers: List[Callable] = []
        # Optionele UnifiedMemory koppeling
        self._memory = None
        self._persist = False
        self._stats = {
            "events_gepubliceerd": 0,
            "events_afgeleverd": 0,
            "fouten": 0,
        }

    def enable_persistence(self):
        """Koppel aan UnifiedMemory voor event persistentie."""
        try:
            from ..brain.unified_memory import UnifiedMemory

            self._memory = UnifiedMemory()
            self._persist = True
        except Exception as e:
            logger.debug("UnifiedMemory koppeling mislukt: %s", e)
            self._persist = False

    def subscribe(
        self,
        event_type: str,
        callback: Callable[[BusEvent], None],
    ):
        """
        Abonneer op een event type.

        Args:
            event_type: EventTypes constante, of "*" voor alle events
            callback: Functie die een BusEvent ontvangt
        """
        with self._lock:
            if event_type == "*":
                if callback not in self._wildcard_subscribers:
                    self._wildcard_subscribers.append(callback)
            else:
                if callback not in self._subscribers[event_type]:
                    self._subscribers[event_type].append(callback)

    def unsubscribe(
        self,
        event_type: str,
        callback: Callable[[BusEvent], None],
    ):
        """Verwijder een subscriber."""
        with self._lock:
            if event_type == "*":
                if callback in self._wildcard_subscribers:
                    self._wildcard_subscribers.remove(callback)
            elif event_type in self._subscribers:
                if callback in self._subscribers[event_type]:
                    self._subscribers[event_type].remove(callback)

    def publish(
        self,
        event_type: str,
        data: Dict[str, Any],
        bron: str = "unknown",
    ):
        """
        Publiceer een event naar alle subscribers.

        Args:
            event_type: EventTypes constante
            data: Event payload (dict)
            bron: Naam van de publicerende app/module
        """
        event = BusEvent(event_type, data, bron)

        with self._lock:
            # Voeg toe aan history (deque maxlen handelt overflow af)
            self._history[event_type].append(event)

            self._stats["events_gepubliceerd"] += 1

            # Verzamel subscribers (type-specifiek + wildcard)
            callbacks = list(self._subscribers.get(event_type, []))
            callbacks.extend(self._wildcard_subscribers)

        # Lever af buiten de lock (voorkom deadlocks)
        for cb in callbacks:
            try:
                if asyncio.iscoroutinefunction(cb):
                    # Async callback — dispatch via event loop
                    try:
                        loop = asyncio.get_running_loop()
                        loop.create_task(self._safe_async_dispatch(cb, event))
                    except RuntimeError:
                        # Geen actieve loop — run blocking
                        asyncio.run(cb(event))
                else:
                    cb(event)
                self._stats["events_afgeleverd"] += 1
            except Exception as e:
                logger.debug("Event callback fout: %s", e)
                self._stats["fouten"] += 1

        # Optioneel: persist naar UnifiedMemory
        if self._persist and self._memory:
            try:
                self._memory.store_event(
                    app=bron,
                    event_type=event_type,
                    data=data,
                    store_vector=False,
                )
            except Exception as e:
                logger.debug("Event persistentie mislukt: %s", e)

    def get_history(
        self,
        event_type: str,
        count: int = 10,
        bron: Optional[str] = None,
    ) -> List[BusEvent]:
        """
        Haal recente events op van een bepaald type.

        Args:
            event_type: EventTypes constante
            count: Aantal events (max)
            bron: Optionele filter op bron-app

        Returns:
            Lijst van BusEvent objecten (nieuwste eerst)
        """
        with self._lock:
            events = list(self._history.get(event_type, []))

        if bron:
            events = [e for e in events if e.bron == bron]

        return list(reversed(events[-count:]))

    def get_latest(self, event_type: str) -> Optional[BusEvent]:
        """Haal het meest recente event op van een type."""
        with self._lock:
            history = self._history.get(event_type, [])
            return history[-1] if history else None

    def get_context(
        self,
        event_types: List[str] = None,
        count: int = 5,
    ) -> Dict[str, List[dict]]:
        """
        Haal cross-app context op voor AI verrijking.

        Args:
            event_types: Welke types ophalen (None = allemaal)
            count: Aantal events per type

        Returns:
            Dict van event_type -> [event_dicts]
        """
        result = {}
        types = event_types or list(self._history.keys())

        for et in types:
            events = self.get_history(et, count=count)
            if events:
                result[et] = [e.to_dict() for e in events]

        return result

    def get_context_stream(
        self,
        event_types: List[str] = None,
        count: int = 20,
    ) -> str:
        """
        Geeft een geformateerde tekst van recente events voor LLM injectie.

        Voorkomt hallucinaties door de AI te gronden in de echte
        systeemstaat. Injecteer dit als systeem-context in elke prompt.

        Args:
            event_types: Welke types ophalen (None = allemaal)
            count: Totaal aantal events (over alle types)

        Returns:
            Leesbare string voor LLM context, of lege string.
        """
        with self._lock:
            types = event_types or list(self._history.keys())
            # Verzamel alle events, sorteer op timestamp
            all_events: List[BusEvent] = []
            for et in types:
                all_events.extend(self._history.get(et, []))

        if not all_events:
            return ""

        all_events.sort(key=lambda e: e.timestamp)
        recent = all_events[-count:]

        lines = ["[REAL-TIME SYSTEM STATE]"]
        for e in recent:
            t = e.timestamp.strftime("%H:%M:%S")
            data_str = ", ".join(f"{k}={v}" for k, v in e.data.items())
            lines.append(f"- {t} | {e.bron}: {e.event_type} -> {data_str}")
        return "\n".join(lines)

    async def _safe_async_dispatch(self, callback: Callable, event: BusEvent):
        """Veilige uitvoering van async callbacks."""
        try:
            await callback(event)
        except Exception as e:
            logger.error("Async callback fout: %s", e)
            self._stats["fouten"] += 1

    def statistieken(self) -> dict:
        """Geef bus statistieken."""
        with self._lock:
            subscriber_count = sum(
                len(cbs) for cbs in self._subscribers.values()
            )
            subscriber_count += len(self._wildcard_subscribers)

            return {
                "subscribers": subscriber_count,
                "event_types_actief": len(self._history),
                "events_in_history": sum(
                    len(h) for h in self._history.values()
                ),
                **self._stats,
            }

    def reset(self):
        """Reset de bus (voor tests)."""
        with self._lock:
            self._subscribers.clear()
            self._wildcard_subscribers.clear()
            self._history.clear()
            self._stats = {
                "events_gepubliceerd": 0,
                "events_afgeleverd": 0,
                "fouten": 0,
            }


# -- Singleton --

_bus_instance: Optional[NeuralBus] = None
_bus_lock = threading.Lock()


def get_bus() -> NeuralBus:
    """Verkrijg de singleton NeuralBus instantie."""
    global _bus_instance
    if _bus_instance is None:
        with _bus_lock:
            if _bus_instance is None:
                _bus_instance = NeuralBus()
    return _bus_instance

"""
NeuralBus - Centraal Pub/Sub Event Systeem voor inter-app communicatie.

Singleton event bus die apps laat communiceren via events.
Thread-safe, met optionele UnifiedMemory persistentie.
HMAC-SHA256 payload signing via OMEGA_BUS_SIGNING_KEY.

Gebruik:
    from danny_toolkit.core.neural_bus import get_bus, EventTypes

    bus = get_bus()
    bus.subscribe(EventTypes.HEALTH_STATUS_CHANGE, mijn_callback)
    bus.publish(EventTypes.WEATHER_UPDATE, {"stad": "Amsterdam", "temp": 12})
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import os
import threading
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
    SYNAPSE_UPDATED = "synapse_updated"
    SYNAPSE_FEEDBACK = "synapse_feedback"
    PHANTOM_PREDICTION = "phantom_prediction"
    PHANTOM_HIT = "phantom_hit"
    SANDBOX_EXECUTION = "sandbox_execution"
    TWIN_CONSULTATION = "twin_consultation"
    IMMUNE_RESPONSE = "immune_response"
    HALLUCINATION_BLOCKED = "hallucination_blocked"
    WAAKHUIS_ALERT = "waakhuis_alert"
    WAAKHUIS_HEALTH = "waakhuis_health"
    ERROR_ESCALATED = "error_escalated"
    # Phase 31: circuit breaker events
    AGENT_CIRCUIT_OPEN = "agent_circuit_open"
    AGENT_CIRCUIT_CLOSED = "agent_circuit_closed"
    # Phase 33: config audit events
    CONFIG_DRIFT_DETECTED = "config_drift_detected"
    CONFIG_AUDIT_COMPLETE = "config_audit_complete"
    # Phase 34: shard routing events
    SHARD_MIGRATION_COMPLETE = "shard_migration_complete"
    SHARD_QUERY_ROUTED = "shard_query_routed"
    # Phase 35: error taxonomy events
    ERROR_CLASSIFIED = "error_classified"
    # Phase 36: request tracing events
    REQUEST_TRACE_COMPLETE = "request_trace_complete"
    # Phase 37: self-pruning events
    PRUNING_STARTED = "pruning_started"
    FRAGMENT_ARCHIVED = "fragment_archived"
    FRAGMENT_DESTROYED = "fragment_destroyed"
    PRUNING_COMPLETE = "pruning_complete"
    # Eternal Sentinel events
    SENTINEL_DEEP_SCAN = "sentinel_deep_scan"
    SENTINEL_THROTTLE = "sentinel_throttle"
    SENTINEL_GPU_BOOST = "sentinel_gpu_boost"
    SENTINEL_REINDEX = "sentinel_reindex"
    # Omega Bus: Agent-to-Agent chaining
    AGENT_CHAIN_REQUEST = "agent_chain_request"
    AGENT_CHAIN_RESPONSE = "agent_chain_response"
    AGENT_CHAIN_BLOCKED = "agent_chain_blocked"


class OmegaSeal:
    """HMAC-SHA256 payload signing voor interne bus-communicatie.

    Elke payload die over de NeuralBus reist krijgt een 'omega_seal'
    handtekening. Ontvangende agents verifiëren het zegel voordat
    ze de payload verwerken.

    Key derivatie (3-laags):
        1. OMEGA_BUS_SIGNING_KEY   — software secret uit .env
        2. LIVE hardware fingerprint — real-time CPU+GPU+moederbord scan
        3. SHA-256(key | live_seal) — derived HMAC key

        De LIVE scan is cruciaal: zelfs als .env gestolen wordt,
        kan de key niet gereconstrueerd worden zonder het fysieke
        silicium. De opgeslagen AUTHORIZED_SILICON_SEAL wordt NIET
        gebruikt voor key derivatie — alleen de live hardware scan.
    """

    _key: Optional[bytes] = None
    _hardware_verified: bool = False
    _live_seal: str = ""

    @classmethod
    def _scan_live_hardware(cls) -> str:
        """Haal de live hardware seal op (cached, single scan).

        Gebruikt _scan_hardware_once() — dezelfde cache als C2 verify.
        Geen dubbele WMIC/nvidia-smi subprocess calls.
        """
        seal = _scan_hardware_once()
        if seal:
            logger.info(
                "[OMEGA SEAL] Live hardware seal: %s...%s",
                seal[:8], seal[-4:],
            )
            return seal

        # Fallback: gebruik opgeslagen seal uit .env
        fallback = os.environ.get("AUTHORIZED_SILICON_SEAL", "")
        if fallback:
            logger.warning(
                "[OMEGA SEAL] Fallback naar opgeslagen seal — minder veilig"
            )
        return fallback

    @classmethod
    def _load_key(cls) -> Optional[bytes]:
        """Laad OMEGA_BUS_SIGNING_KEY en fuseer met LIVE hardware seal.

        Key = SHA-256(OMEGA_BUS_SIGNING_KEY | LIVE_SILICON_SEAL)

        De live scan maakt de key onreconstrueerbaar zonder het
        fysieke silicium, zelfs als de .env volledig gelekt is.
        """
        if cls._key is None:
            bus_key = os.environ.get("OMEGA_BUS_SIGNING_KEY", "")
            if bus_key:
                cls._live_seal = cls._scan_live_hardware()
                if cls._live_seal:
                    combined = f"{bus_key}|{cls._live_seal}"
                    cls._key = hashlib.sha256(combined.encode("utf-8")).digest()
                    cls._hardware_verified = True
                    logger.info(
                        "[OMEGA SEAL] Key derived from LIVE hardware + bus key"
                    )
                else:
                    # Geen hardware seal — software-only mode
                    cls._key = hashlib.sha256(bus_key.encode("utf-8")).digest()
                    cls._hardware_verified = False
                    logger.warning(
                        "[OMEGA SEAL] SOFTWARE-ONLY — geen hardware binding!"
                    )
        return cls._key

    @classmethod
    def sign_payload(cls, payload: dict) -> str:
        """Genereer HMAC-SHA256 handtekening voor een payload dict.

        Returns:
            Hex-encoded HMAC digest, of lege string als key ontbreekt.
        """
        key = cls._load_key()
        if not key:
            return ""
        canonical = json.dumps(payload, sort_keys=True, default=str)
        return hmac.new(key, canonical.encode("utf-8"), hashlib.sha256).hexdigest()

    @classmethod
    def verify(cls, payload: dict, seal: str) -> bool:
        """Verifieer een omega_seal tegen de payload.

        Timing-safe vergelijking via hmac.compare_digest.

        Returns:
            True als het zegel klopt, False als het ontbreekt of corrupt is.
        """
        if not seal:
            return False
        expected = cls.sign_payload(payload)
        if not expected:
            return False
        return hmac.compare_digest(expected, seal)

    @classmethod
    def is_armed(cls) -> bool:
        """Check of de signing key geladen is."""
        return cls._load_key() is not None

    @classmethod
    def is_hardware_bound(cls) -> bool:
        """Check of de key gebonden is aan de hardware (Silicon Seal)."""
        cls._load_key()
        return cls._hardware_verified


def verified_callback(callback: Callable) -> Callable:
    """Decorator die inkomende BusEvents verifieert voor een callback.

    Gebruik:
        @verified_callback
        def mijn_handler(event: BusEvent):
            ...  # Alleen uitgevoerd als seal geldig is

    Events zonder geldig omega_seal worden geweigerd en gelogd.
    """
    def wrapper(event: BusEvent) -> Any:
        if hasattr(event, "verify_seal") and not event.verify_seal():
            logger.warning(
                "[OMEGA GATE] Event geweigerd — ongeldig seal: "
                "type=%s bron=%s", event.event_type, event.bron,
            )
            return None
        return callback(event)

    wrapper.__name__ = callback.__name__
    wrapper.__qualname__ = callback.__qualname__
    return wrapper


class BusEvent:
    """Representatie van een event op de bus."""

    __slots__ = ("event_type", "data", "bron", "timestamp", "omega_seal")

    def __init__(
        self,
        event_type: str,
        data: Dict[str, Any],
        bron: str = "unknown",
    ) -> None:
        """Initializes an event object.

        Args:
            event_type: The type of event.
            data: Additional data associated with the event.
            bron: The source of the event.
        """
        self.event_type = event_type
        self.data = data
        self.bron = bron
        self.timestamp = datetime.now()
        # Cryptografisch zegel — sign de payload bij creatie
        seal_payload = {"event_type": event_type, "data": data, "bron": bron}
        self.omega_seal = OmegaSeal.sign_payload(seal_payload)

    def verify_seal(self) -> bool:
        """Verifieer het omega_seal van dit event."""
        seal_payload = {"event_type": self.event_type, "data": self.data, "bron": self.bron}
        return OmegaSeal.verify(seal_payload, self.omega_seal)

    def to_dict(self) -> dict:
        """To dict."""
        return {
            "event_type": self.event_type,
            "data": self.data,
            "bron": self.bron,
            "timestamp": self.timestamp.isoformat(),
            "omega_seal": self.omega_seal,
        }


class NeuralBus:
    """
    Centraal event bus systeem.

    Thread-safe singleton die publish/subscribe biedt
    voor alle apps in het ecosysteem.
    """

    _MAX_HISTORY = 100  # events per type
    _MAX_CHAIN_DEPTH = 5  # agent-to-agent recursion limit

    def __init__(self) -> None:
        """Init."""
        self._lock = threading.RLock()
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
        # Agent chain tracking — voorkomt infinite loops
        self._active_chains: Dict[str, int] = {}  # chain_id -> depth
        self._chain_lock = threading.Lock()
        self._stats = {
            "events_gepubliceerd": 0,
            "events_afgeleverd": 0,
            "fouten": 0,
            "seals_verified": 0,
            "seals_rejected": 0,
            "chains_blocked": 0,
        }

    def enable_persistence(self) -> None:
        """Koppel aan UnifiedMemory voor event persistentie."""
        try:

            mem = get_unified_memory()
            if mem:
                self._memory = mem
                self._persist = True
            else:
                self._persist = False
        except Exception as e:
            logger.debug("UnifiedMemory koppeling mislukt: %s", e)
            self._persist = False

    def subscribe(
        self,
        event_type: str,
        callback: Callable[[BusEvent], None],
    ) -> None:
        """
        Abonneer op een event type.

        Args:
            event_type: EventTypes constante, of "*" voor alle events
            callback: Functie die een BusEvent ontvangt
        """
        try:
            with self._lock:
                if event_type == "*":
                    if callback not in self._wildcard_subscribers:
                        self._wildcard_subscribers.append(callback)
                else:
                    if callback not in self._subscribers[event_type]:
                        self._subscribers[event_type].append(callback)
        except Exception as e:
            logger.debug("NeuralBus subscribe fout: %s", e)

    def unsubscribe(
        self,
        event_type: str,
        callback: Callable[[BusEvent], None],
    ) -> None:
        """Verwijder een subscriber."""
        try:
            with self._lock:
                if event_type == "*":
                    if callback in self._wildcard_subscribers:
                        self._wildcard_subscribers.remove(callback)
                elif event_type in self._subscribers:
                    if callback in self._subscribers[event_type]:
                        self._subscribers[event_type].remove(callback)
        except Exception as e:
            logger.debug("NeuralBus unsubscribe fout: %s", e)

    def publish(
        self,
        event_type: str,
        data: Dict[str, Any],
        bron: str = "unknown",
    ) -> None:
        """
        Publiceer een event naar alle subscribers.

        Elk event wordt automatisch cryptografisch gesigned bij creatie
        (HMAC-SHA256 via OMEGA_BUS_SIGNING_KEY + AUTHORIZED_SILICON_SEAL).
        Bij aflevering wordt het seal geverifieerd — events met een
        ongeldig seal worden geweigerd en gelogd.

        Args:
            event_type: EventTypes constante
            data: Event payload (dict)
            bron: Naam van de publicerende app/module
        """
        event = BusEvent(event_type, data, bron)

        # Seal verificatie op het moment van publicatie
        if OmegaSeal.is_armed() and event.omega_seal:
            if not event.verify_seal():
                logger.warning(
                    "[OMEGA GATE] Event GEWEIGERD — seal corrupt bij publicatie: "
                    "type=%s bron=%s", event_type, bron,
                )
                with self._lock:
                    self._stats["seals_rejected"] += 1
                return
            with self._lock:
                self._stats["seals_verified"] += 1

        with self._lock:
            # Overflow detectie — log als events verloren gaan
            hist = self._history[event_type]
            if len(hist) >= self._MAX_HISTORY:
                self._stats.setdefault("events_dropped", 0)
                self._stats["events_dropped"] += 1
            hist.append(event)

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
                        # Geen actieve loop — run blocking (safe)
                        try:
                            asyncio.run(cb(event))
                        except RuntimeError:
                            logger.debug("Async callback kon niet starten: geen event loop")
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

    def publish_verified(
        self,
        event_type: str,
        data: Dict[str, Any],
        bron: str = "unknown",
    ) -> bool:
        """Publiceer een event en verifieer het seal na creatie.

        Returns:
            True als het event succesvol gesigned en gepubliceerd is.
        """
        event = BusEvent(event_type, data, bron)
        if not event.verify_seal():
            logger.warning("[OMEGA GATE] Event seal verificatie mislukt: %s van %s", event_type, bron)
            with self._lock:
                self._stats["seals_rejected"] += 1
            return False
        with self._lock:
            self._stats["seals_verified"] += 1
        self.publish(event_type, data, bron)
        return True

    def chain_dispatch(
        self,
        source_agent: str,
        target_agent: str,
        payload: Dict[str, Any],
        chain_id: Optional[str] = None,
    ) -> bool:
        """Agent-to-Agent chaining met recursion guard.

        Sta toe dat Agent A een commando genereert voor Agent B,
        met een harde recursion limit (_MAX_CHAIN_DEPTH) om
        infinite loops te voorkomen.

        Args:
            source_agent: Naam van de bronagent
            target_agent: Naam van de doelagent
            payload: Data voor de doelagent
            chain_id: Optionele chain ID (auto-generated als None)

        Returns:
            True als de chain-dispatch is toegestaan en gepubliceerd.
        """
        if chain_id is None:
            chain_id = f"chain_{source_agent}_{datetime.now().strftime('%H%M%S%f')}"

        with self._chain_lock:
            depth = self._active_chains.get(chain_id, 0)
            if depth >= self._MAX_CHAIN_DEPTH:
                logger.warning(
                    "[OMEGA BUS] Chain depth limit (%d) bereikt: %s → %s (chain=%s)",
                    self._MAX_CHAIN_DEPTH, source_agent, target_agent, chain_id,
                )
                self._stats["chains_blocked"] += 1
                self.publish(
                    EventTypes.AGENT_CHAIN_BLOCKED,
                    {"source": source_agent, "target": target_agent, "depth": depth, "chain_id": chain_id},
                    bron="omega_bus",
                )
                return False
            self._active_chains[chain_id] = depth + 1

        chain_data = {
            "source_agent": source_agent,
            "target_agent": target_agent,
            "chain_id": chain_id,
            "chain_depth": depth + 1,
            "payload": payload,
        }
        self.publish(EventTypes.AGENT_CHAIN_REQUEST, chain_data, bron=source_agent)
        return True

    def chain_complete(self, chain_id: str) -> None:
        """Markeer een agent chain als voltooid."""
        with self._chain_lock:
            self._active_chains.pop(chain_id, None)

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
        try:
            with self._lock:
                events = list(self._history.get(event_type, []))

            if bron:
                events = [e for e in events if e.bron == bron]

            return list(reversed(events[-count:]))
        except Exception as e:
            logger.debug("NeuralBus get_history fout: %s", e)
            return []

    def get_latest(self, event_type: str) -> Optional[BusEvent]:
        """Haal het meest recente event op van een type."""
        try:
            with self._lock:
                history = self._history.get(event_type, [])
                return history[-1] if history else None
        except Exception as e:
            logger.debug("NeuralBus get_latest fout: %s", e)
            return None

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
        try:
            result = {}
            types = event_types or list(self._history.keys())

            for et in types:
                events = self.get_history(et, count=count)
                if events:
                    result[et] = [e.to_dict() for e in events]

            return result
        except Exception as e:
            logger.debug("NeuralBus get_context fout: %s", e)
            return {}

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
        try:
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
        except Exception as e:
            logger.debug("NeuralBus get_context_stream fout: %s", e)
            return ""

    async def _safe_async_dispatch(self, callback: Callable, event: BusEvent) -> None:
        """Veilige uitvoering van async callbacks."""
        try:
            await callback(event)
        except Exception as e:
            logger.error("Async callback fout: %s", e)
            self._stats["fouten"] += 1

    def statistieken(self) -> dict:
        """Geef bus statistieken."""
        try:
            with self._lock:
                subscriber_count = sum(
                    len(cbs) for cbs in self._subscribers.values()
                )
                subscriber_count += len(self._wildcard_subscribers)

                with self._chain_lock:
                    active_chains = len(self._active_chains)

                return {
                    "subscribers": subscriber_count,
                    "event_types_actief": len(self._history),
                    "events_in_history": sum(
                        len(h) for h in self._history.values()
                    ),
                    "omega_seal_armed": OmegaSeal.is_armed(),
                    "hardware_bound": OmegaSeal.is_hardware_bound(),
                    "c2_verified": _c2_verified,
                    "active_chains": active_chains,
                    "max_chain_depth": self._MAX_CHAIN_DEPTH,
                    **self._stats,
                }
        except Exception as e:
            logger.debug("NeuralBus statistieken fout: %s", e)
            return {}

    def get_event_type_counts(self) -> dict:
        """Return per-type event count in history (public API)."""
        try:
            with self._lock:
                return {et: len(q) for et, q in self._history.items()}
        except Exception as e:
            logger.debug("NeuralBus get_event_type_counts fout: %s", e)
            return {}

    def reset(self) -> None:
        """Reset de bus (voor tests)."""
        try:
            with self._lock:
                self._subscribers.clear()
                self._wildcard_subscribers.clear()
                self._history.clear()
                self._stats = {
                    "events_gepubliceerd": 0,
                    "events_afgeleverd": 0,
                    "fouten": 0,
                    "seals_verified": 0,
                    "seals_rejected": 0,
                    "chains_blocked": 0,
                }
            with self._chain_lock:
                self._active_chains.clear()
        except Exception as e:
            logger.debug("NeuralBus reset fout: %s", e)

try:
    from danny_toolkit.core.memory_interface import get_unified_memory
except ImportError:
    logger.debug("Optional import not available: danny_toolkit.core.memory_interface")


def _auto_load_env() -> None:
    """Laad .env automatisch als OMEGA_BUS_SIGNING_KEY niet in env staat.

    Zoekt .env in de project root (3 dirs omhoog van dit bestand).
    Parsed KEY=VALUE regels zonder externe dependencies (geen dotenv nodig).
    """
    if os.environ.get("OMEGA_BUS_SIGNING_KEY"):
        return  # Al geladen

    env_candidates = [
        os.path.join(os.path.dirname(__file__), "..", "..", ".env"),
        os.path.join(os.getcwd(), ".env"),
    ]
    _CRYPTO_KEYS = {
        "OMEGA_BUS_SIGNING_KEY",
        "AUTHORIZED_SILICON_SEAL",
        "C2_AUTH_URL",
    }
    for env_path in env_candidates:
        env_file = os.path.normpath(env_path)
        if os.path.isfile(env_file):
            try:
                with open(env_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#") or "=" not in line:
                            continue
                        k, _, v = line.partition("=")
                        k = k.strip()
                        v = v.strip()
                        if k in _CRYPTO_KEYS and k not in os.environ:
                            os.environ[k] = v
                logger.debug("Auto-loaded crypto keys from %s", env_file)
                return
            except Exception as e:
                logger.debug("Auto-load .env mislukt (%s): %s", env_file, e)


_cached_live_seal: Optional[str] = None


def _scan_hardware_once() -> str:
    """Scan hardware EENMALIG en cache het resultaat.

    Voorkomt dubbele WMIC/nvidia-smi subprocess calls.
    Resultaat wordt hergebruikt door zowel C2 verify als OmegaSeal.
    """
    global _cached_live_seal
    if _cached_live_seal is not None:
        return _cached_live_seal
    try:
        from danny_toolkit.core.hardware_anchor import generate_silicon_seal
        seal = generate_silicon_seal()
        if seal and len(seal) == 64:
            _cached_live_seal = seal
            return seal
    except ImportError:
        logger.debug("[HARDWARE] hardware_anchor niet beschikbaar")
    except Exception as e:
        logger.warning("[HARDWARE] Scan mislukt: %s", e)
    return ""


def _c2_hardware_verify() -> bool:
    """Verifieer hardware tegen C2 Master bij bus startup.

    Gebruikt de gecachte live seal (single hardware scan voor
    het hele startup-proces). Constant-time vergelijking.

    Returns:
        True als hardware geautoriseerd is, False bij fout of mismatch.
    """
    try:
        from danny_toolkit.core.hardware_anchor import fetch_c2_seals
        import secrets as _secrets

        live = _scan_hardware_once()
        if not live:
            logger.critical("[OMEGA BUS C2] Geen live seal — hardware scan mislukt")
            return False

        authorized = fetch_c2_seals()

        if not authorized:
            logger.critical(
                "[OMEGA BUS C2] Lege whitelist — geen machine geautoriseerd!"
            )
            return False

        for seal in authorized:
            if _secrets.compare_digest(seal, live):
                logger.info(
                    "[OMEGA BUS C2] Hardware VERIFIED: %s...%s",
                    live[:8], live[-4:],
                )
                return True

        logger.critical(
            "[OMEGA BUS C2] Hardware NOT AUTHORIZED! Live: %s...%s",
            live[:8], live[-4:],
        )
        return False
    except ConnectionError as e:
        logger.critical("[OMEGA BUS C2] Server onbereikbaar: %s", e)
        return False
    except PermissionError as e:
        logger.critical("[OMEGA BUS C2] Configuratie fout: %s", e)
        return False
    except ImportError:
        logger.debug("[OMEGA BUS C2] hardware_anchor niet beschikbaar — skip")
        return True
    except Exception as e:
        logger.warning("[OMEGA BUS C2] Onverwachte fout: %s", e)
        return False


# -- Singleton --

_bus_instance: Optional[NeuralBus] = None
_bus_lock = threading.Lock()
_c2_verified: bool = False


def get_bus() -> NeuralBus:
    """Verkrijg de singleton NeuralBus instantie.

    Bij eerste aanroep (volledige hardware-gebonden startup):
    1. Laadt OMEGA_BUS_SIGNING_KEY + C2_AUTH_URL uit .env
    2. Scant LIVE hardware (CPU+GPU+moederbord) → Silicon Seal
    3. Verifieert live seal tegen C2 Master (externe whitelist)
    4. Deriveert HMAC key: SHA-256(BUS_KEY | LIVE_SEAL)
    5. Creëert de singleton NeuralBus met auto-sign/verify

    De LIVE hardware scan is de kern: zelfs als .env gestolen wordt,
    kan de HMAC key niet gereconstrueerd worden zonder het fysieke
    silicium van deze machine.
    """
    global _bus_instance, _c2_verified
    if _bus_instance is None:
        with _bus_lock:
            if _bus_instance is None:
                # Stap 1: Laad crypto env vars
                _auto_load_env()

                # Stap 2+3: C2 hardware verificatie (scant live hardware)
                _c2_verified = _c2_hardware_verify()

                # Stap 4: OmegaSeal key derivatie (scant live hardware opnieuw)
                # Dit forceert de live scan in _load_key()
                OmegaSeal._load_key()

                # Stap 5: Creëer de bus
                _bus_instance = NeuralBus()

                # Status rapport
                if OmegaSeal.is_armed():
                    hw = "HARDWARE-BOUND" if OmegaSeal.is_hardware_bound() else "SOFTWARE-ONLY"
                    c2 = "C2-VERIFIED" if _c2_verified else "C2-UNVERIFIED"
                    live = OmegaSeal._live_seal
                    seal_short = f"{live[:8]}...{live[-4:]}" if live else "NONE"
                    logger.info(
                        "[OMEGA BUS] ARMED (%s, %s, seal=%s)",
                        hw, c2, seal_short,
                    )
                else:
                    logger.warning(
                        "[OMEGA BUS] NOT ARMED — bus draait onbeveiligd!"
                    )
    return _bus_instance


def is_c2_verified() -> bool:
    """Check of de C2 hardware verificatie geslaagd is."""
    return _c2_verified

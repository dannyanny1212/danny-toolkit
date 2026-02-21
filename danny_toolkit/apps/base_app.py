"""Base klasse voor alle toolkit apps."""

import json
import logging
import os
from typing import Any, Callable, Dict, List, Optional
from ..core.config import Config

logger = logging.getLogger(__name__)

try:
    from anthropic import Anthropic
    AI_BESCHIKBAAR = True
except ImportError:
    AI_BESCHIKBAAR = False

try:
    from ..core.neural_bus import get_bus, BusEvent, EventTypes
    HAS_BUS = True
except ImportError:
    HAS_BUS = False


class BaseApp:
    """Basis klasse met gedeelde AI en data functionaliteit."""

    VERSIE = "2.0"

    # Override in subclass: welke event types deze app publiceert
    PUBLICEERT: List[str] = []
    # Override in subclass: welke event types deze app ontvangt
    LUISTERT_NAAR: List[str] = []

    def __init__(self, data_bestand: str):
        Config.ensure_dirs()
        self.bestand = Config.APPS_DATA_DIR / data_bestand
        self.bestand.parent.mkdir(exist_ok=True, parents=True)
        self.data = self._laad_data()
        self.client = None
        self._init_ai()
        self._bus_handlers: Dict[str, Callable] = {}
        self._init_bus()

    def _init_ai(self):
        """Initialiseer AI client."""
        if AI_BESCHIKBAAR:
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if api_key:
                try:
                    self.client = Anthropic(api_key=api_key)
                except Exception as e:
                    logger.debug("Anthropic client init error: %s", e)
                    self.client = None

    def _ai_request(self, prompt: str,
                     max_tokens: int = 500) -> str:
        """Maak een AI request."""
        if not self.client:
            return None
        try:
            response = self.client.messages.create(
                model=Config.CLAUDE_MODEL,
                max_tokens=max_tokens,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            return response.content[0].text
        except Exception as e:
            logger.debug("AI request error: %s", e)
            return None

    # ==================== NEURAL BUS ====================

    def _init_bus(self):
        """Initialiseer NeuralBus subscriptions."""
        if not HAS_BUS:
            return
        for event_type in self.LUISTERT_NAAR:
            handler = getattr(self, f"_on_{event_type}", None)
            if handler:
                self._bus_handlers[event_type] = handler
                get_bus().subscribe(event_type, handler)

    def publish(self, event_type: str, data: Dict[str, Any]):
        """Publiceer een event op de NeuralBus."""
        if not HAS_BUS:
            return
        bron = self.__class__.__name__.replace("App", "").lower()
        get_bus().publish(event_type, data, bron=bron)

    def get_bus_context(
        self,
        event_types: List[str] = None,
        count: int = 3,
    ) -> str:
        """
        Haal cross-app context op als tekst voor AI verrijking.

        Returns:
            Leesbare tekst met recente events van andere apps.
        """
        if not HAS_BUS:
            return ""
        ctx = get_bus().get_context(event_types, count=count)
        if not ctx:
            return ""
        regels = ["[Cross-app context]"]
        for et, events in ctx.items():
            for ev in events:
                regels.append(
                    f"- {ev['bron']}: {et} | "
                    f"{', '.join(f'{k}={v}' for k, v in ev['data'].items())}"
                )
        return "\n".join(regels)

    def _cleanup_bus(self):
        """Verwijder bus subscriptions (aanroepen bij afsluiten)."""
        if not HAS_BUS:
            return
        bus = get_bus()
        for event_type, handler in self._bus_handlers.items():
            bus.unsubscribe(event_type, handler)
        self._bus_handlers.clear()

    def _laad_data(self) -> dict:
        """Laad data uit JSON bestand."""
        if self.bestand.exists():
            try:
                with open(self.bestand, "r",
                           encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return self._get_default_data()

    def _get_default_data(self) -> dict:
        """Override in subclass voor standaard data."""
        return {}

    def _sla_op(self):
        """Sla data op."""
        with open(self.bestand, "w",
                   encoding="utf-8") as f:
            json.dump(
                self.data, f, indent=2,
                ensure_ascii=False
            )

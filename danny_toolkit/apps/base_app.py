"""Base klasse voor alle toolkit apps."""

import json
import os
from ..core.config import Config

try:
    from anthropic import Anthropic
    AI_BESCHIKBAAR = True
except ImportError:
    AI_BESCHIKBAAR = False


class BaseApp:
    """Basis klasse met gedeelde AI en data functionaliteit."""

    VERSIE = "2.0"

    def __init__(self, data_bestand: str):
        Config.ensure_dirs()
        self.bestand = Config.APPS_DATA_DIR / data_bestand
        self.bestand.parent.mkdir(exist_ok=True, parents=True)
        self.data = self._laad_data()
        self.client = None
        self._init_ai()

    def _init_ai(self):
        """Initialiseer AI client."""
        if AI_BESCHIKBAAR:
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if api_key:
                try:
                    self.client = Anthropic(api_key=api_key)
                except Exception:
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
        except Exception:
            return None

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

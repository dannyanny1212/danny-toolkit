"""
GhostAmplifier — Token Vermenigvuldiger.

Neemt korte input en expandeert naar rijke, gedetailleerde output.
Strategieën: elaboratie, multi-perspectief, stap-voor-stap uitbreiding,
en recursieve verdieping. Vermenigvuldigt token-waarde 5-10x.

Gebruik:
    from danny_toolkit.brain.ghost_amplifier import GhostAmplifier, get_ghost_amplifier

    amp = get_ghost_amplifier()
    result = await amp.amplify("maak een API server", factor=5)
    # Returns 5x meer tokens met rijke details

    result = await amp.amplify_recursive("login systeem", depth=3)
    # Recursieve verdieping: elke laag voegt detail toe
"""

from __future__ import annotations

import logging
import os
import threading
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from danny_toolkit.core.config import Config
from danny_toolkit.core.utils import Kleur

logger = logging.getLogger(__name__)

try:
    from groq import AsyncGroq
    HAS_GROQ = True
except ImportError:
    HAS_GROQ = False

try:
    from danny_toolkit.core.key_manager import get_key_manager
    HAS_KEY_MANAGER = True
except ImportError:
    HAS_KEY_MANAGER = False

try:
    from danny_toolkit.brain.cortical_stack import get_cortical_stack
    HAS_STACK = True
except ImportError:
    HAS_STACK = False

try:
    from danny_toolkit.core.neural_bus import get_bus, EventTypes
    HAS_BUS = True
except ImportError:
    HAS_BUS = False


@dataclass
class AmplifiedResult:
    """Resultaat van een token-vermenigvuldiging."""
    origineel: str
    geamplificeerd: str
    origineel_tokens: int = 0
    resultaat_tokens: int = 0
    factor: float = 0.0
    strategie: str = ""
    lagen: int = 1
    duur_ms: float = 0.0


class GhostAmplifier:
    """
    TOKEN VERMENIGVULDIGER (Invention #21)
    =======================================
    Neemt compacte input en genereert uitgebreide, gedetailleerde output.

    Strategieën:
    - ELABORATIE: Voegt context, voorbeelden en uitleg toe
    - MULTI_PERSPECTIEF: Bekijkt vanuit 3+ invalshoeken
    - STAP_VOOR_STAP: Decomposed in gedetailleerde stappen
    - RECURSIEF: Elke laag verdiept de vorige output
    - CODE_EXPAND: Kort idee → volledige implementatie met docstrings/tests
    """

    STRATEGIEEN = {
        "elaboratie": (
            "Je bent een expert schrijver. Neem de volgende korte input en "
            "elaboreer het tot een rijk, gedetailleerd stuk. Voeg context, "
            "voorbeelden, analogieën en nuances toe. Vermenigvuldig de "
            "informatiedichtheid {factor}x.\n\n"
            "INPUT: {input}\n\n"
            "Schrijf een uitgebreide elaboratie ({min_tokens}+ woorden):"
        ),
        "multi_perspectief": (
            "Analyseer de volgende input vanuit minstens 4 verschillende "
            "perspectieven: technisch, gebruiker, business en veiligheid. "
            "Geef voor elk perspectief een gedetailleerde analyse.\n\n"
            "INPUT: {input}\n\n"
            "Multi-perspectief analyse ({min_tokens}+ woorden):"
        ),
        "stap_voor_stap": (
            "Decomposeer de volgende input in een gedetailleerd stap-voor-stap "
            "plan. Elke stap moet sub-stappen bevatten met specifieke acties, "
            "vereisten, risico's en verificatie-criteria.\n\n"
            "INPUT: {input}\n\n"
            "Gedetailleerd stappenplan ({min_tokens}+ woorden):"
        ),
        "code_expand": (
            "Je bent een senior Python developer. Neem het volgende korte idee "
            "en genereer een VOLLEDIGE implementatie met:\n"
            "- Complete code met type hints\n"
            "- Google-style docstrings\n"
            "- Error handling (try/except met logging)\n"
            "- Minimaal 3 unit tests\n"
            "- Configuratie-opties\n\n"
            "IDEE: {input}\n\n"
            "Volledige implementatie ({min_tokens}+ woorden):"
        ),
    }

    def __init__(self):
        """Initializes the instance with a Groq API client and model configuration.

 Args:
  None

 Returns:
  None

 Notes:
  If the key manager is available, creates an asynchronous Groq client using the key manager; 
  otherwise, falls back to using the GROQ_API_KEY environment variable. 
  Initializes the model and instance statistics, including call count, token counts, 
  and strategy usage."""
        if HAS_KEY_MANAGER:
            km = get_key_manager()
            self.client = km.create_async_client("GhostWriter")
            if not self.client and HAS_GROQ:
                self.client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))
        elif HAS_GROQ:
            self.client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))
        else:
            self.client = None
        self.model = Config.LLM_MODEL
        self._stats = {
            "calls": 0,
            "tokens_in": 0,
            "tokens_out": 0,
            "gem_factor": 0.0,
            "strategieen_gebruikt": {},
        }

    async def amplify(
        self,
        input_tekst: str,
        factor: int = 5,
        strategie: str = "auto",
        max_tokens: int = 4096,
    ) -> AmplifiedResult:
        """
        Vermenigvuldig token-waarde van korte input.

        Args:
            input_tekst: Korte input tekst.
            factor: Gewenste vermenigvuldigingsfactor (3-10).
            strategie: 'auto', 'elaboratie', 'multi_perspectief',
                       'stap_voor_stap', of 'code_expand'.
            max_tokens: Maximum output tokens.

        Returns:
            AmplifiedResult met origineel + geamplificeerde tekst.
        """
        t0 = time.time()
        factor = max(2, min(factor, 10))

        # Auto-strategie selectie
        if strategie == "auto":
            strategie = self._detect_strategie(input_tekst)

        input_tokens = len(input_tekst.split())
        min_tokens = input_tokens * factor

        # Bouw prompt
        template = self.STRATEGIEEN.get(strategie, self.STRATEGIEEN["elaboratie"])
        prompt = template.format(
            input=input_tekst,
            factor=factor,
            min_tokens=min_tokens,
        )

        print(f"{Kleur.MAGENTA}🔮 GhostAmplifier: {strategie} "
              f"(factor={factor}x, min={min_tokens} woorden)...{Kleur.RESET}")

        try:
            chat = await self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": (
                        "Je bent een token-vermenigvuldiger. Je taak is om "
                        "korte input uit te breiden tot rijke, gedetailleerde "
                        "output. Kwaliteit boven kwantiteit, maar gebruik "
                        f"minimaal {min_tokens} woorden."
                    )},
                    {"role": "user", "content": prompt},
                ],
                model=self.model,
                temperature=0.7,
                max_tokens=max_tokens,
            )
            output = chat.choices[0].message.content or ""
            output_tokens = len(output.split())
            actual_factor = output_tokens / max(input_tokens, 1)
            duur_ms = (time.time() - t0) * 1000

            result = AmplifiedResult(
                origineel=input_tekst,
                geamplificeerd=output,
                origineel_tokens=input_tokens,
                resultaat_tokens=output_tokens,
                factor=round(actual_factor, 1),
                strategie=strategie,
                lagen=1,
                duur_ms=round(duur_ms, 1),
            )

            # Stats update
            self._stats["calls"] += 1
            self._stats["tokens_in"] += input_tokens
            self._stats["tokens_out"] += output_tokens
            total_calls = self._stats["calls"]
            self._stats["gem_factor"] = round(
                self._stats["tokens_out"] / max(self._stats["tokens_in"], 1), 1
            )
            s_key = strategie
            self._stats["strategieen_gebruikt"][s_key] = (
                self._stats["strategieen_gebruikt"].get(s_key, 0) + 1
            )

            # CorticalStack log
            self._log_amplification(result)

            print(f"{Kleur.GROEN}🔮 Amplified: {input_tokens} → "
                  f"{output_tokens} tokens ({actual_factor:.1f}x) "
                  f"in {duur_ms:.0f}ms{Kleur.RESET}")

            return result

        except Exception as e:
            logger.debug("GhostAmplifier amplify error: %s", e)
            duur_ms = (time.time() - t0) * 1000
            return AmplifiedResult(
                origineel=input_tekst,
                geamplificeerd=f"[Amplificatie mislukt: {e}]",
                duur_ms=round(duur_ms, 1),
                strategie=strategie,
            )

    async def amplify_recursive(
        self,
        input_tekst: str,
        depth: int = 3,
        factor_per_laag: int = 3,
    ) -> AmplifiedResult:
        """
        Recursieve token-vermenigvuldiging: elke laag verdiept de vorige.

        Args:
            input_tekst: Korte input.
            depth: Aantal recursieve lagen (2-5).
            factor_per_laag: Vermenigvuldiging per laag.

        Returns:
            AmplifiedResult met de finale, diep-geamplificeerde tekst.
        """
        depth = max(2, min(depth, 5))
        current = input_tekst
        totaal_t0 = time.time()

        print(f"{Kleur.MAGENTA}🔮 Recursieve amplificatie: "
              f"{depth} lagen × {factor_per_laag}x...{Kleur.RESET}")

        for laag in range(depth):
            strategie = ["elaboratie", "stap_voor_stap",
                         "multi_perspectief", "elaboratie", "code_expand"][laag]
            print(f"{Kleur.GEEL}  Laag {laag + 1}/{depth}: "
                  f"{strategie}...{Kleur.RESET}")

            result = await self.amplify(
                current,
                factor=factor_per_laag,
                strategie=strategie,
                max_tokens=4096,
            )
            current = result.geamplificeerd

        totaal_ms = (time.time() - totaal_t0) * 1000
        input_tokens = len(input_tekst.split())
        output_tokens = len(current.split())

        final = AmplifiedResult(
            origineel=input_tekst,
            geamplificeerd=current,
            origineel_tokens=input_tokens,
            resultaat_tokens=output_tokens,
            factor=round(output_tokens / max(input_tokens, 1), 1),
            strategie=f"recursief_{depth}_lagen",
            lagen=depth,
            duur_ms=round(totaal_ms, 1),
        )

        print(f"{Kleur.GROEN}🔮 Recursief klaar: {input_tokens} → "
              f"{output_tokens} tokens ({final.factor}x) "
              f"in {totaal_ms:.0f}ms{Kleur.RESET}")

        return final

    async def amplify_batch(
        self,
        items: List[str],
        factor: int = 5,
        strategie: str = "auto",
    ) -> List[AmplifiedResult]:
        """
        Vermenigvuldig een batch van korte inputs.

        Args:
            items: Lijst van korte teksten.
            factor: Vermenigvuldigingsfactor.
            strategie: Strategie per item.

        Returns:
            Lijst van AmplifiedResult objecten.
        """
        import asyncio
        results = await asyncio.gather(*[
            self.amplify(item, factor=factor, strategie=strategie)
            for item in items
        ])
        return list(results)

    def _detect_strategie(self, tekst: str) -> str:
        """Auto-detecteer de beste strategie op basis van input."""
        lower = tekst.lower()

        # Code-gerelateerd
        code_woorden = ["code", "functie", "class", "api", "endpoint",
                        "script", "implementeer", "bouw", "maak"]
        if any(w in lower for w in code_woorden):
            return "code_expand"

        # Plan/stappen
        plan_woorden = ["plan", "stappen", "hoe", "proces", "workflow",
                        "pipeline", "architectuur"]
        if any(w in lower for w in plan_woorden):
            return "stap_voor_stap"

        # Analyse
        analyse_woorden = ["analyseer", "vergelijk", "evalueer",
                           "voor en tegen", "risico"]
        if any(w in lower for w in analyse_woorden):
            return "multi_perspectief"

        return "elaboratie"

    def _log_amplification(self, result: AmplifiedResult):
        """Log amplificatie naar CorticalStack."""
        if not HAS_STACK:
            return
        try:
            stack = get_cortical_stack()
            stack.log_event(
                actor="GhostAmplifier",
                action="token_amplified",
                details={
                    "input_tokens": result.origineel_tokens,
                    "output_tokens": result.resultaat_tokens,
                    "factor": result.factor,
                    "strategie": result.strategie,
                    "lagen": result.lagen,
                    "duur_ms": result.duur_ms,
                },
                source="ghost_amplifier",
            )
        except Exception as e:
            logger.debug("GhostAmplifier log error: %s", e)

    def get_stats(self) -> dict:
        """Amplifier statistieken."""
        return dict(self._stats)


# ── Singleton Factory ──

_amplifier_instance: Optional["GhostAmplifier"] = None
_amplifier_lock = threading.Lock()


def get_ghost_amplifier() -> "GhostAmplifier":
    """Return the process-wide GhostAmplifier singleton."""
    global _amplifier_instance
    if _amplifier_instance is None:
        with _amplifier_lock:
            if _amplifier_instance is None:
                _amplifier_instance = GhostAmplifier()
    return _amplifier_instance

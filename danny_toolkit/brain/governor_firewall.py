"""
Governor Firewall Mixin — Input validatie & PII bescherming.


Bevat GovernorFirewallMixin met:
- registreer_tokens()    — Token budget tracking
- _check_token_budget()  — Budget limiet check
- valideer_input()       — Prompt injectie + lengte + budget
- scrub_pii()            — PII verwijdering

Geëxtraheerd uit governor.py (Fase C.2 monoliet split).
Mixin leest constanten via self.* (OmegaGovernor attributen).
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Tuple

logger = logging.getLogger(__name__)

try:
    from danny_toolkit.core.alerter import get_alerter, AlertLevel
    HAS_ALERTER = True
except ImportError:
    HAS_ALERTER = False


class GovernorFirewallMixin:
    """Mixin voor input validatie en PII bescherming.

    Vereist dat de host-klasse de volgende attributen heeft:
    - self._INJECTIE_PATRONEN, self._PII_PATRONEN
    - self.MAX_INPUT_LENGTH, self.MAX_TOKENS_PER_HOUR
    - self._token_counts (defaultdict(int))
    - self._log(action, details)
    """

    def registreer_tokens(self, tekst: str) -> None:
        """Registreer geschat tokenverbruik na een LLM response.

        Char-based schatting: 1 token ≈ 4 tekens.

        Args:
            tekst: De LLM response tekst.
        """
        if not tekst:
            return
        tokens = len(tekst) // 4
        hour_key = datetime.now().strftime("%Y%m%d%H")
        self._token_counts[hour_key] += tokens

        # Cleanup: verwijder keys ouder dan 2 uur
        current = datetime.now()
        stale = [
            k for k in self._token_counts
            if k != hour_key and abs(
                int(current.strftime("%Y%m%d%H"))
                - int(k)
            ) > 1
        ]
        for k in stale:
            del self._token_counts[k]

    def _check_token_budget(self) -> Tuple[bool, str]:
        """Check of het token budget nog niet overschreden is.

        Returns:
            Tuple (binnen_budget: bool, reden: str).
        """
        hour_key = datetime.now().strftime("%Y%m%d%H")
        used = self._token_counts.get(hour_key, 0)
        if used >= self.MAX_TOKENS_PER_HOUR:
            self._log("token_budget_bereikt", {
                "used": used,
                "max": self.MAX_TOKENS_PER_HOUR,
            })
            return False, (
                "Token budget bereikt, wacht tot"
                " volgend uur."
            )
        return True, "OK"

    def valideer_input(
        self, tekst: str,
    ) -> Tuple[bool, str]:
        """Valideer gebruikersinput op injectie en lengte.

        Checks:
        1. Lengte limiet (MAX_INPUT_LENGTH)
        2. Prompt injectie patronen
        3. Token budget (uurlimiet)

        Args:
            tekst: Gebruikersinput.

        Returns:
            Tuple (veilig: bool, reden: str).
        """
        if not tekst or not tekst.strip():
            return True, "OK"

        # Token budget check
        budget_ok, budget_reden = self._check_token_budget()
        if not budget_ok:
            if HAS_ALERTER:
                try:
                    get_alerter().alert(
                        AlertLevel.WAARSCHUWING,
                        budget_reden,
                        bron="governor",
                    )
                except Exception as e:
                    logger.debug("Alerter error: %s", e)
            return False, budget_reden

        # Lengte check
        if len(tekst) > self.MAX_INPUT_LENGTH:
            self._log("input_te_lang", {
                "lengte": len(tekst),
            })
            return False, (
                f"Input te lang "
                f"({len(tekst)}/{self.MAX_INPUT_LENGTH})"
            )

        # Prompt injectie detectie
        lower = tekst.lower()
        for patroon in self._INJECTIE_PATRONEN:
            if re.search(patroon, lower):
                print(
                    "  [GOVERNOR] Prompt injectie "
                    "gedetecteerd en geblokkeerd"
                )
                self._log("prompt_injectie_geblokkeerd", {
                    "tekst_preview": tekst[:200],
                })
                return False, "Prompt injectie gedetecteerd"

        return True, "OK"

    def scrub_pii(self, tekst: str) -> str:
        """Vervang PII in tekst door placeholders.

        Detecteert email, IBAN, creditcard, telefoon
        en vervangt door [EMAIL], [IBAN], etc.
        Volgorde: specifiek -> generiek.

        Args:
            tekst: Tekst om te scrubben.

        Returns:
            Geschoonde tekst.
        """
        if not tekst:
            return tekst

        resultaat = tekst
        for label, patroon in self._PII_PATRONEN:
            placeholder = f"[{label}]"
            resultaat = re.sub(
                patroon, placeholder, resultaat,
            )

        return resultaat

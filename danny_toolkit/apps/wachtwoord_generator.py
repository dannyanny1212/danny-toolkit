"""
Wachtwoord Generator - Genereer veilige wachtwoorden.
"""

import json
import logging
import random
import string
from datetime import datetime
from ..core.config import Config
from ..core.utils import clear_scherm

logger = logging.getLogger(__name__)


class WachtwoordGeneratorApp:
    """Genereer veilige wachtwoorden."""

    def __init__(self):
        Config.ensure_dirs()
        self.bestand = Config.APPS_DATA_DIR / "wachtwoorden_history.json"
        self.history = self._laad_history()

    def _laad_history(self) -> list:
        """Laad wachtwoord history."""
        if self.bestand.exists():
            try:
                with open(self.bestand, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.debug("Password history load error: %s", e)
        return []

    def _sla_op(self):
        """Sla history op."""
        with open(self.bestand, "w", encoding="utf-8") as f:
            json.dump(self.history[-50:], f, indent=2)  # Max 50

    def run(self):
        """Start de wachtwoord generator."""
        while True:
            clear_scherm()
            print("+" + "=" * 50 + "+")
            print("|       WACHTWOORD GENERATOR                       |")
            print("+" + "=" * 50 + "+")
            print("|  1. Wachtwoord genereren                         |")
            print("|  2. Wachtwoord sterkte testen                    |")
            print("|  3. Meerdere wachtwoorden                        |")
            print("|  4. PIN code genereren                           |")
            print("|  5. Wachtwoord history                           |")
            print("|  0. Terug                                        |")
            print("+" + "=" * 50 + "+")

            keuze = input("\nKeuze: ").strip()

            if keuze == "0":
                break
            elif keuze == "1":
                self._genereer_wachtwoord()
            elif keuze == "2":
                self._test_sterkte()
            elif keuze == "3":
                self._meerdere_wachtwoorden()
            elif keuze == "4":
                self._genereer_pin()
            elif keuze == "5":
                self._bekijk_history()

            input("\nDruk op Enter...")

    def _genereer_wachtwoord(self):
        """Genereer een wachtwoord met opties."""
        print("\n--- WACHTWOORD GENEREREN ---")

        try:
            lengte = int(input("Lengte (standaard 16): ").strip() or "16")
            lengte = max(8, min(64, lengte))
        except ValueError:
            lengte = 16

        print("\nOpties (j/n):")
        hoofdletters = input("  Hoofdletters? (j/n, standaard j): ").strip().lower() != "n"
        cijfers = input("  Cijfers? (j/n, standaard j): ").strip().lower() != "n"
        symbolen = input("  Symbolen? (j/n, standaard j): ").strip().lower() != "n"

        # Bouw karakter set
        karakters = string.ascii_lowercase
        if hoofdletters:
            karakters += string.ascii_uppercase
        if cijfers:
            karakters += string.digits
        if symbolen:
            karakters += "!@#$%^&*()_+-=[]{}|;:,.<>?"

        # Genereer wachtwoord
        wachtwoord = ''.join(random.choice(karakters) for _ in range(lengte))

        # Zorg voor minimaal 1 van elk type indien geselecteerd
        if hoofdletters and not any(c.isupper() for c in wachtwoord):
            pos = random.randint(0, lengte - 1)
            wachtwoord = wachtwoord[:pos] + random.choice(string.ascii_uppercase) + wachtwoord[pos + 1:]
        if cijfers and not any(c.isdigit() for c in wachtwoord):
            pos = random.randint(0, lengte - 1)
            wachtwoord = wachtwoord[:pos] + random.choice(string.digits) + wachtwoord[pos + 1:]
        if symbolen and not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in wachtwoord):
            pos = random.randint(0, lengte - 1)
            wachtwoord = wachtwoord[:pos] + random.choice("!@#$%^&*()") + wachtwoord[pos + 1:]

        sterkte = self._bereken_sterkte(wachtwoord)

        print(f"\n{'=' * 50}")
        print(f"  WACHTWOORD: {wachtwoord}")
        print(f"{'=' * 50}")
        print(f"  Lengte: {len(wachtwoord)}")
        print(f"  Sterkte: {sterkte}")

        # Sla op in history
        self.history.append({
            "wachtwoord": wachtwoord[:3] + "*" * (len(wachtwoord) - 6) + wachtwoord[-3:],
            "lengte": len(wachtwoord),
            "sterkte": sterkte,
            "datum": datetime.now().isoformat()
        })
        self._sla_op()

    def _bereken_sterkte(self, wachtwoord: str) -> str:
        """Bereken wachtwoord sterkte."""
        score = 0

        # Lengte
        if len(wachtwoord) >= 8:
            score += 1
        if len(wachtwoord) >= 12:
            score += 1
        if len(wachtwoord) >= 16:
            score += 1

        # Complexiteit
        if any(c.islower() for c in wachtwoord):
            score += 1
        if any(c.isupper() for c in wachtwoord):
            score += 1
        if any(c.isdigit() for c in wachtwoord):
            score += 1
        if any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in wachtwoord):
            score += 1

        # Geen herhalingen
        if len(set(wachtwoord)) > len(wachtwoord) * 0.7:
            score += 1

        if score <= 3:
            return "ZWAK"
        elif score <= 5:
            return "GEMIDDELD"
        elif score <= 7:
            return "STERK"
        else:
            return "ZEER STERK"

    def _test_sterkte(self):
        """Test de sterkte van een wachtwoord."""
        print("\n--- WACHTWOORD STERKTE TEST ---")
        wachtwoord = input("Voer wachtwoord in: ").strip()

        if not wachtwoord:
            return

        sterkte = self._bereken_sterkte(wachtwoord)

        print(f"\n  Lengte: {len(wachtwoord)}")
        print(f"  Heeft kleine letters: {'Ja' if any(c.islower() for c in wachtwoord) else 'Nee'}")
        print(f"  Heeft hoofdletters: {'Ja' if any(c.isupper() for c in wachtwoord) else 'Nee'}")
        print(f"  Heeft cijfers: {'Ja' if any(c.isdigit() for c in wachtwoord) else 'Nee'}")
        print(f"  Heeft symbolen: {'Ja' if any(not c.isalnum() for c in wachtwoord) else 'Nee'}")
        print(f"\n  STERKTE: {sterkte}")

    def _meerdere_wachtwoorden(self):
        """Genereer meerdere wachtwoorden."""
        print("\n--- MEERDERE WACHTWOORDEN ---")

        try:
            aantal = int(input("Aantal (max 10): ").strip() or "5")
            aantal = max(1, min(10, aantal))
            lengte = int(input("Lengte (standaard 16): ").strip() or "16")
            lengte = max(8, min(64, lengte))
        except ValueError:
            aantal, lengte = 5, 16

        karakters = string.ascii_letters + string.digits + "!@#$%^&*()"

        print(f"\n{'=' * 50}")
        for i in range(aantal):
            wachtwoord = ''.join(random.choice(karakters) for _ in range(lengte))
            print(f"  {i + 1}. {wachtwoord}")
        print(f"{'=' * 50}")

    def _genereer_pin(self):
        """Genereer een PIN code."""
        print("\n--- PIN CODE GENEREREN ---")

        try:
            lengte = int(input("Lengte (4-8, standaard 4): ").strip() or "4")
            lengte = max(4, min(8, lengte))
        except ValueError:
            lengte = 4

        pin = ''.join(random.choice(string.digits) for _ in range(lengte))

        print(f"\n{'=' * 30}")
        print(f"  PIN: {pin}")
        print(f"{'=' * 30}")

    def _bekijk_history(self):
        """Bekijk wachtwoord history."""
        print("\n--- WACHTWOORD HISTORY ---")

        if not self.history:
            print("Geen history.")
            return

        for i, h in enumerate(self.history[-10:], 1):
            print(f"  {i}. {h['wachtwoord']} (len:{h['lengte']}, {h['sterkte']})")

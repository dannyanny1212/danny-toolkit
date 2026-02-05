"""
Boodschappenlijst App.
"""

from ..core.config import Config
from ..core.utils import clear_scherm


class BoodschappenlijstApp:
    """Interactieve boodschappenlijst applicatie."""

    def __init__(self):
        Config.ensure_dirs()
        self.bestand = Config.BOODSCHAPPENLIJST_FILE
        self.lijst = self._laad_lijst()

    def _laad_lijst(self) -> list:
        """Laadt de lijst uit bestand."""
        if self.bestand.exists():
            with open(self.bestand, "r", encoding="utf-8") as f:
                return [regel.strip() for regel in f.readlines() if regel.strip()]
        return []

    def _sla_op(self):
        """Slaat de lijst op naar bestand."""
        with open(self.bestand, "w", encoding="utf-8") as f:
            for item in self.lijst:
                f.write(item + "\n")
        print(f"Lijst opgeslagen in '{self.bestand}'")

    def _toon_lijst(self):
        """Toont de huidige lijst."""
        if not self.lijst:
            print("\nDe boodschappenlijst is leeg.")
        else:
            print("\n=== Boodschappenlijst ===")
            for i, item in enumerate(self.lijst, 1):
                print(f"  {i}. {item}")
            print(f"=========================")
            print(f"Totaal: {len(self.lijst)} item(s)")

    def _voeg_toe(self):
        """Voegt een item toe."""
        item = input("Wat wil je toevoegen? ").strip()
        if item:
            self.lijst.append(item)
            print(f"'{item}' toegevoegd!")
        else:
            print("Geen item ingevoerd.")

    def _verwijder(self):
        """Verwijdert een item."""
        if not self.lijst:
            print("De lijst is leeg, niets om te verwijderen.")
            return

        self._toon_lijst()
        try:
            nummer = int(input("\nWelk nummer wil je verwijderen? "))
            if 1 <= nummer <= len(self.lijst):
                verwijderd = self.lijst.pop(nummer - 1)
                print(f"'{verwijderd}' verwijderd!")
            else:
                print("Ongeldig nummer.")
        except ValueError:
            print("Voer een geldig nummer in.")

    def _wis_lijst(self):
        """Wist de hele lijst."""
        if not self.lijst:
            print("De lijst is al leeg.")
            return

        bevestig = input("Weet je zeker dat je alles wilt wissen? (j/n): ").lower()
        if bevestig == "j":
            self.lijst = []
            print("Lijst gewist!")
        else:
            print("Actie geannuleerd.")

    def _toon_menu(self):
        """Toont het menu."""
        print("\n=== Boodschappenlijst Menu ===")
        print("1. Toon lijst")
        print("2. Voeg item toe")
        print("3. Verwijder item")
        print("4. Wis hele lijst")
        print("5. Opslaan")
        print("0. Terug naar hoofdmenu")
        print("==============================")

    def run(self):
        """Start de app."""
        clear_scherm()
        print("Welkom bij de Boodschappenlijst!")

        if self.lijst:
            print(f"({len(self.lijst)} item(s) geladen uit bestand)")

        while True:
            self._toon_menu()
            keuze = input("\nKies een optie (0-5): ").strip()

            if keuze == "1":
                self._toon_lijst()
            elif keuze == "2":
                self._voeg_toe()
            elif keuze == "3":
                self._verwijder()
            elif keuze == "4":
                self._wis_lijst()
            elif keuze == "5":
                self._sla_op()
            elif keuze == "0":
                opslaan = input("Wil je opslaan voor het afsluiten? (j/n): ").lower()
                if opslaan == "j":
                    self._sla_op()
                print("Terug naar hoofdmenu...")
                break
            else:
                print("Ongeldige keuze. Kies een nummer van 0 tot 5.")

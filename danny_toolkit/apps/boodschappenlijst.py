"""
Boodschappenlijst App - Uitgebreide versie.
"""

import json
from ..core.config import Config
from ..core.utils import clear_scherm


class BoodschappenlijstApp:
    """Interactieve boodschappenlijst applicatie."""

    CATEGORIEEN = [
        "Groenten & Fruit",
        "Zuivel",
        "Vlees & Vis",
        "Brood & Bakkerij",
        "Dranken",
        "Huishouden",
        "Overig"
    ]

    def __init__(self):
        Config.ensure_dirs()
        self.bestand = Config.APPS_DATA_DIR / "boodschappenlijst.json"
        self.data = self._laad_data()

    def _laad_data(self) -> dict:
        """Laadt de data uit bestand."""
        if self.bestand.exists():
            with open(self.bestand, "r", encoding="utf-8") as f:
                return json.load(f)
        return {
            "items": [],
            "favorieten": []
        }

    def _sla_op(self):
        """Slaat de data op naar bestand."""
        with open(self.bestand, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)
        print(f"Opgeslagen!")

    def _toon_lijst(self):
        """Toont de huidige lijst, gegroepeerd per categorie."""
        items = self.data["items"]

        if not items:
            print("\nDe boodschappenlijst is leeg.")
            return

        print("\n" + "=" * 45)
        print("         BOODSCHAPPENLIJST")
        print("=" * 45)

        # Groepeer per categorie
        per_categorie = {}
        for cat in self.CATEGORIEEN:
            per_categorie[cat] = []

        for i, item in enumerate(items):
            cat = item.get("categorie", "Overig")
            per_categorie[cat].append((i, item))

        # Toon per categorie
        item_nr = 1
        for cat in self.CATEGORIEEN:
            cat_items = per_categorie[cat]
            if cat_items:
                print(f"\n  [{cat.upper()}]")
                for idx, item in cat_items:
                    status = "[x]" if item.get("afgevinkt", False) else "[ ]"
                    hoeveelheid = item.get("hoeveelheid", "")
                    naam = item["naam"]
                    if hoeveelheid:
                        tekst = f"{hoeveelheid} {naam}"
                    else:
                        tekst = naam
                    print(f"    {item_nr}. {status} {tekst}")
                    item_nr += 1

        # Statistieken
        totaal = len(items)
        afgevinkt = sum(1 for i in items if i.get("afgevinkt", False))
        print("\n" + "-" * 45)
        print(f"  Totaal: {totaal} items | Afgevinkt: {afgevinkt}/{totaal}")
        print("=" * 45)

    def _kies_categorie(self) -> str:
        """Laat gebruiker een categorie kiezen."""
        print("\nKies een categorie:")
        for i, cat in enumerate(self.CATEGORIEEN, 1):
            print(f"  {i}. {cat}")

        keuze = input("\nCategorie (1-7): ").strip()
        try:
            idx = int(keuze) - 1
            if 0 <= idx < len(self.CATEGORIEEN):
                return self.CATEGORIEEN[idx]
        except ValueError:
            pass
        return "Overig"

    def _voeg_toe(self):
        """Voegt een item toe met categorie en hoeveelheid."""
        naam = input("\nWat wil je toevoegen? ").strip()
        if not naam:
            print("Geen item ingevoerd.")
            return

        hoeveelheid = input("Hoeveelheid (optioneel, bijv '2 liter' of '500g'): ").strip()
        categorie = self._kies_categorie()

        item = {
            "naam": naam,
            "hoeveelheid": hoeveelheid,
            "categorie": categorie,
            "afgevinkt": False
        }

        self.data["items"].append(item)
        print(f"'{naam}' toegevoegd aan {categorie}!")

        # Vraag of het een favoriet moet worden
        if naam not in [f["naam"] for f in self.data["favorieten"]]:
            fav = input("Toevoegen aan favorieten? (j/n): ").lower().strip()
            if fav == "j":
                self.data["favorieten"].append({
                    "naam": naam,
                    "categorie": categorie
                })
                print(f"'{naam}' toegevoegd aan favorieten!")

    def _voeg_favoriet_toe(self):
        """Voegt een item toe vanuit favorieten."""
        favorieten = self.data["favorieten"]

        if not favorieten:
            print("\nJe hebt nog geen favorieten.")
            print("Voeg eerst items toe en markeer ze als favoriet!")
            return

        print("\n=== FAVORIETEN ===")
        for i, fav in enumerate(favorieten, 1):
            print(f"  {i}. {fav['naam']} ({fav['categorie']})")
        print("  0. Annuleren")

        keuze = input("\nWelk favoriet toevoegen? ").strip()
        try:
            idx = int(keuze) - 1
            if idx == -1:
                return
            if 0 <= idx < len(favorieten):
                fav = favorieten[idx]
                hoeveelheid = input(f"Hoeveelheid voor {fav['naam']} (optioneel): ").strip()

                item = {
                    "naam": fav["naam"],
                    "hoeveelheid": hoeveelheid,
                    "categorie": fav["categorie"],
                    "afgevinkt": False
                }
                self.data["items"].append(item)
                print(f"'{fav['naam']}' toegevoegd!")
            else:
                print("Ongeldige keuze.")
        except ValueError:
            print("Voer een nummer in.")

    def _afvinken(self):
        """Vinkt een item af of haalt vinkje weg."""
        items = self.data["items"]

        if not items:
            print("\nDe lijst is leeg.")
            return

        self._toon_lijst()
        keuze = input("\nWelk nummer afvinken/onafvinken? ").strip()

        try:
            idx = int(keuze) - 1
            if 0 <= idx < len(items):
                items[idx]["afgevinkt"] = not items[idx]["afgevinkt"]
                status = "afgevinkt" if items[idx]["afgevinkt"] else "niet afgevinkt"
                print(f"'{items[idx]['naam']}' is nu {status}!")
            else:
                print("Ongeldig nummer.")
        except ValueError:
            print("Voer een nummer in.")

    def _verwijder(self):
        """Verwijdert een item."""
        items = self.data["items"]

        if not items:
            print("\nDe lijst is leeg.")
            return

        self._toon_lijst()
        print("\nOpties:")
        print("  [nummer] = Verwijder specifiek item")
        print("  a = Verwijder alle afgevinkte items")

        keuze = input("\nKeuze: ").strip().lower()

        if keuze == "a":
            oude_len = len(items)
            self.data["items"] = [i for i in items if not i.get("afgevinkt", False)]
            verwijderd = oude_len - len(self.data["items"])
            print(f"{verwijderd} afgevinkte item(s) verwijderd!")
        else:
            try:
                idx = int(keuze) - 1
                if 0 <= idx < len(items):
                    verwijderd = items.pop(idx)
                    print(f"'{verwijderd['naam']}' verwijderd!")
                else:
                    print("Ongeldig nummer.")
            except ValueError:
                print("Ongeldige invoer.")

    def _beheer_favorieten(self):
        """Beheer favorieten lijst."""
        favorieten = self.data["favorieten"]

        print("\n=== FAVORIETEN BEHEREN ===")
        if favorieten:
            for i, fav in enumerate(favorieten, 1):
                print(f"  {i}. {fav['naam']} ({fav['categorie']})")
        else:
            print("  Nog geen favorieten!")

        print("\nOpties:")
        print("  [nummer] = Verwijder favoriet")
        print("  n = Nieuwe favoriet toevoegen")
        print("  0 = Terug")

        keuze = input("\nKeuze: ").strip().lower()

        if keuze == "0":
            return
        elif keuze == "n":
            naam = input("Naam van nieuwe favoriet: ").strip()
            if naam:
                categorie = self._kies_categorie()
                self.data["favorieten"].append({
                    "naam": naam,
                    "categorie": categorie
                })
                print(f"'{naam}' toegevoegd aan favorieten!")
        else:
            try:
                idx = int(keuze) - 1
                if 0 <= idx < len(favorieten):
                    verwijderd = favorieten.pop(idx)
                    print(f"'{verwijderd['naam']}' verwijderd uit favorieten!")
                else:
                    print("Ongeldig nummer.")
            except ValueError:
                print("Ongeldige invoer.")

    def _wis_lijst(self):
        """Wist de hele lijst."""
        if not self.data["items"]:
            print("\nDe lijst is al leeg.")
            return

        bevestig = input("Weet je zeker dat je alles wilt wissen? (j/n): ").lower()
        if bevestig == "j":
            self.data["items"] = []
            print("Lijst gewist!")
        else:
            print("Actie geannuleerd.")

    def _toon_menu(self):
        """Toont het menu."""
        items_count = len(self.data["items"])
        afgevinkt = sum(1 for i in self.data["items"] if i.get("afgevinkt", False))

        print("\n+================================+")
        print("|     BOODSCHAPPENLIJST          |")
        print(f"|     Items: {items_count} | Afgevinkt: {afgevinkt:<3}   |")
        print("+================================+")
        print("|  1. Toon lijst                 |")
        print("|  2. Voeg item toe              |")
        print("|  3. Voeg favoriet toe          |")
        print("|  4. Afvinken/onafvinken        |")
        print("|  5. Verwijder item(s)          |")
        print("|  6. Beheer favorieten          |")
        print("|  7. Wis hele lijst             |")
        print("|  8. Opslaan                    |")
        print("|  0. Terug naar hoofdmenu       |")
        print("+================================+")

    def run(self):
        """Start de app."""
        clear_scherm()
        print("+" + "=" * 40 + "+")
        print("|   BOODSCHAPPENLIJST                    |")
        print("|   Met categorieen, hoeveelheden,       |")
        print("|   favorieten en afvinken!              |")
        print("+" + "=" * 40 + "+")

        items_count = len(self.data["items"])
        fav_count = len(self.data["favorieten"])
        if items_count > 0 or fav_count > 0:
            print(f"\nGeladen: {items_count} items, {fav_count} favorieten")

        while True:
            self._toon_menu()
            keuze = input("\nKies een optie (0-8): ").strip()

            if keuze == "1":
                self._toon_lijst()
            elif keuze == "2":
                self._voeg_toe()
            elif keuze == "3":
                self._voeg_favoriet_toe()
            elif keuze == "4":
                self._afvinken()
            elif keuze == "5":
                self._verwijder()
            elif keuze == "6":
                self._beheer_favorieten()
            elif keuze == "7":
                self._wis_lijst()
            elif keuze == "8":
                self._sla_op()
            elif keuze == "0":
                opslaan = input("Wil je opslaan voor het afsluiten? (j/n): ").lower()
                if opslaan == "j":
                    self._sla_op()
                print("Terug naar hoofdmenu...")
                break
            else:
                print("Ongeldige keuze.")

            input("\nDruk op Enter om verder te gaan...")

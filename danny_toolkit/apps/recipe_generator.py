"""
Recipe Generator v1.0 - AI recepten, ingrediënten tracker, meal planning.
"""

import json
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
from ..core.config import Config
from ..core.utils import clear_scherm
from .base_app import BaseApp


class RecipeGeneratorApp(BaseApp):
    """Recipe Generator - Recepten en meal planning."""

    # Basis ingrediënten categorieën
    CATEGORIEEN = {
        "groenten": ["ui", "knoflook", "tomaat", "paprika", "wortel", "aardappel",
                     "broccoli", "spinazie", "champignons", "courgette"],
        "fruit": ["appel", "banaan", "citroen", "sinaasappel", "aardbei"],
        "vlees": ["kip", "rund", "varken", "gehakt", "spek"],
        "vis": ["zalm", "kabeljauw", "garnalen", "tonijn"],
        "zuivel": ["melk", "kaas", "boter", "room", "yoghurt", "ei"],
        "granen": ["rijst", "pasta", "brood", "haver", "couscous"],
        "kruiden": ["zout", "peper", "basilicum", "oregano", "paprikapoeder",
                    "komijn", "kurkuma", "kaneel"],
    }

    # Basis recepten (fallback zonder AI)
    BASIS_RECEPTEN = [
        {
            "naam": "Pasta Carbonara",
            "ingredienten": ["pasta", "ei", "spek", "kaas", "peper"],
            "tijd": 20,
            "porties": 2,
            "stappen": [
                "Kook de pasta volgens de verpakking",
                "Bak het spek krokant",
                "Mix eieren met geraspte kaas",
                "Meng hete pasta met spek en ei-mengsel",
                "Voeg peper toe en serveer"
            ]
        },
        {
            "naam": "Roerbak Groenten met Kip",
            "ingredienten": ["kip", "paprika", "ui", "knoflook", "rijst"],
            "tijd": 25,
            "porties": 2,
            "stappen": [
                "Kook rijst volgens verpakking",
                "Snijd kip en groenten in stukjes",
                "Bak kip goudbruin",
                "Voeg groenten toe en roerbak 5 min",
                "Serveer met rijst"
            ]
        },
        {
            "naam": "Tomatensoep",
            "ingredienten": ["tomaat", "ui", "knoflook", "room", "basilicum"],
            "tijd": 30,
            "porties": 4,
            "stappen": [
                "Fruit ui en knoflook",
                "Voeg tomaten toe en laat 15 min sudderen",
                "Pureer tot gladde soep",
                "Roer room erdoor",
                "Garneer met basilicum"
            ]
        },
        {
            "naam": "Omelet",
            "ingredienten": ["ei", "kaas", "champignons", "ui", "boter"],
            "tijd": 10,
            "porties": 1,
            "stappen": [
                "Klop eieren los met zout en peper",
                "Bak champignons en ui in boter",
                "Giet eimengsel erbij",
                "Strooi kaas erover",
                "Vouw dicht en serveer"
            ]
        },
    ]

    def __init__(self):
        super().__init__("recipe_generator/data.json")

    def _get_default_data(self) -> dict:
        """Standaard data structuur."""
        return {
            "voorraad": {},
            "recepten": [],
            "weekmenu": {},
            "boodschappenlijst": [],
            "favorieten": [],
        }

    def _genereer_recept_ai(self, ingredienten: List[str]) -> Optional[Dict]:
        """Genereer recept met AI."""
        if not self.client:
            return None

        try:
            prompt = f"""Genereer een recept met deze ingrediënten: {', '.join(ingredienten)}

Geef het recept in dit exacte JSON formaat (alleen de JSON, geen andere tekst):
{{
    "naam": "Naam van het gerecht",
    "ingredienten": ["ingrediënt 1", "ingrediënt 2"],
    "tijd": 30,
    "porties": 2,
    "stappen": ["Stap 1", "Stap 2", "Stap 3"]
}}"""

            tekst = self._ai_request(prompt, max_tokens=1000)
            if not tekst:
                return None
            # Probeer JSON te extraheren
            import re
            match = re.search(r'\{.*\}', tekst, re.DOTALL)
            if match:
                return json.loads(match.group())
        except Exception as e:
            print(f"  AI fout: {e}")

        return None

    def _genereer_recept_lokaal(self, ingredienten: List[str]) -> Dict:
        """Genereer recept zonder AI (basis matching)."""
        beste_match = None
        beste_score = 0

        alle_recepten = self.BASIS_RECEPTEN + self.data.get("recepten", [])

        for recept in alle_recepten:
            score = sum(1 for ing in recept["ingredienten"]
                       if any(i in ing.lower() for i in ingredienten))
            if score > beste_score:
                beste_score = score
                beste_match = recept

        if beste_match:
            return beste_match

        # Fallback: random basis recept
        return random.choice(self.BASIS_RECEPTEN)

    def _beheer_voorraad(self):
        """Beheer ingrediënten voorraad."""
        while True:
            clear_scherm()
            print("\n  === VOORRAAD BEHEER ===\n")

            voorraad = self.data.get("voorraad", {})

            if voorraad:
                print("  Huidige voorraad:")
                for cat, items in voorraad.items():
                    if items:
                        print(f"\n  {cat.upper()}:")
                        for item, aantal in items.items():
                            print(f"    - {item}: {aantal}")
            else:
                print("  Voorraad is leeg.")

            print("\n  Opties:")
            print("  1. Toevoegen")
            print("  2. Verwijderen")
            print("  3. Snelle voorraad scan")
            print("  0. Terug")

            keuze = input("\n  Keuze: ").strip()

            if keuze == "0":
                break

            elif keuze == "1":
                print("\n  Categorieën:", ", ".join(self.CATEGORIEEN.keys()))
                cat = input("  Categorie: ").strip().lower()
                if cat not in self.CATEGORIEEN:
                    cat = "overig"

                item = input("  Ingrediënt: ").strip().lower()
                try:
                    aantal = int(input("  Aantal (1): ").strip() or "1")
                except ValueError:
                    aantal = 1

                if cat not in self.data["voorraad"]:
                    self.data["voorraad"][cat] = {}

                if item in self.data["voorraad"][cat]:
                    self.data["voorraad"][cat][item] += aantal
                else:
                    self.data["voorraad"][cat][item] = aantal

                self._sla_op()
                print(f"  {item} toegevoegd!")
                input("  Druk op Enter...")

            elif keuze == "2":
                cat = input("  Categorie: ").strip().lower()
                item = input("  Ingrediënt: ").strip().lower()

                if cat in self.data["voorraad"] and item in self.data["voorraad"][cat]:
                    del self.data["voorraad"][cat][item]
                    self._sla_op()
                    print(f"  {item} verwijderd!")
                else:
                    print("  Niet gevonden.")
                input("  Druk op Enter...")

            elif keuze == "3":
                # Snelle scan - voeg meerdere items toe
                print("\n  Typ ingrediënten (komma-gescheiden):")
                items = input("  > ").strip().split(",")

                for item in items:
                    item = item.strip().lower()
                    if item:
                        self.data["voorraad"].setdefault("overig", {})[item] = 1

                self._sla_op()
                print(f"  {len(items)} items toegevoegd!")
                input("  Druk op Enter...")

    def _genereer_recept(self):
        """Genereer een recept."""
        clear_scherm()
        print("\n  === RECEPT GENERATOR ===\n")

        print("  1. Op basis van voorraad")
        print("  2. Eigen ingrediënten opgeven")
        print("  3. Random recept")

        keuze = input("\n  Keuze: ").strip()

        ingredienten = []

        if keuze == "1":
            # Haal alle voorraad items
            for cat, items in self.data.get("voorraad", {}).items():
                ingredienten.extend(items.keys())

            if not ingredienten:
                print("\n  Voorraad is leeg! Voeg eerst ingrediënten toe.")
                input("  Druk op Enter...")
                return

        elif keuze == "2":
            ing_input = input("\n  Ingrediënten (komma-gescheiden): ").strip()
            ingredienten = [i.strip().lower() for i in ing_input.split(",")]

        elif keuze == "3":
            ingredienten = random.sample(
                [i for cat in self.CATEGORIEEN.values() for i in cat], 4
            )

        print(f"\n  Zoeken met: {', '.join(ingredienten)}")
        print("  Even geduld...\n")

        # Probeer AI eerst
        recept = self._genereer_recept_ai(ingredienten)

        if not recept:
            recept = self._genereer_recept_lokaal(ingredienten)

        # Toon recept
        self._toon_recept(recept)

        # Opslaan?
        if input("\n  Toevoegen aan favorieten? (j/n): ").lower() == "j":
            if recept not in self.data["favorieten"]:
                self.data["favorieten"].append(recept)
                self._sla_op()
                print("  Toegevoegd aan favorieten!")

        input("\n  Druk op Enter...")

    def _toon_recept(self, recept: Dict):
        """Toon een recept mooi geformatteerd."""
        print("  " + "=" * 50)
        print(f"  {recept['naam'].upper()}")
        print("  " + "=" * 50)
        print(f"\n  Tijd: {recept.get('tijd', '?')} min | Porties: {recept.get('porties', '?')}")

        print("\n  INGREDIËNTEN:")
        for ing in recept.get("ingredienten", []):
            print(f"    - {ing}")

        print("\n  BEREIDING:")
        for i, stap in enumerate(recept.get("stappen", []), 1):
            print(f"    {i}. {stap}")

    def _weekmenu_planner(self):
        """Plan weekmenu."""
        clear_scherm()
        print("\n  === WEEKMENU PLANNER ===\n")

        dagen = ["Maandag", "Dinsdag", "Woensdag", "Donderdag",
                 "Vrijdag", "Zaterdag", "Zondag"]

        menu = self.data.get("weekmenu", {})

        # Toon huidig menu
        print("  Huidig weekmenu:")
        for dag in dagen:
            gerecht = menu.get(dag, "---")
            print(f"    {dag:12}: {gerecht}")

        print("\n  Opties:")
        print("  1. Dag invullen")
        print("  2. Auto-genereer week")
        print("  3. Boodschappenlijst maken")
        print("  4. Menu wissen")
        print("  0. Terug")

        keuze = input("\n  Keuze: ").strip()

        if keuze == "1":
            print(f"\n  Dagen: {', '.join(dagen)}")
            dag = input("  Welke dag: ").strip().capitalize()
            if dag in dagen:
                gerecht = input("  Gerecht: ").strip()
                self.data["weekmenu"][dag] = gerecht
                self._sla_op()
                print("  Opgeslagen!")
            input("  Druk op Enter...")

        elif keuze == "2":
            alle_recepten = self.BASIS_RECEPTEN + self.data.get("favorieten", [])
            for dag in dagen:
                recept = random.choice(alle_recepten)
                self.data["weekmenu"][dag] = recept["naam"]
            self._sla_op()
            print("  Weekmenu gegenereerd!")
            input("  Druk op Enter...")

        elif keuze == "3":
            # Genereer boodschappenlijst
            alle_ingredienten = []
            alle_recepten = self.BASIS_RECEPTEN + self.data.get("favorieten", [])

            for dag, gerecht in self.data.get("weekmenu", {}).items():
                for recept in alle_recepten:
                    if recept["naam"] == gerecht:
                        alle_ingredienten.extend(recept.get("ingredienten", []))

            # Unieke items
            uniek = list(set(alle_ingredienten))
            self.data["boodschappenlijst"] = uniek
            self._sla_op()

            print("\n  BOODSCHAPPENLIJST:")
            for item in sorted(uniek):
                print(f"    [ ] {item}")

            input("\n  Druk op Enter...")

        elif keuze == "4":
            self.data["weekmenu"] = {}
            self._sla_op()
            print("  Menu gewist!")
            input("  Druk op Enter...")

    def _bekijk_favorieten(self):
        """Bekijk favoriete recepten."""
        clear_scherm()
        print("\n  === FAVORIETE RECEPTEN ===\n")

        favorieten = self.data.get("favorieten", [])

        if not favorieten:
            print("  Geen favorieten opgeslagen.")
            input("\n  Druk op Enter...")
            return

        for i, recept in enumerate(favorieten, 1):
            print(f"  {i}. {recept['naam']} ({recept.get('tijd', '?')} min)")

        keuze = input("\n  Bekijk # (of Enter voor terug): ").strip()
        if keuze.isdigit():
            idx = int(keuze) - 1
            if 0 <= idx < len(favorieten):
                clear_scherm()
                self._toon_recept(favorieten[idx])
                input("\n  Druk op Enter...")

    def run(self):
        """Start de app."""
        while True:
            clear_scherm()

            ai_status = "AI: Actief" if self.client else "AI: Uit (alleen lokaal)"

            print(f"""
  ╔═══════════════════════════════════════════════════════════╗
  ║              RECIPE GENERATOR v1.0                        ║
  ║            Recepten & Meal Planning                       ║
  ╠═══════════════════════════════════════════════════════════╣
  ║  1. Genereer Recept                                       ║
  ║  2. Voorraad Beheren                                      ║
  ║  3. Weekmenu Planner                                      ║
  ║  4. Favoriete Recepten                                    ║
  ║  0. Terug                                                 ║
  ╚═══════════════════════════════════════════════════════════╝
  {ai_status}
""")
            voorraad_count = sum(len(v) for v in self.data.get("voorraad", {}).values())
            print(f"  Voorraad: {voorraad_count} items | Favorieten: {len(self.data.get('favorieten', []))}")

            keuze = input("\n  Keuze: ").strip()

            if keuze == "0":
                break
            elif keuze == "1":
                self._genereer_recept()
            elif keuze == "2":
                self._beheer_voorraad()
            elif keuze == "3":
                self._weekmenu_planner()
            elif keuze == "4":
                self._bekijk_favorieten()

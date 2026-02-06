"""
Citaten Generator - Inspirerende citaten.
"""

import json
import random
from datetime import datetime
from ..core.config import Config
from ..core.utils import clear_scherm


class CitatenGeneratorApp:
    """Genereer en bewaar inspirerende citaten."""

    def __init__(self):
        Config.ensure_dirs()
        self.bestand = Config.APPS_DATA_DIR / "citaten.json"
        self.data = self._laad_data()

        # Ingebouwde citaten
        self.citaten = [
            ("De enige manier om geweldig werk te doen is houden van wat je doet.", "Steve Jobs"),
            ("Succes is niet definitief, falen is niet fataal: het is de moed om door te gaan die telt.", "Winston Churchill"),
            ("Geloof dat je het kunt en je bent al halverwege.", "Theodore Roosevelt"),
            ("De beste tijd om een boom te planten was 20 jaar geleden. De op een na beste tijd is nu.", "Chinees spreekwoord"),
            ("Het leven is wat er gebeurt terwijl je andere plannen maakt.", "John Lennon"),
            ("Wees de verandering die je in de wereld wilt zien.", "Mahatma Gandhi"),
            ("Een reis van duizend mijlen begint met een enkele stap.", "Lao Tzu"),
            ("Kennis is macht.", "Francis Bacon"),
            ("De enige echte wijsheid is weten dat je niets weet.", "Socrates"),
            ("Niet alles wat telt kan geteld worden.", "Albert Einstein"),
            ("Doe elke dag iets dat je bang maakt.", "Eleanor Roosevelt"),
            ("Het geheim van vooruitgang is beginnen.", "Mark Twain"),
            ("Perfectie is niet haalbaar, maar als we perfectie najagen kunnen we excellentie bereiken.", "Vince Lombardi"),
            ("De toekomst behoort toe aan hen die geloven in de schoonheid van hun dromen.", "Eleanor Roosevelt"),
            ("Succes is van falen naar falen gaan zonder je enthousiasme te verliezen.", "Winston Churchill"),
            ("Alles wat je je kunt voorstellen is echt.", "Pablo Picasso"),
            ("Je mist 100% van de schoten die je niet neemt.", "Wayne Gretzky"),
            ("In het midden van moeilijkheid ligt kans.", "Albert Einstein"),
            ("Leer van gisteren, leef voor vandaag, hoop op morgen.", "Albert Einstein"),
            ("Wat achter ons ligt en wat voor ons ligt zijn kleine zaken vergeleken met wat in ons ligt.", "Ralph Waldo Emerson"),
            ("Het is nooit te laat om te zijn wat je had kunnen zijn.", "George Eliot"),
            ("De beste wraak is massaal succes.", "Frank Sinatra"),
            ("Creativiteit is intelligentie die plezier heeft.", "Albert Einstein"),
            ("Eenvoud is de ultieme verfijning.", "Leonardo da Vinci"),
            ("Het enige dat we te vrezen hebben is de vrees zelf.", "Franklin D. Roosevelt"),
            ("Kansen komen niet, je creëert ze.", "Chris Grosser"),
            ("Je bent nooit te oud om nieuwe doelen te stellen of nieuwe dromen te dromen.", "C.S. Lewis"),
            ("Moeilijkheden in het leven zijn bedoeld om ons beter te maken, niet bitter.", "Dan Reeves"),
            ("Geluk is geen toeval, maar een keuze.", "Jim Rohn"),
            ("Elke expert was ooit een beginner.", "Helen Hayes")
        ]

    def _laad_data(self) -> dict:
        """Laad opgeslagen data."""
        if self.bestand.exists():
            try:
                with open(self.bestand, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {
            "favorieten": [],
            "eigen_citaten": [],
            "citaat_van_de_dag": {"datum": "", "citaat": "", "auteur": ""}
        }

    def _sla_op(self):
        """Sla data op."""
        with open(self.bestand, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    def run(self):
        """Start de citaten generator."""
        while True:
            clear_scherm()
            print("+" + "=" * 50 + "+")
            print("|          CITATEN GENERATOR                        |")
            print("+" + "=" * 50 + "+")
            self._toon_citaat_van_de_dag()
            print("+" + "-" * 50 + "+")
            print("|  1. Willekeurig citaat                            |")
            print("|  2. Citaat zoeken                                 |")
            print("|  3. Eigen citaat toevoegen                        |")
            print("|  4. Favorieten bekijken                           |")
            print("|  5. Alle eigen citaten                            |")
            print("|  0. Terug                                         |")
            print("+" + "=" * 50 + "+")

            keuze = input("\nKeuze: ").strip()

            if keuze == "0":
                break
            elif keuze == "1":
                self._willekeurig_citaat()
            elif keuze == "2":
                self._zoek_citaat()
            elif keuze == "3":
                self._eigen_citaat()
            elif keuze == "4":
                self._bekijk_favorieten()
            elif keuze == "5":
                self._eigen_citaten()

            input("\nDruk op Enter...")

    def _toon_citaat_van_de_dag(self):
        """Toon het citaat van de dag."""
        vandaag = datetime.now().date().isoformat()

        if self.data["citaat_van_de_dag"]["datum"] != vandaag:
            # Nieuw citaat kiezen
            citaat, auteur = random.choice(self.citaten)
            self.data["citaat_van_de_dag"] = {
                "datum": vandaag,
                "citaat": citaat,
                "auteur": auteur
            }
            self._sla_op()

        cvd = self.data["citaat_van_de_dag"]
        # Truncate voor display
        kort = cvd["citaat"][:45] + "..." if len(cvd["citaat"]) > 45 else cvd["citaat"]
        print(f"|  \"{kort}\"")
        print(f"|    - {cvd['auteur']:<45}|")

    def _willekeurig_citaat(self):
        """Toon een willekeurig citaat."""
        # Combineer ingebouwde en eigen citaten
        alle_citaten = self.citaten.copy()
        for ec in self.data["eigen_citaten"]:
            alle_citaten.append((ec["citaat"], ec["auteur"]))

        citaat, auteur = random.choice(alle_citaten)

        print("\n" + "=" * 50)
        print()
        # Word wrap
        woorden = citaat.split()
        regels = []
        regel = ""
        for woord in woorden:
            if len(regel) + len(woord) + 1 <= 46:
                regel = regel + " " + woord if regel else woord
            else:
                regels.append(regel)
                regel = woord
        if regel:
            regels.append(regel)

        for r in regels:
            print(f"  \"{r}\"")

        print(f"\n    - {auteur}")
        print("\n" + "=" * 50)

        # Optie om toe te voegen aan favorieten
        fav = input("\nToevoegen aan favorieten? (j/n): ").strip().lower()
        if fav == "j":
            if not any(f["citaat"] == citaat for f in self.data["favorieten"]):
                self.data["favorieten"].append({
                    "citaat": citaat,
                    "auteur": auteur,
                    "toegevoegd": datetime.now().isoformat()
                })
                self._sla_op()
                print("[OK] Toegevoegd aan favorieten!")
            else:
                print("[i] Dit citaat staat al in je favorieten.")

    def _zoek_citaat(self):
        """Zoek naar citaten."""
        print("\n--- CITAAT ZOEKEN ---")

        zoekterm = input("Zoekterm: ").strip().lower()
        if not zoekterm:
            return

        resultaten = []
        for citaat, auteur in self.citaten:
            if zoekterm in citaat.lower() or zoekterm in auteur.lower():
                resultaten.append((citaat, auteur))

        for ec in self.data["eigen_citaten"]:
            if zoekterm in ec["citaat"].lower() or zoekterm in ec["auteur"].lower():
                resultaten.append((ec["citaat"], ec["auteur"]))

        print(f"\n--- {len(resultaten)} RESULTATEN ---")

        for i, (citaat, auteur) in enumerate(resultaten[:10], 1):
            kort = citaat[:50] + "..." if len(citaat) > 50 else citaat
            print(f"\n  {i}. \"{kort}\"")
            print(f"     - {auteur}")

    def _eigen_citaat(self):
        """Voeg een eigen citaat toe."""
        print("\n--- EIGEN CITAAT TOEVOEGEN ---")

        citaat = input("Citaat: ").strip()
        if not citaat:
            print("[!] Citaat is verplicht!")
            return

        auteur = input("Auteur (of 'Onbekend'): ").strip() or "Onbekend"

        eigen = {
            "citaat": citaat,
            "auteur": auteur,
            "toegevoegd": datetime.now().isoformat()
        }

        self.data["eigen_citaten"].append(eigen)
        self._sla_op()

        print(f"\n[OK] Citaat toegevoegd!")

    def _bekijk_favorieten(self):
        """Bekijk favoriete citaten."""
        print("\n--- FAVORIETEN ---")

        if not self.data["favorieten"]:
            print("Geen favorieten opgeslagen.")
            print("Tip: Voeg citaten toe via 'Willekeurig citaat'!")
            return

        for i, f in enumerate(self.data["favorieten"], 1):
            print(f"\n  {i}. \"{f['citaat'][:50]}{'...' if len(f['citaat']) > 50 else ''}\"")
            print(f"     - {f['auteur']}")

        # Optie om te verwijderen
        keuze = input("\nNummer om te verwijderen (of Enter): ").strip()
        if keuze:
            try:
                idx = int(keuze) - 1
                if 0 <= idx < len(self.data["favorieten"]):
                    verwijderd = self.data["favorieten"].pop(idx)
                    self._sla_op()
                    print(f"[OK] Verwijderd uit favorieten.")
            except ValueError:
                pass

    def _eigen_citaten(self):
        """Bekijk eigen citaten."""
        print("\n--- EIGEN CITATEN ---")

        if not self.data["eigen_citaten"]:
            print("Geen eigen citaten toegevoegd.")
            return

        for i, ec in enumerate(self.data["eigen_citaten"], 1):
            print(f"\n  {i}. \"{ec['citaat'][:50]}{'...' if len(ec['citaat']) > 50 else ''}\"")
            print(f"     - {ec['auteur']}")

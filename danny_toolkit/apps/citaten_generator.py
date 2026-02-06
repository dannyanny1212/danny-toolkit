"""
Citaten Generator v2.0 - AI-Powered inspirerende citaten.
"""

import json
import os
import random
from datetime import datetime
from ..core.config import Config
from ..core.utils import clear_scherm

# AI Integration
try:
    from anthropic import Anthropic
    AI_BESCHIKBAAR = True
except ImportError:
    AI_BESCHIKBAAR = False


class CitatenGeneratorApp:
    """AI-Powered citaten generator."""

    VERSIE = "2.0"

    def __init__(self):
        Config.ensure_dirs()
        self.bestand = Config.APPS_DATA_DIR / "citaten.json"
        self.data = self._laad_data()
        self.client = None
        self._init_ai()

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

    def _init_ai(self):
        """Initialiseer AI client."""
        if AI_BESCHIKBAAR:
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if api_key:
                try:
                    self.client = Anthropic(api_key=api_key)
                except Exception:
                    self.client = None

    def _ai_request(self, prompt: str, max_tokens: int = 500) -> str:
        """Maak een AI request."""
        if not self.client:
            return None
        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text
        except Exception:
            return None

    def _sla_op(self):
        """Sla data op."""
        with open(self.bestand, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    def run(self):
        """Start de citaten generator."""
        while True:
            clear_scherm()
            print("+" + "=" * 50 + "+")
            print("|          CITATEN GENERATOR v2.0                   |")
            if self.client:
                print("|          [AI POWERED]                            |")
            print("+" + "=" * 50 + "+")
            self._toon_citaat_van_de_dag()
            print("+" + "-" * 50 + "+")
            print("|  1. Willekeurig citaat                            |")
            print("|  2. Citaat zoeken                                 |")
            print("|  3. Eigen citaat toevoegen                        |")
            print("|  4. Favorieten bekijken                           |")
            print("|  5. Alle eigen citaten                            |")
            print("+" + "-" * 50 + "+")
            print("|  [AI FUNCTIES]                                    |")
            print("|  6. AI Citaat Genereren                           |")
            print("|  7. AI Citaat Uitleg                              |")
            print("|  8. AI Persoonlijk Citaat                         |")
            print("+" + "-" * 50 + "+")
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
            elif keuze == "6":
                self._ai_citaat_genereren()
            elif keuze == "7":
                self._ai_citaat_uitleg()
            elif keuze == "8":
                self._ai_persoonlijk_citaat()

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

    # ==================== AI FUNCTIES ====================

    def _ai_citaat_genereren(self):
        """AI genereert een citaat over een thema."""
        print("\n--- AI CITAAT GENEREREN ---")

        print("Thema's: motivatie, wijsheid, liefde, succes, geluk, vriendschap")
        thema = input("Kies thema (of eigen woord): ").strip()
        if not thema:
            thema = "inspiratie"

        if not self.client:
            # Fallback: random ingebouwd citaat
            citaat, auteur = random.choice(self.citaten)
            print(f"\n\"{citaat}\"")
            print(f"    - {auteur}")
            return

        print("\n[AI genereert citaat...]")
        prompt = f"""Genereer een origineel, inspirerend citaat over: {thema}

Het citaat moet:
- Diepzinnig maar toegankelijk zijn
- Tussen 10-25 woorden
- Tijdloos en universeel

Format:
CITAAT: [het citaat]
AUTEUR: AI Wijsheid"""

        response = self._ai_request(prompt, max_tokens=150)
        if response:
            print(f"\n{response}")

            opslaan = input("\nOpslaan in eigen citaten? (j/n): ").strip().lower()
            if opslaan == "j":
                # Parse
                if "CITAAT:" in response:
                    citaat = response.split("CITAAT:")[1].split("AUTEUR:")[0].strip()
                    auteur = "AI Wijsheid"
                    self.data["eigen_citaten"].append({
                        "citaat": citaat,
                        "auteur": auteur,
                        "toegevoegd": datetime.now().isoformat()
                    })
                    self._sla_op()
                    print("[OK] Citaat opgeslagen!")

    def _ai_citaat_uitleg(self):
        """AI legt een citaat uit."""
        print("\n--- AI CITAAT UITLEG ---")

        # Toon wat citaten
        print("\nRecente citaten:")
        sample = self.citaten[:5]
        for i, (c, a) in enumerate(sample, 1):
            print(f"  {i}. \"{c[:40]}...\" - {a}")

        keuze = input("\nKies nummer of typ eigen citaat: ").strip()

        try:
            idx = int(keuze) - 1
            citaat, auteur = sample[idx]
        except (ValueError, IndexError):
            citaat = keuze
            auteur = "Onbekend"

        if not self.client:
            print(f"\n[Citaat]: \"{citaat}\"")
            print("\n[Betekenis]: Denk na over hoe dit van toepassing is op jouw leven.")
            return

        print("\n[AI analyseert...]")
        prompt = f"""Leg dit citaat uit:

"{citaat}" - {auteur}

Geef:
1. De kernboodschap
2. Historische/filosofische context
3. Hoe je het kunt toepassen in je leven
4. Gerelateerde wijsheid

Helder en inspirerend. Nederlands."""

        response = self._ai_request(prompt, max_tokens=500)
        if response:
            print(f"\n[AI Uitleg]:\n{response}")

    def _ai_persoonlijk_citaat(self):
        """AI maakt een persoonlijk citaat voor jou."""
        print("\n--- AI PERSOONLIJK CITAAT ---")

        print("Vertel me over je situatie (werk, liefde, uitdaging, etc.):")
        situatie = input("> ").strip()
        if not situatie:
            print("[!] Beschrijf je situatie voor een persoonlijk citaat.")
            return

        if not self.client:
            print("\n[Persoonlijke wijsheid]:")
            print("  Elke reis begint met een enkele stap.")
            return

        print("\n[AI creëert persoonlijk citaat...]")
        prompt = f"""Iemand beschrijft hun situatie: "{situatie}"

Creëer een kort, krachtig citaat specifiek voor hen.
Het moet:
- Direct relevant zijn voor hun situatie
- Bemoedigend en empowerend
- Poëtisch maar praktisch
- 10-20 woorden

Geef alleen het citaat, niets anders."""

        response = self._ai_request(prompt, max_tokens=100)
        if response:
            print(f"\n  \"{response}\"")
            print("    - Speciaal voor jou")

            opslaan = input("\nOpslaan? (j/n): ").strip().lower()
            if opslaan == "j":
                self.data["eigen_citaten"].append({
                    "citaat": response.strip('"'),
                    "auteur": "Persoonlijke AI",
                    "toegevoegd": datetime.now().isoformat()
                })
                self._sla_op()
                print("[OK] Opgeslagen!")

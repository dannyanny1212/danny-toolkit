"""
Decision Maker v1.0 - Pro/con analyse, weighted scoring, random picker.
"""

import json
import logging
import random
from datetime import datetime
from typing import Dict
from ..core.config import Config
from ..core.utils import clear_scherm

logger = logging.getLogger(__name__)


class DecisionMakerApp:
    """Decision Maker - Hulp bij het nemen van beslissingen."""

    VERSIE = "1.0"

    # Voorgedefinieerde criteria categorieën
    CRITERIA_TEMPLATES = {
        "carriere": [
            ("Salaris", 0.2),
            ("Werkplezier", 0.25),
            ("Groei mogelijkheden", 0.2),
            ("Werk-prive balans", 0.2),
            ("Locatie", 0.15),
        ],
        "aankoop": [
            ("Prijs", 0.25),
            ("Kwaliteit", 0.25),
            ("Reviews", 0.15),
            ("Functies", 0.2),
            ("Garantie", 0.15),
        ],
        "woning": [
            ("Locatie", 0.25),
            ("Grootte", 0.2),
            ("Prijs", 0.25),
            ("Staat", 0.15),
            ("Voorzieningen", 0.15),
        ],
    }

    def __init__(self):
        Config.ensure_dirs()
        self.data_dir = Config.APPS_DATA_DIR / "decision_maker"
        self.data_dir.mkdir(exist_ok=True)
        self.data_file = self.data_dir / "decisions.json"
        self.data = self._laad_data()

    def _laad_data(self) -> Dict:
        """Laad beslissingen data."""
        if self.data_file.exists():
            try:
                with open(self.data_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.debug("Decision data load error: %s", e)
        return {
            "beslissingen": [],
            "snelle_keuzes": [],
        }

    def _sla_op(self):
        """Sla data op."""
        with open(self.data_file, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    def _random_picker(self):
        """Random keuze maken."""
        clear_scherm()
        print("\n  === RANDOM PICKER ===\n")
        print("  Laat het lot beslissen!\n")

        print("  Voer opties in (een per regel, leeg = klaar):")

        opties = []
        while True:
            optie = input(f"  {len(opties) + 1}. ").strip()
            if not optie:
                break
            opties.append(optie)

        if len(opties) < 2:
            print("\n  Minimaal 2 opties nodig!")
            input("  Druk op Enter...")
            return

        print("\n  De opties zijn:")
        for i, opt in enumerate(opties, 1):
            print(f"    {i}. {opt}")

        print("\n  Draaien aan het rad...")
        input("  Druk op Enter om te stoppen...")

        keuze = random.choice(opties)

        print("\n  " + "=" * 40)
        print(f"  DE KEUZE IS: {keuze.upper()}")
        print("  " + "=" * 40)

        # Log
        self.data["snelle_keuzes"].append({
            "datum": datetime.now().isoformat(),
            "opties": opties,
            "keuze": keuze,
        })
        self._sla_op()

        input("\n  Druk op Enter...")

    def _pro_con_analyse(self):
        """Pro/Con analyse voor een beslissing."""
        clear_scherm()
        print("\n  === PRO/CON ANALYSE ===\n")

        vraag = input("  Wat is de beslissing? ").strip()
        if not vraag:
            return

        beslissing = {
            "type": "pro_con",
            "vraag": vraag,
            "datum": datetime.now().isoformat(),
            "pros": [],
            "cons": [],
            "conclusie": "",
        }

        # Pros
        print("\n  VOORDELEN (pros) - leeg = klaar:")
        while True:
            pro = input("    + ").strip()
            if not pro:
                break
            # Vraag gewicht
            try:
                gewicht = int(input("      Belang (1-5): ").strip() or "3")
                gewicht = max(1, min(5, gewicht))
            except ValueError:
                gewicht = 3
            beslissing["pros"].append({"tekst": pro, "gewicht": gewicht})

        # Cons
        print("\n  NADELEN (cons) - leeg = klaar:")
        while True:
            con = input("    - ").strip()
            if not con:
                break
            try:
                gewicht = int(input("      Belang (1-5): ").strip() or "3")
                gewicht = max(1, min(5, gewicht))
            except ValueError:
                gewicht = 3
            beslissing["cons"].append({"tekst": con, "gewicht": gewicht})

        # Bereken scores
        pro_score = sum(p["gewicht"] for p in beslissing["pros"])
        con_score = sum(c["gewicht"] for c in beslissing["cons"])

        # Toon resultaat
        clear_scherm()
        print("\n  " + "=" * 50)
        print(f"  {vraag.upper()}")
        print("  " + "=" * 50)

        print("\n  VOORDELEN:")
        for p in beslissing["pros"]:
            stars = "*" * p["gewicht"]
            print(f"    + {p['tekst']} [{stars}]")
        print(f"    Totaal: {pro_score}")

        print("\n  NADELEN:")
        for c in beslissing["cons"]:
            stars = "*" * c["gewicht"]
            print(f"    - {c['tekst']} [{stars}]")
        print(f"    Totaal: {con_score}")

        print("\n  " + "-" * 50)

        if pro_score > con_score:
            advies = "DOEN - De voordelen wegen zwaarder!"
        elif con_score > pro_score:
            advies = "NIET DOEN - De nadelen wegen zwaarder!"
        else:
            advies = "TOSS-UP - Evenveel voor- als nadelen!"

        print(f"  ADVIES: {advies}")
        print(f"  Score: {pro_score} vs {con_score}")

        beslissing["conclusie"] = advies
        self.data["beslissingen"].append(beslissing)
        self._sla_op()

        input("\n  Druk op Enter...")

    def _weighted_scoring(self):
        """Gewogen score vergelijking van meerdere opties."""
        clear_scherm()
        print("\n  === GEWOGEN VERGELIJKING ===\n")

        vraag = input("  Wat wil je vergelijken? ").strip()
        if not vraag:
            return

        # Template kiezen
        print("\n  Criteria templates:")
        print("    1. Carrière keuze")
        print("    2. Aankoop beslissing")
        print("    3. Woning keuze")
        print("    4. Eigen criteria")

        template_keuze = input("\n  Keuze: ").strip()

        criteria = []

        if template_keuze == "1":
            criteria = list(self.CRITERIA_TEMPLATES["carriere"])
        elif template_keuze == "2":
            criteria = list(self.CRITERIA_TEMPLATES["aankoop"])
        elif template_keuze == "3":
            criteria = list(self.CRITERIA_TEMPLATES["woning"])
        else:
            # Eigen criteria
            print("\n  Voer criteria in (naam, gewicht 0-1):")
            print("  Voorbeeld: Prijs 0.3")

            while True:
                crit_input = input("  > ").strip()
                if not crit_input:
                    break

                parts = crit_input.rsplit(" ", 1)
                if len(parts) == 2:
                    try:
                        naam = parts[0]
                        gewicht = float(parts[1])
                        criteria.append((naam, gewicht))
                    except ValueError:
                        print("    Ongeldig formaat!")
                else:
                    criteria.append((crit_input, 0.2))

        if not criteria:
            print("  Geen criteria opgegeven!")
            input("  Druk op Enter...")
            return

        # Normaliseer gewichten
        totaal_gewicht = sum(g for _, g in criteria)
        if totaal_gewicht > 0:
            criteria = [(n, g/totaal_gewicht) for n, g in criteria]

        # Opties invoeren
        print("\n  Voer opties in (leeg = klaar):")
        opties = []
        while True:
            optie = input(f"  Optie {len(opties) + 1}: ").strip()
            if not optie:
                break
            opties.append(optie)

        if len(opties) < 2:
            print("  Minimaal 2 opties nodig!")
            input("  Druk op Enter...")
            return

        # Score elke optie
        scores = {opt: [] for opt in opties}

        for crit_naam, crit_gewicht in criteria:
            print(f"\n  Score voor: {crit_naam} (gewicht: {crit_gewicht:.0%})")
            print("  Geef elke optie een score van 1-10:")

            for opt in opties:
                try:
                    score = int(input(f"    {opt}: ").strip() or "5")
                    score = max(1, min(10, score))
                except ValueError:
                    score = 5

                scores[opt].append(score * crit_gewicht)

        # Bereken totalen
        totalen = {}
        for opt in opties:
            totalen[opt] = sum(scores[opt])

        # Toon resultaat
        clear_scherm()
        print("\n  " + "=" * 50)
        print(f"  VERGELIJKING: {vraag.upper()}")
        print("  " + "=" * 50)

        print("\n  CRITERIA:")
        for naam, gewicht in criteria:
            print(f"    {naam}: {gewicht:.0%}")

        print("\n  SCORES:")

        # Sorteer op score
        gesorteerd = sorted(totalen.items(), key=lambda x: x[1], reverse=True)

        for i, (opt, score) in enumerate(gesorteerd, 1):
            bar_len = int(score * 5)
            bar = "#" * bar_len
            medal = ["1e", "2e", "3e"][i-1] if i <= 3 else f"{i}e"
            print(f"    {medal} {opt:20} {bar} ({score:.1f})")

        winnaar = gesorteerd[0][0]
        print("\n  " + "-" * 50)
        print(f"  WINNAAR: {winnaar.upper()}")

        # Opslaan
        self.data["beslissingen"].append({
            "type": "weighted",
            "vraag": vraag,
            "datum": datetime.now().isoformat(),
            "criteria": criteria,
            "opties": opties,
            "scores": totalen,
            "winnaar": winnaar,
        })
        self._sla_op()

        input("\n  Druk op Enter...")

    def _ja_nee_helper(self):
        """Simpele ja/nee beslissing met vragen."""
        clear_scherm()
        print("\n  === JA/NEE HELPER ===\n")

        vraag = input("  Stel je ja/nee vraag: ").strip()
        if not vraag:
            return

        print("\n  Beantwoord de volgende vragen (1-5):")
        print("  1 = Helemaal niet, 5 = Zeer zeker\n")

        vragen = [
            "Past dit bij je lange termijn doelen?",
            "Voel je je er goed bij?",
            "Kun je het je veroorloven (tijd/geld)?",
            "Wat zouden mensen die je vertrouwt zeggen?",
            "Zou je over een jaar blij zijn met deze keuze?",
        ]

        scores = []
        for v in vragen:
            try:
                score = int(input(f"  {v} (1-5): ").strip() or "3")
                scores.append(max(1, min(5, score)))
            except ValueError:
                scores.append(3)

        gemiddelde = sum(scores) / len(scores)

        clear_scherm()
        print("\n  " + "=" * 50)
        print(f"  {vraag.upper()}")
        print("  " + "=" * 50)

        print("\n  Je antwoorden:")
        for v, s in zip(vragen, scores):
            bar = "*" * s
            print(f"    {bar} {v[:40]}")

        print(f"\n  Gemiddelde score: {gemiddelde:.1f}/5")

        if gemiddelde >= 4:
            advies = "STERK JA - Ga ervoor!"
        elif gemiddelde >= 3:
            advies = "WAARSCHIJNLIJK JA - Overweeg het serieus"
        elif gemiddelde >= 2:
            advies = "WAARSCHIJNLIJK NEE - Denk er nog over na"
        else:
            advies = "NEE - Dit lijkt niet de juiste keuze"

        print(f"\n  ADVIES: {advies}")

        input("\n  Druk op Enter...")

    def _bekijk_geschiedenis(self):
        """Bekijk eerdere beslissingen."""
        clear_scherm()
        print("\n  === BESLISSINGEN GESCHIEDENIS ===\n")

        beslissingen = self.data.get("beslissingen", [])

        if not beslissingen:
            print("  Nog geen beslissingen opgeslagen.")
            input("\n  Druk op Enter...")
            return

        for i, b in enumerate(reversed(beslissingen[-10:]), 1):
            datum = b["datum"][:10]
            type_ = b["type"]
            vraag = b["vraag"][:40]
            print(f"  {i}. {datum} [{type_}] {vraag}")

        keuze = input("\n  Bekijk # (of Enter): ").strip()

        if keuze.isdigit():
            idx = len(beslissingen) - int(keuze)
            if 0 <= idx < len(beslissingen):
                b = beslissingen[idx]

                clear_scherm()
                print("\n  " + "=" * 50)
                print(f"  {b['vraag']}")
                print("  " + "=" * 50)
                print(f"\n  Datum: {b['datum'][:10]}")
                print(f"  Type: {b['type']}")

                if b["type"] == "pro_con":
                    print("\n  Voordelen:")
                    for p in b.get("pros", []):
                        print(f"    + {p['tekst']}")
                    print("\n  Nadelen:")
                    for c in b.get("cons", []):
                        print(f"    - {c['tekst']}")
                    print(f"\n  Conclusie: {b.get('conclusie', '-')}")

                elif b["type"] == "weighted":
                    print(f"\n  Winnaar: {b.get('winnaar', '-')}")
                    print("\n  Scores:")
                    for opt, score in b.get("scores", {}).items():
                        print(f"    {opt}: {score:.1f}")

                input("\n  Druk op Enter...")

    def _coin_flip(self):
        """Simpele munt opgooi."""
        clear_scherm()
        print("\n  === MUNT OPGOOIEN ===\n")

        print("  Gooi een munt...")
        input("  Druk op Enter...")

        resultaat = random.choice(["KOP", "MUNT"])

        print(f"""
     _______
    /       \\
   |  {resultaat:^5}  |
    \\_______/

  Resultaat: {resultaat}
""")

        input("\n  Druk op Enter...")

    def run(self):
        """Start de app."""
        while True:
            clear_scherm()

            beslissingen = len(self.data.get("beslissingen", []))

            print(f"""
  ╔═══════════════════════════════════════════════════════════╗
  ║              DECISION MAKER v1.0                          ║
  ║              Hulp bij Beslissingen                        ║
  ╠═══════════════════════════════════════════════════════════╣
  ║  1. Random Picker                                         ║
  ║  2. Pro/Con Analyse                                       ║
  ║  3. Gewogen Vergelijking                                  ║
  ║  4. Ja/Nee Helper                                         ║
  ║  5. Munt Opgooien                                         ║
  ║  6. Bekijk Geschiedenis                                   ║
  ║  0. Terug                                                 ║
  ╚═══════════════════════════════════════════════════════════╝
""")
            print(f"  Opgeslagen beslissingen: {beslissingen}")

            keuze = input("\n  Keuze: ").strip()

            if keuze == "0":
                break
            elif keuze == "1":
                self._random_picker()
            elif keuze == "2":
                self._pro_con_analyse()
            elif keuze == "3":
                self._weighted_scoring()
            elif keuze == "4":
                self._ja_nee_helper()
            elif keuze == "5":
                self._coin_flip()
            elif keuze == "6":
                self._bekijk_geschiedenis()

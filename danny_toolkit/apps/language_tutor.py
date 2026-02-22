"""
Language Tutor v1.0 - Woordenschat trainer, quizzes, spaced repetition.
"""

import json
import logging
import random
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
from ..core.config import Config
from ..core.utils import clear_scherm

logger = logging.getLogger(__name__)


class LanguageTutorApp:
    """Language Tutor - Leer nieuwe talen met spaced repetition."""

    VERSIE = "1.0"

    # Beschikbare talen met basis woordenschat
    TALEN = {
        "engels": {
            "naam": "English",
            "woorden": [
                ("hallo", "hello"), ("wereld", "world"), ("boek", "book"),
                ("water", "water"), ("eten", "food"), ("huis", "house"),
                ("auto", "car"), ("school", "school"), ("vriend", "friend"),
                ("familie", "family"), ("werk", "work"), ("tijd", "time"),
                ("dag", "day"), ("nacht", "night"), ("zon", "sun"),
                ("maan", "moon"), ("ster", "star"), ("boom", "tree"),
                ("bloem", "flower"), ("dier", "animal"),
            ]
        },
        "duits": {
            "naam": "Deutsch",
            "woorden": [
                ("hallo", "Hallo"), ("wereld", "Welt"), ("boek", "Buch"),
                ("water", "Wasser"), ("eten", "Essen"), ("huis", "Haus"),
                ("auto", "Auto"), ("school", "Schule"), ("vriend", "Freund"),
                ("familie", "Familie"), ("werk", "Arbeit"), ("tijd", "Zeit"),
                ("dag", "Tag"), ("nacht", "Nacht"), ("zon", "Sonne"),
            ]
        },
        "frans": {
            "naam": "Francais",
            "woorden": [
                ("hallo", "bonjour"), ("wereld", "monde"), ("boek", "livre"),
                ("water", "eau"), ("eten", "nourriture"), ("huis", "maison"),
                ("auto", "voiture"), ("school", "ecole"), ("vriend", "ami"),
                ("familie", "famille"), ("werk", "travail"), ("tijd", "temps"),
                ("dag", "jour"), ("nacht", "nuit"), ("zon", "soleil"),
            ]
        },
        "spaans": {
            "naam": "Espanol",
            "woorden": [
                ("hallo", "hola"), ("wereld", "mundo"), ("boek", "libro"),
                ("water", "agua"), ("eten", "comida"), ("huis", "casa"),
                ("auto", "coche"), ("school", "escuela"), ("vriend", "amigo"),
                ("familie", "familia"), ("werk", "trabajo"), ("tijd", "tiempo"),
                ("dag", "dia"), ("nacht", "noche"), ("zon", "sol"),
            ]
        },
    }

    # Spaced repetition intervallen (in dagen)
    SR_INTERVALLEN = [1, 3, 7, 14, 30, 90]

    def __init__(self):
        Config.ensure_dirs()
        self.data_dir = Config.APPS_DATA_DIR / "language_tutor"
        self.data_dir.mkdir(exist_ok=True)
        self.data_file = self.data_dir / "progress.json"
        self.data = self._laad_data()

    def _laad_data(self) -> Dict:
        """Laad voortgang data."""
        if self.data_file.exists():
            try:
                with open(self.data_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.debug("Language tutor data load error: %s", e)
        return {
            "actieve_taal": None,
            "woorden": {},  # {taal: {woord: {stats}}}
            "custom_woorden": {},  # {taal: [(nl, vreemd)]}
            "sessies": [],
            "streak": 0,
            "laatste_sessie": None,
        }

    def _sla_op(self):
        """Sla data op."""
        with open(self.data_file, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    def _kies_taal(self):
        """Kies actieve taal."""
        clear_scherm()
        print("\n  === KIES TAAL ===\n")

        for i, (code, info) in enumerate(self.TALEN.items(), 1):
            woorden = len(info["woorden"])
            custom = len(self.data.get("custom_woorden", {}).get(code, []))
            print(f"  {i}. {info['naam']} ({code}) - {woorden + custom} woorden")

        try:
            keuze = int(input("\n  Keuze: ").strip())
            talen = list(self.TALEN.keys())
            if 1 <= keuze <= len(talen):
                self.data["actieve_taal"] = talen[keuze - 1]
                self._sla_op()
                print(f"\n  Actieve taal: {self.data['actieve_taal']}")
        except (ValueError, IndexError):
            pass

        input("\n  Druk op Enter...")

    def _get_woorden(self, taal: str) -> List[Tuple[str, str]]:
        """Haal alle woorden voor een taal."""
        basis = self.TALEN.get(taal, {}).get("woorden", [])
        custom = self.data.get("custom_woorden", {}).get(taal, [])
        return basis + custom

    def _get_woord_stats(self, taal: str, woord: str) -> Dict:
        """Haal statistieken voor een woord."""
        if taal not in self.data["woorden"]:
            self.data["woorden"][taal] = {}

        if woord not in self.data["woorden"][taal]:
            self.data["woorden"][taal][woord] = {
                "correct": 0,
                "fout": 0,
                "level": 0,
                "volgende_review": datetime.now().isoformat(),
            }

        return self.data["woorden"][taal][woord]

    def _update_woord_stats(self, taal: str, woord: str, correct: bool):
        """Update statistieken na een antwoord."""
        stats = self._get_woord_stats(taal, woord)

        if correct:
            stats["correct"] += 1
            stats["level"] = min(stats["level"] + 1, len(self.SR_INTERVALLEN) - 1)
        else:
            stats["fout"] += 1
            stats["level"] = max(0, stats["level"] - 1)

        # Bereken volgende review datum
        dagen = self.SR_INTERVALLEN[stats["level"]]
        volgende = datetime.now() + timedelta(days=dagen)
        stats["volgende_review"] = volgende.isoformat()

        self._sla_op()

    def _get_due_woorden(self, taal: str) -> List[Tuple[str, str]]:
        """Haal woorden die gereviewed moeten worden."""
        alle_woorden = self._get_woorden(taal)
        due = []

        for nl, vreemd in alle_woorden:
            stats = self._get_woord_stats(taal, nl)
            review_datum = datetime.fromisoformat(stats["volgende_review"])

            if review_datum <= datetime.now():
                due.append((nl, vreemd))

        return due

    def _oefen_sessie(self):
        """Start een oefensessie."""
        taal = self.data.get("actieve_taal")
        if not taal:
            print("\n  Kies eerst een taal!")
            input("  Druk op Enter...")
            return

        clear_scherm()
        print(f"\n  === OEFENSESSIE: {self.TALEN[taal]['naam'].upper()} ===\n")

        # Haal due woorden
        due = self._get_due_woorden(taal)

        if not due:
            print("  Geen woorden om te reviewen!")
            print("  Alle woorden zijn up-to-date.")
            input("\n  Druk op Enter...")
            return

        # Neem max 10 woorden
        woorden = random.sample(due, min(10, len(due)))

        correct = 0
        fout = 0

        for i, (nl, vreemd) in enumerate(woorden, 1):
            clear_scherm()
            print(f"\n  Vraag {i}/{len(woorden)}")
            print(f"  Correct: {correct} | Fout: {fout}")
            print("\n  " + "=" * 40)

            # Wissel richting
            if random.random() < 0.5:
                print(f"\n  Nederlands: {nl}")
                print(f"  Vertaal naar {self.TALEN[taal]['naam']}:")
                antwoord = input("\n  > ").strip().lower()
                goed = antwoord == vreemd.lower()
                correct_antwoord = vreemd
            else:
                print(f"\n  {self.TALEN[taal]['naam']}: {vreemd}")
                print(f"  Vertaal naar Nederlands:")
                antwoord = input("\n  > ").strip().lower()
                goed = antwoord == nl.lower()
                correct_antwoord = nl

            if goed:
                print("\n  CORRECT!")
                correct += 1
            else:
                print(f"\n  FOUT! Het juiste antwoord was: {correct_antwoord}")
                fout += 1

            self._update_woord_stats(taal, nl, goed)
            input("\n  Druk op Enter...")

        # Sessie samenvatting
        clear_scherm()
        print("\n  === SESSIE VOLTOOID ===\n")
        print(f"  Correct: {correct}/{len(woorden)}")
        score = correct / len(woorden) * 100
        print(f"  Score: {score:.0f}%")

        # Update streak
        self.data["sessies"].append({
            "datum": datetime.now().isoformat(),
            "taal": taal,
            "correct": correct,
            "totaal": len(woorden),
        })
        self.data["laatste_sessie"] = datetime.now().isoformat()

        # Check streak
        if self.data.get("laatste_sessie"):
            laatste = datetime.fromisoformat(self.data["laatste_sessie"])
            if (datetime.now() - laatste).days <= 1:
                self.data["streak"] += 1
            else:
                self.data["streak"] = 1

        self._sla_op()

        print(f"  Streak: {self.data['streak']} dagen!")

        input("\n  Druk op Enter...")

    def _snel_quiz(self):
        """Snelle quiz zonder spaced repetition."""
        taal = self.data.get("actieve_taal")
        if not taal:
            print("\n  Kies eerst een taal!")
            input("  Druk op Enter...")
            return

        clear_scherm()
        print(f"\n  === SNELLE QUIZ: {self.TALEN[taal]['naam'].upper()} ===\n")

        woorden = self._get_woorden(taal)

        if len(woorden) < 4:
            print("  Niet genoeg woorden voor een quiz!")
            input("\n  Druk op Enter...")
            return

        # Multiple choice quiz
        aantal = min(5, len(woorden))
        quiz_woorden = random.sample(woorden, aantal)

        correct = 0

        for i, (nl, vreemd) in enumerate(quiz_woorden, 1):
            clear_scherm()
            print(f"\n  Vraag {i}/{aantal}")
            print("\n  " + "=" * 40)
            print(f"\n  Wat is '{nl}' in het {self.TALEN[taal]['naam']}?\n")

            # Genereer opties
            opties = [vreemd]
            andere = [w[1] for w in woorden if w[1] != vreemd]
            opties.extend(random.sample(andere, min(3, len(andere))))
            random.shuffle(opties)

            for j, optie in enumerate(opties, 1):
                print(f"  {j}. {optie}")

            try:
                antwoord = int(input("\n  Keuze (1-4): ").strip())
                if opties[antwoord - 1].lower() == vreemd.lower():
                    print("\n  CORRECT!")
                    correct += 1
                else:
                    print(f"\n  FOUT! Het was: {vreemd}")
            except (ValueError, IndexError):
                print(f"\n  Ongeldig! Het was: {vreemd}")

            input("\n  Druk op Enter...")

        # Resultaat
        clear_scherm()
        print("\n  === QUIZ RESULTAAT ===\n")
        print(f"  Score: {correct}/{aantal} ({correct/aantal*100:.0f}%)")

        input("\n  Druk op Enter...")

    def _voeg_woord_toe(self):
        """Voeg eigen woord toe."""
        taal = self.data.get("actieve_taal")
        if not taal:
            print("\n  Kies eerst een taal!")
            input("  Druk op Enter...")
            return

        clear_scherm()
        print(f"\n  === NIEUW WOORD TOEVOEGEN ({taal.upper()}) ===\n")

        nl = input("  Nederlands: ").strip().lower()
        vreemd = input(f"  {self.TALEN[taal]['naam']}: ").strip()

        if nl and vreemd:
            if taal not in self.data["custom_woorden"]:
                self.data["custom_woorden"][taal] = []

            self.data["custom_woorden"][taal].append((nl, vreemd))
            self._sla_op()
            print("\n  Woord toegevoegd!")
        else:
            print("\n  Beide velden zijn verplicht!")

        input("\n  Druk op Enter...")

    def _bekijk_woordenschat(self):
        """Bekijk alle woorden."""
        taal = self.data.get("actieve_taal")
        if not taal:
            print("\n  Kies eerst een taal!")
            input("  Druk op Enter...")
            return

        clear_scherm()
        print(f"\n  === WOORDENSCHAT: {self.TALEN[taal]['naam'].upper()} ===\n")

        woorden = self._get_woorden(taal)

        print(f"  {'Nederlands':20} | {self.TALEN[taal]['naam']:20} | Level | Due")
        print("  " + "-" * 60)

        for nl, vreemd in sorted(woorden):
            stats = self._get_woord_stats(taal, nl)
            level = stats["level"]
            review = datetime.fromisoformat(stats["volgende_review"])
            due = "Nu!" if review <= datetime.now() else review.strftime("%d-%m")

            print(f"  {nl:20} | {vreemd:20} | {level:5} | {due}")

        input("\n  Druk op Enter...")

    def _toon_statistieken(self):
        """Toon leerstatistieken."""
        clear_scherm()
        print("\n  === LEERSTATISTIEKEN ===\n")

        print(f"  Streak: {self.data.get('streak', 0)} dagen")
        print(f"  Totaal sessies: {len(self.data.get('sessies', []))}")

        sessies = self.data.get("sessies", [])
        if sessies:
            totaal_correct = sum(s["correct"] for s in sessies)
            totaal_vragen = sum(s["totaal"] for s in sessies)
            if totaal_vragen > 0:
                print(f"  Gemiddelde score: {totaal_correct/totaal_vragen*100:.0f}%")

        # Per taal
        for taal in self.data.get("woorden", {}):
            print(f"\n  {taal.upper()}:")
            woord_stats = self.data["woorden"][taal]

            totaal = len(woord_stats)
            geleerd = sum(1 for s in woord_stats.values() if s["level"] >= 3)
            print(f"    Woorden: {totaal}")
            print(f"    Geleerd (level 3+): {geleerd}")

            if totaal > 0:
                print(f"    Voortgang: {geleerd/totaal*100:.0f}%")

        input("\n  Druk op Enter...")

    def run(self):
        """Start de app."""
        while True:
            clear_scherm()

            taal = self.data.get("actieve_taal")
            taal_str = self.TALEN[taal]["naam"] if taal else "Geen taal geselecteerd"

            due_count = len(self._get_due_woorden(taal)) if taal else 0

            print(f"""
  ╔═══════════════════════════════════════════════════════════╗
  ║              LANGUAGE TUTOR v1.0                          ║
  ║           Woordenschat & Spaced Repetition                ║
  ╠═══════════════════════════════════════════════════════════╣
  ║  1. Oefensessie (Spaced Repetition)                       ║
  ║  2. Snelle Quiz                                           ║
  ║  3. Bekijk Woordenschat                                   ║
  ║  4. Voeg Woord Toe                                        ║
  ║  5. Kies Taal                                             ║
  ║  6. Statistieken                                          ║
  ║  0. Terug                                                 ║
  ╚═══════════════════════════════════════════════════════════╝
""")
            print(f"  Actieve taal: {taal_str}")
            if due_count > 0:
                print(f"  Te reviewen: {due_count} woorden")
            print(f"  Streak: {self.data.get('streak', 0)} dagen")

            keuze = input("\n  Keuze: ").strip()

            if keuze == "0":
                break
            elif keuze == "1":
                self._oefen_sessie()
            elif keuze == "2":
                self._snel_quiz()
            elif keuze == "3":
                self._bekijk_woordenschat()
            elif keuze == "4":
                self._voeg_woord_toe()
            elif keuze == "5":
                self._kies_taal()
            elif keuze == "6":
                self._toon_statistieken()

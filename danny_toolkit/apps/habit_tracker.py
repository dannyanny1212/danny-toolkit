"""
Habit Tracker v2.0 - AI-Powered gewoonte tracker.
"""

import logging
from datetime import datetime, timedelta
from ..core.utils import clear_scherm
from .base_app import BaseApp

logger = logging.getLogger(__name__)


class HabitTrackerApp(BaseApp):
    """AI-Powered habit tracker voor betere gewoontes."""

    def __init__(self):
        super().__init__("habits.json")

    def _get_default_data(self) -> dict:
        """Standaard data voor habits."""
        return {
            "habits": [],
            "history": {},
            "streaks": {}
        }

    def _log_memory_event(self, event_type, data):
        """Log event naar Unified Memory."""
        try:
            if not hasattr(self, "_memory"):
                from ..brain.unified_memory import UnifiedMemory
                self._memory = UnifiedMemory()
            self._memory.store_event(
                app="habit_tracker",
                event_type=event_type,
                data=data
            )
        except Exception as e:
            logger.debug("Memory event error: %s", e)

    def run(self):
        """Start de habit tracker."""
        while True:
            clear_scherm()
            print("+" + "=" * 50 + "+")
            print("|          HABIT TRACKER v2.0                       |")
            if self.client:
                print("|          [AI POWERED]                            |")
            print("+" + "=" * 50 + "+")
            self._toon_vandaag_status()
            print("+" + "-" * 50 + "+")
            print("|  1. Habit voltooien                               |")
            print("|  2. Nieuwe habit toevoegen                        |")
            print("|  3. Habits bekijken                               |")
            print("|  4. Statistieken                                  |")
            print("|  5. Habit verwijderen                             |")
            print("+" + "-" * 50 + "+")
            print("|  [AI FUNCTIES]                                    |")
            print("|  6. AI Motivatie                                  |")
            print("|  7. AI Habit Suggesties                           |")
            print("|  8. AI Streak Analyse                             |")
            print("|  9. AI Habit Coach                                |")
            print("+" + "-" * 50 + "+")
            print("|  0. Terug                                         |")
            print("+" + "=" * 50 + "+")

            keuze = input("\nKeuze: ").strip()

            if keuze == "0":
                break
            elif keuze == "1":
                self._voltooien_habit()
            elif keuze == "2":
                self._nieuwe_habit()
            elif keuze == "3":
                self._bekijk_habits()
            elif keuze == "4":
                self._statistieken()
            elif keuze == "5":
                self._verwijder_habit()
            elif keuze == "6":
                self._ai_motivatie()
            elif keuze == "7":
                self._ai_habit_suggesties()
            elif keuze == "8":
                self._ai_streak_analyse()
            elif keuze == "9":
                self._ai_habit_coach()

            input("\nDruk op Enter...")

    def _toon_vandaag_status(self):
        """Toon status voor vandaag."""
        vandaag = datetime.now().date().isoformat()
        voltooid = self.data["history"].get(vandaag, [])
        totaal = len(self.data["habits"])
        done = len(voltooid)

        if totaal > 0:
            percentage = int((done / totaal) * 100)
            bar = "█" * (percentage // 10) + "░" * (10 - percentage // 10)
            print(f"|  Vandaag: [{bar}] {done}/{totaal} ({percentage}%){' ' * 10}|")
        else:
            print("|  Geen habits - voeg er een toe!                   |")

    def _nieuwe_habit(self):
        """Voeg een nieuwe habit toe."""
        print("\n--- NIEUWE HABIT ---")

        naam = input("Habit naam: ").strip()
        if not naam:
            print("[!] Naam is verplicht!")
            return

        if any(h["naam"].lower() == naam.lower() for h in self.data["habits"]):
            print("[!] Deze habit bestaat al!")
            return

        print("\nFrequentie:")
        print("  1. Dagelijks")
        print("  2. Weekdagen")
        print("  3. Weekends")
        print("  4. Wekelijks")

        freq_keuze = input("Keuze (1-4): ").strip()
        frequenties = {
            "1": "dagelijks",
            "2": "weekdagen",
            "3": "weekends",
            "4": "wekelijks"
        }
        frequentie = frequenties.get(freq_keuze, "dagelijks")

        beschrijving = input("Beschrijving (optioneel): ").strip()

        habit = {
            "id": len(self.data["habits"]) + 1,
            "naam": naam,
            "frequentie": frequentie,
            "beschrijving": beschrijving,
            "aangemaakt": datetime.now().isoformat()
        }

        self.data["habits"].append(habit)
        self.data["streaks"][str(habit["id"])] = 0
        self._sla_op()
        self._log_memory_event("habit_created", {
            "naam": naam
        })

        print(f"\n[OK] Habit '{naam}' toegevoegd!")

    def _voltooien_habit(self):
        """Markeer een habit als voltooid voor vandaag."""
        if not self.data["habits"]:
            print("\n[!] Geen habits om te voltooien!")
            return

        vandaag = datetime.now().date().isoformat()
        voltooid = self.data["history"].get(vandaag, [])

        print("\n--- HABIT VOLTOOIEN ---")
        print("\nJouw habits:")

        for h in self.data["habits"]:
            status = "✓" if h["id"] in voltooid else "○"
            streak = self.data["streaks"].get(str(h["id"]), 0)
            print(f"  {h['id']}. [{status}] {h['naam']} (streak: {streak})")

        try:
            keuze = int(input("\nHabit ID: ").strip())
            habit = next((h for h in self.data["habits"] if h["id"] == keuze), None)

            if not habit:
                print("[!] Ongeldige ID!")
                return

            if habit["id"] in voltooid:
                print(f"[!] '{habit['naam']}' is al voltooid vandaag!")
                return

            # Voeg toe aan history
            if vandaag not in self.data["history"]:
                self.data["history"][vandaag] = []
            self.data["history"][vandaag].append(habit["id"])

            # Update streak
            gisteren = (datetime.now().date() - timedelta(days=1)).isoformat()
            gisteren_voltooid = self.data["history"].get(gisteren, [])

            if habit["id"] in gisteren_voltooid:
                self.data["streaks"][str(habit["id"])] += 1
            else:
                self.data["streaks"][str(habit["id"])] = 1

            self._sla_op()
            self._log_memory_event("habit_completed", {
                "naam": habit["naam"],
                "streak": self.data["streaks"][str(habit["id"])]
            })

            streak = self.data["streaks"][str(habit["id"])]
            print(f"\n[OK] '{habit['naam']}' voltooid!")
            print(f"     Streak: {streak} dag{'en' if streak != 1 else ''}!")

            if streak == 7:
                print("     🎉 Geweldig! Een week streak!")
            elif streak == 30:
                print("     🏆 Fantastisch! Een maand streak!")
            elif streak == 100:
                print("     👑 Legendarisch! 100 dagen streak!")

        except ValueError:
            print("[!] Voer een geldig nummer in!")

    def _bekijk_habits(self):
        """Bekijk alle habits."""
        print("\n--- ALLE HABITS ---")

        if not self.data["habits"]:
            print("Geen habits gevonden.")
            return

        for h in self.data["habits"]:
            streak = self.data["streaks"].get(str(h["id"]), 0)
            print(f"\n  {h['id']}. {h['naam']}")
            print(f"     Frequentie: {h['frequentie']}")
            print(f"     Streak: {streak} dagen")
            if h.get("beschrijving"):
                print(f"     Info: {h['beschrijving']}")

    def _statistieken(self):
        """Toon habit statistieken."""
        print("\n--- STATISTIEKEN ---")

        if not self.data["habits"]:
            print("Geen habits om te analyseren.")
            return

        # Totale voltooiingen
        totaal_voltooiingen = sum(
            len(v) for v in self.data["history"].values()
        )

        # Beste streak
        beste_streak = max(self.data["streaks"].values()) if self.data["streaks"] else 0

        # Actieve dagen
        actieve_dagen = len(self.data["history"])

        print(f"\n  Totaal habits: {len(self.data['habits'])}")
        print(f"  Totaal voltooiingen: {totaal_voltooiingen}")
        print(f"  Actieve dagen: {actieve_dagen}")
        print(f"  Beste streak: {beste_streak} dagen")

        # Per habit stats
        print("\n  Per habit:")
        for h in self.data["habits"]:
            count = sum(
                1 for v in self.data["history"].values()
                if h["id"] in v
            )
            streak = self.data["streaks"].get(str(h["id"]), 0)
            print(f"    - {h['naam']}: {count}x voltooid, streak: {streak}")

    def _verwijder_habit(self):
        """Verwijder een habit."""
        self._bekijk_habits()

        if not self.data["habits"]:
            return

        try:
            keuze = int(input("\nHabit ID om te verwijderen: ").strip())
            habit = next((h for h in self.data["habits"] if h["id"] == keuze), None)

            if not habit:
                print("[!] Ongeldige ID!")
                return

            bevestig = input(f"'{habit['naam']}' verwijderen? (j/n): ").strip().lower()
            if bevestig == "j":
                self.data["habits"].remove(habit)
                if str(habit["id"]) in self.data["streaks"]:
                    del self.data["streaks"][str(habit["id"])]
                self._sla_op()
                print("[OK] Habit verwijderd!")

        except ValueError:
            print("[!] Voer een geldig nummer in!")

    # ==================== AI FUNCTIES ====================

    def _get_habits_context(self) -> str:
        """Verzamel habit data voor AI context."""
        if not self.data["habits"]:
            return "Geen habits geconfigureerd."

        context = "Huidige habits:\n"
        for h in self.data["habits"]:
            streak = self.data["streaks"].get(str(h["id"]), 0)
            context += f"- {h['naam']} ({h['frequentie']}, streak: {streak})\n"

        vandaag = datetime.now().date()
        context += "\nVoortgang laatste 7 dagen:\n"
        for i in range(7):
            dag = vandaag - timedelta(days=i)
            voltooid = self.data["history"].get(dag.isoformat(), [])
            namen = [h["naam"] for h in self.data["habits"] if h["id"] in voltooid]
            context += f"- {dag.strftime('%a')}: {', '.join(namen) if namen else 'Geen'}\n"

        return context

    def _ai_motivatie(self):
        """AI geeft gepersonaliseerde motivatie."""
        print("\n--- AI MOTIVATIE ---")

        if not self.data["habits"]:
            print("[!] Voeg eerst habits toe!")
            return

        vandaag = datetime.now().date().isoformat()
        voltooid = self.data["history"].get(vandaag, [])
        open_habits = [h for h in self.data["habits"] if h["id"] not in voltooid]

        if not self.client:
            if not open_habits:
                print("\n🎉 Geweldig! Alle habits van vandaag voltooid!")
            else:
                print(f"\n💪 Nog {len(open_habits)} habit(s) te gaan. Je kunt dit!")
            return

        print("\n[AI genereert motivatie...]")
        context = self._get_habits_context()

        prompt = f"""Geef korte, krachtige motivatie voor iemand met habits.

{context}
Open vandaag: {[h['naam'] for h in open_habits]}

Geef 2-3 energieke zinnen. Wees specifiek. Nederlands."""

        response = self._ai_request(prompt, max_tokens=200)
        if response:
            print(f"\n💪 {response}")

    def _ai_habit_suggesties(self):
        """AI suggereert nieuwe habits."""
        print("\n--- AI HABIT SUGGESTIES ---")
        print("\n  1. Gezondheid    2. Productiviteit")
        print("  3. Mindfulness   4. Leren")

        keuze = input("\nCategorie (1-4): ").strip()
        cats = {"1": "gezondheid", "2": "productiviteit", "3": "mindfulness", "4": "leren"}
        cat = cats.get(keuze, "algemeen")

        if not self.client:
            tips = {"1": ["10 min wandelen", "8 glazen water"],
                    "2": ["To-do lijst", "2 uur focus"],
                    "3": ["5 min meditatie", "Dankbaarheid schrijven"],
                    "4": ["20 pagina's lezen", "Nieuwe skill oefenen"]}
            print(f"\n[Suggesties]:")
            for t in tips.get(keuze, ["Begin klein", "Wees consistent"]):
                print(f"  • {t}")
            return

        prompt = f"""Suggereer 4 {cat} habits. Kort en praktisch. Nederlands."""
        response = self._ai_request(prompt, max_tokens=300)
        if response:
            print(f"\n[AI Suggesties]:\n{response}")

    def _ai_streak_analyse(self):
        """AI analyseert streak patronen."""
        print("\n--- AI STREAK ANALYSE ---")

        if not self.data["habits"]:
            print("[!] Geen habits.")
            return

        if not self.client:
            beste = max(self.data["streaks"].values()) if self.data["streaks"] else 0
            print(f"\n  Beste streak: {beste} dagen")
            return

        context = self._get_habits_context()
        prompt = f"""Analyseer habit streaks kort. {context}

Geef: sterke punten, verbeterpunten, 2 tips. Nederlands."""

        response = self._ai_request(prompt, max_tokens=400)
        if response:
            print(f"\n[Analyse]:\n{response}")

    def _ai_habit_coach(self):
        """AI habit coach voor vragen."""
        print("\n--- AI HABIT COACH ---")

        vraag = input("\nStel je vraag: ").strip()
        if not vraag:
            return

        if not self.client:
            print("\n[Tips]: Begin klein, koppel aan routines, track voortgang.")
            return

        context = self._get_habits_context()
        prompt = f"""Je bent een habit coach. Vraag: "{vraag}"

Context: {context}

Geef praktisch, warm antwoord. Nederlands."""

        response = self._ai_request(prompt, max_tokens=400)
        if response:
            print(f"\n[Coach]:\n{response}")

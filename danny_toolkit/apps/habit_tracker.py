"""
Habit Tracker - Volg je dagelijkse gewoontes.
"""

import json
from datetime import datetime, timedelta
from ..core.config import Config
from ..core.utils import clear_scherm


class HabitTrackerApp:
    """Track en bouw goede gewoontes."""

    def __init__(self):
        Config.ensure_dirs()
        self.bestand = Config.APPS_DATA_DIR / "habits.json"
        self.data = self._laad_data()

    def _laad_data(self) -> dict:
        """Laad habits data."""
        if self.bestand.exists():
            try:
                with open(self.bestand, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {
            "habits": [],
            "history": {},
            "streaks": {}
        }

    def _sla_op(self):
        """Sla data op."""
        with open(self.bestand, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    def run(self):
        """Start de habit tracker."""
        while True:
            clear_scherm()
            print("+" + "=" * 50 + "+")
            print("|          HABIT TRACKER                            |")
            print("+" + "=" * 50 + "+")
            self._toon_vandaag_status()
            print("+" + "-" * 50 + "+")
            print("|  1. Habit voltooien                               |")
            print("|  2. Nieuwe habit toevoegen                        |")
            print("|  3. Habits bekijken                               |")
            print("|  4. Statistieken                                  |")
            print("|  5. Habit verwijderen                             |")
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

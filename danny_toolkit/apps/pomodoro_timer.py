"""
Pomodoro Timer - Focus timer voor productiviteit.
"""

import time
import json
from datetime import datetime, timedelta
from ..core.config import Config
from ..core.utils import clear_scherm


class PomodoroTimerApp:
    """Pomodoro techniek timer."""

    def __init__(self):
        Config.ensure_dirs()
        self.bestand = Config.APPS_DATA_DIR / "pomodoro_stats.json"
        self.stats = self._laad_stats()

    def _laad_stats(self) -> dict:
        """Laad pomodoro statistieken."""
        if self.bestand.exists():
            try:
                with open(self.bestand, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {
            "totaal_pomodoros": 0,
            "totaal_minuten": 0,
            "vandaag": {"datum": "", "pomodoros": 0},
            "streak": 0,
            "sessies": []
        }

    def _sla_op(self):
        """Sla stats op."""
        with open(self.bestand, "w", encoding="utf-8") as f:
            json.dump(self.stats, f, indent=2)

    def run(self):
        """Start de pomodoro timer."""
        while True:
            clear_scherm()
            print("+" + "=" * 50 + "+")
            print("|          POMODORO TIMER                          |")
            print("+" + "=" * 50 + "+")
            print(f"|  Totaal pomodoros: {self.stats['totaal_pomodoros']:<29}|")
            print(f"|  Totaal focus tijd: {self.stats['totaal_minuten']} minuten{' ' * (21 - len(str(self.stats['totaal_minuten'])))}|")
            print("+" + "-" * 50 + "+")
            print("|  1. Start Pomodoro (25 min werk)                 |")
            print("|  2. Korte pauze (5 min)                          |")
            print("|  3. Lange pauze (15 min)                         |")
            print("|  4. Aangepaste timer                             |")
            print("|  5. Statistieken                                 |")
            print("|  0. Terug                                        |")
            print("+" + "=" * 50 + "+")

            keuze = input("\nKeuze: ").strip()

            if keuze == "0":
                break
            elif keuze == "1":
                self._start_timer(25, "Pomodoro")
            elif keuze == "2":
                self._start_timer(5, "Korte pauze")
            elif keuze == "3":
                self._start_timer(15, "Lange pauze")
            elif keuze == "4":
                self._aangepaste_timer()
            elif keuze == "5":
                self._toon_statistieken()
                input("\nDruk op Enter...")

    def _start_timer(self, minuten: int, type_timer: str):
        """Start een timer."""
        clear_scherm()
        print(f"\n{'=' * 50}")
        print(f"  {type_timer.upper()} - {minuten} MINUTEN")
        print(f"{'=' * 50}")

        taak = ""
        if type_timer == "Pomodoro":
            taak = input("\nWaar ga je aan werken? ").strip()
            if taak:
                print(f"\nFocus op: {taak}")

        print("\nTimer gestart! Druk Ctrl+C om te stoppen.")
        print(f"\nResterend: {minuten}:00")

        start_tijd = datetime.now()
        eind_tijd = start_tijd + timedelta(minutes=minuten)

        try:
            while datetime.now() < eind_tijd:
                rest = eind_tijd - datetime.now()
                rest_sec = int(rest.total_seconds())
                mins = rest_sec // 60
                secs = rest_sec % 60

                # Toon elke 30 seconden een update
                print(f"\r  [{mins:02d}:{secs:02d}] ", end="", flush=True)
                time.sleep(1)

            # Timer voltooid
            print(f"\n\n{'=' * 50}")
            print(f"  {type_timer.upper()} VOLTOOID!")
            print(f"{'=' * 50}")

            # Update stats voor pomodoro
            if type_timer == "Pomodoro":
                self.stats["totaal_pomodoros"] += 1
                self.stats["totaal_minuten"] += minuten

                vandaag = datetime.now().date().isoformat()
                if self.stats["vandaag"]["datum"] != vandaag:
                    self.stats["vandaag"] = {"datum": vandaag, "pomodoros": 0}
                self.stats["vandaag"]["pomodoros"] += 1

                self.stats["sessies"].append({
                    "datum": datetime.now().isoformat(),
                    "type": type_timer,
                    "minuten": minuten,
                    "taak": taak
                })

                # Houd max 100 sessies
                self.stats["sessies"] = self.stats["sessies"][-100:]
                self._sla_op()

                print(f"\n  Pomodoro #{self.stats['totaal_pomodoros']} voltooid!")
                print(f"  Vandaag: {self.stats['vandaag']['pomodoros']} pomodoros")

        except KeyboardInterrupt:
            print("\n\n  Timer gestopt.")

        input("\nDruk op Enter...")

    def _aangepaste_timer(self):
        """Start een aangepaste timer."""
        try:
            minuten = int(input("\nAantal minuten: ").strip())
            minuten = max(1, min(120, minuten))
            self._start_timer(minuten, "Aangepast")
        except ValueError:
            print("[!] Ongeldig aantal minuten!")
            input("\nDruk op Enter...")

    def _toon_statistieken(self):
        """Toon pomodoro statistieken."""
        clear_scherm()
        print("\n" + "=" * 50)
        print("  POMODORO STATISTIEKEN")
        print("=" * 50)

        print(f"\n  Totaal pomodoros: {self.stats['totaal_pomodoros']}")
        print(f"  Totaal focus tijd: {self.stats['totaal_minuten']} minuten")
        print(f"  Dat is {self.stats['totaal_minuten'] // 60} uur en {self.stats['totaal_minuten'] % 60} minuten!")

        if self.stats["vandaag"]["datum"] == datetime.now().date().isoformat():
            print(f"\n  Vandaag: {self.stats['vandaag']['pomodoros']} pomodoros")

        if self.stats["sessies"]:
            print("\n  Recente sessies:")
            for s in self.stats["sessies"][-5:]:
                datum = s["datum"][:10]
                taak = s.get("taak", "")[:20]
                print(f"    - {datum}: {s['minuten']}min {taak}")

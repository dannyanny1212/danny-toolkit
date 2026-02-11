"""
Pomodoro Timer v2.0 - AI-Powered focus timer.
"""

import time
from datetime import datetime, timedelta
from ..core.utils import clear_scherm
from .base_app import BaseApp


class PomodoroTimerApp(BaseApp):
    """AI-Powered Pomodoro techniek timer."""

    def __init__(self):
        super().__init__("pomodoro_stats.json")
        self.stats = self.data

    def _get_default_data(self) -> dict:
        return {
            "totaal_pomodoros": 0,
            "totaal_minuten": 0,
            "vandaag": {"datum": "", "pomodoros": 0},
            "streak": 0,
            "sessies": []
        }

    def _log_memory_event(self, event_type, data):
        """Log event naar Unified Memory."""
        try:
            if not hasattr(self, "_memory"):
                from ..brain.unified_memory import UnifiedMemory
                self._memory = UnifiedMemory()
            self._memory.store_event(
                app="pomodoro_timer",
                event_type=event_type,
                data=data
            )
        except Exception:
            pass  # Memory is optioneel

    def run(self):
        """Start de pomodoro timer."""
        while True:
            clear_scherm()
            print("+" + "=" * 50 + "+")
            print("|          POMODORO TIMER v2.0                     |")
            if self.client:
                print("|          [AI POWERED]                            |")
            print("+" + "=" * 50 + "+")
            print(f"|  Totaal pomodoros: {self.stats['totaal_pomodoros']:<29}|")
            print(f"|  Totaal focus tijd: {self.stats['totaal_minuten']} minuten{' ' * (21 - len(str(self.stats['totaal_minuten'])))}|")
            print("+" + "-" * 50 + "+")
            print("|  1. Start Pomodoro (25 min werk)                 |")
            print("|  2. Korte pauze (5 min)                          |")
            print("|  3. Lange pauze (15 min)                         |")
            print("|  4. Aangepaste timer                             |")
            print("|  5. Statistieken                                 |")
            print("+" + "-" * 50 + "+")
            print("|  [AI FUNCTIES]                                   |")
            print("|  6. AI Focus Tips                                |")
            print("|  7. AI Motivatie                                 |")
            print("|  8. AI Productiviteit Analyse                    |")
            print("+" + "-" * 50 + "+")
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
            elif keuze == "6":
                self._ai_focus_tips()
                input("\nDruk op Enter...")
            elif keuze == "7":
                self._ai_motivatie()
                input("\nDruk op Enter...")
            elif keuze == "8":
                self._ai_productiviteit_analyse()
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
                self._log_memory_event(
                    "pomodoro_completed",
                    {"duur_min": minuten}
                )

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

    # ==================== AI FUNCTIES ====================

    def _ai_focus_tips(self):
        """AI geeft focus tips."""
        print("\n--- AI FOCUS TIPS ---")

        if not self.client:
            print("\n[Focus Tips]:")
            print("  • Schakel notificaties uit")
            print("  • Werk in een opgeruimde ruimte")
            print("  • Drink genoeg water")
            print("  • Neem korte pauzes")
            print("  • Gebruik noise-cancelling")
            return

        print("\n[AI genereert tips...]")
        prompt = f"""Geef 5 wetenschappelijk onderbouwde focus tips.

Gebruiker statistieken:
- Totaal pomodoros: {self.stats['totaal_pomodoros']}
- Focus minuten: {self.stats['totaal_minuten']}

Geef praktische, direct toepasbare tips voor betere concentratie.
Varieer tussen mindset en praktische tips. Nederlands."""

        response = self._ai_request(prompt, max_tokens=400)
        if response:
            print(f"\n[AI Focus Tips]:\n{response}")

    def _ai_motivatie(self):
        """AI geeft motivatie boost."""
        print("\n--- AI MOTIVATIE ---")

        if not self.client:
            print("\n💪 Je bent bezig met focus bouwen!")
            print(f"   Al {self.stats['totaal_pomodoros']} pomodoros voltooid.")
            print("   Elke sessie maakt je productiever!")
            return

        print("\n[AI genereert motivatie...]")
        prompt = f"""Geef een korte, krachtige motivatie boodschap.

Gebruiker heeft {self.stats['totaal_pomodoros']} pomodoros voltooid.
Dat is {self.stats['totaal_minuten']} minuten focus tijd!

Geef een persoonlijke, energieke motivatie in 2-3 zinnen.
Vier hun voortgang. Nederlands."""

        response = self._ai_request(prompt, max_tokens=150)
        if response:
            print(f"\n🔥 {response}")

    def _ai_productiviteit_analyse(self):
        """AI analyseert productiviteit patronen."""
        print("\n--- AI PRODUCTIVITEIT ANALYSE ---")

        if not self.stats["sessies"]:
            print("[!] Geen sessie data voor analyse.")
            return

        if not self.client:
            print(f"\n[Analyse]:")
            print(f"  Totaal sessies: {len(self.stats['sessies'])}")
            avg = self.stats['totaal_minuten'] / max(self.stats['totaal_pomodoros'], 1)
            print(f"  Gemiddelde sessie: {avg:.0f} minuten")
            return

        # Verzamel context
        sessies_info = "\n".join([
            f"- {s['datum'][:10]}: {s['minuten']}min - {s.get('taak', 'Geen taak')}"
            for s in self.stats["sessies"][-20:]
        ])

        print("\n[AI analyseert...]")
        prompt = f"""Analyseer deze productiviteit data:

Totaal pomodoros: {self.stats['totaal_pomodoros']}
Totaal minuten: {self.stats['totaal_minuten']}

Recente sessies:
{sessies_info}

Geef:
1. Productiviteit patroon observaties
2. Beste tijden/dagen (indien zichtbaar)
3. Tips voor verbetering
4. Moedig aan om door te gaan

Kort en praktisch. Nederlands."""

        response = self._ai_request(prompt, max_tokens=400)
        if response:
            print(f"\n[AI Analyse]:\n{response}")

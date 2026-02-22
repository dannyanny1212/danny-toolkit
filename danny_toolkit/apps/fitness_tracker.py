"""
Fitness Tracker v1.0 - Workouts, sets/reps, voortgang, calorieën.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict
from ..core.config import Config
from ..core.utils import clear_scherm

logger = logging.getLogger(__name__)

try:
    from ..core.neural_bus import get_bus, EventTypes
    HAS_BUS = True
except ImportError:
    HAS_BUS = False


class FitnessTrackerApp:
    """Fitness Tracker - Track je workouts en voortgang."""

    VERSIE = "1.0"

    # Basis oefeningen per categorie
    OEFENINGEN = {
        "borst": ["Bench Press", "Push-ups", "Chest Fly", "Incline Press"],
        "rug": ["Pull-ups", "Rows", "Lat Pulldown", "Deadlift"],
        "schouders": ["Shoulder Press", "Lateral Raise", "Front Raise"],
        "armen": ["Bicep Curl", "Tricep Dips", "Hammer Curl", "Tricep Extension"],
        "benen": ["Squats", "Lunges", "Leg Press", "Calf Raise"],
        "core": ["Plank", "Crunches", "Russian Twist", "Leg Raise"],
        "cardio": ["Hardlopen", "Fietsen", "Roeien", "Touwtje springen"],
    }

    # Calorie verbranding per minuut (geschat)
    CALORIEEN_PER_MIN = {
        "licht": 4,      # Wandelen, stretching
        "matig": 7,      # Gewichten, yoga
        "intensief": 10, # HIIT, hardlopen
        "zeer_intensief": 14,  # Sprint, heavy lifting
    }

    def __init__(self):
        Config.ensure_dirs()
        self.data_dir = Config.APPS_DATA_DIR / "fitness_tracker"
        self.data_dir.mkdir(exist_ok=True)
        self.data_file = self.data_dir / "data.json"
        self.data = self._laad_data()

    def _laad_data(self) -> Dict:
        """Laad fitness data."""
        if self.data_file.exists():
            try:
                with open(self.data_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {
            "profiel": {},
            "workouts": [],
            "personal_records": {},
            "streak": 0,
            "laatste_workout": None,
        }

    def _sla_op(self):
        """Sla data op."""
        with open(self.data_file, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    def _log_memory_event(self, event_type, data):
        """Log event naar Unified Memory."""
        try:
            if not hasattr(self, "_memory"):
                from ..brain.unified_memory import UnifiedMemory
                self._memory = UnifiedMemory()
            self._memory.store_event(
                app="fitness_tracker",
                event_type=event_type,
                data=data
            )
        except Exception as e:
            logger.debug("Memory event error: %s", e)

    def _check_streak(self):
        """Check en update workout streak."""
        if self.data.get("laatste_workout"):
            laatste = datetime.fromisoformat(self.data["laatste_workout"])
            verschil = (datetime.now() - laatste).days

            if verschil > 1:
                self.data["streak"] = 0

    def _setup_profiel(self):
        """Setup gebruikersprofiel."""
        clear_scherm()
        print("\n  === PROFIEL INSTELLEN ===\n")

        profiel = self.data.get("profiel", {})

        naam = input(f"  Naam [{profiel.get('naam', '')}]: ").strip()
        if naam:
            profiel["naam"] = naam

        try:
            gewicht = input(f"  Gewicht in kg [{profiel.get('gewicht', '')}]: ").strip()
            if gewicht:
                profiel["gewicht"] = float(gewicht)
        except ValueError:
            pass

        try:
            lengte = input(f"  Lengte in cm [{profiel.get('lengte', '')}]: ").strip()
            if lengte:
                profiel["lengte"] = float(lengte)
        except ValueError:
            pass

        doel = input(f"  Doel (afvallen/opbouwen/fit) [{profiel.get('doel', 'fit')}]: ").strip()
        if doel:
            profiel["doel"] = doel

        self.data["profiel"] = profiel
        self._sla_op()
        print("\n  Profiel opgeslagen!")
        input("  Druk op Enter...")

    def _start_workout(self):
        """Start een nieuwe workout."""
        clear_scherm()
        print("\n  === NIEUWE WORKOUT ===\n")

        # Kies type
        print("  Workout types:")
        print("  1. Krachttraining")
        print("  2. Cardio")
        print("  3. Mix (kracht + cardio)")

        type_keuze = input("\n  Keuze: ").strip()
        workout_type = {"1": "kracht", "2": "cardio", "3": "mix"}.get(type_keuze, "mix")

        workout = {
            "datum": datetime.now().isoformat(),
            "type": workout_type,
            "oefeningen": [],
            "duur_min": 0,
            "calorieen": 0,
            "notities": "",
        }

        # Voeg oefeningen toe
        print("\n  Voeg oefeningen toe (leeg = klaar)")

        while True:
            print("\n  Categorieën:", ", ".join(self.OEFENINGEN.keys()))
            cat = input("  Categorie (of 'klaar'): ").strip().lower()

            if cat == "klaar" or cat == "":
                break

            if cat in self.OEFENINGEN:
                print(f"  Oefeningen: {', '.join(self.OEFENINGEN[cat])}")
                oefening = input("  Oefening: ").strip()

                if workout_type == "cardio" or cat == "cardio":
                    # Cardio: tijd en intensiteit
                    try:
                        duur = int(input("  Duur (minuten): ").strip() or "10")
                    except ValueError:
                        duur = 10

                    print("  Intensiteit: licht, matig, intensief, zeer_intensief")
                    intensiteit = input("  Intensiteit: ").strip().lower() or "matig"

                    cal = duur * self.CALORIEEN_PER_MIN.get(intensiteit, 7)

                    workout["oefeningen"].append({
                        "naam": oefening,
                        "type": "cardio",
                        "duur_min": duur,
                        "intensiteit": intensiteit,
                        "calorieen": cal,
                    })
                    workout["duur_min"] += duur
                    workout["calorieen"] += cal

                else:
                    # Kracht: sets en reps
                    sets = []
                    print("  Voer sets in (leeg = klaar):")

                    set_nr = 1
                    while True:
                        set_input = input(f"    Set {set_nr} (reps x gewicht, bijv. 10x50): ").strip()
                        if not set_input:
                            break

                        try:
                            if "x" in set_input.lower():
                                reps, gewicht = set_input.lower().split("x")
                                sets.append({
                                    "reps": int(reps),
                                    "gewicht": float(gewicht)
                                })
                            else:
                                sets.append({"reps": int(set_input), "gewicht": 0})
                            set_nr += 1
                        except ValueError:
                            print("      Ongeldige invoer, probeer opnieuw")

                    if sets:
                        # Schat calorieen voor krachttraining
                        cal = len(sets) * 5  # ~5 cal per set
                        duur = len(sets) * 2  # ~2 min per set

                        workout["oefeningen"].append({
                            "naam": oefening,
                            "type": "kracht",
                            "sets": sets,
                            "calorieen": cal,
                        })
                        workout["duur_min"] += duur
                        workout["calorieen"] += cal

                        # Check personal record
                        if sets:
                            max_gewicht = max(s.get("gewicht", 0) for s in sets)
                            pr_key = oefening.lower()
                            huidige_pr = self.data["personal_records"].get(pr_key, 0)

                            if max_gewicht > huidige_pr:
                                self.data["personal_records"][pr_key] = max_gewicht
                                print(f"    NIEUW PERSONAL RECORD: {max_gewicht} kg!")

        # Notities
        workout["notities"] = input("\n  Notities (optioneel): ").strip()

        # Opslaan
        self.data["workouts"].append(workout)
        self.data["laatste_workout"] = workout["datum"]
        self.data["streak"] += 1
        self._sla_op()
        self._log_memory_event("workout_logged", {
            "oefening": ", ".join(
                o["naam"] for o in workout["oefeningen"]
            )[:80],
            "duur": workout["duur_min"]
        })

        # Publiceer naar NeuralBus
        if HAS_BUS:
            get_bus().publish(
                EventTypes.HEALTH_STATUS_CHANGE,
                {
                    "type": workout_type,
                    "duur_min": workout["duur_min"],
                    "calorieen": workout["calorieen"],
                    "oefeningen": len(workout["oefeningen"]),
                    "streak": self.data["streak"],
                    "doel": self.data.get("profiel", {}).get("doel", "fit"),
                },
                bron="fitness_tracker",
            )

        # Samenvatting
        print("\n  " + "=" * 40)
        print("  WORKOUT VOLTOOID!")
        print("  " + "=" * 40)
        print(f"  Oefeningen: {len(workout['oefeningen'])}")
        print(f"  Duur: {workout['duur_min']} minuten")
        print(f"  Calorieën: ~{workout['calorieen']} kcal")
        print(f"  Streak: {self.data['streak']} dagen!")

        input("\n  Druk op Enter...")

    def _bekijk_geschiedenis(self):
        """Bekijk workout geschiedenis."""
        clear_scherm()
        print("\n  === WORKOUT GESCHIEDENIS ===\n")

        workouts = self.data.get("workouts", [])

        if not workouts:
            print("  Nog geen workouts gelogd.")
            input("\n  Druk op Enter...")
            return

        # Toon laatste 10
        for i, w in enumerate(reversed(workouts[-10:]), 1):
            datum = w["datum"][:10]
            type_ = w["type"]
            oef_count = len(w["oefeningen"])
            cal = w.get("calorieen", 0)
            print(f"  {i}. {datum} | {type_:8} | {oef_count} oefeningen | {cal} kcal")

        keuze = input("\n  Bekijk details # (of Enter): ").strip()
        if keuze.isdigit():
            idx = len(workouts) - int(keuze)
            if 0 <= idx < len(workouts):
                self._toon_workout_details(workouts[idx])

    def _toon_workout_details(self, workout: Dict):
        """Toon details van een workout."""
        clear_scherm()
        print("\n  === WORKOUT DETAILS ===\n")
        print(f"  Datum: {workout['datum'][:10]}")
        print(f"  Type: {workout['type']}")
        print(f"  Duur: {workout.get('duur_min', 0)} min")
        print(f"  Calorieën: {workout.get('calorieen', 0)} kcal")

        print("\n  OEFENINGEN:")
        for oef in workout.get("oefeningen", []):
            print(f"\n    {oef['naam']}:")
            if oef["type"] == "cardio":
                print(f"      {oef['duur_min']} min, {oef['intensiteit']}")
            else:
                for i, s in enumerate(oef.get("sets", []), 1):
                    print(f"      Set {i}: {s['reps']} x {s['gewicht']}kg")

        if workout.get("notities"):
            print(f"\n  Notities: {workout['notities']}")

        input("\n  Druk op Enter...")

    def _toon_statistieken(self):
        """Toon fitness statistieken."""
        clear_scherm()
        print("\n  === FITNESS STATISTIEKEN ===\n")

        workouts = self.data.get("workouts", [])
        profiel = self.data.get("profiel", {})

        # Profiel info
        if profiel:
            print(f"  Naam: {profiel.get('naam', '-')}")
            print(f"  Gewicht: {profiel.get('gewicht', '-')} kg")
            print(f"  Doel: {profiel.get('doel', '-')}")
            print()

        # Algemene stats
        print(f"  Totaal workouts: {len(workouts)}")
        print(f"  Huidige streak: {self.data.get('streak', 0)} dagen")

        if workouts:
            totaal_cal = sum(w.get("calorieen", 0) for w in workouts)
            totaal_min = sum(w.get("duur_min", 0) for w in workouts)
            print(f"  Totaal calorieën: {totaal_cal} kcal")
            print(f"  Totaal tijd: {totaal_min} minuten ({totaal_min // 60} uur)")

            # Deze week
            week_geleden = datetime.now() - timedelta(days=7)
            week_workouts = [w for w in workouts
                           if datetime.fromisoformat(w["datum"]) > week_geleden]
            print(f"\n  Deze week: {len(week_workouts)} workouts")

        # Personal Records
        prs = self.data.get("personal_records", {})
        if prs:
            print("\n  PERSONAL RECORDS:")
            for oef, gewicht in sorted(prs.items()):
                print(f"    {oef}: {gewicht} kg")

        # Progress bar voor week goal (bijv. 4 workouts)
        week_goal = 4
        week_done = len(week_workouts) if workouts else 0
        progress = min(week_done / week_goal, 1.0)
        bar_len = 20
        filled = int(bar_len * progress)
        bar = "[" + "#" * filled + "-" * (bar_len - filled) + "]"
        print(f"\n  Week doel: {bar} {week_done}/{week_goal}")

        input("\n  Druk op Enter...")

    def _bekijk_oefeningen(self):
        """Bekijk oefeningen bibliotheek."""
        clear_scherm()
        print("\n  === OEFENINGEN BIBLIOTHEEK ===\n")

        for cat, oefeningen in self.OEFENINGEN.items():
            print(f"  {cat.upper()}:")
            for oef in oefeningen:
                pr = self.data["personal_records"].get(oef.lower())
                pr_str = f" (PR: {pr}kg)" if pr else ""
                print(f"    - {oef}{pr_str}")
            print()

        input("  Druk op Enter...")

    def run(self):
        """Start de app."""
        self._check_streak()

        while True:
            clear_scherm()

            streak = self.data.get("streak", 0)
            streak_emoji = "!" * min(streak, 5) if streak > 0 else ""

            print(f"""
  ╔═══════════════════════════════════════════════════════════╗
  ║              FITNESS TRACKER v1.0                         ║
  ║            Track je Workouts & Voortgang                  ║
  ╠═══════════════════════════════════════════════════════════╣
  ║  1. Start Workout                                         ║
  ║  2. Bekijk Geschiedenis                                   ║
  ║  3. Statistieken                                          ║
  ║  4. Oefeningen Bibliotheek                                ║
  ║  5. Profiel Instellen                                     ║
  ║  0. Terug                                                 ║
  ╚═══════════════════════════════════════════════════════════╝
""")
            print(f"  Streak: {streak} dagen {streak_emoji}")
            print(f"  Workouts: {len(self.data.get('workouts', []))}")

            keuze = input("\n  Keuze: ").strip()

            if keuze == "0":
                break
            elif keuze == "1":
                self._start_workout()
            elif keuze == "2":
                self._bekijk_geschiedenis()
            elif keuze == "3":
                self._toon_statistieken()
            elif keuze == "4":
                self._bekijk_oefeningen()
            elif keuze == "5":
                self._setup_profiel()

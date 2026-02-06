"""
Mood Tracker - Houd je stemming bij.
"""

import json
from datetime import datetime, timedelta
from collections import Counter
from ..core.config import Config
from ..core.utils import clear_scherm


class MoodTrackerApp:
    """Track je dagelijkse stemming en emoties."""

    def __init__(self):
        Config.ensure_dirs()
        self.bestand = Config.APPS_DATA_DIR / "mood.json"
        self.data = self._laad_data()

        self.stemmingen = {
            "1": ("Geweldig", "😄", 5),
            "2": ("Goed", "🙂", 4),
            "3": ("Oké", "😐", 3),
            "4": ("Niet zo goed", "😕", 2),
            "5": ("Slecht", "😢", 1)
        }

        self.activiteiten = [
            "Werk", "Sport", "Vrienden", "Familie", "Hobby",
            "Rust", "Natuur", "Lezen", "Gaming", "Muziek"
        ]

    def _laad_data(self) -> dict:
        """Laad mood data."""
        if self.bestand.exists():
            try:
                with open(self.bestand, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {
            "entries": [],
            "streak": 0
        }

    def _sla_op(self):
        """Sla data op."""
        with open(self.bestand, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    def run(self):
        """Start de mood tracker."""
        while True:
            clear_scherm()
            print("+" + "=" * 50 + "+")
            print("|          MOOD TRACKER                             |")
            print("+" + "=" * 50 + "+")
            self._toon_recente_mood()
            print("+" + "-" * 50 + "+")
            print("|  1. Mood loggen                                   |")
            print("|  2. Vandaag bekijken                              |")
            print("|  3. Week overzicht                                |")
            print("|  4. Statistieken                                  |")
            print("|  5. Mood patronen                                 |")
            print("|  0. Terug                                         |")
            print("+" + "=" * 50 + "+")

            keuze = input("\nKeuze: ").strip()

            if keuze == "0":
                break
            elif keuze == "1":
                self._log_mood()
            elif keuze == "2":
                self._bekijk_vandaag()
            elif keuze == "3":
                self._week_overzicht()
            elif keuze == "4":
                self._statistieken()
            elif keuze == "5":
                self._mood_patronen()

            input("\nDruk op Enter...")

    def _toon_recente_mood(self):
        """Toon meest recente mood."""
        vandaag = datetime.now().date().isoformat()
        vandaag_entries = [
            e for e in self.data["entries"]
            if e["datum"].startswith(vandaag)
        ]

        if vandaag_entries:
            laatste = vandaag_entries[-1]
            print(f"|  Vandaag: {laatste['stemming']} {laatste['emoji']:<37}|")
        else:
            print("|  Nog geen mood gelogd vandaag                     |")

    def _log_mood(self):
        """Log je huidige stemming."""
        print("\n--- MOOD LOGGEN ---")
        print("\nHoe voel je je nu?\n")

        for key, (naam, emoji, _) in self.stemmingen.items():
            print(f"  {key}. {emoji} {naam}")

        keuze = input("\nKeuze (1-5): ").strip()

        if keuze not in self.stemmingen:
            print("[!] Ongeldige keuze!")
            return

        naam, emoji, score = self.stemmingen[keuze]

        # Optionele activiteiten
        print("\nWat heb je gedaan? (kies nummers, gescheiden door komma)")
        for i, act in enumerate(self.activiteiten, 1):
            print(f"  {i}. {act}")

        act_input = input("\nActiviteiten (of Enter): ").strip()
        gekozen_act = []

        if act_input:
            try:
                indices = [int(x.strip()) - 1 for x in act_input.split(",")]
                gekozen_act = [
                    self.activiteiten[i] for i in indices
                    if 0 <= i < len(self.activiteiten)
                ]
            except ValueError:
                pass

        # Optionele notitie
        notitie = input("\nNotitie (optioneel): ").strip()

        entry = {
            "datum": datetime.now().isoformat(),
            "stemming": naam,
            "emoji": emoji,
            "score": score,
            "activiteiten": gekozen_act,
            "notitie": notitie
        }

        self.data["entries"].append(entry)

        # Update streak
        gisteren = (datetime.now().date() - timedelta(days=1)).isoformat()
        heeft_gisteren = any(
            e["datum"].startswith(gisteren) for e in self.data["entries"]
        )

        if heeft_gisteren:
            self.data["streak"] += 1
        else:
            self.data["streak"] = 1

        self._sla_op()

        print(f"\n[OK] Mood gelogd: {emoji} {naam}")
        print(f"     Streak: {self.data['streak']} dagen!")

    def _bekijk_vandaag(self):
        """Bekijk mood entries van vandaag."""
        print("\n--- VANDAAG ---")

        vandaag = datetime.now().date().isoformat()
        entries = [
            e for e in self.data["entries"]
            if e["datum"].startswith(vandaag)
        ]

        if not entries:
            print("Nog geen mood gelogd vandaag.")
            return

        for e in entries:
            tijd = e["datum"][11:16]
            print(f"\n  {tijd} - {e['emoji']} {e['stemming']}")
            if e.get("activiteiten"):
                print(f"        Activiteiten: {', '.join(e['activiteiten'])}")
            if e.get("notitie"):
                print(f"        Notitie: {e['notitie'][:40]}")

    def _week_overzicht(self):
        """Toon mood overzicht van afgelopen week."""
        print("\n--- WEEK OVERZICHT ---")

        vandaag = datetime.now().date()

        print("\n  Dag       Mood")
        print("  " + "-" * 30)

        for i in range(6, -1, -1):
            dag = vandaag - timedelta(days=i)
            dag_str = dag.isoformat()
            dag_naam = dag.strftime("%a %d-%m")

            entries = [
                e for e in self.data["entries"]
                if e["datum"].startswith(dag_str)
            ]

            if entries:
                # Gemiddelde score
                avg = sum(e["score"] for e in entries) / len(entries)
                emojis = "".join(e["emoji"] for e in entries)
                print(f"  {dag_naam}  {emojis} (gem: {avg:.1f})")
            else:
                print(f"  {dag_naam}  ---")

    def _statistieken(self):
        """Toon mood statistieken."""
        print("\n--- STATISTIEKEN ---")

        if not self.data["entries"]:
            print("Geen data om te analyseren.")
            return

        # Basis stats
        totaal = len(self.data["entries"])
        gemiddeld = sum(e["score"] for e in self.data["entries"]) / totaal

        print(f"\n  Totaal logs: {totaal}")
        print(f"  Gemiddelde mood: {gemiddeld:.1f}/5")
        print(f"  Huidige streak: {self.data['streak']} dagen")

        # Verdeling
        print("\n  Mood verdeling:")
        counts = Counter(e["stemming"] for e in self.data["entries"])

        for key, (naam, emoji, _) in self.stemmingen.items():
            count = counts.get(naam, 0)
            percentage = (count / totaal) * 100 if totaal > 0 else 0
            bar = "█" * int(percentage / 5)
            print(f"    {emoji} {naam:15} {bar} {count} ({percentage:.0f}%)")

        # Beste dag
        if totaal >= 7:
            per_dag = {}
            for e in self.data["entries"]:
                dag = datetime.fromisoformat(e["datum"]).strftime("%A")
                if dag not in per_dag:
                    per_dag[dag] = []
                per_dag[dag].append(e["score"])

            beste = max(per_dag.items(), key=lambda x: sum(x[1])/len(x[1]))
            print(f"\n  Beste dag: {beste[0]} (gem: {sum(beste[1])/len(beste[1]):.1f})")

    def _mood_patronen(self):
        """Analyseer mood patronen."""
        print("\n--- MOOD PATRONEN ---")

        if len(self.data["entries"]) < 5:
            print("Minimaal 5 entries nodig voor patronen.")
            return

        # Activiteiten analyse
        act_scores = {}
        for e in self.data["entries"]:
            for act in e.get("activiteiten", []):
                if act not in act_scores:
                    act_scores[act] = []
                act_scores[act].append(e["score"])

        if act_scores:
            print("\n  Activiteiten en je mood:")
            gesorteerd = sorted(
                act_scores.items(),
                key=lambda x: sum(x[1])/len(x[1]),
                reverse=True
            )

            for act, scores in gesorteerd[:5]:
                avg = sum(scores) / len(scores)
                emoji = "😄" if avg >= 4 else "🙂" if avg >= 3 else "😕"
                print(f"    {emoji} {act}: {avg:.1f}/5 ({len(scores)}x)")

        # Trend laatste 7 dagen
        vandaag = datetime.now().date()
        week_scores = []

        for i in range(7):
            dag = vandaag - timedelta(days=i)
            dag_str = dag.isoformat()
            entries = [
                e for e in self.data["entries"]
                if e["datum"].startswith(dag_str)
            ]
            if entries:
                avg = sum(e["score"] for e in entries) / len(entries)
                week_scores.append(avg)

        if len(week_scores) >= 3:
            trend = week_scores[0] - week_scores[-1]
            if trend > 0.5:
                print("\n  📈 Je mood lijkt te verbeteren!")
            elif trend < -0.5:
                print("\n  📉 Je mood lijkt te dalen. Zorg goed voor jezelf!")
            else:
                print("\n  📊 Je mood is stabiel.")

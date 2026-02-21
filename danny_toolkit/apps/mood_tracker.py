"""
Mood Tracker v2.0 - AI-Powered stemming tracker.
"""

import logging
from datetime import datetime, timedelta
from collections import Counter
from ..core.utils import clear_scherm
from .base_app import BaseApp

logger = logging.getLogger(__name__)


class MoodTrackerApp(BaseApp):
    """AI-Powered mood tracker voor stemming en emoties."""

    def __init__(self):
        super().__init__("mood.json")

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

    def _get_default_data(self) -> dict:
        """Standaard data voor mood."""
        return {
            "entries": [],
            "streak": 0
        }

    def _log_memory_event(self, event_type, data):
        """Log event naar Unified Memory."""
        try:
            if not hasattr(self, "_memory"):
                from ..brain.unified_memory import UnifiedMemory
                self._memory = UnifiedMemory()
            self._memory.store_event(
                app="mood_tracker",
                event_type=event_type,
                data=data
            )
        except Exception as e:
            logger.debug("Memory event error: %s", e)

    def run(self):
        """Start de mood tracker."""
        while True:
            clear_scherm()
            print("+" + "=" * 50 + "+")
            print("|          MOOD TRACKER v2.0                        |")
            if self.client:
                print("|          [AI POWERED]                            |")
            print("+" + "=" * 50 + "+")
            self._toon_recente_mood()
            print("+" + "-" * 50 + "+")
            print("|  1. Mood loggen                                   |")
            print("|  2. Vandaag bekijken                              |")
            print("|  3. Week overzicht                                |")
            print("|  4. Statistieken                                  |")
            print("|  5. Mood patronen                                 |")
            print("+" + "-" * 50 + "+")
            print("|  [AI FUNCTIES]                                    |")
            print("|  6. AI Mood Analyse                               |")
            print("|  7. AI Welzijns Tips                              |")
            print("|  8. AI Mood Voorspelling                          |")
            print("|  9. AI Dagboek Reflectie                          |")
            print("+" + "-" * 50 + "+")
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
            elif keuze == "6":
                self._ai_mood_analyse()
            elif keuze == "7":
                self._ai_welzijns_tips()
            elif keuze == "8":
                self._ai_mood_voorspelling()
            elif keuze == "9":
                self._ai_dagboek_reflectie()

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
        self._log_memory_event("mood_logged", {
            "stemming": naam, "score": score
        })

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

    # ==================== AI FUNCTIES ====================

    def _get_mood_context(self) -> str:
        """Verzamel mood data voor AI context."""
        if not self.data["entries"]:
            return "Geen mood data beschikbaar."

        # Laatste 7 dagen data
        vandaag = datetime.now().date()
        week_data = []
        for i in range(7):
            dag = vandaag - timedelta(days=i)
            dag_str = dag.isoformat()
            entries = [e for e in self.data["entries"] if e["datum"].startswith(dag_str)]
            if entries:
                avg_score = sum(e["score"] for e in entries) / len(entries)
                stemmingen = [e["stemming"] for e in entries]
                activiteiten = []
                for e in entries:
                    activiteiten.extend(e.get("activiteiten", []))
                notities = [e.get("notitie", "") for e in entries if e.get("notitie")]
                week_data.append({
                    "dag": dag.strftime("%A"),
                    "score": avg_score,
                    "stemmingen": stemmingen,
                    "activiteiten": list(set(activiteiten)),
                    "notities": notities
                })

        context = "Mood data afgelopen week:\n"
        for d in week_data:
            context += f"- {d['dag']}: Score {d['score']:.1f}/5, "
            context += f"Stemmingen: {', '.join(d['stemmingen'])}"
            if d['activiteiten']:
                context += f", Activiteiten: {', '.join(d['activiteiten'])}"
            if d['notities']:
                context += f", Notities: {'; '.join(d['notities'][:2])}"
            context += "\n"

        return context

    def _ai_mood_analyse(self):
        """AI analyseert je mood patronen diepgaand."""
        print("\n--- AI MOOD ANALYSE ---")

        if len(self.data["entries"]) < 3:
            print("[!] Minimaal 3 mood entries nodig voor analyse.")
            return

        context = self._get_mood_context()

        if not self.client:
            # Fallback analyse
            scores = [e["score"] for e in self.data["entries"][-14:]]
            gem = sum(scores) / len(scores)
            if gem >= 4:
                print("\n[Analyse]: Je mood is overwegend positief!")
            elif gem >= 3:
                print("\n[Analyse]: Je mood is stabiel met ups en downs.")
            else:
                print("\n[Analyse]: Je mood lijkt wat lager. Overweeg zelfzorg.")
            return

        print("\n[AI analyseert je mood data...]")
        prompt = f"""Analyseer deze mood tracking data en geef persoonlijke inzichten.

{context}

Geef een warme, ondersteunende analyse met:
1. Algemene mood trend
2. Opvallende patronen (dagen, activiteiten)
3. Positieve punten om te vieren
4. Zachte suggesties voor verbetering

Houd het persoonlijk en empathisch. Antwoord in het Nederlands."""

        response = self._ai_request(prompt, max_tokens=700)
        if response:
            print(f"\n[AI Mood Analyse]:")
            print(response)
        else:
            print("[!] AI niet beschikbaar.")

    def _ai_welzijns_tips(self):
        """AI geeft gepersonaliseerde welzijnstips."""
        print("\n--- AI WELZIJNS TIPS ---")

        # Bepaal huidige mood context
        vandaag = datetime.now().date().isoformat()
        vandaag_entries = [e for e in self.data["entries"] if e["datum"].startswith(vandaag)]

        if vandaag_entries:
            huidige_mood = vandaag_entries[-1]["stemming"]
            score = vandaag_entries[-1]["score"]
        else:
            huidige_mood = "onbekend"
            score = 3

        if not self.client:
            # Fallback tips
            tips = {
                5: ["Deel je positieve energie met anderen!", "Dit is een goed moment voor creatieve projecten."],
                4: ["Geniet van dit goede gevoel.", "Overweeg een wandeling te maken."],
                3: ["Neem even pauze als je dat nodig hebt.", "Een kopje thee kan helpen."],
                2: ["Wees lief voor jezelf vandaag.", "Praat met iemand die je vertrouwt."],
                1: ["Het is OK om je zo te voelen.", "Kleine stapjes zijn ook stapjes."]
            }
            print("\n[Welzijns Tips]:")
            for tip in tips.get(score, tips[3]):
                print(f"  • {tip}")
            return

        print("\n[AI genereert persoonlijke tips...]")

        context = self._get_mood_context() if self.data["entries"] else ""

        prompt = f"""Geef 5 gepersonaliseerde welzijnstips gebaseerd op deze informatie:

Huidige mood: {huidige_mood} (score: {score}/5)
{context}

Geef praktische, warme en uitvoerbare tips die passen bij de huidige stemming.
Wees empathisch en ondersteunend. Antwoord in het Nederlands met bullet points."""

        response = self._ai_request(prompt, max_tokens=500)
        if response:
            print(f"\n[AI Welzijns Tips voor jou]:")
            print(response)
        else:
            print("[!] AI niet beschikbaar.")

    def _ai_mood_voorspelling(self):
        """AI voorspelt mood trends."""
        print("\n--- AI MOOD VOORSPELLING ---")

        if len(self.data["entries"]) < 7:
            print("[!] Minimaal 7 entries nodig voor voorspelling.")
            return

        context = self._get_mood_context()

        if not self.client:
            # Simpele trend berekening
            scores = [e["score"] for e in self.data["entries"][-7:]]
            trend = scores[0] - scores[-1] if len(scores) > 1 else 0
            if trend > 0:
                print("\n[Trend]: Stijgende lijn verwacht!")
            elif trend < 0:
                print("\n[Trend]: Let op jezelf, dalende trend.")
            else:
                print("\n[Trend]: Stabiele mood verwacht.")
            return

        print("\n[AI analyseert patronen...]")
        prompt = f"""Analyseer deze mood data en geef een voorzichtige voorspelling.

{context}

Geef:
1. Verwachte mood trend voor komende dagen
2. Welke dag waarschijnlijk het beste wordt
3. Tips om de mood positief te houden
4. Waarschuwingen voor potentieel moeilijke momenten

Wees voorzichtig met voorspellingen en benadruk dat dit slechts indicaties zijn.
Antwoord in het Nederlands."""

        response = self._ai_request(prompt, max_tokens=600)
        if response:
            print(f"\n[AI Mood Voorspelling]:")
            print(response)
        else:
            print("[!] AI niet beschikbaar.")

    def _ai_dagboek_reflectie(self):
        """AI helpt met dagelijkse reflectie."""
        print("\n--- AI DAGBOEK REFLECTIE ---")

        print("\nHoe was je dag? Vertel me erover:")
        print("(Typ wat er gebeurd is, hoe je je voelde, etc.)")
        print("(Typ 'KLAAR' om te stoppen)")

        regels = []
        while True:
            regel = input()
            if regel.strip().upper() == "KLAAR":
                break
            regels.append(regel)

        tekst = "\n".join(regels)
        if not tekst.strip():
            print("[!] Geen tekst ingevoerd.")
            return

        if not self.client:
            print("\n[Reflectie]: Bedankt voor het delen!")
            print("  Neem even de tijd om te waarderen wat je vandaag hebt meegemaakt.")
            return

        print("\n[AI reflecteert met je mee...]")
        prompt = f"""Iemand deelt hun dag met je:

"{tekst}"

Geef een warme, empathische reflectie:
1. Erken hun gevoelens
2. Benoem positieve aspecten die je opvalt
3. Geef een zachte, ondersteunende observatie
4. Eindig met een positieve gedachte of vraag om over na te denken

Wees als een warme, begripvolle vriend. Antwoord in het Nederlands."""

        response = self._ai_request(prompt, max_tokens=500)
        if response:
            print(f"\n[AI Reflectie]:")
            print(response)

            # Optie om als notitie bij vandaag te voegen
            opslaan = input("\nDeze reflectie opslaan bij vandaag? (j/n): ").strip().lower()
            if opslaan == "j":
                vandaag = datetime.now().date().isoformat()
                vandaag_entries = [e for e in self.data["entries"] if e["datum"].startswith(vandaag)]
                if vandaag_entries:
                    vandaag_entries[-1]["notitie"] = f"{vandaag_entries[-1].get('notitie', '')} | Reflectie: {response[:200]}"
                    self._sla_op()
                    print("[OK] Reflectie opgeslagen!")
                else:
                    print("[i] Log eerst je mood om reflecties op te slaan.")
        else:
            print("[!] AI niet beschikbaar.")

"""
Agenda Planner v2.0 - AI-Powered planning assistent.
"""

import json
import os
from datetime import datetime, timedelta
from ..core.config import Config
from ..core.utils import clear_scherm

# AI Integration
try:
    from anthropic import Anthropic
    AI_BESCHIKBAAR = True
except ImportError:
    AI_BESCHIKBAAR = False


class AgendaPlannerApp:
    """AI-Powered agenda en planning assistent."""

    VERSIE = "2.0"

    def __init__(self):
        Config.ensure_dirs()
        self.bestand = Config.APPS_DATA_DIR / "agenda.json"
        self.data = self._laad_data()
        self.client = None
        self._init_ai()

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

    def _laad_data(self) -> dict:
        """Laad agenda data."""
        if self.bestand.exists():
            try:
                with open(self.bestand, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {
            "afspraken": [],
            "taken": [],
            "herinneringen": []
        }

    def _sla_op(self):
        """Sla data op."""
        with open(self.bestand, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    def run(self):
        """Start de agenda planner."""
        while True:
            clear_scherm()
            print("+" + "=" * 50 + "+")
            print("|          AGENDA PLANNER v2.0                      |")
            if self.client:
                print("|          [AI POWERED]                            |")
            print("+" + "=" * 50 + "+")
            self._toon_vandaag()
            print("+" + "-" * 50 + "+")
            print("|  1. Afspraak toevoegen                            |")
            print("|  2. Taak toevoegen                                |")
            print("|  3. Week overzicht                                |")
            print("|  4. Alle afspraken                                |")
            print("|  5. Taken beheren                                 |")
            print("|  6. Afspraak verwijderen                          |")
            print("+" + "-" * 50 + "+")
            print("|  [AI FUNCTIES]                                    |")
            print("|  7. AI Dag Planning                               |")
            print("|  8. AI Prioriteiten                               |")
            print("|  9. AI Productiviteit Tips                        |")
            print("+" + "-" * 50 + "+")
            print("|  0. Terug                                         |")
            print("+" + "=" * 50 + "+")

            keuze = input("\nKeuze: ").strip()

            if keuze == "0":
                break
            elif keuze == "1":
                self._nieuwe_afspraak()
            elif keuze == "2":
                self._nieuwe_taak()
            elif keuze == "3":
                self._week_overzicht()
            elif keuze == "4":
                self._alle_afspraken()
            elif keuze == "5":
                self._beheer_taken()
            elif keuze == "6":
                self._verwijder_afspraak()
            elif keuze == "7":
                self._ai_dag_planning()
            elif keuze == "8":
                self._ai_prioriteiten()
            elif keuze == "9":
                self._ai_productiviteit_tips()

            input("\nDruk op Enter...")

    def _toon_vandaag(self):
        """Toon afspraken voor vandaag."""
        vandaag = datetime.now().date().isoformat()
        afspraken = [
            a for a in self.data["afspraken"]
            if a["datum"] == vandaag
        ]
        taken = [t for t in self.data["taken"] if not t.get("voltooid")]

        dag = datetime.now().strftime("%A %d %B")
        print(f"|  {dag:<48}|")

        if afspraken:
            for a in sorted(afspraken, key=lambda x: x.get("tijd", "00:00")):
                tijd = a.get("tijd", "")
                print(f"|    {tijd} - {a['titel'][:35]:<40}|")
        else:
            print(f"|  Geen afspraken vandaag                           |")

        if taken:
            print(f"|  Open taken: {len(taken):<36}|")

    def _nieuwe_afspraak(self):
        """Voeg een nieuwe afspraak toe."""
        print("\n--- NIEUWE AFSPRAAK ---")

        titel = input("Titel: ").strip()
        if not titel:
            print("[!] Titel is verplicht!")
            return

        print("\nDatum (formaat: DD-MM-JJJJ of 'morgen', 'overmorgen'):")
        datum_input = input("Datum: ").strip().lower()

        if datum_input == "morgen":
            datum = (datetime.now() + timedelta(days=1)).date()
        elif datum_input == "overmorgen":
            datum = (datetime.now() + timedelta(days=2)).date()
        elif datum_input == "vandaag" or datum_input == "":
            datum = datetime.now().date()
        else:
            try:
                datum = datetime.strptime(datum_input, "%d-%m-%Y").date()
            except ValueError:
                print("[!] Ongeldig datum formaat!")
                return

        tijd = input("Tijd (HH:MM, optioneel): ").strip()
        if tijd:
            try:
                datetime.strptime(tijd, "%H:%M")
            except ValueError:
                tijd = ""

        locatie = input("Locatie (optioneel): ").strip()
        notities = input("Notities (optioneel): ").strip()

        afspraak = {
            "id": len(self.data["afspraken"]) + 1,
            "titel": titel,
            "datum": datum.isoformat(),
            "tijd": tijd,
            "locatie": locatie,
            "notities": notities,
            "aangemaakt": datetime.now().isoformat()
        }

        self.data["afspraken"].append(afspraak)
        self._sla_op()

        print(f"\n[OK] Afspraak '{titel}' toegevoegd voor {datum.strftime('%d-%m-%Y')}!")

    def _nieuwe_taak(self):
        """Voeg een nieuwe taak toe."""
        print("\n--- NIEUWE TAAK ---")

        titel = input("Taak: ").strip()
        if not titel:
            print("[!] Taak is verplicht!")
            return

        print("\nPrioriteit:")
        print("  1. Hoog")
        print("  2. Normaal")
        print("  3. Laag")

        prio_keuze = input("Keuze (1-3): ").strip()
        prioriteiten = {"1": "hoog", "2": "normaal", "3": "laag"}
        prioriteit = prioriteiten.get(prio_keuze, "normaal")

        deadline = input("Deadline (DD-MM-JJJJ, optioneel): ").strip()
        if deadline:
            try:
                deadline = datetime.strptime(deadline, "%d-%m-%Y").date().isoformat()
            except ValueError:
                deadline = ""

        taak = {
            "id": len(self.data["taken"]) + 1,
            "titel": titel,
            "prioriteit": prioriteit,
            "deadline": deadline,
            "voltooid": False,
            "aangemaakt": datetime.now().isoformat()
        }

        self.data["taken"].append(taak)
        self._sla_op()

        print(f"\n[OK] Taak '{titel}' toegevoegd!")

    def _week_overzicht(self):
        """Toon overzicht van deze week."""
        print("\n--- WEEK OVERZICHT ---")

        vandaag = datetime.now().date()

        for i in range(7):
            dag = vandaag + timedelta(days=i)
            dag_str = dag.isoformat()
            dag_naam = dag.strftime("%a %d-%m")

            afspraken = [
                a for a in self.data["afspraken"]
                if a["datum"] == dag_str
            ]

            if i == 0:
                prefix = "(vandaag)"
            elif i == 1:
                prefix = "(morgen)"
            else:
                prefix = ""

            print(f"\n  {dag_naam} {prefix}")

            if afspraken:
                for a in sorted(afspraken, key=lambda x: x.get("tijd", "00:00")):
                    tijd = a.get("tijd", "  --  ")
                    print(f"    {tijd}  {a['titel'][:30]}")
            else:
                print("    Geen afspraken")

    def _alle_afspraken(self):
        """Bekijk alle afspraken."""
        print("\n--- ALLE AFSPRAKEN ---")

        if not self.data["afspraken"]:
            print("Geen afspraken.")
            return

        # Sorteer op datum
        gesorteerd = sorted(
            self.data["afspraken"],
            key=lambda x: (x["datum"], x.get("tijd", "00:00"))
        )

        vandaag = datetime.now().date().isoformat()

        print("\n  Komende afspraken:")
        for a in gesorteerd:
            if a["datum"] >= vandaag:
                datum = datetime.fromisoformat(a["datum"]).strftime("%d-%m")
                tijd = a.get("tijd", "--:--")
                print(f"    {a['id']}. {datum} {tijd} - {a['titel'][:25]}")

        print("\n  Verlopen afspraken:")
        for a in gesorteerd:
            if a["datum"] < vandaag:
                datum = datetime.fromisoformat(a["datum"]).strftime("%d-%m")
                print(f"    {a['id']}. {datum} - {a['titel'][:25]}")

    def _beheer_taken(self):
        """Beheer taken."""
        print("\n--- TAKEN ---")

        open_taken = [t for t in self.data["taken"] if not t.get("voltooid")]
        voltooide = [t for t in self.data["taken"] if t.get("voltooid")]

        if not self.data["taken"]:
            print("Geen taken.")
            return

        # Sorteer op prioriteit
        prio_order = {"hoog": 0, "normaal": 1, "laag": 2}
        open_taken.sort(key=lambda x: prio_order.get(x["prioriteit"], 1))

        print("\n  Open taken:")
        for t in open_taken:
            prio = {"hoog": "!", "normaal": "-", "laag": "."}[t["prioriteit"]]
            deadline = ""
            if t.get("deadline"):
                deadline = f" (voor {t['deadline'][:10]})"
            print(f"    {t['id']}. [{prio}] {t['titel'][:30]}{deadline}")

        if voltooide:
            print(f"\n  Voltooid: {len(voltooide)} taken")

        # Taak voltooien
        keuze = input("\nTaak ID om te voltooien (of Enter): ").strip()
        if keuze:
            try:
                taak_id = int(keuze)
                for t in self.data["taken"]:
                    if t["id"] == taak_id:
                        t["voltooid"] = True
                        t["voltooid_op"] = datetime.now().isoformat()
                        self._sla_op()
                        print(f"[OK] Taak '{t['titel']}' voltooid!")
                        break
            except ValueError:
                pass

    def _verwijder_afspraak(self):
        """Verwijder een afspraak."""
        self._alle_afspraken()

        if not self.data["afspraken"]:
            return

        try:
            keuze = int(input("\nAfspraak ID om te verwijderen: ").strip())
            for i, a in enumerate(self.data["afspraken"]):
                if a["id"] == keuze:
                    bevestig = input(f"'{a['titel']}' verwijderen? (j/n): ").strip().lower()
                    if bevestig == "j":
                        self.data["afspraken"].pop(i)
                        self._sla_op()
                        print("[OK] Afspraak verwijderd!")
                    break
        except ValueError:
            pass

    # ==================== AI FUNCTIES ====================

    def _get_agenda_context(self) -> str:
        """Verzamel agenda data voor AI."""
        vandaag = datetime.now().date()
        context = "Agenda overzicht:\n\n"

        # Afspraken komende week
        context += "Afspraken komende week:\n"
        for i in range(7):
            dag = vandaag + timedelta(days=i)
            dag_str = dag.isoformat()
            afspraken = [a for a in self.data["afspraken"] if a["datum"] == dag_str]
            if afspraken:
                context += f"- {dag.strftime('%A %d-%m')}:\n"
                for a in afspraken:
                    context += f"  • {a.get('tijd', '')} {a['titel']}\n"

        # Open taken
        open_taken = [t for t in self.data["taken"] if not t.get("voltooid")]
        if open_taken:
            context += "\nOpen taken:\n"
            for t in open_taken:
                prio = t.get("prioriteit", "normaal")
                context += f"- [{prio}] {t['titel']}\n"

        return context

    def _ai_dag_planning(self):
        """AI helpt met dagplanning."""
        print("\n--- AI DAG PLANNING ---")

        context = self._get_agenda_context()

        if not self.client:
            print("\n[Planning Tips]:")
            print("  • Begin met je belangrijkste taak")
            print("  • Plan pauzes tussen afspraken")
            print("  • Houd buffer voor onverwachte zaken")
            return

        print("\n[AI plant je dag...]")
        prompt = f"""Maak een optimale dagplanning op basis van:

{context}

Geef:
1. Voorgestelde volgorde van taken
2. Beste tijden voor focus werk
3. Wanneer pauzes te nemen
4. Tips voor de dag

Praktisch en uitvoerbaar. Nederlands."""

        response = self._ai_request(prompt, max_tokens=500)
        if response:
            print(f"\n[AI Dagplanning]:\n{response}")

    def _ai_prioriteiten(self):
        """AI helpt met prioriteiten stellen."""
        print("\n--- AI PRIORITEITEN ---")

        open_taken = [t for t in self.data["taken"] if not t.get("voltooid")]
        if not open_taken:
            print("[!] Geen open taken om te prioriteren.")
            return

        if not self.client:
            print("\n[Prioriteiten Advies]:")
            hoog = [t for t in open_taken if t.get("prioriteit") == "hoog"]
            if hoog:
                print(f"  Focus eerst op: {hoog[0]['titel']}")
            return

        taken_lijst = "\n".join([
            f"- {t['titel']} (prio: {t.get('prioriteit', 'normaal')})"
            for t in open_taken
        ])

        print("\n[AI analyseert prioriteiten...]")
        prompt = f"""Help me prioriteiten stellen voor deze taken:

{taken_lijst}

Geef:
1. Aanbevolen volgorde (meest urgent eerst)
2. Wat vandaag af moet
3. Wat kan wachten
4. Tips voor focus

Wees specifiek. Nederlands."""

        response = self._ai_request(prompt, max_tokens=400)
        if response:
            print(f"\n[AI Prioriteiten]:\n{response}")

    def _ai_productiviteit_tips(self):
        """AI geeft productiviteit tips."""
        print("\n--- AI PRODUCTIVITEIT TIPS ---")

        context = self._get_agenda_context()

        if not self.client:
            print("\n[Productiviteit Tips]:")
            print("  • Werk in blokken van 25-50 minuten")
            print("  • Elimineer afleidingen")
            print("  • Begin met de moeilijkste taak")
            print("  • Neem regelmatig pauzes")
            return

        print("\n[AI genereert tips...]")
        prompt = f"""Geef productiviteit tips gebaseerd op deze agenda:

{context}

Geef 5 concrete, persoonlijke tips voor:
- Beter tijdmanagement
- Meer focus
- Stress verminderen
- Taken efficienter afronden

Praktisch en direct toepasbaar. Nederlands."""

        response = self._ai_request(prompt, max_tokens=400)
        if response:
            print(f"\n[AI Tips]:\n{response}")

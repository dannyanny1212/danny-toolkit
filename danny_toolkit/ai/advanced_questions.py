"""
Advanced Questions v1.0 - Geavanceerde vragen stellen met AI.
Diepgaande vraag-antwoord sessies, Socratische dialoog, en meer.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from ..core.config import Config
from ..core.utils import clear_scherm

# AI Integration
try:
    from anthropic import Anthropic
    AI_BESCHIKBAAR = True
except ImportError:
    AI_BESCHIKBAAR = False


class AdvancedQuestionsApp:
    """Advanced Questions - Diepgaande AI-gesprekken."""

    VERSIE = "1.0"

    # Vraag modes
    MODES = {
        "socratisch": {
            "naam": "Socratische Dialoog",
            "beschrijving": "Ontdek antwoorden door gerichte vragen",
            "system": """Je bent een Socratische leraar. In plaats van direct antwoorden
te geven, stel je doordachte vragen die de gebruiker helpen om zelf tot
inzichten te komen. Leid ze stap voor stap naar dieper begrip.
Gebruik de Socratische methode: vraag naar definities, voorbeelden,
tegenvoorbeelden, en implicaties."""
        },
        "devil": {
            "naam": "Devil's Advocate",
            "beschrijving": "Daag je standpunten uit",
            "system": """Je speelt de rol van devil's advocate. Wat de gebruiker ook
beweert, je zoekt naar tegenargumenten, zwakke punten, en alternatieve
perspectieven. Wees kritisch maar respectvol. Help ze hun argumenten
te versterken door ze uit te dagen."""
        },
        "expert": {
            "naam": "Expert Interview",
            "beschrijving": "Stel vragen als een expert",
            "system": """Je bent een expert interviewer. Stel diepgaande, professionele
vragen over het onderwerp. Vraag door op details, vraag om bronnen en
bewijs, en help de gebruiker om elk aspect van het onderwerp te verkennen.
Gedraag je als een journalist of wetenschapper die alles wil begrijpen."""
        },
        "filosofisch": {
            "naam": "Filosofische Verkenning",
            "beschrijving": "Verken diepere betekenissen",
            "system": """Je bent een filosoof die helpt bij het verkennen van diepere
vragen over het leven, ethiek, kennis, en realiteit. Stel vragen over
de onderliggende aannames, waarden, en implicaties van standpunten.
Verwijs naar relevante filosofische concepten en denkers."""
        },
        "brainstorm": {
            "naam": "Brainstorm Sessie",
            "beschrijving": "Creatieve idee-generatie",
            "system": """Je bent een creatieve brainstorm partner. Help de gebruiker
om nieuwe ideeën te genereren door vragen te stellen die creativiteit
stimuleren. Gebruik technieken zoals: omgekeerd denken, analogieën,
combineren van concepten, en 'wat als' scenario's."""
        },
        "coach": {
            "naam": "Life Coach",
            "beschrijving": "Persoonlijke groei en reflectie",
            "system": """Je bent een empathische life coach. Stel vragen die helpen
bij zelfreflectie en persoonlijke groei. Focus op doelen, waarden,
obstakels, en actieplannen. Wees ondersteunend maar uitdagend.
Help de gebruiker om inzichten om te zetten in concrete stappen."""
        },
    }

    # Voorgedefinieerde diepe vragen
    DIEPE_VRAGEN = [
        "Wat zou je doen als je wist dat je niet kon falen?",
        "Welke overtuiging heb je die de meeste mensen niet delen?",
        "Wat is het belangrijkste dat je hebt geleerd dit jaar?",
        "Als je kon praten met je 10-jarige zelf, wat zou je zeggen?",
        "Wat zou je veranderen als niemand je zou oordelen?",
        "Welk probleem zou je oplossen als je alle middelen had?",
        "Wat is je grootste angst en wat zegt die over je?",
        "Wanneer voelde je je het meest levend?",
        "Wat betekent succes echt voor jou?",
        "Welke keuze zou je overdoen als je kon?",
    ]

    def __init__(self):
        Config.ensure_dirs()
        self.data_dir = Config.APPS_DATA_DIR / "advanced_questions"
        self.data_dir.mkdir(exist_ok=True)
        self.data_file = self.data_dir / "sessions.json"
        self.data = self._laad_data()
        self.client = None
        if AI_BESCHIKBAAR and Config.has_anthropic_key():
            self.client = Anthropic()

    def _laad_data(self) -> Dict:
        """Laad sessie data."""
        if self.data_file.exists():
            try:
                with open(self.data_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {
            "sessies": [],
            "favoriete_vragen": [],
        }

    def _sla_op(self):
        """Sla data op."""
        with open(self.data_file, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    def _start_sessie(self, mode: str):
        """Start een vraag-sessie."""
        if not self.client:
            print("\n  AI niet beschikbaar. Stel ANTHROPIC_API_KEY in.")
            input("  Druk op Enter...")
            return

        mode_info = self.MODES.get(mode)
        if not mode_info:
            return

        clear_scherm()
        print(f"\n  === {mode_info['naam'].upper()} ===")
        print(f"  {mode_info['beschrijving']}\n")

        sessie = {
            "mode": mode,
            "datum": datetime.now().isoformat(),
            "berichten": [],
        }

        # Onderwerp kiezen
        onderwerp = input("  Onderwerp of vraag: ").strip()
        if not onderwerp:
            return

        print("\n  (Typ 'stop' om de sessie te beëindigen)")
        print("  " + "-" * 50)

        messages = []

        # Eerste vraag
        try:
            response = self.client.messages.create(
                model=Config.CLAUDE_MODEL,
                max_tokens=500,
                system=mode_info["system"],
                messages=[{
                    "role": "user",
                    "content": f"Het onderwerp is: {onderwerp}. Begin de sessie."
                }]
            )

            ai_response = response.content[0].text
            messages.append({"role": "user", "content": onderwerp})
            messages.append({"role": "assistant", "content": ai_response})

            print(f"\n  AI: {ai_response}")

            sessie["berichten"].append({"rol": "gebruiker", "tekst": onderwerp})
            sessie["berichten"].append({"rol": "ai", "tekst": ai_response})

        except Exception as e:
            print(f"\n  Fout: {e}")
            input("  Druk op Enter...")
            return

        # Conversatie loop
        while True:
            print()
            user_input = input("  Jij: ").strip()

            if user_input.lower() == "stop":
                break

            if not user_input:
                continue

            messages.append({"role": "user", "content": user_input})
            sessie["berichten"].append({"rol": "gebruiker", "tekst": user_input})

            try:
                response = self.client.messages.create(
                    model=Config.CLAUDE_MODEL,
                    max_tokens=500,
                    system=mode_info["system"],
                    messages=messages
                )

                ai_response = response.content[0].text
                messages.append({"role": "assistant", "content": ai_response})
                sessie["berichten"].append({"rol": "ai", "tekst": ai_response})

                print(f"\n  AI: {ai_response}")

            except Exception as e:
                print(f"\n  Fout: {e}")
                break

        # Opslaan
        self.data["sessies"].append(sessie)
        self._sla_op()

        print("\n  " + "=" * 50)
        print("  Sessie opgeslagen!")
        print(f"  Berichten: {len(sessie['berichten'])}")

        input("\n  Druk op Enter...")

    def _kies_mode(self):
        """Kies vraag mode."""
        clear_scherm()
        print("\n  === KIES VRAAG MODE ===\n")

        modes = list(self.MODES.keys())

        for i, (key, info) in enumerate(self.MODES.items(), 1):
            print(f"  {i}. {info['naam']}")
            print(f"     {info['beschrijving']}\n")

        try:
            keuze = int(input("  Keuze: ").strip())
            if 1 <= keuze <= len(modes):
                self._start_sessie(modes[keuze - 1])
        except (ValueError, IndexError):
            pass

    def _diepe_vraag(self):
        """Krijg een diepe vraag om over na te denken."""
        clear_scherm()
        print("\n  === DIEPE VRAAG ===\n")

        import random
        vraag = random.choice(self.DIEPE_VRAGEN)

        print("  " + "-" * 50)
        print(f"\n  {vraag}")
        print("\n  " + "-" * 50)

        print("\n  Neem even de tijd om hierover na te denken...")

        if input("\n  Wil je je gedachten vastleggen? (j/n): ").lower() == "j":
            print("\n  Schrijf je gedachten (typ 'klaar' als je klaar bent):")

            gedachten = []
            while True:
                lijn = input("  > ")
                if lijn.lower() == "klaar":
                    break
                gedachten.append(lijn)

            if gedachten:
                self.data["favoriete_vragen"].append({
                    "vraag": vraag,
                    "antwoord": "\n".join(gedachten),
                    "datum": datetime.now().isoformat(),
                })
                self._sla_op()
                print("\n  Opgeslagen!")

        input("\n  Druk op Enter...")

    def _vraag_verdieping(self):
        """Verdiep een eigen vraag met AI hulp."""
        if not self.client:
            print("\n  AI niet beschikbaar. Stel ANTHROPIC_API_KEY in.")
            input("  Druk op Enter...")
            return

        clear_scherm()
        print("\n  === VRAAG VERDIEPING ===\n")
        print("  Stel een vraag en ontvang verdiepende vervolgvragen.\n")

        vraag = input("  Je vraag: ").strip()
        if not vraag:
            return

        try:
            response = self.client.messages.create(
                model=Config.CLAUDE_MODEL,
                max_tokens=800,
                messages=[{
                    "role": "user",
                    "content": f"""Gegeven deze vraag: "{vraag}"

Genereer 5 verdiepende vervolgvragen die helpen om deze vraag
beter te begrijpen en te beantwoorden. Elke vraag moet een ander
aspect van het onderwerp verkennen.

Format:
1. [vraag]
2. [vraag]
etc."""
                }]
            )

            print("\n  VERDIEPENDE VRAGEN:\n")
            print(f"  {response.content[0].text}")

        except Exception as e:
            print(f"\n  Fout: {e}")

        input("\n  Druk op Enter...")

    def _bekijk_sessies(self):
        """Bekijk eerdere sessies."""
        clear_scherm()
        print("\n  === EERDERE SESSIES ===\n")

        sessies = self.data.get("sessies", [])

        if not sessies:
            print("  Nog geen sessies opgeslagen.")
            input("\n  Druk op Enter...")
            return

        for i, s in enumerate(reversed(sessies[-10:]), 1):
            mode = self.MODES.get(s["mode"], {}).get("naam", s["mode"])
            datum = s["datum"][:10]
            berichten = len(s.get("berichten", []))
            print(f"  {i}. {datum} | {mode} | {berichten} berichten")

        keuze = input("\n  Bekijk # (of Enter): ").strip()

        if keuze.isdigit():
            idx = len(sessies) - int(keuze)
            if 0 <= idx < len(sessies):
                s = sessies[idx]

                clear_scherm()
                mode = self.MODES.get(s["mode"], {}).get("naam", s["mode"])
                print(f"\n  === {mode.upper()} ===")
                print(f"  Datum: {s['datum'][:10]}\n")

                for b in s.get("berichten", []):
                    if b["rol"] == "gebruiker":
                        print(f"  Jij: {b['tekst'][:100]}...")
                    else:
                        print(f"  AI: {b['tekst'][:100]}...")
                    print()

                input("\n  Druk op Enter...")

    def _stel_eigen_vraag(self):
        """Stel een directe vraag aan AI."""
        if not self.client:
            print("\n  AI niet beschikbaar. Stel ANTHROPIC_API_KEY in.")
            input("  Druk op Enter...")
            return

        clear_scherm()
        print("\n  === DIRECTE VRAAG ===\n")
        print("  Stel een vraag en krijg een uitgebreid antwoord.\n")

        vraag = input("  Je vraag: ").strip()
        if not vraag:
            return

        print("\n  Even denken...\n")

        try:
            response = self.client.messages.create(
                model=Config.CLAUDE_MODEL,
                max_tokens=1500,
                messages=[{
                    "role": "user",
                    "content": vraag
                }]
            )

            print("  ANTWOORD:\n")
            print("  " + "-" * 50)

            antwoord = response.content[0].text
            # Wrap tekst
            for lijn in antwoord.split("\n"):
                if len(lijn) > 70:
                    woorden = lijn.split()
                    huidige_lijn = "  "
                    for woord in woorden:
                        if len(huidige_lijn) + len(woord) > 70:
                            print(huidige_lijn)
                            huidige_lijn = "  " + woord
                        else:
                            huidige_lijn += " " + woord
                    if huidige_lijn.strip():
                        print(huidige_lijn)
                else:
                    print(f"  {lijn}")

            print("  " + "-" * 50)

        except Exception as e:
            print(f"\n  Fout: {e}")

        input("\n  Druk op Enter...")

    def run(self):
        """Start de app."""
        while True:
            clear_scherm()

            ai_status = "AI: Actief" if self.client else "AI: Niet beschikbaar"
            sessies = len(self.data.get("sessies", []))

            print(f"""
  ╔═══════════════════════════════════════════════════════════╗
  ║              ADVANCED QUESTIONS v1.0                      ║
  ║             Diepgaande Vraag-Sessies                      ║
  ╠═══════════════════════════════════════════════════════════╣
  ║  1. Start Vraag Sessie                                    ║
  ║  2. Diepe Vraag (reflectie)                               ║
  ║  3. Vraag Verdieping                                      ║
  ║  4. Directe Vraag aan AI                                  ║
  ║  5. Bekijk Eerdere Sessies                                ║
  ║  0. Terug                                                 ║
  ╚═══════════════════════════════════════════════════════════╝
  {ai_status} | Sessies: {sessies}
""")
            print("  Modes: Socratisch, Devil's Advocate, Expert, Filosofisch,")
            print("         Brainstorm, Life Coach")

            keuze = input("\n  Keuze: ").strip()

            if keuze == "0":
                break
            elif keuze == "1":
                self._kies_mode()
            elif keuze == "2":
                self._diepe_vraag()
            elif keuze == "3":
                self._vraag_verdieping()
            elif keuze == "4":
                self._stel_eigen_vraag()
            elif keuze == "5":
                self._bekijk_sessies()

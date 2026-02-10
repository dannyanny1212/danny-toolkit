"""
Goals Tracker v1.0 - Persoonlijke doelen en groei tracker.
Track je doelen, visualiseer voortgang en blijf gemotiveerd.
"""

import json
import os
import random
from datetime import datetime, timedelta
from collections import Counter
from ..core.config import Config
from ..core.utils import clear_scherm

# AI Integration
try:
    from anthropic import Anthropic
    AI_BESCHIKBAAR = True
except ImportError:
    AI_BESCHIKBAAR = False


class GoalsTrackerApp:
    """Persoonlijke doelen tracker met dashboards en motivatie."""

    VERSIE = "1.0"

    # Categorieen met emoji's
    CATEGORIEEN = {
        "gezondheid": ("Gezondheid", "💪"),
        "werk": ("Werk & Carriere", "💼"),
        "financieel": ("Financieel", "💰"),
        "persoonlijk": ("Persoonlijke Groei", "🌱"),
        "relaties": ("Relaties", "❤️"),
        "educatie": ("Leren & Educatie", "📚"),
        "creatief": ("Creatief", "🎨"),
        "anders": ("Anders", "⭐")
    }

    # Motivatie quotes
    QUOTES = [
        "Elke reis begint met een enkele stap.",
        "Je bent sterker dan je denkt.",
        "Vooruitgang, niet perfectie.",
        "Kleine stappen leiden tot grote veranderingen.",
        "Vandaag is een nieuwe kans.",
        "Geloof in je eigen potentieel.",
        "Succes is de som van kleine inspanningen.",
        "Je doelen zijn binnen bereik.",
        "Focus op de reis, niet alleen de bestemming.",
        "Elke dag is een kans om te groeien."
    ]

    def __init__(self):
        Config.ensure_dirs()
        self.bestand = Config.APPS_DATA_DIR / "goals.json"
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
        """Laad goals data."""
        if self.bestand.exists():
            try:
                with open(self.bestand, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {
            "doelen": [],
            "milestones": [],
            "check_ins": [],
            "achievements": [],
            "stats": {
                "doelen_voltooid": 0,
                "milestones_bereikt": 0,
                "streak": 0,
                "laatste_check_in": None
            }
        }

    def _sla_op(self):
        """Sla data op."""
        with open(self.bestand, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    def _log_memory_event(self, event_type, data):
        """Log event naar Unified Memory."""
        try:
            if not hasattr(self, "_memory"):
                from ..brain.unified_memory import UnifiedMemory
                self._memory = UnifiedMemory()
            self._memory.store_event(
                app="goals_tracker",
                event_type=event_type,
                data=data
            )
        except Exception:
            pass  # Memory is optioneel

    def run(self):
        """Start de goals tracker."""
        while True:
            clear_scherm()
            self._toon_header()
            self._toon_motivatie_quote()
            print("+" + "-" * 50 + "+")
            print("|  1. Dashboard                                     |")
            print("|  2. Nieuw Doel Toevoegen                          |")
            print("|  3. Voortgang Bijwerken                           |")
            print("|  4. Doelen Bekijken                               |")
            print("|  5. Milestones Beheren                            |")
            print("|  6. Check-in Doen                                 |")
            print("+" + "-" * 50 + "+")
            print("|  [AI FUNCTIES]                                    |")
            print("|  7. AI Doel Coach                                 |")
            print("|  8. AI Actieplan                                  |")
            print("|  9. AI Motivatie Boost                            |")
            print("+" + "-" * 50 + "+")
            print("|  0. Terug                                         |")
            print("+" + "=" * 50 + "+")

            keuze = input("\nKeuze: ").strip()

            if keuze == "0":
                break
            elif keuze == "1":
                self._dashboard()
            elif keuze == "2":
                self._nieuw_doel()
            elif keuze == "3":
                self._update_voortgang()
            elif keuze == "4":
                self._bekijk_doelen()
            elif keuze == "5":
                self._milestones_menu()
            elif keuze == "6":
                self._check_in()
            elif keuze == "7":
                self._ai_doel_coach()
            elif keuze == "8":
                self._ai_actieplan()
            elif keuze == "9":
                self._ai_motivatie()

            input("\nDruk op Enter...")

    def _toon_header(self):
        """Toon header."""
        print("+" + "=" * 50 + "+")
        print("|          GOALS TRACKER v1.0                       |")
        if self.client:
            print("|          [AI POWERED]                            |")
        print("+" + "=" * 50 + "+")

        # Quick stats
        actief = len([d for d in self.data["doelen"] if not d.get("voltooid")])
        voltooid = self.data["stats"]["doelen_voltooid"]
        streak = self.data["stats"]["streak"]

        print(f"|  Actieve doelen: {actief:<5} Voltooid: {voltooid:<5} "
              f"Streak: {streak:<3}|")

    def _toon_motivatie_quote(self):
        """Toon een motiverende quote."""
        quote = random.choice(self.QUOTES)
        # Centreer de quote
        padding = (48 - len(quote)) // 2
        print(f"|  {' ' * padding}{quote}{' ' * (48 - padding - len(quote))}|")

    # =========================================================================
    # DASHBOARD
    # =========================================================================

    def _dashboard(self):
        """Toon gepersonaliseerd dashboard."""
        clear_scherm()
        print("=" * 52)
        print("           PERSOONLIJK DASHBOARD")
        print("=" * 52)

        actieve_doelen = [d for d in self.data["doelen"] if not d.get("voltooid")]

        if not actieve_doelen:
            print("\n  Geen actieve doelen. Voeg er een toe!")
            return

        # Voortgang per categorie
        print("\n  VOORTGANG PER CATEGORIE")
        print("  " + "-" * 46)

        cat_progress = {}
        for doel in actieve_doelen:
            cat = doel.get("categorie", "anders")
            if cat not in cat_progress:
                cat_progress[cat] = []
            cat_progress[cat].append(doel.get("voortgang", 0))

        for cat, progresses in cat_progress.items():
            naam, emoji = self.CATEGORIEEN.get(cat, ("Anders", "⭐"))
            avg = sum(progresses) / len(progresses)
            bar = self._progress_bar(avg)
            print(f"  {emoji} {naam:<20} {bar} {avg:.0f}%")

        # Top 5 actieve doelen
        print("\n  ACTIEVE DOELEN")
        print("  " + "-" * 46)

        for doel in actieve_doelen[:5]:
            voortgang = doel.get("voortgang", 0)
            bar = self._progress_bar(voortgang, width=15)
            naam = doel["naam"][:25]
            print(f"  {bar} {voortgang:>3}% | {naam}")

        if len(actieve_doelen) > 5:
            print(f"  ... en {len(actieve_doelen) - 5} meer doelen")

        # Aankomende milestones
        print("\n  AANKOMENDE MILESTONES")
        print("  " + "-" * 46)

        aankomend = [m for m in self.data["milestones"]
                     if not m.get("bereikt") and m.get("deadline")]

        if aankomend:
            aankomend.sort(key=lambda x: x.get("deadline", "9999"))
            for m in aankomend[:3]:
                deadline = m["deadline"][:10]
                naam = m["naam"][:30]
                print(f"  [{deadline}] {naam}")
        else:
            print("  Geen aankomende milestones")

        # Recente achievements
        if self.data["achievements"]:
            print("\n  RECENTE PRESTATIES")
            print("  " + "-" * 46)
            for ach in self.data["achievements"][-3:]:
                print(f"  🏆 {ach['naam']} ({ach['datum'][:10]})")

        # Streak info
        print("\n  " + "=" * 46)
        streak = self.data["stats"]["streak"]
        if streak > 0:
            print(f"  🔥 Check-in streak: {streak} dag"
                  f"{'en' if streak != 1 else ''}!")
        else:
            print("  💡 Start een streak door dagelijks in te checken!")

    def _progress_bar(self, percentage: float, width: int = 20) -> str:
        """Genereer een progress bar."""
        filled = int(percentage / 100 * width)
        empty = width - filled
        return f"[{'█' * filled}{'░' * empty}]"

    # =========================================================================
    # DOELEN BEHEER
    # =========================================================================

    def _nieuw_doel(self):
        """Voeg een nieuw doel toe."""
        print("\n--- NIEUW DOEL ---")

        naam = input("Doel naam: ").strip()
        if not naam:
            print("[!] Naam is verplicht!")
            return

        # Categorie kiezen
        print("\nCategorie:")
        cats = list(self.CATEGORIEEN.items())
        for i, (key, (naam_cat, emoji)) in enumerate(cats, 1):
            print(f"  {i}. {emoji} {naam_cat}")

        try:
            cat_keuze = int(input(f"\nKeuze (1-{len(cats)}): ").strip()) - 1
            categorie = cats[cat_keuze][0] if 0 <= cat_keuze < len(cats) else "anders"
        except (ValueError, IndexError):
            categorie = "anders"

        beschrijving = input("Beschrijving (optioneel): ").strip()

        # Deadline
        deadline_input = input("Deadline (DD-MM-YYYY of Enter voor geen): ").strip()
        deadline = None
        if deadline_input:
            try:
                deadline = datetime.strptime(deadline_input, "%d-%m-%Y").isoformat()
            except ValueError:
                print("[!] Ongeldig formaat, geen deadline ingesteld.")

        # Prioriteit
        print("\nPrioriteit:")
        print("  1. Laag   2. Normaal   3. Hoog")
        prio_input = input("Keuze (1-3): ").strip()
        prioriteit = {"1": "laag", "2": "normaal", "3": "hoog"}.get(prio_input, "normaal")

        doel = {
            "id": len(self.data["doelen"]) + 1,
            "naam": naam,
            "beschrijving": beschrijving,
            "categorie": categorie,
            "prioriteit": prioriteit,
            "voortgang": 0,
            "deadline": deadline,
            "aangemaakt": datetime.now().isoformat(),
            "voltooid": False,
            "notities": []
        }

        self.data["doelen"].append(doel)
        self._sla_op()
        self._log_memory_event("goal_created", {
            "naam": naam, "categorie": categorie
        })

        cat_naam, cat_emoji = self.CATEGORIEEN.get(categorie, ("Anders", "⭐"))
        print(f"\n[OK] Doel '{naam}' toegevoegd!")
        print(f"     Categorie: {cat_emoji} {cat_naam}")
        print(f"     Prioriteit: {prioriteit}")

    def _update_voortgang(self):
        """Update voortgang van een doel."""
        print("\n--- VOORTGANG BIJWERKEN ---")

        actief = [d for d in self.data["doelen"] if not d.get("voltooid")]
        if not actief:
            print("[!] Geen actieve doelen.")
            return

        print("\nActieve doelen:")
        for d in actief:
            voortgang = d.get("voortgang", 0)
            bar = self._progress_bar(voortgang, 10)
            print(f"  {d['id']}. {d['naam'][:25]} {bar} {voortgang}%")

        try:
            doel_id = int(input("\nDoel ID: ").strip())
            doel = next((d for d in self.data["doelen"] if d["id"] == doel_id), None)

            if not doel:
                print("[!] Doel niet gevonden!")
                return

            print(f"\nHuidige voortgang: {doel.get('voortgang', 0)}%")
            nieuwe_voortgang = input("Nieuwe voortgang (0-100): ").strip()

            voortgang = int(nieuwe_voortgang)
            voortgang = max(0, min(100, voortgang))

            oude_voortgang = doel.get("voortgang", 0)
            doel["voortgang"] = voortgang

            # Check of doel voltooid is
            if voortgang == 100 and not doel.get("voltooid"):
                doel["voltooid"] = True
                doel["voltooid_op"] = datetime.now().isoformat()
                self.data["stats"]["doelen_voltooid"] += 1

                # Achievement toevoegen
                self.data["achievements"].append({
                    "naam": f"Doel bereikt: {doel['naam']}",
                    "datum": datetime.now().isoformat()
                })

                print(f"\n🎉 GEFELICITEERD! Doel '{doel['naam']}' voltooid!")

            else:
                verschil = voortgang - oude_voortgang
                if verschil > 0:
                    print(f"\n[OK] Voortgang bijgewerkt: +{verschil}%!")
                    print(f"     {self._progress_bar(voortgang)} {voortgang}%")
                else:
                    print(f"\n[OK] Voortgang bijgewerkt naar {voortgang}%")

            # Optionele notitie
            notitie = input("\nNotitie toevoegen (optioneel): ").strip()
            if notitie:
                doel["notities"].append({
                    "tekst": notitie,
                    "datum": datetime.now().isoformat(),
                    "voortgang": voortgang
                })

            self._sla_op()
            self._log_memory_event("goal_updated", {
                "naam": doel["naam"],
                "voortgang": voortgang
            })

        except ValueError:
            print("[!] Voer geldige nummers in!")

    def _bekijk_doelen(self):
        """Bekijk alle doelen."""
        print("\n--- ALLE DOELEN ---")

        if not self.data["doelen"]:
            print("Geen doelen gevonden.")
            return

        print("\n  Filter:")
        print("  1. Alle   2. Actief   3. Voltooid   4. Per categorie")
        filter_keuze = input("\nKeuze (1-4): ").strip()

        doelen = self.data["doelen"]

        if filter_keuze == "2":
            doelen = [d for d in doelen if not d.get("voltooid")]
        elif filter_keuze == "3":
            doelen = [d for d in doelen if d.get("voltooid")]
        elif filter_keuze == "4":
            print("\nCategorie:")
            cats = list(self.CATEGORIEEN.items())
            for i, (key, (naam, emoji)) in enumerate(cats, 1):
                print(f"  {i}. {emoji} {naam}")
            try:
                cat_idx = int(input("\nKeuze: ").strip()) - 1
                cat_key = cats[cat_idx][0]
                doelen = [d for d in doelen if d.get("categorie") == cat_key]
            except (ValueError, IndexError):
                pass

        if not doelen:
            print("\nGeen doelen gevonden met deze filter.")
            return

        for d in doelen:
            cat_naam, cat_emoji = self.CATEGORIEEN.get(
                d.get("categorie", "anders"), ("Anders", "⭐"))
            status = "✓ Voltooid" if d.get("voltooid") else f"{d.get('voortgang', 0)}%"

            print(f"\n  {cat_emoji} {d['naam']}")
            print(f"     ID: {d['id']} | Status: {status}")
            print(f"     Prioriteit: {d.get('prioriteit', 'normaal')}")

            if d.get("deadline"):
                deadline = d["deadline"][:10]
                print(f"     Deadline: {deadline}")

            if d.get("beschrijving"):
                print(f"     {d['beschrijving'][:50]}")

            if not d.get("voltooid"):
                bar = self._progress_bar(d.get("voortgang", 0), 30)
                print(f"     {bar}")

    # =========================================================================
    # MILESTONES
    # =========================================================================

    def _milestones_menu(self):
        """Milestones beheer menu."""
        print("\n--- MILESTONES ---")
        print("\n  1. Milestone toevoegen")
        print("  2. Milestones bekijken")
        print("  3. Milestone bereikt markeren")
        print("  0. Terug")

        keuze = input("\nKeuze: ").strip()

        if keuze == "1":
            self._nieuwe_milestone()
        elif keuze == "2":
            self._bekijk_milestones()
        elif keuze == "3":
            self._milestone_bereikt()

    def _nieuwe_milestone(self):
        """Voeg nieuwe milestone toe."""
        actief = [d for d in self.data["doelen"] if not d.get("voltooid")]
        if not actief:
            print("[!] Geen actieve doelen om milestone aan te koppelen.")
            return

        print("\nKies doel voor milestone:")
        for d in actief:
            print(f"  {d['id']}. {d['naam']}")

        try:
            doel_id = int(input("\nDoel ID: ").strip())
            doel = next((d for d in self.data["doelen"] if d["id"] == doel_id), None)

            if not doel:
                print("[!] Doel niet gevonden!")
                return

            naam = input("Milestone naam: ").strip()
            if not naam:
                print("[!] Naam is verplicht!")
                return

            deadline_input = input("Deadline (DD-MM-YYYY of Enter): ").strip()
            deadline = None
            if deadline_input:
                try:
                    deadline = datetime.strptime(deadline_input, "%d-%m-%Y").isoformat()
                except ValueError:
                    pass

            milestone = {
                "id": len(self.data["milestones"]) + 1,
                "doel_id": doel_id,
                "naam": naam,
                "deadline": deadline,
                "bereikt": False,
                "aangemaakt": datetime.now().isoformat()
            }

            self.data["milestones"].append(milestone)
            self._sla_op()

            print(f"\n[OK] Milestone '{naam}' toegevoegd aan '{doel['naam']}'!")

        except ValueError:
            print("[!] Ongeldig nummer!")

    def _bekijk_milestones(self):
        """Bekijk alle milestones."""
        if not self.data["milestones"]:
            print("\nGeen milestones gevonden.")
            return

        print("\nMilestones:")
        for m in self.data["milestones"]:
            doel = next((d for d in self.data["doelen"]
                        if d["id"] == m["doel_id"]), None)
            doel_naam = doel["naam"][:20] if doel else "Onbekend"

            status = "✓" if m.get("bereikt") else "○"
            deadline = f" (deadline: {m['deadline'][:10]})" if m.get("deadline") else ""

            print(f"  {status} {m['naam']}")
            print(f"     Doel: {doel_naam}{deadline}")

    def _milestone_bereikt(self):
        """Markeer milestone als bereikt."""
        open_milestones = [m for m in self.data["milestones"] if not m.get("bereikt")]

        if not open_milestones:
            print("\nGeen open milestones.")
            return

        print("\nOpen milestones:")
        for m in open_milestones:
            print(f"  {m['id']}. {m['naam']}")

        try:
            m_id = int(input("\nMilestone ID: ").strip())
            milestone = next((m for m in self.data["milestones"]
                            if m["id"] == m_id), None)

            if not milestone:
                print("[!] Milestone niet gevonden!")
                return

            milestone["bereikt"] = True
            milestone["bereikt_op"] = datetime.now().isoformat()
            self.data["stats"]["milestones_bereikt"] += 1

            # Achievement
            self.data["achievements"].append({
                "naam": f"Milestone bereikt: {milestone['naam']}",
                "datum": datetime.now().isoformat()
            })

            self._sla_op()
            print(f"\n🎯 Milestone '{milestone['naam']}' bereikt!")

        except ValueError:
            print("[!] Ongeldig nummer!")

    # =========================================================================
    # CHECK-IN
    # =========================================================================

    def _check_in(self):
        """Dagelijkse check-in."""
        print("\n--- DAGELIJKSE CHECK-IN ---")

        vandaag = datetime.now().date().isoformat()

        # Check of al ingecheckt vandaag
        vandaag_checkin = any(
            c["datum"].startswith(vandaag)
            for c in self.data["check_ins"]
        )

        if vandaag_checkin:
            print("\n[i] Je hebt vandaag al ingecheckt!")
            hercheck = input("Opnieuw inchecken? (j/n): ").strip().lower()
            if hercheck != "j":
                return

        print("\nHoe gaat het met je doelen vandaag?")
        print("\n  1. Uitstekend - Veel vooruitgang!")
        print("  2. Goed - Steady progress")
        print("  3. Neutraal - Beetje gedaan")
        print("  4. Lastig - Moeite vandaag")
        print("  5. Moeilijk - Geen vooruitgang")

        gevoel = input("\nKeuze (1-5): ").strip()
        gevoel_map = {
            "1": ("uitstekend", 5),
            "2": ("goed", 4),
            "3": ("neutraal", 3),
            "4": ("lastig", 2),
            "5": ("moeilijk", 1)
        }
        gevoel_naam, score = gevoel_map.get(gevoel, ("neutraal", 3))

        notitie = input("\nKorte reflectie (optioneel): ").strip()

        check_in = {
            "datum": datetime.now().isoformat(),
            "gevoel": gevoel_naam,
            "score": score,
            "notitie": notitie
        }

        self.data["check_ins"].append(check_in)

        # Update streak
        gisteren = (datetime.now().date() - timedelta(days=1)).isoformat()
        had_gisteren = any(
            c["datum"].startswith(gisteren)
            for c in self.data["check_ins"]
        )

        if had_gisteren:
            self.data["stats"]["streak"] += 1
        else:
            self.data["stats"]["streak"] = 1

        self.data["stats"]["laatste_check_in"] = vandaag
        self._sla_op()

        streak = self.data["stats"]["streak"]
        print(f"\n[OK] Check-in voltooid!")
        print(f"     🔥 Streak: {streak} dag{'en' if streak != 1 else ''}!")

        if streak == 7:
            print("     🎉 Een week streak! Fantastisch!")
        elif streak == 30:
            print("     🏆 Een maand streak! Ongelofelijk!")

        # Toon motiverende boodschap
        if score >= 4:
            print("\n     Geweldig! Blijf zo doorgaan! 💪")
        elif score == 3:
            print("\n     Elke stap telt. Morgen weer een kans!")
        else:
            print("\n     Moeilijke dagen horen erbij. Je bent niet alleen. ❤️")

    # =========================================================================
    # AI FUNCTIES
    # =========================================================================

    def _get_goals_context(self) -> str:
        """Verzamel doelen context voor AI."""
        if not self.data["doelen"]:
            return "Geen doelen geconfigureerd."

        context = "Huidige doelen:\n"
        for d in self.data["doelen"]:
            status = "Voltooid" if d.get("voltooid") else f"{d.get('voortgang', 0)}% voortgang"
            context += f"- {d['naam']} ({d.get('categorie', 'anders')}): {status}\n"
            if d.get("beschrijving"):
                context += f"  Beschrijving: {d['beschrijving']}\n"

        if self.data["check_ins"]:
            context += "\nRecente check-ins:\n"
            for c in self.data["check_ins"][-5:]:
                context += f"- {c['datum'][:10]}: {c['gevoel']}"
                if c.get("notitie"):
                    context += f" - {c['notitie'][:50]}"
                context += "\n"

        return context

    def _ai_doel_coach(self):
        """AI coach voor doelen."""
        print("\n--- AI DOEL COACH ---")

        vraag = input("\nWat is je vraag over je doelen? ").strip()
        if not vraag:
            return

        if not self.client:
            print("\n[Coach]: Focus op kleine, haalbare stappen.")
            print("         Vier je vooruitgang, hoe klein ook!")
            return

        context = self._get_goals_context()
        prompt = f"""Je bent een warme, ondersteunende doelen coach.

Context van de gebruiker:
{context}

Vraag: "{vraag}"

Geef persoonlijk, praktisch advies. Wees bemoedigend maar realistisch.
Antwoord in het Nederlands, max 200 woorden."""

        print("\n[AI Coach denkt na...]")
        response = self._ai_request(prompt, max_tokens=400)
        if response:
            print(f"\n[Coach]:\n{response}")

    def _ai_actieplan(self):
        """AI genereert actieplan voor een doel."""
        print("\n--- AI ACTIEPLAN ---")

        actief = [d for d in self.data["doelen"] if not d.get("voltooid")]
        if not actief:
            print("[!] Geen actieve doelen.")
            return

        print("\nKies een doel voor het actieplan:")
        for d in actief:
            print(f"  {d['id']}. {d['naam']}")

        try:
            doel_id = int(input("\nDoel ID: ").strip())
            doel = next((d for d in self.data["doelen"] if d["id"] == doel_id), None)

            if not doel:
                print("[!] Doel niet gevonden!")
                return

            if not self.client:
                print(f"\n[Actieplan voor '{doel['naam']}']:")
                print("  1. Breek het doel op in kleinere stappen")
                print("  2. Stel een dagelijkse actie vast")
                print("  3. Track je voortgang wekelijks")
                print("  4. Vier elke mijlpaal")
                return

            prompt = f"""Maak een concreet actieplan voor dit doel:

Doel: {doel['naam']}
Beschrijving: {doel.get('beschrijving', 'Geen')}
Huidige voortgang: {doel.get('voortgang', 0)}%
Categorie: {doel.get('categorie', 'anders')}
Deadline: {doel.get('deadline', 'Geen')}

Geef een praktisch stappenplan met:
1. 5-7 concrete actiestappen
2. Tijdsindicatie per stap
3. Potentiele obstakels en oplossingen
4. Motivatietips

Antwoord in het Nederlands."""

            print("\n[AI genereert actieplan...]")
            response = self._ai_request(prompt, max_tokens=700)
            if response:
                print(f"\n[Actieplan]:\n{response}")

        except ValueError:
            print("[!] Ongeldig nummer!")

    def _ai_motivatie(self):
        """AI geeft motivatie boost."""
        print("\n--- AI MOTIVATIE BOOST ---")

        if not self.client:
            print("\n" + "=" * 40)
            print(random.choice(self.QUOTES))
            print("=" * 40)
            print("\nJe bent op de goede weg. Blijf gaan! 💪")
            return

        context = self._get_goals_context()
        prompt = f"""Geef een korte, krachtige motivatie boost.

Context:
{context}

Geef:
1. Een persoonlijke, bemoedigende boodschap
2. Erken wat ze al bereikt hebben
3. Eindig met een energieke call-to-action

Wees warm, authentiek en inspirerend. Max 100 woorden. Nederlands."""

        print("\n[AI genereert motivatie...]")
        response = self._ai_request(prompt, max_tokens=200)
        if response:
            print("\n" + "=" * 40)
            print(response)
            print("=" * 40)

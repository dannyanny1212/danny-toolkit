"""
Notitie App v2.0 - AI-Powered Notities maken en organiseren.
"""

import logging
from datetime import datetime
from ..core.utils import clear_scherm
from .base_app import BaseApp

logger = logging.getLogger(__name__)


class NotitieApp(BaseApp):
    """Een AI-powered app voor het maken en organiseren van notities."""

    def __init__(self):
        super().__init__("notities.json")
        self.notities = self.data

    def _get_default_data(self) -> dict:
        """Standaard data voor notities."""
        return {
            "notities": [],
            "categorieen": [
                "Algemeen", "Werk",
                "Persoonlijk", "Ideeen"
            ]
        }

    def _log_memory_event(self, event_type, data):
        """Log event naar Unified Memory."""
        try:
            if not hasattr(self, "_memory"):
                from ..brain.unified_memory import UnifiedMemory
                self._memory = UnifiedMemory()
            self._memory.store_event(
                app="notitie_app",
                event_type=event_type,
                data=data
            )
        except Exception as e:
            logger.debug("Memory event error: %s", e)

    def run(self):
        """Start de notitie app."""
        while True:
            clear_scherm()
            print("+" + "=" * 50 + "+")
            print("|          NOTITIE APP v2.0                        |")
            if self.client:
                print("|          [AI POWERED]                            |")
            print("+" + "=" * 50 + "+")
            print(f"|  Totaal notities: {len(self.notities['notities']):<30}|")
            print("+" + "-" * 50 + "+")
            print("|  1. Nieuwe notitie                               |")
            print("|  2. Notities bekijken                            |")
            print("|  3. Notitie zoeken                               |")
            print("|  4. Notitie verwijderen                          |")
            print("|  5. Categorieen beheren                          |")
            print("+" + "-" * 50 + "+")
            print("|  [AI FUNCTIES]                                   |")
            print("|  6. AI Samenvatting                              |")
            print("|  7. AI Brainstorm                                |")
            print("|  8. AI Categoriseer                              |")
            print("|  9. AI Schrijfhulp                               |")
            print("+" + "-" * 50 + "+")
            print("|  0. Terug                                        |")
            print("+" + "=" * 50 + "+")

            keuze = input("\nKeuze: ").strip()

            if keuze == "0":
                break
            elif keuze == "1":
                self._nieuwe_notitie()
            elif keuze == "2":
                self._bekijk_notities()
            elif keuze == "3":
                self._zoek_notitie()
            elif keuze == "4":
                self._verwijder_notitie()
            elif keuze == "5":
                self._beheer_categorieen()
            elif keuze == "6":
                self._ai_samenvatting()
            elif keuze == "7":
                self._ai_brainstorm()
            elif keuze == "8":
                self._ai_categoriseer()
            elif keuze == "9":
                self._ai_schrijfhulp()

            input("\nDruk op Enter...")

    def _nieuwe_notitie(self):
        """Maak een nieuwe notitie."""
        print("\n--- NIEUWE NOTITIE ---")

        # Kies categorie
        print("\nCategorieen:")
        for i, cat in enumerate(self.notities["categorieen"], 1):
            print(f"  {i}. {cat}")

        try:
            cat_idx = int(input("\nKies categorie: ").strip()) - 1
            categorie = self.notities["categorieen"][cat_idx]
        except (ValueError, IndexError):
            categorie = "Algemeen"

        titel = input("Titel: ").strip()
        if not titel:
            print("[!] Titel is verplicht!")
            return

        print("Inhoud (typ 'KLAAR' op een nieuwe regel als je klaar bent):")
        inhoud_regels = []
        while True:
            regel = input()
            if regel.strip().upper() == "KLAAR":
                break
            inhoud_regels.append(regel)

        inhoud = "\n".join(inhoud_regels)

        notitie = {
            "id": len(self.notities["notities"]) + 1,
            "titel": titel,
            "inhoud": inhoud,
            "categorie": categorie,
            "gemaakt": datetime.now().isoformat(),
            "gewijzigd": datetime.now().isoformat()
        }

        self.notities["notities"].append(notitie)
        self._sla_op()
        self._log_memory_event("note_created", {
            "titel": titel, "categorie": categorie
        })
        print(f"\n[OK] Notitie '{titel}' opgeslagen!")

    def _bekijk_notities(self):
        """Bekijk alle notities."""
        print("\n--- ALLE NOTITIES ---")

        if not self.notities["notities"]:
            print("Geen notities gevonden.")
            return

        # Groepeer per categorie
        per_categorie = {}
        for n in self.notities["notities"]:
            cat = n.get("categorie", "Algemeen")
            if cat not in per_categorie:
                per_categorie[cat] = []
            per_categorie[cat].append(n)

        for cat, notities in per_categorie.items():
            print(f"\n[{cat}]")
            for n in notities:
                datum = n["gemaakt"][:10]
                print(f"  {n['id']}. {n['titel'][:30]} ({datum})")

        # Detail bekijken
        keuze = input("\nNotitie ID om te lezen (of Enter): ").strip()
        if keuze:
            try:
                notitie_id = int(keuze)
                for n in self.notities["notities"]:
                    if n["id"] == notitie_id:
                        print(f"\n{'=' * 50}")
                        print(f"TITEL: {n['titel']}")
                        print(f"Categorie: {n['categorie']}")
                        print(f"Datum: {n['gemaakt'][:10]}")
                        print(f"{'=' * 50}")
                        print(n["inhoud"])
                        print(f"{'=' * 50}")
                        break
            except ValueError:
                pass

    def _zoek_notitie(self):
        """Zoek in notities."""
        zoekterm = input("\nZoekterm: ").strip().lower()
        if not zoekterm:
            return

        resultaten = []
        for n in self.notities["notities"]:
            if zoekterm in n["titel"].lower() or zoekterm in n["inhoud"].lower():
                resultaten.append(n)

        print(f"\n--- RESULTATEN ({len(resultaten)}) ---")
        for n in resultaten:
            print(f"  {n['id']}. {n['titel']} [{n['categorie']}]")

    def _verwijder_notitie(self):
        """Verwijder een notitie."""
        self._bekijk_notities()
        try:
            notitie_id = int(input("\nNotitie ID om te verwijderen: ").strip())
            for i, n in enumerate(self.notities["notities"]):
                if n["id"] == notitie_id:
                    bevestig = input(f"'{n['titel']}' verwijderen? (j/n): ").strip().lower()
                    if bevestig == "j":
                        self.notities["notities"].pop(i)
                        self._sla_op()
                        print("[OK] Notitie verwijderd!")
                    break
        except ValueError:
            pass

    def _beheer_categorieen(self):
        """Beheer categorieen."""
        print("\n--- CATEGORIEEN ---")
        for i, cat in enumerate(self.notities["categorieen"], 1):
            print(f"  {i}. {cat}")

        print("\n  a. Nieuwe categorie")
        print("  0. Terug")

        keuze = input("\nKeuze: ").strip().lower()
        if keuze == "a":
            nieuwe = input("Nieuwe categorie naam: ").strip()
            if nieuwe and nieuwe not in self.notities["categorieen"]:
                self.notities["categorieen"].append(nieuwe)
                self._sla_op()
                print(f"[OK] Categorie '{nieuwe}' toegevoegd!")

    # ==================== AI FUNCTIES ====================

    def _ai_samenvatting(self):
        """AI maakt een samenvatting van een notitie."""
        print("\n--- AI SAMENVATTING ---")

        if not self.notities["notities"]:
            print("[!] Geen notities om samen te vatten.")
            return

        # Toon notities
        for i, n in enumerate(self.notities["notities"], 1):
            print(f"  {i}. {n['titel'][:40]}")

        try:
            keuze = int(input("\nWelke notitie samenvatten? ").strip()) - 1
            if 0 <= keuze < len(self.notities["notities"]):
                notitie = self.notities["notities"][keuze]

                if not self.client:
                    # Fallback zonder AI
                    woorden = notitie["inhoud"].split()
                    samenvatting = " ".join(woorden[:30]) + "..." if len(woorden) > 30 else notitie["inhoud"]
                    print(f"\n[Basis samenvatting]: {samenvatting}")
                    return

                print("\n[AI denkt na...]")
                prompt = f"""Maak een korte, heldere samenvatting van deze notitie in het Nederlands.
Houd het beknopt (max 3-4 zinnen).

Titel: {notitie['titel']}
Inhoud: {notitie['inhoud']}"""

                response = self._ai_request(prompt)
                if response:
                    print(f"\n[AI Samenvatting]:")
                    print(f"  {response}")
                else:
                    print("[!] AI niet beschikbaar, probeer later.")
        except (ValueError, IndexError):
            print("[!] Ongeldige keuze.")

    def _ai_brainstorm(self):
        """AI helpt met brainstormen over een onderwerp."""
        print("\n--- AI BRAINSTORM ---")

        onderwerp = input("Waar wil je over brainstormen? ").strip()
        if not onderwerp:
            print("[!] Geen onderwerp ingevoerd.")
            return

        if not self.client:
            # Fallback suggesties
            fallback_tips = [
                f"- Wat zijn de voor- en nadelen van {onderwerp}?",
                f"- Wie kan je helpen met {onderwerp}?",
                f"- Wat is de eerste stap voor {onderwerp}?",
                f"- Welke bronnen heb je nodig voor {onderwerp}?",
                f"- Wat is je deadline voor {onderwerp}?"
            ]
            print("\n[Brainstorm vragen]:")
            for tip in fallback_tips:
                print(f"  {tip}")
            return

        print("\n[AI brainstormt...]")
        prompt = f"""Help me brainstormen over: {onderwerp}

Geef me 5-7 creatieve ideeen, vragen of invalshoeken om over na te denken.
Gebruik bullet points en houd het praktisch en inspirerend.
Antwoord in het Nederlands."""

        response = self._ai_request(prompt, max_tokens=600)
        if response:
            print(f"\n[AI Brainstorm Ideeen]:")
            print(response)

            # Optie om als notitie op te slaan
            opslaan = input("\nOpslaan als notitie? (j/n): ").strip().lower()
            if opslaan == "j":
                self.notities["notities"].append({
                    "id": len(self.notities["notities"]) + 1,
                    "titel": f"Brainstorm: {onderwerp}",
                    "inhoud": response,
                    "categorie": "Ideeen",
                    "gemaakt": datetime.now().isoformat(),
                    "gewijzigd": datetime.now().isoformat()
                })
                self._sla_op()
                print("[OK] Brainstorm opgeslagen als notitie!")
        else:
            print("[!] AI niet beschikbaar.")

    def _ai_categoriseer(self):
        """AI suggereert categorien voor notities."""
        print("\n--- AI CATEGORISEER ---")

        ongecategoriseerd = [
            n for n in self.notities["notities"]
            if n.get("categorie") == "Algemeen"
        ]

        if not ongecategoriseerd:
            print("[i] Alle notities zijn al gecategoriseerd!")
            return

        print(f"Er zijn {len(ongecategoriseerd)} notities in 'Algemeen'.")

        for notitie in ongecategoriseerd[:5]:  # Max 5 tegelijk
            print(f"\n  Notitie: {notitie['titel']}")

            if self.client:
                prompt = f"""Bekijk deze notitie en suggereer de beste categorie.
Beschikbare categorieen: {', '.join(self.notities['categorieen'])}

Titel: {notitie['titel']}
Inhoud: {notitie['inhoud'][:200]}

Antwoord met alleen de categorie naam, niets anders."""

                response = self._ai_request(prompt, max_tokens=50)
                if response:
                    suggestie = response.strip()
                    # Check of suggestie geldig is
                    if suggestie in self.notities["categorieen"]:
                        print(f"  AI suggestie: {suggestie}")
                        bevestig = input(f"  Toepassen? (j/n): ").strip().lower()
                        if bevestig == "j":
                            notitie["categorie"] = suggestie
                            notitie["gewijzigd"] = datetime.now().isoformat()
                            print(f"  [OK] Categorie gewijzigd naar '{suggestie}'")
                    else:
                        print(f"  AI suggestie: {suggestie} (nieuwe categorie)")
                        toevoegen = input("  Categorie toevoegen en toepassen? (j/n): ").strip().lower()
                        if toevoegen == "j":
                            self.notities["categorieen"].append(suggestie)
                            notitie["categorie"] = suggestie
                            print(f"  [OK] Nieuwe categorie '{suggestie}' toegevoegd!")
            else:
                print("  [!] AI niet beschikbaar voor suggestie")

        self._sla_op()
        print("\n[OK] Categorisatie voltooid!")

    def _ai_schrijfhulp(self):
        """AI helpt met het schrijven of verbeteren van notities."""
        print("\n--- AI SCHRIJFHULP ---")
        print("\n  1. Notitie uitbreiden")
        print("  2. Notitie verbeteren")
        print("  3. Nieuwe notitie dicteren")

        keuze = input("\nKeuze: ").strip()

        if keuze == "1":
            self._ai_uitbreiden()
        elif keuze == "2":
            self._ai_verbeteren()
        elif keuze == "3":
            self._ai_dicteren()

    def _ai_uitbreiden(self):
        """AI breidt een korte notitie uit."""
        if not self.notities["notities"]:
            print("[!] Geen notities beschikbaar.")
            return

        for i, n in enumerate(self.notities["notities"], 1):
            print(f"  {i}. {n['titel'][:40]}")

        try:
            keuze = int(input("\nWelke notitie uitbreiden? ").strip()) - 1
            notitie = self.notities["notities"][keuze]

            if not self.client:
                print("[!] AI niet beschikbaar voor uitbreiding.")
                return

            print("\n[AI breidt uit...]")
            prompt = f"""Breid deze notitie uit met meer details, context en nuttige informatie.
Behoud de originele boodschap maar maak het completer.

Titel: {notitie['titel']}
Originele inhoud: {notitie['inhoud']}

Schrijf de uitgebreide versie in het Nederlands."""

            response = self._ai_request(prompt, max_tokens=800)
            if response:
                print(f"\n[Uitgebreide versie]:")
                print(response)

                toepassen = input("\nDeze versie opslaan? (j/n): ").strip().lower()
                if toepassen == "j":
                    notitie["inhoud"] = response
                    notitie["gewijzigd"] = datetime.now().isoformat()
                    self._sla_op()
                    print("[OK] Notitie bijgewerkt!")
        except (ValueError, IndexError):
            print("[!] Ongeldige keuze.")

    def _ai_verbeteren(self):
        """AI verbetert spelling en stijl van een notitie."""
        if not self.notities["notities"]:
            print("[!] Geen notities beschikbaar.")
            return

        for i, n in enumerate(self.notities["notities"], 1):
            print(f"  {i}. {n['titel'][:40]}")

        try:
            keuze = int(input("\nWelke notitie verbeteren? ").strip()) - 1
            notitie = self.notities["notities"][keuze]

            if not self.client:
                print("[!] AI niet beschikbaar.")
                return

            print("\n[AI controleert...]")
            prompt = f"""Verbeter deze notitie qua spelling, grammatica en leesbaarheid.
Behoud de originele inhoud en betekenis, maar maak het professioneler.

Titel: {notitie['titel']}
Inhoud: {notitie['inhoud']}

Geef alleen de verbeterde tekst terug, in het Nederlands."""

            response = self._ai_request(prompt, max_tokens=600)
            if response:
                print(f"\n[Verbeterde versie]:")
                print(response)

                toepassen = input("\nDeze versie opslaan? (j/n): ").strip().lower()
                if toepassen == "j":
                    notitie["inhoud"] = response
                    notitie["gewijzigd"] = datetime.now().isoformat()
                    self._sla_op()
                    print("[OK] Notitie verbeterd!")
        except (ValueError, IndexError):
            print("[!] Ongeldige keuze.")

    def _ai_dicteren(self):
        """AI helpt met het structureren van gedicteerde gedachten."""
        print("\n--- AI DICTEREN ---")
        print("Typ je gedachten (ongestructureerd is OK):")
        print("(Typ 'KLAAR' op een nieuwe regel als je klaar bent)")

        gedachten = []
        while True:
            regel = input()
            if regel.strip().upper() == "KLAAR":
                break
            gedachten.append(regel)

        tekst = "\n".join(gedachten)
        if not tekst.strip():
            print("[!] Geen tekst ingevoerd.")
            return

        if not self.client:
            # Sla gewoon op zonder AI
            titel = tekst[:30] + "..." if len(tekst) > 30 else tekst
            self.notities["notities"].append({
                "id": len(self.notities["notities"]) + 1,
                "titel": titel,
                "inhoud": tekst,
                "categorie": "Algemeen",
                "gemaakt": datetime.now().isoformat(),
                "gewijzigd": datetime.now().isoformat()
            })
            self._sla_op()
            print("[OK] Notitie opgeslagen!")
            return

        print("\n[AI structureert...]")
        prompt = f"""Neem deze ruwe gedachten en maak er een gestructureerde notitie van.
Geef een passende titel en organiseer de inhoud logisch.

Ruwe tekst:
{tekst}

Format je antwoord als:
TITEL: [passende titel]
---
[gestructureerde inhoud]"""

        response = self._ai_request(prompt, max_tokens=600)
        if response:
            # Parse response
            if "TITEL:" in response and "---" in response:
                delen = response.split("---", 1)
                titel = delen[0].replace("TITEL:", "").strip()
                inhoud = delen[1].strip() if len(delen) > 1 else tekst
            else:
                titel = tekst[:30] + "..."
                inhoud = response

            print(f"\n[AI Resultaat]:")
            print(f"Titel: {titel}")
            print(f"Inhoud:\n{inhoud}")

            opslaan = input("\nOpslaan als notitie? (j/n): ").strip().lower()
            if opslaan == "j":
                categorie = self._kies_categorie_simpel()
                self.notities["notities"].append({
                    "id": len(self.notities["notities"]) + 1,
                    "titel": titel,
                    "inhoud": inhoud,
                    "categorie": categorie,
                    "gemaakt": datetime.now().isoformat(),
                    "gewijzigd": datetime.now().isoformat()
                })
                self._sla_op()
                print("[OK] Notitie opgeslagen!")

    def _kies_categorie_simpel(self) -> str:
        """Simpele categorie keuze."""
        print("\nCategorieen:")
        for i, cat in enumerate(self.notities["categorieen"], 1):
            print(f"  {i}. {cat}")
        try:
            keuze = int(input("Keuze: ").strip()) - 1
            return self.notities["categorieen"][keuze]
        except (ValueError, IndexError):
            return "Algemeen"

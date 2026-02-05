"""
Nieuws Agent - Multi-agent nieuws analyse systeem.
"""

import math
from pathlib import Path
from datetime import datetime
from collections import Counter

from ..core.config import Config
from ..core.utils import clear_scherm


class VectorDatabase:
    """Simpele vector database voor de nieuws agent."""

    def __init__(self):
        self.documenten = []

    def voeg_toe(self, bron: str, tekst: str):
        """Voegt een document toe."""
        doc_id = len(self.documenten)
        self.documenten.append({
            "id": doc_id,
            "bron": bron,
            "tekst": tekst,
            "embedding": self._maak_embedding(tekst)
        })
        return doc_id

    def _maak_embedding(self, tekst: str) -> dict:
        """Maakt een simpele TF embedding."""
        woorden = tekst.lower().split()
        woorden = [w.strip(".,!?:;()[]{}\"'") for w in woorden]
        woorden = [w for w in woorden if len(w) > 2]
        return dict(Counter(woorden))


class WebZoeker:
    """Simuleert web search functionaliteit."""

    def __init__(self):
        self.nieuws_database = {
            "ruimtevaart": [
                {
                    "bron": "SpaceNews.nl",
                    "titel": "SpaceX lanceert nieuwe Starship raket",
                    "tekst": "SpaceX heeft vandaag succesvol een nieuwe Starship raket gelanceerd.",
                    "datum": "2026-02-01",
                    "betrouwbaar": True
                },
                {
                    "bron": "NASA.gov",
                    "titel": "Artemis III missie uitgesteld naar 2027",
                    "tekst": "NASA heeft de Artemis III missie uitgesteld tot 2027.",
                    "datum": "2026-01-30",
                    "betrouwbaar": True
                },
                {
                    "bron": "SterrenKijker.nl",
                    "titel": "Aliens landen volgende week",
                    "tekst": "Bronnen beweren dat buitenaardse wezens contact hebben gemaakt.",
                    "datum": "2026-02-01",
                    "betrouwbaar": False
                }
            ],
            "gaming": [
                {
                    "bron": "IGN.com",
                    "titel": "GTA 6 release datum bevestigd",
                    "tekst": "Rockstar Games bevestigt: GTA 6 komt uit op 15 oktober 2026.",
                    "datum": "2026-02-01",
                    "betrouwbaar": True
                },
                {
                    "bron": "GameKrant.nl",
                    "titel": "Nintendo kondigt Switch 2 aan",
                    "tekst": "Nintendo heeft de Switch 2 aangekondigd met 8-inch OLED scherm.",
                    "datum": "2026-01-29",
                    "betrouwbaar": True
                },
                {
                    "bron": "GamerGerucht.net",
                    "titel": "Half-Life 3 aangekondigd",
                    "tekst": "Anonieme bronnen beweren dat Valve Half-Life 3 zal aankondigen.",
                    "datum": "2026-02-01",
                    "betrouwbaar": False
                }
            ],
            "ai": [
                {
                    "bron": "Anthropic.com",
                    "titel": "Claude 5 aangekondigd",
                    "tekst": "Anthropic kondigt Claude 5 aan met 2 miljoen token context window.",
                    "datum": "2026-02-01",
                    "betrouwbaar": True
                },
                {
                    "bron": "TechCrunch.com",
                    "titel": "OpenAI lanceert GPT-5",
                    "tekst": "OpenAI lanceert GPT-5 met verbeterde code-generatie.",
                    "datum": "2026-01-28",
                    "betrouwbaar": True
                },
                {
                    "bron": "AITijdschrift.nl",
                    "titel": "AI vervangt 50% van alle banen",
                    "tekst": "Experts voorspellen massale baanverlies door AI.",
                    "datum": "2026-02-01",
                    "betrouwbaar": False
                }
            ]
        }

    def zoek_nieuws(self, onderwerp: str) -> list:
        """Zoekt nieuws over een onderwerp."""
        onderwerp_lower = onderwerp.lower()

        for key in self.nieuws_database.keys():
            if key in onderwerp_lower or onderwerp_lower in key:
                return self.nieuws_database[key]

        return self.nieuws_database["ruimtevaart"]


class Agent:
    """Basis agent class."""

    def __init__(self, naam: str, emoji: str):
        self.naam = naam
        self.emoji = emoji

    def log(self, bericht: str):
        print(f"  [{self.naam}] {bericht}")


class ZoekerAgent(Agent):
    """Agent die informatie verzamelt."""

    def __init__(self):
        super().__init__("Zoeker", "[ZOEK]")
        self.web = WebZoeker()
        self.database = VectorDatabase()

    def verzamel(self, onderwerp: str) -> list:
        """Verzamelt nieuws over een onderwerp."""
        self.log(f"Zoeken naar nieuws over: {onderwerp}")
        artikelen = self.web.zoek_nieuws(onderwerp)

        for artikel in artikelen:
            self.database.voeg_toe(artikel["bron"], artikel["tekst"])
            self.log(f"Gevonden: {artikel['titel'][:40]}...")

        return artikelen


class FeitencheckerAgent(Agent):
    """Agent die feiten controleert."""

    def __init__(self):
        super().__init__("Checker", "[CHECK]")

    def controleer(self, artikelen: list) -> list:
        """Controleert de betrouwbaarheid van artikelen."""
        self.log("Betrouwbaarheid controleren...")

        resultaten = []
        for artikel in artikelen:
            is_betrouwbaar = artikel.get("betrouwbaar", False)
            status = "BETROUWBAAR" if is_betrouwbaar else "ONBETROUWBAAR"
            symbool = "[OK]" if is_betrouwbaar else "[!!]"
            self.log(f"{symbool} {artikel['bron']}: {status}")
            resultaten.append({**artikel, "status": status})

        return resultaten


class SchrijverAgent(Agent):
    """Agent die het rapport schrijft."""

    def __init__(self):
        super().__init__("Schrijver", "[SCHRIJF]")

    def schrijf_rapport(self, onderwerp: str, artikelen: list) -> dict:
        """Schrijft een rapport."""
        self.log("Rapport schrijven...")

        betrouwbaar = [a for a in artikelen if a["status"] == "BETROUWBAAR"]
        onbetrouwbaar = [a for a in artikelen if a["status"] == "ONBETROUWBAAR"]

        samenvatting = f"Dit rapport bevat {len(artikelen)} artikelen over {onderwerp}. "
        samenvatting += f"{len(betrouwbaar)} betrouwbaar, {len(onbetrouwbaar)} onbetrouwbaar."

        rapport = {
            "onderwerp": onderwerp,
            "datum": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "samenvatting": samenvatting,
            "betrouwbare_artikelen": betrouwbaar,
            "onbetrouwbare_artikelen": onbetrouwbaar,
            "actiepunten": [
                f"Blijf de ontwikkelingen rond {onderwerp} volgen",
                "Verifieer altijd nieuwsbronnen",
                "Wees kritisch over sensationele claims"
            ]
        }

        self.log(f"Rapport compleet: {len(betrouwbaar)} betrouwbare bronnen")
        return rapport


class RapportGeneratorAgent(Agent):
    """Agent die het rapport als bestand genereert."""

    def __init__(self):
        super().__init__("Generator", "[GEN]")
        Config.ensure_dirs()
        self.output_map = Config.RAPPORTEN_DIR

    def genereer(self, rapport: dict) -> str:
        """Genereert een HTML rapport."""
        self.log("HTML rapport genereren...")

        html = f"""<!DOCTYPE html>
<html lang="nl">
<head>
    <meta charset="UTF-8">
    <title>Nieuws Rapport: {rapport['onderwerp']}</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 40px auto; padding: 20px; }}
        h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }}
        h2 {{ color: #34495e; margin-top: 30px; }}
        .samenvatting {{ background: #ecf0f1; padding: 20px; border-radius: 8px; }}
        .artikel {{ border-left: 4px solid #3498db; padding: 15px; margin: 15px 0; background: #f9f9f9; }}
        .artikel.onbetrouwbaar {{ border-left-color: #e74c3c; background: #fdf2f2; }}
    </style>
</head>
<body>
    <h1>Nieuws Rapport: {rapport['onderwerp'].title()}</h1>
    <p>Gegenereerd op: {rapport['datum']}</p>
    <div class="samenvatting"><h2>Samenvatting</h2><p>{rapport['samenvatting']}</p></div>
    <h2>Betrouwbare Bronnen ({len(rapport['betrouwbare_artikelen'])})</h2>
"""
        for artikel in rapport["betrouwbare_artikelen"]:
            html += f'<div class="artikel"><strong>{artikel["bron"]}</strong>: {artikel["titel"]}<br><small>{artikel["tekst"]}</small></div>\n'

        if rapport["onbetrouwbare_artikelen"]:
            html += f'<h2>Onbetrouwbare Bronnen ({len(rapport["onbetrouwbare_artikelen"])})</h2>\n'
            for artikel in rapport["onbetrouwbare_artikelen"]:
                html += f'<div class="artikel onbetrouwbaar"><strong>{artikel["bron"]}</strong>: {artikel["titel"]}<br><small>LET OP: Niet geverifieerd</small></div>\n'

        html += "</body></html>"

        bestandsnaam = f"nieuws_{rapport['onderwerp'].lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        pad = self.output_map / bestandsnaam

        with open(pad, "w", encoding="utf-8") as f:
            f.write(html)

        self.log(f"Rapport opgeslagen: {pad}")
        return str(pad)


class NieuwsAgentApp:
    """Nieuws Agent orchestrator."""

    def __init__(self):
        self.zoeker = ZoekerAgent()
        self.feitenchecker = FeitencheckerAgent()
        self.schrijver = SchrijverAgent()
        self.generator = RapportGeneratorAgent()

    def analyseer(self, onderwerp: str) -> str:
        """Voert de complete nieuws-analyse uit."""
        print("\n" + "=" * 60)
        print("NIEUWS-AGENT")
        print("=" * 60)
        print(f"\nOnderwerp: {onderwerp}")
        print(f"Datum: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

        print("\n" + "-" * 40)
        print("STAP 1: INFORMATIE VERZAMELEN")
        print("-" * 40)
        artikelen = self.zoeker.verzamel(onderwerp)

        print("\n" + "-" * 40)
        print("STAP 2: FEITEN CONTROLEREN")
        print("-" * 40)
        gecontroleerd = self.feitenchecker.controleer(artikelen)

        print("\n" + "-" * 40)
        print("STAP 3: RAPPORT SCHRIJVEN")
        print("-" * 40)
        rapport = self.schrijver.schrijf_rapport(onderwerp, gecontroleerd)

        print("\n" + "-" * 40)
        print("STAP 4: RAPPORT GENEREREN")
        print("-" * 40)
        pdf_pad = self.generator.genereer(rapport)

        print("\n" + "=" * 60)
        print("[OK] NIEUWS-AGENT COMPLEET!")
        print("=" * 60)

        betrouwbaar = len([a for a in gecontroleerd if a["status"] == "BETROUWBAAR"])
        onbetrouwbaar = len([a for a in gecontroleerd if a["status"] == "ONBETROUWBAAR"])

        print(f"\nResultaten:")
        print(f"   Artikelen gevonden: {len(artikelen)}")
        print(f"   Betrouwbaar: {betrouwbaar}")
        print(f"   Onbetrouwbaar: {onbetrouwbaar}")
        print(f"\nRapport: {pdf_pad}")

        return pdf_pad

    def run(self):
        """Start de interactieve nieuws agent."""
        clear_scherm()
        print("\n" + "=" * 50)
        print("   NIEUWS-AGENT: Multi-Agent Nieuws Analyse")
        print("=" * 50)

        print("\nKies een onderwerp:")
        print("1. Ruimtevaart")
        print("2. Gaming")
        print("3. AI (Kunstmatige Intelligentie)")
        print("4. Eigen onderwerp")

        keuze = input("\nJouw keuze (1-4): ").strip()

        onderwerpen = {"1": "Ruimtevaart", "2": "Gaming", "3": "AI"}

        if keuze in onderwerpen:
            onderwerp = onderwerpen[keuze]
        elif keuze == "4":
            onderwerp = input("Voer je onderwerp in: ").strip() or "Ruimtevaart"
        else:
            onderwerp = "Ruimtevaart"

        rapport_pad = self.analyseer(onderwerp)

        print("\n" + "-" * 60)
        openen = input("Wil je het rapport openen in je browser? (j/n): ").lower().strip()

        if openen == "j":
            import webbrowser
            import os
            webbrowser.open(f"file://{os.path.abspath(rapport_pad)}")
            print("Rapport geopend in browser!")

        input("\nDruk op Enter om terug te gaan...")

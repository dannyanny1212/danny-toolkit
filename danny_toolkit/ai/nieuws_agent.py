"""
Nieuws Agent - Multi-agent nieuws analyse systeem v2.0.
Met sentiment analyse, samenvattingen en trending topics.
"""

import random
from pathlib import Path
from datetime import datetime, timedelta
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
    """Simuleert web search functionaliteit met uitgebreide nieuws database."""

    def __init__(self):
        self.nieuws_database = {
            "ruimtevaart": [
                {"bron": "SpaceNews.nl", "titel": "SpaceX lanceert nieuwe Starship raket",
                 "tekst": "SpaceX heeft vandaag succesvol een nieuwe Starship raket gelanceerd. Dit is een grote stap voorwaarts voor de Mars-missie.",
                 "datum": "2026-02-05", "betrouwbaar": True, "sentiment_hint": "positief"},
                {"bron": "NASA.gov", "titel": "Artemis III missie uitgesteld naar 2027",
                 "tekst": "NASA heeft de Artemis III maanmissie uitgesteld tot 2027 vanwege technische problemen met het landingsvoertuig.",
                 "datum": "2026-02-03", "betrouwbaar": True, "sentiment_hint": "negatief"},
                {"bron": "ESA.int", "titel": "Europa lanceert nieuwe satelliet",
                 "tekst": "De Europese ruimtevaartorganisatie ESA heeft succesvol een nieuwe aardobservatie satelliet gelanceerd.",
                 "datum": "2026-02-01", "betrouwbaar": True, "sentiment_hint": "positief"},
                {"bron": "SterrenKijker.nl", "titel": "Aliens landen volgende week",
                 "tekst": "Anonieme bronnen beweren dat buitenaardse wezens contact hebben gemaakt met de aarde.",
                 "datum": "2026-02-04", "betrouwbaar": False, "sentiment_hint": "neutraal"},
            ],
            "gaming": [
                {"bron": "IGN.com", "titel": "GTA 6 release datum bevestigd",
                 "tekst": "Rockstar Games bevestigt eindelijk: GTA 6 komt uit op 15 oktober 2026. Fans zijn enthousiast!",
                 "datum": "2026-02-05", "betrouwbaar": True, "sentiment_hint": "positief"},
                {"bron": "GameKrant.nl", "titel": "Nintendo kondigt Switch 2 aan",
                 "tekst": "Nintendo heeft de langverwachte Switch 2 aangekondigd met 8-inch OLED scherm en betere graphics.",
                 "datum": "2026-02-02", "betrouwbaar": True, "sentiment_hint": "positief"},
                {"bron": "Tweakers.net", "titel": "PlayStation 6 specificaties gelekt",
                 "tekst": "Documenten tonen aan dat de PS6 8K gaming zal ondersteunen met custom AMD chip.",
                 "datum": "2026-01-30", "betrouwbaar": True, "sentiment_hint": "neutraal"},
                {"bron": "GamerGerucht.net", "titel": "Half-Life 3 aangekondigd",
                 "tekst": "Anonieme bronnen beweren dat Valve Half-Life 3 binnenkort zal aankondigen.",
                 "datum": "2026-02-04", "betrouwbaar": False, "sentiment_hint": "neutraal"},
            ],
            "ai": [
                {"bron": "Anthropic.com", "titel": "Claude 5 aangekondigd met baanbrekende mogelijkheden",
                 "tekst": "Anthropic kondigt Claude 5 aan met 2 miljoen token context window en verbeterde reasoning.",
                 "datum": "2026-02-05", "betrouwbaar": True, "sentiment_hint": "positief"},
                {"bron": "TechCrunch.com", "titel": "OpenAI lanceert GPT-5",
                 "tekst": "OpenAI lanceert GPT-5 met verbeterde code-generatie en multimodale mogelijkheden.",
                 "datum": "2026-02-01", "betrouwbaar": True, "sentiment_hint": "positief"},
                {"bron": "Reuters.com", "titel": "EU stemt over AI-wetgeving",
                 "tekst": "Het Europees Parlement stemt volgende week over strenge nieuwe AI-regelgeving.",
                 "datum": "2026-02-03", "betrouwbaar": True, "sentiment_hint": "neutraal"},
                {"bron": "AITijdschrift.nl", "titel": "AI vervangt 50% van alle banen",
                 "tekst": "Sensationeel rapport claimt dat AI de helft van alle banen zal vervangen binnen 5 jaar.",
                 "datum": "2026-02-04", "betrouwbaar": False, "sentiment_hint": "negatief"},
            ],
            "sport": [
                {"bron": "NOS.nl", "titel": "Ajax wint met 4-0 van Feyenoord",
                 "tekst": "Ajax heeft de Klassieker gewonnen met een overtuigende 4-0 overwinning op Feyenoord.",
                 "datum": "2026-02-05", "betrouwbaar": True, "sentiment_hint": "positief"},
                {"bron": "AD.nl", "titel": "Max Verstappen pakt pole position",
                 "tekst": "Max Verstappen heeft wederom pole position gepakt voor de GP van Bahrein.",
                 "datum": "2026-02-04", "betrouwbaar": True, "sentiment_hint": "positief"},
                {"bron": "ESPN.com", "titel": "Nederlands elftal plaatst zich voor WK",
                 "tekst": "Oranje heeft zich geplaatst voor het WK 2026 na een spannende wedstrijd tegen Frankrijk.",
                 "datum": "2026-02-01", "betrouwbaar": True, "sentiment_hint": "positief"},
                {"bron": "SportRoddel.nl", "titel": "Bekende voetballer stopt ermee",
                 "tekst": "Geruchten suggereren dat een topspeler van Ajax zou stoppen met voetbal.",
                 "datum": "2026-02-03", "betrouwbaar": False, "sentiment_hint": "negatief"},
            ],
            "technologie": [
                {"bron": "TheVerge.com", "titel": "Apple onthult iPhone 18",
                 "tekst": "Apple heeft de iPhone 18 gepresenteerd met revolutionaire holografische display technologie.",
                 "datum": "2026-02-05", "betrouwbaar": True, "sentiment_hint": "positief"},
                {"bron": "Tweakers.net", "titel": "Samsung vouwbare tablet aangekondigd",
                 "tekst": "Samsung presenteert een nieuwe vouwbare tablet met 15-inch scherm wanneer uitgevouwen.",
                 "datum": "2026-02-03", "betrouwbaar": True, "sentiment_hint": "positief"},
                {"bron": "Wired.com", "titel": "Quantum computer doorbraak",
                 "tekst": "Onderzoekers claimen een grote doorbraak in quantum computing met 1000 stabiele qubits.",
                 "datum": "2026-02-01", "betrouwbaar": True, "sentiment_hint": "positief"},
                {"bron": "TechGerucht.nl", "titel": "Google stopt met Android",
                 "tekst": "Onbevestigde bronnen beweren dat Google zou stoppen met Android ontwikkeling.",
                 "datum": "2026-02-02", "betrouwbaar": False, "sentiment_hint": "negatief"},
            ],
            "wetenschap": [
                {"bron": "Nature.com", "titel": "Doorbraak in kankeronderzoek",
                 "tekst": "Wetenschappers hebben een nieuwe behandeling ontdekt die tumoren met 90% kan verkleinen.",
                 "datum": "2026-02-05", "betrouwbaar": True, "sentiment_hint": "positief"},
                {"bron": "Science.org", "titel": "Nieuw element ontdekt",
                 "tekst": "Onderzoekers van CERN hebben een nieuw superzwaar element ontdekt met atoomnummer 120.",
                 "datum": "2026-02-02", "betrouwbaar": True, "sentiment_hint": "positief"},
                {"bron": "NationalGeographic.com", "titel": "Nieuwe dinosaurus soort gevonden",
                 "tekst": "Paleontologen hebben in Argentinie een nieuwe grote dinosaurus soort ontdekt.",
                 "datum": "2026-01-28", "betrouwbaar": True, "sentiment_hint": "positief"},
                {"bron": "WetenschapWonder.nl", "titel": "Onsterfelijkheid binnen bereik",
                 "tekst": "Controversieel onderzoek claimt dat mensen binnen 10 jaar onsterfelijk kunnen worden.",
                 "datum": "2026-02-03", "betrouwbaar": False, "sentiment_hint": "neutraal"},
            ],
            "entertainment": [
                {"bron": "Variety.com", "titel": "Nieuwe Marvel film breekt records",
                 "tekst": "De nieuwe Avengers film heeft in het openingsweekend 500 miljoen dollar opgehaald.",
                 "datum": "2026-02-05", "betrouwbaar": True, "sentiment_hint": "positief"},
                {"bron": "Billboard.com", "titel": "Nederlandse artiest wint Grammy",
                 "tekst": "Een Nederlandse DJ heeft voor het eerst een Grammy gewonnen voor beste dance album.",
                 "datum": "2026-02-03", "betrouwbaar": True, "sentiment_hint": "positief"},
                {"bron": "Netflix.com", "titel": "Nieuwe Nederlandse serie groot succes",
                 "tekst": "De nieuwe Nederlandse Netflix serie staat op nummer 1 in 45 landen wereldwijd.",
                 "datum": "2026-02-01", "betrouwbaar": True, "sentiment_hint": "positief"},
                {"bron": "RoddelKrant.nl", "titel": "Bekende BN'er in schandaal",
                 "tekst": "Anonieme bronnen beweren dat een bekende Nederlander betrokken is bij fraude.",
                 "datum": "2026-02-04", "betrouwbaar": False, "sentiment_hint": "negatief"},
            ],
            "economie": [
                {"bron": "Bloomberg.com", "titel": "AEX bereikt record hoogte",
                 "tekst": "De Amsterdamse beurs heeft een nieuw record bereikt met de AEX boven de 1000 punten.",
                 "datum": "2026-02-05", "betrouwbaar": True, "sentiment_hint": "positief"},
                {"bron": "RTVNieuws.nl", "titel": "Inflatie daalt naar 2%",
                 "tekst": "De inflatie in Nederland is gedaald naar 2%, het laagste niveau in 3 jaar.",
                 "datum": "2026-02-03", "betrouwbaar": True, "sentiment_hint": "positief"},
                {"bron": "FD.nl", "titel": "Grote techbedrijf kondigt ontslagen aan",
                 "tekst": "Een groot technologiebedrijf heeft aangekondigd 10.000 banen te schrappen wereldwijd.",
                 "datum": "2026-02-01", "betrouwbaar": True, "sentiment_hint": "negatief"},
                {"bron": "CryptoNieuws.nl", "titel": "Bitcoin naar 1 miljoen",
                 "tekst": "Crypto-experts voorspellen dat Bitcoin binnen een jaar naar 1 miljoen dollar stijgt.",
                 "datum": "2026-02-02", "betrouwbaar": False, "sentiment_hint": "positief"},
            ],
        }

        # Trending topics (gesimuleerd)
        self.trending = [
            {"onderwerp": "AI", "mentions": 1250, "trend": "up"},
            {"onderwerp": "Technologie", "mentions": 980, "trend": "up"},
            {"onderwerp": "Sport", "mentions": 875, "trend": "stable"},
            {"onderwerp": "Gaming", "mentions": 720, "trend": "up"},
            {"onderwerp": "Wetenschap", "mentions": 650, "trend": "up"},
            {"onderwerp": "Entertainment", "mentions": 590, "trend": "down"},
            {"onderwerp": "Economie", "mentions": 480, "trend": "stable"},
            {"onderwerp": "Ruimtevaart", "mentions": 420, "trend": "up"},
        ]

    def zoek_nieuws(self, onderwerp: str) -> list:
        """Zoekt nieuws over een onderwerp."""
        onderwerp_lower = onderwerp.lower()

        for key in self.nieuws_database.keys():
            if key in onderwerp_lower or onderwerp_lower in key:
                return self.nieuws_database[key]

        # Fallback
        return self.nieuws_database.get("ai", [])

    def get_trending(self) -> list:
        """Geeft trending topics."""
        return self.trending


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

    def get_trending(self) -> list:
        """Haalt trending topics op."""
        self.log("Trending topics ophalen...")
        return self.web.get_trending()


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


class SentimentAgent(Agent):
    """Agent die sentiment analyse uitvoert."""

    # Sentiment woorden
    POSITIEF = ["succesvol", "gewonnen", "doorbraak", "record", "beste", "fantastisch",
                "geweldig", "verbeterd", "groei", "winst", "positief", "enthousiast",
                "revolutionair", "baanbrekend", "groot succes", "optimistisch"]
    NEGATIEF = ["uitgesteld", "probleem", "verlies", "daling", "schandaal", "fraude",
                "stopt", "mislukt", "crisis", "ontslagen", "negatief", "zorgen",
                "slecht", "gevaar", "risico", "verliezen"]

    def __init__(self):
        super().__init__("Sentiment", "[SENT]")

    def analyseer(self, artikelen: list) -> list:
        """Analyseert sentiment van artikelen."""
        self.log("Sentiment analyse uitvoeren...")

        resultaten = []
        for artikel in artikelen:
            tekst = (artikel["titel"] + " " + artikel["tekst"]).lower()

            positief_score = sum(1 for w in self.POSITIEF if w in tekst)
            negatief_score = sum(1 for w in self.NEGATIEF if w in tekst)

            if positief_score > negatief_score:
                sentiment = "POSITIEF"
                icon = "[+]"
            elif negatief_score > positief_score:
                sentiment = "NEGATIEF"
                icon = "[-]"
            else:
                sentiment = "NEUTRAAL"
                icon = "[=]"

            self.log(f"{icon} {artikel['bron']}: {sentiment}")
            resultaten.append({
                **artikel,
                "sentiment": sentiment,
                "positief_score": positief_score,
                "negatief_score": negatief_score
            })

        return resultaten


class SamenvatterAgent(Agent):
    """Agent die samenvattingen genereert."""

    def __init__(self):
        super().__init__("Samenvatter", "[SUM]")

    def vat_samen(self, artikelen: list, onderwerp: str) -> str:
        """Genereert een samenvatting van alle artikelen."""
        self.log("Samenvatting genereren...")

        betrouwbaar = [a for a in artikelen if a.get("status") == "BETROUWBAAR"]
        positief = [a for a in artikelen if a.get("sentiment") == "POSITIEF"]
        negatief = [a for a in artikelen if a.get("sentiment") == "NEGATIEF"]

        samenvatting = f"SAMENVATTING: {onderwerp.upper()}\n"
        samenvatting += "=" * 50 + "\n\n"

        samenvatting += f"Totaal {len(artikelen)} artikelen geanalyseerd.\n"
        samenvatting += f"- {len(betrouwbaar)} van betrouwbare bronnen\n"
        samenvatting += f"- {len(positief)} met positief sentiment\n"
        samenvatting += f"- {len(negatief)} met negatief sentiment\n\n"

        samenvatting += "BELANGRIJKSTE HEADLINES:\n"
        for artikel in betrouwbaar[:3]:
            sent_icon = {"POSITIEF": "+", "NEGATIEF": "-", "NEUTRAAL": "="}.get(
                artikel.get("sentiment", "NEUTRAAL"), "=")
            samenvatting += f"  [{sent_icon}] {artikel['titel']}\n"

        if positief:
            samenvatting += f"\nPOSITIEF NIEUWS: {positief[0]['titel']}\n"
        if negatief:
            samenvatting += f"AANDACHTSPUNT: {negatief[0]['titel']}\n"

        self.log("Samenvatting compleet!")
        return samenvatting


class SchrijverAgent(Agent):
    """Agent die het rapport schrijft."""

    def __init__(self):
        super().__init__("Schrijver", "[SCHRIJF]")

    def schrijf_rapport(self, onderwerp: str, artikelen: list, samenvatting: str) -> dict:
        """Schrijft een compleet rapport."""
        self.log("Rapport schrijven...")

        betrouwbaar = [a for a in artikelen if a.get("status") == "BETROUWBAAR"]
        onbetrouwbaar = [a for a in artikelen if a.get("status") == "ONBETROUWBAAR"]
        positief = [a for a in artikelen if a.get("sentiment") == "POSITIEF"]
        negatief = [a for a in artikelen if a.get("sentiment") == "NEGATIEF"]
        neutraal = [a for a in artikelen if a.get("sentiment") == "NEUTRAAL"]

        rapport = {
            "onderwerp": onderwerp,
            "datum": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "samenvatting": samenvatting,
            "statistieken": {
                "totaal": len(artikelen),
                "betrouwbaar": len(betrouwbaar),
                "onbetrouwbaar": len(onbetrouwbaar),
                "positief": len(positief),
                "negatief": len(negatief),
                "neutraal": len(neutraal),
            },
            "betrouwbare_artikelen": betrouwbaar,
            "onbetrouwbare_artikelen": onbetrouwbaar,
            "actiepunten": [
                f"Blijf de ontwikkelingen rond {onderwerp} volgen",
                "Verifieer altijd nieuwsbronnen voor het delen",
                "Let op sentiment bias in berichtgeving",
                "Wees kritisch over sensationele claims"
            ]
        }

        self.log(f"Rapport compleet: {len(betrouwbaar)} betrouwbare bronnen")
        return rapport


class RapportGeneratorAgent(Agent):
    """Agent die het rapport als HTML bestand genereert."""

    def __init__(self):
        super().__init__("Generator", "[GEN]")
        Config.ensure_dirs()
        self.output_map = Config.RAPPORTEN_DIR

    def genereer(self, rapport: dict) -> str:
        """Genereert een uitgebreid HTML rapport."""
        self.log("HTML rapport genereren...")

        stats = rapport["statistieken"]

        html = f"""<!DOCTYPE html>
<html lang="nl">
<head>
    <meta charset="UTF-8">
    <title>Nieuws Rapport: {rapport['onderwerp']}</title>
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; max-width: 900px; margin: 40px auto; padding: 20px; background: #f5f5f5; }}
        .container {{ background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }}
        h2 {{ color: #34495e; margin-top: 30px; }}
        .stats {{ display: flex; flex-wrap: wrap; gap: 15px; margin: 20px 0; }}
        .stat-box {{ background: #ecf0f1; padding: 15px 25px; border-radius: 8px; text-align: center; }}
        .stat-box.positief {{ background: #d5f5e3; border-left: 4px solid #27ae60; }}
        .stat-box.negatief {{ background: #fadbd8; border-left: 4px solid #e74c3c; }}
        .stat-box h3 {{ margin: 0; font-size: 24px; }}
        .stat-box p {{ margin: 5px 0 0 0; color: #666; }}
        .artikel {{ border-left: 4px solid #3498db; padding: 15px; margin: 15px 0; background: #f9f9f9; border-radius: 0 8px 8px 0; }}
        .artikel.onbetrouwbaar {{ border-left-color: #e74c3c; background: #fdf2f2; }}
        .artikel.positief {{ border-left-color: #27ae60; }}
        .artikel.negatief {{ border-left-color: #e74c3c; }}
        .sentiment {{ display: inline-block; padding: 3px 10px; border-radius: 12px; font-size: 12px; margin-left: 10px; }}
        .sentiment.positief {{ background: #27ae60; color: white; }}
        .sentiment.negatief {{ background: #e74c3c; color: white; }}
        .sentiment.neutraal {{ background: #95a5a6; color: white; }}
        .samenvatting {{ background: #eaf2f8; padding: 20px; border-radius: 8px; white-space: pre-line; font-family: monospace; }}
    </style>
</head>
<body>
<div class="container">
    <h1>Nieuws Rapport: {rapport['onderwerp'].title()}</h1>
    <p>Gegenereerd op: {rapport['datum']}</p>

    <div class="stats">
        <div class="stat-box"><h3>{stats['totaal']}</h3><p>Artikelen</p></div>
        <div class="stat-box"><h3>{stats['betrouwbaar']}</h3><p>Betrouwbaar</p></div>
        <div class="stat-box positief"><h3>{stats['positief']}</h3><p>Positief</p></div>
        <div class="stat-box negatief"><h3>{stats['negatief']}</h3><p>Negatief</p></div>
        <div class="stat-box"><h3>{stats['neutraal']}</h3><p>Neutraal</p></div>
    </div>

    <h2>Samenvatting</h2>
    <div class="samenvatting">{rapport['samenvatting']}</div>

    <h2>Betrouwbare Bronnen ({len(rapport['betrouwbare_artikelen'])})</h2>
"""
        for artikel in rapport["betrouwbare_artikelen"]:
            sentiment = artikel.get("sentiment", "NEUTRAAL").lower()
            html += f'''<div class="artikel {sentiment}">
                <strong>{artikel["bron"]}</strong>
                <span class="sentiment {sentiment}">{artikel.get("sentiment", "?")}</span>
                <br><b>{artikel["titel"]}</b>
                <br><small>{artikel["tekst"]}</small>
                <br><small style="color:#888">Datum: {artikel["datum"]}</small>
            </div>\n'''

        if rapport["onbetrouwbare_artikelen"]:
            html += f'<h2>Onbetrouwbare Bronnen ({len(rapport["onbetrouwbare_artikelen"])})</h2>\n'
            for artikel in rapport["onbetrouwbare_artikelen"]:
                html += f'''<div class="artikel onbetrouwbaar">
                    <strong>{artikel["bron"]}</strong>
                    <span class="sentiment neutraal">NIET GEVERIFIEERD</span>
                    <br><b>{artikel["titel"]}</b>
                    <br><small style="color:#c0392b">LET OP: Niet geverifieerd - wees kritisch!</small>
                </div>\n'''

        html += """
    <h2>Actiepunten</h2>
    <ul>
"""
        for punt in rapport["actiepunten"]:
            html += f"        <li>{punt}</li>\n"

        html += """    </ul>
</div>
</body>
</html>"""

        bestandsnaam = f"nieuws_{rapport['onderwerp'].lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        pad = self.output_map / bestandsnaam

        with open(pad, "w", encoding="utf-8") as f:
            f.write(html)

        self.log(f"Rapport opgeslagen: {pad}")
        return str(pad)


class NieuwsAgentApp:
    """Nieuws Agent orchestrator v2.0."""

    ONDERWERPEN = {
        "1": "Ruimtevaart",
        "2": "Gaming",
        "3": "AI",
        "4": "Sport",
        "5": "Technologie",
        "6": "Wetenschap",
        "7": "Entertainment",
        "8": "Economie",
    }

    def __init__(self):
        self.zoeker = ZoekerAgent()
        self.feitenchecker = FeitencheckerAgent()
        self.sentiment_agent = SentimentAgent()
        self.samenvatter = SamenvatterAgent()
        self.schrijver = SchrijverAgent()
        self.generator = RapportGeneratorAgent()

    def toon_trending(self):
        """Toont trending topics."""
        print("\n" + "=" * 50)
        print("TRENDING TOPICS")
        print("=" * 50)

        trending = self.zoeker.get_trending()
        for i, topic in enumerate(trending, 1):
            trend_icon = {"up": "[^]", "down": "[v]", "stable": "[-]"}.get(topic["trend"], "[-]")
            print(f"  {i}. {topic['onderwerp']}: {topic['mentions']} mentions {trend_icon}")

    def analyseer(self, onderwerp: str) -> str:
        """Voert de complete nieuws-analyse uit met alle agents."""
        print("\n" + "=" * 60)
        print("NIEUWS-AGENT v2.0")
        print("=" * 60)
        print(f"\nOnderwerp: {onderwerp}")
        print(f"Datum: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

        # Stap 1: Verzamelen
        print("\n" + "-" * 40)
        print("STAP 1: INFORMATIE VERZAMELEN")
        print("-" * 40)
        artikelen = self.zoeker.verzamel(onderwerp)

        # Stap 2: Feiten checken
        print("\n" + "-" * 40)
        print("STAP 2: FEITEN CONTROLEREN")
        print("-" * 40)
        artikelen = self.feitenchecker.controleer(artikelen)

        # Stap 3: Sentiment analyse
        print("\n" + "-" * 40)
        print("STAP 3: SENTIMENT ANALYSE")
        print("-" * 40)
        artikelen = self.sentiment_agent.analyseer(artikelen)

        # Stap 4: Samenvatting
        print("\n" + "-" * 40)
        print("STAP 4: SAMENVATTING GENEREREN")
        print("-" * 40)
        samenvatting = self.samenvatter.vat_samen(artikelen, onderwerp)

        # Stap 5: Rapport schrijven
        print("\n" + "-" * 40)
        print("STAP 5: RAPPORT SCHRIJVEN")
        print("-" * 40)
        rapport = self.schrijver.schrijf_rapport(onderwerp, artikelen, samenvatting)

        # Stap 6: HTML genereren
        print("\n" + "-" * 40)
        print("STAP 6: HTML RAPPORT GENEREREN")
        print("-" * 40)
        rapport_pad = self.generator.genereer(rapport)

        # Resultaten
        print("\n" + "=" * 60)
        print("[OK] NIEUWS-AGENT COMPLEET!")
        print("=" * 60)

        stats = rapport["statistieken"]
        print(f"\nResultaten:")
        print(f"   Artikelen gevonden:  {stats['totaal']}")
        print(f"   Betrouwbaar:         {stats['betrouwbaar']}")
        print(f"   Onbetrouwbaar:       {stats['onbetrouwbaar']}")
        print(f"\nSentiment:")
        print(f"   [+] Positief:        {stats['positief']}")
        print(f"   [-] Negatief:        {stats['negatief']}")
        print(f"   [=] Neutraal:        {stats['neutraal']}")
        print(f"\nRapport: {rapport_pad}")

        return rapport_pad

    def run(self):
        """Start de interactieve nieuws agent."""
        clear_scherm()
        print("\n" + "=" * 55)
        print("   NIEUWS-AGENT v2.0: Multi-Agent Nieuws Analyse")
        print("   Met sentiment analyse, samenvattingen & trending!")
        print("=" * 55)

        # Toon trending topics
        self.toon_trending()

        print("\n" + "-" * 55)
        print("Kies een onderwerp:")
        for num, naam in self.ONDERWERPEN.items():
            print(f"  {num}. {naam}")
        print("  9. Eigen onderwerp")

        keuze = input("\nJouw keuze (1-9): ").strip()

        if keuze in self.ONDERWERPEN:
            onderwerp = self.ONDERWERPEN[keuze]
        elif keuze == "9":
            onderwerp = input("Voer je onderwerp in: ").strip() or "AI"
        else:
            onderwerp = "AI"

        rapport_pad = self.analyseer(onderwerp)

        print("\n" + "-" * 60)
        openen = input("Wil je het rapport openen in je browser? (j/n): ").lower().strip()

        if openen == "j":
            import webbrowser
            import os
            webbrowser.open(f"file://{os.path.abspath(rapport_pad)}")
            print("Rapport geopend in browser!")

        input("\nDruk op Enter om terug te gaan...")

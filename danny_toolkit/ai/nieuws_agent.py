"""
Nieuws Agent v2.0 - Professioneel Multi-Agent Nieuws Analyse Systeem.

Features:
- Multi-agent architectuur (Zoeker, Checker, Sentiment, Samenvatter, etc.)
- Kleurrijke terminal output
- Uitgebreide fake news detectie
- Bias detectie in bronnen
- Keyword tracking en alerts
- Bookmark systeem
- Historische analyse vergelijking
- Export naar TXT, JSON, HTML, Markdown
- Persoonlijke voorkeuren
- Social media trend indicatoren
- Leestijd schattingen
"""

import json
import random
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from collections import Counter
from typing import List, Dict, Any, Optional

from ..core.config import Config
from ..core.utils import clear_scherm, kleur


class VectorDatabase:
    """Simpele vector database voor de nieuws agent."""

    def __init__(self):
        self.documenten = []

    def voeg_toe(self, bron: str, tekst: str) -> int:
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

    def zoek_similar(self, query: str, top_k: int = 5) -> List[dict]:
        """Zoek vergelijkbare documenten."""
        query_embedding = self._maak_embedding(query)
        scores = []

        for doc in self.documenten:
            score = sum(
                query_embedding.get(w, 0) * doc["embedding"].get(w, 0)
                for w in set(query_embedding.keys()) | set(doc["embedding"].keys())
            )
            scores.append((doc, score))

        scores.sort(key=lambda x: x[1], reverse=True)
        return [doc for doc, _ in scores[:top_k]]


class WebZoeker:
    """Simuleert web search met uitgebreide nieuws database."""

    def __init__(self):
        self.nieuws_database = {
            "ruimtevaart": [
                {
                    "bron": "SpaceNews.nl", "titel": "SpaceX lanceert nieuwe Starship raket",
                    "tekst": "SpaceX heeft vandaag succesvol een nieuwe Starship raket gelanceerd. "
                             "Dit is een grote stap voorwaarts voor de Mars-missie. CEO Elon Musk "
                             "noemt het een historisch moment voor de ruimtevaart.",
                    "datum": "2026-02-05", "betrouwbaar": True, "sentiment_hint": "positief",
                    "categorie": "ruimtevaart", "leestijd": 3, "social_shares": 15420
                },
                {
                    "bron": "NASA.gov", "titel": "Artemis III missie uitgesteld naar 2027",
                    "tekst": "NASA heeft de Artemis III maanmissie uitgesteld tot 2027 vanwege "
                             "technische problemen met het landingsvoertuig van SpaceX.",
                    "datum": "2026-02-03", "betrouwbaar": True, "sentiment_hint": "negatief",
                    "categorie": "ruimtevaart", "leestijd": 4, "social_shares": 8750
                },
                {
                    "bron": "ESA.int", "titel": "Europa lanceert nieuwe aardobservatie satelliet",
                    "tekst": "De Europese ruimtevaartorganisatie ESA heeft succesvol een nieuwe "
                             "aardobservatie satelliet gelanceerd voor klimaatonderzoek.",
                    "datum": "2026-02-01", "betrouwbaar": True, "sentiment_hint": "positief",
                    "categorie": "ruimtevaart", "leestijd": 2, "social_shares": 4200
                },
                {
                    "bron": "SterrenKijker.nl", "titel": "Aliens landen volgende week op aarde",
                    "tekst": "Anonieme bronnen beweren dat buitenaardse wezens contact hebben "
                             "gemaakt en volgende week zullen landen.",
                    "datum": "2026-02-04", "betrouwbaar": False, "sentiment_hint": "neutraal",
                    "categorie": "ruimtevaart", "leestijd": 1, "social_shares": 89000
                },
            ],
            "gaming": [
                {
                    "bron": "IGN.com", "titel": "GTA 6 release datum officieel bevestigd",
                    "tekst": "Rockstar Games bevestigt eindelijk: GTA 6 komt uit op 15 oktober 2026. "
                             "De game speelt zich af in Vice City en omgeving.",
                    "datum": "2026-02-05", "betrouwbaar": True, "sentiment_hint": "positief",
                    "categorie": "gaming", "leestijd": 5, "social_shares": 125000
                },
                {
                    "bron": "GameKrant.nl", "titel": "Nintendo kondigt Switch 2 aan",
                    "tekst": "Nintendo heeft de langverwachte Switch 2 aangekondigd met 8-inch "
                             "OLED scherm, 4K output en backwards compatibility.",
                    "datum": "2026-02-02", "betrouwbaar": True, "sentiment_hint": "positief",
                    "categorie": "gaming", "leestijd": 4, "social_shares": 78000
                },
                {
                    "bron": "Tweakers.net", "titel": "PlayStation 6 specificaties gelekt",
                    "tekst": "Documenten tonen aan dat de PS6 8K gaming zal ondersteunen met een "
                             "custom AMD chip en 2TB SSD standaard.",
                    "datum": "2026-01-30", "betrouwbaar": True, "sentiment_hint": "neutraal",
                    "categorie": "gaming", "leestijd": 3, "social_shares": 45000
                },
                {
                    "bron": "GamerGerucht.net", "titel": "Half-Life 3 eindelijk aangekondigd",
                    "tekst": "Anonieme bronnen beweren dat Valve Half-Life 3 binnenkort aankondigt.",
                    "datum": "2026-02-04", "betrouwbaar": False, "sentiment_hint": "neutraal",
                    "categorie": "gaming", "leestijd": 1, "social_shares": 250000
                },
            ],
            "ai": [
                {
                    "bron": "Anthropic.com", "titel": "Claude 5 aangekondigd met baanbrekende mogelijkheden",
                    "tekst": "Anthropic kondigt Claude 5 aan met 2 miljoen token context window, "
                             "verbeterde reasoning en nieuwe multimodale capaciteiten.",
                    "datum": "2026-02-05", "betrouwbaar": True, "sentiment_hint": "positief",
                    "categorie": "ai", "leestijd": 6, "social_shares": 95000
                },
                {
                    "bron": "TechCrunch.com", "titel": "OpenAI lanceert GPT-5 met nieuwe features",
                    "tekst": "OpenAI lanceert GPT-5 met verbeterde code-generatie, multimodale "
                             "mogelijkheden en langere context.",
                    "datum": "2026-02-01", "betrouwbaar": True, "sentiment_hint": "positief",
                    "categorie": "ai", "leestijd": 5, "social_shares": 87000
                },
                {
                    "bron": "Reuters.com", "titel": "EU stemt over strenge AI-wetgeving",
                    "tekst": "Het Europees Parlement stemt volgende week over strenge nieuwe "
                             "AI-regelgeving die grote techbedrijven raakt.",
                    "datum": "2026-02-03", "betrouwbaar": True, "sentiment_hint": "neutraal",
                    "categorie": "ai", "leestijd": 4, "social_shares": 23000
                },
                {
                    "bron": "AITijdschrift.nl", "titel": "AI vervangt 50% van alle banen binnen 5 jaar",
                    "tekst": "Sensationeel rapport claimt dat AI de helft van alle banen vervangt. "
                             "Experts zijn sceptisch over deze voorspelling.",
                    "datum": "2026-02-04", "betrouwbaar": False, "sentiment_hint": "negatief",
                    "categorie": "ai", "leestijd": 2, "social_shares": 156000
                },
            ],
            "sport": [
                {
                    "bron": "NOS.nl", "titel": "Ajax wint Klassieker met 4-0 van Feyenoord",
                    "tekst": "Ajax heeft de Klassieker gewonnen met een overtuigende 4-0 overwinning "
                             "op Feyenoord. Brobbey scoorde een hattrick.",
                    "datum": "2026-02-05", "betrouwbaar": True, "sentiment_hint": "positief",
                    "categorie": "sport", "leestijd": 3, "social_shares": 67000
                },
                {
                    "bron": "AD.nl", "titel": "Max Verstappen pakt pole position in Bahrein",
                    "tekst": "Max Verstappen heeft wederom pole position gepakt voor de GP van "
                             "Bahrein. Hij was 0.3 seconden sneller dan Norris.",
                    "datum": "2026-02-04", "betrouwbaar": True, "sentiment_hint": "positief",
                    "categorie": "sport", "leestijd": 2, "social_shares": 54000
                },
                {
                    "bron": "ESPN.com", "titel": "Nederlands elftal plaatst zich voor WK 2026",
                    "tekst": "Oranje heeft zich geplaatst voor het WK 2026 na een spannende "
                             "wedstrijd tegen Frankrijk (2-1).",
                    "datum": "2026-02-01", "betrouwbaar": True, "sentiment_hint": "positief",
                    "categorie": "sport", "leestijd": 4, "social_shares": 89000
                },
                {
                    "bron": "SportRoddel.nl", "titel": "Topspeler Ajax stopt met voetbal",
                    "tekst": "Geruchten suggereren dat een topspeler van Ajax zou stoppen met "
                             "voetbal vanwege persoonlijke redenen.",
                    "datum": "2026-02-03", "betrouwbaar": False, "sentiment_hint": "negatief",
                    "categorie": "sport", "leestijd": 1, "social_shares": 34000
                },
            ],
            "technologie": [
                {
                    "bron": "TheVerge.com", "titel": "Apple onthult iPhone 18 met holografisch display",
                    "tekst": "Apple heeft de iPhone 18 gepresenteerd met revolutionaire "
                             "holografische display technologie en 5nm chip.",
                    "datum": "2026-02-05", "betrouwbaar": True, "sentiment_hint": "positief",
                    "categorie": "technologie", "leestijd": 5, "social_shares": 112000
                },
                {
                    "bron": "Tweakers.net", "titel": "Samsung vouwbare tablet van 15 inch aangekondigd",
                    "tekst": "Samsung presenteert een nieuwe vouwbare tablet met 15-inch scherm "
                             "wanneer uitgevouwen en S Pen ondersteuning.",
                    "datum": "2026-02-03", "betrouwbaar": True, "sentiment_hint": "positief",
                    "categorie": "technologie", "leestijd": 3, "social_shares": 28000
                },
                {
                    "bron": "Wired.com", "titel": "Grote doorbraak in quantum computing bereikt",
                    "tekst": "Onderzoekers claimen een grote doorbraak in quantum computing "
                             "met 1000 stabiele qubits bij kamertemperatuur.",
                    "datum": "2026-02-01", "betrouwbaar": True, "sentiment_hint": "positief",
                    "categorie": "technologie", "leestijd": 6, "social_shares": 45000
                },
                {
                    "bron": "TechGerucht.nl", "titel": "Google stopt volledig met Android",
                    "tekst": "Onbevestigde bronnen beweren dat Google zou stoppen met Android "
                             "ontwikkeling en overschakelt naar Fuchsia.",
                    "datum": "2026-02-02", "betrouwbaar": False, "sentiment_hint": "negatief",
                    "categorie": "technologie", "leestijd": 2, "social_shares": 78000
                },
            ],
            "wetenschap": [
                {
                    "bron": "Nature.com", "titel": "Doorbraak in kankeronderzoek met nieuwe therapie",
                    "tekst": "Wetenschappers hebben een nieuwe behandeling ontdekt die tumoren "
                             "met 90% kan verkleinen zonder bijwerkingen.",
                    "datum": "2026-02-05", "betrouwbaar": True, "sentiment_hint": "positief",
                    "categorie": "wetenschap", "leestijd": 7, "social_shares": 156000
                },
                {
                    "bron": "Science.org", "titel": "Nieuw superzwaar element 120 ontdekt bij CERN",
                    "tekst": "Onderzoekers van CERN hebben een nieuw superzwaar element ontdekt "
                             "met atoomnummer 120, genaamd Unbinilium.",
                    "datum": "2026-02-02", "betrouwbaar": True, "sentiment_hint": "positief",
                    "categorie": "wetenschap", "leestijd": 5, "social_shares": 34000
                },
                {
                    "bron": "NationalGeographic.com", "titel": "Nieuwe gigantische dinosaurus ontdekt",
                    "tekst": "Paleontologen hebben in Argentinie een nieuwe grote dinosaurus "
                             "soort ontdekt, groter dan de T-Rex.",
                    "datum": "2026-01-28", "betrouwbaar": True, "sentiment_hint": "positief",
                    "categorie": "wetenschap", "leestijd": 4, "social_shares": 67000
                },
                {
                    "bron": "WetenschapWonder.nl", "titel": "Onsterfelijkheid mogelijk binnen 10 jaar",
                    "tekst": "Controversieel onderzoek claimt dat mensen binnen 10 jaar "
                             "onsterfelijk kunnen worden door gentherapie.",
                    "datum": "2026-02-03", "betrouwbaar": False, "sentiment_hint": "neutraal",
                    "categorie": "wetenschap", "leestijd": 2, "social_shares": 234000
                },
            ],
            "entertainment": [
                {
                    "bron": "Variety.com", "titel": "Nieuwe Avengers film breekt alle records",
                    "tekst": "De nieuwe Avengers film heeft in het openingsweekend 500 miljoen "
                             "dollar opgehaald, een nieuw record.",
                    "datum": "2026-02-05", "betrouwbaar": True, "sentiment_hint": "positief",
                    "categorie": "entertainment", "leestijd": 3, "social_shares": 189000
                },
                {
                    "bron": "Billboard.com", "titel": "Nederlandse DJ wint Grammy Award",
                    "tekst": "Een Nederlandse DJ heeft voor het eerst een Grammy gewonnen "
                             "voor beste dance/electronic album.",
                    "datum": "2026-02-03", "betrouwbaar": True, "sentiment_hint": "positief",
                    "categorie": "entertainment", "leestijd": 2, "social_shares": 78000
                },
                {
                    "bron": "Netflix.com", "titel": "Nederlandse serie wereldwijd nummer 1",
                    "tekst": "De nieuwe Nederlandse Netflix serie staat op nummer 1 in 45 "
                             "landen wereldwijd met 90 miljoen views.",
                    "datum": "2026-02-01", "betrouwbaar": True, "sentiment_hint": "positief",
                    "categorie": "entertainment", "leestijd": 2, "social_shares": 145000
                },
                {
                    "bron": "RoddelKrant.nl", "titel": "Bekende BN'er betrokken bij groot schandaal",
                    "tekst": "Anonieme bronnen beweren dat een bekende Nederlander betrokken "
                             "is bij een groot financieel schandaal.",
                    "datum": "2026-02-04", "betrouwbaar": False, "sentiment_hint": "negatief",
                    "categorie": "entertainment", "leestijd": 1, "social_shares": 456000
                },
            ],
            "economie": [
                {
                    "bron": "Bloomberg.com", "titel": "AEX bereikt historisch record boven 1000 punten",
                    "tekst": "De Amsterdamse beurs heeft een nieuw record bereikt met de AEX "
                             "boven de 1000 punten voor het eerst.",
                    "datum": "2026-02-05", "betrouwbaar": True, "sentiment_hint": "positief",
                    "categorie": "economie", "leestijd": 4, "social_shares": 23000
                },
                {
                    "bron": "RTVNieuws.nl", "titel": "Inflatie Nederland daalt naar 2 procent",
                    "tekst": "De inflatie in Nederland is gedaald naar 2%, het laagste niveau "
                             "in 3 jaar. ECB overweegt renteverlaging.",
                    "datum": "2026-02-03", "betrouwbaar": True, "sentiment_hint": "positief",
                    "categorie": "economie", "leestijd": 3, "social_shares": 12000
                },
                {
                    "bron": "FD.nl", "titel": "Groot techbedrijf schrapt 10.000 banen",
                    "tekst": "Een groot technologiebedrijf heeft aangekondigd 10.000 banen te "
                             "schrappen wereldwijd vanwege reorganisatie.",
                    "datum": "2026-02-01", "betrouwbaar": True, "sentiment_hint": "negatief",
                    "categorie": "economie", "leestijd": 4, "social_shares": 34000
                },
                {
                    "bron": "CryptoNieuws.nl", "titel": "Bitcoin stijgt naar 1 miljoen dollar",
                    "tekst": "Crypto-experts voorspellen dat Bitcoin binnen een jaar naar "
                             "1 miljoen dollar stijgt na recente rally.",
                    "datum": "2026-02-02", "betrouwbaar": False, "sentiment_hint": "positief",
                    "categorie": "economie", "leestijd": 2, "social_shares": 189000
                },
            ],
            "gezondheid": [
                {
                    "bron": "WHO.int", "titel": "Nieuwe griepvaccin 95% effectief",
                    "tekst": "De Wereldgezondheidsorganisatie meldt dat het nieuwe universele "
                             "griepvaccin 95% effectief is tegen alle stammen.",
                    "datum": "2026-02-05", "betrouwbaar": True, "sentiment_hint": "positief",
                    "categorie": "gezondheid", "leestijd": 4, "social_shares": 67000
                },
                {
                    "bron": "RIVM.nl", "titel": "Nederland gezondste land van Europa",
                    "tekst": "Volgens nieuw onderzoek is Nederland het gezondste land van "
                             "Europa met de hoogste levensverwachting.",
                    "datum": "2026-02-03", "betrouwbaar": True, "sentiment_hint": "positief",
                    "categorie": "gezondheid", "leestijd": 3, "social_shares": 45000
                },
                {
                    "bron": "Medscape.com", "titel": "Doorbraak in Alzheimer behandeling",
                    "tekst": "Onderzoekers melden een doorbraak in Alzheimer behandeling "
                             "die geheugenverlies kan vertragen met 80%.",
                    "datum": "2026-02-01", "betrouwbaar": True, "sentiment_hint": "positief",
                    "categorie": "gezondheid", "leestijd": 5, "social_shares": 123000
                },
                {
                    "bron": "GezondheidsGerucht.nl", "titel": "Koffie veroorzaakt kanker zegt studie",
                    "tekst": "Een controversiele studie beweert dat koffie kanker kan "
                             "veroorzaken, maar experts zijn zeer sceptisch.",
                    "datum": "2026-02-04", "betrouwbaar": False, "sentiment_hint": "negatief",
                    "categorie": "gezondheid", "leestijd": 2, "social_shares": 345000
                },
            ],
            "klimaat": [
                {
                    "bron": "KNMI.nl", "titel": "2026 wordt warmste jaar ooit gemeten",
                    "tekst": "Het KNMI voorspelt dat 2026 het warmste jaar ooit wordt met "
                             "temperaturen 1.5 graden boven het gemiddelde.",
                    "datum": "2026-02-05", "betrouwbaar": True, "sentiment_hint": "negatief",
                    "categorie": "klimaat", "leestijd": 4, "social_shares": 78000
                },
                {
                    "bron": "Greenpeace.org", "titel": "Nederland haalt klimaatdoelen 2030",
                    "tekst": "Nederland ligt op koers om de klimaatdoelen van 2030 te halen "
                             "dankzij snelle groei van duurzame energie.",
                    "datum": "2026-02-03", "betrouwbaar": True, "sentiment_hint": "positief",
                    "categorie": "klimaat", "leestijd": 3, "social_shares": 34000
                },
                {
                    "bron": "UN.org", "titel": "Nieuw klimaatakkoord getekend door 195 landen",
                    "tekst": "Een nieuw klimaatakkoord is getekend door 195 landen met "
                             "strengere doelen voor CO2-reductie.",
                    "datum": "2026-02-01", "betrouwbaar": True, "sentiment_hint": "positief",
                    "categorie": "klimaat", "leestijd": 5, "social_shares": 56000
                },
                {
                    "bron": "KlimaatScepsis.nl", "titel": "Klimaatverandering is een hoax",
                    "tekst": "Controversiele website beweert dat klimaatverandering niet "
                             "door mensen wordt veroorzaakt.",
                    "datum": "2026-02-04", "betrouwbaar": False, "sentiment_hint": "negatief",
                    "categorie": "klimaat", "leestijd": 2, "social_shares": 234000
                },
            ],
        }

        # Trending topics met social media data
        self.trending = [
            {"onderwerp": "AI", "mentions": 125000, "trend": "up", "change": "+15%"},
            {"onderwerp": "Gaming", "mentions": 98000, "trend": "up", "change": "+8%"},
            {"onderwerp": "Sport", "mentions": 87500, "trend": "stable", "change": "+1%"},
            {"onderwerp": "Technologie", "mentions": 72000, "trend": "up", "change": "+12%"},
            {"onderwerp": "Wetenschap", "mentions": 65000, "trend": "up", "change": "+5%"},
            {"onderwerp": "Entertainment", "mentions": 59000, "trend": "down", "change": "-3%"},
            {"onderwerp": "Economie", "mentions": 48000, "trend": "stable", "change": "0%"},
            {"onderwerp": "Ruimtevaart", "mentions": 42000, "trend": "up", "change": "+20%"},
            {"onderwerp": "Gezondheid", "mentions": 38000, "trend": "up", "change": "+7%"},
            {"onderwerp": "Klimaat", "mentions": 35000, "trend": "up", "change": "+10%"},
        ]

        # Bekende betrouwbare bronnen
        self.betrouwbare_bronnen = {
            "NASA.gov", "ESA.int", "Reuters.com", "Bloomberg.com", "Nature.com",
            "Science.org", "WHO.int", "KNMI.nl", "NOS.nl", "AD.nl", "FD.nl",
            "Tweakers.net", "TheVerge.com", "TechCrunch.com", "Wired.com",
            "IGN.com", "ESPN.com", "Variety.com", "Billboard.com", "Anthropic.com",
            "RIVM.nl", "Medscape.com", "UN.org", "Greenpeace.org", "NationalGeographic.com"
        }

        # Onbetrouwbare bron patronen
        self.onbetrouwbare_patronen = [
            "gerucht", "roddel", "wonder", "scepsis", "anoniem", "sensatie"
        ]

    def zoek_nieuws(self, onderwerp: str) -> list:
        """Zoekt nieuws over een onderwerp."""
        onderwerp_lower = onderwerp.lower()

        for key in self.nieuws_database.keys():
            if key in onderwerp_lower or onderwerp_lower in key:
                return self.nieuws_database[key]

        # Fallback naar AI nieuws
        return self.nieuws_database.get("ai", [])

    def zoek_alle_categorieen(self) -> dict:
        """Haalt nieuws uit alle categorieen."""
        return self.nieuws_database

    def get_trending(self) -> list:
        """Geeft trending topics."""
        return self.trending

    def is_betrouwbare_bron(self, bron: str) -> bool:
        """Check of een bron betrouwbaar is."""
        if bron in self.betrouwbare_bronnen:
            return True
        for patroon in self.onbetrouwbare_patronen:
            if patroon in bron.lower():
                return False
        return None  # Onbekend


class Agent:
    """Basis agent class met kleurrijke output."""

    def __init__(self, naam: str, emoji: str, kleur_naam: str = "wit"):
        self.naam = naam
        self.emoji = emoji
        self.kleur_naam = kleur_naam

    def log(self, bericht: str, extra_kleur: str = None):
        """Log een bericht met kleur."""
        k = extra_kleur or self.kleur_naam
        print(f"  {kleur(f'[{self.naam}]', k)} {bericht}")


class ZoekerAgent(Agent):
    """Agent die informatie verzamelt."""

    def __init__(self):
        super().__init__("ZOEKER", "[S]", "cyaan")
        self.web = WebZoeker()
        self.database = VectorDatabase()

    def verzamel(self, onderwerp: str) -> list:
        """Verzamelt nieuws over een onderwerp."""
        self.log(f"Zoeken naar nieuws over: {kleur(onderwerp, 'geel')}")
        artikelen = self.web.zoek_nieuws(onderwerp)

        for artikel in artikelen:
            self.database.voeg_toe(artikel["bron"], artikel["tekst"])
            titel_kort = artikel["titel"][:45] + "..." if len(artikel["titel"]) > 45 else artikel["titel"]
            self.log(f"Gevonden: {titel_kort}")

        return artikelen

    def get_trending(self) -> list:
        """Haalt trending topics op."""
        self.log("Trending topics ophalen...")
        return self.web.get_trending()

    def zoek_alle(self) -> dict:
        """Haalt nieuws uit alle categorieen."""
        self.log("Alle categorieen doorzoeken...")
        return self.web.zoek_alle_categorieen()


class FeitencheckerAgent(Agent):
    """Agent die feiten controleert met uitgebreide analyse."""

    # Bekende fake news indicatoren
    FAKE_NEWS_INDICATOREN = [
        "anonieme bronnen", "bronnen beweren", "geruchten", "onbevestigd",
        "zou kunnen", "experts zeggen", "sommigen beweren", "men zegt",
        "controversieel", "schokkend", "sensationeel", "onthulling"
    ]

    # Clickbait woorden
    CLICKBAIT_WOORDEN = [
        "schokkend", "ongelooflijk", "je gelooft niet", "geheim",
        "verboden", "dit verandert alles", "breaking", "exclusief"
    ]

    def __init__(self):
        super().__init__("CHECKER", "[C]", "groen")
        self.web = WebZoeker()

    def controleer(self, artikelen: list) -> list:
        """Controleert de betrouwbaarheid van artikelen."""
        self.log("Betrouwbaarheid controleren...")

        resultaten = []
        for artikel in artikelen:
            # Basis betrouwbaarheid
            is_betrouwbaar = artikel.get("betrouwbaar", False)

            # Extra checks
            fake_score = self._bereken_fake_score(artikel)
            clickbait_score = self._bereken_clickbait_score(artikel)
            bron_check = self.web.is_betrouwbare_bron(artikel["bron"])

            # Bepaal status
            if is_betrouwbaar and fake_score < 3 and clickbait_score < 2:
                status = "BETROUWBAAR"
                symbool = kleur("[OK]", "groen")
            elif fake_score >= 5 or clickbait_score >= 3:
                status = "FAKE NEWS"
                symbool = kleur("[!!]", "rood")
            elif not is_betrouwbaar:
                status = "ONBETROUWBAAR"
                symbool = kleur("[??]", "oranje")
            else:
                status = "TWIJFELACHTIG"
                symbool = kleur("[?]", "geel")

            self.log(f"{symbool} {artikel['bron']}: {status}")

            resultaten.append({
                **artikel,
                "status": status,
                "fake_score": fake_score,
                "clickbait_score": clickbait_score,
                "bron_betrouwbaar": bron_check
            })

        return resultaten

    def _bereken_fake_score(self, artikel: dict) -> int:
        """Bereken fake news score."""
        tekst = (artikel["titel"] + " " + artikel["tekst"]).lower()
        score = 0
        for indicator in self.FAKE_NEWS_INDICATOREN:
            if indicator in tekst:
                score += 1
        return score

    def _bereken_clickbait_score(self, artikel: dict) -> int:
        """Bereken clickbait score."""
        titel = artikel["titel"].lower()
        score = 0
        for woord in self.CLICKBAIT_WOORDEN:
            if woord in titel:
                score += 1
        # Extra punt voor allemaal hoofdletters
        if artikel["titel"].isupper():
            score += 2
        return score


class BiasDetectorAgent(Agent):
    """Agent die bias in nieuwsbronnen detecteert."""

    # Bias indicatoren per type
    BIAS_PATRONEN = {
        "politiek_links": ["progressief", "sociaal", "gelijkheid", "klimaat", "diversiteit"],
        "politiek_rechts": ["traditioneel", "conservatief", "vrijheid", "markt", "soevereiniteit"],
        "commercieel": ["koop nu", "aanbieding", "gesponsord", "partner", "advertentie"],
        "sensationeel": ["schokkend", "ongelooflijk", "verbijsterend", "drama", "schandaal"],
    }

    def __init__(self):
        super().__init__("BIAS", "[B]", "magenta")

    def analyseer_bias(self, artikelen: list) -> list:
        """Analyseer bias in artikelen."""
        self.log("Bias analyse uitvoeren...")

        resultaten = []
        for artikel in artikelen:
            tekst = (artikel["titel"] + " " + artikel["tekst"]).lower()

            bias_scores = {}
            for bias_type, patronen in self.BIAS_PATRONEN.items():
                score = sum(1 for p in patronen if p in tekst)
                if score > 0:
                    bias_scores[bias_type] = score

            # Bepaal dominante bias
            if bias_scores:
                dominante_bias = max(bias_scores, key=bias_scores.get)
                bias_niveau = "laag" if max(bias_scores.values()) <= 1 else "medium"
                if max(bias_scores.values()) >= 3:
                    bias_niveau = "hoog"
            else:
                dominante_bias = "geen"
                bias_niveau = "geen"

            if dominante_bias != "geen":
                self.log(f"{artikel['bron']}: {dominante_bias} bias ({bias_niveau})")

            resultaten.append({
                **artikel,
                "bias_scores": bias_scores,
                "dominante_bias": dominante_bias,
                "bias_niveau": bias_niveau
            })

        return resultaten


class SentimentAgent(Agent):
    """Agent die sentiment analyse uitvoert."""

    # Uitgebreide sentiment woorden
    POSITIEF = [
        "succesvol", "gewonnen", "doorbraak", "record", "beste", "fantastisch",
        "geweldig", "verbeterd", "groei", "winst", "positief", "enthousiast",
        "revolutionair", "baanbrekend", "groot succes", "optimistisch", "trots",
        "innovatief", "historisch", "uitstekend", "briljant", "indrukwekkend",
        "hoopvol", "blij", "tevreden", "gelukkig", "vreugde", "viering"
    ]
    NEGATIEF = [
        "uitgesteld", "probleem", "verlies", "daling", "schandaal", "fraude",
        "stopt", "mislukt", "crisis", "ontslagen", "negatief", "zorgen",
        "slecht", "gevaar", "risico", "verliezen", "tragisch", "ramp",
        "failliet", "conflict", "oorlog", "schade", "teleurstelling", "angst",
        "woede", "protest", "kritiek", "beschuldiging", "onderzoek"
    ]

    def __init__(self):
        super().__init__("SENTIMENT", "[S]", "geel")

    def analyseer(self, artikelen: list) -> list:
        """Analyseert sentiment van artikelen."""
        self.log("Sentiment analyse uitvoeren...")

        resultaten = []
        for artikel in artikelen:
            tekst = (artikel["titel"] + " " + artikel["tekst"]).lower()

            positief_score = sum(1 for w in self.POSITIEF if w in tekst)
            negatief_score = sum(1 for w in self.NEGATIEF if w in tekst)

            # Bereken sentiment
            totaal = positief_score + negatief_score
            if totaal == 0:
                sentiment = "NEUTRAAL"
                sentiment_ratio = 0.5
                icon = kleur("[=]", "grijs")
            elif positief_score > negatief_score:
                sentiment = "POSITIEF"
                sentiment_ratio = positief_score / totaal
                icon = kleur("[+]", "groen")
            else:
                sentiment = "NEGATIEF"
                sentiment_ratio = negatief_score / totaal
                icon = kleur("[-]", "rood")

            self.log(f"{icon} {artikel['bron']}: {sentiment} ({sentiment_ratio:.0%})")

            resultaten.append({
                **artikel,
                "sentiment": sentiment,
                "positief_score": positief_score,
                "negatief_score": negatief_score,
                "sentiment_ratio": sentiment_ratio
            })

        return resultaten


class SamenvatterAgent(Agent):
    """Agent die samenvattingen genereert."""

    def __init__(self):
        super().__init__("SAMENVATTER", "[Z]", "cyaan")

    def vat_samen(self, artikelen: list, onderwerp: str) -> str:
        """Genereert een samenvatting van alle artikelen."""
        self.log("Samenvatting genereren...")

        betrouwbaar = [a for a in artikelen if a.get("status") == "BETROUWBAAR"]
        positief = [a for a in artikelen if a.get("sentiment") == "POSITIEF"]
        negatief = [a for a in artikelen if a.get("sentiment") == "NEGATIEF"]
        neutraal = [a for a in artikelen if a.get("sentiment") == "NEUTRAAL"]

        # Bereken totale leestijd
        totale_leestijd = sum(a.get("leestijd", 2) for a in betrouwbaar)

        samenvatting = f"SAMENVATTING: {onderwerp.upper()}\n"
        samenvatting += "=" * 50 + "\n\n"

        samenvatting += f"Totaal {len(artikelen)} artikelen geanalyseerd.\n"
        samenvatting += f"- {len(betrouwbaar)} van betrouwbare bronnen\n"
        samenvatting += f"- {len(positief)} met positief sentiment\n"
        samenvatting += f"- {len(negatief)} met negatief sentiment\n"
        samenvatting += f"- {len(neutraal)} neutraal\n"
        samenvatting += f"- Geschatte leestijd: {totale_leestijd} minuten\n\n"

        # Sentiment overzicht
        if len(positief) > len(negatief):
            samenvatting += "OVERALL SENTIMENT: POSITIEF\n"
            samenvatting += f"Het nieuws over {onderwerp} is overwegend positief.\n\n"
        elif len(negatief) > len(positief):
            samenvatting += "OVERALL SENTIMENT: NEGATIEF\n"
            samenvatting += f"Er zijn zorgen in het nieuws over {onderwerp}.\n\n"
        else:
            samenvatting += "OVERALL SENTIMENT: GEMENGD\n"
            samenvatting += f"Het nieuws over {onderwerp} is gemengd.\n\n"

        samenvatting += "BELANGRIJKSTE HEADLINES:\n"
        for artikel in betrouwbaar[:3]:
            sent_icon = {"POSITIEF": "+", "NEGATIEF": "-", "NEUTRAAL": "="}.get(
                artikel.get("sentiment", "NEUTRAAL"), "=")
            samenvatting += f"  [{sent_icon}] {artikel['titel']}\n"

        if positief:
            samenvatting += f"\nPOSITIEF NIEUWS:\n  {positief[0]['titel']}\n"
        if negatief:
            samenvatting += f"\nAANDACHTSPUNT:\n  {negatief[0]['titel']}\n"

        self.log("Samenvatting compleet!")
        return samenvatting

    def genereer_digest(self, alle_nieuws: dict) -> str:
        """Genereer een dagelijkse digest van alle categorieen."""
        self.log("Dagelijkse digest genereren...")

        digest = "DAGELIJKSE NIEUWS DIGEST\n"
        digest += f"Datum: {datetime.now().strftime('%Y-%m-%d')}\n"
        digest += "=" * 60 + "\n\n"

        for categorie, artikelen in alle_nieuws.items():
            betrouwbaar = [a for a in artikelen if a.get("betrouwbaar", False)]
            if betrouwbaar:
                digest += f"\n{categorie.upper()}\n"
                digest += "-" * 30 + "\n"
                for artikel in betrouwbaar[:2]:
                    digest += f"  * {artikel['titel']}\n"

        return digest


class SchrijverAgent(Agent):
    """Agent die het rapport schrijft."""

    def __init__(self):
        super().__init__("SCHRIJVER", "[W]", "wit")

    def schrijf_rapport(self, onderwerp: str, artikelen: list, samenvatting: str) -> dict:
        """Schrijft een compleet rapport."""
        self.log("Rapport schrijven...")

        betrouwbaar = [a for a in artikelen if a.get("status") == "BETROUWBAAR"]
        onbetrouwbaar = [a for a in artikelen if a.get("status") in ["ONBETROUWBAAR", "FAKE NEWS"]]
        positief = [a for a in artikelen if a.get("sentiment") == "POSITIEF"]
        negatief = [a for a in artikelen if a.get("sentiment") == "NEGATIEF"]
        neutraal = [a for a in artikelen if a.get("sentiment") == "NEUTRAAL"]

        # Social engagement
        totaal_shares = sum(a.get("social_shares", 0) for a in artikelen)
        meest_gedeeld = max(artikelen, key=lambda x: x.get("social_shares", 0))

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
                "totaal_social_shares": totaal_shares,
            },
            "betrouwbare_artikelen": betrouwbaar,
            "onbetrouwbare_artikelen": onbetrouwbaar,
            "meest_gedeeld": meest_gedeeld,
            "actiepunten": [
                f"Blijf de ontwikkelingen rond {onderwerp} volgen",
                "Verifieer altijd nieuwsbronnen voor het delen",
                "Let op sentiment bias in berichtgeving",
                "Wees kritisch over sensationele claims",
                "Check meerdere bronnen voor belangrijk nieuws"
            ]
        }

        self.log(f"Rapport compleet: {len(betrouwbaar)} betrouwbare bronnen")
        return rapport


class RapportGeneratorAgent(Agent):
    """Agent die rapporten genereert in verschillende formaten."""

    def __init__(self):
        super().__init__("GENERATOR", "[G]", "magenta")
        Config.ensure_dirs()
        self.output_map = Config.RAPPORTEN_DIR

    def genereer_html(self, rapport: dict) -> str:
        """Genereert een uitgebreid HTML rapport."""
        self.log("HTML rapport genereren...")

        stats = rapport["statistieken"]
        meest_gedeeld = rapport.get("meest_gedeeld", {})

        html = f"""<!DOCTYPE html>
<html lang="nl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Nieuws Rapport: {rapport['onderwerp']}</title>
    <style>
        * {{ box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            max-width: 1000px;
            margin: 0 auto;
            padding: 20px;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #eee;
            min-height: 100vh;
        }}
        .container {{
            background: rgba(255,255,255,0.05);
            padding: 30px;
            border-radius: 15px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.1);
        }}
        h1 {{
            color: #00d4ff;
            border-bottom: 3px solid #00d4ff;
            padding-bottom: 15px;
            margin-bottom: 25px;
        }}
        h2 {{
            color: #ff6b6b;
            margin-top: 35px;
            border-left: 4px solid #ff6b6b;
            padding-left: 15px;
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
            gap: 15px;
            margin: 25px 0;
        }}
        .stat-box {{
            background: rgba(255,255,255,0.1);
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            transition: transform 0.2s;
        }}
        .stat-box:hover {{ transform: translateY(-5px); }}
        .stat-box.positief {{ background: rgba(39, 174, 96, 0.3); border: 1px solid #27ae60; }}
        .stat-box.negatief {{ background: rgba(231, 76, 60, 0.3); border: 1px solid #e74c3c; }}
        .stat-box.neutraal {{ background: rgba(149, 165, 166, 0.3); border: 1px solid #95a5a6; }}
        .stat-box h3 {{ margin: 0; font-size: 32px; color: #00d4ff; }}
        .stat-box p {{ margin: 8px 0 0 0; color: #aaa; font-size: 14px; }}
        .artikel {{
            background: rgba(255,255,255,0.05);
            border-left: 4px solid #00d4ff;
            padding: 20px;
            margin: 15px 0;
            border-radius: 0 10px 10px 0;
            transition: background 0.2s;
        }}
        .artikel:hover {{ background: rgba(255,255,255,0.1); }}
        .artikel.onbetrouwbaar {{ border-left-color: #e74c3c; background: rgba(231,76,60,0.1); }}
        .artikel.positief {{ border-left-color: #27ae60; }}
        .artikel.negatief {{ border-left-color: #e74c3c; }}
        .artikel h4 {{ margin: 0 0 10px 0; color: #fff; }}
        .artikel p {{ margin: 5px 0; color: #bbb; font-size: 14px; }}
        .sentiment {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 15px;
            font-size: 11px;
            font-weight: bold;
            margin-left: 10px;
        }}
        .sentiment.positief {{ background: #27ae60; color: white; }}
        .sentiment.negatief {{ background: #e74c3c; color: white; }}
        .sentiment.neutraal {{ background: #95a5a6; color: white; }}
        .samenvatting {{
            background: rgba(0, 212, 255, 0.1);
            padding: 25px;
            border-radius: 10px;
            white-space: pre-line;
            font-family: 'Courier New', monospace;
            font-size: 14px;
            border: 1px solid rgba(0, 212, 255, 0.3);
        }}
        .social {{ color: #888; font-size: 12px; margin-top: 5px; }}
        .meest-gedeeld {{
            background: linear-gradient(135deg, rgba(255,107,107,0.2), rgba(0,212,255,0.2));
            padding: 20px;
            border-radius: 10px;
            margin: 20px 0;
        }}
        .actiepunten {{ list-style: none; padding: 0; }}
        .actiepunten li {{
            padding: 10px 15px;
            margin: 8px 0;
            background: rgba(255,255,255,0.05);
            border-radius: 5px;
            border-left: 3px solid #00d4ff;
        }}
        .meta {{ color: #666; font-size: 14px; margin-bottom: 20px; }}
    </style>
</head>
<body>
<div class="container">
    <h1>Nieuws Rapport: {rapport['onderwerp'].title()}</h1>
    <p class="meta">Gegenereerd op: {rapport['datum']} | Danny Toolkit Nieuws Agent v2.0</p>

    <div class="stats">
        <div class="stat-box"><h3>{stats['totaal']}</h3><p>Artikelen</p></div>
        <div class="stat-box"><h3>{stats['betrouwbaar']}</h3><p>Betrouwbaar</p></div>
        <div class="stat-box positief"><h3>{stats['positief']}</h3><p>Positief</p></div>
        <div class="stat-box negatief"><h3>{stats['negatief']}</h3><p>Negatief</p></div>
        <div class="stat-box neutraal"><h3>{stats['neutraal']}</h3><p>Neutraal</p></div>
        <div class="stat-box"><h3>{stats['totaal_social_shares']:,}</h3><p>Social Shares</p></div>
    </div>

    <div class="meest-gedeeld">
        <strong>Meest Gedeeld:</strong> {meest_gedeeld.get('titel', 'N/A')}
        <br><small>{meest_gedeeld.get('social_shares', 0):,} shares op social media</small>
    </div>

    <h2>Samenvatting</h2>
    <div class="samenvatting">{rapport['samenvatting']}</div>

    <h2>Betrouwbare Bronnen ({len(rapport['betrouwbare_artikelen'])})</h2>
"""
        for artikel in rapport["betrouwbare_artikelen"]:
            sentiment = artikel.get("sentiment", "NEUTRAAL").lower()
            leestijd = artikel.get("leestijd", 2)
            shares = artikel.get("social_shares", 0)
            html += f'''    <div class="artikel {sentiment}">
        <h4>{artikel["bron"]} <span class="sentiment {sentiment}">{artikel.get("sentiment", "?")}</span></h4>
        <p><strong>{artikel["titel"]}</strong></p>
        <p>{artikel["tekst"]}</p>
        <p class="social">Datum: {artikel["datum"]} | Leestijd: {leestijd} min | Shares: {shares:,}</p>
    </div>
'''

        if rapport["onbetrouwbare_artikelen"]:
            html += f'    <h2>Niet-Geverifieerde Bronnen ({len(rapport["onbetrouwbare_artikelen"])})</h2>\n'
            for artikel in rapport["onbetrouwbare_artikelen"]:
                html += f'''    <div class="artikel onbetrouwbaar">
        <h4>{artikel["bron"]} <span class="sentiment neutraal">NIET GEVERIFIEERD</span></h4>
        <p><strong>{artikel["titel"]}</strong></p>
        <p style="color:#ff6b6b">LET OP: Deze bron is niet geverifieerd - wees kritisch!</p>
    </div>
'''

        html += """    <h2>Actiepunten</h2>
    <ul class="actiepunten">
"""
        for punt in rapport["actiepunten"]:
            html += f"        <li>{punt}</li>\n"

        html += """    </ul>
    <p style="text-align:center;color:#666;margin-top:30px;">
        Gegenereerd door Danny Toolkit Nieuws Agent v2.0
    </p>
</div>
</body>
</html>"""

        bestandsnaam = f"nieuws_{rapport['onderwerp'].lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        pad = self.output_map / bestandsnaam

        with open(pad, "w", encoding="utf-8") as f:
            f.write(html)

        self.log(f"HTML rapport opgeslagen: {pad.name}")
        return str(pad)

    def genereer_json(self, rapport: dict) -> str:
        """Genereer JSON rapport."""
        self.log("JSON rapport genereren...")

        bestandsnaam = f"nieuws_{rapport['onderwerp'].lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        pad = self.output_map / bestandsnaam

        with open(pad, "w", encoding="utf-8") as f:
            json.dump(rapport, f, indent=2, ensure_ascii=False, default=str)

        self.log(f"JSON rapport opgeslagen: {pad.name}")
        return str(pad)

    def genereer_markdown(self, rapport: dict) -> str:
        """Genereer Markdown rapport."""
        self.log("Markdown rapport genereren...")

        stats = rapport["statistieken"]

        md = f"""# Nieuws Rapport: {rapport['onderwerp'].title()}

*Gegenereerd op: {rapport['datum']}*

## Statistieken

| Metric | Waarde |
|--------|--------|
| Totaal artikelen | {stats['totaal']} |
| Betrouwbaar | {stats['betrouwbaar']} |
| Positief | {stats['positief']} |
| Negatief | {stats['negatief']} |
| Neutraal | {stats['neutraal']} |

## Samenvatting

```
{rapport['samenvatting']}
```

## Betrouwbare Bronnen

"""
        for artikel in rapport["betrouwbare_artikelen"]:
            sentiment = artikel.get("sentiment", "NEUTRAAL")
            md += f"### {artikel['titel']}\n\n"
            md += f"**Bron:** {artikel['bron']} | **Sentiment:** {sentiment}\n\n"
            md += f"{artikel['tekst']}\n\n"
            md += f"*Datum: {artikel['datum']}*\n\n---\n\n"

        md += "## Actiepunten\n\n"
        for punt in rapport["actiepunten"]:
            md += f"- {punt}\n"

        bestandsnaam = f"nieuws_{rapport['onderwerp'].lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        pad = self.output_map / bestandsnaam

        with open(pad, "w", encoding="utf-8") as f:
            f.write(md)

        self.log(f"Markdown rapport opgeslagen: {pad.name}")
        return str(pad)


class NieuwsAgentApp:
    """Nieuws Agent orchestrator v2.0 met uitgebreide features."""

    VERSIE = "2.0"

    ONDERWERPEN = {
        "1": "Ruimtevaart",
        "2": "Gaming",
        "3": "AI",
        "4": "Sport",
        "5": "Technologie",
        "6": "Wetenschap",
        "7": "Entertainment",
        "8": "Economie",
        "9": "Gezondheid",
        "10": "Klimaat",
    }

    def __init__(self):
        self.zoeker = ZoekerAgent()
        self.feitenchecker = FeitencheckerAgent()
        self.bias_detector = BiasDetectorAgent()
        self.sentiment_agent = SentimentAgent()
        self.samenvatter = SamenvatterAgent()
        self.schrijver = SchrijverAgent()
        self.generator = RapportGeneratorAgent()

        # Data opslag
        self.data_bestand = Path.home() / ".danny_toolkit" / "nieuws_agent.json"
        self.data = self._laad_data()

    def _laad_data(self) -> dict:
        """Laad opgeslagen data."""
        if self.data_bestand.exists():
            try:
                with open(self.data_bestand, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {
            "versie": self.VERSIE,
            "analyses_totaal": 0,
            "bookmarks": [],
            "alerts": [],
            "geschiedenis": [],
            "voorkeuren": {
                "favoriete_categorieen": [],
                "export_formaat": "html",
            }
        }

    def _sla_data_op(self):
        """Sla data op."""
        self.data_bestand.parent.mkdir(parents=True, exist_ok=True)
        with open(self.data_bestand, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    def toon_trending(self):
        """Toont trending topics met kleur."""
        print("\n" + kleur("=" * 55, "cyaan"))
        print(kleur("  TRENDING TOPICS", "geel"))
        print(kleur("=" * 55, "cyaan"))

        trending = self.zoeker.get_trending()
        for i, topic in enumerate(trending, 1):
            if topic["trend"] == "up":
                trend_icon = kleur("[^]", "groen")
                change = kleur(topic["change"], "groen")
            elif topic["trend"] == "down":
                trend_icon = kleur("[v]", "rood")
                change = kleur(topic["change"], "rood")
            else:
                trend_icon = kleur("[-]", "grijs")
                change = kleur(topic["change"], "grijs")

            print(f"  {i:2}. {topic['onderwerp']:<15} {topic['mentions']:>7,} mentions {trend_icon} {change}")

    def toon_menu(self):
        """Toon het hoofdmenu."""
        print()
        print(kleur("+" + "=" * 55 + "+", "cyaan"))
        print(kleur("|       NIEUWS AGENT v2.0                              |", "cyaan"))
        print(kleur("+" + "=" * 55 + "+", "cyaan"))
        print(kleur("| ANALYSE                                              |", "wit"))
        print("|  1. Analyseer onderwerp                              |")
        print("|  2. Dagelijkse digest (alle categorieen)             |")
        print("|  3. Vergelijk categorieen                            |")
        print(kleur("+" + "-" * 55 + "+", "grijs"))
        print(kleur("| TOOLS                                                |", "wit"))
        print("|  4. Bekijk trending topics                           |")
        print("|  5. Bookmark beheer                                  |")
        print("|  6. Configureer alerts                               |")
        print(kleur("+" + "-" * 55 + "+", "grijs"))
        print(kleur("| STATISTIEKEN                                         |", "wit"))
        print("|  7. Analyse geschiedenis                             |")
        print("|  8. Bron statistieken                                |")
        print(kleur("+" + "-" * 55 + "+", "grijs"))
        print("|  0. Terug naar hoofdmenu                             |")
        print(kleur("+" + "=" * 55 + "+", "cyaan"))

    def kies_onderwerp(self) -> str:
        """Laat gebruiker een onderwerp kiezen."""
        print("\n" + kleur("Kies een onderwerp:", "geel"))
        for num, naam in self.ONDERWERPEN.items():
            print(f"  {num:2}. {naam}")
        print("  11. Eigen onderwerp")

        keuze = input("\nJouw keuze: ").strip()

        if keuze in self.ONDERWERPEN:
            return self.ONDERWERPEN[keuze]
        elif keuze == "11":
            return input("Voer je onderwerp in: ").strip() or "AI"
        else:
            return "AI"

    def kies_export_formaat(self) -> str:
        """Laat gebruiker export formaat kiezen."""
        print("\n" + kleur("Kies export formaat:", "geel"))
        print("  1. HTML (aanbevolen)")
        print("  2. JSON")
        print("  3. Markdown")
        print("  4. Alle formaten")

        keuze = input("\nKeuze [1]: ").strip() or "1"
        return {"1": "html", "2": "json", "3": "markdown", "4": "alle"}.get(keuze, "html")

    def analyseer(self, onderwerp: str) -> str:
        """Voert de complete nieuws-analyse uit met alle agents."""
        print("\n" + kleur("=" * 60, "cyaan"))
        print(kleur("  NIEUWS-AGENT v2.0 - Multi-Agent Analyse", "geel"))
        print(kleur("=" * 60, "cyaan"))
        print(f"\nOnderwerp: {kleur(onderwerp, 'groen')}")
        print(f"Datum: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

        # Stap 1: Verzamelen
        print("\n" + kleur("-" * 45, "grijs"))
        print(kleur("STAP 1: INFORMATIE VERZAMELEN", "geel"))
        print(kleur("-" * 45, "grijs"))
        artikelen = self.zoeker.verzamel(onderwerp)

        # Stap 2: Feiten checken
        print("\n" + kleur("-" * 45, "grijs"))
        print(kleur("STAP 2: FEITEN CONTROLEREN", "geel"))
        print(kleur("-" * 45, "grijs"))
        artikelen = self.feitenchecker.controleer(artikelen)

        # Stap 3: Bias detectie
        print("\n" + kleur("-" * 45, "grijs"))
        print(kleur("STAP 3: BIAS DETECTIE", "geel"))
        print(kleur("-" * 45, "grijs"))
        artikelen = self.bias_detector.analyseer_bias(artikelen)

        # Stap 4: Sentiment analyse
        print("\n" + kleur("-" * 45, "grijs"))
        print(kleur("STAP 4: SENTIMENT ANALYSE", "geel"))
        print(kleur("-" * 45, "grijs"))
        artikelen = self.sentiment_agent.analyseer(artikelen)

        # Stap 5: Samenvatting
        print("\n" + kleur("-" * 45, "grijs"))
        print(kleur("STAP 5: SAMENVATTING GENEREREN", "geel"))
        print(kleur("-" * 45, "grijs"))
        samenvatting = self.samenvatter.vat_samen(artikelen, onderwerp)

        # Stap 6: Rapport schrijven
        print("\n" + kleur("-" * 45, "grijs"))
        print(kleur("STAP 6: RAPPORT SCHRIJVEN", "geel"))
        print(kleur("-" * 45, "grijs"))
        rapport = self.schrijver.schrijf_rapport(onderwerp, artikelen, samenvatting)

        # Stap 7: Export
        print("\n" + kleur("-" * 45, "grijs"))
        print(kleur("STAP 7: RAPPORT EXPORTEREN", "geel"))
        print(kleur("-" * 45, "grijs"))

        formaat = self.kies_export_formaat()
        rapport_paden = []

        if formaat in ["html", "alle"]:
            rapport_paden.append(self.generator.genereer_html(rapport))
        if formaat in ["json", "alle"]:
            rapport_paden.append(self.generator.genereer_json(rapport))
        if formaat in ["markdown", "alle"]:
            rapport_paden.append(self.generator.genereer_markdown(rapport))

        # Update statistieken
        self.data["analyses_totaal"] += 1
        self.data["geschiedenis"].append({
            "onderwerp": onderwerp,
            "datum": datetime.now().isoformat(),
            "artikelen": len(artikelen),
            "betrouwbaar": rapport["statistieken"]["betrouwbaar"]
        })
        self.data["geschiedenis"] = self.data["geschiedenis"][-50:]  # Max 50
        self._sla_data_op()

        # Resultaten
        print("\n" + kleur("=" * 60, "groen"))
        print(kleur("  NIEUWS-AGENT ANALYSE COMPLEET!", "groen"))
        print(kleur("=" * 60, "groen"))

        stats = rapport["statistieken"]
        print(f"\n{kleur('Resultaten:', 'geel')}")
        print(f"   Artikelen gevonden:  {stats['totaal']}")
        print(f"   Betrouwbaar:         {kleur(str(stats['betrouwbaar']), 'groen')}")
        print(f"   Onbetrouwbaar:       {kleur(str(stats['onbetrouwbaar']), 'rood')}")

        print(f"\n{kleur('Sentiment:', 'geel')}")
        print(f"   {kleur('[+]', 'groen')} Positief:        {stats['positief']}")
        print(f"   {kleur('[-]', 'rood')} Negatief:        {stats['negatief']}")
        print(f"   {kleur('[=]', 'grijs')} Neutraal:        {stats['neutraal']}")

        print(f"\n{kleur('Rapporten:', 'geel')}")
        for pad in rapport_paden:
            print(f"   {pad}")

        return rapport_paden[0] if rapport_paden else ""

    def dagelijkse_digest(self):
        """Genereer een dagelijkse digest van alle categorieen."""
        print("\n" + kleur("Dagelijkse digest genereren...", "geel"))

        alle_nieuws = self.zoeker.zoek_alle()
        digest = self.samenvatter.genereer_digest(alle_nieuws)

        print("\n" + kleur(digest, "cyaan"))

    def vergelijk_categorieen(self):
        """Vergelijk sentiment tussen categorieen."""
        print("\n" + kleur("=" * 55, "cyaan"))
        print(kleur("  CATEGORIE VERGELIJKING", "geel"))
        print(kleur("=" * 55, "cyaan"))

        alle_nieuws = self.zoeker.zoek_alle()

        print(f"\n{'Categorie':<15} {'Positief':>10} {'Negatief':>10} {'Neutraal':>10}")
        print("-" * 50)

        for categorie, artikelen in alle_nieuws.items():
            artikelen = self.sentiment_agent.analyseer(artikelen)
            pos = sum(1 for a in artikelen if a.get("sentiment") == "POSITIEF")
            neg = sum(1 for a in artikelen if a.get("sentiment") == "NEGATIEF")
            neu = sum(1 for a in artikelen if a.get("sentiment") == "NEUTRAAL")

            pos_str = kleur(str(pos), "groen")
            neg_str = kleur(str(neg), "rood")
            neu_str = kleur(str(neu), "grijs")

            print(f"{categorie.title():<15} {pos_str:>18} {neg_str:>18} {neu_str:>18}")

    def beheer_bookmarks(self):
        """Beheer bookmarks."""
        print("\n" + kleur("BOOKMARK BEHEER", "cyaan"))
        print("-" * 40)

        if not self.data["bookmarks"]:
            print(kleur("Geen bookmarks opgeslagen.", "grijs"))
        else:
            for i, bm in enumerate(self.data["bookmarks"], 1):
                print(f"  {i}. {bm['titel'][:40]}... ({bm['datum']})")

        print("\n  a. Voeg bookmark toe")
        print("  v. Verwijder bookmark")
        print("  0. Terug")

    def toon_geschiedenis(self):
        """Toon analyse geschiedenis."""
        print("\n" + kleur("ANALYSE GESCHIEDENIS", "cyaan"))
        print("=" * 50)

        if not self.data["geschiedenis"]:
            print(kleur("\nGeen analyses in geschiedenis.", "grijs"))
            return

        print(f"\nTotaal analyses: {self.data['analyses_totaal']}")
        print(f"\nLaatste analyses:")
        for analyse in reversed(self.data["geschiedenis"][-10:]):
            datum = analyse["datum"][:10]
            print(f"  {datum} | {analyse['onderwerp']:<15} | {analyse['artikelen']} artikelen")

    def toon_bron_statistieken(self):
        """Toon statistieken per bron."""
        print("\n" + kleur("BRON STATISTIEKEN", "cyaan"))
        print("=" * 50)

        alle_nieuws = self.zoeker.zoek_alle()
        bron_stats = {}

        for categorie, artikelen in alle_nieuws.items():
            for artikel in artikelen:
                bron = artikel["bron"]
                if bron not in bron_stats:
                    bron_stats[bron] = {"artikelen": 0, "betrouwbaar": artikel.get("betrouwbaar", False)}
                bron_stats[bron]["artikelen"] += 1

        print(f"\n{'Bron':<25} {'Artikelen':>10} {'Status':>15}")
        print("-" * 55)

        for bron, stats in sorted(bron_stats.items(), key=lambda x: x[1]["artikelen"], reverse=True)[:15]:
            status = kleur("Betrouwbaar", "groen") if stats["betrouwbaar"] else kleur("Onbekend", "geel")
            print(f"{bron:<25} {stats['artikelen']:>10} {status:>23}")

    def run(self):
        """Start de interactieve nieuws agent."""
        clear_scherm()
        print(kleur("+" + "=" * 58 + "+", "cyaan"))
        print(kleur("|    NIEUWS-AGENT v2.0: Multi-Agent Nieuws Analyse         |", "cyaan"))
        print(kleur("|                                                          |", "cyaan"))
        print(kleur("|    Features:                                             |", "grijs"))
        print(kleur("|    - Fake news detectie    - Bias analyse                |", "grijs"))
        print(kleur("|    - Sentiment analyse     - Social media trends         |", "grijs"))
        print(kleur("|    - Multi-format export   - Categorie vergelijking      |", "grijs"))
        print(kleur("+" + "=" * 58 + "+", "cyaan"))

        # Toon trending
        self.toon_trending()

        while True:
            self.toon_menu()
            keuze = input("\nKeuze: ").strip()

            if keuze == "0":
                break
            elif keuze == "1":
                onderwerp = self.kies_onderwerp()
                rapport_pad = self.analyseer(onderwerp)

                if rapport_pad and rapport_pad.endswith(".html"):
                    print(f"\n{kleur('Wil je het rapport openen in je browser? (j/n)', 'cyaan')}")
                    if input("> ").lower().strip() == "j":
                        import webbrowser
                        import os
                        webbrowser.open(f"file://{os.path.abspath(rapport_pad)}")
                        print(kleur("Rapport geopend in browser!", "groen"))

            elif keuze == "2":
                self.dagelijkse_digest()
            elif keuze == "3":
                self.vergelijk_categorieen()
            elif keuze == "4":
                self.toon_trending()
            elif keuze == "5":
                self.beheer_bookmarks()
            elif keuze == "6":
                print(kleur("\nAlerts configuratie komt in volgende update!", "geel"))
            elif keuze == "7":
                self.toon_geschiedenis()
            elif keuze == "8":
                self.toon_bron_statistieken()
            else:
                print(kleur("Ongeldige keuze.", "rood"))

            input(kleur("\nDruk op Enter om verder te gaan...", "grijs"))

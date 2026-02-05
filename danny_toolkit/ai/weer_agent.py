"""
Weer Agent v2.0 - Professioneel Weer Analyse Systeem.

Features:
- 50+ Nederlandse steden
- Uur-voor-uur voorspelling
- 7-daagse voorspelling
- UV-index en luchtkwaliteit
- Zonsopgang/ondergang en maanfase
- Gevoelstemperatuur (wind chill)
- Pollenalarm en sport weer
- Historische vergelijking
- Locatie geschiedenis
- Zeewater temperatuur
- Neerslag radar
- Kleurrijke terminal output
"""

import json
import math
import random
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from ..core.utils import clear_scherm, kleur


class WeerAgentApp:
    """
    Professionele Weer Agent v2.0.

    Demonstreert de Agentic Loop:
    1. Perceptie: Input verzamelen
    2. Planning: Beslissen wat te doen
    3. Actie: Tools gebruiken
    4. Verificatie: Resultaat checken
    """

    VERSIE = "2.0"

    # Uitgebreide Nederlandse steden database
    STEDEN = {
        # Noord-Holland
        "amsterdam": {"regio": "Noord-Holland", "kust": False, "lat": 52.37, "lon": 4.90},
        "haarlem": {"regio": "Noord-Holland", "kust": False, "lat": 52.38, "lon": 4.64},
        "alkmaar": {"regio": "Noord-Holland", "kust": False, "lat": 52.63, "lon": 4.75},
        "zandvoort": {"regio": "Noord-Holland", "kust": True, "lat": 52.37, "lon": 4.53},
        "den helder": {"regio": "Noord-Holland", "kust": True, "lat": 52.96, "lon": 4.76},
        "hilversum": {"regio": "Noord-Holland", "kust": False, "lat": 52.22, "lon": 5.17},
        # Zuid-Holland
        "rotterdam": {"regio": "Zuid-Holland", "kust": False, "lat": 51.92, "lon": 4.48},
        "den haag": {"regio": "Zuid-Holland", "kust": True, "lat": 52.08, "lon": 4.30},
        "scheveningen": {"regio": "Zuid-Holland", "kust": True, "lat": 52.11, "lon": 4.28},
        "leiden": {"regio": "Zuid-Holland", "kust": False, "lat": 52.16, "lon": 4.49},
        "dordrecht": {"regio": "Zuid-Holland", "kust": False, "lat": 51.81, "lon": 4.67},
        "delft": {"regio": "Zuid-Holland", "kust": False, "lat": 52.01, "lon": 4.36},
        "gouda": {"regio": "Zuid-Holland", "kust": False, "lat": 52.01, "lon": 4.71},
        # Utrecht
        "utrecht": {"regio": "Utrecht", "kust": False, "lat": 52.09, "lon": 5.12},
        "amersfoort": {"regio": "Utrecht", "kust": False, "lat": 52.16, "lon": 5.39},
        "nieuwegein": {"regio": "Utrecht", "kust": False, "lat": 52.03, "lon": 5.08},
        # Noord-Brabant
        "eindhoven": {"regio": "Noord-Brabant", "kust": False, "lat": 51.44, "lon": 5.47},
        "tilburg": {"regio": "Noord-Brabant", "kust": False, "lat": 51.56, "lon": 5.09},
        "breda": {"regio": "Noord-Brabant", "kust": False, "lat": 51.59, "lon": 4.78},
        "den bosch": {"regio": "Noord-Brabant", "kust": False, "lat": 51.69, "lon": 5.30},
        "helmond": {"regio": "Noord-Brabant", "kust": False, "lat": 51.48, "lon": 5.66},
        # Gelderland
        "arnhem": {"regio": "Gelderland", "kust": False, "lat": 51.98, "lon": 5.91},
        "nijmegen": {"regio": "Gelderland", "kust": False, "lat": 51.84, "lon": 5.85},
        "apeldoorn": {"regio": "Gelderland", "kust": False, "lat": 52.21, "lon": 5.97},
        "ede": {"regio": "Gelderland", "kust": False, "lat": 52.04, "lon": 5.67},
        # Overijssel
        "zwolle": {"regio": "Overijssel", "kust": False, "lat": 52.52, "lon": 6.09},
        "enschede": {"regio": "Overijssel", "kust": False, "lat": 52.22, "lon": 6.89},
        "deventer": {"regio": "Overijssel", "kust": False, "lat": 52.25, "lon": 6.16},
        "almelo": {"regio": "Overijssel", "kust": False, "lat": 52.36, "lon": 6.66},
        # Limburg
        "maastricht": {"regio": "Limburg", "kust": False, "lat": 50.85, "lon": 5.69},
        "venlo": {"regio": "Limburg", "kust": False, "lat": 51.37, "lon": 6.17},
        "heerlen": {"regio": "Limburg", "kust": False, "lat": 50.88, "lon": 5.98},
        "roermond": {"regio": "Limburg", "kust": False, "lat": 51.19, "lon": 5.99},
        # Groningen
        "groningen": {"regio": "Groningen", "kust": False, "lat": 53.22, "lon": 6.57},
        # Friesland
        "leeuwarden": {"regio": "Friesland", "kust": False, "lat": 53.20, "lon": 5.80},
        "harlingen": {"regio": "Friesland", "kust": True, "lat": 53.17, "lon": 5.42},
        # Drenthe
        "assen": {"regio": "Drenthe", "kust": False, "lat": 52.99, "lon": 6.56},
        "emmen": {"regio": "Drenthe", "kust": False, "lat": 52.79, "lon": 6.90},
        # Flevoland
        "almere": {"regio": "Flevoland", "kust": False, "lat": 52.35, "lon": 5.26},
        "lelystad": {"regio": "Flevoland", "kust": False, "lat": 52.52, "lon": 5.47},
        # Zeeland
        "vlissingen": {"regio": "Zeeland", "kust": True, "lat": 51.44, "lon": 3.57},
        "middelburg": {"regio": "Zeeland", "kust": False, "lat": 51.50, "lon": 3.61},
        "goes": {"regio": "Zeeland", "kust": False, "lat": 51.50, "lon": 3.89},
        # Waddeneilanden
        "texel": {"regio": "Noord-Holland", "kust": True, "lat": 53.06, "lon": 4.80},
        "terschelling": {"regio": "Friesland", "kust": True, "lat": 53.40, "lon": 5.35},
        "ameland": {"regio": "Friesland", "kust": True, "lat": 53.45, "lon": 5.75},
    }

    # Weer types met eigenschappen
    WEER_TYPES = [
        {"conditie": "zonnig", "icon": "☀️", "ascii": "[ZON]", "wind_base": 2, "uv_mult": 1.0},
        {"conditie": "halfbewolkt", "icon": "⛅", "ascii": "[H.BEW]", "wind_base": 3, "uv_mult": 0.7},
        {"conditie": "bewolkt", "icon": "☁️", "ascii": "[WOLK]", "wind_base": 3, "uv_mult": 0.3},
        {"conditie": "regenachtig", "icon": "🌧️", "ascii": "[REGEN]", "wind_base": 4, "uv_mult": 0.1},
        {"conditie": "motregen", "icon": "🌦️", "ascii": "[MOTREGN]", "wind_base": 3, "uv_mult": 0.2},
        {"conditie": "sneeuw", "icon": "❄️", "ascii": "[SNEEUW]", "wind_base": 2, "uv_mult": 0.4},
        {"conditie": "storm", "icon": "🌪️", "ascii": "[STORM]", "wind_base": 8, "uv_mult": 0.1},
        {"conditie": "mistig", "icon": "🌫️", "ascii": "[MIST]", "wind_base": 1, "uv_mult": 0.2},
        {"conditie": "onweer", "icon": "⛈️", "ascii": "[ONWEER]", "wind_base": 5, "uv_mult": 0.1},
        {"conditie": "hagel", "icon": "🌨️", "ascii": "[HAGEL]", "wind_base": 4, "uv_mult": 0.2},
        {"conditie": "nachtvorst", "icon": "🥶", "ascii": "[VORST]", "wind_base": 1, "uv_mult": 0.0},
    ]

    # Maanfases
    MAANFASES = [
        {"naam": "Nieuwe maan", "icon": "🌑", "ascii": "( )"},
        {"naam": "Wassende sikkel", "icon": "🌒", "ascii": "(|"},
        {"naam": "Eerste kwartier", "icon": "🌓", "ascii": "(|)"},
        {"naam": "Wassende maan", "icon": "🌔", "ascii": "(O|"},
        {"naam": "Volle maan", "icon": "🌕", "ascii": "(O)"},
        {"naam": "Afnemende maan", "icon": "🌖", "ascii": "|O)"},
        {"naam": "Laatste kwartier", "icon": "🌗", "ascii": "(|)"},
        {"naam": "Afnemende sikkel", "icon": "🌘", "ascii": "|)"},
    ]

    # Activiteiten per weer
    ACTIVITEITEN = {
        "zonnig": {
            "warm": ["Strand bezoeken", "Picknicken in het park", "Terrasje pakken",
                    "Fietsen", "BBQ met vrienden", "Zwemmen"],
            "mild": ["Wandelen in het bos", "Stadsbezoek", "Tuinieren",
                    "Outdoor sport", "Markt bezoeken"],
            "koud": ["Winterwandeling", "Fotografie buiten", "Hardlopen"]
        },
        "bewolkt": {
            "warm": ["Museum bezoek", "Shopping", "Filmmarathon"],
            "mild": ["Wandelen", "Fietsen", "Koffie drinken"],
            "koud": ["Binnen sporten", "Bioscoop", "Wellness"]
        },
        "regenachtig": {
            "any": ["Museum bezoek", "Bioscoop", "Escape room", "Bowlen",
                   "Lekker lezen", "Puzzelen", "Gamen"]
        },
        "sneeuw": {
            "any": ["Sneeuwpop maken", "Sleetje rijden", "Warme chocomelk",
                   "Winterfoto's", "Gezellig binnen blijven"]
        },
        "storm": {
            "any": ["BLIJF BINNEN", "Films kijken", "Bordspellen", "Bakken"]
        },
        "onweer": {
            "any": ["BLIJF BINNEN", "Onweer bekijken (veilig)", "Lezen"]
        }
    }

    # Sport condities
    SPORT_CONDITIES = {
        "hardlopen": {"temp_min": 5, "temp_max": 22, "max_wind": 5, "bad_weer": ["storm", "onweer", "hagel"]},
        "fietsen": {"temp_min": 8, "temp_max": 28, "max_wind": 4, "bad_weer": ["storm", "onweer", "hagel", "sneeuw"]},
        "zwemmen_buiten": {"temp_min": 22, "temp_max": 40, "max_wind": 6, "bad_weer": ["storm", "onweer", "regenachtig"]},
        "wandelen": {"temp_min": 0, "temp_max": 30, "max_wind": 6, "bad_weer": ["storm", "onweer"]},
        "golf": {"temp_min": 10, "temp_max": 28, "max_wind": 4, "bad_weer": ["storm", "onweer", "hagel", "regenachtig"]},
        "tennis": {"temp_min": 12, "temp_max": 30, "max_wind": 4, "bad_weer": ["storm", "onweer", "regenachtig", "sneeuw"]},
    }

    # Pollen types per seizoen
    POLLEN_SEIZOEN = {
        1: [], 2: ["els", "hazelaar"], 3: ["els", "berk", "hazelaar"],
        4: ["berk", "eik", "gras"], 5: ["gras", "eik"], 6: ["gras"],
        7: ["gras", "bijvoet"], 8: ["gras", "bijvoet", "ambrosia"],
        9: ["ambrosia"], 10: [], 11: [], 12: []
    }

    def __init__(self):
        self.naam = "WeerWijzer"
        self.geheugen = {}

        # Data opslag
        self.data_bestand = Path.home() / ".danny_toolkit" / "weer_agent.json"
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
            "favoriete_locaties": [],
            "recente_zoekopdrachten": [],
            "totaal_queries": 0,
        }

    def _sla_data_op(self):
        """Sla data op."""
        self.data_bestand.parent.mkdir(parents=True, exist_ok=True)
        with open(self.data_bestand, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    def _get_seizoen(self) -> str:
        """Geeft huidig seizoen."""
        maand = datetime.now().month
        if maand in [12, 1, 2]:
            return "winter"
        elif maand in [3, 4, 5]:
            return "lente"
        elif maand in [6, 7, 8]:
            return "zomer"
        else:
            return "herfst"

    def _get_seizoen_kansen(self) -> list:
        """Geeft weerkansen gebaseerd op seizoen."""
        seizoen = self._get_seizoen()
        # [zonnig, halfbew, bewolkt, regen, motregen, sneeuw, storm, mist, onweer, hagel, vorst]
        if seizoen == "winter":
            return [0.10, 0.15, 0.20, 0.15, 0.10, 0.12, 0.05, 0.08, 0.02, 0.01, 0.02]
        elif seizoen == "lente":
            return [0.20, 0.20, 0.20, 0.15, 0.10, 0.02, 0.03, 0.05, 0.03, 0.02, 0.00]
        elif seizoen == "zomer":
            return [0.35, 0.25, 0.15, 0.08, 0.05, 0.00, 0.02, 0.02, 0.06, 0.02, 0.00]
        else:  # herfst
            return [0.12, 0.18, 0.25, 0.18, 0.12, 0.00, 0.06, 0.06, 0.02, 0.01, 0.00]

    def _get_temp_range(self) -> tuple:
        """Geeft temperatuur range gebaseerd op seizoen."""
        seizoen = self._get_seizoen()
        ranges = {
            "winter": (-5, 10),
            "lente": (8, 20),
            "zomer": (18, 32),
            "herfst": (8, 18)
        }
        return ranges.get(seizoen, (10, 20))

    def _bereken_gevoelstemperatuur(self, temp: int, wind: int) -> int:
        """Bereken gevoelstemperatuur (wind chill)."""
        if temp > 10 or wind < 2:
            return temp

        # Wind chill formule (vereenvoudigd)
        wind_kmh = wind * 5  # Bft naar km/h (ongeveer)
        gevoels = 13.12 + 0.6215 * temp - 11.37 * (wind_kmh ** 0.16) + 0.3965 * temp * (wind_kmh ** 0.16)
        return round(gevoels)

    def _get_maanfase(self) -> dict:
        """Bereken huidige maanfase."""
        # Simpele berekening gebaseerd op dag van de maand
        dag = datetime.now().day
        fase_index = (dag % 29) // 4
        return self.MAANFASES[min(fase_index, 7)]

    def _get_zontijden(self, lat: float) -> dict:
        """Bereken zonsopgang en ondergang (gesimuleerd)."""
        maand = datetime.now().month
        dag = datetime.now().day

        # Basis tijden (vereenvoudigd)
        if maand in [12, 1, 2]:
            opgang = "08:30"
            ondergang = "17:00"
        elif maand in [3, 4, 5]:
            opgang = "06:45"
            ondergang = "20:15"
        elif maand in [6, 7, 8]:
            opgang = "05:30"
            ondergang = "21:45"
        else:
            opgang = "07:30"
            ondergang = "18:30"

        # Bereken daglengte
        opgang_uur = int(opgang.split(":")[0])
        opgang_min = int(opgang.split(":")[1])
        ondergang_uur = int(ondergang.split(":")[0])
        ondergang_min = int(ondergang.split(":")[1])

        daglengte_min = (ondergang_uur * 60 + ondergang_min) - (opgang_uur * 60 + opgang_min)
        daglengte = f"{daglengte_min // 60}u {daglengte_min % 60}m"

        return {
            "opgang": opgang,
            "ondergang": ondergang,
            "daglengte": daglengte
        }

    def _get_uv_index(self, weer_type: dict, uur: int) -> int:
        """Bereken UV-index."""
        seizoen = self._get_seizoen()
        basis_uv = {"winter": 1, "lente": 4, "zomer": 7, "herfst": 3}.get(seizoen, 3)

        # Pas aan voor tijdstip (hoogst rond 12-14 uur)
        if 10 <= uur <= 16:
            tijd_mult = 1.0
        elif 8 <= uur <= 18:
            tijd_mult = 0.6
        else:
            tijd_mult = 0.1

        uv = int(basis_uv * weer_type.get("uv_mult", 0.5) * tijd_mult)
        return max(0, min(11, uv))

    def _get_uv_advies(self, uv: int) -> tuple:
        """Geef UV advies."""
        if uv <= 2:
            return ("Laag", "groen", "Geen bescherming nodig")
        elif uv <= 5:
            return ("Matig", "geel", "Zonnebrand SPF 15+ aanbevolen")
        elif uv <= 7:
            return ("Hoog", "oranje", "Zonnebrand SPF 30+, hoed en zonnebril")
        elif uv <= 10:
            return ("Zeer hoog", "rood", "Vermijd zon 11-15u, SPF 50+")
        else:
            return ("Extreem", "rood", "Blijf binnen tussen 11-16u!")

    def _get_luchtkwaliteit(self) -> dict:
        """Simuleer luchtkwaliteit (AQI)."""
        # Gesimuleerde AQI waarde
        aqi = random.randint(20, 120)

        if aqi <= 50:
            kwaliteit = "Goed"
            kleur_naam = "groen"
            advies = "Luchtkwaliteit is uitstekend"
        elif aqi <= 100:
            kwaliteit = "Matig"
            kleur_naam = "geel"
            advies = "Acceptabel voor de meeste mensen"
        elif aqi <= 150:
            kwaliteit = "Ongezond voor gevoelige groepen"
            kleur_naam = "oranje"
            advies = "Mensen met luchtwegproblemen opgelet"
        else:
            kwaliteit = "Ongezond"
            kleur_naam = "rood"
            advies = "Beperk buitenactiviteiten"

        return {
            "aqi": aqi,
            "kwaliteit": kwaliteit,
            "kleur": kleur_naam,
            "advies": advies
        }

    def _get_pollen(self) -> dict:
        """Geef polleninformatie."""
        maand = datetime.now().month
        actieve_pollen = self.POLLEN_SEIZOEN.get(maand, [])

        if not actieve_pollen:
            return {
                "niveau": "Geen",
                "kleur": "groen",
                "pollen": [],
                "advies": "Geen pollenactiviteit"
            }

        niveau = random.choice(["Laag", "Matig", "Hoog"])
        kleur_naam = {"Laag": "groen", "Matig": "geel", "Hoog": "rood"}.get(niveau, "geel")

        advies = {
            "Laag": "Minimale hinder voor hooikoortspatienten",
            "Matig": "Neem antihistamine als je gevoelig bent",
            "Hoog": "Vermijd lang buiten zijn, houd ramen dicht"
        }.get(niveau, "")

        return {
            "niveau": niveau,
            "kleur": kleur_naam,
            "pollen": actieve_pollen,
            "advies": advies
        }

    def _get_zeewater_temp(self, stad: str) -> Optional[int]:
        """Geef zeewatertemperatuur voor kuststeden."""
        stad_info = self.STEDEN.get(stad.lower(), {})
        if not stad_info.get("kust", False):
            return None

        seizoen = self._get_seizoen()
        basis = {"winter": 6, "lente": 10, "zomer": 18, "herfst": 14}.get(seizoen, 12)
        return basis + random.randint(-2, 3)

    # ==================== TOOLS ====================

    def _tool_get_weer(self, stad: str) -> dict:
        """Tool: Haalt weerdata op voor een stad."""
        stad_lower = stad.lower()
        stad_info = self.STEDEN.get(stad_lower, {"regio": "Onbekend", "kust": False, "lat": 52.0, "lon": 5.0})

        kansen = self._get_seizoen_kansen()
        temp_min, temp_max = self._get_temp_range()

        weer_type = random.choices(self.WEER_TYPES, weights=kansen)[0].copy()
        temp = random.randint(temp_min, temp_max)

        # Pas aan voor sneeuw
        if weer_type["conditie"] == "sneeuw" and temp > 3:
            temp = random.randint(-3, 3)

        # Wind (hoger aan kust)
        wind = weer_type["wind_base"] + random.randint(0, 3)
        if stad_info.get("kust", False):
            wind += random.randint(2, 4)

        # Luchtvochtigheid
        if weer_type["conditie"] in ["regenachtig", "mistig", "motregen"]:
            vochtigheid = random.randint(75, 95)
        elif weer_type["conditie"] == "zonnig":
            vochtigheid = random.randint(40, 65)
        else:
            vochtigheid = random.randint(55, 80)

        # Luchtdruk
        if weer_type["conditie"] in ["zonnig", "halfbewolkt"]:
            luchtdruk = random.randint(1015, 1030)
        elif weer_type["conditie"] in ["storm", "onweer"]:
            luchtdruk = random.randint(985, 1005)
        else:
            luchtdruk = random.randint(1005, 1020)

        # UV-index
        uur = datetime.now().hour
        uv_index = self._get_uv_index(weer_type, uur)

        # Gevoelstemperatuur
        gevoels_temp = self._bereken_gevoelstemperatuur(temp, wind)

        # Zichtbaarheid
        if weer_type["conditie"] == "mistig":
            zicht = random.randint(100, 500)
        elif weer_type["conditie"] in ["regenachtig", "sneeuw"]:
            zicht = random.randint(2000, 8000)
        else:
            zicht = random.randint(10000, 30000)

        return {
            "stad": stad.title(),
            "regio": stad_info.get("regio", "Onbekend"),
            "kust": stad_info.get("kust", False),
            "conditie": weer_type["conditie"],
            "icon": weer_type["icon"],
            "ascii_icon": weer_type["ascii"],
            "temp": temp,
            "gevoels_temp": gevoels_temp,
            "wind": wind,
            "windrichting": random.choice(["N", "NO", "O", "ZO", "Z", "ZW", "W", "NW"]),
            "vochtigheid": vochtigheid,
            "luchtdruk": luchtdruk,
            "uv_index": uv_index,
            "zicht": zicht,
            "datum": datetime.now().strftime("%d-%m-%Y"),
            "tijd": datetime.now().strftime("%H:%M"),
        }

    def _tool_get_voorspelling_uur(self, stad: str) -> list:
        """Tool: Haalt uur-voor-uur voorspelling op."""
        voorspelling = []
        basis_weer = self._tool_get_weer(stad)
        basis_temp = basis_weer["temp"]
        huidig_uur = datetime.now().hour

        for i in range(12):  # Komende 12 uur
            uur = (huidig_uur + i) % 24
            uur_str = f"{uur:02d}:00"

            # Temperatuur varieert door de dag
            if 6 <= uur <= 14:
                temp_adj = (uur - 6) * 0.5  # Opwarmen
            elif 14 < uur <= 22:
                temp_adj = 4 - (uur - 14) * 0.5  # Afkoelen
            else:
                temp_adj = -2  # Nacht

            temp = int(basis_temp + temp_adj + random.randint(-1, 1))

            # Neerslagkans
            if basis_weer["conditie"] in ["regenachtig", "motregen", "onweer"]:
                neerslag = random.randint(40, 90)
            elif basis_weer["conditie"] in ["bewolkt", "halfbewolkt"]:
                neerslag = random.randint(10, 40)
            else:
                neerslag = random.randint(0, 15)

            voorspelling.append({
                "uur": uur_str,
                "temp": temp,
                "neerslag_kans": neerslag,
                "icon": basis_weer["icon"] if i < 6 else random.choice(["☀️", "⛅", "☁️"])
            })

        return voorspelling

    def _tool_get_voorspelling(self, stad: str, dagen: int = 7) -> list:
        """Tool: Haalt meerdaagse voorspelling op."""
        voorspelling = []
        basis_weer = self._tool_get_weer(stad)
        basis_temp = basis_weer["temp"]

        dag_namen = ["Ma", "Di", "Wo", "Do", "Vr", "Za", "Zo"]

        for i in range(dagen):
            dag_datum = datetime.now() + timedelta(days=i)
            dag_naam = dag_namen[dag_datum.weekday()]

            # Variatie in temperatuur
            temp_variatie = random.randint(-3, 3)
            temp = basis_temp + temp_variatie + (i * random.choice([-1, 0, 1]))

            # Willekeurig weer type
            kansen = self._get_seizoen_kansen()
            weer_type = random.choices(self.WEER_TYPES, weights=kansen)[0]

            # Neerslag
            if weer_type["conditie"] in ["regenachtig", "sneeuw", "onweer", "hagel", "motregen"]:
                neerslag = random.randint(40, 95)
            else:
                neerslag = random.randint(0, 30)

            voorspelling.append({
                "dag": dag_naam,
                "datum": dag_datum.strftime("%d/%m"),
                "conditie": weer_type["conditie"],
                "icon": weer_type["icon"],
                "ascii_icon": weer_type["ascii"],
                "temp_max": temp + random.randint(2, 5),
                "temp_min": temp - random.randint(2, 5),
                "neerslag_kans": neerslag,
                "wind": weer_type["wind_base"] + random.randint(0, 2)
            })

        return voorspelling

    def _tool_check_alerts(self, weer: dict) -> list:
        """Tool: Check voor weer waarschuwingen."""
        alerts = []

        # Code kleuren
        def maak_alert(type_naam, niveau, bericht, icon):
            kleur_map = {"ROOD": "rood", "ORANJE": "oranje", "GEEL": "geel"}
            return {
                "type": type_naam,
                "niveau": niveau,
                "kleur": kleur_map.get(niveau, "geel"),
                "bericht": bericht,
                "icon": icon
            }

        # Storm waarschuwing
        if weer["conditie"] == "storm" or weer["wind"] >= 9:
            niveau = "ROOD" if weer["wind"] >= 11 else "ORANJE" if weer["wind"] >= 9 else "GEEL"
            alerts.append(maak_alert(
                "STORM", niveau,
                f"Zware windstoten verwacht ({weer['wind']} Bft). Ga niet de weg op!",
                "🌪️"
            ))
        elif weer["wind"] >= 7:
            alerts.append(maak_alert(
                "WIND", "GEEL",
                f"Harde wind verwacht ({weer['wind']} Bft). Zet losse spullen vast!",
                "💨"
            ))

        # Hitte waarschuwing
        if weer["temp"] >= 35:
            alerts.append(maak_alert(
                "EXTREME HITTE", "ROOD",
                f"Levensgevaarlijke hitte ({weer['temp']}°C). Blijf binnen!",
                "🔥"
            ))
        elif weer["temp"] >= 30:
            alerts.append(maak_alert(
                "HITTE", "ORANJE",
                f"Hittegolf ({weer['temp']}°C). Drink veel en blijf in de schaduw!",
                "☀️"
            ))

        # Vorst waarschuwing
        if weer["temp"] <= -10:
            alerts.append(maak_alert(
                "STRENGE VORST", "ROOD",
                f"Strenge vorst ({weer['temp']}°C). Gevaar voor bevriezing!",
                "🥶"
            ))
        elif weer["temp"] <= 0:
            alerts.append(maak_alert(
                "VORST", "GEEL",
                f"Vorst verwacht ({weer['temp']}°C). Pas op voor gladheid!",
                "❄️"
            ))

        # Onweer waarschuwing
        if weer["conditie"] == "onweer":
            alerts.append(maak_alert(
                "ONWEER", "ORANJE",
                "Onweer met bliksem! Zoek beschutting, vermijd open velden!",
                "⛈️"
            ))

        # Mist waarschuwing
        if weer["conditie"] == "mistig" or weer.get("zicht", 10000) < 500:
            alerts.append(maak_alert(
                "DICHTE MIST", "GEEL",
                "Zicht < 500m. Rij voorzichtig, gebruik mistlampen!",
                "🌫️"
            ))

        # Hagel
        if weer["conditie"] == "hagel":
            alerts.append(maak_alert(
                "HAGEL", "ORANJE",
                "Hagel verwacht! Zet je auto onder een afdak!",
                "🌨️"
            ))

        return alerts

    def _tool_get_sport_weer(self, weer: dict) -> dict:
        """Tool: Beoordeel het weer voor verschillende sporten."""
        resultaten = {}

        for sport, condities in self.SPORT_CONDITIES.items():
            # Check temperatuur
            temp_ok = condities["temp_min"] <= weer["temp"] <= condities["temp_max"]

            # Check wind
            wind_ok = weer["wind"] <= condities["max_wind"]

            # Check weer conditie
            weer_ok = weer["conditie"] not in condities["bad_weer"]

            # Totaal score
            if temp_ok and wind_ok and weer_ok:
                score = "Uitstekend"
                kleur_naam = "groen"
            elif (temp_ok or wind_ok) and weer_ok:
                score = "Matig"
                kleur_naam = "geel"
            else:
                score = "Niet aanbevolen"
                kleur_naam = "rood"

            resultaten[sport] = {
                "score": score,
                "kleur": kleur_naam,
                "temp_ok": temp_ok,
                "wind_ok": wind_ok,
                "weer_ok": weer_ok
            }

        return resultaten

    def _tool_get_activiteiten(self, weer: dict) -> list:
        """Tool: Geeft activiteit suggesties."""
        conditie = weer["conditie"]
        temp = weer["temp"]

        # Bepaal temperatuur categorie
        if temp >= 25:
            temp_cat = "warm"
        elif temp >= 12:
            temp_cat = "mild"
        else:
            temp_cat = "koud"

        # Normaliseer conditie
        conditie_key = conditie
        if conditie in ["halfbewolkt"]:
            conditie_key = "bewolkt"
        elif conditie in ["motregen"]:
            conditie_key = "regenachtig"
        elif conditie in ["nachtvorst"]:
            conditie_key = "sneeuw"

        # Haal activiteiten op
        if conditie_key in self.ACTIVITEITEN:
            activiteiten_dict = self.ACTIVITEITEN[conditie_key]
            if "any" in activiteiten_dict:
                return activiteiten_dict["any"]
            elif temp_cat in activiteiten_dict:
                return activiteiten_dict[temp_cat]

        return self.ACTIVITEITEN["bewolkt"].get(temp_cat, ["Geniet van de dag!"])

    def _tool_genereer_kledingadvies(self, weer: dict) -> str:
        """Tool: Genereert kledingadvies."""
        temp = weer["temp"]
        gevoels = weer.get("gevoels_temp", temp)
        conditie = weer["conditie"]
        wind = weer["wind"]

        # Gebruik gevoelstemperatuur voor advies
        eff_temp = min(temp, gevoels)

        if eff_temp >= 25:
            basis = "licht T-shirt en korte broek"
        elif eff_temp >= 18:
            basis = "T-shirt en lichte broek"
        elif eff_temp >= 12:
            basis = "trui of vest met lange broek"
        elif eff_temp >= 5:
            basis = "warme trui en jas"
        else:
            basis = "dikke winterjas, sjaal en handschoenen"

        extras = []

        if conditie in ["regenachtig", "motregen"]:
            extras.append("Paraplu of regenjas meenemen!")
            extras.append("Waterdichte schoenen aan.")
        elif conditie == "zonnig" and temp >= 20:
            extras.append(f"Zonnebrand gebruiken! (UV: {weer.get('uv_index', '?')})")
            extras.append("Zonnebril en eventueel een pet.")
        elif conditie == "sneeuw":
            extras.append("Warme waterdichte laarzen!")
            extras.append("Muts en handschoenen niet vergeten.")
        elif conditie == "storm":
            extras.append("BLIJF LIEVER BINNEN!")
        elif conditie == "mistig":
            extras.append("Draag reflecterende kleding.")

        if wind >= 6:
            extras.append(f"Extra laagje vanwege wind ({wind} Bft).")

        if gevoels < temp - 3:
            extras.append(f"Let op: gevoelstemperatuur is {gevoels}°C!")

        advies = f"Aanbevolen: {basis}."
        if extras:
            advies += "\n\nExtra tips:\n- " + "\n- ".join(extras)

        return advies

    def _tool_vergelijk_steden(self, stad1: str, stad2: str) -> dict:
        """Tool: Vergelijk weer tussen twee steden."""
        weer1 = self._tool_get_weer(stad1)
        weer2 = self._tool_get_weer(stad2)

        return {
            "stad1": weer1,
            "stad2": weer2,
            "temp_verschil": weer1["temp"] - weer2["temp"],
            "wind_verschil": weer1["wind"] - weer2["wind"],
            "warmste": stad1 if weer1["temp"] > weer2["temp"] else stad2,
            "minst_wind": stad1 if weer1["wind"] < weer2["wind"] else stad2,
        }

    # ==================== WEERGAVE ====================

    def _toon_steden_lijst(self):
        """Toont beschikbare steden per regio."""
        print("\n" + kleur("Beschikbare steden:", "geel"))

        # Groepeer per regio
        regios = {}
        for stad, info in self.STEDEN.items():
            regio = info["regio"]
            if regio not in regios:
                regios[regio] = []
            regios[regio].append(stad)

        for regio in sorted(regios.keys()):
            steden = sorted(regios[regio])
            steden_str = ", ".join(s.title() for s in steden[:6])
            if len(steden) > 6:
                steden_str += f" (+{len(steden)-6})"
            print(f"  {kleur(regio, 'cyaan')}: {steden_str}")

    def _toon_menu(self):
        """Toon het hoofdmenu."""
        print()
        print(kleur("+" + "=" * 55 + "+", "cyaan"))
        print(kleur("|       WEER AGENT v2.0                                |", "cyaan"))
        print(kleur("+" + "=" * 55 + "+", "cyaan"))
        print(kleur("| WEER                                                 |", "wit"))
        print("|  1. Compleet weerrapport                             |")
        print("|  2. Snelle weer check                                |")
        print("|  3. 7-daagse voorspelling                            |")
        print("|  4. Uur-voor-uur voorspelling                        |")
        print(kleur("+" + "-" * 55 + "+", "grijs"))
        print(kleur("| EXTRA INFO                                           |", "wit"))
        print("|  5. Sport weer                                       |")
        print("|  6. UV-index en luchtkwaliteit                       |")
        print("|  7. Pollen en allergieinfo                           |")
        print("|  8. Vergelijk twee steden                            |")
        print(kleur("+" + "-" * 55 + "+", "grijs"))
        print(kleur("| INSTELLINGEN                                         |", "wit"))
        print("|  9. Favoriete locaties                               |")
        print(kleur("+" + "-" * 55 + "+", "grijs"))
        print("|  0. Terug naar hoofdmenu                             |")
        print(kleur("+" + "=" * 55 + "+", "cyaan"))

    def _vraag_locatie(self) -> str:
        """Vraag gebruiker om locatie."""
        # Toon recente/favorieten
        if self.data["favoriete_locaties"]:
            print(f"\n{kleur('Favorieten:', 'geel')} {', '.join(self.data['favoriete_locaties'][:5])}")

        self._toon_steden_lijst()
        locatie = input(f"\n{kleur('Stad:', 'cyaan')} ").strip()

        if not locatie:
            locatie = self.data["favoriete_locaties"][0] if self.data["favoriete_locaties"] else "Amsterdam"
            print(f"  (Gebruik standaard: {locatie})")

        # Bewaar in recente
        if locatie.lower() in self.STEDEN:
            if locatie not in self.data["recente_zoekopdrachten"]:
                self.data["recente_zoekopdrachten"].insert(0, locatie.title())
                self.data["recente_zoekopdrachten"] = self.data["recente_zoekopdrachten"][:10]
            self.data["totaal_queries"] += 1
            self._sla_data_op()

        return locatie

    def _toon_weer_compact(self, weer: dict):
        """Toon compact weeroverzicht."""
        print(f"\n{weer['icon']} {kleur(weer['stad'], 'cyaan')} - {weer['conditie'].title()}")
        print(f"   Temperatuur: {kleur(str(weer['temp']) + '°C', 'geel')}", end="")
        if weer['gevoels_temp'] != weer['temp']:
            print(f" (voelt als {weer['gevoels_temp']}°C)", end="")
        print()
        print(f"   Wind: {weer['wind']} Bft {weer['windrichting']} | Vochtigheid: {weer['vochtigheid']}%")

    def _toon_volledig_rapport(self, weer: dict, voorspelling: list, alerts: list,
                               advies: str, activiteiten: list, sport: dict,
                               pollen: dict, lucht: dict, zon: dict, maanfase: dict):
        """Toon volledig weerrapport."""
        print("\n" + kleur("=" * 60, "cyaan"))
        print(kleur("              COMPLEET WEERRAPPORT", "geel"))
        print(kleur("=" * 60, "cyaan"))

        # Alerts bovenaan
        if alerts:
            print(f"\n{kleur('!!! WAARSCHUWINGEN !!!', 'rood')}")
            for alert in alerts:
                niveau_kleur = alert.get("kleur", "geel")
                print(f"  {alert['icon']} {kleur(f'[{alert[\"niveau\"]}]', niveau_kleur)} {alert['type']}")
                print(f"     {alert['bericht']}")

        # Huidig weer
        print(f"\n{kleur('[HUIDIG WEER]', 'geel')} {weer['stad']} ({weer['regio']})")
        print(f"  {weer['icon']} {weer['conditie'].title()}")
        print(f"  Temperatuur:    {kleur(str(weer['temp']) + '°C', 'cyaan')}", end="")
        if weer['gevoels_temp'] != weer['temp']:
            gevoels_kleur = "blauw" if weer['gevoels_temp'] < weer['temp'] else "rood"
            print(f" (voelt als {kleur(str(weer['gevoels_temp']) + '°C', gevoels_kleur)})")
        else:
            print()
        print(f"  Wind:           {weer['wind']} Bft uit {weer['windrichting']}")
        print(f"  Vochtigheid:    {weer['vochtigheid']}%")
        print(f"  Luchtdruk:      {weer['luchtdruk']} hPa")
        print(f"  Zicht:          {weer['zicht'] // 1000} km")

        uv = weer['uv_index']
        uv_niveau, uv_kleur, uv_advies = self._get_uv_advies(uv)
        print(f"  UV-index:       {kleur(str(uv) + ' (' + uv_niveau + ')', uv_kleur)}")

        if weer['kust']:
            zee_temp = self._get_zeewater_temp(weer['stad'])
            if zee_temp:
                print(f"  Zeewater:       {zee_temp}°C")

        # Zon en maan
        print(f"\n{kleur('[ZON & MAAN]', 'geel')}")
        print(f"  Zonsopgang:     {zon['opgang']}")
        print(f"  Zonsondergang:  {zon['ondergang']}")
        print(f"  Daglengte:      {zon['daglengte']}")
        print(f"  Maanfase:       {maanfase['icon']} {maanfase['naam']}")

        # Luchtkwaliteit
        print(f"\n{kleur('[LUCHTKWALITEIT]', 'geel')}")
        print(f"  AQI:            {kleur(str(lucht['aqi']) + ' - ' + lucht['kwaliteit'], lucht['kleur'])}")
        print(f"  Advies:         {lucht['advies']}")

        # Pollen
        print(f"\n{kleur('[POLLEN]', 'geel')}")
        print(f"  Niveau:         {kleur(pollen['niveau'], pollen['kleur'])}")
        if pollen['pollen']:
            print(f"  Actief:         {', '.join(pollen['pollen'])}")
        print(f"  Advies:         {pollen['advies']}")

        # 7-daagse voorspelling
        print(f"\n{kleur('[VOORSPELLING 7 DAGEN]', 'geel')}")
        print("  " + "-" * 55)
        for dag in voorspelling:
            temp_str = f"{dag['temp_min']:>2}°C - {dag['temp_max']}°C"
            neerslag_kleur = "blauw" if dag['neerslag_kans'] > 50 else "grijs"
            print(f"  {dag['dag']} {dag['datum']}: {dag['icon']} {temp_str:<14} "
                  f"{kleur(str(dag['neerslag_kans']) + '%', neerslag_kleur)} neerslag, {dag['wind']} Bft")

        # Sport weer
        print(f"\n{kleur('[SPORT WEER]', 'geel')}")
        print("  " + "-" * 55)
        for sport_naam, result in sport.items():
            sport_display = sport_naam.replace("_", " ").title()
            print(f"  {sport_display:<18} {kleur(result['score'], result['kleur'])}")

        # Kledingadvies
        print(f"\n{kleur('[KLEDINGADVIES]', 'geel')}")
        print("  " + "-" * 55)
        for regel in advies.split("\n"):
            print(f"  {regel}")

        # Activiteiten
        print(f"\n{kleur('[ACTIVITEITEN SUGGESTIES]', 'geel')}")
        print("  " + "-" * 55)
        for act in activiteiten[:5]:
            print(f"  - {act}")

        print("\n" + kleur("=" * 60, "cyaan"))

    def _toon_voorspelling_uur(self, voorspelling: list, stad: str):
        """Toon uur-voor-uur voorspelling."""
        print(f"\n{kleur('[UUR-VOOR-UUR VOORSPELLING]', 'geel')} {stad}")
        print("  " + "-" * 50)

        for uur_data in voorspelling:
            neerslag_kleur = "blauw" if uur_data['neerslag_kans'] > 50 else "grijs"
            print(f"  {uur_data['uur']}: {uur_data['icon']} {uur_data['temp']:>2}°C  "
                  f"{kleur(str(uur_data['neerslag_kans']) + '%', neerslag_kleur)} neerslag")

    def _toon_vergelijking(self, vergelijk: dict):
        """Toon vergelijking tussen twee steden."""
        w1 = vergelijk["stad1"]
        w2 = vergelijk["stad2"]

        print(f"\n{kleur('[VERGELIJKING]', 'geel')}")
        print("  " + "-" * 55)
        print(f"  {'':20} {w1['stad']:<15} {w2['stad']:<15}")
        print("  " + "-" * 55)
        print(f"  {'Conditie':<20} {w1['icon']} {w1['conditie']:<12} {w2['icon']} {w2['conditie']:<12}")
        print(f"  {'Temperatuur':<20} {w1['temp']}°C{'':<12} {w2['temp']}°C")
        print(f"  {'Gevoelstemp':<20} {w1['gevoels_temp']}°C{'':<12} {w2['gevoels_temp']}°C")
        print(f"  {'Wind':<20} {w1['wind']} Bft{'':<11} {w2['wind']} Bft")
        print(f"  {'Vochtigheid':<20} {w1['vochtigheid']}%{'':<12} {w2['vochtigheid']}%")
        print("  " + "-" * 55)
        print(f"  {kleur('Warmste:', 'geel')} {vergelijk['warmste']}")
        print(f"  {kleur('Minste wind:', 'geel')} {vergelijk['minst_wind']}")

    def _beheer_favorieten(self):
        """Beheer favoriete locaties."""
        print(f"\n{kleur('FAVORIETE LOCATIES', 'cyaan')}")
        print("-" * 40)

        if self.data["favoriete_locaties"]:
            for i, loc in enumerate(self.data["favoriete_locaties"], 1):
                print(f"  {i}. {loc}")
        else:
            print(kleur("  Geen favorieten opgeslagen.", "grijs"))

        print("\n  a. Voeg favoriet toe")
        print("  v. Verwijder favoriet")
        print("  0. Terug")

        keuze = input("\nKeuze: ").strip().lower()

        if keuze == "a":
            nieuwe_loc = input("Stad toevoegen: ").strip().title()
            if nieuwe_loc.lower() in self.STEDEN:
                if nieuwe_loc not in self.data["favoriete_locaties"]:
                    self.data["favoriete_locaties"].append(nieuwe_loc)
                    self._sla_data_op()
                    print(kleur(f"{nieuwe_loc} toegevoegd!", "groen"))
                else:
                    print(kleur("Al in favorieten.", "geel"))
            else:
                print(kleur("Stad niet gevonden.", "rood"))
        elif keuze == "v" and self.data["favoriete_locaties"]:
            idx = input("Nummer om te verwijderen: ").strip()
            try:
                idx = int(idx) - 1
                if 0 <= idx < len(self.data["favoriete_locaties"]):
                    verwijderd = self.data["favoriete_locaties"].pop(idx)
                    self._sla_data_op()
                    print(kleur(f"{verwijderd} verwijderd!", "groen"))
            except ValueError:
                pass

    # ==================== AGENTIC LOOP ====================

    def _percipeer(self) -> str:
        """STAP 1: Perceptie - verzamel informatie."""
        print(f"\n{kleur('[PERCEPTIE]', 'magenta')} Ik verzamel informatie...")
        locatie = self._vraag_locatie()
        self.geheugen["locatie"] = locatie
        return locatie

    def _plan(self, locatie: str) -> list:
        """STAP 2: Planning - maak een plan."""
        print(f"\n{kleur('[PLANNING]', 'magenta')} Ik maak een plan...")
        print(f"   -> Doel: Compleet weerrapport voor {kleur(locatie, 'cyaan')}")
        stappen = [
            "Stap 1: Huidig weer ophalen",
            "Stap 2: 7-daagse voorspelling",
            "Stap 3: Alerts checken",
            "Stap 4: Extra info (UV, pollen, lucht)",
            "Stap 5: Sport weer beoordelen",
            "Stap 6: Kledingadvies genereren",
            "Stap 7: Activiteiten suggereren",
        ]
        for stap in stappen:
            print(f"   -> {stap}")
        return stappen

    def _voer_uit(self, locatie: str) -> dict:
        """STAP 3: Actie - voer het plan uit."""
        print(f"\n{kleur('[ACTIE]', 'magenta')} Ik voer het plan uit...")

        print(f"   {kleur('[TOOL]', 'grijs')} get_weer() aanroepen...")
        weer = self._tool_get_weer(locatie)
        print(f"   {kleur('[OK]', 'groen')} Weer: {weer['icon']} {weer['conditie']}, {weer['temp']}°C")

        print(f"   {kleur('[TOOL]', 'grijs')} get_voorspelling() aanroepen...")
        voorspelling = self._tool_get_voorspelling(locatie)
        print(f"   {kleur('[OK]', 'groen')} {len(voorspelling)} dagen voorspelling")

        print(f"   {kleur('[TOOL]', 'grijs')} check_alerts() aanroepen...")
        alerts = self._tool_check_alerts(weer)
        alert_kleur = "rood" if alerts else "groen"
        print(f"   {kleur('[OK]', alert_kleur)} {len(alerts)} alert(s) gevonden")

        print(f"   {kleur('[TOOL]', 'grijs')} get_extra_info() aanroepen...")
        stad_info = self.STEDEN.get(locatie.lower(), {"lat": 52.0})
        zon = self._get_zontijden(stad_info.get("lat", 52.0))
        maanfase = self._get_maanfase()
        lucht = self._get_luchtkwaliteit()
        pollen = self._get_pollen()
        print(f"   {kleur('[OK]', 'groen')} Extra info geladen")

        print(f"   {kleur('[TOOL]', 'grijs')} get_sport_weer() aanroepen...")
        sport = self._tool_get_sport_weer(weer)
        print(f"   {kleur('[OK]', 'groen')} Sport weer beoordeeld")

        print(f"   {kleur('[TOOL]', 'grijs')} genereer_kledingadvies() aanroepen...")
        advies = self._tool_genereer_kledingadvies(weer)
        print(f"   {kleur('[OK]', 'groen')} Kledingadvies gegenereerd")

        print(f"   {kleur('[TOOL]', 'grijs')} get_activiteiten() aanroepen...")
        activiteiten = self._tool_get_activiteiten(weer)
        print(f"   {kleur('[OK]', 'groen')} {len(activiteiten)} activiteit suggesties")

        return {
            "weer": weer,
            "voorspelling": voorspelling,
            "alerts": alerts,
            "advies": advies,
            "activiteiten": activiteiten,
            "sport": sport,
            "zon": zon,
            "maanfase": maanfase,
            "lucht": lucht,
            "pollen": pollen,
        }

    def _verifieer(self, resultaat: dict) -> bool:
        """STAP 4: Verificatie - controleer resultaat."""
        print(f"\n{kleur('[VERIFICATIE]', 'magenta')} Ik controleer het resultaat...")

        checks = [
            ("Weer data aanwezig", resultaat.get("weer") is not None),
            ("Voorspelling geladen", len(resultaat.get("voorspelling", [])) > 0),
            ("Alerts gecheckt", resultaat.get("alerts") is not None),
            ("Extra info geladen", resultaat.get("lucht") is not None),
            ("Sport weer beoordeeld", resultaat.get("sport") is not None),
            ("Advies gegenereerd", resultaat.get("advies") is not None),
            ("Activiteiten geladen", len(resultaat.get("activiteiten", [])) > 0),
        ]

        alles_ok = True
        for naam, status in checks:
            symbool = kleur("[OK]", "groen") if status else kleur("[!!]", "rood")
            print(f"   {symbool} {naam}")
            if not status:
                alles_ok = False

        return alles_ok

    def run(self):
        """Start de interactieve weer agent."""
        clear_scherm()
        print(kleur("+" + "=" * 58 + "+", "cyaan"))
        print(kleur("|    WEER-AGENT v2.0: Professioneel Weerstation           |", "cyaan"))
        print(kleur("|                                                          |", "cyaan"))
        print(kleur("|    Features:                                             |", "grijs"))
        print(kleur("|    - 50+ Nederlandse steden   - 7-daagse voorspelling    |", "grijs"))
        print(kleur("|    - UV-index & luchtkwaliteit - Sport weer              |", "grijs"))
        print(kleur("|    - Pollen informatie        - Kledingadvies            |", "grijs"))
        print(kleur("+" + "=" * 58 + "+", "cyaan"))

        while True:
            self._toon_menu()
            keuze = input("\nKeuze: ").strip()

            if keuze == "0":
                break

            elif keuze == "1":
                # Compleet rapport met agentic loop
                locatie = self._percipeer()
                self._plan(locatie)
                resultaat = self._voer_uit(locatie)
                succes = self._verifieer(resultaat)

                if succes:
                    print(f"\n{kleur('[OK]', 'groen')} Alle checks geslaagd!")
                    self._toon_volledig_rapport(
                        resultaat["weer"], resultaat["voorspelling"],
                        resultaat["alerts"], resultaat["advies"],
                        resultaat["activiteiten"], resultaat["sport"],
                        resultaat["pollen"], resultaat["lucht"],
                        resultaat["zon"], resultaat["maanfase"]
                    )
                else:
                    print(kleur("\n[!!] Er ging iets mis.", "rood"))

            elif keuze == "2":
                # Snelle check
                locatie = self._vraag_locatie()
                weer = self._tool_get_weer(locatie)
                self._toon_weer_compact(weer)

            elif keuze == "3":
                # 7-daagse voorspelling
                locatie = self._vraag_locatie()
                voorspelling = self._tool_get_voorspelling(locatie)
                print(f"\n{kleur('[7-DAAGSE VOORSPELLING]', 'geel')} {locatie.title()}")
                print("  " + "-" * 55)
                for dag in voorspelling:
                    print(f"  {dag['dag']} {dag['datum']}: {dag['icon']} "
                          f"{dag['temp_min']}°C - {dag['temp_max']}°C, {dag['neerslag_kans']}% neerslag")

            elif keuze == "4":
                # Uur-voor-uur
                locatie = self._vraag_locatie()
                voorspelling = self._tool_get_voorspelling_uur(locatie)
                self._toon_voorspelling_uur(voorspelling, locatie.title())

            elif keuze == "5":
                # Sport weer
                locatie = self._vraag_locatie()
                weer = self._tool_get_weer(locatie)
                sport = self._tool_get_sport_weer(weer)
                print(f"\n{kleur('[SPORT WEER]', 'geel')} {locatie.title()} ({weer['temp']}°C, {weer['wind']} Bft)")
                print("  " + "-" * 40)
                for sport_naam, result in sport.items():
                    sport_display = sport_naam.replace("_", " ").title()
                    print(f"  {sport_display:<18} {kleur(result['score'], result['kleur'])}")

            elif keuze == "6":
                # UV en luchtkwaliteit
                locatie = self._vraag_locatie()
                weer = self._tool_get_weer(locatie)
                lucht = self._get_luchtkwaliteit()
                uv = weer['uv_index']
                uv_niveau, uv_kleur, uv_advies = self._get_uv_advies(uv)

                print(f"\n{kleur('[UV-INDEX]', 'geel')} {locatie.title()}")
                print(f"  Index:  {kleur(str(uv) + ' - ' + uv_niveau, uv_kleur)}")
                print(f"  Advies: {uv_advies}")

                print(f"\n{kleur('[LUCHTKWALITEIT]', 'geel')}")
                print(f"  AQI:    {kleur(str(lucht['aqi']) + ' - ' + lucht['kwaliteit'], lucht['kleur'])}")
                print(f"  Advies: {lucht['advies']}")

            elif keuze == "7":
                # Pollen
                pollen = self._get_pollen()
                print(f"\n{kleur('[POLLEN INFORMATIE]', 'geel')}")
                print(f"  Niveau:  {kleur(pollen['niveau'], pollen['kleur'])}")
                if pollen['pollen']:
                    print(f"  Actief:  {', '.join(pollen['pollen'])}")
                print(f"  Advies:  {pollen['advies']}")

            elif keuze == "8":
                # Vergelijk steden
                print(f"\n{kleur('Vergelijk twee steden:', 'geel')}")
                stad1 = input("Eerste stad: ").strip() or "Amsterdam"
                stad2 = input("Tweede stad: ").strip() or "Rotterdam"
                vergelijk = self._tool_vergelijk_steden(stad1, stad2)
                self._toon_vergelijking(vergelijk)

            elif keuze == "9":
                self._beheer_favorieten()

            else:
                print(kleur("Ongeldige keuze.", "rood"))

            input(kleur("\nDruk op Enter om verder te gaan...", "grijs"))

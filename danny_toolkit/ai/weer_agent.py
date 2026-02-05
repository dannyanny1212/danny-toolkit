"""
Weer Agent - Uitgebreide versie met voorspellingen en alerts.
"""

import random
from datetime import datetime, timedelta

from ..core.utils import clear_scherm


class WeerAgentApp:
    """
    Weer agent die de Agentic Loop demonstreert:
    1. Perceptie: Input verzamelen
    2. Planning: Beslissen wat te doen
    3. Actie: Tools gebruiken
    4. Verificatie: Resultaat checken
    """

    # Nederlandse steden database
    STEDEN = {
        "amsterdam": {"regio": "Noord-Holland", "kust": False},
        "rotterdam": {"regio": "Zuid-Holland", "kust": False},
        "den haag": {"regio": "Zuid-Holland", "kust": True},
        "utrecht": {"regio": "Utrecht", "kust": False},
        "eindhoven": {"regio": "Noord-Brabant", "kust": False},
        "groningen": {"regio": "Groningen", "kust": False},
        "tilburg": {"regio": "Noord-Brabant", "kust": False},
        "almere": {"regio": "Flevoland", "kust": False},
        "breda": {"regio": "Noord-Brabant", "kust": False},
        "nijmegen": {"regio": "Gelderland", "kust": False},
        "arnhem": {"regio": "Gelderland", "kust": False},
        "haarlem": {"regio": "Noord-Holland", "kust": False},
        "zwolle": {"regio": "Overijssel", "kust": False},
        "maastricht": {"regio": "Limburg", "kust": False},
        "leiden": {"regio": "Zuid-Holland", "kust": False},
        "dordrecht": {"regio": "Zuid-Holland", "kust": False},
        "enschede": {"regio": "Overijssel", "kust": False},
        "scheveningen": {"regio": "Zuid-Holland", "kust": True},
        "zandvoort": {"regio": "Noord-Holland", "kust": True},
        "vlissingen": {"regio": "Zeeland", "kust": True},
    }

    # Weer types met eigenschappen
    WEER_TYPES = [
        {"conditie": "zonnig", "icon": "[ZON]", "wind_base": 2},
        {"conditie": "bewolkt", "icon": "[WOLK]", "wind_base": 3},
        {"conditie": "regenachtig", "icon": "[REGEN]", "wind_base": 4},
        {"conditie": "sneeuw", "icon": "[SNEEUW]", "wind_base": 2},
        {"conditie": "storm", "icon": "[STORM]", "wind_base": 7},
        {"conditie": "mistig", "icon": "[MIST]", "wind_base": 1},
        {"conditie": "onweer", "icon": "[BLIKSEM]", "wind_base": 5},
        {"conditie": "hagel", "icon": "[HAGEL]", "wind_base": 4},
    ]

    # Activiteiten database
    ACTIVITEITEN = {
        "zonnig": {
            "warm": ["Ga naar het strand", "Picknicken in het park", "Terrasje pakken",
                    "Fietsen door de natuur", "BBQ met vrienden"],
            "mild": ["Wandelen in het bos", "Stadsbezoek", "Tuinieren",
                    "Outdoor sport", "Markt bezoeken"],
            "koud": ["Winterwandeling", "Schaatsen (als het vriest)", "Fotografie buiten"]
        },
        "bewolkt": {
            "warm": ["Museum bezoek", "Shopping", "Filmmarathon thuis"],
            "mild": ["Wandelen", "Fietsen", "Koffie drinken in de stad"],
            "koud": ["Binnen sporten", "Bioscoop", "Wellness/sauna"]
        },
        "regenachtig": {
            "any": ["Museum bezoek", "Bioscoop", "Escape room", "Bowlen",
                   "Lekker lezen met thee", "Puzzelen", "Gamen"]
        },
        "sneeuw": {
            "any": ["Sneeuwpop maken", "Sleetje rijden", "Warme chocomelk drinken",
                   "Winterfoto's maken", "Gezellig binnen blijven"]
        },
        "storm": {
            "any": ["BLIJF BINNEN", "Films kijken", "Bordspellen", "Bakken"]
        },
        "onweer": {
            "any": ["BLIJF BINNEN", "Onweer bekijken (veilig)", "Lezen", "Gamen"]
        }
    }

    def __init__(self):
        self.naam = "WeerWijzer"
        self.versie = "2.0"
        self.geheugen = {}

    def _get_seizoen_kansen(self) -> list:
        """Geeft weerkansen gebaseerd op seizoen."""
        maand = datetime.now().month
        # [zonnig, bewolkt, regen, sneeuw, storm, mist, onweer, hagel]
        if maand in [12, 1, 2]:  # Winter
            return [0.10, 0.25, 0.20, 0.20, 0.10, 0.10, 0.03, 0.02]
        elif maand in [3, 4, 5]:  # Lente
            return [0.25, 0.30, 0.25, 0.02, 0.05, 0.08, 0.03, 0.02]
        elif maand in [6, 7, 8]:  # Zomer
            return [0.45, 0.25, 0.15, 0.00, 0.03, 0.02, 0.08, 0.02]
        else:  # Herfst
            return [0.15, 0.30, 0.30, 0.00, 0.10, 0.10, 0.03, 0.02]

    def _get_temp_range(self) -> tuple:
        """Geeft temperatuur range gebaseerd op seizoen."""
        maand = datetime.now().month
        if maand in [12, 1, 2]:
            return (-5, 10)
        elif maand in [3, 4, 5]:
            return (8, 20)
        elif maand in [6, 7, 8]:
            return (18, 32)
        else:
            return (8, 18)

    def _tool_get_weer(self, stad: str) -> dict:
        """Tool: Haalt weerdata op voor een stad."""
        stad_lower = stad.lower()
        stad_info = self.STEDEN.get(stad_lower, {"regio": "Onbekend", "kust": False})

        kansen = self._get_seizoen_kansen()
        temp_min, temp_max = self._get_temp_range()

        weer_type = random.choices(self.WEER_TYPES, weights=kansen)[0].copy()
        temp = random.randint(temp_min, temp_max)

        # Pas aan voor sneeuw
        if weer_type["conditie"] == "sneeuw" and temp > 3:
            temp = random.randint(-3, 3)

        # Wind (hoger aan kust)
        wind = weer_type["wind_base"] + random.randint(0, 3)
        if stad_info["kust"]:
            wind += random.randint(2, 4)

        # Luchtvochtigheid
        if weer_type["conditie"] in ["regenachtig", "mistig"]:
            vochtigheid = random.randint(75, 95)
        elif weer_type["conditie"] == "zonnig":
            vochtigheid = random.randint(40, 65)
        else:
            vochtigheid = random.randint(55, 80)

        return {
            "stad": stad.title(),
            "regio": stad_info["regio"],
            "kust": stad_info["kust"],
            "conditie": weer_type["conditie"],
            "icon": weer_type["icon"],
            "temp": temp,
            "wind": wind,
            "vochtigheid": vochtigheid,
            "datum": datetime.now().strftime("%d-%m-%Y"),
            "tijd": datetime.now().strftime("%H:%M"),
        }

    def _tool_get_voorspelling(self, stad: str, dagen: int = 5) -> list:
        """Tool: Haalt meerdaagse voorspelling op."""
        voorspelling = []
        basis_weer = self._tool_get_weer(stad)
        basis_temp = basis_weer["temp"]

        for i in range(dagen):
            dag_datum = datetime.now() + timedelta(days=i)
            dag_naam = ["Ma", "Di", "Wo", "Do", "Vr", "Za", "Zo"][dag_datum.weekday()]

            # Variatie in temperatuur (-3 tot +3 per dag)
            temp_variatie = random.randint(-3, 3)
            temp = basis_temp + temp_variatie + (i * random.choice([-1, 0, 1]))

            # Willekeurig weer type
            kansen = self._get_seizoen_kansen()
            weer_type = random.choices(self.WEER_TYPES, weights=kansen)[0]

            voorspelling.append({
                "dag": dag_naam,
                "datum": dag_datum.strftime("%d/%m"),
                "conditie": weer_type["conditie"],
                "icon": weer_type["icon"],
                "temp_max": temp + random.randint(2, 5),
                "temp_min": temp - random.randint(2, 5),
                "neerslag_kans": random.randint(0, 100) if weer_type["conditie"] in
                                ["regenachtig", "sneeuw", "onweer", "hagel"] else random.randint(0, 30)
            })

        return voorspelling

    def _tool_check_alerts(self, weer: dict) -> list:
        """Tool: Check voor weer waarschuwingen."""
        alerts = []

        # Storm waarschuwing
        if weer["conditie"] == "storm" or weer["wind"] >= 8:
            alerts.append({
                "type": "STORM",
                "niveau": "ORANJE" if weer["wind"] >= 10 else "GEEL",
                "bericht": f"Harde wind verwacht ({weer['wind']} Bft). Zet losse spullen vast!",
                "icon": "[!STORM!]"
            })

        # Hitte waarschuwing
        if weer["temp"] >= 30:
            alerts.append({
                "type": "HITTE",
                "niveau": "ORANJE" if weer["temp"] >= 35 else "GEEL",
                "bericht": f"Extreme hitte ({weer['temp']}C). Drink voldoende en blijf in de schaduw!",
                "icon": "[!HITTE!]"
            })

        # Vorst waarschuwing
        if weer["temp"] <= 0:
            alerts.append({
                "type": "VORST",
                "niveau": "ORANJE" if weer["temp"] <= -5 else "GEEL",
                "bericht": f"Vorst verwacht ({weer['temp']}C). Pas op voor gladheid!",
                "icon": "[!VORST!]"
            })

        # Onweer waarschuwing
        if weer["conditie"] == "onweer":
            alerts.append({
                "type": "ONWEER",
                "niveau": "GEEL",
                "bericht": "Onweer verwacht. Zoek beschutting en vermijd open velden!",
                "icon": "[!BLIKSEM!]"
            })

        # Dichte mist
        if weer["conditie"] == "mistig":
            alerts.append({
                "type": "MIST",
                "niveau": "GEEL",
                "bericht": "Dichte mist. Rij voorzichtig en gebruik mistlampen!",
                "icon": "[!MIST!]"
            })

        # Hagel
        if weer["conditie"] == "hagel":
            alerts.append({
                "type": "HAGEL",
                "niveau": "GEEL",
                "bericht": "Hagel verwacht. Zet je auto onder een afdak!",
                "icon": "[!HAGEL!]"
            })

        return alerts

    def _tool_get_activiteiten(self, weer: dict) -> list:
        """Tool: Geeft activiteit suggesties op basis van weer."""
        conditie = weer["conditie"]
        temp = weer["temp"]

        # Bepaal temperatuur categorie
        if temp >= 25:
            temp_cat = "warm"
        elif temp >= 12:
            temp_cat = "mild"
        else:
            temp_cat = "koud"

        # Haal activiteiten op
        if conditie in self.ACTIVITEITEN:
            activiteiten_dict = self.ACTIVITEITEN[conditie]
            if "any" in activiteiten_dict:
                return activiteiten_dict["any"]
            elif temp_cat in activiteiten_dict:
                return activiteiten_dict[temp_cat]

        # Fallback naar bewolkt
        return self.ACTIVITEITEN["bewolkt"].get(temp_cat, ["Geniet van de dag!"])

    def _tool_genereer_kledingadvies(self, weer: dict) -> str:
        """Tool: Genereert kledingadvies."""
        temp = weer["temp"]
        conditie = weer["conditie"]
        wind = weer["wind"]

        if temp >= 25:
            basis = "een licht T-shirt en korte broek"
        elif temp >= 18:
            basis = "een T-shirt en een lichte broek"
        elif temp >= 12:
            basis = "een trui of vest met lange broek"
        elif temp >= 5:
            basis = "een warme trui en jas"
        else:
            basis = "een dikke winterjas, sjaal en handschoenen"

        extras = []
        if conditie == "regenachtig":
            extras.append("Paraplu of regenjas meenemen!")
            extras.append("Waterdichte schoenen aan.")
        elif conditie == "zonnig" and temp >= 20:
            extras.append("Zonnebrand factor 30+ gebruiken!")
            extras.append("Zonnebril en eventueel een pet.")
        elif conditie == "sneeuw":
            extras.append("Warme waterdichte laarzen!")
            extras.append("Muts en handschoenen niet vergeten.")
        elif conditie == "storm":
            extras.append("BLIJF LIEVER BINNEN!")
            extras.append("Geen paraplu (waait weg).")
        elif conditie == "mistig":
            extras.append("Draag reflecterende kleding.")

        if wind >= 6:
            extras.append(f"Extra laagje vanwege wind ({wind} Bft).")

        advies = f"Ik raad aan: {basis}."
        if extras:
            advies += "\n\nExtra tips:\n- " + "\n- ".join(extras)

        return advies

    def _toon_steden_lijst(self):
        """Toont beschikbare steden."""
        print("\nBeschikbare steden:")
        steden_sorted = sorted(self.STEDEN.keys())
        for i in range(0, len(steden_sorted), 4):
            rij = steden_sorted[i:i+4]
            print("  " + ", ".join(s.title() for s in rij))

    def _percipeer(self) -> str:
        """STAP 1: Perceptie - verzamel informatie."""
        print("\n" + "=" * 55)
        print(f"[AGENT] {self.naam} v{self.versie}")
        print("=" * 55)
        print("\n[PERCEPTIE] Ik verzamel informatie...")

        self._toon_steden_lijst()
        locatie = input("\nIn welke stad ben je? ").strip()

        if not locatie:
            locatie = "Amsterdam"
            print(f"   (Geen input, ik gebruik '{locatie}')")
        elif locatie.lower() not in self.STEDEN:
            print(f"   ('{locatie}' niet in database, ik genereer weer)")

        self.geheugen["locatie"] = locatie
        return locatie

    def _plan(self, locatie: str) -> list:
        """STAP 2: Planning - maak een plan."""
        print("\n[PLANNING] Ik maak een plan...")
        print(f"   -> Doel: Compleet weerrapport voor {locatie}")
        stappen = [
            "Stap 1: Huidig weer ophalen",
            "Stap 2: 5-daagse voorspelling",
            "Stap 3: Alerts checken",
            "Stap 4: Kledingadvies genereren",
            "Stap 5: Activiteiten suggereren",
        ]
        for stap in stappen:
            print(f"   -> {stap}")
        return stappen

    def _voer_uit(self, locatie: str) -> dict:
        """STAP 3: Actie - voer het plan uit."""
        print("\n[ACTIE] Ik voer het plan uit...")

        print("   [TOOL] get_weer() aanroepen...")
        weer = self._tool_get_weer(locatie)
        print(f"   [OK] Weer: {weer['icon']} {weer['conditie']}, {weer['temp']}C")

        print("   [TOOL] get_voorspelling() aanroepen...")
        voorspelling = self._tool_get_voorspelling(locatie)
        print(f"   [OK] {len(voorspelling)} dagen voorspelling")

        print("   [TOOL] check_alerts() aanroepen...")
        alerts = self._tool_check_alerts(weer)
        print(f"   [OK] {len(alerts)} alert(s) gevonden")

        print("   [TOOL] genereer_kledingadvies() aanroepen...")
        advies = self._tool_genereer_kledingadvies(weer)
        print("   [OK] Kledingadvies gegenereerd")

        print("   [TOOL] get_activiteiten() aanroepen...")
        activiteiten = self._tool_get_activiteiten(weer)
        print(f"   [OK] {len(activiteiten)} activiteit suggesties")

        return {
            "weer": weer,
            "voorspelling": voorspelling,
            "alerts": alerts,
            "advies": advies,
            "activiteiten": activiteiten
        }

    def _verifieer(self, resultaat: dict) -> bool:
        """STAP 4: Verificatie - controleer resultaat."""
        print("\n[VERIFICATIE] Ik controleer het resultaat...")

        checks = [
            ("Weer data aanwezig", resultaat.get("weer") is not None),
            ("Voorspelling geladen", len(resultaat.get("voorspelling", [])) > 0),
            ("Alerts gecheckt", resultaat.get("alerts") is not None),
            ("Advies gegenereerd", resultaat.get("advies") is not None),
            ("Activiteiten geladen", len(resultaat.get("activiteiten", [])) > 0),
        ]

        alles_ok = True
        for naam, status in checks:
            symbool = "[OK]" if status else "[!!]"
            print(f"   {symbool} {naam}")
            if not status:
                alles_ok = False

        return alles_ok

    def _presenteer(self, resultaat: dict):
        """Presenteert het eindresultaat."""
        weer = resultaat["weer"]
        voorspelling = resultaat["voorspelling"]
        alerts = resultaat["alerts"]
        advies = resultaat["advies"]
        activiteiten = resultaat["activiteiten"]

        print("\n" + "=" * 55)
        print("                 WEERRAPPORT")
        print("=" * 55)

        # Alerts bovenaan (indien aanwezig)
        if alerts:
            print("\n!!! WAARSCHUWINGEN !!!")
            for alert in alerts:
                print(f"  {alert['icon']} [{alert['niveau']}] {alert['type']}")
                print(f"     {alert['bericht']}")

        # Huidig weer
        print(f"\n[HUIDIGE WEER] {weer['stad']} ({weer['regio']})")
        print(f"  {weer['icon']} {weer['conditie'].title()}")
        print(f"  Temperatuur: {weer['temp']}C")
        print(f"  Wind: {weer['wind']} Bft")
        print(f"  Luchtvochtigheid: {weer['vochtigheid']}%")
        if weer['kust']:
            print("  (Kustlocatie)")

        # 5-daagse voorspelling
        print("\n[VOORSPELLING 5 DAGEN]")
        print("  " + "-" * 50)
        for dag in voorspelling:
            print(f"  {dag['dag']} {dag['datum']}: {dag['icon']} "
                  f"{dag['temp_min']}C - {dag['temp_max']}C "
                  f"({dag['neerslag_kans']}% neerslag)")

        # Kledingadvies
        print("\n[KLEDINGADVIES]")
        print("  " + "-" * 50)
        for regel in advies.split("\n"):
            print(f"  {regel}")

        # Activiteiten
        print("\n[ACTIVITEITEN SUGGESTIES]")
        print("  " + "-" * 50)
        for act in activiteiten[:5]:
            print(f"  - {act}")

        print("\n" + "=" * 55)

    def run(self):
        """Voert de volledige Agentic Loop uit."""
        clear_scherm()
        print("\n" + "=" * 55)
        print("        WEER-AGENT v2.0: Compleet Weerrapport")
        print("        Met voorspelling, alerts en activiteiten!")
        print("=" * 55)

        while True:
            try:
                locatie = self._percipeer()
                self._plan(locatie)
                resultaat = self._voer_uit(locatie)
                succes = self._verifieer(resultaat)

                if succes:
                    print("\n[OK] Alle checks geslaagd!")
                    self._presenteer(resultaat)
                else:
                    print("\n[!!] Er ging iets mis. Probeer opnieuw.")
                    continue

                print("\n" + "-" * 55)
                opnieuw = input("Wil je nog een locatie checken? (j/n): ").lower().strip()

                if opnieuw != "j":
                    print("\nBedankt voor het gebruiken van WeerWijzer v2.0!")
                    break

                self.geheugen = {}
                clear_scherm()

            except KeyboardInterrupt:
                print("\n\nTot ziens!")
                break

        input("\nDruk op Enter om terug te gaan...")

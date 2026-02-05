"""
Weer Agent - Demonstreert de Agentic Loop.
"""

import random
from datetime import datetime

from ..core.utils import clear_scherm


class WeerAgentApp:
    """
    Weer agent die de Agentic Loop demonstreert:
    1. Perceptie: Input verzamelen
    2. Planning: Beslissen wat te doen
    3. Actie: Tools gebruiken
    4. Verificatie: Resultaat checken
    """

    def __init__(self):
        self.naam = "WeerWijzer"
        self.versie = "1.0"
        self.geheugen = {}

    def _tool_get_weer(self, stad: str) -> dict:
        """Tool: Haalt weerdata op voor een stad."""
        weer_types = [
            {"conditie": "zonnig", "temp": random.randint(20, 30), "icon": "[ZON]"},
            {"conditie": "bewolkt", "temp": random.randint(12, 20), "icon": "[WOLK]"},
            {"conditie": "regenachtig", "temp": random.randint(8, 15), "icon": "[REGEN]"},
            {"conditie": "sneeuw", "temp": random.randint(-5, 3), "icon": "[SNEEUW]"},
            {"conditie": "storm", "temp": random.randint(10, 18), "icon": "[STORM]"},
            {"conditie": "mistig", "temp": random.randint(5, 12), "icon": "[MIST]"},
        ]

        maand = datetime.now().month
        if maand in [12, 1, 2]:
            kansen = [0.05, 0.2, 0.2, 0.3, 0.1, 0.15]
        elif maand in [3, 4, 5]:
            kansen = [0.3, 0.3, 0.25, 0.0, 0.05, 0.1]
        elif maand in [6, 7, 8]:
            kansen = [0.5, 0.25, 0.15, 0.0, 0.05, 0.05]
        else:
            kansen = [0.15, 0.3, 0.3, 0.0, 0.1, 0.15]

        weer = random.choices(weer_types, weights=kansen)[0]
        weer["stad"] = stad.title()
        return weer

    def _tool_genereer_kledingadvies(self, weer: dict) -> str:
        """Tool: Genereert kledingadvies."""
        temp = weer["temp"]
        conditie = weer["conditie"]

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
            extras.append("Vergeet je paraplu niet!")
            extras.append("Draag waterdichte schoenen.")
        elif conditie == "zonnig" and temp >= 20:
            extras.append("Neem zonnebrand mee!")
            extras.append("Een zonnebril is handig.")
        elif conditie == "sneeuw":
            extras.append("Draag warme laarzen!")
            extras.append("Een muts houdt je hoofd warm.")
        elif conditie == "storm":
            extras.append("Blijf liever binnen als het kan!")
        elif conditie == "mistig":
            extras.append("Draag iets reflecterends voor zichtbaarheid.")

        advies = f"Ik raad aan: {basis}."
        if extras:
            advies += "\n\nExtra tips:\n- " + "\n- ".join(extras)

        return advies

    def _percipeer(self) -> str:
        """STAP 1: Perceptie - verzamel informatie."""
        print("\n" + "=" * 50)
        print(f"[AGENT] {self.naam} v{self.versie}")
        print("=" * 50)
        print("\n[PERCEPTIE] Ik verzamel informatie...\n")

        locatie = input("In welke stad ben je? ").strip()
        if not locatie:
            locatie = "Amsterdam"
            print(f"   (Geen input, ik gebruik '{locatie}')")

        self.geheugen["locatie"] = locatie
        return locatie

    def _plan(self, locatie: str) -> list:
        """STAP 2: Planning - maak een plan."""
        print("\n[PLANNING] Ik maak een plan...")
        print(f"   -> Doel: Kledingadvies geven voor {locatie}")
        print("   -> Stap 1: Weer ophalen")
        print("   -> Stap 2: Advies genereren")
        print("   -> Stap 3: Resultaat presenteren")
        return ["haal_weer", "genereer_advies", "presenteer"]

    def _voer_uit(self, locatie: str) -> dict:
        """STAP 3: Actie - voer het plan uit."""
        print("\n[ACTIE] Ik voer het plan uit...")

        print("   [TOOL] get_weer() aanroepen...")
        weer = self._tool_get_weer(locatie)
        self.geheugen["weer"] = weer
        print(f"   [OK] Weer opgehaald: {weer['icon']} {weer['conditie']}, {weer['temp']}C")

        print("   [TOOL] genereer_kledingadvies() aanroepen...")
        advies = self._tool_genereer_kledingadvies(weer)
        self.geheugen["advies"] = advies
        print("   [OK] Advies gegenereerd!")

        return {"weer": weer, "advies": advies}

    def _verifieer(self, resultaat: dict) -> bool:
        """STAP 4: Verificatie - controleer resultaat."""
        print("\n[VERIFICATIE] Ik controleer het resultaat...")

        checks = [
            ("Weer data aanwezig", resultaat.get("weer") is not None),
            ("Advies gegenereerd", resultaat.get("advies") is not None),
            ("Locatie onthouden", self.geheugen.get("locatie") is not None),
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
        advies = resultaat["advies"]

        print("\n" + "=" * 50)
        print("RESULTAAT")
        print("=" * 50)

        print(f"\nLocatie: {weer['stad']}")
        print(f"{weer['icon']} Weer: {weer['conditie'].title()}")
        print(f"Temperatuur: {weer['temp']}C")

        print(f"\nKLEDINGADVIES:")
        print("-" * 30)
        print(advies)

    def run(self):
        """Voert de volledige Agentic Loop uit."""
        clear_scherm()
        print("\n" + "=" * 50)
        print("   WEER-AGENT: Agentic Loop Demo")
        print("=" * 50)

        while True:
            try:
                # 1. Perceptie
                locatie = self._percipeer()

                # 2. Planning
                self._plan(locatie)

                # 3. Actie
                resultaat = self._voer_uit(locatie)

                # 4. Verificatie
                succes = self._verifieer(resultaat)

                if succes:
                    print("\n[OK] Alle checks geslaagd!")
                    self._presenteer(resultaat)
                else:
                    print("\n[!!] Er ging iets mis. Probeer opnieuw.")
                    continue

                print("\n" + "-" * 50)
                tevreden = input("Was dit advies nuttig? (j/n): ").lower().strip()

                if tevreden == "j":
                    print("\nFijn! Veel plezier vandaag!")
                else:
                    print("\nBedankt voor de feedback. Ik leer ervan!")

                print("\n" + "=" * 50)
                opnieuw = input("Wil je nog een locatie checken? (j/n): ").lower().strip()

                if opnieuw != "j":
                    print("\nBedankt voor het gebruiken van WeerWijzer!")
                    print("Je hebt de Agentic Loop in actie gezien!")
                    break

                self.geheugen = {}

            except KeyboardInterrupt:
                print("\n\nTot ziens!")
                break

"""
Virtueel Huisdier App.
"""

import json
import time
import random
from datetime import datetime

from ..core.config import Config
from ..core.utils import clear_scherm


class VirtueelHuisdierApp:
    """Virtueel huisdier simulator."""

    def __init__(self):
        Config.ensure_dirs()
        self.bestand = Config.HUISDIER_FILE
        self.huisdier = None

    def _laad_huisdier(self) -> dict:
        """Laadt het huisdier uit bestand."""
        if self.bestand.exists():
            with open(self.bestand, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    def _sla_op(self):
        """Slaat het huisdier op."""
        self.huisdier["laatste_update"] = datetime.now().isoformat()
        with open(self.bestand, "w", encoding="utf-8") as f:
            json.dump(self.huisdier, f, indent=2, ensure_ascii=False)

    def _maak_nieuw_huisdier(self) -> dict:
        """Maakt een nieuw huisdier aan."""
        clear_scherm()
        print("=== NIEUW HUISDIER MAKEN ===\n")

        naam = input("Hoe wil je je huisdier noemen? ").strip()
        if not naam:
            naam = "Fluffy"

        print("\nWelk type huisdier wil je?")
        print("1. Kat")
        print("2. Hond")
        print("3. Konijn")
        print("4. Hamster")

        keuze = input("\nKies (1-4): ").strip()
        types = {"1": "kat", "2": "hond", "3": "konijn", "4": "hamster"}
        emoji = {"1": "[KAT]", "2": "[HOND]", "3": "[KONIJN]", "4": "[HAMSTER]"}

        huisdier_type = types.get(keuze, "kat")
        huisdier_emoji = emoji.get(keuze, "[KAT]")

        huisdier = {
            "naam": naam,
            "type": huisdier_type,
            "emoji": huisdier_emoji,
            "honger": 50,
            "energie": 100,
            "geluk": 75,
            "gezondheid": 100,
            "leeftijd_dagen": 0,
            "aangemaakt": datetime.now().isoformat(),
            "laatste_update": datetime.now().isoformat()
        }

        self.huisdier = huisdier
        self._sla_op()
        print(f"\n{huisdier_emoji} {naam} de {huisdier_type} is geboren!")
        input("\nDruk op Enter om verder te gaan...")
        return huisdier

    def _bereken_tijd_verlies(self):
        """Berekent hoeveel stats verloren zijn sinds laatste update."""
        laatste = datetime.fromisoformat(self.huisdier["laatste_update"])
        nu = datetime.now()
        verschil_minuten = (nu - laatste).total_seconds() / 60
        uren = verschil_minuten / 60

        if uren > 0.1:
            self.huisdier["honger"] = max(0, self.huisdier["honger"] - int(uren * 5))
            self.huisdier["energie"] = max(0, self.huisdier["energie"] - int(uren * 3))
            self.huisdier["geluk"] = max(0, self.huisdier["geluk"] - int(uren * 4))

            if self.huisdier["honger"] < 20 or self.huisdier["energie"] < 20:
                self.huisdier["gezondheid"] = max(
                    0, self.huisdier["gezondheid"] - int(uren * 2)
                )

            aangemaakt = datetime.fromisoformat(self.huisdier["aangemaakt"])
            self.huisdier["leeftijd_dagen"] = (nu - aangemaakt).days

    def _maak_balk(self, waarde: int, max_waarde: int = 100) -> str:
        """Maakt een visuele progress bar."""
        gevuld = int((waarde / max_waarde) * 10)
        leeg = 10 - gevuld
        if waarde >= 70:
            kleur = "#"
        elif waarde >= 40:
            kleur = "="
        else:
            kleur = "-"
        return "[" + kleur * gevuld + "." * leeg + "]"

    def _toon_status(self):
        """Toont de status van het huisdier."""
        h = self.huisdier
        gemiddelde = (h["honger"] + h["energie"] + h["geluk"] + h["gezondheid"]) / 4

        if gemiddelde >= 80:
            stemming = "is super blij!"
        elif gemiddelde >= 60:
            stemming = "voelt zich goed"
        elif gemiddelde >= 40:
            stemming = "is een beetje moe"
        elif gemiddelde >= 20:
            stemming = "voelt zich niet lekker"
        else:
            stemming = "heeft dringend hulp nodig!"

        print(f"\n{'='*40}")
        print(f"  {h['emoji']} {h['naam']} de {h['type']} {stemming}")
        print(f"  Leeftijd: {h['leeftijd_dagen']} dagen")
        print(f"{'='*40}")
        print(f"\n  Honger:     {self._maak_balk(h['honger'])} {h['honger']}%")
        print(f"  Energie:    {self._maak_balk(h['energie'])} {h['energie']}%")
        print(f"  Geluk:      {self._maak_balk(h['geluk'])} {h['geluk']}%")
        print(f"  Gezondheid: {self._maak_balk(h['gezondheid'])} {h['gezondheid']}%")

    def _toon_voedsel_menu(self):
        """Toont het voedsel keuzemenu."""
        print("\n+--------------------------------+")
        print("|     WAT WIL JE GEVEN?          |")
        print("+--------------------------------+")
        print("|  1. Standaard brokjes          |")
        print("|     Honger +20                 |")
        print("|  2. Premium vlees              |")
        print("|     Honger +30, Geluk +10      |")
        print("|  3. Verse groenten             |")
        print("|     Honger +15, Gezondheid +10 |")
        print("|  4. Lekkere snoepjes           |")
        print("|     Honger +10, Geluk +20      |")
        print("|     Gezondheid -5 (ongezond!)  |")
        print("|  5. Superfood deluxe           |")
        print("|     Honger +25, Energie +15    |")
        print("|     Gezondheid +10             |")
        print("|  0. Terug                      |")
        print("+--------------------------------+")

    def _voeren(self):
        """Geeft het huisdier eten met keuzemenu."""
        self._toon_voedsel_menu()
        keuze = input("\nKies voedsel (0-5): ").strip()

        voedsel_opties = {
            "1": {
                "naam": "standaard brokjes",
                "honger": 20,
                "energie": 0,
                "geluk": 0,
                "gezondheid": 0,
                "reacties": [
                    f"{self.huisdier['naam']} eet de brokjes op.",
                    f"{self.huisdier['naam']} knapt ervan op!",
                ]
            },
            "2": {
                "naam": "premium vlees",
                "honger": 30,
                "energie": 0,
                "geluk": 10,
                "gezondheid": 0,
                "reacties": [
                    f"{self.huisdier['naam']} smult van het vlees!",
                    f"Mmm! {self.huisdier['naam']} likt tevreden de bak leeg!",
                    f"{self.huisdier['naam']} kwispelt/spint van geluk!",
                ]
            },
            "3": {
                "naam": "verse groenten",
                "honger": 15,
                "energie": 0,
                "geluk": 0,
                "gezondheid": 10,
                "reacties": [
                    f"{self.huisdier['naam']} knabbelt gezond aan de groenten.",
                    f"Knapperig! {self.huisdier['naam']} voelt zich fit!",
                ]
            },
            "4": {
                "naam": "lekkere snoepjes",
                "honger": 10,
                "energie": 0,
                "geluk": 20,
                "gezondheid": -5,
                "reacties": [
                    f"{self.huisdier['naam']} is SUPER blij met de snoepjes!",
                    f"Yum! {self.huisdier['naam']} wil er meer!",
                    f"{self.huisdier['naam']} springt van vreugde!",
                ]
            },
            "5": {
                "naam": "superfood deluxe",
                "honger": 25,
                "energie": 15,
                "geluk": 0,
                "gezondheid": 10,
                "reacties": [
                    f"{self.huisdier['naam']} geniet van de superfood!",
                    f"Wow! {self.huisdier['naam']} bruist van energie!",
                    f"{self.huisdier['naam']} voelt zich sterker dan ooit!",
                ]
            },
        }

        if keuze == "0":
            print("Je geeft niets te eten.")
            return

        if keuze not in voedsel_opties:
            print("Ongeldige keuze!")
            return

        voedsel = voedsel_opties[keuze]
        print(f"\nJe geeft {self.huisdier['naam']} {voedsel['naam']}...")
        time.sleep(0.5)

        self.huisdier["honger"] = min(100, self.huisdier["honger"] + voedsel["honger"])
        self.huisdier["energie"] = min(100, self.huisdier["energie"] + voedsel["energie"])
        self.huisdier["geluk"] = min(100, self.huisdier["geluk"] + voedsel["geluk"])
        self.huisdier["gezondheid"] = max(0, min(100,
            self.huisdier["gezondheid"] + voedsel["gezondheid"]))

        print(random.choice(voedsel["reacties"]))

        if voedsel["gezondheid"] < 0:
            print("(Pas op: te veel snoep is niet gezond!)")

    def _spelen(self):
        """Speelt met het huisdier."""
        if self.huisdier["energie"] < 20:
            print(f"\n{self.huisdier['naam']} is te moe om te spelen...")
            return
        print(f"\nJe speelt met {self.huisdier['naam']}...")
        time.sleep(0.5)
        self.huisdier["geluk"] = min(100, self.huisdier["geluk"] + 20)
        self.huisdier["energie"] = max(0, self.huisdier["energie"] - 15)
        self.huisdier["honger"] = max(0, self.huisdier["honger"] - 10)
        reacties = [
            f"{self.huisdier['naam']} rent vrolijk rond!",
            f"{self.huisdier['naam']} springt van plezier!",
            f"Wat leuk! {self.huisdier['naam']} wil nog meer spelen!"
        ]
        print(random.choice(reacties))

    def _slapen(self):
        """Laat het huisdier slapen."""
        print(f"\n{self.huisdier['naam']} gaat slapen...")
        time.sleep(1)
        self.huisdier["energie"] = min(100, self.huisdier["energie"] + 40)
        self.huisdier["gezondheid"] = min(100, self.huisdier["gezondheid"] + 10)
        print(f"Zzzzz... {self.huisdier['naam']} slaapt heerlijk.")
        print(f"*gaaap* {self.huisdier['naam']} is weer uitgerust!")

    def _knuffelen(self):
        """Knuffelt het huisdier."""
        print(f"\nJe knuffelt {self.huisdier['naam']}...")
        time.sleep(0.5)
        self.huisdier["geluk"] = min(100, self.huisdier["geluk"] + 15)
        self.huisdier["gezondheid"] = min(100, self.huisdier["gezondheid"] + 5)
        reacties = [
            f"{self.huisdier['naam']} spint/kwispelt van geluk!",
            f"Aaah! {self.huisdier['naam']} geniet van de aandacht!",
            f"{self.huisdier['naam']} geeft je een likje!"
        ]
        print(random.choice(reacties))

    def _dokter(self):
        """Brengt het huisdier naar de dokter."""
        if self.huisdier["gezondheid"] >= 90:
            print(f"\n{self.huisdier['naam']} is kerngezond! Geen dokter nodig.")
            return
        print(f"\nJe brengt {self.huisdier['naam']} naar de dierenarts...")
        time.sleep(1)
        self.huisdier["gezondheid"] = 100
        print(f"{self.huisdier['naam']} is weer helemaal beter!")

    def _toon_menu(self):
        """Toont het actiemenu."""
        print("\n+----------------------------+")
        print("|      WAT WIL JE DOEN?      |")
        print("+----------------------------+")
        print("|  1. Voeren                 |")
        print("|  2. Spelen                 |")
        print("|  3. Laten slapen           |")
        print("|  4. Knuffelen              |")
        print("|  5. Naar de dokter         |")
        print("|  6. Status bekijken        |")
        print("|  0. Opslaan & Afsluiten    |")
        print("+----------------------------+")

    def run(self):
        """Start de app."""
        clear_scherm()
        print("+---------------------------------------+")
        print("|   VIRTUEEL HUISDIER SIMULATOR        |")
        print("+---------------------------------------+")

        self.huisdier = self._laad_huisdier()

        if self.huisdier:
            print(f"\nWelkom terug! {self.huisdier['emoji']} {self.huisdier['naam']} heeft je gemist!")
            self._bereken_tijd_verlies()

            if self.huisdier["honger"] < 30:
                print(f"[!] {self.huisdier['naam']} heeft honger!")
            if self.huisdier["energie"] < 30:
                print(f"[!] {self.huisdier['naam']} is moe!")
            if self.huisdier["gezondheid"] < 50:
                print(f"[!] {self.huisdier['naam']} voelt zich niet lekker!")

            input("\nDruk op Enter om verder te gaan...")
        else:
            print("\nJe hebt nog geen huisdier!")
            input("Druk op Enter om er een te maken...")
            self._maak_nieuw_huisdier()

        while True:
            clear_scherm()
            self._toon_status()
            self._toon_menu()

            keuze = input("\nJouw keuze (0-6): ").strip()

            if keuze == "1":
                self._voeren()
            elif keuze == "2":
                self._spelen()
            elif keuze == "3":
                self._slapen()
            elif keuze == "4":
                self._knuffelen()
            elif keuze == "5":
                self._dokter()
            elif keuze == "6":
                pass
            elif keuze == "0":
                self._sla_op()
                print(f"\n{self.huisdier['naam']} is opgeslagen!")
                print(f"Tot de volgende keer! {self.huisdier['emoji']}")
                break
            else:
                print("Ongeldige keuze!")

            self._sla_op()

            if keuze != "6":
                input("\nDruk op Enter om verder te gaan...")

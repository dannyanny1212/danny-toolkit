"""
Virtueel Huisdier App.
Versie 2.0 - Met achievements, mini-games, tricks, evolutie en meer!
"""

import json
import time
import random
import re
from datetime import datetime, timedelta
from pathlib import Path

from ..core.config import Config
from ..core.utils import clear_scherm


class VirtueelHuisdierApp:
    """Virtueel huisdier simulator - Uitgebreide versie."""

    # Alle beschikbare huisdier types
    HUISDIER_TYPES = {
        "1": {"naam": "kat", "emoji": "[KAT]", "geluid": "Miauw!"},
        "2": {"naam": "hond", "emoji": "[HOND]", "geluid": "Woef!"},
        "3": {"naam": "konijn", "emoji": "[KONIJN]", "geluid": "*wiebelt neus*"},
        "4": {"naam": "hamster", "emoji": "[HAMSTER]", "geluid": "*piep piep*"},
        "5": {"naam": "vogel", "emoji": "[VOGEL]", "geluid": "Tjilp tjilp!"},
        "6": {"naam": "vis", "emoji": "[VIS]", "geluid": "*blub blub*"},
        "7": {"naam": "draak", "emoji": "[DRAAK]", "geluid": "*ROARRR*"},
        "8": {"naam": "eenhoorn", "emoji": "[EENHOORN]", "geluid": "*magisch gehinnik*"},
        "9": {"naam": "robot", "emoji": "[ROBOT]", "geluid": "Beep boop!"},
        "10": {"naam": "schildpad", "emoji": "[SCHILDPAD]", "geluid": "*langzaam knikt*"},
        "11": {"naam": "panda", "emoji": "[PANDA]", "geluid": "*kauwt op bamboe*"},
        "12": {"naam": "uil", "emoji": "[UIL]", "geluid": "Oehoe!"},
        # Nieuwe huisdier types
        "13": {"naam": "alien", "emoji": "[ALIEN]", "geluid": "*telepathisch: Groetingen!*"},
        "14": {"naam": "phoenix", "emoji": "[PHOENIX]", "geluid": "*majestueus gekrijs*"},
        "15": {"naam": "dino", "emoji": "[DINO]", "geluid": "*prehistorisch gebrul*"},
        "16": {"naam": "slime", "emoji": "[SLIME]", "geluid": "*bloop bloop*"},
    }

    # Evolutie stadia
    EVOLUTIE_STADIA = {
        0: {"naam": "Baby", "dagen": 0, "bonus": 0},
        1: {"naam": "Kind", "dagen": 3, "bonus": 5},
        2: {"naam": "Tiener", "dagen": 7, "bonus": 10},
        3: {"naam": "Volwassen", "dagen": 14, "bonus": 15},
        4: {"naam": "Meester", "dagen": 30, "bonus": 25},
        5: {"naam": "Legende", "dagen": 100, "bonus": 50},
    }

    # Achievements
    ACHIEVEMENTS = {
        "eerste_voeding": {"naam": "Eerste Hapje", "beschrijving": "Voed je huisdier voor het eerst", "punten": 10},
        "week_oud": {"naam": "Een Week!", "beschrijving": "Je huisdier is 7 dagen oud", "punten": 25},
        "maand_oud": {"naam": "Maandknuffel", "beschrijving": "Je huisdier is 30 dagen oud", "punten": 100},
        "perfecte_gezondheid": {"naam": "Topfit", "beschrijving": "Bereik 100% gezondheid", "punten": 15},
        "eerste_trick": {"naam": "Slim Beestje", "beschrijving": "Leer je eerste trick", "punten": 20},
        "alle_tricks": {"naam": "Circus Ster", "beschrijving": "Leer alle tricks", "punten": 100},
        "50_voedingen": {"naam": "Fijnproever", "beschrijving": "Voed je huisdier 50 keer", "punten": 50},
        "mini_game_winnaar": {"naam": "Game Master", "beschrijving": "Win een mini-game", "punten": 15},
        "10_games_gewonnen": {"naam": "Kampioen", "beschrijving": "Win 10 mini-games", "punten": 75},
        "schatzoeker": {"naam": "Schatzoeker", "beschrijving": "Vind 10 schatten in avonturen", "punten": 50},
        "avonturier": {"naam": "Avonturier", "beschrijving": "Voltooi 5 schatzoek avonturen", "punten": 30},
        "wiskunde_genie": {"naam": "Wiskunde Genie", "beschrijving": "Los 20 rekensommen op", "punten": 40},
        "bug_hunter": {"naam": "Bug Hunter", "beschrijving": "Vind 15 bugs in code", "punten": 45},
        "boodschapper": {"naam": "Boodschapper", "beschrijving": "Doe 10 keer boodschappen", "punten": 35},
        "werkend_huisdier": {"naam": "Werkend Huisdier", "beschrijving": "Voltooi 25 werk taken", "punten": 75},
        "kenniszoeker": {"naam": "Kenniszoeker", "beschrijving": "Leer 10 feiten uit de kennisbank", "punten": 40},
        "nieuwslezer": {"naam": "Nieuwslezer", "beschrijving": "Lees 10 nieuwsberichten", "punten": 35},
        "weerwatcher": {"naam": "Weer Watcher", "beschrijving": "Check 10 keer het weer", "punten": 30},
        "ai_student": {"naam": "AI Student", "beschrijving": "Voer 10 AI gesprekken", "punten": 50},
        "super_slim": {"naam": "Super Slim", "beschrijving": "Bereik 100 intelligentie", "punten": 100},
        "dagelijkse_bonus": {"naam": "Trouwe Vriend", "beschrijving": "Claim 7 dagelijkse bonussen", "punten": 50},
        "evolutie_kind": {"naam": "Groeiend", "beschrijving": "Evolueer naar Kind stadium", "punten": 20},
        "evolutie_volwassen": {"naam": "Volgroeid", "beschrijving": "Evolueer naar Volwassen stadium", "punten": 50},
        "evolutie_legende": {"naam": "Legendarisch", "beschrijving": "Bereik Legende stadium", "punten": 200},
        "eerste_accessoire": {"naam": "Fashionista", "beschrijving": "Koop je eerste accessoire", "punten": 15},
        "alle_accessoires": {"naam": "Verzamelaar", "beschrijving": "Koop alle accessoires", "punten": 150},
    }

    # Beschikbare tricks
    TRICKS = {
        "zit": {"naam": "Zitten", "moeilijkheid": 1, "geluk_bonus": 5, "beloning": 5},
        "poot": {"naam": "Pootje geven", "moeilijkheid": 2, "geluk_bonus": 10, "beloning": 10},
        "rol": {"naam": "Rollen", "moeilijkheid": 3, "geluk_bonus": 15, "beloning": 15},
        "spring": {"naam": "Springen", "moeilijkheid": 4, "geluk_bonus": 20, "beloning": 20},
        "dans": {"naam": "Dansen", "moeilijkheid": 5, "geluk_bonus": 25, "beloning": 50},
        "spreek": {"naam": "Spreken", "moeilijkheid": 3, "geluk_bonus": 15, "beloning": 15},
        "dood": {"naam": "Dood spelen", "moeilijkheid": 4, "geluk_bonus": 20, "beloning": 20},
        "high_five": {"naam": "High Five", "moeilijkheid": 2, "geluk_bonus": 10, "beloning": 10},
        # Nieuwe tricks
        "backflip": {"naam": "Backflip", "moeilijkheid": 5, "geluk_bonus": 30, "beloning": 30},
        "zingen": {"naam": "Zingen", "moeilijkheid": 3, "geluk_bonus": 20, "beloning": 20},
        "magie": {"naam": "Goocheltruc", "moeilijkheid": 6, "geluk_bonus": 35, "beloning": 35},
        "teleporteer": {"naam": "Teleporteren", "moeilijkheid": 7, "geluk_bonus": 40, "beloning": 50},
        "onzichtbaar": {"naam": "Onzichtbaar worden", "moeilijkheid": 6, "geluk_bonus": 35, "beloning": 35},
    }

    # Accessoires
    ACCESSOIRES = {
        "bed": {"naam": "Luxe Bedje", "prijs": 50, "effect": "energie", "bonus": 10},
        "speelgoed": {"naam": "Speelgoed", "prijs": 30, "effect": "geluk", "bonus": 10},
        "halsband": {"naam": "Mooie Halsband", "prijs": 40, "effect": "geluk", "bonus": 5},
        "voerbak": {"naam": "Gouden Voerbak", "prijs": 60, "effect": "honger", "bonus": 10},
        "medicijn": {"naam": "Vitamines", "prijs": 45, "effect": "gezondheid", "bonus": 15},
        "outfit": {"naam": "Schattig Outfit", "prijs": 75, "effect": "geluk", "bonus": 20},
        "troon": {"naam": "Koninklijke Troon", "prijs": 200, "effect": "alles", "bonus": 10},
        # Nieuwe accessoires
        "kroon": {"naam": "Gouden Kroon", "prijs": 150, "effect": "geluk", "bonus": 25},
        "vleugels": {"naam": "Engelenvleugels", "prijs": 120, "effect": "energie", "bonus": 20},
        "cape": {"naam": "Superhelden Cape", "prijs": 80, "effect": "geluk", "bonus": 15},
        "zonnebril": {"naam": "Coole Zonnebril", "prijs": 35, "effect": "geluk", "bonus": 10},
        "jetpack": {"naam": "Mini Jetpack", "prijs": 250, "effect": "energie", "bonus": 30},
    }

    # Voedsel opties
    VOEDSEL = {
        "1": {"naam": "Standaard brokjes", "honger": 20, "energie": 0, "geluk": 0, "gezondheid": 0},
        "2": {"naam": "Premium vlees", "honger": 30, "energie": 0, "geluk": 10, "gezondheid": 0},
        "3": {"naam": "Verse groenten", "honger": 15, "energie": 0, "geluk": 0, "gezondheid": 10},
        "4": {"naam": "Lekkere snoepjes", "honger": 10, "energie": 0, "geluk": 20, "gezondheid": -5},
        "5": {"naam": "Superfood deluxe", "honger": 25, "energie": 15, "geluk": 0, "gezondheid": 10},
        "6": {"naam": "Energie shake", "honger": 10, "energie": 30, "geluk": 5, "gezondheid": 5},
    }

    def __init__(self):
        Config.ensure_dirs()
        self.bestand = Config.HUISDIER_FILE
        self.huisdier = None

    def _laad_huisdier(self) -> dict:
        """Laadt het huisdier uit bestand."""
        if self.bestand.exists():
            with open(self.bestand, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Migreer oude data naar nieuw format
                return self._migreer_data(data)
        return None

    def _migreer_data(self, data: dict) -> dict:
        """Migreer oude huisdier data naar nieuw format."""
        # Voeg ontbrekende velden toe
        defaults = {
            "munten": 100,
            "ervaring": 0,
            "intelligentie": 0,
            "evolutie_stadium": 0,
            "tricks_geleerd": [],
            "accessoires": [],
            "achievements": [],
            "stats": {
                "voedingen": 0,
                "games_gewonnen": 0,
                "tricks_uitgevoerd": 0,
                "dagen_gespeeld": 0,
                "feiten_geleerd": 0,
                "nieuws_gelezen": 0,
                "weer_gecheckt": 0,
                "ai_gesprekken": 0,
            },
            "dagelijkse_bonus": {
                "laatste_claim": None,
                "streak": 0,
            },
        }

        for key, value in defaults.items():
            if key not in data:
                data[key] = value
            elif isinstance(value, dict) and isinstance(data.get(key), dict):
                # Ook geneste velden migreren
                for sub_key, sub_value in value.items():
                    if sub_key not in data[key]:
                        data[key][sub_key] = sub_value

        return data

    def _sla_op(self):
        """Slaat het huisdier op."""
        self.huisdier["laatste_update"] = datetime.now().isoformat()
        with open(self.bestand, "w", encoding="utf-8") as f:
            json.dump(self.huisdier, f, indent=2, ensure_ascii=False)

    def _maak_nieuw_huisdier(self) -> dict:
        """Maakt een nieuw huisdier aan."""
        clear_scherm()
        print("=" * 50)
        print("       NIEUW HUISDIER MAKEN")
        print("=" * 50)

        naam = input("\nHoe wil je je huisdier noemen? ").strip()
        if not naam:
            naam = "Fluffy"

        print("\nWelk type huisdier wil je?")
        print("-" * 30)
        for key, info in self.HUISDIER_TYPES.items():
            print(f"  {key:>2}. {info['emoji']} {info['naam'].capitalize()}")

        keuze = input("\nKies (1-16): ").strip()
        if keuze not in self.HUISDIER_TYPES:
            keuze = "1"

        type_info = self.HUISDIER_TYPES[keuze]

        huisdier = {
            "naam": naam,
            "type": type_info["naam"],
            "emoji": type_info["emoji"],
            "geluid": type_info["geluid"],
            "honger": 50,
            "energie": 100,
            "geluk": 75,
            "gezondheid": 100,
            "leeftijd_dagen": 0,
            "munten": 100,
            "ervaring": 0,
            "intelligentie": 0,
            "evolutie_stadium": 0,
            "tricks_geleerd": [],
            "accessoires": [],
            "achievements": [],
            "stats": {
                "voedingen": 0,
                "games_gewonnen": 0,
                "tricks_uitgevoerd": 0,
                "dagen_gespeeld": 1,
                "feiten_geleerd": 0,
                "nieuws_gelezen": 0,
                "weer_gecheckt": 0,
                "ai_gesprekken": 0,
            },
            "dagelijkse_bonus": {
                "laatste_claim": None,
                "streak": 0,
            },
            "aangemaakt": datetime.now().isoformat(),
            "laatste_update": datetime.now().isoformat()
        }

        self.huisdier = huisdier
        self._sla_op()

        print(f"\n{type_info['emoji']} {naam} de {type_info['naam']} is geboren!")
        print(f"{type_info['geluid']}")
        print(f"\nJe hebt 100 munten gekregen om te beginnen!")
        input("\nDruk op Enter om verder te gaan...")
        return huisdier

    def _bereken_tijd_verlies(self):
        """Berekent hoeveel stats verloren zijn sinds laatste update."""
        laatste = datetime.fromisoformat(self.huisdier["laatste_update"])
        nu = datetime.now()
        verschil_minuten = (nu - laatste).total_seconds() / 60
        uren = verschil_minuten / 60

        if uren > 0.1:
            # Accessoire bonussen
            bonus = self._bereken_accessoire_bonus()

            self.huisdier["honger"] = max(0, self.huisdier["honger"] - int(uren * 5) + bonus.get("honger", 0))
            self.huisdier["energie"] = max(0, self.huisdier["energie"] - int(uren * 3) + bonus.get("energie", 0))
            self.huisdier["geluk"] = max(0, self.huisdier["geluk"] - int(uren * 4) + bonus.get("geluk", 0))

            if self.huisdier["honger"] < 20 or self.huisdier["energie"] < 20:
                verlies = int(uren * 2) - bonus.get("gezondheid", 0)
                self.huisdier["gezondheid"] = max(0, self.huisdier["gezondheid"] - verlies)

            aangemaakt = datetime.fromisoformat(self.huisdier["aangemaakt"])
            self.huisdier["leeftijd_dagen"] = (nu - aangemaakt).days

            # Check evolutie
            self._check_evolutie()

    def _bereken_accessoire_bonus(self) -> dict:
        """Bereken totale bonus van accessoires."""
        bonus = {"honger": 0, "energie": 0, "geluk": 0, "gezondheid": 0}

        for acc_id in self.huisdier.get("accessoires", []):
            if acc_id in self.ACCESSOIRES:
                acc = self.ACCESSOIRES[acc_id]
                if acc["effect"] == "alles":
                    for key in bonus:
                        bonus[key] += acc["bonus"]
                elif acc["effect"] in bonus:
                    bonus[acc["effect"]] += acc["bonus"]

        return bonus

    def _check_evolutie(self):
        """Check of huisdier kan evolueren."""
        dagen = self.huisdier["leeftijd_dagen"]
        huidig_stadium = self.huisdier["evolutie_stadium"]

        for stadium, info in self.EVOLUTIE_STADIA.items():
            if stadium > huidig_stadium and dagen >= info["dagen"]:
                self.huisdier["evolutie_stadium"] = stadium
                print(f"\n*** {self.huisdier['naam']} is geëvolueerd naar {info['naam']}! ***")

                # Achievement check
                if stadium == 1:
                    self._unlock_achievement("evolutie_kind")
                elif stadium == 3:
                    self._unlock_achievement("evolutie_volwassen")
                elif stadium == 5:
                    self._unlock_achievement("evolutie_legende")

    def _unlock_achievement(self, achievement_id: str):
        """Unlock een achievement."""
        if achievement_id not in self.huisdier["achievements"]:
            if achievement_id in self.ACHIEVEMENTS:
                ach = self.ACHIEVEMENTS[achievement_id]
                self.huisdier["achievements"].append(achievement_id)
                self.huisdier["munten"] += ach["punten"]
                print(f"\n*** ACHIEVEMENT UNLOCKED: {ach['naam']}! ***")
                print(f"   {ach['beschrijving']}")
                print(f"   +{ach['punten']} munten!")

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

    def _get_evolutie_info(self) -> dict:
        """Haal evolutie info op."""
        return self.EVOLUTIE_STADIA.get(self.huisdier["evolutie_stadium"], self.EVOLUTIE_STADIA[0])

    def _toon_status(self):
        """Toont de status van het huisdier."""
        h = self.huisdier
        gemiddelde = (h["honger"] + h["energie"] + h["geluk"] + h["gezondheid"]) / 4
        evolutie = self._get_evolutie_info()

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

        print(f"\n{'='*50}")
        print(f"  {h['emoji']} {h['naam']} de {h['type']} {stemming}")
        print(f"  Stadium: {evolutie['naam']} | Leeftijd: {h['leeftijd_dagen']} dagen")
        intel = h.get('intelligentie', 0)
        print(f"  Munten: {h['munten']} | Ervaring: {h['ervaring']} | IQ: {intel}")
        print(f"{'='*50}")
        print(f"\n  Honger:     {self._maak_balk(h['honger'])} {h['honger']}%")
        print(f"  Energie:    {self._maak_balk(h['energie'])} {h['energie']}%")
        print(f"  Geluk:      {self._maak_balk(h['geluk'])} {h['geluk']}%")
        print(f"  Gezondheid: {self._maak_balk(h['gezondheid'])} {h['gezondheid']}%")

        # Accessoires
        if h["accessoires"]:
            acc_namen = [self.ACCESSOIRES[a]["naam"] for a in h["accessoires"] if a in self.ACCESSOIRES]
            print(f"\n  Accessoires: {', '.join(acc_namen)}")

        # Tricks
        if h["tricks_geleerd"]:
            trick_namen = [self.TRICKS[t]["naam"] for t in h["tricks_geleerd"] if t in self.TRICKS]
            print(f"  Tricks: {', '.join(trick_namen)}")

    def _toon_menu(self):
        """Toont het hoofdmenu."""
        print("\n+================================+")
        print("|       WAT WIL JE DOEN?         |")
        print("+================================+")
        print("|  1. Voeren                     |")
        print("|  2. Spelen                     |")
        print("|  3. Laten slapen               |")
        print("|  4. Knuffelen                  |")
        print("|  5. Naar de dokter             |")
        print("|  6. Mini-games                 |")
        print("|  7. Tricks leren/uitvoeren     |")
        print("|  8. Winkel (accessoires)       |")
        print("|  9. Achievements bekijken      |")
        print("| 10. Dagelijkse bonus           |")
        print("| 11. Huisdier Werk              |")
        print("| 12. Huisdier Leren (AI)        |")
        print("|  0. Opslaan & Afsluiten        |")
        print("+================================+")

    def _voeren(self):
        """Voer het huisdier."""
        print("\n+--------------------------------+")
        print("|     WAT WIL JE GEVEN?          |")
        print("+--------------------------------+")

        for key, voedsel in self.VOEDSEL.items():
            effecten = []
            if voedsel["honger"]: effecten.append(f"Honger +{voedsel['honger']}")
            if voedsel["energie"]: effecten.append(f"Energie +{voedsel['energie']}")
            if voedsel["geluk"] > 0: effecten.append(f"Geluk +{voedsel['geluk']}")
            if voedsel["gezondheid"] > 0: effecten.append(f"Gezondheid +{voedsel['gezondheid']}")
            if voedsel["gezondheid"] < 0: effecten.append(f"Gezondheid {voedsel['gezondheid']}")

            print(f"|  {key}. {voedsel['naam']:<20}|")
            print(f"|     {', '.join(effecten):<25}|")

        print("|  0. Terug                      |")
        print("+--------------------------------+")

        keuze = input("\nKies (0-6): ").strip()

        if keuze == "0" or keuze not in self.VOEDSEL:
            return

        voedsel = self.VOEDSEL[keuze]
        print(f"\nJe geeft {self.huisdier['naam']} {voedsel['naam']}...")
        time.sleep(0.5)

        self.huisdier["honger"] = min(100, self.huisdier["honger"] + voedsel["honger"])
        self.huisdier["energie"] = min(100, self.huisdier["energie"] + voedsel["energie"])
        self.huisdier["geluk"] = min(100, self.huisdier["geluk"] + voedsel["geluk"])
        self.huisdier["gezondheid"] = max(0, min(100, self.huisdier["gezondheid"] + voedsel["gezondheid"]))

        self.huisdier["stats"]["voedingen"] += 1
        self.huisdier["ervaring"] += 5

        reacties = [
            f"{self.huisdier['naam']} smult ervan!",
            f"Mmm! {self.huisdier['naam']} likt tevreden de bak leeg!",
            f"{self.huisdier['geluid']}",
        ]
        print(random.choice(reacties))

        # Achievement checks
        if self.huisdier["stats"]["voedingen"] == 1:
            self._unlock_achievement("eerste_voeding")
        if self.huisdier["stats"]["voedingen"] >= 50:
            self._unlock_achievement("50_voedingen")

    def _spelen(self):
        """Speelt met het huisdier."""
        if self.huisdier["energie"] < 20:
            print(f"\n{self.huisdier['naam']} is te moe om te spelen...")
            return

        print(f"\nJe speelt met {self.huisdier['naam']}...")
        time.sleep(0.5)

        bonus = self._get_evolutie_info()["bonus"]
        self.huisdier["geluk"] = min(100, self.huisdier["geluk"] + 20 + bonus)
        self.huisdier["energie"] = max(0, self.huisdier["energie"] - 15)
        self.huisdier["honger"] = max(0, self.huisdier["honger"] - 10)
        self.huisdier["ervaring"] += 10

        reacties = [
            f"{self.huisdier['naam']} rent vrolijk rond!",
            f"{self.huisdier['naam']} springt van plezier!",
            f"Wat leuk! {self.huisdier['naam']} wil nog meer spelen!",
            f"{self.huisdier['geluid']}",
        ]
        print(random.choice(reacties))

    def _slapen(self):
        """Laat het huisdier slapen."""
        print(f"\n{self.huisdier['naam']} gaat slapen...")
        time.sleep(1)

        bonus = 0
        if "bed" in self.huisdier["accessoires"]:
            bonus = 10
            print("(Bonus van luxe bedje!)")

        self.huisdier["energie"] = min(100, self.huisdier["energie"] + 40 + bonus)
        self.huisdier["gezondheid"] = min(100, self.huisdier["gezondheid"] + 10)
        self.huisdier["ervaring"] += 5

        print(f"Zzzzz... {self.huisdier['naam']} slaapt heerlijk.")
        print(f"*gaaap* {self.huisdier['naam']} is weer uitgerust!")

    def _knuffelen(self):
        """Knuffelt het huisdier."""
        print(f"\nJe knuffelt {self.huisdier['naam']}...")
        time.sleep(0.5)

        self.huisdier["geluk"] = min(100, self.huisdier["geluk"] + 15)
        self.huisdier["gezondheid"] = min(100, self.huisdier["gezondheid"] + 5)
        self.huisdier["ervaring"] += 5

        reacties = [
            f"{self.huisdier['naam']} geniet van de aandacht!",
            f"Aaah! {self.huisdier['naam']} is zo blij!",
            f"{self.huisdier['naam']} geeft je een likje!",
            f"{self.huisdier['geluid']}",
        ]
        print(random.choice(reacties))

        if self.huisdier["gezondheid"] == 100:
            self._unlock_achievement("perfecte_gezondheid")

    def _dokter(self):
        """Naar de dierenarts."""
        if self.huisdier["gezondheid"] >= 90:
            print(f"\n{self.huisdier['naam']} is kerngezond! Geen dokter nodig.")
            return

        kosten = 25
        if self.huisdier["munten"] < kosten:
            print(f"\nJe hebt niet genoeg munten! (Nodig: {kosten})")
            return

        print(f"\nJe brengt {self.huisdier['naam']} naar de dierenarts... (-{kosten} munten)")
        time.sleep(1)

        self.huisdier["munten"] -= kosten
        self.huisdier["gezondheid"] = 100
        print(f"{self.huisdier['naam']} is weer helemaal beter!")

    def _mini_games(self):
        """Mini-games menu."""
        while True:
            print("\n+====================================+")
            print("|          MINI-GAMES                |")
            print("+====================================+")
            print("|  1. Raad het getal (5 munten)      |")
            print("|  2. Steen-papier-schaar            |")
            print("|  3. Memory (10 munten)             |")
            print("|  4. Snelheidstest                  |")
            print("|  5. Verstoppertje (8 munten)       |")
            print("|  6. Race (12 munten)               |")
            print("|  7. Quiz (6 munten)                |")
            print("|  8. Vangen (10 munten)             |")
            print("|  9. Schatzoek Avontuur (15 munten) |")
            print("|  0. Terug                          |")
            print("+====================================+")

            keuze = input("\nKies een spel: ").strip()

            if keuze == "0":
                break
            elif keuze == "1":
                self._game_raad_getal()
            elif keuze == "2":
                self._game_steen_papier_schaar()
            elif keuze == "3":
                self._game_memory()
            elif keuze == "4":
                self._game_snelheid()
            elif keuze == "5":
                self._game_verstoppertje()
            elif keuze == "6":
                self._game_race()
            elif keuze == "7":
                self._game_quiz()
            elif keuze == "8":
                self._game_vangen()
            elif keuze == "9":
                self._game_schatzoek_avontuur()

            input("\nDruk op Enter...")

    def _game_raad_getal(self):
        """Raad het getal spel."""
        if self.huisdier["munten"] < 5:
            print("\nJe hebt niet genoeg munten! (Nodig: 5)")
            return

        self.huisdier["munten"] -= 5
        getal = random.randint(1, 10)
        pogingen = 3

        print(f"\n{self.huisdier['naam']} denkt aan een getal tussen 1 en 10...")
        print(f"Je hebt {pogingen} pogingen!")

        for i in range(pogingen):
            try:
                gok = int(input(f"\nPoging {i+1}: ").strip())
                if gok == getal:
                    winst = 15
                    print(f"\n[OK] GOED! Je wint {winst} munten!")
                    self.huisdier["munten"] += winst
                    self.huisdier["stats"]["games_gewonnen"] += 1
                    self._check_game_achievements()
                    return
                elif gok < getal:
                    print("Hoger!")
                else:
                    print("Lager!")
            except ValueError:
                print("Voer een getal in!")

        print(f"\nHelaas! Het getal was {getal}.")

    def _game_steen_papier_schaar(self):
        """Steen papier schaar."""
        opties = ["steen", "papier", "schaar"]

        print(f"\n{self.huisdier['naam']} wil steen-papier-schaar spelen!")
        keuze = input("Jouw keuze (steen/papier/schaar): ").strip().lower()

        if keuze not in opties:
            print("Ongeldige keuze!")
            return

        huisdier_keuze = random.choice(opties)
        print(f"\n{self.huisdier['naam']} kiest: {huisdier_keuze}!")

        if keuze == huisdier_keuze:
            print("Gelijkspel!")
        elif (keuze == "steen" and huisdier_keuze == "schaar") or \
             (keuze == "papier" and huisdier_keuze == "steen") or \
             (keuze == "schaar" and huisdier_keuze == "papier"):
            print("[OK] Je wint! +10 munten!")
            self.huisdier["munten"] += 10
            self.huisdier["stats"]["games_gewonnen"] += 1
            self._check_game_achievements()
        else:
            print(f"{self.huisdier['naam']} wint!")
            self.huisdier["geluk"] = min(100, self.huisdier["geluk"] + 5)

    def _game_memory(self):
        """Simpel memory spel."""
        if self.huisdier["munten"] < 10:
            print("\nJe hebt niet genoeg munten! (Nodig: 10)")
            return

        self.huisdier["munten"] -= 10

        reeks = [random.randint(1, 9) for _ in range(4)]
        print(f"\n{self.huisdier['naam']} laat een reeks zien...")
        print(f"\nOnthoud: {' '.join(map(str, reeks))}")
        time.sleep(2)
        print("\n" * 3)

        try:
            antwoord = input("Wat was de reeks? (bijv: 1 2 3 4): ").strip()
            gebruiker_reeks = list(map(int, antwoord.split()))

            if gebruiker_reeks == reeks:
                winst = 30
                print(f"\n[OK] PERFECT! Je wint {winst} munten!")
                self.huisdier["munten"] += winst
                self.huisdier["stats"]["games_gewonnen"] += 1
                self._check_game_achievements()
            else:
                print(f"\nHelaas! De reeks was: {' '.join(map(str, reeks))}")
        except ValueError:
            print("Ongeldige invoer!")

    def _game_snelheid(self):
        """Snelheidstest."""
        print(f"\n{self.huisdier['naam']} wil je reflexen testen!")
        print("Druk op Enter zodra je 'NU!' ziet...")

        time.sleep(random.uniform(1, 4))
        start = time.time()
        print("\n>>> NU! <<<")
        input()
        reactietijd = time.time() - start

        if reactietijd < 0.3:
            print(f"[OK] BLIKSEMNEL! {reactietijd:.3f}s - +15 munten!")
            self.huisdier["munten"] += 15
            self.huisdier["stats"]["games_gewonnen"] += 1
            self._check_game_achievements()
        elif reactietijd < 0.5:
            print(f"Goed! {reactietijd:.3f}s - +5 munten!")
            self.huisdier["munten"] += 5
        else:
            print(f"Te langzaam! {reactietijd:.3f}s")

    def _game_verstoppertje(self):
        """Verstoppertje mini-game - zoek je huisdier!"""
        if self.huisdier["munten"] < 8:
            print("\nJe hebt niet genoeg munten! (Nodig: 8)")
            return

        self.huisdier["munten"] -= 8

        # Maak een 3x3 grid met 9 verstopplekken
        plekken = [
            "achter de bank", "in de kast", "onder het bed",
            "achter het gordijn", "in de wasmand", "onder de tafel",
            "in de doos", "achter de deur", "onder de deken"
        ]

        verstopplek = random.choice(plekken)
        pogingen = 3

        print(f"\n{self.huisdier['naam']} heeft zich verstopt!")
        print(f"{self.huisdier['geluid']}")
        print(f"\nJe hebt {pogingen} pogingen om {self.huisdier['naam']} te vinden!")

        print("\nWaar zou je zoeken?")
        for i, plek in enumerate(plekken, 1):
            print(f"  {i}. {plek.capitalize()}")

        for poging in range(pogingen):
            try:
                keuze = int(input(f"\nPoging {poging + 1}/{pogingen} - Kies (1-9): ").strip())
                if 1 <= keuze <= 9:
                    gekozen = plekken[keuze - 1]

                    if gekozen == verstopplek:
                        winst = 20 + (pogingen - poging) * 5
                        print(f"\n[OK] GEVONDEN! {self.huisdier['naam']} zat {verstopplek}!")
                        print(f"{self.huisdier['naam']} springt blij in je armen!")
                        print(f"+{winst} munten!")
                        self.huisdier["munten"] += winst
                        self.huisdier["geluk"] = min(100, self.huisdier["geluk"] + 15)
                        self.huisdier["stats"]["games_gewonnen"] += 1
                        self._check_game_achievements()
                        return
                    else:
                        # Geef een hint
                        if poging < pogingen - 1:
                            verstop_idx = plekken.index(verstopplek)
                            keuze_idx = keuze - 1
                            if abs(verstop_idx - keuze_idx) <= 2:
                                print(f"\n*je hoort geritsel* {self.huisdier['naam']} is dichtbij!")
                            else:
                                print(f"\n*stilte* {self.huisdier['naam']} is niet in de buurt...")
            except ValueError:
                print("Voer een nummer in (1-9)!")

        print(f"\n{self.huisdier['naam']} komt tevoorschijn van {verstopplek}!")
        print(f"{self.huisdier['geluid']} - Beter geluk volgende keer!")
        self.huisdier["geluk"] = min(100, self.huisdier["geluk"] + 5)

    def _game_race(self):
        """Race mini-game - race tegen je huisdier!"""
        if self.huisdier["munten"] < 12:
            print("\nJe hebt niet genoeg munten! (Nodig: 12)")
            return

        self.huisdier["munten"] -= 12

        print(f"\n{self.huisdier['naam']} daagt je uit voor een race!")
        print("Druk zo snel mogelijk op Enter wanneer de race begint!")
        print("\nKlaar...")
        time.sleep(1)
        print("Set...")
        time.sleep(random.uniform(0.5, 2))
        print("\n>>> START! <<<")

        # Speler moet 5x op enter drukken
        start = time.time()
        for i in range(5):
            input(f"[{i+1}/5] DRUK ENTER!")
        speler_tijd = time.time() - start

        # Huisdier tijd (gebaseerd op geluk en energie)
        basis_tijd = 3.0
        huisdier_bonus = (self.huisdier["geluk"] + self.huisdier["energie"]) / 200
        huisdier_tijd = basis_tijd - huisdier_bonus + random.uniform(-0.5, 0.5)

        print(f"\nJouw tijd: {speler_tijd:.2f}s")
        print(f"{self.huisdier['naam']}'s tijd: {huisdier_tijd:.2f}s")

        if speler_tijd < huisdier_tijd:
            winst = 25
            print(f"\n[OK] JE WINT! +{winst} munten!")
            self.huisdier["munten"] += winst
            self.huisdier["stats"]["games_gewonnen"] += 1
            self._check_game_achievements()
        elif speler_tijd > huisdier_tijd:
            print(f"\n{self.huisdier['naam']} wint! {self.huisdier['geluid']}")
            self.huisdier["geluk"] = min(100, self.huisdier["geluk"] + 10)
        else:
            print("\nGelijkspel! +5 munten troostprijs!")
            self.huisdier["munten"] += 5

    def _game_quiz(self):
        """Quiz mini-game - beantwoord vragen over huisdieren!"""
        if self.huisdier["munten"] < 6:
            print("\nJe hebt niet genoeg munten! (Nodig: 6)")
            return

        self.huisdier["munten"] -= 6

        vragen = [
            {"vraag": "Hoeveel levens heeft een kat volgens het gezegde?", "antwoord": "9", "opties": ["7", "9", "5", "3"]},
            {"vraag": "Welk dier is het symbool van trouw?", "antwoord": "hond", "opties": ["kat", "hond", "vis", "vogel"]},
            {"vraag": "Wat eet een konijn het liefst?", "antwoord": "wortels", "opties": ["vlees", "wortels", "vis", "brood"]},
            {"vraag": "Hoe noem je een groep wolven?", "antwoord": "roedel", "opties": ["kudde", "zwerm", "roedel", "school"]},
            {"vraag": "Welk dier slaapt staand?", "antwoord": "paard", "opties": ["hond", "kat", "paard", "konijn"]},
            {"vraag": "Hoeveel poten heeft een spin?", "antwoord": "8", "opties": ["6", "8", "10", "4"]},
            {"vraag": "Welk dier kan het hardst rennen?", "antwoord": "cheeta", "opties": ["leeuw", "cheeta", "paard", "hond"]},
            {"vraag": "Wat is de grootste vogel ter wereld?", "antwoord": "struisvogel", "opties": ["adelaar", "struisvogel", "albatros", "condor"]},
        ]

        vraag = random.choice(vragen)
        random.shuffle(vraag["opties"])

        print(f"\n{self.huisdier['naam']} stelt een vraag:")
        print(f"\n>> {vraag['vraag']}")
        for i, optie in enumerate(vraag["opties"], 1):
            print(f"  {i}. {optie}")

        try:
            keuze = int(input("\nJouw antwoord (1-4): ").strip())
            gekozen = vraag["opties"][keuze - 1].lower()

            if gekozen == vraag["antwoord"].lower():
                winst = 20
                print(f"\n[OK] CORRECT! +{winst} munten!")
                self.huisdier["munten"] += winst
                self.huisdier["stats"]["games_gewonnen"] += 1
                self._check_game_achievements()
            else:
                print(f"\nHelaas! Het juiste antwoord was: {vraag['antwoord']}")
        except (ValueError, IndexError):
            print("Ongeldige keuze!")

    def _game_vangen(self):
        """Vangen mini-game - vang het vallende object!"""
        if self.huisdier["munten"] < 10:
            print("\nJe hebt niet genoeg munten! (Nodig: 10)")
            return

        self.huisdier["munten"] -= 10

        objecten = ["bal", "bot", "muis", "veer", "ring"]
        obj = random.choice(objecten)

        print(f"\n{self.huisdier['naam']} gooit een {obj} in de lucht!")
        print("Typ het object en druk Enter om te vangen!")
        print("\n3...")
        time.sleep(1)
        print("2...")
        time.sleep(1)
        print("1...")
        time.sleep(random.uniform(0.3, 1.0))
        print(f"\n>>> {obj.upper()} <<<")

        start = time.time()
        antwoord = input("VANG: ").strip().lower()
        reactietijd = time.time() - start

        if antwoord == obj and reactietijd < 2.0:
            if reactietijd < 0.8:
                winst = 30
                print(f"\n[OK] PERFECTE VANGST! {reactietijd:.2f}s - +{winst} munten!")
            elif reactietijd < 1.5:
                winst = 20
                print(f"\n[OK] Goed gevangen! {reactietijd:.2f}s - +{winst} munten!")
            else:
                winst = 10
                print(f"\nNet op tijd! {reactietijd:.2f}s - +{winst} munten!")
            self.huisdier["munten"] += winst
            self.huisdier["stats"]["games_gewonnen"] += 1
            self._check_game_achievements()
        elif antwoord != obj:
            print(f"\nJe typte '{antwoord}' maar het was '{obj}'!")
        else:
            print(f"\nTe langzaam! ({reactietijd:.2f}s)")

        self.huisdier["geluk"] = min(100, self.huisdier["geluk"] + 5)

    def _game_schatzoek_avontuur(self):
        """Schatzoek avontuur - je huisdier gaat automatisch op schattenjacht!"""
        if self.huisdier["munten"] < 15:
            print("\nJe hebt niet genoeg munten! (Nodig: 15)")
            return

        if self.huisdier["energie"] < 20:
            print(f"\n{self.huisdier['naam']} is te moe voor een avontuur!")
            print("Laat je huisdier eerst rusten.")
            return

        self.huisdier["munten"] -= 15
        self.huisdier["energie"] = max(0, self.huisdier["energie"] - 20)

        # Init stats als ze niet bestaan
        if "schatten_gevonden" not in self.huisdier["stats"]:
            self.huisdier["stats"]["schatten_gevonden"] = 0
        if "avonturen_voltooid" not in self.huisdier["stats"]:
            self.huisdier["stats"]["avonturen_voltooid"] = 0

        naam = self.huisdier["naam"]
        geluid = self.huisdier["geluid"]

        # Moeilijkheid gebaseerd op evolutie
        evolutie = self.huisdier.get("evolutie_stadium", 0)
        geluk = self.huisdier["geluk"]

        # Bereken success kansen
        basis_kans = 50 + (evolutie * 5) + (geluk // 5)
        basis_kans = min(90, basis_kans)  # Max 90%

        print("\n" + "=" * 50)
        print(f"  [AVONTUUR] {naam} GAAT OP SCHATTENJACHT!")
        print("=" * 50)
        time.sleep(0.5)

        # Kies een biome
        biomes = [
            ("Mysterieus Bos", "[BOS]"),
            ("Donkere Grot", "[GROT]"),
            ("Verloren Woestijn", "[WOESTIJN]"),
            ("Verlaten Kasteel", "[KASTEEL]"),
            ("Bevroren IJsgrot", "[IJSGROT]"),
        ]
        biome_naam, biome_emoji = random.choice(biomes)

        print(f"\n  {biome_emoji} Locatie: {biome_naam}")
        print(f"  {geluid}")
        time.sleep(0.8)

        # Simuleer het avontuur
        schatten = 0
        monsters_verslagen = 0
        events = []

        # 5 kamers verkennen
        for kamer in range(1, 6):
            print(f"\n  --- Kamer {kamer}/5 ---")
            time.sleep(0.4)

            # Random events
            event = random.choices(
                ["schat", "monster", "val", "powerup", "leeg"],
                weights=[25, 20, 15, 15, 25]
            )[0]

            if event == "schat":
                if random.randint(1, 100) <= basis_kans:
                    schatten += 1
                    print(f"  [DIAMANT] {naam} vindt een schitterende schat!")
                    events.append("schat")
                else:
                    print(f"  [?] {naam} ziet iets glinsteren maar kan er niet bij...")

            elif event == "monster":
                monster = random.choice(["Goblin", "Spin", "Vleermuis", "Slime"])
                if random.randint(1, 100) <= basis_kans + 10:
                    monsters_verslagen += 1
                    print(f"  [ZWAARD] {naam} verslaat een {monster}!")
                    events.append("monster")
                else:
                    print(f"  [!] Een {monster}! {naam} rent weg!")

            elif event == "val":
                if random.randint(1, 100) <= basis_kans:
                    print(f"  [!] Een valstrik! {naam} ontwijkt hem handig!")
                else:
                    print(f"  [X] Oeps! {naam} trapt in een val! (-5 energie)")
                    self.huisdier["energie"] = max(0, self.huisdier["energie"] - 5)

            elif event == "powerup":
                powerup = random.choice(["hartje", "ster", "trank"])
                print(f"  [+] {naam} vindt een {powerup}! (+5 geluk)")
                self.huisdier["geluk"] = min(100, self.huisdier["geluk"] + 5)
                events.append("powerup")

            else:  # leeg
                print(f"  [_] Een lege kamer... {naam} snuffelt rond.")

            time.sleep(0.3)

        # Resultaten
        print("\n" + "=" * 50)
        print("  [VLAG] AVONTUUR VOLTOOID!")
        print("=" * 50)

        # Beloningen berekenen
        munt_beloning = schatten * 20 + monsters_verslagen * 10
        xp_beloning = schatten * 15 + monsters_verslagen * 10 + 10

        print(f"\n  Resultaten van {naam}:")
        print(f"    [DIAMANT] Schatten gevonden: {schatten}")
        print(f"    [ZWAARD] Monsters verslagen: {monsters_verslagen}")
        print(f"    [MUNT] Munten verdiend: +{munt_beloning}")
        print(f"    [XP] Ervaring: +{xp_beloning}")

        # Geef beloningen
        self.huisdier["munten"] += munt_beloning
        self.huisdier["ervaring"] += xp_beloning
        self.huisdier["stats"]["schatten_gevonden"] += schatten
        self.huisdier["stats"]["avonturen_voltooid"] += 1
        self.huisdier["stats"]["games_gewonnen"] += 1 if schatten > 0 else 0

        # Bonus voor perfect avontuur
        if schatten >= 3:
            bonus = 25
            print(f"\n  [TROFEE] GEWELDIG! Bonus voor 3+ schatten: +{bonus} munten!")
            self.huisdier["munten"] += bonus

        # Achievements checken
        self._check_game_achievements()
        if self.huisdier["stats"]["schatten_gevonden"] >= 10:
            self._unlock_achievement("schatzoeker")
        if self.huisdier["stats"]["avonturen_voltooid"] >= 5:
            self._unlock_achievement("avonturier")

        # Level check
        self._check_evolutie()

        print(f"\n  {geluid}")
        self._sla_op()

    def _check_game_achievements(self):
        """Check game achievements."""
        self._unlock_achievement("mini_game_winnaar")
        if self.huisdier["stats"]["games_gewonnen"] >= 10:
            self._unlock_achievement("10_games_gewonnen")

    # ==================== HUISDIER WERK ====================

    def _huisdier_werk(self):
        """Menu voor huisdier werk activiteiten."""
        while True:
            print("\n+====================================+")
            print("|        HUISDIER WERK               |")
            print("+====================================+")
            print("|  Je huisdier kan helpen met taken! |")
            print("+------------------------------------+")
            print("|  1. Boodschappen Doen (10 munten)  |")
            print("|  2. Wiskunde Uitdaging (8 munten)  |")
            print("|  3. Bug Jacht (12 munten)          |")
            print("|  0. Terug                          |")
            print("+====================================+")

            keuze = input("\nKies een activiteit: ").strip()

            if keuze == "0":
                break
            elif keuze == "1":
                self._werk_boodschappen()
            elif keuze == "2":
                self._werk_wiskunde()
            elif keuze == "3":
                self._werk_bug_jacht()

            input("\nDruk op Enter...")

    def _werk_boodschappen(self):
        """Huisdier gaat boodschappen doen en helpt met de boodschappenlijst."""
        if self.huisdier["munten"] < 10:
            print("\nJe hebt niet genoeg munten! (Nodig: 10)")
            return

        if self.huisdier["energie"] < 15:
            print(f"\n{self.huisdier['naam']} is te moe om boodschappen te doen!")
            return

        self.huisdier["munten"] -= 10
        self.huisdier["energie"] = max(0, self.huisdier["energie"] - 15)

        # Init stats
        if "boodschappen_gedaan" not in self.huisdier["stats"]:
            self.huisdier["stats"]["boodschappen_gedaan"] = 0
        if "werk_taken" not in self.huisdier["stats"]:
            self.huisdier["stats"]["werk_taken"] = 0

        naam = self.huisdier["naam"]
        geluid = self.huisdier["geluid"]
        huisdier_type = self.huisdier["type"]

        # Producten die het huisdier kan vinden
        winkel_secties = {
            "dieren": ["Hondenvoer", "Kattenvoer", "Snacks", "Speeltjes", "Kattenbakkorrels"],
            "snacks": ["Koekjes", "Chips", "Chocolade", "Nootjes"],
            "groenten": ["Appels", "Bananen", "Wortels", "Tomaten"],
            "zuivel": ["Melk", "Kaas", "Yoghurt", "Eieren"],
        }

        print("\n" + "=" * 50)
        print(f"  [WINKEL] {naam} GAAT BOODSCHAPPEN DOEN!")
        print("=" * 50)
        time.sleep(0.5)

        print(f"\n  {geluid}")
        print(f"  {naam} pakt een winkelwagentje...")
        time.sleep(0.5)

        gevonden_items = []
        totaal_korting = 0

        # Bezoek 4 secties
        for sectie_naam, producten in random.sample(list(winkel_secties.items()), 4):
            print(f"\n  --- Sectie: {sectie_naam.upper()} ---")
            time.sleep(0.3)

            # Huisdier zoekt producten
            if random.randint(1, 100) <= 70:  # 70% kans
                product = random.choice(producten)
                gevonden_items.append(product)
                print(f"  [OK] {naam} vindt: {product}")

                # Kans op korting
                if random.randint(1, 100) <= 30:
                    korting = random.randint(5, 20)
                    totaal_korting += korting
                    print(f"  [BONUS] Aanbieding gevonden! -{korting}% korting!")
            else:
                print(f"  [_] {naam} snuffelt rond maar vindt niks speciaals...")

            time.sleep(0.3)

        # Resultaten
        print("\n" + "=" * 50)
        print("  [KASSA] BOODSCHAPPEN KLAAR!")
        print("=" * 50)

        munt_beloning = len(gevonden_items) * 8 + totaal_korting // 2
        xp_beloning = len(gevonden_items) * 5 + 10

        print(f"\n  {naam}'s winkelresultaat:")
        print(f"    [TAS] Items gevonden: {len(gevonden_items)}")
        if gevonden_items:
            for item in gevonden_items:
                print(f"        - {item}")
        print(f"    [%] Totale korting: {totaal_korting}%")
        print(f"    [MUNT] Verdiend: +{munt_beloning} munten")
        print(f"    [XP] Ervaring: +{xp_beloning}")

        # Geef beloningen
        self.huisdier["munten"] += munt_beloning
        self.huisdier["ervaring"] += xp_beloning
        self.huisdier["geluk"] = min(100, self.huisdier["geluk"] + 5)
        self.huisdier["stats"]["boodschappen_gedaan"] += 1
        self.huisdier["stats"]["werk_taken"] += 1

        # Achievements
        if self.huisdier["stats"]["boodschappen_gedaan"] >= 10:
            self._unlock_achievement("boodschapper")
        if self.huisdier["stats"]["werk_taken"] >= 25:
            self._unlock_achievement("werkend_huisdier")

        self._check_evolutie()
        print(f"\n  {geluid}")
        self._sla_op()

    def _werk_wiskunde(self):
        """Huisdier lost wiskundige puzzels op."""
        if self.huisdier["munten"] < 8:
            print("\nJe hebt niet genoeg munten! (Nodig: 8)")
            return

        if self.huisdier["energie"] < 10:
            print(f"\n{self.huisdier['naam']} is te moe om na te denken!")
            return

        self.huisdier["munten"] -= 8
        self.huisdier["energie"] = max(0, self.huisdier["energie"] - 10)

        # Init stats
        if "sommen_opgelost" not in self.huisdier["stats"]:
            self.huisdier["stats"]["sommen_opgelost"] = 0
        if "werk_taken" not in self.huisdier["stats"]:
            self.huisdier["stats"]["werk_taken"] = 0

        naam = self.huisdier["naam"]
        geluid = self.huisdier["geluid"]
        evolutie = self.huisdier.get("evolutie_stadium", 0)

        # Moeilijkheid gebaseerd op evolutie
        max_getal = 10 + (evolutie * 5)

        print("\n" + "=" * 50)
        print(f"  [CALCULATOR] {naam} GAAT REKENEN!")
        print("=" * 50)
        time.sleep(0.5)

        print(f"\n  {geluid}")
        print(f"  {naam} pakt een rekenmachine...")
        time.sleep(0.5)

        correct = 0
        totaal = 5

        operaties = [
            ("+", lambda a, b: a + b),
            ("-", lambda a, b: a - b),
            ("x", lambda a, b: a * b),
        ]

        for ronde in range(1, totaal + 1):
            a = random.randint(1, max_getal)
            b = random.randint(1, max_getal)
            op_sym, op_func = random.choice(operaties)

            # Zorg dat aftrekken niet negatief wordt
            if op_sym == "-" and b > a:
                a, b = b, a

            antwoord = op_func(a, b)

            print(f"\n  --- Som {ronde}/{totaal} ---")
            print(f"  Wat is {a} {op_sym} {b} = ?")

            # Huisdier probeert te raden (AI simulatie)
            basis_kans = 60 + (evolutie * 5) + (self.huisdier["geluk"] // 10)
            basis_kans = min(95, basis_kans)

            time.sleep(0.5)

            if random.randint(1, 100) <= basis_kans:
                print(f"  {naam}: \"{antwoord}!\"")
                print(f"  [OK] Correct!")
                correct += 1
            else:
                # Fout antwoord
                fout_antwoord = antwoord + random.choice([-2, -1, 1, 2])
                print(f"  {naam}: \"{fout_antwoord}?\"")
                print(f"  [X] Fout! Het was {antwoord}")

            time.sleep(0.3)

        # Resultaten
        print("\n" + "=" * 50)
        print("  [RESULTAAT] WISKUNDE SESSIE KLAAR!")
        print("=" * 50)

        munt_beloning = correct * 6
        xp_beloning = correct * 8 + 5

        print(f"\n  {naam}'s score:")
        print(f"    [#] Correct: {correct}/{totaal}")
        print(f"    [MUNT] Verdiend: +{munt_beloning} munten")
        print(f"    [XP] Ervaring: +{xp_beloning}")

        if correct == totaal:
            bonus = 15
            print(f"\n  [TROFEE] PERFECT! Bonus: +{bonus} munten!")
            munt_beloning += bonus

        # Geef beloningen
        self.huisdier["munten"] += munt_beloning
        self.huisdier["ervaring"] += xp_beloning
        self.huisdier["stats"]["sommen_opgelost"] += correct
        self.huisdier["stats"]["werk_taken"] += 1

        # Achievements
        if self.huisdier["stats"]["sommen_opgelost"] >= 20:
            self._unlock_achievement("wiskunde_genie")
        if self.huisdier["stats"]["werk_taken"] >= 25:
            self._unlock_achievement("werkend_huisdier")

        self._check_evolutie()
        print(f"\n  {geluid}")
        self._sla_op()

    def _werk_bug_jacht(self):
        """Huisdier zoekt bugs in ECHTE code bestanden."""
        if self.huisdier["munten"] < 12:
            print("\nJe hebt niet genoeg munten! (Nodig: 12)")
            return

        if self.huisdier["energie"] < 20:
            print(f"\n{self.huisdier['naam']} is te moe om code te analyseren!")
            return

        self.huisdier["munten"] -= 12
        self.huisdier["energie"] = max(0, self.huisdier["energie"] - 20)

        # Init stats
        if "bugs_gevonden" not in self.huisdier["stats"]:
            self.huisdier["stats"]["bugs_gevonden"] = 0
        if "werk_taken" not in self.huisdier["stats"]:
            self.huisdier["stats"]["werk_taken"] = 0

        naam = self.huisdier["naam"]
        geluid = self.huisdier["geluid"]

        # Code analyse patronen (verbeterd - minder false positives)
        analyse_patronen = {
            "Security": [
                (r'\beval\s*\(', "eval() gevonden - potentieel gevaarlijk"),
                (r'\bexec\s*\(', "exec() gevonden - potentieel gevaarlijk"),
                (r'os\.system\s*\(', "os.system() - gebruik subprocess"),
                (r'password\s*=\s*["\'][^"\']{3,}["\']', "Hardcoded password"),
                (r'api_key\s*=\s*["\'][^"\']{10,}["\']', "Hardcoded API key"),
                (r'secret\s*=\s*["\'][^"\']{5,}["\']', "Hardcoded secret"),
            ],
            "Code Smell": [
                (r'#\s*(TODO|FIXME|XXX|HACK|BUG):', "TODO/FIXME commentaar"),
                (r'except\s*:\s*$', "Bare except - specificeer exception type"),
            ],
            "Logic": [
                (r'==\s*None\b', "Gebruik 'is None' ipv '== None'"),
                (r'!=\s*None\b', "Gebruik 'is not None' ipv '!= None'"),
                (r'==\s*True\b', "Gebruik 'if x:' ipv 'if x == True'"),
                (r'==\s*False\b', "Gebruik 'if not x:' ipv 'if x == False'"),
            ],
            "Complexity": [
                (r'if .+ and .+ and .+ and .+', "Complexe conditie (4+ and)"),
                (r'lambda.*:.*lambda', "Geneste lambda functies"),
            ],
        }

        print("\n" + "=" * 50)
        print(f"  [CODE] {naam} ANALYSEERT ECHTE CODE!")
        print("=" * 50)
        time.sleep(0.5)

        print(f"\n  {geluid}")
        print(f"  {naam} opent de Code Analyse tool...")
        time.sleep(0.5)

        # Vind echte Python bestanden
        project_dir = Config.BASE_DIR / "danny_toolkit"
        python_bestanden = list(project_dir.glob("**/*.py"))

        if not python_bestanden:
            print("  [!] Geen Python bestanden gevonden!")
            return

        bugs_gevonden = []
        bestanden_geanalyseerd = 0

        # Analyseer max 5 willekeurige bestanden
        for bestand in random.sample(python_bestanden, min(5, len(python_bestanden))):
            relative_path = bestand.relative_to(Config.BASE_DIR)
            print(f"\n  --- Analyseren: {relative_path} ---")
            time.sleep(0.3)

            bestanden_geanalyseerd += 1

            try:
                content = bestand.read_text(encoding="utf-8")
                bestand_bugs = []

                # Check alle patronen
                for categorie, patronen in analyse_patronen.items():
                    for patroon, beschrijving in patronen:
                        matches = re.findall(patroon, content, re.MULTILINE)
                        if matches:
                            bestand_bugs.append((categorie, beschrijving, len(matches)))

                if bestand_bugs:
                    for categorie, beschrijving, count in bestand_bugs[:2]:  # Max 2 per bestand
                        bugs_gevonden.append((categorie, beschrijving, str(relative_path)))
                        print(f"  [BUG] {naam} vindt: {beschrijving}")
                        print(f"        Categorie: {categorie} ({count}x)")
                else:
                    print(f"  [OK] {naam}: Code ziet er goed uit!")

            except Exception as e:
                print(f"  [!] Kon bestand niet lezen: {e}")

            time.sleep(0.2)

        # Resultaten
        print("\n" + "=" * 50)
        print("  [RAPPORT] ECHTE CODE ANALYSE KLAAR!")
        print("=" * 50)

        # Intelligentie bonus voor echte analyse
        intel_bonus = bestanden_geanalyseerd + len(bugs_gevonden)
        munt_beloning = len(bugs_gevonden) * 8 + bestanden_geanalyseerd * 2
        xp_beloning = len(bugs_gevonden) * 10 + bestanden_geanalyseerd * 5

        print(f"\n  {naam}'s analyse rapport:")
        print(f"    [FILE] Bestanden geanalyseerd: {bestanden_geanalyseerd}")
        print(f"    [BUG] Issues gevonden: {len(bugs_gevonden)}")
        if bugs_gevonden:
            for categorie, beschrijving, bestand in bugs_gevonden[:5]:
                print(f"        - [{categorie}] {beschrijving}")
                print(f"          in: {bestand}")
        print(f"    [IQ] Intelligentie: +{intel_bonus}")
        print(f"    [MUNT] Verdiend: +{munt_beloning} munten")
        print(f"    [XP] Ervaring: +{xp_beloning}")

        # Bonus voor veel bugs
        if len(bugs_gevonden) >= 4:
            bonus = 20
            print(f"\n  [TROFEE] SUPER DETECTIVE! Bonus: +{bonus} munten!")
            munt_beloning += bonus

        # Geef beloningen
        self.huisdier["munten"] += munt_beloning
        self.huisdier["ervaring"] += xp_beloning
        self.huisdier["intelligentie"] = self.huisdier.get("intelligentie", 0) + intel_bonus
        self.huisdier["stats"]["bugs_gevonden"] += len(bugs_gevonden)
        self.huisdier["stats"]["werk_taken"] += 1

        # Achievements
        if self.huisdier["stats"]["bugs_gevonden"] >= 15:
            self._unlock_achievement("bug_hunter")
        if self.huisdier["stats"]["werk_taken"] >= 25:
            self._unlock_achievement("werkend_huisdier")
        if self.huisdier.get("intelligentie", 0) >= 100:
            self._unlock_achievement("super_slim")

        self._check_evolutie()
        print(f"\n  {geluid}")
        self._sla_op()

    # ==================== HUISDIER LEREN (AI) ====================

    def _huisdier_leren(self):
        """Menu voor huisdier AI leeractiviteiten."""
        while True:
            intel = self.huisdier.get("intelligentie", 0)
            print("\n+====================================+")
            print("|        HUISDIER LEREN (AI)         |")
            print("+====================================+")
            print(f"|  IQ van {self.huisdier['naam']}: {intel}")
            print("+------------------------------------+")
            print("|  1. RAG Studeren (10 munten)       |")
            print("|     Leer feiten uit de kennisbank  |")
            print("|  2. Nieuws Lezen (8 munten)        |")
            print("|     Blijf op de hoogte van nieuws  |")
            print("|  3. Weer Checken (5 munten)        |")
            print("|     Leer over het weer             |")
            print("|  4. AI Gesprek (15 munten)         |")
            print("|     Praat met Claude AI            |")
            print("|  0. Terug                          |")
            print("+====================================+")

            keuze = input("\nKies een activiteit: ").strip()

            if keuze == "0":
                break
            elif keuze == "1":
                self._leren_rag()
            elif keuze == "2":
                self._leren_nieuws()
            elif keuze == "3":
                self._leren_weer()
            elif keuze == "4":
                self._leren_ai_gesprek()

            input("\nDruk op Enter...")

    def _leren_rag(self):
        """Huisdier leert van de kennisbank (RAG systeem)."""
        if self.huisdier["munten"] < 10:
            print("\nJe hebt niet genoeg munten! (Nodig: 10)")
            return

        if self.huisdier["energie"] < 15:
            print(f"\n{self.huisdier['naam']} is te moe om te studeren!")
            return

        self.huisdier["munten"] -= 10
        self.huisdier["energie"] = max(0, self.huisdier["energie"] - 15)

        # Init stats
        if "feiten_geleerd" not in self.huisdier["stats"]:
            self.huisdier["stats"]["feiten_geleerd"] = 0

        naam = self.huisdier["naam"]
        geluid = self.huisdier["geluid"]

        # Kennisbank onderwerpen
        onderwerpen = {
            "Machine Learning": [
                "ML is een tak van AI waarbij computers leren van data",
                "Supervised learning gebruikt gelabelde trainingsdata",
                "Unsupervised learning vindt patronen zonder labels",
                "Overfitting betekent dat een model te goed past op trainingsdata",
            ],
            "Neural Networks": [
                "Een neuraal netwerk is geinspireerd op het menselijk brein",
                "Backpropagation is hoe neurale netwerken leren",
                "CNN's zijn speciaal voor beeldherkenning",
                "Transformers zijn de basis voor GPT en Claude",
            ],
            "Python": [
                "Decorators wrappen functies voor extra functionaliteit",
                "Generators gebruiken yield voor memory-efficiente iteratie",
                "List comprehensions zijn korte syntax voor lijsten maken",
                "Type hints verbeteren code leesbaarheid",
            ],
            "API Design": [
                "REST API's gebruiken HTTP methodes zoals GET en POST",
                "Status code 200 betekent succes",
                "Status code 404 betekent niet gevonden",
                "JSON is het standaard data formaat voor API's",
            ],
            "Vector Databases": [
                "Embeddings zijn numerieke representaties van tekst",
                "Cosine similarity meet gelijkenis tussen vectoren",
                "RAG combineert retrieval met AI generatie",
                "Chunking splitst documenten in kleinere stukken",
            ],
        }

        print("\n" + "=" * 50)
        print(f"  [BOEK] {naam} GAAT STUDEREN!")
        print("=" * 50)
        time.sleep(0.5)

        print(f"\n  {geluid}")
        print(f"  {naam} opent de kennisbank...")
        time.sleep(0.5)

        feiten_geleerd = []
        intel_bonus = 0

        # Studeer 3 onderwerpen
        for onderwerp in random.sample(list(onderwerpen.keys()), 3):
            print(f"\n  --- Onderwerp: {onderwerp} ---")
            time.sleep(0.4)

            # Leer 1-2 feiten per onderwerp
            feiten = random.sample(onderwerpen[onderwerp], min(2, len(onderwerpen[onderwerp])))
            for feit in feiten:
                if random.randint(1, 100) <= 80:  # 80% kans om te leren
                    feiten_geleerd.append(feit)
                    intel_bonus += 2
                    print(f"  [LAMP] {naam} leert: \"{feit[:50]}...\"")
                else:
                    print(f"  [?] {naam} snapt dit nog niet helemaal...")
            time.sleep(0.3)

        # Resultaten
        print("\n" + "=" * 50)
        print("  [DIPLOMA] STUDIE SESSIE VOLTOOID!")
        print("=" * 50)

        xp_beloning = len(feiten_geleerd) * 10 + 5
        munt_beloning = len(feiten_geleerd) * 3

        print(f"\n  {naam}'s studieresultaten:")
        print(f"    [BOEK] Feiten geleerd: {len(feiten_geleerd)}")
        print(f"    [IQ] Intelligentie: +{intel_bonus}")
        print(f"    [MUNT] Munten: +{munt_beloning}")
        print(f"    [XP] Ervaring: +{xp_beloning}")

        # Geef beloningen
        self.huisdier["munten"] += munt_beloning
        self.huisdier["ervaring"] += xp_beloning
        self.huisdier["intelligentie"] = self.huisdier.get("intelligentie", 0) + intel_bonus
        self.huisdier["stats"]["feiten_geleerd"] += len(feiten_geleerd)

        # Achievements
        if self.huisdier["stats"]["feiten_geleerd"] >= 10:
            self._unlock_achievement("kenniszoeker")
        if self.huisdier.get("intelligentie", 0) >= 100:
            self._unlock_achievement("super_slim")

        self._check_evolutie()
        print(f"\n  {geluid}")
        self._sla_op()

    def _leren_nieuws(self):
        """Huisdier leest nieuws."""
        if self.huisdier["munten"] < 8:
            print("\nJe hebt niet genoeg munten! (Nodig: 8)")
            return

        if self.huisdier["energie"] < 10:
            print(f"\n{self.huisdier['naam']} is te moe om te lezen!")
            return

        self.huisdier["munten"] -= 8
        self.huisdier["energie"] = max(0, self.huisdier["energie"] - 10)

        # Init stats
        if "nieuws_gelezen" not in self.huisdier["stats"]:
            self.huisdier["stats"]["nieuws_gelezen"] = 0

        naam = self.huisdier["naam"]
        geluid = self.huisdier["geluid"]

        # Nieuws onderwerpen
        nieuws_items = [
            ("Tech", "SpaceX lanceert nieuwe Starship raket naar Mars"),
            ("Tech", "Apple kondigt nieuwe AI-functies aan voor iPhone"),
            ("Tech", "Google's quantum computer bereikt doorbraak"),
            ("Sport", "Nederlands elftal wint belangrijke wedstrijd"),
            ("Sport", "Olympische Spelen breken kijkcijferrecords"),
            ("Wetenschap", "Nieuwe ontdekking in zoektocht naar buitenaards leven"),
            ("Wetenschap", "Doorbraak in kernfusie onderzoek"),
            ("Natuur", "Zeldzame diersoort herontdekt in regenwoud"),
            ("Natuur", "Nieuw klimaatakkoord getekend door 50 landen"),
            ("Cultuur", "Blockbuster film breekt box office records"),
        ]

        print("\n" + "=" * 50)
        print(f"  [KRANT] {naam} LEEST HET NIEUWS!")
        print("=" * 50)
        time.sleep(0.5)

        print(f"\n  {geluid}")
        print(f"  {naam} opent de nieuwsapp...")
        time.sleep(0.5)

        gelezen = []
        intel_bonus = 0

        # Lees 4 nieuwsberichten
        for categorie, titel in random.sample(nieuws_items, 4):
            print(f"\n  --- {categorie.upper()} ---")
            print(f"  [>] {titel}")
            time.sleep(0.4)

            if random.randint(1, 100) <= 75:
                gelezen.append(titel)
                intel_bonus += 1
                reacties = [
                    f"{naam} vindt dit interessant!",
                    f"{naam} onthoudt dit nieuws.",
                    f"{naam} deelt dit met vrienden!",
                ]
                print(f"  [OK] {random.choice(reacties)}")
            else:
                print(f"  [_] {naam} scrollt verder...")

            time.sleep(0.3)

        # Resultaten
        print("\n" + "=" * 50)
        print("  [NIEUWS] KLAAR MET LEZEN!")
        print("=" * 50)

        xp_beloning = len(gelezen) * 5 + 5
        munt_beloning = len(gelezen) * 2

        print(f"\n  {naam}'s nieuwsoverzicht:")
        print(f"    [KRANT] Artikelen gelezen: {len(gelezen)}")
        print(f"    [IQ] Intelligentie: +{intel_bonus}")
        print(f"    [MUNT] Munten: +{munt_beloning}")
        print(f"    [XP] Ervaring: +{xp_beloning}")

        # Geef beloningen
        self.huisdier["munten"] += munt_beloning
        self.huisdier["ervaring"] += xp_beloning
        self.huisdier["intelligentie"] = self.huisdier.get("intelligentie", 0) + intel_bonus
        self.huisdier["stats"]["nieuws_gelezen"] += len(gelezen)
        self.huisdier["geluk"] = min(100, self.huisdier["geluk"] + 3)

        # Achievements
        if self.huisdier["stats"]["nieuws_gelezen"] >= 10:
            self._unlock_achievement("nieuwslezer")
        if self.huisdier.get("intelligentie", 0) >= 100:
            self._unlock_achievement("super_slim")

        self._check_evolutie()
        print(f"\n  {geluid}")
        self._sla_op()

    def _leren_weer(self):
        """Huisdier checkt het weer."""
        if self.huisdier["munten"] < 5:
            print("\nJe hebt niet genoeg munten! (Nodig: 5)")
            return

        self.huisdier["munten"] -= 5

        # Init stats
        if "weer_gecheckt" not in self.huisdier["stats"]:
            self.huisdier["stats"]["weer_gecheckt"] = 0

        naam = self.huisdier["naam"]
        geluid = self.huisdier["geluid"]

        # Steden en weer
        steden = ["Amsterdam", "Rotterdam", "Utrecht", "Eindhoven", "Groningen"]
        weer_types = [
            ("Zonnig", "[ZON]", "Lekker weer om buiten te spelen!"),
            ("Bewolkt", "[WOLK]", "Misschien later regen..."),
            ("Regen", "[REGEN]", "Neem een paraplu mee!"),
            ("Sneeuw", "[SNEEUW]", "Tijd voor een sneeuwpop!"),
            ("Storm", "[STORM]", "Beter binnen blijven vandaag!"),
        ]

        stad = random.choice(steden)
        weer, emoji, advies = random.choice(weer_types)
        temp = random.randint(-5, 30)
        wind = random.randint(0, 80)

        print("\n" + "=" * 50)
        print(f"  [WEER] {naam} CHECKT HET WEER!")
        print("=" * 50)
        time.sleep(0.5)

        print(f"\n  {geluid}")
        print(f"  {naam} kijkt naar buiten...")
        time.sleep(0.5)

        print(f"\n  --- Weer in {stad} ---")
        print(f"  {emoji} {weer}")
        print(f"  [TEMP] Temperatuur: {temp}C")
        print(f"  [WIND] Wind: {wind} km/u")
        print(f"\n  [TIP] {advies}")

        intel_bonus = 1
        xp_beloning = 8
        munt_beloning = 2

        # Bonus voor extreem weer
        if temp > 25 or temp < 0 or wind > 50:
            print(f"\n  [!] {naam} leert over extreem weer! +1 IQ")
            intel_bonus += 1

        print("\n" + "=" * 50)
        print(f"    [IQ] Intelligentie: +{intel_bonus}")
        print(f"    [MUNT] Munten: +{munt_beloning}")
        print(f"    [XP] Ervaring: +{xp_beloning}")

        # Geef beloningen
        self.huisdier["munten"] += munt_beloning
        self.huisdier["ervaring"] += xp_beloning
        self.huisdier["intelligentie"] = self.huisdier.get("intelligentie", 0) + intel_bonus
        self.huisdier["stats"]["weer_gecheckt"] += 1

        # Achievements
        if self.huisdier["stats"]["weer_gecheckt"] >= 10:
            self._unlock_achievement("weerwatcher")
        if self.huisdier.get("intelligentie", 0) >= 100:
            self._unlock_achievement("super_slim")

        self._check_evolutie()
        print(f"\n  {geluid}")
        self._sla_op()

    def _leren_ai_gesprek(self):
        """Huisdier heeft een gesprek met AI."""
        if self.huisdier["munten"] < 15:
            print("\nJe hebt niet genoeg munten! (Nodig: 15)")
            return

        if self.huisdier["energie"] < 20:
            print(f"\n{self.huisdier['naam']} is te moe voor een diep gesprek!")
            return

        self.huisdier["munten"] -= 15
        self.huisdier["energie"] = max(0, self.huisdier["energie"] - 20)

        # Init stats
        if "ai_gesprekken" not in self.huisdier["stats"]:
            self.huisdier["stats"]["ai_gesprekken"] = 0

        naam = self.huisdier["naam"]
        geluid = self.huisdier["geluid"]
        huisdier_type = self.huisdier["type"]

        # AI gesprek onderwerpen
        gesprekken = [
            {
                "vraag": "Wat is de zin van het leven?",
                "antwoord": "Het leven gaat over leren, groeien en anderen helpen!",
                "les": "Filosofie is nadenken over belangrijke vragen",
            },
            {
                "vraag": "Hoe werkt kunstmatige intelligentie?",
                "antwoord": "AI leert patronen van grote hoeveelheden data!",
                "les": "AI is gebaseerd op wiskunde en statistiek",
            },
            {
                "vraag": "Waarom is de lucht blauw?",
                "antwoord": "Zonlicht verstrooit in de atmosfeer, blauw het meest!",
                "les": "Dit heet Rayleigh-verstrooiing",
            },
            {
                "vraag": "Hoe groot is het universum?",
                "antwoord": "Het waarneembare universum is 93 miljard lichtjaar breed!",
                "les": "Het universum breidt nog steeds uit",
            },
            {
                "vraag": "Waarom hebben we slaap nodig?",
                "antwoord": "Slaap helpt ons brein om herinneringen te verwerken!",
                "les": "Slaap is essentieel voor gezondheid",
            },
            {
                "vraag": f"Wat maakt een {huisdier_type} speciaal?",
                "antwoord": f"Elke {huisdier_type} is uniek en heeft eigen talenten!",
                "les": f"{naam} is heel bijzonder",
            },
        ]

        print("\n" + "=" * 50)
        print(f"  [AI] {naam} PRAAT MET CLAUDE AI!")
        print("=" * 50)
        time.sleep(0.5)

        print(f"\n  {geluid}")
        print(f"  {naam} opent Claude Chat...")
        time.sleep(0.8)

        intel_bonus = 0
        lessen_geleerd = []

        # Voer 3 gesprekken
        for gesprek in random.sample(gesprekken, 3):
            print(f"\n  --- Nieuw Gesprek ---")
            print(f"  {naam}: \"{gesprek['vraag']}\"")
            time.sleep(0.6)

            print(f"  Claude: \"{gesprek['antwoord']}\"")
            time.sleep(0.4)

            if random.randint(1, 100) <= 85:
                lessen_geleerd.append(gesprek["les"])
                intel_bonus += 3
                print(f"  [LAMP] {naam} leert: {gesprek['les']}")
            else:
                print(f"  [?] {naam} moet hier nog over nadenken...")

            time.sleep(0.3)

        # Resultaten
        print("\n" + "=" * 50)
        print("  [CHAT] AI GESPREK VOLTOOID!")
        print("=" * 50)

        xp_beloning = len(lessen_geleerd) * 15 + 10
        munt_beloning = len(lessen_geleerd) * 5

        print(f"\n  {naam}'s gesprek met Claude:")
        print(f"    [CHAT] Gesprekken: 3")
        print(f"    [LAMP] Lessen geleerd: {len(lessen_geleerd)}")
        print(f"    [IQ] Intelligentie: +{intel_bonus}")
        print(f"    [MUNT] Munten: +{munt_beloning}")
        print(f"    [XP] Ervaring: +{xp_beloning}")

        if len(lessen_geleerd) == 3:
            bonus = 10
            print(f"\n  [TROFEE] PERFECTE STUDENT! Bonus: +{bonus} munten!")
            munt_beloning += bonus

        # Geef beloningen
        self.huisdier["munten"] += munt_beloning
        self.huisdier["ervaring"] += xp_beloning
        self.huisdier["intelligentie"] = self.huisdier.get("intelligentie", 0) + intel_bonus
        self.huisdier["stats"]["ai_gesprekken"] += 1
        self.huisdier["geluk"] = min(100, self.huisdier["geluk"] + 5)

        # Achievements
        if self.huisdier["stats"]["ai_gesprekken"] >= 10:
            self._unlock_achievement("ai_student")
        if self.huisdier.get("intelligentie", 0) >= 100:
            self._unlock_achievement("super_slim")

        self._check_evolutie()
        print(f"\n  {geluid}")
        self._sla_op()

    def _tricks_menu(self):
        """Tricks leren en uitvoeren."""
        while True:
            geleerde = self.huisdier["tricks_geleerd"]

            print("\n+================================+")
            print("|      TRICKS                    |")
            print("+================================+")
            print("|  LEREN:                        |")

            beschikbaar = []
            for trick_id, trick in self.TRICKS.items():
                if trick_id not in geleerde:
                    beschikbaar.append((trick_id, trick))
                    print(f"|  L{len(beschikbaar)}. {trick['naam']:<15} "
                          f"(Moeilijkheid: {trick['moeilijkheid']}) |")

            if geleerde:
                print("|                                |")
                print("|  UITVOEREN:                    |")
                for i, trick_id in enumerate(geleerde, 1):
                    trick = self.TRICKS[trick_id]
                    print(f"|  {i}. {trick['naam']:<20} |")

            print("|  0. Terug                      |")
            print("+================================+")

            keuze = input("\nKeuze: ").strip().lower()

            if keuze == "0":
                break
            elif keuze.startswith("l") and len(keuze) > 1:
                try:
                    idx = int(keuze[1:]) - 1
                    if 0 <= idx < len(beschikbaar):
                        self._leer_trick(beschikbaar[idx][0])
                except (ValueError, IndexError):
                    pass
            else:
                try:
                    idx = int(keuze) - 1
                    if 0 <= idx < len(geleerde):
                        self._voer_trick_uit(geleerde[idx])
                except (ValueError, IndexError):
                    pass

            input("\nDruk op Enter...")

    def _leer_trick(self, trick_id: str):
        """Leer een nieuwe trick."""
        trick = self.TRICKS[trick_id]
        kosten = trick["moeilijkheid"] * 20

        if self.huisdier["munten"] < kosten:
            print(f"\nJe hebt niet genoeg munten! (Nodig: {kosten})")
            return

        if self.huisdier["energie"] < 30:
            print(f"\n{self.huisdier['naam']} is te moe om te leren!")
            return

        print(f"\nJe leert {self.huisdier['naam']} '{trick['naam']}'... (-{kosten} munten)")
        time.sleep(1)

        # Kans op succes
        kans = 100 - (trick["moeilijkheid"] * 15)
        if random.randint(1, 100) <= kans:
            self.huisdier["munten"] -= kosten
            self.huisdier["tricks_geleerd"].append(trick_id)
            self.huisdier["energie"] = max(0, self.huisdier["energie"] - 20)
            self.huisdier["ervaring"] += trick["moeilijkheid"] * 10

            print(f"[OK] {self.huisdier['naam']} heeft '{trick['naam']}' geleerd!")

            if len(self.huisdier["tricks_geleerd"]) == 1:
                self._unlock_achievement("eerste_trick")
            if len(self.huisdier["tricks_geleerd"]) == len(self.TRICKS):
                self._unlock_achievement("alle_tricks")
        else:
            self.huisdier["munten"] -= kosten // 2
            self.huisdier["energie"] = max(0, self.huisdier["energie"] - 10)
            print(f"Helaas, {self.huisdier['naam']} heeft het nog niet onder de knie...")
            print(f"(-{kosten // 2} munten)")

    def _voer_trick_uit(self, trick_id: str):
        """Voer een geleerde trick uit."""
        trick = self.TRICKS[trick_id]

        print(f"\n{self.huisdier['naam']} voert '{trick['naam']}' uit...")
        time.sleep(0.5)

        self.huisdier["geluk"] = min(100, self.huisdier["geluk"] + trick["geluk_bonus"])
        self.huisdier["stats"]["tricks_uitgevoerd"] += 1
        beloning = trick.get("beloning", trick["moeilijkheid"] * 2)
        self.huisdier["munten"] += beloning
        self.huisdier["ervaring"] += trick["moeilijkheid"] * 5

        reacties = [
            f"[SHOW] Geweldig! {self.huisdier['naam']} doet het perfect!",
            f"Wow! {self.huisdier['naam']} is een ster!",
            f"{self.huisdier['geluid']} - Applaus!",
        ]
        print(random.choice(reacties))
        print(f"+{beloning} munten!")

    def _winkel(self):
        """Accessoires winkel."""
        while True:
            print("\n+================================+")
            print("|         WINKEL                 |")
            print(f"|    Jouw munten: {self.huisdier['munten']:<14}|")
            print("+================================+")

            beschikbaar = []
            for acc_id, acc in self.ACCESSOIRES.items():
                if acc_id not in self.huisdier["accessoires"]:
                    beschikbaar.append((acc_id, acc))
                    print(f"|  {len(beschikbaar)}. {acc['naam']:<15} "
                          f"{acc['prijs']:>4} munten |")
                    print(f"|     ({acc['effect']} +{acc['bonus']})")

            if not beschikbaar:
                print("|  Je hebt alles al!             |")

            print("|  0. Terug                      |")
            print("+================================+")

            keuze = input("\nWat wil je kopen? ").strip()

            if keuze == "0":
                break

            try:
                idx = int(keuze) - 1
                if 0 <= idx < len(beschikbaar):
                    acc_id, acc = beschikbaar[idx]

                    if self.huisdier["munten"] >= acc["prijs"]:
                        self.huisdier["munten"] -= acc["prijs"]
                        self.huisdier["accessoires"].append(acc_id)
                        print(f"\n[BONUS] Je hebt '{acc['naam']}' gekocht!")

                        if len(self.huisdier["accessoires"]) == 1:
                            self._unlock_achievement("eerste_accessoire")
                        if len(self.huisdier["accessoires"]) == len(self.ACCESSOIRES):
                            self._unlock_achievement("alle_accessoires")
                    else:
                        print("\nJe hebt niet genoeg munten!")
            except (ValueError, IndexError):
                pass

            input("\nDruk op Enter...")

    def _achievements_bekijken(self):
        """Bekijk achievements."""
        print("\n+================================+")
        print("|       ACHIEVEMENTS             |")
        print("+================================+")

        totaal_punten = 0
        unlocked = 0

        for ach_id, ach in self.ACHIEVEMENTS.items():
            if ach_id in self.huisdier["achievements"]:
                print(f"| ✓ {ach['naam']:<20} +{ach['punten']:>3} |")
                totaal_punten += ach["punten"]
                unlocked += 1
            else:
                print(f"| ? {ach['naam']:<20}  ???  |")

        print("+================================+")
        print(f"| Unlocked: {unlocked}/{len(self.ACHIEVEMENTS):<18}|")
        print(f"| Totaal punten: {totaal_punten:<13}|")
        print("+================================+")

    def _dagelijkse_bonus(self):
        """Claim dagelijkse bonus."""
        bonus_data = self.huisdier["dagelijkse_bonus"]
        nu = datetime.now().date()

        if bonus_data["laatste_claim"]:
            laatste = datetime.fromisoformat(bonus_data["laatste_claim"]).date()

            if laatste == nu:
                print("\nJe hebt de dagelijkse bonus al geclaimd!")
                print(f"Huidige streak: {bonus_data['streak']} dagen")
                return

            if laatste == nu - timedelta(days=1):
                bonus_data["streak"] += 1
            else:
                bonus_data["streak"] = 1
        else:
            bonus_data["streak"] = 1

        bonus_data["laatste_claim"] = nu.isoformat()

        # Bereken bonus
        basis_bonus = 20
        streak_bonus = min(bonus_data["streak"] * 5, 50)
        totaal = basis_bonus + streak_bonus

        self.huisdier["munten"] += totaal
        self.huisdier["stats"]["dagen_gespeeld"] += 1

        print(f"\n[BONUS] DAGELIJKSE BONUS!")
        print(f"   Basis: +{basis_bonus} munten")
        print(f"   Streak ({bonus_data['streak']} dagen): +{streak_bonus} munten")
        print(f"   Totaal: +{totaal} munten!")

        # Achievement checks
        if bonus_data["streak"] >= 7:
            self._unlock_achievement("dagelijkse_bonus")

        # Leeftijd achievements
        if self.huisdier["leeftijd_dagen"] >= 7:
            self._unlock_achievement("week_oud")
        if self.huisdier["leeftijd_dagen"] >= 30:
            self._unlock_achievement("maand_oud")

    def run(self):
        """Start de app."""
        clear_scherm()
        print("+=======================================+")
        print("|   VIRTUEEL HUISDIER SIMULATOR v2.0   |")
        print("|   Met achievements, tricks & meer!   |")
        print("+=======================================+")

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

            keuze = input("\nJouw keuze (0-10): ").strip()

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
                self._mini_games()
            elif keuze == "7":
                self._tricks_menu()
            elif keuze == "8":
                self._winkel()
            elif keuze == "9":
                self._achievements_bekijken()
            elif keuze == "10":
                self._dagelijkse_bonus()
            elif keuze == "11":
                self._huisdier_werk()
            elif keuze == "12":
                self._huisdier_leren()
            elif keuze == "0":
                self._sla_op()
                print(f"\n{self.huisdier['naam']} is opgeslagen!")
                print(f"Tot de volgende keer! {self.huisdier['emoji']}")
                break
            else:
                print("Ongeldige keuze!")
                continue

            self._sla_op()
            input("\nDruk op Enter om verder te gaan...")

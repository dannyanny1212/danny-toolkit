"""
Schatzoek Game App - Uitgebreide versie.
"""

import json
import random
from pathlib import Path
from ..core.utils import clear_scherm
from ..core.config import Config


class SchatzoekApp:
    """Schatzoek game - vind alle schatten in het grid!"""

    MOEILIJKHEID = {
        "makkelijk": {"grid": 4, "schatten": 2, "muren": 2, "vallen": 1, "powerups": 2},
        "normaal": {"grid": 6, "schatten": 3, "muren": 4, "vallen": 2, "powerups": 2},
        "moeilijk": {"grid": 8, "schatten": 5, "muren": 8, "vallen": 4, "powerups": 3},
    }

    def __init__(self):
        Config.ensure_dirs()
        self.highscore_file = Config.APPS_DATA_DIR / "schatzoek_scores.json"
        self.moeilijkheid = "normaal"
        self.grid_grootte = 6
        self.aantal_schatten = 3
        self.speler_positie = (0, 0)
        self.schatten = set()
        self.gevonden_schatten = set()
        self.muren = set()
        self.vallen = set()
        self.powerups = {}
        self.inventory = []
        self.stappen = 0
        self.highscores = self._laad_highscores()

    def _laad_highscores(self) -> dict:
        """Laadt highscores uit bestand."""
        if self.highscore_file.exists():
            with open(self.highscore_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"makkelijk": [], "normaal": [], "moeilijk": []}

    def _sla_highscore_op(self, naam: str, stappen: int):
        """Slaat een nieuwe highscore op."""
        self.highscores[self.moeilijkheid].append({
            "naam": naam,
            "stappen": stappen
        })
        self.highscores[self.moeilijkheid].sort(key=lambda x: x["stappen"])
        self.highscores[self.moeilijkheid] = self.highscores[self.moeilijkheid][:5]

        with open(self.highscore_file, "w", encoding="utf-8") as f:
            json.dump(self.highscores, f, indent=2, ensure_ascii=False)

    def _toon_highscores(self):
        """Toont de highscores."""
        print("\n" + "=" * 40)
        print("         HIGHSCORES")
        print("=" * 40)

        for niveau in ["makkelijk", "normaal", "moeilijk"]:
            print(f"\n  [{niveau.upper()}]")
            scores = self.highscores.get(niveau, [])
            if scores:
                for i, score in enumerate(scores[:5], 1):
                    print(f"    {i}. {score['naam']}: {score['stappen']} stappen")
            else:
                print("    Nog geen scores!")

        print("\n" + "=" * 40)

    def _bereken_afstand(self, pos1: tuple, pos2: tuple) -> int:
        """Berekent de Manhattan-afstand tussen twee posities."""
        return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])

    def _krijg_richting(self, doel: tuple) -> str:
        """Geeft de richting naar een doel."""
        x, y = self.speler_positie
        dx, dy = doel[0] - x, doel[1] - y

        richtingen = []
        if dy < 0:
            richtingen.append("Noord")
        elif dy > 0:
            richtingen.append("Zuid")
        if dx > 0:
            richtingen.append("Oost")
        elif dx < 0:
            richtingen.append("West")

        return "-".join(richtingen) if richtingen else "Hier!"

    def _krijg_hint(self) -> str:
        """Geeft een hint gebaseerd op afstand tot dichtstbijzijnde schat."""
        niet_gevonden = self.schatten - self.gevonden_schatten
        if not niet_gevonden:
            return "Alle schatten gevonden!"

        kleinste_afstand = min(
            self._bereken_afstand(self.speler_positie, schat)
            for schat in niet_gevonden
        )

        if kleinste_afstand == 0:
            return "SCHAT GEVONDEN!"
        elif kleinste_afstand == 1:
            return "Gloeiend heet! Je bent er bijna!"
        elif kleinste_afstand == 2:
            return "Warm... je komt dichterbij!"
        elif kleinste_afstand <= 4:
            return "Lauw... blijf zoeken!"
        else:
            return "Koud... de schat is nog ver weg."

    def _toon_grid(self):
        """Toont het speelveld."""
        print("\n  ", end="")
        for x in range(self.grid_grootte):
            print(f" {x}", end="")
        print()

        for y in range(self.grid_grootte):
            print(f" {y} ", end="")
            for x in range(self.grid_grootte):
                pos = (x, y)
                if pos == self.speler_positie:
                    print("@", end=" ")
                elif pos in self.gevonden_schatten:
                    print("$", end=" ")
                elif pos in self.muren:
                    print("#", end=" ")
                elif pos in self.powerups:
                    print("?", end=" ")
                else:
                    print(".", end=" ")
            print()

    def _toon_instructies(self):
        """Toont de spelinstructies."""
        settings = self.MOEILIJKHEID[self.moeilijkheid]
        print(f"\n=== HOE TE SPELEN ({self.moeilijkheid.upper()}) ===")
        print(f"Grid: {settings['grid']}x{settings['grid']}")
        print(f"Schatten: {settings['schatten']}")
        print(f"Muren: {settings['muren']}, Vallen: {settings['vallen']}")
        print("\nSymbolen:")
        print("  @ = Jij")
        print("  $ = Gevonden schat")
        print("  # = Muur (niet doorheen)")
        print("  ? = Power-up")
        print("  . = Leeg veld (of verborgen val!)")
        print("\nBeweging: n/o/z/w")
        print("Power-ups: k=kompas, r=radar, t=teleport")
        print("Stoppen: q")
        print("=" * 35)

    def _kies_moeilijkheid(self) -> str:
        """Laat speler moeilijkheid kiezen."""
        print("\nKies moeilijkheid:")
        print("  1. Makkelijk (4x4, 2 schatten)")
        print("  2. Normaal   (6x6, 3 schatten)")
        print("  3. Moeilijk  (8x8, 5 schatten)")

        keuze = input("\nKeuze (1-3): ").strip()
        if keuze == "1":
            return "makkelijk"
        elif keuze == "3":
            return "moeilijk"
        return "normaal"

    def _reset(self):
        """Reset het spel met gekozen moeilijkheid."""
        settings = self.MOEILIJKHEID[self.moeilijkheid]
        self.grid_grootte = settings["grid"]
        self.aantal_schatten = settings["schatten"]

        self.speler_positie = (0, 0)
        self.schatten = set()
        self.gevonden_schatten = set()
        self.muren = set()
        self.vallen = set()
        self.powerups = {}
        self.inventory = []
        self.stappen = 0

        bezet = {self.speler_positie}

        # Plaats schatten
        while len(self.schatten) < self.aantal_schatten:
            pos = (random.randint(0, self.grid_grootte - 1),
                   random.randint(0, self.grid_grootte - 1))
            if pos not in bezet:
                self.schatten.add(pos)
                bezet.add(pos)

        # Plaats muren
        while len(self.muren) < settings["muren"]:
            pos = (random.randint(0, self.grid_grootte - 1),
                   random.randint(0, self.grid_grootte - 1))
            if pos not in bezet:
                self.muren.add(pos)
                bezet.add(pos)

        # Plaats vallen (onzichtbaar!)
        while len(self.vallen) < settings["vallen"]:
            pos = (random.randint(0, self.grid_grootte - 1),
                   random.randint(0, self.grid_grootte - 1))
            if pos not in bezet:
                self.vallen.add(pos)
                bezet.add(pos)

        # Plaats power-ups
        powerup_types = ["kompas", "radar", "teleport"]
        for _ in range(settings["powerups"]):
            pos = (random.randint(0, self.grid_grootte - 1),
                   random.randint(0, self.grid_grootte - 1))
            if pos not in bezet:
                self.powerups[pos] = random.choice(powerup_types)
                bezet.add(pos)

    def _gebruik_kompas(self):
        """Kompas: toont richting naar dichtstbijzijnde schat."""
        if "kompas" not in self.inventory:
            print("Je hebt geen kompas!")
            return

        niet_gevonden = self.schatten - self.gevonden_schatten
        if not niet_gevonden:
            print("Alle schatten al gevonden!")
            return

        dichtstbij = min(niet_gevonden,
                        key=lambda s: self._bereken_afstand(self.speler_positie, s))
        richting = self._krijg_richting(dichtstbij)

        self.inventory.remove("kompas")
        print(f"\n[KOMPAS] De schat ligt richting: {richting}")

    def _gebruik_radar(self):
        """Radar: toont exacte afstand naar alle schatten."""
        if "radar" not in self.inventory:
            print("Je hebt geen radar!")
            return

        niet_gevonden = self.schatten - self.gevonden_schatten
        if not niet_gevonden:
            print("Alle schatten al gevonden!")
            return

        self.inventory.remove("radar")
        print("\n[RADAR] Afstanden tot schatten:")
        for i, schat in enumerate(niet_gevonden, 1):
            afstand = self._bereken_afstand(self.speler_positie, schat)
            print(f"  Schat {i}: {afstand} stappen")

    def _gebruik_teleport(self):
        """Teleport: spring naar een gekozen positie."""
        if "teleport" not in self.inventory:
            print("Je hebt geen teleport!")
            return

        try:
            coords = input("Teleport naar (x,y): ").strip()
            x, y = map(int, coords.replace(" ", "").split(","))

            if not (0 <= x < self.grid_grootte and 0 <= y < self.grid_grootte):
                print("Ongeldige coordinaten!")
                return

            if (x, y) in self.muren:
                print("Je kunt niet naar een muur teleporteren!")
                return

            self.inventory.remove("teleport")
            self.speler_positie = (x, y)
            print(f"\n[TELEPORT] Je bent nu op ({x}, {y})!")

        except ValueError:
            print("Gebruik format: x,y (bijv: 3,4)")

    def _check_val(self) -> bool:
        """Controleert of speler in een val is gestapt."""
        if self.speler_positie in self.vallen:
            self.vallen.remove(self.speler_positie)
            print("\n*** OEPS! Je bent in een val gestapt! ***")

            if self.inventory:
                verloren = self.inventory.pop()
                print(f"Je bent je {verloren} kwijtgeraakt!")
            else:
                self.stappen += 3
                print("Je verliest 3 extra stappen!")

            return True
        return False

    def _check_powerup(self):
        """Controleert of speler een power-up heeft gevonden."""
        if self.speler_positie in self.powerups:
            powerup = self.powerups.pop(self.speler_positie)
            self.inventory.append(powerup)
            print(f"\n*** POWER-UP! Je hebt een {powerup.upper()} gevonden! ***")

    def run(self):
        """Start de app."""
        clear_scherm()
        print("=" * 45)
        print("   WELKOM BIJ DE SCHATZOEK-GAME!")
        print("   Nu met moeilijkheidsgraden & power-ups!")
        print("=" * 45)

        # Toon highscores
        self._toon_highscores()

        # Kies moeilijkheid
        self.moeilijkheid = self._kies_moeilijkheid()
        self._reset()

        self._toon_instructies()
        input("\nDruk op Enter om te beginnen...")

        while len(self.gevonden_schatten) < self.aantal_schatten:
            clear_scherm()
            print(f"\n=== SCHATZOEK ({self.moeilijkheid.upper()}) === Stappen: {self.stappen}")
            print(f"Schatten: {len(self.gevonden_schatten)}/{self.aantal_schatten}")
            if self.inventory:
                print(f"Inventory: {', '.join(self.inventory)}")

            self._toon_grid()

            # Check voor schat op huidige positie
            if self.speler_positie in self.schatten and \
               self.speler_positie not in self.gevonden_schatten:
                self.gevonden_schatten.add(self.speler_positie)
                print("\n*** HOERA! Je hebt een schat gevonden! ***")
                if len(self.gevonden_schatten) < self.aantal_schatten:
                    input("Druk op Enter om verder te zoeken...")
                    continue
                else:
                    break

            # Toon hint
            hint = self._krijg_hint()
            print(f"\nHint: {hint}")

            # Vraag om input
            x, y = self.speler_positie
            print(f"\nPositie: ({x}, {y})")
            actie = input("Actie (n/o/z/w/k/r/t/q): ").lower().strip()

            # Power-ups
            if actie == "k":
                self._gebruik_kompas()
                input("Druk op Enter...")
                continue
            elif actie == "r":
                self._gebruik_radar()
                input("Druk op Enter...")
                continue
            elif actie == "t":
                self._gebruik_teleport()
                self._check_val()
                self._check_powerup()
                continue

            # Verwerk beweging
            nieuwe_x, nieuwe_y = self.speler_positie

            if actie == "n":
                nieuwe_y -= 1
            elif actie == "z":
                nieuwe_y += 1
            elif actie == "o":
                nieuwe_x += 1
            elif actie == "w":
                nieuwe_x -= 1
            elif actie == "q":
                print("\nBedankt voor het spelen!")
                print(f"Je hebt {len(self.gevonden_schatten)} schat(ten) gevonden.")
                input("\nDruk op Enter...")
                return
            else:
                print("Ongeldige invoer!")
                input("Druk op Enter...")
                continue

            # Check grenzen en muren
            nieuwe_pos = (nieuwe_x, nieuwe_y)
            if not (0 <= nieuwe_x < self.grid_grootte and
                    0 <= nieuwe_y < self.grid_grootte):
                print("Je kunt niet van het grid af!")
                input("Druk op Enter...")
                continue

            if nieuwe_pos in self.muren:
                print("Daar staat een muur!")
                input("Druk op Enter...")
                continue

            # Beweeg
            self.speler_positie = nieuwe_pos
            self.stappen += 1

            # Check val en power-up
            self._check_val()
            self._check_powerup()

        # Eindscherm
        clear_scherm()
        print("\n" + "=" * 50)
        print("   GEFELICITEERD! JE HEBT ALLE SCHATTEN GEVONDEN!")
        print("=" * 50)
        self._toon_grid()
        print(f"\nMoeilijkheid: {self.moeilijkheid.upper()}")
        print(f"Stappen: {self.stappen}")

        # Check highscore
        huidige_scores = self.highscores.get(self.moeilijkheid, [])
        is_highscore = len(huidige_scores) < 5 or \
                       self.stappen < huidige_scores[-1]["stappen"]

        if is_highscore:
            print("\n*** NIEUWE HIGHSCORE! ***")
            naam = input("Voer je naam in: ").strip() or "Anoniem"
            self._sla_highscore_op(naam, self.stappen)

        self._toon_highscores()
        print("\nBedankt voor het spelen!")
        input("\nDruk op Enter om terug te gaan...")

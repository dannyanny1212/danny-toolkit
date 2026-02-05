"""
Schatzoek Game App.
"""

import random
from ..core.utils import clear_scherm


class SchatzoekApp:
    """Schatzoek game - vind alle schatten in het grid!"""

    def __init__(self):
        self.grid_grootte = 5
        self.aantal_schatten = 3
        self.speler_positie = (0, 0)
        self.schatten = set()
        self.gevonden_schatten = set()
        self.stappen = 0

    def _bereken_afstand(self, pos1: tuple, pos2: tuple) -> int:
        """Berekent de Manhattan-afstand tussen twee posities."""
        return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])

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
        elif kleinste_afstand == 3:
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
                if (x, y) == self.speler_positie:
                    print("@", end=" ")
                elif (x, y) in self.gevonden_schatten:
                    print("X", end=" ")
                else:
                    print(".", end=" ")
            print()

    def _toon_instructies(self):
        """Toont de spelinstructies."""
        print("\n=== HOE TE SPELEN ===")
        print("Je bent de @ op het grid.")
        print("Vind alle 3 verborgen schatten!")
        print("\nBeweging:")
        print("  n = Noord (omhoog)")
        print("  z = Zuid (omlaag)")
        print("  o = Oost (rechts)")
        print("  w = West (links)")
        print("\nTips:")
        print("  X = Gevonden schat")
        print("  Let op de hints!")
        print("=" * 22)

    def _reset(self):
        """Reset het spel."""
        self.speler_positie = (0, 0)
        self.schatten = set()
        self.gevonden_schatten = set()
        self.stappen = 0

        while len(self.schatten) < self.aantal_schatten:
            x = random.randint(0, self.grid_grootte - 1)
            y = random.randint(0, self.grid_grootte - 1)
            if (x, y) != self.speler_positie:
                self.schatten.add((x, y))

    def run(self):
        """Start de app."""
        self._reset()

        clear_scherm()
        print("=" * 40)
        print("   WELKOM BIJ DE SCHATZOEK-GAME!")
        print("=" * 40)
        self._toon_instructies()
        input("\nDruk op Enter om te beginnen...")

        while len(self.gevonden_schatten) < self.aantal_schatten:
            clear_scherm()
            print(f"\n=== SCHATZOEK-GAME === Stappen: {self.stappen}")
            print(f"Schatten gevonden: {len(self.gevonden_schatten)}/{self.aantal_schatten}")

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
            beweging = input("Waar wil je heen? (n/o/z/w of q=stoppen): ").lower().strip()

            # Verwerk beweging
            nieuwe_x, nieuwe_y = self.speler_positie

            if beweging == "n":
                nieuwe_y -= 1
            elif beweging == "z":
                nieuwe_y += 1
            elif beweging == "o":
                nieuwe_x += 1
            elif beweging == "w":
                nieuwe_x -= 1
            elif beweging == "q":
                print("\nBedankt voor het spelen!")
                print(f"Je hebt {len(self.gevonden_schatten)} schat(ten) gevonden in {self.stappen} stappen.")
                return
            else:
                print("Ongeldige invoer! Gebruik n/o/z/w of q.")
                input("Druk op Enter...")
                continue

            # Check grenzen
            if 0 <= nieuwe_x < self.grid_grootte and 0 <= nieuwe_y < self.grid_grootte:
                self.speler_positie = (nieuwe_x, nieuwe_y)
                self.stappen += 1
            else:
                print("Je kunt niet van het grid af!")
                input("Druk op Enter...")

        # Eindscherm
        clear_scherm()
        print("\n" + "=" * 50)
        print("   GEFELICITEERD! JE HEBT ALLE SCHATTEN GEVONDEN!")
        print("=" * 50)
        self._toon_grid()
        print(f"\nJe hebt het spel gewonnen in {self.stappen} stappen!")

        if self.stappen <= 10:
            print("Ongelooflijk! Je bent een echte schattenjager!")
        elif self.stappen <= 20:
            print("Goed gedaan! Je hebt een goede neus voor schatten!")
        elif self.stappen <= 30:
            print("Niet slecht! Met oefening word je beter!")
        else:
            print("Je hebt het gehaald! Probeer het volgende keer sneller!")

        print("\nBedankt voor het spelen!")
        input("\nDruk op Enter om terug te gaan...")

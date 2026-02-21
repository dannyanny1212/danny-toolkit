"""
Music Composer v1.0 - Genereer melodieën, akkoorden en drumpatronen.
ASCII-gebaseerde muziek compositie tool.
"""

import json
import logging
import random
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from ..core.config import Config
from ..core.utils import clear_scherm

logger = logging.getLogger(__name__)


class MuziekTheorie:
    """Muziektheorie constanten en hulpfuncties."""

    # Noten
    NOTEN = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

    # Toonladders (intervallen vanaf grondtoon)
    TOONLADDERS = {
        "majeur": [0, 2, 4, 5, 7, 9, 11],
        "mineur": [0, 2, 3, 5, 7, 8, 10],
        "blues": [0, 3, 5, 6, 7, 10],
        "pentatonisch": [0, 2, 4, 7, 9],
        "harmonisch_mineur": [0, 2, 3, 5, 7, 8, 11],
        "dorisch": [0, 2, 3, 5, 7, 9, 10],
        "mixolydisch": [0, 2, 4, 5, 7, 9, 10],
    }

    # Akkoord types (intervallen)
    AKKOORDEN = {
        "maj": [0, 4, 7],
        "min": [0, 3, 7],
        "7": [0, 4, 7, 10],
        "maj7": [0, 4, 7, 11],
        "min7": [0, 3, 7, 10],
        "dim": [0, 3, 6],
        "aug": [0, 4, 8],
        "sus4": [0, 5, 7],
        "sus2": [0, 2, 7],
    }

    # Akkoord progressies
    PROGRESSIES = {
        "pop": ["I", "V", "vi", "IV"],
        "blues": ["I", "I", "I", "I", "IV", "IV", "I", "I", "V", "IV", "I", "V"],
        "jazz": ["ii", "V", "I", "I"],
        "rock": ["I", "IV", "V", "I"],
        "triest": ["i", "VI", "III", "VII"],
        "episch": ["I", "V", "vi", "iii", "IV", "I", "IV", "V"],
    }

    # Drum patronen (16 stappen, 1=hit, 0=rust)
    DRUM_PATRONEN = {
        "basic_rock": {
            "kick":  [1,0,0,0, 1,0,0,0, 1,0,0,0, 1,0,0,0],
            "snare": [0,0,0,0, 1,0,0,0, 0,0,0,0, 1,0,0,0],
            "hihat": [1,0,1,0, 1,0,1,0, 1,0,1,0, 1,0,1,0],
        },
        "disco": {
            "kick":  [1,0,0,0, 1,0,0,0, 1,0,0,0, 1,0,0,0],
            "snare": [0,0,0,0, 1,0,0,0, 0,0,0,0, 1,0,0,0],
            "hihat": [1,1,1,1, 1,1,1,1, 1,1,1,1, 1,1,1,1],
        },
        "hiphop": {
            "kick":  [1,0,0,1, 0,0,1,0, 0,1,0,0, 1,0,0,0],
            "snare": [0,0,0,0, 1,0,0,0, 0,0,0,0, 1,0,0,1],
            "hihat": [1,0,1,0, 1,0,1,0, 1,0,1,0, 1,0,1,0],
        },
        "jazz": {
            "kick":  [1,0,0,0, 0,0,1,0, 0,0,0,0, 1,0,0,0],
            "snare": [0,0,0,0, 0,0,0,0, 0,0,1,0, 0,0,0,0],
            "hihat": [1,0,1,1, 1,0,1,1, 1,0,1,1, 1,0,1,1],
        },
        "latin": {
            "kick":  [1,0,0,1, 0,0,1,0, 1,0,0,1, 0,0,1,0],
            "snare": [0,0,1,0, 0,1,0,0, 0,0,1,0, 0,1,0,0],
            "hihat": [1,1,1,1, 1,1,1,1, 1,1,1,1, 1,1,1,1],
        },
    }

    @classmethod
    def get_noot_index(cls, noot: str) -> int:
        """Haal index van noot."""
        noot = noot.upper().replace("♯", "#").replace("♭", "b")
        # Converteer flats naar sharps
        if "B" in noot and len(noot) > 1:
            idx = cls.NOTEN.index(noot[0])
            return (idx - 1) % 12
        return cls.NOTEN.index(noot)

    @classmethod
    def get_toonladder(cls, grondtoon: str, type_: str = "majeur") -> List[str]:
        """Genereer toonladder."""
        start = cls.get_noot_index(grondtoon)
        intervallen = cls.TOONLADDERS.get(type_, cls.TOONLADDERS["majeur"])
        return [cls.NOTEN[(start + i) % 12] for i in intervallen]

    @classmethod
    def get_akkoord(cls, grondtoon: str, type_: str = "maj") -> List[str]:
        """Genereer akkoord noten."""
        start = cls.get_noot_index(grondtoon)
        intervallen = cls.AKKOORDEN.get(type_, cls.AKKOORDEN["maj"])
        return [cls.NOTEN[(start + i) % 12] for i in intervallen]


class MelodieGenerator:
    """Genereer melodieën."""

    def __init__(self, toonladder: List[str]):
        self.toonladder = toonladder

    def genereer(self, lengte: int = 8, stijl: str = "random") -> List[str]:
        """Genereer een melodie."""
        if stijl == "stap":
            return self._stap_melodie(lengte)
        elif stijl == "sprong":
            return self._sprong_melodie(lengte)
        elif stijl == "arpeggio":
            return self._arpeggio_melodie(lengte)
        else:
            return self._random_melodie(lengte)

    def _random_melodie(self, lengte: int) -> List[str]:
        """Volledig willekeurige melodie."""
        return [random.choice(self.toonladder) for _ in range(lengte)]

    def _stap_melodie(self, lengte: int) -> List[str]:
        """Melodie met kleine stappen."""
        melodie = [random.choice(self.toonladder)]
        idx = self.toonladder.index(melodie[0])

        for _ in range(lengte - 1):
            stap = random.choice([-1, 0, 1])
            idx = max(0, min(len(self.toonladder) - 1, idx + stap))
            melodie.append(self.toonladder[idx])

        return melodie

    def _sprong_melodie(self, lengte: int) -> List[str]:
        """Melodie met grotere sprongen."""
        melodie = [random.choice(self.toonladder)]
        idx = self.toonladder.index(melodie[0])

        for _ in range(lengte - 1):
            sprong = random.choice([-3, -2, 2, 3])
            idx = (idx + sprong) % len(self.toonladder)
            melodie.append(self.toonladder[idx])

        return melodie

    def _arpeggio_melodie(self, lengte: int) -> List[str]:
        """Arpeggio-gebaseerde melodie."""
        # Gebruik 1e, 3e, 5e noot van toonladder
        arpeggio = [self.toonladder[0], self.toonladder[2], self.toonladder[4]]
        melodie = []

        for i in range(lengte):
            melodie.append(arpeggio[i % len(arpeggio)])

        return melodie


class MusicComposerApp:
    """Music Composer - Genereer muziek in ASCII."""

    VERSIE = "1.0"

    def __init__(self):
        Config.ensure_dirs()
        self.data_dir = Config.APPS_DATA_DIR / "music_composer"
        self.data_dir.mkdir(exist_ok=True)
        self.composities_file = self.data_dir / "composities.json"
        self.composities = self._laad_composities()

    def _laad_composities(self) -> List[Dict]:
        """Laad opgeslagen composities."""
        if self.composities_file.exists():
            try:
                with open(self.composities_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.debug("Composities load error: %s", e)
        return []

    def _sla_op(self):
        """Sla composities op."""
        with open(self.composities_file, "w", encoding="utf-8") as f:
            json.dump(self.composities, f, indent=2, ensure_ascii=False)

    def _teken_piano_roll(self, melodie: List[str], toonladder: List[str]):
        """Teken melodie als piano roll."""
        print("\n  PIANO ROLL:")
        print("  " + "-" * (len(melodie) * 4 + 10))

        for noot in reversed(toonladder):
            lijn = f"  {noot:3} |"
            for m in melodie:
                if m == noot:
                    lijn += " ## "
                else:
                    lijn += " -- "
            lijn += "|"
            print(lijn)

        print("  " + "-" * (len(melodie) * 4 + 10))
        # Beat nummers
        beats = "      "
        for i in range(len(melodie)):
            beats += f" {i+1:2} "
        print(beats)

    def _teken_drum_patroon(self, patroon: Dict[str, List[int]]):
        """Teken drum patroon."""
        print("\n  DRUM PATROON (16 stappen):")
        print("  " + "-" * 70)

        symbolen = {"kick": "K", "snare": "S", "hihat": "H"}

        for naam, hits in patroon.items():
            symbool = symbolen.get(naam, naam[0].upper())
            lijn = f"  {naam:6} |"
            for i, hit in enumerate(hits):
                if i % 4 == 0 and i > 0:
                    lijn += "|"
                if hit:
                    lijn += f" {symbool} "
                else:
                    lijn += " . "
            lijn += "|"
            print(lijn)

        print("  " + "-" * 70)
        print("         | 1  2  3  4 | 5  6  7  8 | 9 10 11 12 |13 14 15 16 |")

    def _teken_akkoord(self, noten: List[str], naam: str):
        """Teken akkoord als ASCII."""
        print(f"\n  {naam}:")
        print("  +" + "-" * 20 + "+")
        for noot in noten:
            print(f"  | {noot:3} {'#' * 15} |")
        print("  +" + "-" * 20 + "+")

    def _genereer_melodie(self):
        """Genereer een nieuwe melodie."""
        clear_scherm()
        print("\n  === MELODIE GENERATOR ===\n")

        # Kies grondtoon
        print("  Beschikbare noten:", ", ".join(MuziekTheorie.NOTEN))
        grondtoon = input("  Grondtoon (bijv. C): ").strip().upper() or "C"

        # Kies toonladder
        print("\n  Toonladders:", ", ".join(MuziekTheorie.TOONLADDERS.keys()))
        ladder = input("  Toonladder (bijv. majeur): ").strip().lower() or "majeur"

        # Kies stijl
        print("\n  Stijlen: random, stap, sprong, arpeggio")
        stijl = input("  Stijl: ").strip().lower() or "random"

        # Kies lengte
        try:
            lengte = int(input("  Lengte (4-16): ").strip() or "8")
            lengte = max(4, min(16, lengte))
        except ValueError:
            lengte = 8

        # Genereer
        toonladder = MuziekTheorie.get_toonladder(grondtoon, ladder)
        generator = MelodieGenerator(toonladder)
        melodie = generator.genereer(lengte, stijl)

        print(f"\n  Toonladder {grondtoon} {ladder}: {', '.join(toonladder)}")
        print(f"  Melodie: {' - '.join(melodie)}")

        self._teken_piano_roll(melodie, toonladder)

        # Opslaan?
        if input("\n  Opslaan? (j/n): ").lower() == "j":
            naam = input("  Naam: ").strip() or f"Melodie {len(self.composities) + 1}"
            self.composities.append({
                "type": "melodie",
                "naam": naam,
                "grondtoon": grondtoon,
                "toonladder": ladder,
                "noten": melodie,
                "datum": datetime.now().isoformat()
            })
            self._sla_op()
            print("  Opgeslagen!")

        input("\n  Druk op Enter...")

    def _genereer_akkoorden(self):
        """Genereer akkoord progressie."""
        clear_scherm()
        print("\n  === AKKOORD PROGRESSIE ===\n")

        # Kies grondtoon
        grondtoon = input("  Grondtoon (bijv. C): ").strip().upper() or "C"

        # Kies progressie
        print("\n  Progressies:", ", ".join(MuziekTheorie.PROGRESSIES.keys()))
        prog_type = input("  Progressie: ").strip().lower() or "pop"

        progressie = MuziekTheorie.PROGRESSIES.get(prog_type, ["I", "IV", "V", "I"])

        # Bepaal akkoorden
        toonladder = MuziekTheorie.get_toonladder(grondtoon, "majeur")
        akkoord_map = {
            "I": (toonladder[0], "maj"),
            "ii": (toonladder[1], "min"),
            "iii": (toonladder[2], "min"),
            "IV": (toonladder[3], "maj"),
            "V": (toonladder[4], "maj"),
            "vi": (toonladder[5], "min"),
            "VII": (toonladder[6], "dim"),
            "i": (toonladder[0], "min"),
            "III": (toonladder[2], "maj"),
            "VI": (toonladder[5], "maj"),
        }

        print(f"\n  Progressie in {grondtoon}: {' - '.join(progressie)}\n")

        for symbool in progressie:
            if symbool in akkoord_map:
                noot, type_ = akkoord_map[symbool]
                akkoord_noten = MuziekTheorie.get_akkoord(noot, type_)
                naam = f"{noot}{type_}"
                self._teken_akkoord(akkoord_noten, naam)

        # Opslaan?
        if input("\n  Opslaan? (j/n): ").lower() == "j":
            naam = input("  Naam: ").strip() or f"Progressie {len(self.composities) + 1}"
            self.composities.append({
                "type": "progressie",
                "naam": naam,
                "grondtoon": grondtoon,
                "progressie": progressie,
                "datum": datetime.now().isoformat()
            })
            self._sla_op()
            print("  Opgeslagen!")

        input("\n  Druk op Enter...")

    def _genereer_drums(self):
        """Genereer drum patroon."""
        clear_scherm()
        print("\n  === DRUM PATROON GENERATOR ===\n")

        # Kies patroon of random
        print("  Patronen:", ", ".join(MuziekTheorie.DRUM_PATRONEN.keys()))
        print("  (of 'random' voor willekeurig)")

        keuze = input("\n  Keuze: ").strip().lower() or "basic_rock"

        if keuze == "random":
            patroon = {
                "kick": [random.choice([0, 1]) for _ in range(16)],
                "snare": [random.choice([0, 1]) for _ in range(16)],
                "hihat": [random.choice([0, 1]) for _ in range(16)],
            }
            # Zorg voor minimaal wat hits
            patroon["kick"][0] = 1
            patroon["snare"][4] = 1
            patroon["snare"][12] = 1
        else:
            patroon = MuziekTheorie.DRUM_PATRONEN.get(
                keuze, MuziekTheorie.DRUM_PATRONEN["basic_rock"]
            )

        self._teken_drum_patroon(patroon)

        # Speel simulatie
        print("\n  Simulatie (tekst):")
        for i in range(16):
            sounds = []
            if patroon["kick"][i]:
                sounds.append("BOOM")
            if patroon["snare"][i]:
                sounds.append("CLAP")
            if patroon["hihat"][i]:
                sounds.append("tss")
            if sounds:
                print(f"    {i+1:2}: {' + '.join(sounds)}")
            else:
                print(f"    {i+1:2}: ...")

        # Opslaan?
        if input("\n  Opslaan? (j/n): ").lower() == "j":
            naam = input("  Naam: ").strip() or f"Drums {len(self.composities) + 1}"
            self.composities.append({
                "type": "drums",
                "naam": naam,
                "patroon": patroon,
                "datum": datetime.now().isoformat()
            })
            self._sla_op()
            print("  Opgeslagen!")

        input("\n  Druk op Enter...")

    def _bekijk_composities(self):
        """Bekijk opgeslagen composities."""
        clear_scherm()
        print("\n  === OPGESLAGEN COMPOSITIES ===\n")

        if not self.composities:
            print("  Geen composities opgeslagen.")
            input("\n  Druk op Enter...")
            return

        for i, comp in enumerate(self.composities, 1):
            print(f"  {i}. [{comp['type']}] {comp['naam']}")
            print(f"     Datum: {comp['datum'][:10]}")

        keuze = input("\n  Bekijk # (of Enter voor terug): ").strip()
        if keuze.isdigit():
            idx = int(keuze) - 1
            if 0 <= idx < len(self.composities):
                comp = self.composities[idx]
                clear_scherm()
                print(f"\n  === {comp['naam']} ===\n")

                if comp["type"] == "melodie":
                    toonladder = MuziekTheorie.get_toonladder(
                        comp["grondtoon"], comp["toonladder"]
                    )
                    print(f"  Noten: {' - '.join(comp['noten'])}")
                    self._teken_piano_roll(comp["noten"], toonladder)

                elif comp["type"] == "drums":
                    self._teken_drum_patroon(comp["patroon"])

                elif comp["type"] == "progressie":
                    print(f"  Grondtoon: {comp['grondtoon']}")
                    print(f"  Progressie: {' - '.join(comp['progressie'])}")

                input("\n  Druk op Enter...")

    def _toonladder_referentie(self):
        """Toon toonladder referentie."""
        clear_scherm()
        print("\n  === TOONLADDER REFERENTIE ===\n")

        grondtoon = input("  Grondtoon (bijv. C): ").strip().upper() or "C"

        print(f"\n  Toonladders in {grondtoon}:\n")

        for naam, _ in MuziekTheorie.TOONLADDERS.items():
            ladder = MuziekTheorie.get_toonladder(grondtoon, naam)
            print(f"  {naam:20}: {' - '.join(ladder)}")

        print(f"\n  Akkoorden op {grondtoon}:\n")

        for type_, _ in MuziekTheorie.AKKOORDEN.items():
            noten = MuziekTheorie.get_akkoord(grondtoon, type_)
            print(f"  {grondtoon}{type_:6}: {' - '.join(noten)}")

        input("\n  Druk op Enter...")

    def run(self):
        """Start de app."""
        while True:
            clear_scherm()
            print("""
  ╔═══════════════════════════════════════════════════════════╗
  ║              MUSIC COMPOSER v1.0                          ║
  ║          Genereer Melodieen, Akkoorden & Drums            ║
  ╠═══════════════════════════════════════════════════════════╣
  ║  1. Genereer Melodie                                      ║
  ║  2. Genereer Akkoord Progressie                           ║
  ║  3. Genereer Drum Patroon                                 ║
  ║  4. Bekijk Opgeslagen Composities                         ║
  ║  5. Toonladder Referentie                                 ║
  ║  0. Terug                                                 ║
  ╚═══════════════════════════════════════════════════════════╝
""")
            print(f"  Opgeslagen: {len(self.composities)} composities")

            keuze = input("\n  Keuze: ").strip()

            if keuze == "0":
                break
            elif keuze == "1":
                self._genereer_melodie()
            elif keuze == "2":
                self._genereer_akkoorden()
            elif keuze == "3":
                self._genereer_drums()
            elif keuze == "4":
                self._bekijk_composities()
            elif keuze == "5":
                self._toonladder_referentie()

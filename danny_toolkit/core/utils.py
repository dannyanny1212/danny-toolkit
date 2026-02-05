"""
Gedeelde hulpfuncties voor Danny Toolkit.
Versie 2.0 - Met kleuren, progress bar, tabel formatter en logging.
"""

import os
import sys
import time
import logging
import subprocess
from datetime import datetime
from pathlib import Path
from typing import List, Optional


# =============================================================================
# KLEUREN
# =============================================================================

class Kleur:
    """ANSI kleurcodes voor terminal output."""

    # Reset
    RESET = "\033[0m"

    # Standaard kleuren
    ZWART = "\033[30m"
    ROOD = "\033[31m"
    GROEN = "\033[32m"
    GEEL = "\033[33m"
    BLAUW = "\033[34m"
    MAGENTA = "\033[35m"
    CYAAN = "\033[36m"
    WIT = "\033[37m"

    # Felle kleuren
    FEL_ZWART = "\033[90m"
    FEL_ROOD = "\033[91m"
    FEL_GROEN = "\033[92m"
    FEL_GEEL = "\033[93m"
    FEL_BLAUW = "\033[94m"
    FEL_MAGENTA = "\033[95m"
    FEL_CYAAN = "\033[96m"
    FEL_WIT = "\033[97m"

    # Achtergrond kleuren
    BG_ZWART = "\033[40m"
    BG_ROOD = "\033[41m"
    BG_GROEN = "\033[42m"
    BG_GEEL = "\033[43m"
    BG_BLAUW = "\033[44m"
    BG_MAGENTA = "\033[45m"
    BG_CYAAN = "\033[46m"
    BG_WIT = "\033[47m"

    # Stijlen
    VET = "\033[1m"
    DIM = "\033[2m"
    CURSIEF = "\033[3m"
    ONDERSTREEPT = "\033[4m"

    _enabled = True

    @classmethod
    def aan(cls):
        """Zet kleuren aan."""
        cls._enabled = True

    @classmethod
    def uit(cls):
        """Zet kleuren uit."""
        cls._enabled = False

    @classmethod
    def is_aan(cls) -> bool:
        """Check of kleuren aan staan."""
        return cls._enabled


def kleur(tekst: str, kleur_code: str) -> str:
    """Voeg kleur toe aan tekst."""
    if not Kleur._enabled:
        return tekst
    return f"{kleur_code}{tekst}{Kleur.RESET}"


def succes(tekst: str) -> str:
    """Groene tekst voor succes berichten."""
    return kleur(tekst, Kleur.FEL_GROEN)


def fout(tekst: str) -> str:
    """Rode tekst voor fout berichten."""
    return kleur(tekst, Kleur.FEL_ROOD)


def waarschuwing(tekst: str) -> str:
    """Gele tekst voor waarschuwingen."""
    return kleur(tekst, Kleur.FEL_GEEL)


def info(tekst: str) -> str:
    """Cyaan tekst voor info berichten."""
    return kleur(tekst, Kleur.FEL_CYAAN)


def vet(tekst: str) -> str:
    """Vette tekst."""
    return kleur(tekst, Kleur.VET)


def dim(tekst: str) -> str:
    """Gedimde tekst."""
    return kleur(tekst, Kleur.DIM)


# =============================================================================
# PROGRESS BAR
# =============================================================================

class ProgressBar:
    """Visuele voortgangsbalk voor de terminal."""

    def __init__(self, totaal: int, breedte: int = 40, prefix: str = "",
                 suffix: str = "", vulling: str = "█", leeg: str = "░"):
        """
        Initialiseer progress bar.

        Args:
            totaal: Totaal aantal stappen
            breedte: Breedte van de balk in karakters
            prefix: Tekst voor de balk
            suffix: Tekst na de balk
            vulling: Karakter voor voltooide deel
            leeg: Karakter voor onvoltooide deel
        """
        self.totaal = max(1, totaal)
        self.breedte = breedte
        self.prefix = prefix
        self.suffix = suffix
        self.vulling = vulling
        self.leeg = leeg
        self.huidig = 0
        self.start_tijd = time.time()

    def update(self, huidig: int = None):
        """Update de progress bar."""
        if huidig is not None:
            self.huidig = huidig
        else:
            self.huidig += 1

        percentage = self.huidig / self.totaal
        gevuld = int(self.breedte * percentage)
        balk = self.vulling * gevuld + self.leeg * (self.breedte - gevuld)

        # Bereken tijd
        verstreken = time.time() - self.start_tijd
        if self.huidig > 0:
            geschat_totaal = verstreken / percentage
            resterend = geschat_totaal - verstreken
            tijd_str = self._format_tijd(resterend)
        else:
            tijd_str = "--:--"

        # Print de balk
        print(f"\r{self.prefix} |{balk}| {percentage*100:.1f}% "
              f"[{self.huidig}/{self.totaal}] {tijd_str} {self.suffix}",
              end="", flush=True)

        if self.huidig >= self.totaal:
            print()  # Nieuwe regel aan het eind

    def _format_tijd(self, seconden: float) -> str:
        """Format tijd als MM:SS."""
        if seconden < 0:
            return "00:00"
        minuten = int(seconden // 60)
        secs = int(seconden % 60)
        return f"{minuten:02d}:{secs:02d}"

    def finish(self):
        """Markeer als voltooid."""
        self.update(self.totaal)


class Spinner:
    """Draaiende animatie voor onbepaalde taken."""

    FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    FRAMES_SIMPLE = ["|", "/", "-", "\\"]

    def __init__(self, bericht: str = "Laden...", gebruik_unicode: bool = True):
        """
        Initialiseer spinner.

        Args:
            bericht: Bericht om te tonen
            gebruik_unicode: Gebruik unicode frames (False voor simpele)
        """
        self.bericht = bericht
        self.frames = self.FRAMES if gebruik_unicode else self.FRAMES_SIMPLE
        self.frame_idx = 0
        self.actief = False

    def spin(self):
        """Toon volgende frame."""
        frame = self.frames[self.frame_idx % len(self.frames)]
        print(f"\r{frame} {self.bericht}", end="", flush=True)
        self.frame_idx += 1

    def stop(self, succes_bericht: str = None):
        """Stop de spinner."""
        if succes_bericht:
            print(f"\r✓ {succes_bericht}          ")
        else:
            print("\r" + " " * (len(self.bericht) + 5) + "\r", end="")


# =============================================================================
# TABEL FORMATTER
# =============================================================================

class TabelFormatter:
    """Formatteert data als ASCII tabellen."""

    def __init__(self, headers: List[str], uitlijning: List[str] = None):
        """
        Initialiseer tabel formatter.

        Args:
            headers: Kolomkoppen
            uitlijning: Uitlijning per kolom ('l', 'c', 'r')
        """
        self.headers = headers
        self.uitlijning = uitlijning or ["l"] * len(headers)
        self.rijen = []
        self.kolom_breedtes = [len(h) for h in headers]

    def voeg_rij_toe(self, *waarden):
        """Voeg een rij toe aan de tabel."""
        rij = [str(w) for w in waarden]
        # Pad met lege strings als nodig
        while len(rij) < len(self.headers):
            rij.append("")
        rij = rij[:len(self.headers)]  # Limiteer tot aantal headers

        self.rijen.append(rij)

        # Update kolom breedtes
        for i, waarde in enumerate(rij):
            self.kolom_breedtes[i] = max(self.kolom_breedtes[i], len(waarde))

    def _lijn_rij(self, rij: List[str]) -> str:
        """Format een enkele rij met uitlijning."""
        cellen = []
        for i, waarde in enumerate(rij):
            breedte = self.kolom_breedtes[i]
            uitlijn = self.uitlijning[i] if i < len(self.uitlijning) else "l"

            if uitlijn == "c":
                cellen.append(waarde.center(breedte))
            elif uitlijn == "r":
                cellen.append(waarde.rjust(breedte))
            else:
                cellen.append(waarde.ljust(breedte))

        return "│ " + " │ ".join(cellen) + " │"

    def _horizontale_lijn(self, positie: str = "midden") -> str:
        """Maak een horizontale lijn."""
        if positie == "boven":
            links, kruis, rechts = "┌", "┬", "┐"
        elif positie == "onder":
            links, kruis, rechts = "└", "┴", "┘"
        else:
            links, kruis, rechts = "├", "┼", "┤"

        segmenten = ["─" * (b + 2) for b in self.kolom_breedtes]
        return links + kruis.join(segmenten) + rechts

    def render(self) -> str:
        """Render de tabel als string."""
        lijnen = []

        # Bovenlijn
        lijnen.append(self._horizontale_lijn("boven"))

        # Headers
        lijnen.append(self._lijn_rij(self.headers))
        lijnen.append(self._horizontale_lijn("midden"))

        # Data rijen
        for rij in self.rijen:
            lijnen.append(self._lijn_rij(rij))

        # Onderlijn
        lijnen.append(self._horizontale_lijn("onder"))

        return "\n".join(lijnen)

    def print(self):
        """Print de tabel naar stdout."""
        print(self.render())

    def wis(self):
        """Wis alle rijen."""
        self.rijen = []
        self.kolom_breedtes = [len(h) for h in self.headers]


def simpele_tabel(headers: List[str], rijen: List[List], uitlijning: List[str] = None) -> str:
    """
    Snelle functie om een tabel te maken.

    Args:
        headers: Kolomkoppen
        rijen: Lijst van rijen (elk een lijst van waarden)
        uitlijning: Optionele uitlijning per kolom

    Returns:
        Geformatteerde tabel als string
    """
    formatter = TabelFormatter(headers, uitlijning)
    for rij in rijen:
        formatter.voeg_rij_toe(*rij)
    return formatter.render()


# =============================================================================
# LOGGING
# =============================================================================

class ToolkitLogger:
    """Centrale logger voor de toolkit."""

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if ToolkitLogger._initialized:
            return

        self.logger = logging.getLogger("danny_toolkit")
        self.logger.setLevel(logging.DEBUG)

        # Console handler (alleen INFO en hoger)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_format = logging.Formatter(
            "%(levelname)s: %(message)s"
        )
        console_handler.setFormatter(console_format)
        self.logger.addHandler(console_handler)

        # File handler wordt later toegevoegd als log_dir bekend is
        self._file_handler = None

        ToolkitLogger._initialized = True

    def setup_bestand(self, log_dir: Path):
        """Setup file logging."""
        if self._file_handler:
            return

        log_dir.mkdir(parents=True, exist_ok=True)
        log_bestand = log_dir / f"toolkit_{datetime.now():%Y%m%d}.log"

        self._file_handler = logging.FileHandler(
            log_bestand, encoding="utf-8"
        )
        self._file_handler.setLevel(logging.DEBUG)
        file_format = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        self._file_handler.setFormatter(file_format)
        self.logger.addHandler(self._file_handler)

    def debug(self, bericht: str):
        """Log debug bericht."""
        self.logger.debug(bericht)

    def info(self, bericht: str):
        """Log info bericht."""
        self.logger.info(bericht)

    def waarschuwing(self, bericht: str):
        """Log waarschuwing."""
        self.logger.warning(bericht)

    def fout(self, bericht: str):
        """Log fout."""
        self.logger.error(bericht)

    def kritiek(self, bericht: str):
        """Log kritieke fout."""
        self.logger.critical(bericht)

    def exceptie(self, bericht: str):
        """Log exceptie met traceback."""
        self.logger.exception(bericht)


# Globale logger instance
_logger = None


def get_logger() -> ToolkitLogger:
    """Verkrijg de globale logger."""
    global _logger
    if _logger is None:
        _logger = ToolkitLogger()
    return _logger


def log_debug(bericht: str):
    """Snelle debug log."""
    get_logger().debug(bericht)


def log_info(bericht: str):
    """Snelle info log."""
    get_logger().info(bericht)


def log_waarschuwing(bericht: str):
    """Snelle waarschuwing log."""
    get_logger().waarschuwing(bericht)


def log_fout(bericht: str):
    """Snelle fout log."""
    get_logger().fout(bericht)


# =============================================================================
# BESTAANDE FUNCTIES (VERBETERD)
# =============================================================================

def fix_encoding():
    """Fix Windows encoding voor emoji's en speciale tekens."""
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except AttributeError:
            pass  # Python < 3.7


def clear_scherm():
    """Maakt het scherm leeg."""
    if os.name == "nt":
        subprocess.run(["cmd", "/c", "cls"], shell=False)
    else:
        subprocess.run(["clear"], shell=False)


def toon_banner(titel: str, emoji: str = "", breedte: int = 60,
                kleur_code: str = None):
    """Toont een mooie banner."""
    if kleur_code and Kleur._enabled:
        titel = kleur(titel, kleur_code)

    if emoji:
        lijn = f"{emoji} " * (breedte // 3)
        print(f"\n{lijn}")
        print(f"   {titel}")
        print(f"{lijn}")
    else:
        print("\n" + "=" * breedte)
        print(f"   {titel}")
        print("=" * breedte)


def vraag_bevestiging(vraag: str, standaard: bool = None) -> bool:
    """
    Vraagt om bevestiging (j/n).

    Args:
        vraag: De vraag om te stellen
        standaard: Default waarde als Enter wordt gedrukt (None = geen default)

    Returns:
        True of False
    """
    opties = "(j/n)"
    if standaard is True:
        opties = "(J/n)"
    elif standaard is False:
        opties = "(j/N)"

    while True:
        antwoord = input(f"{vraag} {opties}: ").lower().strip()

        if antwoord == "":
            if standaard is not None:
                return standaard
            continue

        if antwoord in ("j", "ja", "y", "yes"):
            return True
        if antwoord in ("n", "nee", "no"):
            return False

        print("Voer 'j' of 'n' in.")


def druk_enter(bericht: str = None):
    """Wacht op Enter toets."""
    bericht = bericht or "Druk op Enter om verder te gaan..."
    input(f"\n{bericht}")


def kies_uit_lijst(opties: List[str], titel: str = "Kies een optie:",
                   terug_optie: bool = True) -> int:
    """
    Laat gebruiker kiezen uit een lijst.

    Args:
        opties: Lijst van opties
        titel: Titel boven de opties
        terug_optie: Voeg '0. Terug' toe

    Returns:
        Index van gekozen optie (-1 voor terug/annuleren)
    """
    print(f"\n{titel}")
    for i, optie in enumerate(opties, 1):
        print(f"  {i}. {optie}")
    if terug_optie:
        print("  0. Terug")

    while True:
        try:
            keuze = input("\nKeuze: ").strip()
            if keuze == "":
                continue

            idx = int(keuze)
            if terug_optie and idx == 0:
                return -1
            if 1 <= idx <= len(opties):
                return idx - 1

            print(f"Kies een nummer tussen 1 en {len(opties)}")
        except ValueError:
            print("Voer een nummer in.")


def truncate(tekst: str, max_lengte: int, suffix: str = "...") -> str:
    """
    Kort tekst in als deze te lang is.

    Args:
        tekst: De tekst om in te korten
        max_lengte: Maximale lengte
        suffix: Suffix om toe te voegen als tekst wordt ingekort

    Returns:
        Ingekorte tekst
    """
    if len(tekst) <= max_lengte:
        return tekst
    return tekst[:max_lengte - len(suffix)] + suffix


def format_bytes(bytes_: int) -> str:
    """Format bytes als leesbare string."""
    for eenheid in ["B", "KB", "MB", "GB", "TB"]:
        if abs(bytes_) < 1024.0:
            return f"{bytes_:.1f} {eenheid}"
        bytes_ /= 1024.0
    return f"{bytes_:.1f} PB"


def format_duur(seconden: float) -> str:
    """Format duur in seconden als leesbare string."""
    if seconden < 60:
        return f"{seconden:.1f}s"
    elif seconden < 3600:
        minuten = int(seconden // 60)
        secs = int(seconden % 60)
        return f"{minuten}m {secs}s"
    else:
        uren = int(seconden // 3600)
        minuten = int((seconden % 3600) // 60)
        return f"{uren}u {minuten}m"

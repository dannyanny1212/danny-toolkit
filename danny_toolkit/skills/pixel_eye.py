"""
PixelEye — Het Oog van Project Omega.

Standalone vision skill via Ollama LLaVA.
Analyseert afbeeldingen, screenshots, vergelijkt
beelden — alles lokaal zonder API rate limits.
"""

import logging
import os
import time
from pathlib import Path

logger = logging.getLogger(__name__)

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# ─── Config import (root config.py) ───
import sys

_root = Path(__file__).parent.parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from config import VISION_MODEL, GOLDEN_DIR

# ─── Constanten ───

console = Console()


class PixelEye:
    """Het Oog — Vision analyse via Ollama LLaVA.

    Gebruikt het lokale LLaVA model voor beeld-analyse.
    Geen API rate limits, geen cloud dependency.

    Gebruik:
        eye = PixelEye()
        result = eye.analyze_image("pad/naar/foto.png")
        print(result["analyse"])
    """

    def __init__(self, model=None):
        self.model = model or VISION_MODEL
        self._analyses = 0
        self._totale_tijd = 0.0
        self._ollama = None

        # Check Ollama beschikbaarheid
        try:
            import ollama
            self._ollama = ollama
        except ImportError:
            console.print(
                "[red]Fout: ollama package niet"
                " geinstalleerd.[/red]\n"
                "[dim]pip install ollama[/dim]"
            )

    # ─── Kern: Vision Call ───

    def _vision_call(self, image_path, prompt):
        """Stuur een afbeelding naar Ollama LLaVA.

        Args:
            image_path: Pad naar afbeeldingsbestand.
            prompt: Instructie voor het model.

        Returns:
            Antwoord van het model (str).

        Raises:
            RuntimeError: Als Ollama niet beschikbaar is.
            FileNotFoundError: Als het bestand niet bestaat.
        """
        if not self._ollama:
            raise RuntimeError(
                "Ollama niet beschikbaar."
                " Installeer met: pip install ollama"
            )

        pad = Path(image_path)
        if not pad.exists():
            raise FileNotFoundError(
                f"Bestand niet gevonden: {image_path}"
            )

        response = self._ollama.chat(
            model=self.model,
            messages=[{
                "role": "user",
                "content": prompt,
                "images": [str(pad)],
            }],
        )
        return response.message.content

    # ─── Publieke API ───

    def analyze_image(self, pad, vraag=None):
        """Analyseer een afbeelding.

        Args:
            pad: Pad naar het afbeeldingsbestand.
            vraag: Optionele specifieke vraag.

        Returns:
            dict met analyse, model, tijd, pad.
        """
        if vraag:
            prompt = (
                f"{vraag}\n"
                "Antwoord in het Nederlands."
            )
        else:
            prompt = (
                "Analyseer dit beeld in detail."
                " Beschrijf wat je ziet."
                " Als je tekst ziet, lees die"
                " letterlijk voor."
                " Antwoord in het Nederlands."
            )

        start = time.time()
        try:
            analyse = self._vision_call(
                pad, prompt
            )
        except Exception as e:
            console.print(
                f"[red]Vision fout: {e}[/red]"
            )
            return {
                "analyse": None,
                "fout": str(e),
                "model": self.model,
                "tijd": time.time() - start,
                "pad": str(pad),
            }

        elapsed = time.time() - start
        self._analyses += 1
        self._totale_tijd += elapsed

        console.print(
            f"[green]Analyse klaar[/green]"
            f" [dim]({elapsed:.1f}s,"
            f" {self.model})[/dim]"
        )

        return {
            "analyse": analyse,
            "model": self.model,
            "tijd": elapsed,
            "pad": str(pad),
        }

    def analyze_screen(self, vraag=None):
        """Maak screenshot en analyseer.

        Args:
            vraag: Optionele specifieke vraag.

        Returns:
            dict met analyse, model, tijd, pad.
        """
        try:
            import pyautogui
        except ImportError:
            console.print(
                "[red]Fout: pyautogui niet"
                " geinstalleerd.[/red]\n"
                "[dim]pip install pyautogui[/dim]"
            )
            return {
                "analyse": None,
                "fout": "pyautogui niet beschikbaar",
                "model": self.model,
                "tijd": 0,
                "pad": None,
            }

        # Screenshot opslaan
        screenshot_dir = _root / "data"
        os.makedirs(str(screenshot_dir), exist_ok=True)
        screenshot_path = str(
            screenshot_dir / "screenshot_pixel_eye.png"
        )

        console.print(
            "[cyan]Screenshot maken...[/cyan]"
        )
        screenshot = pyautogui.screenshot()
        screenshot.save(screenshot_path)

        return self.analyze_image(
            screenshot_path, vraag
        )

    def describe(self, pad):
        """Korte beschrijving van een afbeelding.

        Args:
            pad: Pad naar het afbeeldingsbestand.

        Returns:
            Beschrijving als string.
        """
        prompt = (
            "Geef een korte beschrijving van dit"
            " beeld in 1-2 zinnen."
            " Antwoord in het Nederlands."
        )

        start = time.time()
        try:
            result = self._vision_call(pad, prompt)
        except Exception as e:
            console.print(
                f"[red]Vision fout: {e}[/red]"
            )
            return f"Fout: {e}"

        elapsed = time.time() - start
        self._analyses += 1
        self._totale_tijd += elapsed

        console.print(
            f"[green]Beschrijving klaar[/green]"
            f" [dim]({elapsed:.1f}s)[/dim]"
        )

        return result

    def compare(self, pad1, pad2):
        """Vergelijk twee afbeeldingen.

        Args:
            pad1: Pad naar eerste afbeelding.
            pad2: Pad naar tweede afbeelding.

        Returns:
            dict met vergelijking, model, tijd,
            pad1, pad2.
        """
        # Analyseer beide afbeeldingen apart
        prompt1 = (
            "Beschrijf dit beeld gedetailleerd."
            " Antwoord in het Nederlands."
        )
        prompt2 = prompt1

        start = time.time()
        try:
            beschrijving1 = self._vision_call(
                pad1, prompt1
            )
            beschrijving2 = self._vision_call(
                pad2, prompt2
            )
        except Exception as e:
            console.print(
                f"[red]Vision fout: {e}[/red]"
            )
            return {
                "vergelijking": None,
                "fout": str(e),
                "model": self.model,
                "tijd": time.time() - start,
                "pad1": str(pad1),
                "pad2": str(pad2),
            }

        # Vergelijk via tekst-prompt
        vergelijk_prompt = (
            "Vergelijk deze twee beschrijvingen"
            " en geef de belangrijkste"
            " verschillen en overeenkomsten:\n\n"
            f"BEELD 1:\n{beschrijving1}\n\n"
            f"BEELD 2:\n{beschrijving2}\n\n"
            "Antwoord in het Nederlands."
        )

        try:
            vergelijking = self._vision_call(
                pad1, vergelijk_prompt
            )
        except Exception as e:
            logger.debug("Vision comparison call failed, using fallback: %s", e)
            # Fallback: geef beide beschrijvingen
            vergelijking = (
                f"Beeld 1: {beschrijving1}\n\n"
                f"Beeld 2: {beschrijving2}"
            )

        elapsed = time.time() - start
        self._analyses += 2
        self._totale_tijd += elapsed

        console.print(
            f"[green]Vergelijking klaar[/green]"
            f" [dim]({elapsed:.1f}s)[/dim]"
        )

        return {
            "vergelijking": vergelijking,
            "beschrijving1": beschrijving1,
            "beschrijving2": beschrijving2,
            "model": self.model,
            "tijd": elapsed,
            "pad1": str(pad1),
            "pad2": str(pad2),
        }

    def toon_stats(self):
        """Toon vision statistieken."""
        console.print(Panel(
            "[bold magenta]PIXEL EYE STATS"
            "[/bold magenta]\n"
            "[dim]Het Oog — Vision Analyse[/dim]",
            border_style="magenta",
        ))

        stats_table = Table(
            border_style="magenta",
            show_header=False,
        )
        stats_table.add_column("label", width=25)
        stats_table.add_column("waarde")

        stats_table.add_row(
            "Vision model",
            f"[cyan]{self.model}[/cyan]",
        )
        stats_table.add_row(
            "Ollama status",
            (
                "[green]Verbonden[/green]"
                if self._ollama
                else "[red]Niet beschikbaar[/red]"
            ),
        )
        stats_table.add_row(
            "Analyses uitgevoerd",
            f"[bold green]{self._analyses}"
            f"[/bold green]",
        )

        if self._analyses > 0:
            gem = self._totale_tijd / self._analyses
            stats_table.add_row(
                "Totale tijd",
                f"[cyan]{self._totale_tijd:.1f}s"
                f"[/cyan]",
            )
            stats_table.add_row(
                "Gemiddelde tijd",
                f"[cyan]{gem:.1f}s[/cyan]",
            )

        console.print(stats_table)

    # ─── Screenshot Helper ───

    def _screenshot(self, naam):
        """Maak screenshot en sla op.

        Args:
            naam: Bestandsnaam (zonder extensie).

        Returns:
            Pad naar screenshot (str).
        """
        try:
            import pyautogui
        except ImportError:
            raise RuntimeError(
                "pyautogui niet beschikbaar."
                " Installeer met: pip install pyautogui"
            )

        screenshot_dir = _root / "data" / "screenshots"
        os.makedirs(str(screenshot_dir), exist_ok=True)
        pad = str(
            screenshot_dir / f"{naam}.png"
        )

        screenshot = pyautogui.screenshot()
        screenshot.save(pad)
        return pad

    # ─── Golden Master Management ───

    def save_golden(self, naam, pad=None):
        """Sla een screenshot op als golden master.

        Als pad=None, maak screenshot van huidig scherm.

        Args:
            naam: Naam voor de golden master.
            pad: Optioneel pad naar bestaand beeld.

        Returns:
            Pad naar golden master bestand (str).
        """
        os.makedirs(str(GOLDEN_DIR), exist_ok=True)
        doel = GOLDEN_DIR / f"{naam}.png"

        if pad:
            # Kopieer bestaand bestand
            import shutil
            shutil.copy2(str(pad), str(doel))
        else:
            # Maak screenshot
            try:
                import pyautogui
            except ImportError:
                raise RuntimeError(
                    "pyautogui niet beschikbaar."
                    " Installeer met:"
                    " pip install pyautogui"
                )
            screenshot = pyautogui.screenshot()
            screenshot.save(str(doel))

        console.print(
            f"[green]Golden master opgeslagen:"
            f"[/green] {doel}"
        )
        return str(doel)

    def compare_golden(self, naam, vraag=None):
        """Maak screenshot en vergelijk met golden master.

        Args:
            naam: Naam van de golden master.
            vraag: Optionele extra context.

        Returns:
            dict met match, analyse, golden_pad,
            huidig_pad, model, tijd.
        """
        golden_pad = GOLDEN_DIR / f"{naam}.png"
        if not golden_pad.exists():
            raise FileNotFoundError(
                f"Golden master niet gevonden:"
                f" {golden_pad}"
            )

        # Maak huidig screenshot
        huidig_pad = self._screenshot(
            f"golden_check_{naam}"
        )

        start = time.time()

        # Analyseer beide beelden
        prompt_golden = (
            "Beschrijf dit beeld gedetailleerd."
            " Antwoord in het Nederlands."
        )
        prompt_huidig = prompt_golden

        try:
            beschrijving_golden = self._vision_call(
                str(golden_pad), prompt_golden
            )
            beschrijving_huidig = self._vision_call(
                huidig_pad, prompt_huidig
            )
        except Exception as e:
            return {
                "match": None,
                "analyse": None,
                "fout": str(e),
                "golden_pad": str(golden_pad),
                "huidig_pad": huidig_pad,
                "model": self.model,
                "tijd": time.time() - start,
            }

        # Vergelijk via LLaVA
        context = (
            f" Context: {vraag}" if vraag else ""
        )
        vergelijk_prompt = (
            "Vergelijk deze twee beschrijvingen"
            " en bepaal of ze visueel overeenkomen."
            " Zijn er significante visuele"
            " afwijkingen?\n\n"
            f"REFERENTIE:\n{beschrijving_golden}\n\n"
            f"HUIDIG:\n{beschrijving_huidig}\n\n"
            f"{context}\n"
            "Begin je antwoord met MATCH of"
            " AFWIJKING."
            " Antwoord in het Nederlands."
        )

        try:
            analyse = self._vision_call(
                huidig_pad, vergelijk_prompt
            )
        except Exception as e:
            logger.debug("Golden master comparison call failed: %s", e)
            analyse = (
                f"Referentie: {beschrijving_golden}"
                f"\n\nHuidig: {beschrijving_huidig}"
            )

        elapsed = time.time() - start
        self._analyses += 2
        self._totale_tijd += elapsed

        match = analyse.strip().upper().startswith(
            "MATCH"
        )

        console.print(
            f"[{'green' if match else 'red'}]"
            f"Golden check: "
            f"{'MATCH' if match else 'AFWIJKING'}"
            f"[/{'green' if match else 'red'}]"
            f" [dim]({elapsed:.1f}s)[/dim]"
        )

        return {
            "match": match,
            "analyse": analyse,
            "golden_pad": str(golden_pad),
            "huidig_pad": huidig_pad,
            "model": self.model,
            "tijd": elapsed,
        }

    def list_goldens(self):
        """Toon alle opgeslagen golden masters.

        Returns:
            Lijst van golden master namen (list).
        """
        if not GOLDEN_DIR.exists():
            return []

        goldens = []
        for f in sorted(GOLDEN_DIR.glob("*.png")):
            goldens.append(f.stem)
        return goldens

    # ─── Visual Logic Gate ───

    def verify_action(
        self, actie_fn, beschrijving, timeout=5
    ):
        """Voer actie uit en verifieer visueel.

        1. Screenshot VOOR
        2. actie_fn() uitvoeren
        3. Wacht timeout seconden
        4. Screenshot NA
        5. LLaVA vergelijkt: is de verwachte
           verandering opgetreden?

        Args:
            actie_fn: Callable die de actie uitvoert.
            beschrijving: Wat er zou moeten veranderen.
            timeout: Wachttijd na actie (seconden).

        Returns:
            dict met geslaagd, voor_pad, na_pad,
            analyse, beschrijving, tijd.
        """
        console.print(
            f"[cyan]Screenshot VOOR actie...[/cyan]"
        )
        voor_pad = self._screenshot("verify_voor")

        console.print(
            f"[cyan]Actie uitvoeren:"
            f" {beschrijving}...[/cyan]"
        )
        actie_fn()

        console.print(
            f"[cyan]Wachten {timeout}s...[/cyan]"
        )
        time.sleep(timeout)

        console.print(
            f"[cyan]Screenshot NA actie...[/cyan]"
        )
        na_pad = self._screenshot("verify_na")

        start = time.time()

        # Analyseer beide beelden
        prompt_beeld = (
            "Beschrijf dit beeld gedetailleerd."
            " Antwoord in het Nederlands."
        )

        try:
            beschrijving_voor = self._vision_call(
                voor_pad, prompt_beeld
            )
            beschrijving_na = self._vision_call(
                na_pad, prompt_beeld
            )
        except Exception as e:
            return {
                "geslaagd": None,
                "analyse": None,
                "fout": str(e),
                "voor_pad": voor_pad,
                "na_pad": na_pad,
                "beschrijving": beschrijving,
                "model": self.model,
                "tijd": time.time() - start,
            }

        # Vergelijk voor/na
        vergelijk_prompt = (
            "Je ziet twee beschrijvingen:"
            " VOOR en NA een actie.\n"
            "De verwachte verandering was:"
            f" '{beschrijving}'.\n\n"
            f"VOOR:\n{beschrijving_voor}\n\n"
            f"NA:\n{beschrijving_na}\n\n"
            "Vraag 1: Is de verandering"
            " opgetreden? (JA/NEE)\n"
            "Vraag 2: Beschrijf wat er"
            " veranderd is.\n"
            "Begin je antwoord met JA of NEE."
            " Antwoord in het Nederlands."
        )

        try:
            analyse = self._vision_call(
                na_pad, vergelijk_prompt
            )
        except Exception as e:
            logger.debug("Action verification vision call failed: %s", e)
            analyse = (
                f"VOOR: {beschrijving_voor}\n\n"
                f"NA: {beschrijving_na}"
            )

        elapsed = time.time() - start
        self._analyses += 2
        self._totale_tijd += elapsed

        geslaagd = analyse.strip().upper().startswith(
            "JA"
        )

        console.print(
            f"[{'green' if geslaagd else 'red'}]"
            f"Verificatie: "
            f"{'GESLAAGD' if geslaagd else 'GEFAALD'}"
            f"[/{'green' if geslaagd else 'red'}]"
            f" [dim]({elapsed:.1f}s)[/dim]"
        )

        return {
            "geslaagd": geslaagd,
            "voor_pad": voor_pad,
            "na_pad": na_pad,
            "analyse": analyse,
            "beschrijving": beschrijving,
            "model": self.model,
            "tijd": elapsed,
        }

    def check_state(self, verwachting):
        """Controleer of het scherm matcht met verwachting.

        Puur beschrijvend — geen actie nodig.

        Args:
            verwachting: Beschrijving van wat je
                verwacht te zien.

        Returns:
            dict met match, analyse, pad, model, tijd.
        """
        console.print(
            f"[cyan]Screenshot maken...[/cyan]"
        )
        pad = self._screenshot("check_state")

        start = time.time()

        prompt = (
            "Bekijk dit screenshot en beantwoord:\n"
            f"Verwachting: '{verwachting}'\n\n"
            "Komt het scherm overeen met de"
            " verwachting?\n"
            "Begin je antwoord met JA of NEE.\n"
            "Geef daarna een korte toelichting."
            " Antwoord in het Nederlands."
        )

        try:
            analyse = self._vision_call(pad, prompt)
        except Exception as e:
            return {
                "match": None,
                "analyse": None,
                "fout": str(e),
                "pad": pad,
                "model": self.model,
                "tijd": time.time() - start,
            }

        elapsed = time.time() - start
        self._analyses += 1
        self._totale_tijd += elapsed

        match = analyse.strip().upper().startswith(
            "JA"
        )

        console.print(
            f"[{'green' if match else 'red'}]"
            f"Check: "
            f"{'MATCH' if match else 'GEEN MATCH'}"
            f"[/{'green' if match else 'red'}]"
            f" [dim]({elapsed:.1f}s)[/dim]"
        )

        return {
            "match": match,
            "analyse": analyse,
            "pad": pad,
            "model": self.model,
            "tijd": elapsed,
        }


__all__ = ["PixelEye"]

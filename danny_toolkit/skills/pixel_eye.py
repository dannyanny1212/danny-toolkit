"""
PixelEye — Het Oog van Project Omega.

Standalone vision skill via Ollama LLaVA.
Analyseert afbeeldingen, screenshots, vergelijkt
beelden — alles lokaal zonder API rate limits.
"""

import os
import time
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# ─── Config import (root config.py) ───
import sys

_root = Path(__file__).parent.parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from config import VISION_MODEL

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
        except Exception:
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


__all__ = ["PixelEye"]

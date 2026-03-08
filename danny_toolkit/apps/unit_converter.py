"""Unit Converter — Converteer eenheden tussen metrisch, imperiaal en digitaal.

Diamond Polish v6.11.0 — volledige type hints, class constants, precompiled regex.
"""

from __future__ import annotations

import logging
import re
from typing import Callable, Union

from danny_toolkit.core.utils import clear_scherm

logger = logging.getLogger(__name__)

# Precompiled pattern voor snelle conversie parsing (bijv. "100km", "25.5 c")
_SNELLE_RE = re.compile(r"([\d.]+)\s*(\w+)")

# Type alias voor conversie factor: getal of callable
ConversieFunc = Union[float, Callable[[float], float]]


class UnitConverterApp:
    """Converteer tussen verschillende eenheden via ratio-naar-basis of speciale formules.

    Ondersteunt 7 categorieën (lengte, gewicht, temperatuur, volume, tijd, data, snelheid)
    plus snelle eenheid-herkenning via regex.
    """

    CONVERSIES: dict[str, dict[str, object]] = {
        "lengte": {
            "naam": "Lengte",
            "eenheden": {
                "mm": 0.001, "cm": 0.01, "m": 1.0, "km": 1000.0,
                "inch": 0.0254, "feet": 0.3048, "yard": 0.9144, "mile": 1609.34,
            },
        },
        "gewicht": {
            "naam": "Gewicht",
            "eenheden": {
                "mg": 0.000001, "g": 0.001, "kg": 1.0, "ton": 1000.0,
                "oz": 0.0283495, "lb": 0.453592,
            },
        },
        "temperatuur": {
            "naam": "Temperatuur",
            "eenheden": ["celsius", "fahrenheit", "kelvin"],
        },
        "volume": {
            "naam": "Volume",
            "eenheden": {
                "ml": 0.001, "cl": 0.01, "dl": 0.1, "l": 1.0,
                "m3": 1000.0, "gallon": 3.78541, "pint": 0.473176,
            },
        },
        "tijd": {
            "naam": "Tijd",
            "eenheden": {
                "sec": 1.0, "min": 60.0, "uur": 3600.0, "dag": 86400.0,
                "week": 604800.0, "maand": 2592000.0, "jaar": 31536000.0,
            },
        },
        "data": {
            "naam": "Data (digitaal)",
            "eenheden": {
                "bit": 1.0, "byte": 8.0, "KB": 8192.0, "MB": 8388608.0,
                "GB": 8589934592.0, "TB": 8796093022208.0,
            },
        },
        "snelheid": {
            "naam": "Snelheid",
            "eenheden": {
                "m/s": 1.0, "km/h": 0.277778, "mph": 0.44704, "knopen": 0.514444,
            },
        },
    }

    SNELLE_CONVERSIES: dict[str, tuple[str, ConversieFunc]] = {
        "km": ("miles", 0.621371),
        "mile": ("km", 1.60934),
        "miles": ("km", 1.60934),
        "kg": ("lbs", 2.20462),
        "lb": ("kg", 0.453592),
        "lbs": ("kg", 0.453592),
        "c": ("fahrenheit", lambda x: x * 9 / 5 + 32),
        "f": ("celsius", lambda x: (x - 32) * 5 / 9),
        "m": ("feet", 3.28084),
        "feet": ("meter", 0.3048),
        "l": ("gallon", 0.264172),
        "gallon": ("liter", 3.78541),
        "cm": ("inch", 0.393701),
        "inch": ("cm", 2.54),
    }

    TEMP_LABELS: dict[str, str] = {"1": "°C", "2": "°F", "3": "K"}

    def __init__(self) -> None:
        """Initialiseer de UnitConverterApp (stateless — alle data is class-level)."""

    def run(self) -> None:
        """Start de interactieve unit converter loop."""
        while True:
            clear_scherm()
            print("+" + "=" * 50 + "+")
            print("|          UNIT CONVERTER                           |")
            print("+" + "=" * 50 + "+")
            print("|  1. Lengte                                        |")
            print("|  2. Gewicht                                       |")
            print("|  3. Temperatuur                                   |")
            print("|  4. Volume                                        |")
            print("|  5. Tijd                                          |")
            print("|  6. Data (digitaal)                               |")
            print("|  7. Snelheid                                      |")
            print("|  8. Snelle conversies                             |")
            print("|  0. Terug                                         |")
            print("+" + "=" * 50 + "+")

            keuze = input("\nKeuze: ").strip()

            if keuze == "0":
                break
            elif keuze == "1":
                self._converteer("lengte")
            elif keuze == "2":
                self._converteer("gewicht")
            elif keuze == "3":
                self._converteer_temp()
            elif keuze == "4":
                self._converteer("volume")
            elif keuze == "5":
                self._converteer("tijd")
            elif keuze == "6":
                self._converteer("data")
            elif keuze == "7":
                self._converteer("snelheid")
            elif keuze == "8":
                self._snelle_conversies()

            input("\nDruk op Enter...")

    def _converteer(self, categorie: str) -> None:
        """Voer een ratio-gebaseerde conversie uit via de basiseenheid.

        Args:
            categorie: Sleutel in CONVERSIES (bijv. 'lengte', 'gewicht').
        """
        info = self.CONVERSIES[categorie]
        eenheden: dict[str, float] = info["eenheden"]  # type: ignore[assignment]

        print(f"\n--- {info['naam'].upper()} CONVERSIE ---")
        print("\nBeschikbare eenheden:")

        eenheid_lijst = list(eenheden.keys())
        for i, e in enumerate(eenheid_lijst, 1):
            print(f"  {i}. {e}")

        try:
            print("\nVan welke eenheid?")
            van_idx = int(input("Nummer: ").strip()) - 1
            van_eenheid = eenheid_lijst[van_idx]

            print("\nNaar welke eenheid?")
            naar_idx = int(input("Nummer: ").strip()) - 1
            naar_eenheid = eenheid_lijst[naar_idx]

            waarde = float(input(f"\nWaarde in {van_eenheid}: ").strip().replace(",", "."))

            basis = waarde * eenheden[van_eenheid]
            resultaat = basis / eenheden[naar_eenheid]

            print(f"\n{'=' * 40}")
            print(f"  {waarde} {van_eenheid} = {resultaat:.6g} {naar_eenheid}")
            print(f"{'=' * 40}")

        except (ValueError, IndexError):
            logger.warning("Ongeldige invoer bij %s conversie", categorie)
            print("[!] Ongeldige invoer!")

    def _converteer_temp(self) -> None:
        """Converteer temperatuur via Celsius als tussenstap (speciale formules)."""
        print("\n--- TEMPERATUUR CONVERSIE ---")
        print("\nEenheden:")
        print("  1. Celsius")
        print("  2. Fahrenheit")
        print("  3. Kelvin")

        try:
            van = input("\nVan (1-3): ").strip()
            naar = input("Naar (1-3): ").strip()
            waarde = float(input("Waarde: ").strip().replace(",", "."))

            celsius = self._naar_celsius(van, waarde)
            if celsius is None:
                print("[!] Ongeldige keuze!")
                return

            resultaat, eenheid = self._van_celsius(naar, celsius)
            if resultaat is None:
                print("[!] Ongeldige keuze!")
                return

            print(f"\n{'=' * 40}")
            print(f"  {waarde} {self.TEMP_LABELS.get(van, '?')} = {resultaat:.2f} {eenheid}")
            print(f"{'=' * 40}")

        except ValueError:
            logger.warning("Ongeldige invoer bij temperatuur conversie")
            print("[!] Ongeldige invoer!")

    @staticmethod
    def _naar_celsius(keuze: str, waarde: float) -> float | None:
        """Converteer van gekozen eenheid naar Celsius.

        Returns:
            Celsius waarde, of None bij ongeldige keuze.
        """
        if keuze == "1":
            return waarde
        if keuze == "2":
            return (waarde - 32) * 5 / 9
        if keuze == "3":
            return waarde - 273.15
        return None

    @staticmethod
    def _van_celsius(keuze: str, celsius: float) -> tuple[float | None, str]:
        """Converteer van Celsius naar gekozen eenheid.

        Returns:
            Tuple van (resultaat, eenheid_label). Resultaat is None bij ongeldige keuze.
        """
        if keuze == "1":
            return celsius, "°C"
        if keuze == "2":
            return celsius * 9 / 5 + 32, "°F"
        if keuze == "3":
            return celsius + 273.15, "K"
        return None, "?"

    def _snelle_conversies(self) -> None:
        """Parse vrije-tekst invoer (bijv. '100km') en toon de snelle conversie."""
        print("\n--- SNELLE CONVERSIES ---")
        print("\nVoer een waarde in met eenheid:")
        print("  Voorbeelden: 100km, 50kg, 25c, 1mile")

        invoer = input("\nConverteer: ").strip().lower()
        if not invoer:
            return

        match = _SNELLE_RE.match(invoer)
        if not match:
            logger.warning("Snelle conversie: formaat niet herkend voor '%s'", invoer)
            print("[!] Formaat niet herkend!")
            return

        waarde = float(match.group(1))
        eenheid = match.group(2)

        if eenheid not in self.SNELLE_CONVERSIES:
            print(f"[!] Eenheid '{eenheid}' niet herkend!")
            print("    Probeer: km, mile, kg, lb, c, f, m, feet, l, gallon")
            return

        naar, factor = self.SNELLE_CONVERSIES[eenheid]
        resultaat = factor(waarde) if callable(factor) else waarde * factor

        print(f"\n{'=' * 40}")
        print(f"  {waarde} {eenheid} = {resultaat:.2f} {naar}")
        print(f"{'=' * 40}")

"""
Unit Converter - Converteer eenheden.
"""

import logging

from ..core.utils import clear_scherm

logger = logging.getLogger(__name__)


class UnitConverterApp:
    """Converteer tussen verschillende eenheden."""

    def __init__(self):
        self.conversies = {
            "lengte": {
                "naam": "Lengte",
                "eenheden": {
                    "mm": 0.001,
                    "cm": 0.01,
                    "m": 1.0,
                    "km": 1000.0,
                    "inch": 0.0254,
                    "feet": 0.3048,
                    "yard": 0.9144,
                    "mile": 1609.34
                }
            },
            "gewicht": {
                "naam": "Gewicht",
                "eenheden": {
                    "mg": 0.000001,
                    "g": 0.001,
                    "kg": 1.0,
                    "ton": 1000.0,
                    "oz": 0.0283495,
                    "lb": 0.453592
                }
            },
            "temperatuur": {
                "naam": "Temperatuur",
                "eenheden": ["celsius", "fahrenheit", "kelvin"]
            },
            "volume": {
                "naam": "Volume",
                "eenheden": {
                    "ml": 0.001,
                    "cl": 0.01,
                    "dl": 0.1,
                    "l": 1.0,
                    "m3": 1000.0,
                    "gallon": 3.78541,
                    "pint": 0.473176
                }
            },
            "tijd": {
                "naam": "Tijd",
                "eenheden": {
                    "sec": 1.0,
                    "min": 60.0,
                    "uur": 3600.0,
                    "dag": 86400.0,
                    "week": 604800.0,
                    "maand": 2592000.0,
                    "jaar": 31536000.0
                }
            },
            "data": {
                "naam": "Data (digitaal)",
                "eenheden": {
                    "bit": 1.0,
                    "byte": 8.0,
                    "KB": 8192.0,
                    "MB": 8388608.0,
                    "GB": 8589934592.0,
                    "TB": 8796093022208.0
                }
            },
            "snelheid": {
                "naam": "Snelheid",
                "eenheden": {
                    "m/s": 1.0,
                    "km/h": 0.277778,
                    "mph": 0.44704,
                    "knopen": 0.514444
                }
            }
        }

    def run(self):
        """Start de unit converter."""
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

    def _converteer(self, categorie: str):
        """Voer een conversie uit."""
        info = self.conversies[categorie]
        eenheden = info["eenheden"]

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

            # Converteer via basis eenheid
            basis = waarde * eenheden[van_eenheid]
            resultaat = basis / eenheden[naar_eenheid]

            print(f"\n{'=' * 40}")
            print(f"  {waarde} {van_eenheid} = {resultaat:.6g} {naar_eenheid}")
            print(f"{'=' * 40}")

        except (ValueError, IndexError):
            print("[!] Ongeldige invoer!")

    def _converteer_temp(self):
        """Converteer temperatuur (speciale formules)."""
        print("\n--- TEMPERATUUR CONVERSIE ---")
        print("\nEenheden:")
        print("  1. Celsius")
        print("  2. Fahrenheit")
        print("  3. Kelvin")

        try:
            van = input("\nVan (1-3): ").strip()
            naar = input("Naar (1-3): ").strip()
            waarde = float(input("Waarde: ").strip().replace(",", "."))

            # Converteer naar Celsius
            if van == "1":
                celsius = waarde
            elif van == "2":
                celsius = (waarde - 32) * 5 / 9
            elif van == "3":
                celsius = waarde - 273.15
            else:
                print("[!] Ongeldige keuze!")
                return

            # Converteer van Celsius naar doel
            if naar == "1":
                resultaat = celsius
                eenheid = "°C"
            elif naar == "2":
                resultaat = celsius * 9 / 5 + 32
                eenheid = "°F"
            elif naar == "3":
                resultaat = celsius + 273.15
                eenheid = "K"
            else:
                print("[!] Ongeldige keuze!")
                return

            eenheden_van = {
                "1": "°C", "2": "°F", "3": "K"
            }

            print(f"\n{'=' * 40}")
            print(f"  {waarde} {eenheden_van[van]} = {resultaat:.2f} {eenheid}")
            print(f"{'=' * 40}")

        except ValueError:
            print("[!] Ongeldige invoer!")

    def _snelle_conversies(self):
        """Snelle veelgebruikte conversies."""
        print("\n--- SNELLE CONVERSIES ---")
        print("\nVoer een waarde in met eenheid:")
        print("  Voorbeelden: 100km, 50kg, 25c, 1mile")

        invoer = input("\nConverteer: ").strip().lower()

        if not invoer:
            return

        # Parse invoer
        import re
        match = re.match(r"([\d.]+)\s*(\w+)", invoer)

        if not match:
            print("[!] Formaat niet herkend!")
            return

        waarde = float(match.group(1))
        eenheid = match.group(2)

        # Snelle conversies
        conversies = {
            "km": ("miles", 0.621371),
            "mile": ("km", 1.60934),
            "miles": ("km", 1.60934),
            "kg": ("lbs", 2.20462),
            "lb": ("kg", 0.453592),
            "lbs": ("kg", 0.453592),
            "c": ("fahrenheit", lambda x: x * 9/5 + 32),
            "f": ("celsius", lambda x: (x - 32) * 5/9),
            "m": ("feet", 3.28084),
            "feet": ("meter", 0.3048),
            "l": ("gallon", 0.264172),
            "gallon": ("liter", 3.78541),
            "cm": ("inch", 0.393701),
            "inch": ("cm", 2.54)
        }

        if eenheid in conversies:
            naar, factor = conversies[eenheid]
            if callable(factor):
                resultaat = factor(waarde)
            else:
                resultaat = waarde * factor

            print(f"\n{'=' * 40}")
            print(f"  {waarde} {eenheid} = {resultaat:.2f} {naar}")
            print(f"{'=' * 40}")
        else:
            print(f"[!] Eenheid '{eenheid}' niet herkend!")
            print("    Probeer: km, mile, kg, lb, c, f, m, feet, l, gallon")

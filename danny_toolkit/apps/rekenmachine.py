"""
Slimme Rekenmachine App v2.0 - Uitgebreide wetenschappelijke calculator.

Features:
- Basis en wetenschappelijke berekeningen
- Eenheden omrekenen
- Financiële berekeningen
- Statistieken
- Gezondheidsberekeningen
- Expressie parser
- Geheugen en geschiedenis
"""

import math
import json
from datetime import datetime
from pathlib import Path
from ..core.config import Config
from ..core.utils import clear_scherm, kleur, succes, fout, waarschuwing, info


class RekenmachineApp:
    """Uitgebreide wetenschappelijke rekenmachine v2.0."""

    VERSIE = "2.0"

    # Wiskundige constanten
    CONSTANTEN = {
        "pi": ("π", math.pi, "Pi - verhouding omtrek/diameter cirkel"),
        "e": ("e", math.e, "Euler's getal - basis natuurlijke logaritme"),
        "phi": ("φ", 1.618033988749895, "Gulden snede"),
        "sqrt2": ("√2", math.sqrt(2), "Wortel van 2"),
        "sqrt3": ("√3", math.sqrt(3), "Wortel van 3"),
        "c": ("c", 299792458, "Lichtsnelheid in m/s"),
        "g": ("g", 9.80665, "Valversnelling op aarde in m/s²")
    }

    # Eenheden conversie tabellen
    LENGTE_EENHEDEN = {
        "mm": 0.001,
        "cm": 0.01,
        "m": 1.0,
        "km": 1000.0,
        "inch": 0.0254,
        "feet": 0.3048,
        "yard": 0.9144,
        "mile": 1609.344
    }

    GEWICHT_EENHEDEN = {
        "mg": 0.000001,
        "g": 0.001,
        "kg": 1.0,
        "ton": 1000.0,
        "oz": 0.0283495,
        "lb": 0.453592
    }

    TEMPERATUUR_EENHEDEN = ["celsius", "fahrenheit", "kelvin"]

    DATA_EENHEDEN = {
        "bytes": 1,
        "KB": 1024,
        "MB": 1024**2,
        "GB": 1024**3,
        "TB": 1024**4,
        "PB": 1024**5
    }

    TIJD_EENHEDEN = {
        "seconden": 1,
        "minuten": 60,
        "uren": 3600,
        "dagen": 86400,
        "weken": 604800
    }

    # Valuta koersen (vast, voor demo)
    VALUTA_KOERSEN = {
        "EUR": 1.0,
        "USD": 1.08,
        "GBP": 0.86,
        "JPY": 162.50,
        "CHF": 0.95,
        "CAD": 1.47,
        "AUD": 1.65,
        "CNY": 7.82
    }

    def __init__(self):
        Config.ensure_dirs()
        self.bestand = Config.APPS_DATA_DIR / "rekenmachine.json"
        self.data = self._laad_data()
        self.laatste_resultaat = 0.0
        self.geheugen = self.data.get("geheugen", {})

    def _laad_data(self) -> dict:
        """Laadt opgeslagen data."""
        if self.bestand.exists():
            try:
                with open(self.bestand, "r", encoding="utf-8") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                pass
        return {
            "geschiedenis": [],
            "geheugen": {},
            "statistieken": {
                "berekeningen": 0,
                "favoriete_functie": {}
            }
        }

    def _sla_op(self):
        """Slaat data op."""
        self.data["geheugen"] = self.geheugen
        with open(self.bestand, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    def _voeg_geschiedenis_toe(self, berekening: str, resultaat: float):
        """Voegt berekening toe aan geschiedenis."""
        self.data["geschiedenis"].append({
            "berekening": berekening,
            "resultaat": resultaat,
            "datum": datetime.now().isoformat()
        })
        # Houd laatste 100
        if len(self.data["geschiedenis"]) > 100:
            self.data["geschiedenis"] = self.data["geschiedenis"][-100:]

        self.data["statistieken"]["berekeningen"] += 1
        self.laatste_resultaat = resultaat

    def _toon_header(self, titel: str):
        """Toont een mooie header."""
        print()
        print(kleur("╔" + "═" * 50 + "╗", "cyan"))
        print(kleur("║", "cyan") + f" {titel:^48} " + kleur("║", "cyan"))
        print(kleur("╚" + "═" * 50 + "╝", "cyan"))

    def _get_getal(self, prompt: str, allow_ans: bool = True) -> float:
        """Vraagt om een getal met foutafhandeling."""
        while True:
            invoer = input(kleur(f"  {prompt}", "cyan")).strip().lower()

            # Speciale invoer
            if allow_ans and invoer in ["ans", "antwoord", "laatste"]:
                print(kleur(f"    (gebruikt: {self.laatste_resultaat})", "grijs"))
                return self.laatste_resultaat

            # Geheugen ophalen
            if invoer.startswith("m") and len(invoer) == 2:
                slot = invoer[1]
                if slot in self.geheugen:
                    waarde = self.geheugen[slot]
                    print(kleur(f"    (uit geheugen {slot}: {waarde})", "grijs"))
                    return waarde

            # Constanten
            if invoer in self.CONSTANTEN:
                waarde = self.CONSTANTEN[invoer][1]
                print(kleur(f"    (gebruikt: {invoer} = {waarde})", "grijs"))
                return waarde

            try:
                return float(invoer.replace(",", "."))
            except ValueError:
                fout("Ongeldige invoer. Voer een getal in (of 'ans' voor laatste resultaat)")

    # ==================== BASIS BEREKENINGEN ====================

    def _basis_menu(self):
        """Toont basis berekeningen menu."""
        while True:
            self._toon_header("🔢 Basis Berekeningen")

            print(kleur("\n  Operaties:", "geel"))
            print("    1. Optellen (+)")
            print("    2. Aftrekken (-)")
            print("    3. Vermenigvuldigen (×)")
            print("    4. Delen (÷)")
            print("    5. Machtsverheffen (^)")
            print("    6. Worteltrekken (√)")
            print("    7. Modulo (%)")
            print("    8. Absolute waarde (|x|)")
            print(kleur("\n    0. Terug", "grijs"))

            keuze = input(kleur("\n  Keuze: ", "cyan")).strip()

            if keuze == "0":
                break

            resultaat = None
            berekening = ""

            try:
                if keuze == "1":
                    a = self._get_getal("Eerste getal: ")
                    b = self._get_getal("Tweede getal: ")
                    resultaat = a + b
                    berekening = f"{a} + {b}"

                elif keuze == "2":
                    a = self._get_getal("Eerste getal: ")
                    b = self._get_getal("Tweede getal: ")
                    resultaat = a - b
                    berekening = f"{a} - {b}"

                elif keuze == "3":
                    a = self._get_getal("Eerste getal: ")
                    b = self._get_getal("Tweede getal: ")
                    resultaat = a * b
                    berekening = f"{a} × {b}"

                elif keuze == "4":
                    a = self._get_getal("Eerste getal: ")
                    b = self._get_getal("Tweede getal: ")
                    if b == 0:
                        raise ValueError("Kan niet delen door nul!")
                    resultaat = a / b
                    berekening = f"{a} ÷ {b}"

                elif keuze == "5":
                    a = self._get_getal("Grondtal: ")
                    b = self._get_getal("Exponent: ")
                    resultaat = a ** b
                    berekening = f"{a}^{b}"

                elif keuze == "6":
                    a = self._get_getal("Getal: ")
                    n = input(kleur("  Wortelgraad (leeg=2): ", "cyan")).strip()
                    n = float(n) if n else 2
                    if a < 0 and n % 2 == 0:
                        raise ValueError("Kan geen even wortel van negatief getal!")
                    resultaat = a ** (1/n)
                    berekening = f"ⁿ√{a}" if n != 2 else f"√{a}"

                elif keuze == "7":
                    a = self._get_getal("Eerste getal: ")
                    b = self._get_getal("Tweede getal: ")
                    if b == 0:
                        raise ValueError("Kan niet delen door nul!")
                    resultaat = a % b
                    berekening = f"{a} mod {b}"

                elif keuze == "8":
                    a = self._get_getal("Getal: ")
                    resultaat = abs(a)
                    berekening = f"|{a}|"

                else:
                    fout("Ongeldige keuze.")
                    continue

                if resultaat is not None:
                    self._toon_resultaat(berekening, resultaat)

            except ValueError as e:
                fout(str(e))
            except Exception as e:
                fout(f"Fout: {e}")

            input(kleur("\n  Druk op Enter om verder te gaan...", "grijs"))

    # ==================== WETENSCHAPPELIJK ====================

    def _wetenschap_menu(self):
        """Wetenschappelijke berekeningen menu."""
        while True:
            self._toon_header("🔬 Wetenschappelijk")

            print(kleur("\n  Trigonometrie:", "geel"))
            print("    1. Sinus (sin)")
            print("    2. Cosinus (cos)")
            print("    3. Tangens (tan)")
            print("    4. Inverse sin (asin)")
            print("    5. Inverse cos (acos)")
            print("    6. Inverse tan (atan)")

            print(kleur("\n  Logaritmen:", "geel"))
            print("    7. Natuurlijke log (ln)")
            print("    8. Log base 10 (log)")
            print("    9. Log base 2 (log₂)")
            print("    a. Log willekeurige base")

            print(kleur("\n  Overig:", "geel"))
            print("    b. Factoriaal (n!)")
            print("    c. Constanten bekijken")
            print("    d. Graden ↔ Radialen")

            print(kleur("\n    0. Terug", "grijs"))

            keuze = input(kleur("\n  Keuze: ", "cyan")).strip().lower()

            if keuze == "0":
                break

            resultaat = None
            berekening = ""

            try:
                if keuze == "1":
                    hoek = self._get_getal("Hoek in graden: ")
                    resultaat = math.sin(math.radians(hoek))
                    berekening = f"sin({hoek}°)"

                elif keuze == "2":
                    hoek = self._get_getal("Hoek in graden: ")
                    resultaat = math.cos(math.radians(hoek))
                    berekening = f"cos({hoek}°)"

                elif keuze == "3":
                    hoek = self._get_getal("Hoek in graden: ")
                    resultaat = math.tan(math.radians(hoek))
                    berekening = f"tan({hoek}°)"

                elif keuze == "4":
                    waarde = self._get_getal("Waarde (-1 tot 1): ")
                    if not -1 <= waarde <= 1:
                        raise ValueError("Waarde moet tussen -1 en 1 zijn!")
                    resultaat = math.degrees(math.asin(waarde))
                    berekening = f"asin({waarde})"

                elif keuze == "5":
                    waarde = self._get_getal("Waarde (-1 tot 1): ")
                    if not -1 <= waarde <= 1:
                        raise ValueError("Waarde moet tussen -1 en 1 zijn!")
                    resultaat = math.degrees(math.acos(waarde))
                    berekening = f"acos({waarde})"

                elif keuze == "6":
                    waarde = self._get_getal("Waarde: ")
                    resultaat = math.degrees(math.atan(waarde))
                    berekening = f"atan({waarde})"

                elif keuze == "7":
                    getal = self._get_getal("Getal (>0): ")
                    if getal <= 0:
                        raise ValueError("Getal moet groter dan 0 zijn!")
                    resultaat = math.log(getal)
                    berekening = f"ln({getal})"

                elif keuze == "8":
                    getal = self._get_getal("Getal (>0): ")
                    if getal <= 0:
                        raise ValueError("Getal moet groter dan 0 zijn!")
                    resultaat = math.log10(getal)
                    berekening = f"log₁₀({getal})"

                elif keuze == "9":
                    getal = self._get_getal("Getal (>0): ")
                    if getal <= 0:
                        raise ValueError("Getal moet groter dan 0 zijn!")
                    resultaat = math.log2(getal)
                    berekening = f"log₂({getal})"

                elif keuze == "a":
                    getal = self._get_getal("Getal (>0): ")
                    base = self._get_getal("Base (>0, ≠1): ")
                    if getal <= 0 or base <= 0 or base == 1:
                        raise ValueError("Ongeldige waarden!")
                    resultaat = math.log(getal, base)
                    berekening = f"log_{base}({getal})"

                elif keuze == "b":
                    getal = self._get_getal("Getal (≥0, geheel): ")
                    n = int(getal)
                    if n < 0:
                        raise ValueError("Getal moet ≥0 zijn!")
                    if n > 170:
                        raise ValueError("Te groot! Maximum is 170.")
                    resultaat = math.factorial(n)
                    berekening = f"{n}!"

                elif keuze == "c":
                    self._toon_constanten()
                    continue

                elif keuze == "d":
                    self._graden_radialen()
                    continue

                else:
                    fout("Ongeldige keuze.")
                    continue

                if resultaat is not None:
                    self._toon_resultaat(berekening, resultaat)

            except ValueError as e:
                fout(str(e))
            except Exception as e:
                fout(f"Fout: {e}")

            input(kleur("\n  Druk op Enter om verder te gaan...", "grijs"))

    def _toon_constanten(self):
        """Toont alle beschikbare constanten."""
        self._toon_header("📐 Wiskundige Constanten")
        print()
        for key, (symbool, waarde, beschrijving) in self.CONSTANTEN.items():
            print(f"    {kleur(key, 'groen'):8} {symbool:3} = {waarde:<20} {kleur(beschrijving, 'grijs')}")
        print(kleur("\n  Tip: Typ de naam (bijv. 'pi') als invoer!", "geel"))

    def _graden_radialen(self):
        """Converteert tussen graden en radialen."""
        print(kleur("\n  1. Graden → Radialen", "geel"))
        print(kleur("  2. Radialen → Graden", "geel"))

        keuze = input(kleur("\n  Keuze: ", "cyan")).strip()

        if keuze == "1":
            graden = self._get_getal("Graden: ")
            radialen = math.radians(graden)
            self._toon_resultaat(f"{graden}° → rad", radialen)
        elif keuze == "2":
            radialen = self._get_getal("Radialen: ")
            graden = math.degrees(radialen)
            self._toon_resultaat(f"{radialen} rad → °", graden)

    # ==================== EENHEDEN ====================

    def _eenheden_menu(self):
        """Eenheden conversie menu."""
        while True:
            self._toon_header("📏 Eenheden Omrekenen")

            print(kleur("\n  Categorieën:", "geel"))
            print("    1. Lengte (mm, cm, m, km, inch, feet, mile)")
            print("    2. Gewicht (mg, g, kg, ton, oz, lb)")
            print("    3. Temperatuur (°C, °F, K)")
            print("    4. Data (bytes, KB, MB, GB, TB)")
            print("    5. Tijd (sec, min, uur, dag, week)")

            print(kleur("\n    0. Terug", "grijs"))

            keuze = input(kleur("\n  Keuze: ", "cyan")).strip()

            if keuze == "0":
                break
            elif keuze == "1":
                self._converteer_eenheid("Lengte", self.LENGTE_EENHEDEN)
            elif keuze == "2":
                self._converteer_eenheid("Gewicht", self.GEWICHT_EENHEDEN)
            elif keuze == "3":
                self._converteer_temperatuur()
            elif keuze == "4":
                self._converteer_eenheid("Data", self.DATA_EENHEDEN)
            elif keuze == "5":
                self._converteer_eenheid("Tijd", self.TIJD_EENHEDEN)
            else:
                fout("Ongeldige keuze.")

            input(kleur("\n  Druk op Enter om verder te gaan...", "grijs"))

    def _converteer_eenheid(self, categorie: str, eenheden: dict):
        """Generieke eenheden conversie."""
        print(kleur(f"\n  Beschikbare {categorie.lower()} eenheden:", "geel"))
        eenheid_lijst = list(eenheden.keys())
        for i, eenheid in enumerate(eenheid_lijst, 1):
            print(f"    {i}. {eenheid}")

        van_idx = input(kleur("\n  Van (nummer): ", "cyan")).strip()
        naar_idx = input(kleur("  Naar (nummer): ", "cyan")).strip()

        try:
            van = eenheid_lijst[int(van_idx) - 1]
            naar = eenheid_lijst[int(naar_idx) - 1]
            waarde = self._get_getal(f"Waarde in {van}: ")

            # Converteer via basis eenheid
            basis = waarde * eenheden[van]
            resultaat = basis / eenheden[naar]

            self._toon_resultaat(f"{waarde} {van} → {naar}", resultaat)
            print(kleur(f"    = {resultaat:.6g} {naar}", "groen"))

        except (ValueError, IndexError):
            fout("Ongeldige invoer.")

    def _converteer_temperatuur(self):
        """Temperatuur conversie."""
        print(kleur("\n  Temperatuur eenheden:", "geel"))
        print("    1. Celsius (°C)")
        print("    2. Fahrenheit (°F)")
        print("    3. Kelvin (K)")

        van = input(kleur("\n  Van (1-3): ", "cyan")).strip()
        naar = input(kleur("  Naar (1-3): ", "cyan")).strip()
        waarde = self._get_getal("Waarde: ")

        eenheden = ["celsius", "fahrenheit", "kelvin"]
        try:
            van_e = eenheden[int(van) - 1]
            naar_e = eenheden[int(naar) - 1]
        except (ValueError, IndexError):
            fout("Ongeldige invoer.")
            return

        # Eerst naar Celsius
        if van_e == "fahrenheit":
            celsius = (waarde - 32) * 5/9
        elif van_e == "kelvin":
            celsius = waarde - 273.15
        else:
            celsius = waarde

        # Dan naar doel
        if naar_e == "fahrenheit":
            resultaat = celsius * 9/5 + 32
            symbool = "°F"
        elif naar_e == "kelvin":
            resultaat = celsius + 273.15
            symbool = "K"
        else:
            resultaat = celsius
            symbool = "°C"

        van_sym = {"celsius": "°C", "fahrenheit": "°F", "kelvin": "K"}[van_e]
        self._toon_resultaat(f"{waarde}{van_sym} → {symbool}", resultaat)

    # ==================== FINANCIEEL ====================

    def _financieel_menu(self):
        """Financiële berekeningen menu."""
        while True:
            self._toon_header("💰 Financiële Berekeningen")

            print(kleur("\n  Berekeningen:", "geel"))
            print("    1. BTW berekenen")
            print("    2. Korting berekenen")
            print("    3. Percentage van bedrag")
            print("    4. Enkelvoudige rente")
            print("    5. Samengestelde rente")
            print("    6. Lening/Hypotheek (maandlasten)")
            print("    7. Valuta omrekenen")
            print("    8. Winstmarge berekenen")
            print("    9. Tip/Fooi berekenen")

            print(kleur("\n    0. Terug", "grijs"))

            keuze = input(kleur("\n  Keuze: ", "cyan")).strip()

            if keuze == "0":
                break

            try:
                if keuze == "1":
                    self._btw_berekenen()
                elif keuze == "2":
                    self._korting_berekenen()
                elif keuze == "3":
                    self._percentage_van()
                elif keuze == "4":
                    self._enkelvoudige_rente()
                elif keuze == "5":
                    self._samengestelde_rente()
                elif keuze == "6":
                    self._lening_berekenen()
                elif keuze == "7":
                    self._valuta_omrekenen()
                elif keuze == "8":
                    self._winstmarge()
                elif keuze == "9":
                    self._fooi_berekenen()
                else:
                    fout("Ongeldige keuze.")

            except ValueError as e:
                fout(str(e))

            input(kleur("\n  Druk op Enter om verder te gaan...", "grijs"))

    def _btw_berekenen(self):
        """BTW berekeningen."""
        print(kleur("\n  BTW berekening:", "geel"))
        print("    1. BTW toevoegen aan bedrag")
        print("    2. BTW uit bedrag halen")
        print("    3. BTW berekenen van bedrag")

        keuze = input(kleur("\n  Keuze: ", "cyan")).strip()
        bedrag = self._get_getal("Bedrag (€): ")
        btw_pct = self._get_getal("BTW percentage [21]: ") or 21

        if keuze == "1":
            btw = bedrag * (btw_pct / 100)
            totaal = bedrag + btw
            print(kleur(f"\n  Excl. BTW: €{bedrag:.2f}", "wit"))
            print(kleur(f"  BTW ({btw_pct}%): €{btw:.2f}", "wit"))
            print(kleur(f"  Incl. BTW: €{totaal:.2f}", "groen"))
            self._voeg_geschiedenis_toe(f"€{bedrag} + {btw_pct}% BTW", totaal)

        elif keuze == "2":
            excl = bedrag / (1 + btw_pct/100)
            btw = bedrag - excl
            print(kleur(f"\n  Incl. BTW: €{bedrag:.2f}", "wit"))
            print(kleur(f"  BTW ({btw_pct}%): €{btw:.2f}", "wit"))
            print(kleur(f"  Excl. BTW: €{excl:.2f}", "groen"))
            self._voeg_geschiedenis_toe(f"€{bedrag} - {btw_pct}% BTW", excl)

        elif keuze == "3":
            btw = bedrag * (btw_pct / 100)
            print(kleur(f"\n  Bedrag: €{bedrag:.2f}", "wit"))
            print(kleur(f"  BTW ({btw_pct}%): €{btw:.2f}", "groen"))
            self._voeg_geschiedenis_toe(f"{btw_pct}% van €{bedrag}", btw)

    def _korting_berekenen(self):
        """Korting berekening."""
        bedrag = self._get_getal("Originele prijs (€): ")
        korting_pct = self._get_getal("Korting percentage: ")

        korting = bedrag * (korting_pct / 100)
        nieuw = bedrag - korting

        print(kleur(f"\n  Origineel: €{bedrag:.2f}", "wit"))
        print(kleur(f"  Korting ({korting_pct}%): -€{korting:.2f}", "rood"))
        print(kleur(f"  Nieuw bedrag: €{nieuw:.2f}", "groen"))
        print(kleur(f"  Je bespaart: €{korting:.2f}", "geel"))

        self._voeg_geschiedenis_toe(f"€{bedrag} - {korting_pct}%", nieuw)

    def _percentage_van(self):
        """Percentage van een bedrag."""
        percentage = self._get_getal("Percentage: ")
        bedrag = self._get_getal("Van bedrag: ")

        resultaat = bedrag * (percentage / 100)
        self._toon_resultaat(f"{percentage}% van {bedrag}", resultaat)

    def _enkelvoudige_rente(self):
        """Enkelvoudige rente berekening."""
        hoofdsom = self._get_getal("Hoofdsom (€): ")
        rente = self._get_getal("Jaarlijkse rente (%): ")
        jaren = self._get_getal("Aantal jaren: ")

        rente_bedrag = hoofdsom * (rente/100) * jaren
        totaal = hoofdsom + rente_bedrag

        print(kleur(f"\n  Hoofdsom: €{hoofdsom:.2f}", "wit"))
        print(kleur(f"  Rente ({rente}% × {jaren} jaar): €{rente_bedrag:.2f}", "wit"))
        print(kleur(f"  Totaal: €{totaal:.2f}", "groen"))

        self._voeg_geschiedenis_toe(f"Enkelvoudige rente: €{hoofdsom} @ {rente}%", totaal)

    def _samengestelde_rente(self):
        """Samengestelde rente berekening."""
        hoofdsom = self._get_getal("Hoofdsom (€): ")
        rente = self._get_getal("Jaarlijkse rente (%): ")
        jaren = self._get_getal("Aantal jaren: ")
        freq_str = input(kleur("  Frequentie per jaar [12]: ", "cyan")).strip()
        frequentie = int(freq_str) if freq_str else 12

        totaal = hoofdsom * (1 + rente/100/frequentie) ** (frequentie * jaren)
        rente_bedrag = totaal - hoofdsom

        print(kleur(f"\n  Hoofdsom: €{hoofdsom:.2f}", "wit"))
        print(kleur(f"  Rente verdiend: €{rente_bedrag:.2f}", "wit"))
        print(kleur(f"  Totaal na {jaren} jaar: €{totaal:.2f}", "groen"))

        self._voeg_geschiedenis_toe(f"Samengestelde rente: €{hoofdsom} @ {rente}%", totaal)

    def _lening_berekenen(self):
        """Lening/hypotheek maandlasten berekening."""
        hoofdsom = self._get_getal("Leenbedrag (€): ")
        rente = self._get_getal("Jaarlijkse rente (%): ")
        jaren = self._get_getal("Looptijd (jaren): ")

        maanden = int(jaren * 12)
        maand_rente = rente / 100 / 12

        if maand_rente == 0:
            maandlast = hoofdsom / maanden
        else:
            maandlast = hoofdsom * (maand_rente * (1 + maand_rente)**maanden) / \
                       ((1 + maand_rente)**maanden - 1)

        totaal = maandlast * maanden
        totaal_rente = totaal - hoofdsom

        print(kleur(f"\n  Leenbedrag: €{hoofdsom:.2f}", "wit"))
        print(kleur(f"  Looptijd: {jaren} jaar ({maanden} maanden)", "wit"))
        print(kleur(f"  Rente: {rente}% per jaar", "wit"))
        print(kleur(f"\n  Maandlast: €{maandlast:.2f}", "groen"))
        print(kleur(f"  Totaal te betalen: €{totaal:.2f}", "wit"))
        print(kleur(f"  Totaal rente: €{totaal_rente:.2f}", "rood"))

        self._voeg_geschiedenis_toe(f"Lening €{hoofdsom}: maandlast", maandlast)

    def _valuta_omrekenen(self):
        """Valuta conversie."""
        print(kleur("\n  Beschikbare valuta:", "geel"))
        valuta_lijst = list(self.VALUTA_KOERSEN.keys())
        for i, valuta in enumerate(valuta_lijst, 1):
            koers = self.VALUTA_KOERSEN[valuta]
            print(f"    {i}. {valuta} (1 EUR = {koers})")

        van_idx = input(kleur("\n  Van (nummer): ", "cyan")).strip()
        naar_idx = input(kleur("  Naar (nummer): ", "cyan")).strip()
        bedrag = self._get_getal("Bedrag: ")

        try:
            van = valuta_lijst[int(van_idx) - 1]
            naar = valuta_lijst[int(naar_idx) - 1]

            # Via EUR
            in_eur = bedrag / self.VALUTA_KOERSEN[van]
            resultaat = in_eur * self.VALUTA_KOERSEN[naar]

            print(kleur(f"\n  {bedrag:.2f} {van} = {resultaat:.2f} {naar}", "groen"))
            self._voeg_geschiedenis_toe(f"{bedrag} {van} → {naar}", resultaat)

        except (ValueError, IndexError):
            fout("Ongeldige invoer.")

    def _winstmarge(self):
        """Winstmarge berekening."""
        inkoop = self._get_getal("Inkoopprijs (€): ")
        verkoop = self._get_getal("Verkoopprijs (€): ")

        winst = verkoop - inkoop
        marge_pct = (winst / verkoop) * 100 if verkoop > 0 else 0
        markup_pct = (winst / inkoop) * 100 if inkoop > 0 else 0

        print(kleur(f"\n  Inkoopprijs: €{inkoop:.2f}", "wit"))
        print(kleur(f"  Verkoopprijs: €{verkoop:.2f}", "wit"))
        print(kleur(f"  Winst: €{winst:.2f}", "groen"))
        print(kleur(f"  Winstmarge: {marge_pct:.1f}%", "geel"))
        print(kleur(f"  Markup: {markup_pct:.1f}%", "geel"))

    def _fooi_berekenen(self):
        """Fooi/tip berekening."""
        rekening = self._get_getal("Rekeningbedrag (€): ")
        fooi_pct = self._get_getal("Fooi percentage [15]: ") or 15
        personen_str = input(kleur("  Aantal personen [1]: ", "cyan")).strip()
        personen = int(personen_str) if personen_str else 1

        fooi = rekening * (fooi_pct / 100)
        totaal = rekening + fooi
        per_persoon = totaal / personen

        print(kleur(f"\n  Rekening: €{rekening:.2f}", "wit"))
        print(kleur(f"  Fooi ({fooi_pct}%): €{fooi:.2f}", "wit"))
        print(kleur(f"  Totaal: €{totaal:.2f}", "groen"))
        if personen > 1:
            print(kleur(f"  Per persoon: €{per_persoon:.2f}", "geel"))

    # ==================== STATISTIEKEN ====================

    def _statistieken_menu(self):
        """Statistieken berekeningen menu."""
        while True:
            self._toon_header("📊 Statistieken")

            print(kleur("\n  Berekeningen:", "geel"))
            print("    1. Gemiddelde")
            print("    2. Mediaan")
            print("    3. Modus")
            print("    4. Standaarddeviatie")
            print("    5. Variantie")
            print("    6. Som & Aantal")
            print("    7. Min & Max")
            print("    8. Alle statistieken")

            print(kleur("\n    0. Terug", "grijs"))

            keuze = input(kleur("\n  Keuze: ", "cyan")).strip()

            if keuze == "0":
                break

            # Vraag om getallen
            print(kleur("\n  Voer getallen in (gescheiden door komma of spatie):", "geel"))
            invoer = input(kleur("  Getallen: ", "cyan")).strip()

            try:
                # Parse getallen
                getallen = []
                for deel in invoer.replace(",", " ").split():
                    getallen.append(float(deel.replace(",", ".")))

                if not getallen:
                    raise ValueError("Geen getallen ingevoerd!")

                if keuze == "1":
                    resultaat = sum(getallen) / len(getallen)
                    self._toon_resultaat("Gemiddelde", resultaat)

                elif keuze == "2":
                    gesorteerd = sorted(getallen)
                    n = len(gesorteerd)
                    if n % 2 == 0:
                        resultaat = (gesorteerd[n//2-1] + gesorteerd[n//2]) / 2
                    else:
                        resultaat = gesorteerd[n//2]
                    self._toon_resultaat("Mediaan", resultaat)

                elif keuze == "3":
                    from collections import Counter
                    teller = Counter(getallen)
                    max_freq = max(teller.values())
                    modi = [k for k, v in teller.items() if v == max_freq]
                    print(kleur(f"\n  Modus: {modi}", "groen"))
                    print(kleur(f"  (komt {max_freq}x voor)", "grijs"))

                elif keuze == "4":
                    gem = sum(getallen) / len(getallen)
                    variantie = sum((x - gem)**2 for x in getallen) / len(getallen)
                    resultaat = math.sqrt(variantie)
                    self._toon_resultaat("Standaarddeviatie", resultaat)

                elif keuze == "5":
                    gem = sum(getallen) / len(getallen)
                    resultaat = sum((x - gem)**2 for x in getallen) / len(getallen)
                    self._toon_resultaat("Variantie", resultaat)

                elif keuze == "6":
                    print(kleur(f"\n  Som: {sum(getallen)}", "groen"))
                    print(kleur(f"  Aantal: {len(getallen)}", "groen"))

                elif keuze == "7":
                    print(kleur(f"\n  Minimum: {min(getallen)}", "groen"))
                    print(kleur(f"  Maximum: {max(getallen)}", "groen"))
                    print(kleur(f"  Bereik: {max(getallen) - min(getallen)}", "groen"))

                elif keuze == "8":
                    self._alle_statistieken(getallen)

                else:
                    fout("Ongeldige keuze.")

            except ValueError as e:
                fout(str(e))

            input(kleur("\n  Druk op Enter om verder te gaan...", "grijs"))

    def _alle_statistieken(self, getallen: list):
        """Berekent alle statistieken."""
        n = len(getallen)
        som = sum(getallen)
        gem = som / n
        gesorteerd = sorted(getallen)

        # Mediaan
        if n % 2 == 0:
            mediaan = (gesorteerd[n//2-1] + gesorteerd[n//2]) / 2
        else:
            mediaan = gesorteerd[n//2]

        # Variantie en std
        variantie = sum((x - gem)**2 for x in getallen) / n
        std = math.sqrt(variantie)

        print(kleur("\n  ═══ Statistisch Overzicht ═══", "geel"))
        print(f"    Aantal: {n}")
        print(f"    Som: {som}")
        print(f"    Gemiddelde: {gem:.4f}")
        print(f"    Mediaan: {mediaan:.4f}")
        print(f"    Minimum: {min(getallen)}")
        print(f"    Maximum: {max(getallen)}")
        print(f"    Bereik: {max(getallen) - min(getallen)}")
        print(f"    Variantie: {variantie:.4f}")
        print(f"    Standaarddeviatie: {std:.4f}")

    # ==================== GEZONDHEID ====================

    def _gezondheid_menu(self):
        """Gezondheidsberekeningen menu."""
        while True:
            self._toon_header("❤️ Gezondheidsberekeningen")

            print(kleur("\n  Berekeningen:", "geel"))
            print("    1. BMI (Body Mass Index)")
            print("    2. Ideaal gewicht")
            print("    3. Calorieën behoefte (BMR)")
            print("    4. Hartslag zones")
            print("    5. Waterinname advies")

            print(kleur("\n    0. Terug", "grijs"))

            keuze = input(kleur("\n  Keuze: ", "cyan")).strip()

            if keuze == "0":
                break

            try:
                if keuze == "1":
                    self._bmi_berekenen()
                elif keuze == "2":
                    self._ideaal_gewicht()
                elif keuze == "3":
                    self._calorieen_berekenen()
                elif keuze == "4":
                    self._hartslag_zones()
                elif keuze == "5":
                    self._waterinname()
                else:
                    fout("Ongeldige keuze.")

            except ValueError as e:
                fout(str(e))

            input(kleur("\n  Druk op Enter om verder te gaan...", "grijs"))

    def _bmi_berekenen(self):
        """BMI berekening."""
        gewicht = self._get_getal("Gewicht (kg): ")
        lengte = self._get_getal("Lengte (cm): ")

        lengte_m = lengte / 100
        bmi = gewicht / (lengte_m ** 2)

        # Classificatie
        if bmi < 18.5:
            categorie = "Ondergewicht"
            kleur_cat = "geel"
        elif bmi < 25:
            categorie = "Normaal gewicht"
            kleur_cat = "groen"
        elif bmi < 30:
            categorie = "Overgewicht"
            kleur_cat = "geel"
        else:
            categorie = "Obesitas"
            kleur_cat = "rood"

        print(kleur(f"\n  BMI: {bmi:.1f}", "groen"))
        print(kleur(f"  Categorie: {categorie}", kleur_cat))

        print(kleur("\n  BMI Schaal:", "grijs"))
        print("    < 18.5  : Ondergewicht")
        print("    18.5-25 : Normaal")
        print("    25-30   : Overgewicht")
        print("    > 30    : Obesitas")

    def _ideaal_gewicht(self):
        """Berekent ideaal gewicht."""
        lengte = self._get_getal("Lengte (cm): ")
        print(kleur("\n  Geslacht:", "geel"))
        print("    1. Man")
        print("    2. Vrouw")
        geslacht = input(kleur("  Keuze: ", "cyan")).strip()

        lengte_m = lengte / 100

        # Devine formule
        if geslacht == "1":
            ideaal = 50 + 2.3 * ((lengte - 152.4) / 2.54)
        else:
            ideaal = 45.5 + 2.3 * ((lengte - 152.4) / 2.54)

        # BMI methode (BMI 22)
        bmi_ideaal = 22 * (lengte_m ** 2)

        print(kleur(f"\n  Ideaal gewicht (Devine): {ideaal:.1f} kg", "groen"))
        print(kleur(f"  Ideaal gewicht (BMI 22): {bmi_ideaal:.1f} kg", "groen"))
        print(kleur(f"  Gezond bereik: {18.5 * lengte_m**2:.1f} - {24.9 * lengte_m**2:.1f} kg", "geel"))

    def _calorieen_berekenen(self):
        """Berekent dagelijkse caloriebehoefte."""
        gewicht = self._get_getal("Gewicht (kg): ")
        lengte = self._get_getal("Lengte (cm): ")
        leeftijd = self._get_getal("Leeftijd (jaren): ")

        print(kleur("\n  Geslacht:", "geel"))
        print("    1. Man")
        print("    2. Vrouw")
        geslacht = input(kleur("  Keuze: ", "cyan")).strip()

        # Harris-Benedict BMR
        if geslacht == "1":
            bmr = 88.362 + (13.397 * gewicht) + (4.799 * lengte) - (5.677 * leeftijd)
        else:
            bmr = 447.593 + (9.247 * gewicht) + (3.098 * lengte) - (4.330 * leeftijd)

        print(kleur(f"\n  Basaal Metabolisme (BMR): {bmr:.0f} kcal/dag", "groen"))

        print(kleur("\n  Dagelijkse behoefte per activiteitsniveau:", "geel"))
        print(f"    Sedentair (weinig beweging):    {bmr * 1.2:.0f} kcal")
        print(f"    Licht actief (1-3x/week):       {bmr * 1.375:.0f} kcal")
        print(f"    Matig actief (3-5x/week):       {bmr * 1.55:.0f} kcal")
        print(f"    Zeer actief (6-7x/week):        {bmr * 1.725:.0f} kcal")
        print(f"    Extra actief (atleet):          {bmr * 1.9:.0f} kcal")

    def _hartslag_zones(self):
        """Berekent hartslag trainingszones."""
        leeftijd = self._get_getal("Leeftijd (jaren): ")

        max_hr = 220 - leeftijd

        print(kleur(f"\n  Maximale hartslag: {max_hr:.0f} bpm", "groen"))
        print(kleur("\n  Trainingszones:", "geel"))
        print(f"    Zone 1 (50-60%): {max_hr*0.5:.0f}-{max_hr*0.6:.0f} bpm - Herstel")
        print(f"    Zone 2 (60-70%): {max_hr*0.6:.0f}-{max_hr*0.7:.0f} bpm - Vetverbranding")
        print(f"    Zone 3 (70-80%): {max_hr*0.7:.0f}-{max_hr*0.8:.0f} bpm - Aerobe zone")
        print(f"    Zone 4 (80-90%): {max_hr*0.8:.0f}-{max_hr*0.9:.0f} bpm - Anaerobe zone")
        print(f"    Zone 5 (90-100%): {max_hr*0.9:.0f}-{max_hr:.0f} bpm - Maximum")

    def _waterinname(self):
        """Berekent aanbevolen waterinname."""
        gewicht = self._get_getal("Gewicht (kg): ")

        # 30-35 ml per kg
        basis = gewicht * 0.033
        actief = gewicht * 0.04

        print(kleur(f"\n  Aanbevolen waterinname:", "geel"))
        print(kleur(f"    Basis: {basis:.1f} liter/dag", "groen"))
        print(kleur(f"    Bij sport: {actief:.1f} liter/dag", "groen"))
        print(kleur(f"    Aantal glazen (250ml): {basis*4:.0f}-{actief*4:.0f}", "grijs"))

    # ==================== EXPRESSIE PARSER ====================

    def _expressie_menu(self):
        """Directe expressie invoer."""
        self._toon_header("⌨️ Expressie Calculator")

        print(kleur("\n  Voer directe berekeningen in zoals:", "geel"))
        print("    2 + 3 * 4")
        print("    sqrt(16)")
        print("    sin(45)")
        print("    2^10")
        print("    100 / 3")
        print(kleur("\n  Typ 'q' om terug te gaan", "grijs"))
        print(kleur("  Typ 'ans' voor laatste resultaat", "grijs"))

        while True:
            expressie = input(kleur("\n  > ", "cyan")).strip()

            if expressie.lower() == "q":
                break

            if not expressie:
                continue

            try:
                # Vervang symbolen
                expr = expressie.lower()
                expr = expr.replace("^", "**")
                expr = expr.replace("√", "math.sqrt")
                expr = expr.replace("sqrt", "math.sqrt")
                expr = expr.replace("sin", "math.sin")
                expr = expr.replace("cos", "math.cos")
                expr = expr.replace("tan", "math.tan")
                expr = expr.replace("log", "math.log10")
                expr = expr.replace("ln", "math.log")
                expr = expr.replace("pi", "math.pi")
                expr = expr.replace("e", "math.e")
                expr = expr.replace("ans", str(self.laatste_resultaat))

                # Evalueer (veilig)
                allowed = {
                    "math": math,
                    "__builtins__": {}
                }
                resultaat = eval(expr, allowed)

                print(kleur(f"  = {resultaat}", "groen"))
                self._voeg_geschiedenis_toe(expressie, resultaat)

            except Exception as e:
                fout(f"Fout in expressie: {e}")

    # ==================== GEHEUGEN ====================

    def _geheugen_menu(self):
        """Geheugen en geschiedenis menu."""
        while True:
            self._toon_header("💾 Geheugen & Geschiedenis")

            print(kleur("\n  Geheugen slots:", "geel"))
            if self.geheugen:
                for slot, waarde in self.geheugen.items():
                    print(f"    M{slot}: {waarde}")
            else:
                print(kleur("    (leeg)", "grijs"))

            print(kleur(f"\n  Laatste resultaat (ans): {self.laatste_resultaat}", "geel"))

            print(kleur("\n  Opties:", "geel"))
            print("    1. Opslaan in geheugen")
            print("    2. Geheugen wissen")
            print("    3. Geschiedenis bekijken")
            print("    4. Statistieken")

            print(kleur("\n    0. Terug", "grijs"))

            keuze = input(kleur("\n  Keuze: ", "cyan")).strip()

            if keuze == "0":
                break
            elif keuze == "1":
                slot = input(kleur("  Slot (1-9): ", "cyan")).strip()
                if slot in "123456789":
                    waarde = self._get_getal(f"Waarde voor M{slot}: ")
                    self.geheugen[slot] = waarde
                    succes(f"M{slot} = {waarde}")
            elif keuze == "2":
                self.geheugen.clear()
                succes("Geheugen gewist!")
            elif keuze == "3":
                self._toon_geschiedenis()
            elif keuze == "4":
                self._toon_rekenmachine_stats()

            input(kleur("\n  Druk op Enter om verder te gaan...", "grijs"))

    def _toon_geschiedenis(self):
        """Toont berekeningsgeschiedenis."""
        geschiedenis = self.data.get("geschiedenis", [])

        if not geschiedenis:
            waarschuwing("Geen geschiedenis.")
            return

        print(kleur("\n  Laatste 20 berekeningen:", "geel"))
        for entry in geschiedenis[-20:]:
            datum = entry["datum"][:10]
            print(f"    {datum}: {entry['berekening']} = {entry['resultaat']}")

    def _toon_rekenmachine_stats(self):
        """Toont rekenmachine statistieken."""
        stats = self.data.get("statistieken", {})

        print(kleur("\n  Statistieken:", "geel"))
        print(f"    Totaal berekeningen: {stats.get('berekeningen', 0)}")

    # ==================== HULPFUNCTIES ====================

    def _toon_resultaat(self, berekening: str, resultaat: float):
        """Toont het resultaat en slaat op."""
        print()
        print(kleur("  ┌" + "─" * 40 + "┐", "groen"))
        print(kleur("  │", "groen") + f" {berekening:^38} " + kleur("│", "groen"))
        print(kleur("  │", "groen") + kleur(f" = {resultaat:^36} ", "geel") + kleur("│", "groen"))
        print(kleur("  └" + "─" * 40 + "┘", "groen"))

        self._voeg_geschiedenis_toe(berekening, resultaat)

    def _toon_hoofdmenu(self):
        """Toont het hoofdmenu."""
        print()
        print(kleur("┌" + "─" * 44 + "┐", "cyan"))
        print(kleur("│", "cyan") + kleur("     🧮 SLIMME REKENMACHINE v2.0", "geel") +
              kleur("          │", "cyan"))
        print(kleur("├" + "─" * 44 + "┤", "cyan"))

        menu_items = [
            ("1", "Basis berekeningen"),
            ("2", "Wetenschappelijk"),
            ("3", "Eenheden omrekenen"),
            ("4", "Financieel"),
            ("5", "Statistieken"),
            ("6", "Gezondheid"),
            ("", ""),
            ("7", "Expressie calculator"),
            ("8", "Geheugen & Geschiedenis"),
            ("", ""),
            ("0", "Terug naar hoofdmenu")
        ]

        for key, label in menu_items:
            if key == "":
                print(kleur("│", "cyan") + " " * 44 + kleur("│", "cyan"))
            else:
                print(kleur("│", "cyan") + f"  {kleur(key, 'groen'):>5}. {label:<36}" +
                      kleur("│", "cyan"))

        print(kleur("└" + "─" * 44 + "┘", "cyan"))

        if self.laatste_resultaat != 0:
            print(kleur(f"  Laatste resultaat (ans): {self.laatste_resultaat}", "grijs"))

    # ==================== MAIN ====================

    def run(self):
        """Start de app."""
        clear_scherm()

        print(kleur("""
    ╔═══════════════════════════════════════════════════╗
    ║                                                   ║
    ║   🧮  SLIMME REKENMACHINE  v2.0                  ║
    ║                                                   ║
    ║   Wetenschappelijk • Financieel • Statistiek     ║
    ║                                                   ║
    ╚═══════════════════════════════════════════════════╝
        """, "cyan"))

        stats = self.data.get("statistieken", {})
        print(f"    Totaal berekeningen: {stats.get('berekeningen', 0)}")

        while True:
            self._toon_hoofdmenu()
            keuze = input(kleur("\n  Kies een optie: ", "cyan")).strip()

            if keuze == "0":
                self._sla_op()
                print(kleur("\n  Terug naar hoofdmenu...", "grijs"))
                break
            elif keuze == "1":
                self._basis_menu()
            elif keuze == "2":
                self._wetenschap_menu()
            elif keuze == "3":
                self._eenheden_menu()
            elif keuze == "4":
                self._financieel_menu()
            elif keuze == "5":
                self._statistieken_menu()
            elif keuze == "6":
                self._gezondheid_menu()
            elif keuze == "7":
                self._expressie_menu()
            elif keuze == "8":
                self._geheugen_menu()
            else:
                fout("Ongeldige keuze.")

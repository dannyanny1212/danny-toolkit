"""
Code Analyse App - Python code analyzer met echte bestandsanalyse.
"""

import re
import ast
from pathlib import Path
from collections import Counter
from statistics import mean, median, stdev
from typing import List, Dict, Any, Optional

from ..core.utils import clear_scherm


class CodeAnalyseApp:
    """Python code analyzer met bestandsanalyse, complexity en formatting."""

    # Complexity keywords die branches toevoegen
    COMPLEXITY_KEYWORDS = ["if", "elif", "for", "while", "except", "with", "and", "or"]

    def __init__(self):
        self.huidig_bestand = None
        self.huidige_code = None

    # ==================== BESTAND ANALYSEREN ====================

    def analyseer_bestand(self, pad: str) -> Dict[str, Any]:
        """Analyseer een Python bestand volledig."""
        path = Path(pad)
        if not path.exists():
            return {"fout": f"Bestand niet gevonden: {pad}"}
        if not path.suffix == ".py":
            return {"fout": "Alleen Python bestanden (.py) worden ondersteund"}

        with open(path, "r", encoding="utf-8") as f:
            code = f.read()

        self.huidig_bestand = pad
        self.huidige_code = code

        regels = code.split("\n")
        lege_regels = sum(1 for r in regels if not r.strip())
        comment_regels = sum(1 for r in regels if r.strip().startswith("#"))
        code_regels = len(regels) - lege_regels - comment_regels

        # Parse met AST
        try:
            tree = ast.parse(code)
            functies = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
            klassen = [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
            imports = [node for node in ast.walk(tree)
                      if isinstance(node, (ast.Import, ast.ImportFrom))]
        except SyntaxError as e:
            return {"fout": f"Syntax error in bestand: {e}"}

        return {
            "bestand": path.name,
            "pad": str(path.absolute()),
            "totaal_regels": len(regels),
            "code_regels": code_regels,
            "lege_regels": lege_regels,
            "comment_regels": comment_regels,
            "aantal_functies": len(functies),
            "functie_namen": [f.name for f in functies],
            "aantal_klassen": len(klassen),
            "klasse_namen": [k.name for k in klassen],
            "aantal_imports": len(imports),
        }

    # ==================== CODE COMPLEXITY ====================

    def bereken_complexity(self, code: str = None) -> Dict[str, Any]:
        """Bereken cyclomatic complexity en nesting depth."""
        code = code or self.huidige_code
        if not code:
            return {"fout": "Geen code geladen"}

        regels = code.split("\n")

        # Cyclomatic complexity (aantal decision points + 1)
        complexity = 1
        for regel in regels:
            regel_stripped = regel.strip()
            for keyword in self.COMPLEXITY_KEYWORDS:
                # Check of keyword aan begin van regel staat of na spatie
                pattern = rf'\b{keyword}\b'
                complexity += len(re.findall(pattern, regel_stripped))

        # Nesting depth
        max_nesting = 0
        current_nesting = 0
        for regel in regels:
            if regel.strip():
                # Tel indentatie niveau (4 spaties = 1 niveau)
                indent = len(regel) - len(regel.lstrip())
                niveau = indent // 4
                current_nesting = niveau
                max_nesting = max(max_nesting, current_nesting)

        # Gemiddelde regel lengte
        niet_lege = [r for r in regels if r.strip()]
        gem_lengte = mean([len(r) for r in niet_lege]) if niet_lege else 0

        # Lange regels (> 80 karakters)
        lange_regels = [(i+1, len(r)) for i, r in enumerate(regels) if len(r) > 80]

        # Complexity rating
        if complexity <= 5:
            rating = "Eenvoudig (goed!)"
        elif complexity <= 10:
            rating = "Matig complex"
        elif complexity <= 20:
            rating = "Complex (refactor overwegen)"
        else:
            rating = "Zeer complex (refactor nodig!)"

        return {
            "cyclomatic_complexity": complexity,
            "complexity_rating": rating,
            "max_nesting_depth": max_nesting,
            "gemiddelde_regel_lengte": round(gem_lengte, 1),
            "lange_regels_count": len(lange_regels),
            "lange_regels": lange_regels[:5],  # Eerste 5
        }

    # ==================== CODE FORMATTER ====================

    def check_formatting(self, code: str = None) -> Dict[str, Any]:
        """Check code formatting issues."""
        code = code or self.huidige_code
        if not code:
            return {"fout": "Geen code geladen"}

        regels = code.split("\n")
        problemen = []

        for i, regel in enumerate(regels, 1):
            # Trailing whitespace
            if regel != regel.rstrip():
                problemen.append({
                    "regel": i,
                    "type": "trailing_whitespace",
                    "beschrijving": "Trailing whitespace aan einde van regel"
                })

            # Tabs in plaats van spaties
            if "\t" in regel:
                problemen.append({
                    "regel": i,
                    "type": "tabs",
                    "beschrijving": "Tab gevonden (gebruik 4 spaties)"
                })

            # Te lange regel
            if len(regel) > 100:
                problemen.append({
                    "regel": i,
                    "type": "te_lang",
                    "beschrijving": f"Regel te lang ({len(regel)} > 100 karakters)"
                })

            # Meerdere lege regels achter elkaar
            if i > 1 and not regel.strip() and not regels[i-2].strip():
                if i > 2 and not regels[i-3].strip():
                    problemen.append({
                        "regel": i,
                        "type": "teveel_lege_regels",
                        "beschrijving": "Meer dan 2 lege regels achter elkaar"
                    })

            # Spatie voor dubbele punt
            if re.search(r'\s+:', regel) and "http" not in regel:
                problemen.append({
                    "regel": i,
                    "type": "spatie_voor_dubbelpunt",
                    "beschrijving": "Spatie voor dubbele punt"
                })

        return {
            "totaal_problemen": len(problemen),
            "problemen": problemen[:10],  # Eerste 10
            "score": max(0, 100 - len(problemen) * 5),
        }

    def fix_formatting(self, code: str = None) -> str:
        """Fix basis formatting issues."""
        code = code or self.huidige_code
        if not code:
            return ""

        regels = code.split("\n")
        gefixte_regels = []

        vorige_leeg = False
        dubbel_leeg = False

        for regel in regels:
            # Fix tabs naar 4 spaties
            regel = regel.replace("\t", "    ")

            # Fix trailing whitespace
            regel = regel.rstrip()

            # Beperk lege regels tot max 2
            is_leeg = not regel.strip()
            if is_leeg:
                if dubbel_leeg:
                    continue  # Skip extra lege regels
                if vorige_leeg:
                    dubbel_leeg = True
            else:
                dubbel_leeg = False

            gefixte_regels.append(regel)
            vorige_leeg = is_leeg

        return "\n".join(gefixte_regels)

    # ==================== DOCUMENTATIE CHECKER ====================

    def check_documentatie(self, code: str = None) -> Dict[str, Any]:
        """Check of functies en klassen docstrings hebben."""
        code = code or self.huidige_code
        if not code:
            return {"fout": "Geen code geladen"}

        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return {"fout": f"Syntax error: {e}"}

        resultaten = {
            "functies_totaal": 0,
            "functies_met_docstring": 0,
            "functies_zonder_docstring": [],
            "klassen_totaal": 0,
            "klassen_met_docstring": 0,
            "klassen_zonder_docstring": [],
        }

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                resultaten["functies_totaal"] += 1
                docstring = ast.get_docstring(node)
                if docstring:
                    resultaten["functies_met_docstring"] += 1
                else:
                    resultaten["functies_zonder_docstring"].append(node.name)

            elif isinstance(node, ast.ClassDef):
                resultaten["klassen_totaal"] += 1
                docstring = ast.get_docstring(node)
                if docstring:
                    resultaten["klassen_met_docstring"] += 1
                else:
                    resultaten["klassen_zonder_docstring"].append(node.name)

        # Bereken percentage
        totaal = resultaten["functies_totaal"] + resultaten["klassen_totaal"]
        met_doc = resultaten["functies_met_docstring"] + resultaten["klassen_met_docstring"]
        resultaten["documentatie_percentage"] = round(
            (met_doc / totaal * 100) if totaal > 0 else 100, 1
        )

        return resultaten

    # ==================== STATISTIEK FUNCTIES (origineel) ====================

    @staticmethod
    def bereken_statistieken(getallen: List[float]) -> Dict[str, Any]:
        """Berekent uitgebreide statistieken van een lijst getallen."""
        if not getallen:
            return {"fout": "Lege lijst"}

        return {
            "som": sum(getallen),
            "gemiddelde": mean(getallen),
            "mediaan": median(getallen),
            "minimum": min(getallen),
            "maximum": max(getallen),
            "bereik": max(getallen) - min(getallen),
            "aantal": len(getallen),
            "standaarddeviatie": stdev(getallen) if len(getallen) > 1 else 0
        }

    @staticmethod
    def tel_woorden(tekst: str) -> Dict[str, int]:
        """Telt woorden in een tekst."""
        tekst = tekst.lower()
        for teken in ".,!?;:\"'()[]{}":
            tekst = tekst.replace(teken, "")
        return dict(Counter(tekst.split()))

    # ==================== INTERACTIEVE MODUS ====================

    def _toon_menu(self):
        """Toont het hoofdmenu."""
        print("\n+==================================+")
        print("|       CODE ANALYSE TOOL          |")
        print("+==================================+")
        print("|  1. Analyseer Python bestand     |")
        print("|  2. Check code complexity        |")
        print("|  3. Check formatting             |")
        print("|  4. Fix formatting               |")
        print("|  5. Check documentatie           |")
        print("|  6. Volledige analyse            |")
        print("+----------------------------------+")
        print("|  7. Statistieken (getallen)      |")
        print("|  8. Woordtelling (tekst)         |")
        print("|  0. Terug naar hoofdmenu         |")
        print("+==================================+")
        if self.huidig_bestand:
            print(f"  Geladen: {Path(self.huidig_bestand).name}")

    def _laad_bestand(self):
        """Vraag gebruiker om bestand te laden."""
        print("\nVoer het pad naar een Python bestand in:")
        print("(Tip: gebruik relatief pad zoals 'main.py')")
        pad = input("\nPad: ").strip()

        if not pad:
            print("Geen pad ingevoerd.")
            return

        resultaat = self.analyseer_bestand(pad)

        if "fout" in resultaat:
            print(f"\nFout: {resultaat['fout']}")
            return

        print("\n" + "=" * 50)
        print("BESTANDSANALYSE")
        print("=" * 50)
        print(f"\nBestand: {resultaat['bestand']}")
        print(f"\nRegels:")
        print(f"  Totaal:    {resultaat['totaal_regels']}")
        print(f"  Code:      {resultaat['code_regels']}")
        print(f"  Comments:  {resultaat['comment_regels']}")
        print(f"  Leeg:      {resultaat['lege_regels']}")
        print(f"\nStructuur:")
        print(f"  Klassen:   {resultaat['aantal_klassen']}")
        if resultaat['klasse_namen']:
            for naam in resultaat['klasse_namen']:
                print(f"             - {naam}")
        print(f"  Functies:  {resultaat['aantal_functies']}")
        if resultaat['functie_namen']:
            for naam in resultaat['functie_namen'][:10]:
                print(f"             - {naam}")
            if len(resultaat['functie_namen']) > 10:
                print(f"             ... en {len(resultaat['functie_namen'])-10} meer")
        print(f"  Imports:   {resultaat['aantal_imports']}")

    def _toon_complexity(self):
        """Toon complexity analyse."""
        if not self.huidige_code:
            print("\nLaad eerst een bestand (optie 1)!")
            return

        result = self.bereken_complexity()
        print("\n" + "=" * 50)
        print("CODE COMPLEXITY")
        print("=" * 50)
        print(f"\nCyclomatic Complexity: {result['cyclomatic_complexity']}")
        print(f"Rating: {result['complexity_rating']}")
        print(f"\nMax Nesting Depth: {result['max_nesting_depth']}")
        print(f"Gem. Regel Lengte: {result['gemiddelde_regel_lengte']} karakters")
        print(f"\nLange regels (>80): {result['lange_regels_count']}")
        if result['lange_regels']:
            for regel_nr, lengte in result['lange_regels']:
                print(f"  Regel {regel_nr}: {lengte} karakters")

    def _toon_formatting(self):
        """Toon formatting check."""
        if not self.huidige_code:
            print("\nLaad eerst een bestand (optie 1)!")
            return

        result = self.check_formatting()
        print("\n" + "=" * 50)
        print("FORMATTING CHECK")
        print("=" * 50)
        print(f"\nScore: {result['score']}/100")
        print(f"Problemen gevonden: {result['totaal_problemen']}")

        if result['problemen']:
            print("\nEerste problemen:")
            for p in result['problemen']:
                print(f"  Regel {p['regel']}: {p['beschrijving']}")

    def _fix_formatting(self):
        """Fix formatting en toon resultaat."""
        if not self.huidige_code:
            print("\nLaad eerst een bestand (optie 1)!")
            return

        gefixte_code = self.fix_formatting()
        origineel_problemen = self.check_formatting(self.huidige_code)['totaal_problemen']
        nieuw_problemen = self.check_formatting(gefixte_code)['totaal_problemen']

        print("\n" + "=" * 50)
        print("FORMATTING FIX")
        print("=" * 50)
        print(f"\nProblemen voor fix: {origineel_problemen}")
        print(f"Problemen na fix:   {nieuw_problemen}")
        print(f"Opgelost:           {origineel_problemen - nieuw_problemen}")

        opslaan = input("\nWil je de gefixte code opslaan? (j/n): ").lower().strip()
        if opslaan == "j" and self.huidig_bestand:
            with open(self.huidig_bestand, "w", encoding="utf-8") as f:
                f.write(gefixte_code)
            self.huidige_code = gefixte_code
            print(f"Opgeslagen naar {self.huidig_bestand}!")

    def _toon_documentatie(self):
        """Toon documentatie check."""
        if not self.huidige_code:
            print("\nLaad eerst een bestand (optie 1)!")
            return

        result = self.check_documentatie()

        if "fout" in result:
            print(f"\nFout: {result['fout']}")
            return

        print("\n" + "=" * 50)
        print("DOCUMENTATIE CHECK")
        print("=" * 50)
        print(f"\nDocumentatie Score: {result['documentatie_percentage']}%")
        print(f"\nFuncties: {result['functies_met_docstring']}/{result['functies_totaal']} met docstring")
        if result['functies_zonder_docstring']:
            print("  Zonder docstring:")
            for naam in result['functies_zonder_docstring'][:5]:
                print(f"    - {naam}()")
        print(f"\nKlassen: {result['klassen_met_docstring']}/{result['klassen_totaal']} met docstring")
        if result['klassen_zonder_docstring']:
            print("  Zonder docstring:")
            for naam in result['klassen_zonder_docstring']:
                print(f"    - {naam}")

    def _volledige_analyse(self):
        """Voer volledige analyse uit."""
        if not self.huidige_code:
            print("\nLaad eerst een bestand (optie 1)!")
            return

        print("\n" + "=" * 60)
        print("          VOLLEDIGE CODE ANALYSE")
        print("=" * 60)

        # Basis info
        result = self.analyseer_bestand(self.huidig_bestand)
        print(f"\n[BESTAND] {result['bestand']}")
        print(f"  {result['totaal_regels']} regels | {result['aantal_functies']} functies | {result['aantal_klassen']} klassen")

        # Complexity
        complexity = self.bereken_complexity()
        print(f"\n[COMPLEXITY]")
        print(f"  Cyclomatic: {complexity['cyclomatic_complexity']} ({complexity['complexity_rating']})")
        print(f"  Max Nesting: {complexity['max_nesting_depth']}")

        # Formatting
        formatting = self.check_formatting()
        print(f"\n[FORMATTING]")
        print(f"  Score: {formatting['score']}/100 ({formatting['totaal_problemen']} problemen)")

        # Documentatie
        docs = self.check_documentatie()
        print(f"\n[DOCUMENTATIE]")
        print(f"  Coverage: {docs['documentatie_percentage']}%")

        print("\n" + "=" * 60)

    def run(self):
        """Start de app."""
        clear_scherm()
        print("+" + "=" * 42 + "+")
        print("|        CODE ANALYSE TOOL                 |")
        print("|  Analyseer Python bestanden op:          |")
        print("|  - Structuur, Complexity, Formatting     |")
        print("|  - Documentatie coverage                 |")
        print("+" + "=" * 42 + "+")

        while True:
            self._toon_menu()
            keuze = input("\nKeuze: ").strip()

            if keuze == "0":
                break
            elif keuze == "1":
                self._laad_bestand()
            elif keuze == "2":
                self._toon_complexity()
            elif keuze == "3":
                self._toon_formatting()
            elif keuze == "4":
                self._fix_formatting()
            elif keuze == "5":
                self._toon_documentatie()
            elif keuze == "6":
                self._volledige_analyse()
            elif keuze == "7":
                invoer = input("Voer getallen in (gescheiden door spaties): ")
                try:
                    nummers = [float(x) for x in invoer.split()]
                    if nummers:
                        stats = self.bereken_statistieken(nummers)
                        print("\nResultaat:")
                        for k, v in stats.items():
                            if isinstance(v, float):
                                print(f"  {k}: {v:.2f}")
                            else:
                                print(f"  {k}: {v}")
                except ValueError:
                    print("Fout: voer geldige getallen in.")
            elif keuze == "8":
                tekst = input("Voer tekst in: ")
                if tekst:
                    telling = self.tel_woorden(tekst)
                    print(f"\nAantal unieke woorden: {len(telling)}")
                    top = Counter(telling).most_common(5)
                    print(f"Top 5: {top}")
            else:
                print("Ongeldige keuze.")

            input("\nDruk op Enter om verder te gaan...")

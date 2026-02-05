"""
Code Analyse App v2.0 - Professionele Python Code Analyzer.

Features:
- Bestandsanalyse met kleurrijke output
- Security vulnerability scanner
- Code smell detector
- Import analyzer (ongebruikt, circulair)
- Type hint coverage checker
- Dead code detector
- Performance pattern detector
- Multi-file project analyse
- Code metrics dashboard
- TODO/FIXME scanner
- Naming convention checker
- Analyse geschiedenis en export
"""

import re
import ast
import os
import json
import hashlib
from pathlib import Path
from datetime import datetime
from collections import Counter
from statistics import mean, median, stdev
from typing import List, Dict, Any, Optional, Set, Tuple

from ..core.utils import clear_scherm, kleur


class CodeAnalyseApp:
    """
    Professionele Python Code Analyzer v2.0.

    Analyseert Python code op:
    - Structuur en metrics
    - Security vulnerabilities
    - Code smells
    - Import problemen
    - Type hints coverage
    - Documentation coverage
    - Performance patterns
    - Naming conventions
    """

    VERSIE = "2.0"

    # Complexity keywords
    COMPLEXITY_KEYWORDS = [
        "if", "elif", "for", "while", "except",
        "with", "and", "or", "assert", "lambda"
    ]

    # Security patterns (regex patterns voor gevaarlijke code)
    SECURITY_PATTERNS = {
        "sql_injection": [
            (r'execute\s*\(\s*["\'].*%s', "Mogelijke SQL injection met %s formatting"),
            (r'execute\s*\(\s*f["\']', "Mogelijke SQL injection met f-string"),
            (r'execute\s*\(\s*["\'].*\+', "Mogelijke SQL injection met string concatenatie"),
        ],
        "command_injection": [
            (r'os\.system\s*\(', "os.system() is gevaarlijk - gebruik subprocess"),
            (r'subprocess\.call\s*\(\s*["\'].*\+', "Shell command injection risico"),
            (r'eval\s*\(', "eval() is gevaarlijk - vermijd indien mogelijk"),
            (r'exec\s*\(', "exec() is gevaarlijk - vermijd indien mogelijk"),
        ],
        "hardcoded_secrets": [
            (r'password\s*=\s*["\'][^"\']+["\']', "Hardcoded password gevonden"),
            (r'api_key\s*=\s*["\'][^"\']+["\']', "Hardcoded API key gevonden"),
            (r'secret\s*=\s*["\'][^"\']+["\']', "Hardcoded secret gevonden"),
            (r'token\s*=\s*["\'][A-Za-z0-9]{20,}["\']', "Mogelijke hardcoded token"),
        ],
        "xss_patterns": [
            (r'innerHTML\s*=', "Mogelijke XSS via innerHTML"),
            (r'\.html\s*\([^)]*\+', "Mogelijke XSS in HTML template"),
        ],
        "path_traversal": [
            (r'open\s*\([^)]*\+[^)]*\)', "Mogelijke path traversal in open()"),
            (r'Path\s*\([^)]*\+', "Mogelijke path traversal met Path"),
        ],
    }

    # Code smell patterns
    CODE_SMELL_PATTERNS = {
        "magic_numbers": r'(?<![a-zA-Z_])\d{2,}(?![a-zA-Z_\d])',
        "todo_fixme": r'#\s*(TODO|FIXME|XXX|HACK|BUG)',
        "print_debug": r'\bprint\s*\(.*(debug|test|xxx)',
        "commented_code": r'#\s*(def |class |import |from |if |for |while )',
    }

    # Naming convention patterns
    NAMING_CONVENTIONS = {
        "snake_case": r'^[a-z][a-z0-9_]*$',
        "UPPER_CASE": r'^[A-Z][A-Z0-9_]*$',
        "PascalCase": r'^[A-Z][a-zA-Z0-9]*$',
        "camelCase": r'^[a-z][a-zA-Z0-9]*$',
    }

    # Performance anti-patterns
    PERFORMANCE_PATTERNS = [
        (r'for\s+\w+\s+in\s+range\s*\(\s*len\s*\(',
         "Gebruik enumerate() in plaats van range(len())"),
        (r'\+\s*=\s*["\']',
         "String concatenatie in loop - gebruik join() of list"),
        (r'\.append\s*\([^)]+\)\s*$.*\.append',
         "Meerdere appends - overweeg list comprehension"),
        (r'time\.sleep\s*\(\s*0\s*\)',
         "sleep(0) is zinloos"),
        (r'== True\b|== False\b',
         "Vergelijk niet met True/False, gebruik direct de boolean"),
        (r'if\s+len\s*\([^)]+\)\s*==\s*0',
         "Gebruik 'if not seq:' in plaats van 'if len(seq) == 0'"),
        (r'if\s+len\s*\([^)]+\)\s*>\s*0',
         "Gebruik 'if seq:' in plaats van 'if len(seq) > 0'"),
    ]

    def __init__(self):
        self.huidig_bestand = None
        self.huidige_code = None
        self.huidige_tree = None

        # Data opslag
        self.data_bestand = Path.home() / ".danny_toolkit" / "code_analyse.json"
        self.data = self._laad_data()

    def _laad_data(self) -> Dict[str, Any]:
        """Laad opgeslagen data."""
        if self.data_bestand.exists():
            try:
                with open(self.data_bestand, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return self._migreer_data(data)
            except (json.JSONDecodeError, IOError):
                pass
        return self._standaard_data()

    def _standaard_data(self) -> Dict[str, Any]:
        """Standaard data structuur."""
        return {
            "versie": self.VERSIE,
            "analyses_totaal": 0,
            "bestanden_geanalyseerd": [],
            "analyse_geschiedenis": [],
            "favorieten": [],
            "statistieken": {
                "totaal_regels_geanalyseerd": 0,
                "security_issues_gevonden": 0,
                "code_smells_gevonden": 0,
                "fixes_toegepast": 0,
            },
            "instellingen": {
                "max_regel_lengte": 100,
                "min_docstring_coverage": 80,
                "strikt_naming": False,
            }
        }

    def _migreer_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Migreer oude data naar nieuwe structuur."""
        standaard = self._standaard_data()
        for key, value in standaard.items():
            if key not in data:
                data[key] = value
            elif isinstance(value, dict):
                for subkey, subvalue in value.items():
                    if subkey not in data[key]:
                        data[key][subkey] = subvalue
        data["versie"] = self.VERSIE
        return data

    def _sla_data_op(self):
        """Sla data op."""
        self.data_bestand.parent.mkdir(parents=True, exist_ok=True)
        with open(self.data_bestand, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    # ==================== BESTAND LADEN ====================

    def laad_bestand(self, pad: str) -> Dict[str, Any]:
        """Laad en parse een Python bestand."""
        path = Path(pad)

        if not path.exists():
            return {"fout": f"Bestand niet gevonden: {pad}"}
        if path.suffix != ".py":
            return {"fout": "Alleen Python bestanden (.py) worden ondersteund"}

        try:
            with open(path, "r", encoding="utf-8") as f:
                code = f.read()
        except UnicodeDecodeError:
            return {"fout": "Kan bestand niet lezen (encoding probleem)"}

        self.huidig_bestand = str(path.absolute())
        self.huidige_code = code

        # Parse AST
        try:
            self.huidige_tree = ast.parse(code)
        except SyntaxError as e:
            self.huidige_tree = None
            return {"fout": f"Syntax error op regel {e.lineno}: {e.msg}"}

        return {"succes": True, "bestand": path.name, "regels": len(code.split("\n"))}

    # ==================== BASIS ANALYSE ====================

    def analyseer_bestand(self, pad: str = None) -> Dict[str, Any]:
        """Analyseer een Python bestand volledig."""
        if pad:
            result = self.laad_bestand(pad)
            if "fout" in result:
                return result

        if not self.huidige_code:
            return {"fout": "Geen bestand geladen"}

        path = Path(self.huidig_bestand)
        code = self.huidige_code
        regels = code.split("\n")

        # Regel statistieken
        lege_regels = sum(1 for r in regels if not r.strip())
        comment_regels = sum(1 for r in regels if r.strip().startswith("#"))
        docstring_regels = len(re.findall(r'"""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\'', code))
        code_regels = len(regels) - lege_regels - comment_regels

        # AST analyse
        if self.huidige_tree:
            functies = [n for n in ast.walk(self.huidige_tree)
                       if isinstance(n, ast.FunctionDef)]
            async_functies = [n for n in ast.walk(self.huidige_tree)
                            if isinstance(n, ast.AsyncFunctionDef)]
            klassen = [n for n in ast.walk(self.huidige_tree)
                      if isinstance(n, ast.ClassDef)]
            imports = [n for n in ast.walk(self.huidige_tree)
                      if isinstance(n, (ast.Import, ast.ImportFrom))]

            # Import details
            import_namen = []
            for node in imports:
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        import_namen.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    for alias in node.names:
                        import_namen.append(f"{module}.{alias.name}")
        else:
            functies = async_functies = klassen = imports = []
            import_namen = []

        # Update statistieken
        self.data["analyses_totaal"] += 1
        self.data["statistieken"]["totaal_regels_geanalyseerd"] += len(regels)
        if str(path) not in self.data["bestanden_geanalyseerd"]:
            self.data["bestanden_geanalyseerd"].append(str(path))
        self._sla_data_op()

        return {
            "bestand": path.name,
            "pad": str(path.absolute()),
            "grootte_bytes": path.stat().st_size,
            "totaal_regels": len(regels),
            "code_regels": code_regels,
            "lege_regels": lege_regels,
            "comment_regels": comment_regels,
            "docstring_regels": docstring_regels,
            "aantal_functies": len(functies),
            "aantal_async_functies": len(async_functies),
            "functie_namen": [f.name for f in functies],
            "aantal_klassen": len(klassen),
            "klasse_namen": [k.name for k in klassen],
            "aantal_imports": len(imports),
            "import_namen": import_namen,
        }

    # ==================== COMPLEXITY ANALYSE ====================

    def bereken_complexity(self, code: str = None) -> Dict[str, Any]:
        """Bereken uitgebreide complexity metrics."""
        code = code or self.huidige_code
        if not code:
            return {"fout": "Geen code geladen"}

        regels = code.split("\n")

        # Cyclomatic complexity
        complexity = 1
        per_functie = {}
        huidige_functie = None

        for i, regel in enumerate(regels):
            stripped = regel.strip()

            # Track functies
            if stripped.startswith("def ") or stripped.startswith("async def "):
                match = re.match(r'(?:async\s+)?def\s+(\w+)', stripped)
                if match:
                    huidige_functie = match.group(1)
                    per_functie[huidige_functie] = 1

            # Tel complexity keywords
            for keyword in self.COMPLEXITY_KEYWORDS:
                pattern = rf'\b{keyword}\b'
                count = len(re.findall(pattern, stripped))
                complexity += count
                if huidige_functie and huidige_functie in per_functie:
                    per_functie[huidige_functie] += count

        # Nesting depth analyse
        max_nesting = 0
        nesting_per_regel = []
        for regel in regels:
            if regel.strip():
                indent = len(regel) - len(regel.lstrip())
                niveau = indent // 4
                nesting_per_regel.append(niveau)
                max_nesting = max(max_nesting, niveau)

        gem_nesting = mean(nesting_per_regel) if nesting_per_regel else 0

        # Regel lengtes
        niet_lege = [r for r in regels if r.strip()]
        gem_lengte = mean([len(r) for r in niet_lege]) if niet_lege else 0
        max_lengte = max([len(r) for r in regels]) if regels else 0

        # Lange regels
        max_regel = self.data["instellingen"]["max_regel_lengte"]
        lange_regels = [(i+1, len(r)) for i, r in enumerate(regels) if len(r) > max_regel]

        # Complexity per functie (top 5 hoogste)
        functie_complexity = sorted(
            per_functie.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]

        # Rating
        if complexity <= 5:
            rating = ("Eenvoudig", "groen")
        elif complexity <= 10:
            rating = ("Matig", "geel")
        elif complexity <= 20:
            rating = ("Complex", "oranje")
        else:
            rating = ("Zeer Complex", "rood")

        # Maintainability index (vereenvoudigd)
        # MI = 171 - 5.2 * ln(V) - 0.23 * G - 16.2 * ln(LOC)
        import math
        loc = len(niet_lege)
        halstead_v = loc * math.log2(max(complexity, 1) + 1)  # Vereenvoudigd
        mi = 171 - 5.2 * math.log(halstead_v + 1) - 0.23 * complexity - 16.2 * math.log(loc + 1)
        mi = max(0, min(100, mi))

        return {
            "cyclomatic_complexity": complexity,
            "complexity_rating": rating[0],
            "rating_kleur": rating[1],
            "max_nesting_depth": max_nesting,
            "gemiddelde_nesting": round(gem_nesting, 2),
            "gemiddelde_regel_lengte": round(gem_lengte, 1),
            "max_regel_lengte": max_lengte,
            "lange_regels_count": len(lange_regels),
            "lange_regels": lange_regels[:10],
            "functie_complexity": functie_complexity,
            "maintainability_index": round(mi, 1),
        }

    # ==================== SECURITY SCANNER ====================

    def scan_security(self, code: str = None) -> Dict[str, Any]:
        """Scan code voor security vulnerabilities."""
        code = code or self.huidige_code
        if not code:
            return {"fout": "Geen code geladen"}

        regels = code.split("\n")
        issues = []

        for categorie, patterns in self.SECURITY_PATTERNS.items():
            for pattern, beschrijving in patterns:
                for i, regel in enumerate(regels):
                    if re.search(pattern, regel, re.IGNORECASE):
                        issues.append({
                            "regel": i + 1,
                            "categorie": categorie,
                            "ernst": "hoog" if "injection" in categorie else "medium",
                            "beschrijving": beschrijving,
                            "code": regel.strip()[:60],
                        })

        # Update statistieken
        self.data["statistieken"]["security_issues_gevonden"] += len(issues)
        self._sla_data_op()

        # Categoriseer
        per_categorie = {}
        for issue in issues:
            cat = issue["categorie"]
            if cat not in per_categorie:
                per_categorie[cat] = 0
            per_categorie[cat] += 1

        # Security score (100 - penalties)
        score = 100
        for issue in issues:
            if issue["ernst"] == "hoog":
                score -= 15
            else:
                score -= 5
        score = max(0, score)

        return {
            "totaal_issues": len(issues),
            "issues": issues,
            "per_categorie": per_categorie,
            "security_score": score,
            "aanbevelingen": self._security_aanbevelingen(issues),
        }

    def _security_aanbevelingen(self, issues: List[Dict]) -> List[str]:
        """Genereer security aanbevelingen."""
        aanbevelingen = []
        categorieën = set(i["categorie"] for i in issues)

        if "sql_injection" in categorieën:
            aanbevelingen.append(
                "Gebruik parameterized queries of ORM in plaats van string formatting"
            )
        if "command_injection" in categorieën:
            aanbevelingen.append(
                "Gebruik subprocess.run() met shell=False en lijst van argumenten"
            )
        if "hardcoded_secrets" in categorieën:
            aanbevelingen.append(
                "Gebruik environment variables of een secrets manager"
            )
        if "xss_patterns" in categorieën:
            aanbevelingen.append(
                "Sanitize alle user input voordat het in HTML wordt geplaatst"
            )
        if "path_traversal" in categorieën:
            aanbevelingen.append(
                "Valideer en sanitize bestandspaden, gebruik Path.resolve()"
            )

        return aanbevelingen

    # ==================== CODE SMELL DETECTOR ====================

    def detect_code_smells(self, code: str = None) -> Dict[str, Any]:
        """Detecteer code smells en anti-patterns."""
        code = code or self.huidige_code
        if not code:
            return {"fout": "Geen code geladen"}

        regels = code.split("\n")
        smells = []

        # Magic numbers
        for i, regel in enumerate(regels):
            if not regel.strip().startswith("#"):
                numbers = re.findall(self.CODE_SMELL_PATTERNS["magic_numbers"], regel)
                for num in numbers:
                    if int(num) not in [0, 1, 2, 100, 1000]:  # Veelvoorkomende OK nummers
                        smells.append({
                            "regel": i + 1,
                            "type": "magic_number",
                            "beschrijving": f"Magic number {num} - gebruik een constante",
                        })

        # TODO/FIXME comments
        for i, regel in enumerate(regels):
            if re.search(self.CODE_SMELL_PATTERNS["todo_fixme"], regel, re.IGNORECASE):
                match = re.search(r'#\s*(TODO|FIXME|XXX|HACK|BUG):?\s*(.*)',
                                regel, re.IGNORECASE)
                smells.append({
                    "regel": i + 1,
                    "type": "todo_fixme",
                    "beschrijving": f"{match.group(1)}: {match.group(2)[:40]}" if match else "TODO gevonden",
                })

        # Commented out code
        for i, regel in enumerate(regels):
            if re.search(self.CODE_SMELL_PATTERNS["commented_code"], regel):
                smells.append({
                    "regel": i + 1,
                    "type": "commented_code",
                    "beschrijving": "Uitgecommentarieerde code - verwijder of herstel",
                })

        # Lange functies (AST analyse)
        if self.huidige_tree:
            for node in ast.walk(self.huidige_tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    func_lines = node.end_lineno - node.lineno if hasattr(node, 'end_lineno') else 0
                    if func_lines > 50:
                        smells.append({
                            "regel": node.lineno,
                            "type": "lange_functie",
                            "beschrijving": f"Functie '{node.name}' is {func_lines} regels (max 50)",
                        })

                    # Te veel parameters
                    if len(node.args.args) > 5:
                        smells.append({
                            "regel": node.lineno,
                            "type": "te_veel_parameters",
                            "beschrijving": f"Functie '{node.name}' heeft {len(node.args.args)} parameters (max 5)",
                        })

        # Duplicate string literals
        string_literals = re.findall(r'["\']([^"\']{10,})["\']', code)
        duplicates = [s for s, count in Counter(string_literals).items() if count > 2]
        for dup in duplicates[:5]:
            smells.append({
                "regel": 0,
                "type": "duplicate_string",
                "beschrijving": f"String '{dup[:30]}...' komt meerdere keren voor",
            })

        # Update statistieken
        self.data["statistieken"]["code_smells_gevonden"] += len(smells)
        self._sla_data_op()

        # Per type
        per_type = {}
        for smell in smells:
            t = smell["type"]
            if t not in per_type:
                per_type[t] = 0
            per_type[t] += 1

        return {
            "totaal_smells": len(smells),
            "smells": smells,
            "per_type": per_type,
        }

    # ==================== IMPORT ANALYZER ====================

    def analyseer_imports(self, code: str = None) -> Dict[str, Any]:
        """Analyseer imports op problemen."""
        code = code or self.huidige_code
        if not code or not self.huidige_tree:
            return {"fout": "Geen code geladen"}

        # Verzamel alle imports
        imports = []
        for node in ast.walk(self.huidige_tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append({
                        "module": alias.name,
                        "alias": alias.asname,
                        "regel": node.lineno,
                        "type": "import",
                    })
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    imports.append({
                        "module": f"{node.module}.{alias.name}" if node.module else alias.name,
                        "alias": alias.asname,
                        "regel": node.lineno,
                        "type": "from_import",
                    })

        # Zoek gebruikte namen in code
        namen_in_code = set(re.findall(r'\b([a-zA-Z_]\w*)\b', code))

        # Check ongebruikte imports
        ongebruikt = []
        for imp in imports:
            naam = imp["alias"] or imp["module"].split(".")[-1]
            if naam not in namen_in_code and naam != "*":
                ongebruikt.append(imp)

        # Check import volgorde (standaard, third-party, lokaal)
        import_volgorde_ok = True
        vorige_type = None
        for imp in imports:
            module = imp["module"].split(".")[0]
            # Simpele check: stdlib modules zijn meestal lowercase zonder underscore
            # Dit is een vereenvoudiging
            if vorige_type == "local" and module in ["os", "sys", "re", "json"]:
                import_volgorde_ok = False
                break

        # Duplicate imports
        module_namen = [i["module"] for i in imports]
        duplicates = [m for m, c in Counter(module_namen).items() if c > 1]

        return {
            "totaal_imports": len(imports),
            "imports": imports,
            "ongebruikte_imports": ongebruikt,
            "duplicate_imports": duplicates,
            "import_volgorde_ok": import_volgorde_ok,
        }

    # ==================== TYPE HINT COVERAGE ====================

    def check_type_hints(self, code: str = None) -> Dict[str, Any]:
        """Check type hint coverage."""
        code = code or self.huidige_code
        if not code or not self.huidige_tree:
            return {"fout": "Geen code geladen"}

        functies = []

        for node in ast.walk(self.huidige_tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Check return type
                heeft_return_type = node.returns is not None

                # Check argument types
                args_totaal = len(node.args.args)
                args_met_type = sum(1 for arg in node.args.args if arg.annotation)

                # Skip self/cls
                if args_totaal > 0 and node.args.args[0].arg in ["self", "cls"]:
                    args_totaal -= 1
                    if node.args.args[0].annotation:
                        args_met_type -= 1

                functies.append({
                    "naam": node.name,
                    "regel": node.lineno,
                    "heeft_return_type": heeft_return_type,
                    "args_totaal": args_totaal,
                    "args_met_type": args_met_type,
                    "volledig_getypt": heeft_return_type and args_met_type == args_totaal,
                })

        # Bereken coverage
        volledig_getypt = sum(1 for f in functies if f["volledig_getypt"])
        coverage = (volledig_getypt / len(functies) * 100) if functies else 100

        # Functies zonder types
        zonder_types = [f for f in functies if not f["volledig_getypt"]]

        return {
            "functies_totaal": len(functies),
            "volledig_getypt": volledig_getypt,
            "type_coverage": round(coverage, 1),
            "functies_zonder_types": zonder_types[:10],
        }

    # ==================== DOCUMENTATIE CHECKER ====================

    def check_documentatie(self, code: str = None) -> Dict[str, Any]:
        """Check documentatie coverage."""
        code = code or self.huidige_code
        if not code or not self.huidige_tree:
            return {"fout": "Geen code geladen"}

        resultaten = {
            "module_docstring": ast.get_docstring(self.huidige_tree) is not None,
            "functies_totaal": 0,
            "functies_met_docstring": 0,
            "functies_zonder_docstring": [],
            "klassen_totaal": 0,
            "klassen_met_docstring": 0,
            "klassen_zonder_docstring": [],
        }

        for node in ast.walk(self.huidige_tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                resultaten["functies_totaal"] += 1
                if ast.get_docstring(node):
                    resultaten["functies_met_docstring"] += 1
                else:
                    # Skip private functies (_ prefix)
                    if not node.name.startswith("_"):
                        resultaten["functies_zonder_docstring"].append({
                            "naam": node.name,
                            "regel": node.lineno,
                        })

            elif isinstance(node, ast.ClassDef):
                resultaten["klassen_totaal"] += 1
                if ast.get_docstring(node):
                    resultaten["klassen_met_docstring"] += 1
                else:
                    resultaten["klassen_zonder_docstring"].append({
                        "naam": node.name,
                        "regel": node.lineno,
                    })

        # Bereken percentage
        totaal = resultaten["functies_totaal"] + resultaten["klassen_totaal"]
        met_doc = resultaten["functies_met_docstring"] + resultaten["klassen_met_docstring"]
        resultaten["documentatie_percentage"] = round(
            (met_doc / totaal * 100) if totaal > 0 else 100, 1
        )

        return resultaten

    # ==================== PERFORMANCE PATTERNS ====================

    def check_performance(self, code: str = None) -> Dict[str, Any]:
        """Check voor performance anti-patterns."""
        code = code or self.huidige_code
        if not code:
            return {"fout": "Geen code geladen"}

        regels = code.split("\n")
        issues = []

        for pattern, beschrijving in self.PERFORMANCE_PATTERNS:
            for i, regel in enumerate(regels):
                if re.search(pattern, regel):
                    issues.append({
                        "regel": i + 1,
                        "beschrijving": beschrijving,
                        "code": regel.strip()[:50],
                    })

        # Check list comprehension mogelijkheden
        for i, regel in enumerate(regels):
            if "for " in regel and ".append(" in regel:
                issues.append({
                    "regel": i + 1,
                    "beschrijving": "Overweeg list comprehension in plaats van append in loop",
                    "code": regel.strip()[:50],
                })

        return {
            "totaal_issues": len(issues),
            "issues": issues,
        }

    # ==================== NAMING CONVENTIONS ====================

    def check_naming(self, code: str = None) -> Dict[str, Any]:
        """Check naming conventions."""
        code = code or self.huidige_code
        if not code or not self.huidige_tree:
            return {"fout": "Geen code geladen"}

        problemen = []

        for node in ast.walk(self.huidige_tree):
            # Functies moeten snake_case zijn
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if not re.match(self.NAMING_CONVENTIONS["snake_case"], node.name):
                    if not node.name.startswith("_"):  # Dunder methods OK
                        problemen.append({
                            "regel": node.lineno,
                            "naam": node.name,
                            "type": "functie",
                            "verwacht": "snake_case",
                        })

            # Klassen moeten PascalCase zijn
            elif isinstance(node, ast.ClassDef):
                if not re.match(self.NAMING_CONVENTIONS["PascalCase"], node.name):
                    problemen.append({
                        "regel": node.lineno,
                        "naam": node.name,
                        "type": "klasse",
                        "verwacht": "PascalCase",
                    })

            # Constanten (UPPER_CASE) - module niveau assignments
            elif isinstance(node, ast.Assign):
                if hasattr(node, 'lineno'):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            naam = target.id
                            # Als het allemaal hoofdletters zou moeten zijn
                            if naam.isupper() and not re.match(
                                self.NAMING_CONVENTIONS["UPPER_CASE"], naam
                            ):
                                problemen.append({
                                    "regel": node.lineno,
                                    "naam": naam,
                                    "type": "constante",
                                    "verwacht": "UPPER_CASE",
                                })

        return {
            "totaal_problemen": len(problemen),
            "problemen": problemen,
            "naming_score": max(0, 100 - len(problemen) * 5),
        }

    # ==================== FORMATTING ====================

    def check_formatting(self, code: str = None) -> Dict[str, Any]:
        """Check code formatting issues."""
        code = code or self.huidige_code
        if not code:
            return {"fout": "Geen code geladen"}

        regels = code.split("\n")
        problemen = []
        max_lengte = self.data["instellingen"]["max_regel_lengte"]

        for i, regel in enumerate(regels, 1):
            # Trailing whitespace
            if regel != regel.rstrip():
                problemen.append({
                    "regel": i,
                    "type": "trailing_whitespace",
                    "beschrijving": "Trailing whitespace",
                })

            # Tabs
            if "\t" in regel:
                problemen.append({
                    "regel": i,
                    "type": "tabs",
                    "beschrijving": "Tab gevonden (gebruik 4 spaties)",
                })

            # Te lange regel
            if len(regel) > max_lengte:
                problemen.append({
                    "regel": i,
                    "type": "te_lang",
                    "beschrijving": f"Regel te lang ({len(regel)} > {max_lengte})",
                })

            # Meerdere statements op een regel
            if ";" in regel and not regel.strip().startswith("#"):
                problemen.append({
                    "regel": i,
                    "type": "meerdere_statements",
                    "beschrijving": "Meerdere statements op een regel",
                })

        # Lege regels aan begin/eind
        if regels and not regels[0].strip():
            problemen.append({
                "regel": 1,
                "type": "lege_regel_begin",
                "beschrijving": "Lege regel aan begin van bestand",
            })

        if regels and len(regels) > 1 and not regels[-1].strip() and not regels[-2].strip():
            problemen.append({
                "regel": len(regels),
                "type": "lege_regels_eind",
                "beschrijving": "Meerdere lege regels aan eind van bestand",
            })

        return {
            "totaal_problemen": len(problemen),
            "problemen": problemen[:20],
            "score": max(0, 100 - len(problemen) * 3),
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

        # Skip lege regels aan begin
        start_idx = 0
        while start_idx < len(regels) and not regels[start_idx].strip():
            start_idx += 1

        for regel in regels[start_idx:]:
            # Fix tabs naar 4 spaties
            regel = regel.replace("\t", "    ")

            # Fix trailing whitespace
            regel = regel.rstrip()

            # Beperk lege regels tot max 2
            is_leeg = not regel.strip()
            if is_leeg:
                if dubbel_leeg:
                    continue
                if vorige_leeg:
                    dubbel_leeg = True
            else:
                dubbel_leeg = False

            gefixte_regels.append(regel)
            vorige_leeg = is_leeg

        # Verwijder trailing lege regels, houd 1
        while len(gefixte_regels) > 1 and not gefixte_regels[-1].strip():
            gefixte_regels.pop()

        if gefixte_regels and gefixte_regels[-1].strip():
            gefixte_regels.append("")  # Een lege regel aan eind

        self.data["statistieken"]["fixes_toegepast"] += 1
        self._sla_data_op()

        return "\n".join(gefixte_regels)

    # ==================== PROJECT ANALYSE ====================

    def analyseer_project(self, pad: str = ".") -> Dict[str, Any]:
        """Analyseer een heel Python project."""
        project_path = Path(pad)

        if not project_path.exists():
            return {"fout": f"Map niet gevonden: {pad}"}

        # Vind alle Python bestanden
        py_bestanden = list(project_path.rglob("*.py"))

        # Filter __pycache__ en venv
        py_bestanden = [
            f for f in py_bestanden
            if "__pycache__" not in str(f)
            and "venv" not in str(f)
            and ".venv" not in str(f)
            and "site-packages" not in str(f)
        ]

        if not py_bestanden:
            return {"fout": "Geen Python bestanden gevonden"}

        resultaten = {
            "project": project_path.name,
            "totaal_bestanden": len(py_bestanden),
            "totaal_regels": 0,
            "totaal_functies": 0,
            "totaal_klassen": 0,
            "bestanden": [],
            "security_issues": 0,
            "code_smells": 0,
        }

        for bestand in py_bestanden[:50]:  # Max 50 bestanden
            self.laad_bestand(str(bestand))
            if self.huidige_code:
                analyse = self.analyseer_bestand()
                if "fout" not in analyse:
                    resultaten["totaal_regels"] += analyse["totaal_regels"]
                    resultaten["totaal_functies"] += analyse["aantal_functies"]
                    resultaten["totaal_klassen"] += analyse["aantal_klassen"]
                    resultaten["bestanden"].append({
                        "naam": analyse["bestand"],
                        "regels": analyse["totaal_regels"],
                    })

                # Security scan
                security = self.scan_security()
                resultaten["security_issues"] += security.get("totaal_issues", 0)

                # Code smells
                smells = self.detect_code_smells()
                resultaten["code_smells"] += smells.get("totaal_smells", 0)

        # Sorteer bestanden op grootte
        resultaten["bestanden"].sort(key=lambda x: x["regels"], reverse=True)
        resultaten["grootste_bestanden"] = resultaten["bestanden"][:10]

        return resultaten

    # ==================== RAPPORT GENERATIE ====================

    def genereer_rapport(self, formaat: str = "txt") -> str:
        """Genereer een volledig analyse rapport."""
        if not self.huidige_code:
            return "Geen bestand geladen"

        # Verzamel alle analyses
        basis = self.analyseer_bestand()
        complexity = self.bereken_complexity()
        security = self.scan_security()
        smells = self.detect_code_smells()
        imports = self.analyseer_imports()
        types = self.check_type_hints()
        docs = self.check_documentatie()
        formatting = self.check_formatting()
        naming = self.check_naming()
        performance = self.check_performance()

        if formaat == "json":
            return json.dumps({
                "basis": basis,
                "complexity": complexity,
                "security": security,
                "code_smells": smells,
                "imports": imports,
                "type_hints": types,
                "documentatie": docs,
                "formatting": formatting,
                "naming": naming,
                "performance": performance,
                "gegenereerd": datetime.now().isoformat(),
            }, indent=2, ensure_ascii=False)

        elif formaat == "html":
            return self._genereer_html_rapport(
                basis, complexity, security, smells, imports,
                types, docs, formatting, naming, performance
            )

        else:  # txt
            return self._genereer_txt_rapport(
                basis, complexity, security, smells, imports,
                types, docs, formatting, naming, performance
            )

    def _genereer_txt_rapport(self, basis, complexity, security, smells,
                              imports, types, docs, formatting, naming, performance) -> str:
        """Genereer tekst rapport."""
        lijnen = [
            "=" * 60,
            "        CODE ANALYSE RAPPORT",
            "=" * 60,
            f"Bestand: {basis.get('bestand', 'Onbekend')}",
            f"Gegenereerd: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            "-" * 40,
            "BASIS INFORMATIE",
            "-" * 40,
            f"Totaal regels:     {basis.get('totaal_regels', 0)}",
            f"Code regels:       {basis.get('code_regels', 0)}",
            f"Functies:          {basis.get('aantal_functies', 0)}",
            f"Klassen:           {basis.get('aantal_klassen', 0)}",
            f"Imports:           {basis.get('aantal_imports', 0)}",
            "",
            "-" * 40,
            "COMPLEXITY",
            "-" * 40,
            f"Cyclomatic:        {complexity.get('cyclomatic_complexity', 0)}",
            f"Rating:            {complexity.get('complexity_rating', 'Onbekend')}",
            f"Max Nesting:       {complexity.get('max_nesting_depth', 0)}",
            f"Maintainability:   {complexity.get('maintainability_index', 0)}",
            "",
            "-" * 40,
            "SECURITY",
            "-" * 40,
            f"Issues gevonden:   {security.get('totaal_issues', 0)}",
            f"Security Score:    {security.get('security_score', 100)}/100",
            "",
            "-" * 40,
            "CODE QUALITY",
            "-" * 40,
            f"Code Smells:       {smells.get('totaal_smells', 0)}",
            f"Type Coverage:     {types.get('type_coverage', 0)}%",
            f"Doc Coverage:      {docs.get('documentatie_percentage', 0)}%",
            f"Formatting Score:  {formatting.get('score', 0)}/100",
            f"Naming Score:      {naming.get('naming_score', 0)}/100",
            f"Perf Issues:       {performance.get('totaal_issues', 0)}",
            "",
            "-" * 40,
            "IMPORTS",
            "-" * 40,
            f"Totaal:            {imports.get('totaal_imports', 0)}",
            f"Ongebruikt:        {len(imports.get('ongebruikte_imports', []))}",
            "",
            "=" * 60,
        ]

        return "\n".join(lijnen)

    def _genereer_html_rapport(self, basis, complexity, security, smells,
                               imports, types, docs, formatting, naming, performance) -> str:
        """Genereer HTML rapport."""
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Code Analyse Rapport - {basis.get('bestand', 'Onbekend')}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 900px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; border-bottom: 2px solid #4CAF50; padding-bottom: 10px; }}
        h2 {{ color: #666; margin-top: 30px; }}
        .metric {{ display: inline-block; background: #e8f5e9; padding: 10px 20px; margin: 5px; border-radius: 4px; }}
        .metric.warning {{ background: #fff3e0; }}
        .metric.danger {{ background: #ffebee; }}
        .score {{ font-size: 24px; font-weight: bold; color: #4CAF50; }}
        .score.warning {{ color: #ff9800; }}
        .score.danger {{ color: #f44336; }}
        table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
        th, td {{ padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background: #f5f5f5; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Code Analyse Rapport</h1>
        <p><strong>Bestand:</strong> {basis.get('bestand', 'Onbekend')}</p>
        <p><strong>Gegenereerd:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>

        <h2>Overzicht</h2>
        <div class="metric"><span class="score">{basis.get('totaal_regels', 0)}</span><br>Regels</div>
        <div class="metric"><span class="score">{basis.get('aantal_functies', 0)}</span><br>Functies</div>
        <div class="metric"><span class="score">{basis.get('aantal_klassen', 0)}</span><br>Klassen</div>

        <h2>Scores</h2>
        <div class="metric {'warning' if security.get('security_score', 100) < 80 else ''}">
            <span class="score {'warning' if security.get('security_score', 100) < 80 else ''}">{security.get('security_score', 100)}</span><br>Security
        </div>
        <div class="metric {'warning' if formatting.get('score', 100) < 80 else ''}">
            <span class="score">{formatting.get('score', 100)}</span><br>Formatting
        </div>
        <div class="metric">
            <span class="score">{docs.get('documentatie_percentage', 0)}%</span><br>Documentatie
        </div>
        <div class="metric">
            <span class="score">{types.get('type_coverage', 0)}%</span><br>Type Hints
        </div>

        <h2>Complexity</h2>
        <table>
            <tr><th>Metric</th><th>Waarde</th></tr>
            <tr><td>Cyclomatic Complexity</td><td>{complexity.get('cyclomatic_complexity', 0)}</td></tr>
            <tr><td>Rating</td><td>{complexity.get('complexity_rating', 'Onbekend')}</td></tr>
            <tr><td>Max Nesting</td><td>{complexity.get('max_nesting_depth', 0)}</td></tr>
            <tr><td>Maintainability Index</td><td>{complexity.get('maintainability_index', 0)}</td></tr>
        </table>

        <h2>Issues</h2>
        <table>
            <tr><th>Type</th><th>Aantal</th></tr>
            <tr><td>Security Issues</td><td>{security.get('totaal_issues', 0)}</td></tr>
            <tr><td>Code Smells</td><td>{smells.get('totaal_smells', 0)}</td></tr>
            <tr><td>Ongebruikte Imports</td><td>{len(imports.get('ongebruikte_imports', []))}</td></tr>
            <tr><td>Performance Issues</td><td>{performance.get('totaal_issues', 0)}</td></tr>
            <tr><td>Naming Issues</td><td>{naming.get('totaal_problemen', 0)}</td></tr>
        </table>
    </div>
</body>
</html>"""
        return html

    def bewaar_analyse(self):
        """Bewaar huidige analyse in geschiedenis."""
        if not self.huidige_code:
            return

        # Genereer hash van code
        code_hash = hashlib.md5(self.huidige_code.encode()).hexdigest()[:8]

        analyse = {
            "bestand": Path(self.huidig_bestand).name if self.huidig_bestand else "onbekend",
            "datum": datetime.now().isoformat(),
            "hash": code_hash,
            "regels": len(self.huidige_code.split("\n")),
            "complexity": self.bereken_complexity().get("cyclomatic_complexity", 0),
            "security_score": self.scan_security().get("security_score", 100),
            "doc_coverage": self.check_documentatie().get("documentatie_percentage", 0),
        }

        self.data["analyse_geschiedenis"].append(analyse)
        # Houd max 50 analyses
        self.data["analyse_geschiedenis"] = self.data["analyse_geschiedenis"][-50:]
        self._sla_data_op()

    # ==================== STATISTIEK FUNCTIES ====================

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
        """Toont het hoofdmenu met kleuren."""
        print()
        print(kleur("+" + "=" * 50 + "+", "cyaan"))
        print(kleur("|       CODE ANALYSE TOOL v2.0                     |", "cyaan"))
        print(kleur("+" + "=" * 50 + "+", "cyaan"))
        print(kleur("| ANALYSE                                          |", "wit"))
        print("|  1. Analyseer Python bestand                     |")
        print("|  2. Analyseer project (meerdere bestanden)       |")
        print("|  3. Volledige analyse (huidig bestand)           |")
        print(kleur("+" + "-" * 50 + "+", "grijs"))
        print(kleur("| KWALITEIT                                        |", "wit"))
        print("|  4. Security scan                                |")
        print("|  5. Code smell detector                          |")
        print("|  6. Complexity analyse                           |")
        print("|  7. Performance check                            |")
        print("|  8. Duplicate code detector                      |")
        print(kleur("+" + "-" * 50 + "+", "grijs"))
        print(kleur("| STIJL                                            |", "wit"))
        print("|  9. Formatting check/fix                         |")
        print("| 10. Naming conventions                           |")
        print("| 11. Documentatie coverage                        |")
        print("| 12. Type hint coverage                           |")
        print("| 13. Import analyse                               |")
        print(kleur("+" + "-" * 50 + "+", "grijs"))
        print(kleur("| RAPPORT                                          |", "wit"))
        print("| 14. Genereer rapport (TXT/JSON/HTML)             |")
        print("| 15. Bekijk analyse geschiedenis                  |")
        print("| 16. Statistieken                                 |")
        print(kleur("+" + "-" * 50 + "+", "grijs"))
        print(kleur("| TOOLS                                            |", "wit"))
        print("| 17. Woordtelling                                 |")
        print("| 18. Getallen statistieken                        |")
        print(kleur("+" + "-" * 50 + "+", "grijs"))
        print("|  0. Terug naar hoofdmenu                         |")
        print(kleur("+" + "=" * 50 + "+", "cyaan"))

        if self.huidig_bestand:
            print(kleur(f"  Geladen: {Path(self.huidig_bestand).name}", "groen"))

    def _laad_bestand_interactief(self):
        """Vraag gebruiker om bestand te laden."""
        print("\n" + kleur("BESTAND LADEN", "cyaan"))
        print("-" * 40)
        print("Voer het pad naar een Python bestand in:")
        print(kleur("(Tip: gebruik relatief pad zoals 'main.py')", "grijs"))

        pad = input("\nPad: ").strip()
        if not pad:
            print(kleur("Geen pad ingevoerd.", "rood"))
            return

        resultaat = self.laad_bestand(pad)

        if "fout" in resultaat:
            print(kleur(f"\nFout: {resultaat['fout']}", "rood"))
            return

        # Toon basis analyse
        analyse = self.analyseer_bestand()

        print("\n" + kleur("BESTANDSANALYSE", "groen"))
        print("=" * 50)
        print(f"\nBestand: {kleur(analyse['bestand'], 'cyaan')}")
        print(f"Grootte: {analyse['grootte_bytes']:,} bytes")
        print(f"\n{kleur('Regels:', 'geel')}")
        print(f"  Totaal:    {analyse['totaal_regels']}")
        print(f"  Code:      {analyse['code_regels']}")
        print(f"  Comments:  {analyse['comment_regels']}")
        print(f"  Leeg:      {analyse['lege_regels']}")
        print(f"\n{kleur('Structuur:', 'geel')}")
        print(f"  Klassen:   {analyse['aantal_klassen']}")
        if analyse['klasse_namen']:
            for naam in analyse['klasse_namen'][:5]:
                print(f"             - {naam}")
        print(f"  Functies:  {analyse['aantal_functies']}")
        if analyse['functie_namen']:
            for naam in analyse['functie_namen'][:8]:
                print(f"             - {naam}")
            if len(analyse['functie_namen']) > 8:
                print(f"             ... en {len(analyse['functie_namen'])-8} meer")
        print(f"  Imports:   {analyse['aantal_imports']}")

        # Bewaar in geschiedenis
        self.bewaar_analyse()

    def _toon_project_analyse(self):
        """Analyseer een project."""
        print("\n" + kleur("PROJECT ANALYSE", "cyaan"))
        print("-" * 40)
        print("Voer het pad naar een project map in:")
        print(kleur("(Laat leeg voor huidige map)", "grijs"))

        pad = input("\nPad: ").strip() or "."

        print(kleur("\nProject wordt geanalyseerd...", "geel"))
        resultaat = self.analyseer_project(pad)

        if "fout" in resultaat:
            print(kleur(f"\nFout: {resultaat['fout']}", "rood"))
            return

        print("\n" + kleur("PROJECT OVERZICHT", "groen"))
        print("=" * 50)
        print(f"\nProject: {kleur(resultaat['project'], 'cyaan')}")
        print(f"\n{kleur('Statistieken:', 'geel')}")
        print(f"  Python bestanden: {resultaat['totaal_bestanden']}")
        print(f"  Totaal regels:    {resultaat['totaal_regels']:,}")
        print(f"  Totaal functies:  {resultaat['totaal_functies']}")
        print(f"  Totaal klassen:   {resultaat['totaal_klassen']}")

        print(f"\n{kleur('Kwaliteit:', 'geel')}")
        print(f"  Security issues:  {resultaat['security_issues']}")
        print(f"  Code smells:      {resultaat['code_smells']}")

        print(f"\n{kleur('Grootste bestanden:', 'geel')}")
        for i, bestand in enumerate(resultaat['grootste_bestanden'][:5], 1):
            print(f"  {i}. {bestand['naam']}: {bestand['regels']} regels")

    def _toon_volledige_analyse(self):
        """Voer volledige analyse uit."""
        if not self.huidige_code:
            print(kleur("\nLaad eerst een bestand (optie 1)!", "rood"))
            return

        print("\n" + kleur("VOLLEDIGE CODE ANALYSE", "cyaan"))
        print("=" * 60)

        # Basis info
        basis = self.analyseer_bestand()
        print(f"\n{kleur('[BESTAND]', 'geel')} {basis['bestand']}")
        print(f"  {basis['totaal_regels']} regels | {basis['aantal_functies']} functies | {basis['aantal_klassen']} klassen")

        # Complexity
        complexity = self.bereken_complexity()
        rating_kleur = {
            "Eenvoudig": "groen", "Matig": "geel",
            "Complex": "oranje", "Zeer Complex": "rood"
        }.get(complexity['complexity_rating'], "wit")
        print(f"\n{kleur('[COMPLEXITY]', 'geel')}")
        print(f"  Cyclomatic: {complexity['cyclomatic_complexity']} ({kleur(complexity['complexity_rating'], rating_kleur)})")
        print(f"  Max Nesting: {complexity['max_nesting_depth']}")
        print(f"  Maintainability Index: {complexity['maintainability_index']}")

        # Security
        security = self.scan_security()
        sec_kleur = "groen" if security['security_score'] >= 80 else "rood"
        print(f"\n{kleur('[SECURITY]', 'geel')}")
        print(f"  Score: {kleur(str(security['security_score']) + '/100', sec_kleur)}")
        print(f"  Issues: {security['totaal_issues']}")

        # Code smells
        smells = self.detect_code_smells()
        print(f"\n{kleur('[CODE SMELLS]', 'geel')}")
        print(f"  Gevonden: {smells['totaal_smells']}")

        # Documentation
        docs = self.check_documentatie()
        doc_kleur = "groen" if docs['documentatie_percentage'] >= 80 else "geel"
        print(f"\n{kleur('[DOCUMENTATIE]', 'geel')}")
        print(f"  Coverage: {kleur(str(docs['documentatie_percentage']) + '%', doc_kleur)}")

        # Type hints
        types = self.check_type_hints()
        print(f"\n{kleur('[TYPE HINTS]', 'geel')}")
        print(f"  Coverage: {types['type_coverage']}%")

        # Formatting
        formatting = self.check_formatting()
        fmt_kleur = "groen" if formatting['score'] >= 80 else "geel"
        print(f"\n{kleur('[FORMATTING]', 'geel')}")
        print(f"  Score: {kleur(str(formatting['score']) + '/100', fmt_kleur)} ({formatting['totaal_problemen']} problemen)")

        # Performance
        perf = self.check_performance()
        print(f"\n{kleur('[PERFORMANCE]', 'geel')}")
        print(f"  Issues: {perf['totaal_issues']}")

        print("\n" + "=" * 60)

    def _toon_security_scan(self):
        """Toon security scan resultaten."""
        if not self.huidige_code:
            print(kleur("\nLaad eerst een bestand (optie 1)!", "rood"))
            return

        result = self.scan_security()

        print("\n" + kleur("SECURITY SCAN", "cyaan"))
        print("=" * 50)

        score_kleur = "groen" if result['security_score'] >= 80 else "rood"
        print(f"\nSecurity Score: {kleur(str(result['security_score']) + '/100', score_kleur)}")
        print(f"Issues gevonden: {result['totaal_issues']}")

        if result['per_categorie']:
            print(f"\n{kleur('Per categorie:', 'geel')}")
            for cat, count in result['per_categorie'].items():
                print(f"  {cat}: {count}")

        if result['issues']:
            print(f"\n{kleur('Details:', 'geel')}")
            for issue in result['issues'][:10]:
                ernst_kleur = "rood" if issue['ernst'] == "hoog" else "oranje"
                print(f"  Regel {issue['regel']}: {kleur(issue['beschrijving'], ernst_kleur)}")
                print(f"    {kleur(issue['code'], 'grijs')}")

        if result['aanbevelingen']:
            print(f"\n{kleur('Aanbevelingen:', 'groen')}")
            for aanbeveling in result['aanbevelingen']:
                print(f"  • {aanbeveling}")

    def _toon_code_smells(self):
        """Toon code smell detectie."""
        if not self.huidige_code:
            print(kleur("\nLaad eerst een bestand (optie 1)!", "rood"))
            return

        result = self.detect_code_smells()

        print("\n" + kleur("CODE SMELL DETECTOR", "cyaan"))
        print("=" * 50)
        print(f"\nCode smells gevonden: {result['totaal_smells']}")

        if result['per_type']:
            print(f"\n{kleur('Per type:', 'geel')}")
            for smell_type, count in result['per_type'].items():
                print(f"  {smell_type}: {count}")

        if result['smells']:
            print(f"\n{kleur('Details:', 'geel')}")
            for smell in result['smells'][:15]:
                regel_str = f"Regel {smell['regel']}" if smell['regel'] > 0 else "Algemeen"
                print(f"  {regel_str}: {smell['beschrijving']}")

    def _toon_complexity(self):
        """Toon complexity analyse."""
        if not self.huidige_code:
            print(kleur("\nLaad eerst een bestand (optie 1)!", "rood"))
            return

        result = self.bereken_complexity()

        print("\n" + kleur("COMPLEXITY ANALYSE", "cyaan"))
        print("=" * 50)

        rating_kleur = result.get('rating_kleur', 'wit')
        print(f"\nCyclomatic Complexity: {result['cyclomatic_complexity']}")
        print(f"Rating: {kleur(result['complexity_rating'], rating_kleur)}")
        print(f"\nMax Nesting Depth: {result['max_nesting_depth']}")
        print(f"Gemiddelde Nesting: {result['gemiddelde_nesting']}")
        print(f"Maintainability Index: {result['maintainability_index']}/100")

        print(f"\n{kleur('Regel lengtes:', 'geel')}")
        print(f"  Gemiddeld: {result['gemiddelde_regel_lengte']} karakters")
        print(f"  Maximum:   {result['max_regel_lengte']} karakters")
        print(f"  Te lang:   {result['lange_regels_count']} regels")

        if result['functie_complexity']:
            print(f"\n{kleur('Meest complexe functies:', 'geel')}")
            for naam, comp in result['functie_complexity']:
                print(f"  {naam}(): {comp}")

    def _toon_performance(self):
        """Toon performance check."""
        if not self.huidige_code:
            print(kleur("\nLaad eerst een bestand (optie 1)!", "rood"))
            return

        result = self.check_performance()

        print("\n" + kleur("PERFORMANCE CHECK", "cyaan"))
        print("=" * 50)
        print(f"\nPerformance issues: {result['totaal_issues']}")

        if result['issues']:
            print(f"\n{kleur('Gevonden:', 'geel')}")
            for issue in result['issues'][:10]:
                print(f"  Regel {issue['regel']}: {kleur(issue['beschrijving'], 'oranje')}")
                print(f"    {kleur(issue['code'], 'grijs')}")

    def detect_duplicate_code(self, code: str = None, min_regels: int = 4) -> Dict[str, Any]:
        """Detecteert duplicate code blokken."""
        code = code or self.huidige_code
        if not code:
            return {"fout": "Geen code geladen"}

        regels = code.split("\n")
        duplicaten = []
        gevonden_hashes = {}

        # Normaliseer regels (verwijder leading whitespace voor vergelijking)
        def normaliseer(regel):
            return regel.strip()

        # Zoek naar duplicate blokken van min_regels of meer
        for start in range(len(regels) - min_regels + 1):
            # Maak een blok van min_regels regels
            blok_regels = []
            for i in range(min_regels):
                regel = normaliseer(regels[start + i])
                if regel and not regel.startswith("#"):
                    blok_regels.append(regel)

            if len(blok_regels) < min_regels - 1:
                continue

            blok_hash = hash(tuple(blok_regels))

            if blok_hash in gevonden_hashes:
                # Check of het geen overlappend blok is
                vorige_start = gevonden_hashes[blok_hash]
                if abs(start - vorige_start) >= min_regels:
                    duplicaten.append({
                        "blok_1_start": vorige_start + 1,
                        "blok_2_start": start + 1,
                        "regels": min_regels,
                        "code_preview": blok_regels[0][:50] + "..." if len(blok_regels[0]) > 50 else blok_regels[0]
                    })
            else:
                gevonden_hashes[blok_hash] = start

        # Verwijder duplicaten in de resultaten
        unieke_duplicaten = []
        gezien = set()
        for dup in duplicaten:
            key = (dup["blok_1_start"], dup["blok_2_start"])
            if key not in gezien:
                gezien.add(key)
                unieke_duplicaten.append(dup)

        # Bereken duplicate score
        totaal_regels = len([r for r in regels if r.strip()])
        duplicate_regels = len(unieke_duplicaten) * min_regels
        duplicate_percentage = (duplicate_regels / totaal_regels * 100) if totaal_regels > 0 else 0

        return {
            "totaal_duplicaten": len(unieke_duplicaten),
            "duplicaten": unieke_duplicaten[:20],
            "duplicate_regels": duplicate_regels,
            "duplicate_percentage": round(duplicate_percentage, 1),
            "min_blok_grootte": min_regels
        }

    def _toon_duplicate_code(self):
        """Toon duplicate code detectie."""
        if not self.huidige_code:
            print(kleur("\nLaad eerst een bestand (optie 1)!", "rood"))
            return

        print("\n" + kleur("DUPLICATE CODE DETECTOR", "cyaan"))
        print("=" * 50)

        min_regels_str = input(kleur(
            "\nMinimum blokgrootte (aantal regels) [4]: ", "cyaan"
        )).strip()
        min_regels = int(min_regels_str) if min_regels_str.isdigit() else 4

        result = self.detect_duplicate_code(min_regels=min_regels)

        if "fout" in result:
            print(kleur(f"\nFout: {result['fout']}", "rood"))
            return

        print(f"\nDuplicate blokken gevonden: {result['totaal_duplicaten']}")
        print(f"Duplicate regels: ~{result['duplicate_regels']}")
        print(f"Duplicate percentage: {result['duplicate_percentage']}%")

        if result['duplicaten']:
            print(f"\n{kleur('Gevonden duplicaten:', 'geel')}")
            for i, dup in enumerate(result['duplicaten'][:10], 1):
                print(f"\n  {i}. Regel {dup['blok_1_start']} ↔ Regel {dup['blok_2_start']}")
                print(f"     ({dup['regels']} regels)")
                print(kleur(f"     Preview: {dup['code_preview']}", "grijs"))

            if result['totaal_duplicaten'] > 10:
                print(kleur(f"\n  ... en {result['totaal_duplicaten'] - 10} meer", "grijs"))

            print(f"\n{kleur('Aanbevelingen:', 'groen')}")
            if result['duplicate_percentage'] > 10:
                print("  • Overweeg duplicate code te refactoren naar functies")
                print("  • Maak herbruikbare utilities voor veelgebruikte patronen")
            elif result['duplicate_percentage'] > 5:
                print("  • Er is enige duplicatie - review de gemarkeerde blokken")
            else:
                print("  • Weinig duplicatie gevonden - goede code structuur!")

    def analyze_imports(self, code: str = None) -> Dict[str, Any]:
        """Analyseer imports - vind ongebruikte en problematische imports."""
        code = code or self.huidige_code
        if not code:
            return {"fout": "Geen code geladen"}

        result = {
            "totaal_imports": 0,
            "import_statements": [],
            "ongebruikte_imports": [],
            "wildcard_imports": [],
            "relatieve_imports": [],
            "standaard_lib": [],
            "externe_packages": [],
            "lokale_imports": [],
            "circulaire_risico": [],
            "aanbevelingen": []
        }

        # Parse de code met AST
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return {"fout": "Syntax error in code"}

        # Verzamel alle imports
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    naam = alias.asname if alias.asname else alias.name
                    imports.append({
                        "module": alias.name,
                        "alias": naam,
                        "regel": node.lineno,
                        "type": "import"
                    })
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    if alias.name == "*":
                        result["wildcard_imports"].append({
                            "module": module,
                            "regel": node.lineno
                        })
                    naam = alias.asname if alias.asname else alias.name
                    imports.append({
                        "module": f"{module}.{alias.name}" if module else alias.name,
                        "alias": naam,
                        "regel": node.lineno,
                        "type": "from",
                        "relatief": node.level > 0
                    })
                    if node.level > 0:
                        result["relatieve_imports"].append({
                            "module": module,
                            "naam": alias.name,
                            "regel": node.lineno,
                            "niveau": node.level
                        })

        result["totaal_imports"] = len(imports)
        result["import_statements"] = imports

        # Verzamel alle gebruikte namen in de code
        gebruikte_namen = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                gebruikte_namen.add(node.id)
            elif isinstance(node, ast.Attribute):
                # Voor module.functie() calls
                if isinstance(node.value, ast.Name):
                    gebruikte_namen.add(node.value.id)

        # Check welke imports ongebruikt zijn
        for imp in imports:
            alias = imp["alias"]
            # Split op . voor module imports (bv. os.path -> check 'os')
            base_naam = alias.split(".")[0]
            if base_naam not in gebruikte_namen and alias not in gebruikte_namen:
                result["ongebruikte_imports"].append({
                    "naam": alias,
                    "module": imp["module"],
                    "regel": imp["regel"]
                })

        # Categoriseer imports (standaard lib vs extern)
        standaard_lib = {
            "os", "sys", "re", "json", "time", "datetime", "math", "random",
            "collections", "itertools", "functools", "pathlib", "typing",
            "abc", "io", "copy", "hashlib", "logging", "unittest", "ast",
            "subprocess", "threading", "multiprocessing", "socket", "http",
            "urllib", "email", "html", "xml", "sqlite3", "csv", "pickle",
            "gzip", "zipfile", "tarfile", "tempfile", "shutil", "glob",
            "fnmatch", "stat", "fileinput", "struct", "codecs", "string",
            "textwrap", "difflib", "enum", "dataclasses", "contextlib",
            "warnings", "traceback", "inspect", "dis", "gc", "weakref"
        }

        for imp in imports:
            base_module = imp["module"].split(".")[0]
            if base_module in standaard_lib:
                result["standaard_lib"].append(imp["module"])
            elif imp.get("relatief"):
                result["lokale_imports"].append(imp["module"])
            else:
                result["externe_packages"].append(imp["module"])

        # Genereer aanbevelingen
        if result["wildcard_imports"]:
            result["aanbevelingen"].append(
                "Vermijd wildcard imports (from x import *) - importeer specifieke namen"
            )
        if len(result["ongebruikte_imports"]) > 0:
            result["aanbevelingen"].append(
                f"Verwijder {len(result['ongebruikte_imports'])} ongebruikte import(s)"
            )
        if len(imports) > 20:
            result["aanbevelingen"].append(
                "Veel imports - overweeg de module op te splitsen"
            )

        return result

    def _toon_import_analyse(self):
        """Toon import analyse resultaten."""
        if not self.huidige_code:
            print(kleur("\nLaad eerst een bestand (optie 1)!", "rood"))
            return

        print("\n" + kleur("IMPORT ANALYZER", "cyaan"))
        print("=" * 50)

        result = self.analyze_imports()

        if "fout" in result:
            print(kleur(f"\nFout: {result['fout']}", "rood"))
            return

        print(f"\nTotaal imports: {result['totaal_imports']}")
        print(f"  - Standaard library: {len(result['standaard_lib'])}")
        print(f"  - Externe packages: {len(set(result['externe_packages']))}")
        print(f"  - Lokale/relatieve: {len(result['relatieve_imports'])}")

        # Ongebruikte imports
        if result["ongebruikte_imports"]:
            print(f"\n{kleur('Ongebruikte imports:', 'geel')}")
            for imp in result["ongebruikte_imports"][:10]:
                print(f"  Regel {imp['regel']}: {kleur(imp['naam'], 'oranje')} ({imp['module']})")
            if len(result["ongebruikte_imports"]) > 10:
                print(kleur(f"  ... en {len(result['ongebruikte_imports']) - 10} meer", "grijs"))

        # Wildcard imports
        if result["wildcard_imports"]:
            print(f"\n{kleur('Wildcard imports (vermijden!):', 'rood')}")
            for imp in result["wildcard_imports"]:
                print(f"  Regel {imp['regel']}: from {imp['module']} import *")

        # Relatieve imports
        if result["relatieve_imports"]:
            print(f"\n{kleur('Relatieve imports:', 'cyaan')}")
            for imp in result["relatieve_imports"][:5]:
                dots = "." * imp["niveau"]
                print(f"  Regel {imp['regel']}: from {dots}{imp['module']} import {imp['naam']}")

        # Aanbevelingen
        if result["aanbevelingen"]:
            print(f"\n{kleur('Aanbevelingen:', 'groen')}")
            for aanbeveling in result["aanbevelingen"]:
                print(f"  • {aanbeveling}")

    def _toon_formatting(self):
        """Toon formatting check en bied fix aan."""
        if not self.huidige_code:
            print(kleur("\nLaad eerst een bestand (optie 1)!", "rood"))
            return

        result = self.check_formatting()

        print("\n" + kleur("FORMATTING CHECK", "cyaan"))
        print("=" * 50)

        score_kleur = "groen" if result['score'] >= 80 else "geel"
        print(f"\nFormatting Score: {kleur(str(result['score']) + '/100', score_kleur)}")
        print(f"Problemen gevonden: {result['totaal_problemen']}")

        if result['problemen']:
            print(f"\n{kleur('Details:', 'geel')}")
            for p in result['problemen'][:10]:
                print(f"  Regel {p['regel']}: {p['beschrijving']}")

            print(f"\n{kleur('Wil je de problemen automatisch fixen? (j/n)', 'cyaan')}")
            keuze = input("> ").strip().lower()

            if keuze == "j":
                gefixte_code = self.fix_formatting()
                nieuw_result = self.check_formatting(gefixte_code)

                print(f"\nProblemen voor fix: {result['totaal_problemen']}")
                print(f"Problemen na fix:   {nieuw_result['totaal_problemen']}")
                print(kleur(f"Opgelost: {result['totaal_problemen'] - nieuw_result['totaal_problemen']}", "groen"))

                if self.huidig_bestand:
                    print(f"\n{kleur('Wil je de gefixte code opslaan? (j/n)', 'cyaan')}")
                    opslaan = input("> ").strip().lower()

                    if opslaan == "j":
                        with open(self.huidig_bestand, "w", encoding="utf-8") as f:
                            f.write(gefixte_code)
                        self.huidige_code = gefixte_code
                        print(kleur(f"Opgeslagen naar {Path(self.huidig_bestand).name}!", "groen"))

    def _toon_naming(self):
        """Toon naming conventions check."""
        if not self.huidige_code:
            print(kleur("\nLaad eerst een bestand (optie 1)!", "rood"))
            return

        result = self.check_naming()

        print("\n" + kleur("NAMING CONVENTIONS", "cyaan"))
        print("=" * 50)

        score_kleur = "groen" if result['naming_score'] >= 80 else "geel"
        print(f"\nNaming Score: {kleur(str(result['naming_score']) + '/100', score_kleur)}")
        print(f"Problemen gevonden: {result['totaal_problemen']}")

        if result['problemen']:
            print(f"\n{kleur('Details:', 'geel')}")
            for p in result['problemen'][:10]:
                print(f"  Regel {p['regel']}: {p['type']} '{p['naam']}' moet {p['verwacht']} zijn")

    def _toon_documentatie(self):
        """Toon documentatie coverage."""
        if not self.huidige_code:
            print(kleur("\nLaad eerst een bestand (optie 1)!", "rood"))
            return

        result = self.check_documentatie()

        if "fout" in result:
            print(kleur(f"\nFout: {result['fout']}", "rood"))
            return

        print("\n" + kleur("DOCUMENTATIE CHECK", "cyaan"))
        print("=" * 50)

        doc_kleur = "groen" if result['documentatie_percentage'] >= 80 else "geel"
        print(f"\nDocumentatie Score: {kleur(str(result['documentatie_percentage']) + '%', doc_kleur)}")
        print(f"Module docstring: {'✓' if result['module_docstring'] else '✗'}")

        print(f"\n{kleur('Functies:', 'geel')}")
        print(f"  Met docstring:    {result['functies_met_docstring']}/{result['functies_totaal']}")
        if result['functies_zonder_docstring']:
            print("  Zonder docstring:")
            for f in result['functies_zonder_docstring'][:5]:
                print(f"    - {f['naam']}() op regel {f['regel']}")

        print(f"\n{kleur('Klassen:', 'geel')}")
        print(f"  Met docstring:    {result['klassen_met_docstring']}/{result['klassen_totaal']}")
        if result['klassen_zonder_docstring']:
            print("  Zonder docstring:")
            for k in result['klassen_zonder_docstring']:
                print(f"    - {k['naam']} op regel {k['regel']}")

    def _toon_type_hints(self):
        """Toon type hint coverage."""
        if not self.huidige_code:
            print(kleur("\nLaad eerst een bestand (optie 1)!", "rood"))
            return

        result = self.check_type_hints()

        print("\n" + kleur("TYPE HINT COVERAGE", "cyaan"))
        print("=" * 50)

        coverage_kleur = "groen" if result['type_coverage'] >= 80 else "geel"
        print(f"\nType Coverage: {kleur(str(result['type_coverage']) + '%', coverage_kleur)}")
        print(f"Volledig getypt: {result['volledig_getypt']}/{result['functies_totaal']} functies")

        if result['functies_zonder_types']:
            print(f"\n{kleur('Functies zonder complete types:', 'geel')}")
            for f in result['functies_zonder_types'][:10]:
                info = []
                if not f['heeft_return_type']:
                    info.append("geen return type")
                if f['args_met_type'] < f['args_totaal']:
                    info.append(f"{f['args_met_type']}/{f['args_totaal']} args getypt")
                print(f"  {f['naam']}(): {', '.join(info)}")

    def _toon_import_analyse(self):
        """Toon import analyse."""
        if not self.huidige_code:
            print(kleur("\nLaad eerst een bestand (optie 1)!", "rood"))
            return

        result = self.analyseer_imports()

        print("\n" + kleur("IMPORT ANALYSE", "cyaan"))
        print("=" * 50)
        print(f"\nTotaal imports: {result['totaal_imports']}")
        print(f"Import volgorde OK: {'✓' if result['import_volgorde_ok'] else '✗'}")

        if result['ongebruikte_imports']:
            print(f"\n{kleur('Ongebruikte imports:', 'oranje')}")
            for imp in result['ongebruikte_imports'][:10]:
                print(f"  Regel {imp['regel']}: {imp['module']}")

        if result['duplicate_imports']:
            print(f"\n{kleur('Duplicate imports:', 'oranje')}")
            for dup in result['duplicate_imports']:
                print(f"  {dup}")

    def _genereer_rapport_menu(self):
        """Menu voor rapport generatie."""
        if not self.huidige_code:
            print(kleur("\nLaad eerst een bestand (optie 1)!", "rood"))
            return

        print("\n" + kleur("RAPPORT GENEREREN", "cyaan"))
        print("-" * 40)
        print("Kies een formaat:")
        print("  1. Tekst (TXT)")
        print("  2. JSON")
        print("  3. HTML")

        keuze = input("\nKeuze: ").strip()

        formaat_map = {"1": "txt", "2": "json", "3": "html"}
        formaat = formaat_map.get(keuze, "txt")

        rapport = self.genereer_rapport(formaat)

        # Opslaan
        bestand_naam = Path(self.huidig_bestand).stem if self.huidig_bestand else "rapport"
        output_naam = f"{bestand_naam}_analyse.{formaat}"

        print(f"\n{kleur('Wil je het rapport opslaan? (j/n)', 'cyaan')}")
        opslaan = input("> ").strip().lower()

        if opslaan == "j":
            with open(output_naam, "w", encoding="utf-8") as f:
                f.write(rapport)
            print(kleur(f"\nRapport opgeslagen: {output_naam}", "groen"))
        else:
            print("\n" + rapport[:2000])
            if len(rapport) > 2000:
                print(kleur("\n... (output afgekapt)", "grijs"))

    def _toon_geschiedenis(self):
        """Toon analyse geschiedenis."""
        print("\n" + kleur("ANALYSE GESCHIEDENIS", "cyaan"))
        print("=" * 50)

        if not self.data["analyse_geschiedenis"]:
            print(kleur("\nGeen analyses in geschiedenis.", "grijs"))
            return

        print(f"\nLaatste {len(self.data['analyse_geschiedenis'])} analyses:\n")

        for analyse in reversed(self.data["analyse_geschiedenis"][-10:]):
            datum = analyse['datum'][:10]
            print(f"  {datum} | {analyse['bestand']} | {analyse['regels']} regels | Security: {analyse['security_score']}")

    def _toon_statistieken(self):
        """Toon globale statistieken."""
        print("\n" + kleur("STATISTIEKEN", "cyaan"))
        print("=" * 50)

        stats = self.data["statistieken"]
        print(f"\nAnalyses uitgevoerd:     {self.data['analyses_totaal']}")
        print(f"Bestanden geanalyseerd:  {len(self.data['bestanden_geanalyseerd'])}")
        print(f"Regels geanalyseerd:     {stats['totaal_regels_geanalyseerd']:,}")
        print(f"Security issues gevonden: {stats['security_issues_gevonden']}")
        print(f"Code smells gevonden:    {stats['code_smells_gevonden']}")
        print(f"Fixes toegepast:         {stats['fixes_toegepast']}")

    def run(self):
        """Start de interactieve app."""
        clear_scherm()
        print(kleur("+" + "=" * 50 + "+", "cyaan"))
        print(kleur("|        CODE ANALYSE TOOL v2.0                    |", "cyaan"))
        print(kleur("|  Professionele Python Code Analyzer              |", "wit"))
        print(kleur("|                                                  |", "wit"))
        print(kleur("|  Features:                                       |", "grijs"))
        print(kleur("|  • Security scanning    • Code smells            |", "grijs"))
        print(kleur("|  • Complexity metrics   • Performance check      |", "grijs"))
        print(kleur("|  • Type hint coverage   • Documentation check    |", "grijs"))
        print(kleur("|  • Project analyse      • Rapport generatie      |", "grijs"))
        print(kleur("+" + "=" * 50 + "+", "cyaan"))

        while True:
            self._toon_menu()
            keuze = input("\nKeuze: ").strip()

            if keuze == "0":
                break
            elif keuze == "1":
                self._laad_bestand_interactief()
            elif keuze == "2":
                self._toon_project_analyse()
            elif keuze == "3":
                self._toon_volledige_analyse()
            elif keuze == "4":
                self._toon_security_scan()
            elif keuze == "5":
                self._toon_code_smells()
            elif keuze == "6":
                self._toon_complexity()
            elif keuze == "7":
                self._toon_performance()
            elif keuze == "8":
                self._toon_duplicate_code()
            elif keuze == "9":
                self._toon_formatting()
            elif keuze == "10":
                self._toon_naming()
            elif keuze == "11":
                self._toon_documentatie()
            elif keuze == "12":
                self._toon_type_hints()
            elif keuze == "13":
                self._toon_import_analyse()
            elif keuze == "14":
                self._genereer_rapport_menu()
            elif keuze == "15":
                self._toon_geschiedenis()
            elif keuze == "16":
                self._toon_statistieken()
            elif keuze == "17":
                tekst = input("\nVoer tekst in: ")
                if tekst:
                    telling = self.tel_woorden(tekst)
                    print(f"\nAantal unieke woorden: {len(telling)}")
                    top = Counter(telling).most_common(5)
                    print(f"Top 5: {top}")
            elif keuze == "18":
                invoer = input("\nVoer getallen in (gescheiden door spaties): ")
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
                    print(kleur("Fout: voer geldige getallen in.", "rood"))
            else:
                print(kleur("Ongeldige keuze.", "rood"))

            input(kleur("\nDruk op Enter om verder te gaan...", "grijs"))

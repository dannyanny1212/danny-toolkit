"""Auto Refactor Guard — AST-gebaseerde kwaliteitschecker voor v6.11.0 Diamond Polish.

Scant Python bestanden op 8 kwaliteitscriteria en genereert een score (0-10).
Gebruik: venv311/Scripts/python.exe auto_refactor_guard.py [pad] [--json] [--fix-future]

Criteria:
  1. from __future__ import annotations  (10 pts)
  2. Return type hints op alle functies  (20 pts)
  3. Docstrings op alle functies         (15 pts)
  4. Geen relative imports               (10 pts)
  5. Geen bare except/pass               (10 pts)
  6. Logger aanwezig (geen bare print)   (10 pts)
  7. Geen imports in functies            (10 pts)
  8. Type hints op alle parameters       (15 pts)
"""

from __future__ import annotations

import ast
import json
import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import TextIO

logger = logging.getLogger(__name__)


@dataclass
class Issue:
    """Een enkel kwaliteitsprobleem gevonden door de guard."""

    rule: str
    line: int
    message: str
    severity: str = "warning"  # "warning" | "error"


@dataclass
class AuditResult:
    """Resultaat van een bestandsaudit."""

    path: str
    lines: int = 0
    classes: int = 0
    functions: int = 0
    score: float = 0.0
    max_score: float = 100.0
    issues: list[Issue] = field(default_factory=list)

    @property
    def quality(self) -> float:
        """Kwaliteitsscore op schaal 0-10."""
        return round(self.score / self.max_score * 10, 1)

    @property
    def grade(self) -> str:
        """Letter grade op basis van kwaliteit."""
        q = self.quality
        if q >= 9:
            return "A+"
        if q >= 8:
            return "A"
        if q >= 7:
            return "B"
        if q >= 5:
            return "C"
        if q >= 3:
            return "D"
        return "F"

    def to_dict(self) -> dict:
        """Converteer naar dictionary voor JSON output."""
        return {
            "path": self.path,
            "lines": self.lines,
            "classes": self.classes,
            "functions": self.functions,
            "quality": self.quality,
            "grade": self.grade,
            "score": f"{self.score}/{self.max_score}",
            "issues": [
                {"rule": i.rule, "line": i.line, "message": i.message, "severity": i.severity}
                for i in self.issues
            ],
        }


def audit_file(path: Path) -> AuditResult:
    """Voer een volledige Diamond Polish audit uit op een Python bestand.

    Args:
        path: Pad naar het .py bestand.

    Returns:
        AuditResult met score, issues en metadata.
    """
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))

    result = AuditResult(path=str(path), lines=len(source.splitlines()))
    score = 100.0  # Start perfect, trek af per issue

    # Gather all classes and functions
    all_classes = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
    all_functions = _collect_functions(tree)
    result.classes = len(all_classes)
    result.functions = len(all_functions)

    # === Rule 1: __future__ annotations (10 pts) ===
    has_future = any(
        isinstance(n, ast.ImportFrom) and n.module == "__future__" and
        any(alias.name == "annotations" for alias in n.names)
        for n in ast.walk(tree)
    )
    if not has_future:
        score -= 10
        result.issues.append(Issue(
            rule="future-annotations", line=1,
            message="Missing 'from __future__ import annotations'",
            severity="error",
        ))

    # === Rule 2: Return type hints (20 pts) ===
    if all_functions:
        missing_return = [f for f in all_functions if f.returns is None]
        if missing_return:
            penalty = 20 * len(missing_return) / len(all_functions)
            score -= penalty
            for f in missing_return:
                result.issues.append(Issue(
                    rule="return-type-hint", line=f.lineno,
                    message=f"Function '{f.name}' missing return type hint",
                ))

    # === Rule 3: Docstrings (15 pts) ===
    if all_functions:
        missing_docs = [f for f in all_functions if not _has_docstring(f)]
        if missing_docs:
            penalty = 15 * len(missing_docs) / len(all_functions)
            score -= penalty
            for f in missing_docs:
                result.issues.append(Issue(
                    rule="docstring", line=f.lineno,
                    message=f"Function '{f.name}' missing docstring",
                ))

    # === Rule 4: No relative imports (10 pts) ===
    relative_imports = [
        n for n in ast.walk(tree)
        if isinstance(n, ast.ImportFrom) and n.level and n.level > 0
    ]
    if relative_imports:
        score -= 10
        for imp in relative_imports:
            result.issues.append(Issue(
                rule="absolute-import", line=imp.lineno,
                message=f"Relative import found (level={imp.level})",
                severity="error",
            ))

    # === Rule 5: No bare except/pass (10 pts) ===
    bare_excepts = _find_bare_except_pass(tree)
    if bare_excepts:
        penalty = min(10, 3 * len(bare_excepts))
        score -= penalty
        for lineno in bare_excepts:
            result.issues.append(Issue(
                rule="bare-except-pass", line=lineno,
                message="Bare 'except: pass' or 'except Exception: pass' found",
            ))

    # === Rule 6: Logger present (10 pts) ===
    has_logger = any(
        isinstance(n, ast.Assign) and
        any(isinstance(t, ast.Name) and t.id == "logger" for t in (n.targets if isinstance(n, ast.Assign) else []))
        for n in ast.walk(tree)
    )
    if not has_logger and result.lines > 50:
        score -= 10
        result.issues.append(Issue(
            rule="logger", line=1,
            message="No logger defined (expected 'logger = logging.getLogger(__name__)')",
        ))

    # === Rule 7: No imports inside functions (10 pts) ===
    inner_imports = _find_inner_imports(tree)
    if inner_imports:
        penalty = min(10, 5 * len(inner_imports))
        score -= penalty
        for lineno, mod in inner_imports:
            result.issues.append(Issue(
                rule="inner-import", line=lineno,
                message=f"Import '{mod}' found inside function body",
            ))

    # === Rule 8: Parameter type hints (15 pts) ===
    if all_functions:
        missing_params = _count_missing_param_hints(all_functions)
        total_params = _count_total_params(all_functions)
        if total_params > 0 and missing_params > 0:
            penalty = 15 * missing_params / total_params
            score -= penalty
            result.issues.append(Issue(
                rule="param-type-hint", line=1,
                message=f"{missing_params}/{total_params} parameters missing type hints",
            ))

    result.score = max(0.0, round(score, 1))
    return result


def _collect_functions(tree: ast.AST) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    """Verzamel alle functies en methodes (exclusief dunder behalve __init__)."""
    funcs = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Skip dunders behalve __init__
            if node.name.startswith("__") and node.name.endswith("__") and node.name != "__init__":
                continue
            funcs.append(node)
    return funcs


def _has_docstring(func: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Check of een functie een docstring heeft."""
    if not func.body:
        return False
    first = func.body[0]
    return isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str)


def _find_bare_except_pass(tree: ast.AST) -> list[int]:
    """Vind alle 'except: pass' of 'except Exception: pass' patronen."""
    lines: list[int] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler):
            if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
                lines.append(node.lineno)
    return lines


def _is_lazy_load_import(func_node: ast.AST, import_node: ast.AST) -> bool:
    """Check of een import in een try/except ImportError|ModuleNotFoundError zit.

    Legitieme lazy-load imports zitten in een try-blok waarvan de
    except-handler specifiek ImportError of ModuleNotFoundError afvangt.
    Deze tellen niet mee voor de inner-import penalty.
    """
    for node in ast.walk(func_node):
        if not isinstance(node, ast.Try):
            continue
        # Check of de import in de try-body zit
        for body_node in ast.walk(node):
            if body_node is import_node:
                # Controleer of een handler ImportError/ModuleNotFoundError afvangt
                for handler in node.handlers:
                    if handler.type is None:
                        # Bare except: — telt als lazy load (vangt alles)
                        return True
                    if isinstance(handler.type, ast.Name):
                        if handler.type.id in ("ImportError", "ModuleNotFoundError", "Exception"):
                            return True
                    elif isinstance(handler.type, ast.Tuple):
                        for elt in handler.type.elts:
                            if isinstance(elt, ast.Name) and elt.id in (
                                "ImportError", "ModuleNotFoundError", "Exception",
                            ):
                                return True
    return False


def _find_inner_imports(tree: ast.AST) -> list[tuple[int, str]]:
    """Vind imports die binnen functiebodies leven, exclusief lazy-loads.

    Imports in try/except ImportError|ModuleNotFoundError blokken worden
    uitgesloten — dit zijn legitieme lazy-load patronen voor zware deps.
    """
    results: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for child in ast.walk(node):
            if isinstance(child, ast.Import):
                if _is_lazy_load_import(node, child):
                    continue
                for alias in child.names:
                    results.append((child.lineno, alias.name))
            elif isinstance(child, ast.ImportFrom) and child.module != "__future__":
                if _is_lazy_load_import(node, child):
                    continue
                results.append((child.lineno, child.module or ""))
    return results


def _count_missing_param_hints(funcs: list[ast.FunctionDef | ast.AsyncFunctionDef]) -> int:
    """Tel parameters zonder type hint (exclusief self/cls)."""
    missing = 0
    for f in funcs:
        for arg in f.args.args:
            if arg.arg in ("self", "cls"):
                continue
            if arg.annotation is None:
                missing += 1
    return missing


def _count_total_params(funcs: list[ast.FunctionDef | ast.AsyncFunctionDef]) -> int:
    """Tel totaal aantal parameters (exclusief self/cls)."""
    total = 0
    for f in funcs:
        for arg in f.args.args:
            if arg.arg in ("self", "cls"):
                continue
            total += 1
    return total


def fix_future(path: Path) -> bool:
    """Voeg 'from __future__ import annotations' toe als deze ontbreekt.

    Returns:
        True als het bestand gewijzigd is.
    """
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)

    has_future = any(
        isinstance(n, ast.ImportFrom) and n.module == "__future__"
        for n in ast.walk(tree)
    )
    if has_future:
        return False

    lines = source.splitlines(keepends=True)

    # Use AST to find module docstring end line, then insert after it
    insert_idx = 0
    if tree.body and isinstance(tree.body[0], ast.Expr) and isinstance(
        getattr(tree.body[0], "value", None), ast.Constant
    ) and isinstance(tree.body[0].value.value, str):
        # Module has a docstring — insert after it
        insert_idx = tree.body[0].end_lineno  # type: ignore[attr-defined]
        # Skip blank lines after docstring
        while insert_idx < len(lines) and not lines[insert_idx].strip():
            insert_idx += 1
    else:
        # No docstring — skip shebang and encoding comments
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("#") or not stripped:
                insert_idx = i + 1
                continue
            break

    lines.insert(insert_idx, "from __future__ import annotations\n\n")
    path.write_text("".join(lines), encoding="utf-8")
    return True


def print_report(result: AuditResult, out: TextIO = sys.stdout) -> None:
    """Print een leesbaar rapport naar de gegeven stream."""
    q = result.quality
    grade = result.grade

    # Kleur op basis van score
    if q >= 8:
        color = "\033[92m"  # groen
    elif q >= 5:
        color = "\033[93m"  # geel
    else:
        color = "\033[91m"  # rood
    reset = "\033[0m"

    out.write(f"\n{'=' * 60}\n")
    out.write(f"  Auto Refactor Guard — Diamond Polish v6.11.0\n")
    out.write(f"{'=' * 60}\n")
    out.write(f"  File:      {result.path}\n")
    out.write(f"  Lines:     {result.lines}\n")
    out.write(f"  Classes:   {result.classes}\n")
    out.write(f"  Functions: {result.functions}\n")
    out.write(f"  Score:     {color}{result.score}/{result.max_score} ({q}/10) [{grade}]{reset}\n")
    out.write(f"{'=' * 60}\n")

    if result.issues:
        out.write(f"\n  Issues ({len(result.issues)}):\n")
        for issue in result.issues:
            icon = "\033[91m✗\033[0m" if issue.severity == "error" else "\033[93m⚠\033[0m"
            out.write(f"    {icon} L{issue.line:>4} [{issue.rule}] {issue.message}\n")
    else:
        out.write(f"\n  \033[92m✓ No issues found — Diamond Polish compliant!\033[0m\n")

    out.write("\n")


def scan_directory(path: Path, min_lines: int = 30) -> list[AuditResult]:
    """Scan alle .py bestanden in een directory recursief.

    Args:
        path: Root directory om te scannen.
        min_lines: Minimaal aantal regels om te auditen (skip tiny files).

    Returns:
        Lijst van AuditResult gesorteerd op quality (laagste eerst).
    """
    results: list[AuditResult] = []
    for py_file in sorted(path.rglob("*.py")):
        # Skip __pycache__, venv, test files
        parts = py_file.parts
        if any(skip in parts for skip in ("__pycache__", "venv311", ".git", "node_modules")):
            continue
        try:
            result = audit_file(py_file)
            if result.lines >= min_lines:
                results.append(result)
        except SyntaxError:
            logger.debug("Kan %s niet parsen, overgeslagen", py_file)

    results.sort(key=lambda r: r.quality)
    return results


def main() -> None:
    """CLI entrypoint voor de Auto Refactor Guard."""
    args = sys.argv[1:]

    json_mode = "--json" in args
    do_fix = "--fix-future" in args
    args = [a for a in args if not a.startswith("--")]

    target = Path(args[0]) if args else Path("danny_toolkit")

    if target.is_file():
        if do_fix:
            changed = fix_future(target)
            if changed:
                print(f"  [FIX] Added __future__ annotations to {target}")

        result = audit_file(target)
        if json_mode:
            print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
        else:
            print_report(result)
    elif target.is_dir():
        results = scan_directory(target)

        if json_mode:
            summary = {
                "total_files": len(results),
                "avg_quality": round(sum(r.quality for r in results) / len(results), 1) if results else 0,
                "worst_5": [r.to_dict() for r in results[:5]],
                "best_5": [r.to_dict() for r in results[-5:]],
                "grade_distribution": {},
            }
            for r in results:
                g = r.grade
                summary["grade_distribution"][g] = summary["grade_distribution"].get(g, 0) + 1
            print(json.dumps(summary, indent=2, ensure_ascii=False))
        else:
            print(f"\n{'=' * 60}")
            print(f"  Auto Refactor Guard — Directory Scan")
            print(f"  Target: {target}")
            print(f"  Files:  {len(results)}")
            if results:
                avg = sum(r.quality for r in results) / len(results)
                print(f"  Avg:    {avg:.1f}/10")
            print(f"{'=' * 60}")

            # Grade distribution
            grades: dict[str, int] = {}
            for r in results:
                g = r.grade
                grades[g] = grades.get(g, 0) + 1
            print(f"\n  Grade Distribution:")
            for g in ["A+", "A", "B", "C", "D", "F"]:
                if g in grades:
                    bar = "█" * grades[g]
                    print(f"    {g:>2}: {grades[g]:>3} {bar}")

            # Worst 10
            print(f"\n  Worst 10 (refactor candidates):")
            for r in results[:10]:
                color = "\033[91m" if r.quality < 5 else "\033[93m" if r.quality < 8 else "\033[92m"
                print(f"    {color}{r.quality:>4.1f}/10\033[0m [{r.grade:>2}] {r.path} ({r.lines} LOC, {len(r.issues)} issues)")

            print()
    else:
        print(f"[!] Pad niet gevonden: {target}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

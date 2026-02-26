"""
Import Analyzer -- Chirurgisch wapen voor Fase B.1.

Scant de danny_toolkit codebase op relatieve imports en classificeert ze:
- VEILIG: from ..X → from danny_toolkit.X (reguliere modules)
- SKIP:   from .X in __init__.py (standaard re-exports)
- RISICO: circulaire dependency detectie

Gebruik:
    python -m danny_toolkit.core.import_analyzer          # Volledige analyse
    python -m danny_toolkit.core.import_analyzer --fix     # Dry-run fix preview
    python -m danny_toolkit.core.import_analyzer --apply   # Voer fixes uit
"""

import ast
import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple

# --- Constanten ---

PACKAGE_ROOT = Path(__file__).parent.parent  # danny_toolkit/
PROJECT_ROOT = PACKAGE_ROOT.parent           # C:\Users\danny\danny-toolkit\
PACKAGE_NAME = "danny_toolkit"

# Regex voor relatieve imports
RE_RELATIVE = re.compile(
    r"^(\s*from\s+)(\.{1,3})([a-zA-Z_][a-zA-Z0-9_.]*)?(\s+import\s+.+)$"
)


# --- Analyse Functies ---

def resolve_relative_import(
    file_path: Path, dots: str, module_path: str
) -> str:
    """Vertaal een relatieve import naar een absolute.

    Args:
        file_path: Het bestand dat de import bevat.
        dots: De dot-prefix (., .., ...).
        module_path: Het module-pad na de dots (kan leeg zijn).

    Returns:
        Het absolute import pad (bijv. danny_toolkit.core.config).
    """
    # Bepaal huidige package relatief aan danny_toolkit/
    rel = file_path.relative_to(PACKAGE_ROOT)
    parts = list(rel.parts[:-1])  # directories = package path

    # Ga 'levels' omhoog
    levels = len(dots)
    if levels > 1:
        up = levels - 1
        if up > len(parts):
            return f"ONGELDIG({dots}{module_path})"
        parts = parts[:-up]

    # Combineer
    base = [PACKAGE_NAME] + parts
    if module_path:
        base.extend(module_path.split("."))

    return ".".join(base)


def scan_file(file_path: Path) -> List[dict]:
    """Scan een bestand op relatieve imports.

    Returns:
        Lijst van dicts met: line_num, original, dots, module, absolute, safe.
    """
    results = []
    is_init = file_path.name == "__init__.py"

    try:
        content = file_path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return results

    for i, line in enumerate(content.splitlines(), 1):
        m = RE_RELATIVE.match(line)
        if not m:
            continue

        prefix = m.group(1)   # "from "
        dots = m.group(2)     # "." or ".." or "..."
        module = m.group(3) or ""  # module pad na dots
        suffix = m.group(4)   # " import X, Y, Z"

        absolute = resolve_relative_import(file_path, dots, module)

        # Classificeer
        if is_init and len(dots) == 1:
            safety = "SKIP_INIT"
        elif "ONGELDIG" in absolute:
            safety = "ONGELDIG"
        elif len(dots) == 1 and not is_init:
            safety = "VEILIG"  # single-dot in regulier bestand
        elif len(dots) >= 2:
            safety = "VEILIG"  # double/triple-dot
        else:
            safety = "ONBEKEND"

        results.append({
            "file": str(file_path.relative_to(PROJECT_ROOT)),
            "line_num": i,
            "original": line.rstrip(),
            "dots": dots,
            "module": module,
            "absolute": absolute,
            "suffix": suffix.strip(),
            "safety": safety,
            "is_init": is_init,
        })

    return results


def scan_codebase() -> List[dict]:
    """Scan de volledige danny_toolkit/ codebase."""
    all_results = []

    for py_file in sorted(PACKAGE_ROOT.rglob("*.py")):
        # Skip __pycache__
        if "__pycache__" in str(py_file):
            continue
        all_results.extend(scan_file(py_file))

    return all_results


def detect_circular_risks(results: List[dict]) -> Dict[str, Set[str]]:
    """Detecteer potentiële circulaire imports.

    Bouwt een dependency-graph en zoekt naar cycles.
    """
    # Graph: module -> set van modules die het importeert
    graph: Dict[str, Set[str]] = defaultdict(set)

    for r in results:
        if r["safety"] == "SKIP_INIT":
            continue
        # Source module
        src_parts = Path(r["file"]).with_suffix("").parts
        if src_parts[0] == "danny_toolkit":
            src_module = ".".join(src_parts)
        else:
            src_module = ".".join(["danny_toolkit"] + list(src_parts))

        # Target module
        target = r["absolute"]
        graph[src_module].add(target)

    # DFS cycle detection
    cycles = {}
    visited = set()
    rec_stack = set()

    def dfs(node: str, path: list):
        """**Performs a depth-first search on a graph to detect cycles.**

*   Args:
    *   node: The current node being visited.
    *   path: The current path of nodes from the starting node to the current node.
*   Returns:
    *   None. Cycles are stored in the `cycles` dictionary.
*   Notes:
    *   Uses a recursive stack to keep track of nodes in the current recursion stack.
    *   Cycles are stored as a set of nodes in the `cycles` dictionary with a string key representing the cycle."""
        visited.add(node)
        rec_stack.add(node)
        path.append(node)

        for neighbor in graph.get(node, set()):
            if neighbor not in visited:
                dfs(neighbor, path)
            elif neighbor in rec_stack:
                # Cycle gevonden
                cycle_start = path.index(neighbor)
                cycle = path[cycle_start:] + [neighbor]
                key = " -> ".join(cycle)
                cycles[key] = set(cycle)

        path.pop()
        rec_stack.discard(node)

    for node in graph:
        if node not in visited:
            dfs(node, [])

    return cycles


def generate_fix(result: dict) -> Tuple[str, str]:
    """Genereer de oude en nieuwe regel voor een veilige import.

    Returns:
        (old_line, new_line) tuple.
    """
    m = RE_RELATIVE.match(result["original"])
    if not m:
        return result["original"], result["original"]

    prefix = m.group(1)  # "from " (behoud indentatie)
    suffix = m.group(4)  # " import X"

    new_line = f"{prefix}{result['absolute']}{suffix}"
    return result["original"], new_line


def apply_fixes(results: List[dict], dry_run: bool = True) -> int:
    """Pas veilige fixes toe op bestanden.

    Args:
        results: Lijst van scan-resultaten.
        dry_run: Als True, toon alleen wat er zou veranderen.

    Returns:
        Aantal gefixte imports.
    """
    # Groepeer per bestand
    by_file: Dict[str, List[dict]] = defaultdict(list)
    for r in results:
        if r["safety"] == "VEILIG":
            by_file[r["file"]].append(r)

    fixed = 0
    for filepath, items in sorted(by_file.items()):
        full_path = PROJECT_ROOT / filepath
        try:
            lines = full_path.read_text(encoding="utf-8").splitlines(True)
        except (UnicodeDecodeError, OSError):
            continue

        modified = False
        for item in sorted(items, key=lambda x: x["line_num"], reverse=True):
            idx = item["line_num"] - 1
            old, new = generate_fix(item)

            if dry_run:
                print(f"  {filepath}:{item['line_num']}")
                print(f"    - {old.strip()}")
                print(f"    + {new.strip()}")
            else:
                if idx < len(lines):
                    lines[idx] = new + ("\n" if not new.endswith("\n") else "")
                    modified = True

            fixed += 1

        if modified and not dry_run:
            full_path.write_text("".join(lines), encoding="utf-8")
            print(f"  FIXED: {filepath} ({len(items)} imports)")

    return fixed


# --- Rapport ---

def print_report(results: List[dict], cycles: Dict[str, Set[str]]):
    """Print het volledige analyse-rapport."""
    print("=" * 70)
    print("IMPORT ANALYZER -- DEPENDENCY GRAPH RAPPORT")
    print("=" * 70)

    # Tellingen
    safe = [r for r in results if r["safety"] == "VEILIG"]
    skip = [r for r in results if r["safety"] == "SKIP_INIT"]
    invalid = [r for r in results if r["safety"] == "ONGELDIG"]

    print(f"\nTOTAAL GESCAND: {len(results)} relatieve imports")
    print(f"  VEILIG om te converteren:  {len(safe)}")
    print(f"  SKIP (__init__.py):        {len(skip)}")
    print(f"  ONGELDIG:                  {len(invalid)}")

    # Per-package breakdown
    print(f"\n{'-' * 70}")
    print("PER PACKAGE BREAKDOWN (alleen VEILIG targets):")
    print(f"{'-' * 70}")

    by_pkg: Dict[str, int] = defaultdict(int)
    by_file_count: Dict[str, int] = defaultdict(int)
    for r in safe:
        pkg = Path(r["file"]).parts[1] if len(Path(r["file"]).parts) > 1 else "root"
        by_pkg[pkg] += 1
        by_file_count[r["file"]] += 1

    for pkg, count in sorted(by_pkg.items(), key=lambda x: -x[1]):
        print(f"  {pkg:30s} {count:4d} imports")

    # Top bestanden
    print(f"\n{'-' * 70}")
    print("TOP 15 BESTANDEN (meeste veilige targets):")
    print(f"{'-' * 70}")

    for filepath, count in sorted(
        by_file_count.items(), key=lambda x: -x[1]
    )[:15]:
        print(f"  {filepath:55s} {count:3d}")

    # Double-dot vs single-dot breakdown
    double = [r for r in safe if len(r["dots"]) >= 2]
    single = [r for r in safe if len(r["dots"]) == 1]
    print(f"\n{'-' * 70}")
    print("IMPORT TYPE BREAKDOWN (VEILIG):")
    print(f"{'-' * 70}")
    print(f"  from ..X  (cross-package):  {len(double)}")
    print(f"  from .X   (intra-package):  {len(single)}")

    # Circulaire risico's
    print(f"\n{'-' * 70}")
    print("CIRCULAIRE DEPENDENCY RISICO'S:")
    print(f"{'-' * 70}")

    if cycles:
        print(f"  WAARSCHUWING: {len(cycles)} potentiele cycles gedetecteerd!")
        for cycle_desc in list(cycles.keys())[:10]:
            print(f"  !! {cycle_desc}")
    else:
        print("  GEEN cycles gedetecteerd. Conversie is VEILIG.")

    # Ongeldige imports
    if invalid:
        print(f"\n{'-' * 70}")
        print("ONGELDIGE IMPORTS (niet converteerbaar):")
        print(f"{'-' * 70}")
        for r in invalid:
            print(f"  {r['file']}:{r['line_num']}: {r['original'].strip()}")

    print(f"\n{'=' * 70}")
    print(f"VERDICT: {len(safe)} imports VEILIG voor conversie")
    if not cycles:
        print("DEPENDENCY GRAPH: SCHOON -- geen circulaire risico's")
    print(f"{'=' * 70}")


# --- Entry Point ---

def main():
    """Hoofdfunctie -- scan, analyseer, rapporteer."""
    args = sys.argv[1:]

    print("Scanning danny_toolkit/ ...")
    results = scan_codebase()

    print("Analysing dependency graph ...")
    cycles = detect_circular_risks(results)

    if "--apply" in args:
        print("\n APPLYING FIXES (LIVE):")
        count = apply_fixes(results, dry_run=False)
        print(f"\n{count} imports geconverteerd.")
    elif "--fix" in args:
        print("\n DRY-RUN FIX PREVIEW:")
        count = apply_fixes(results, dry_run=True)
        print(f"\n{count} imports zouden geconverteerd worden.")
    else:
        print_report(results, cycles)


if __name__ == "__main__":
    main()

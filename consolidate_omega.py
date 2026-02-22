"""
OMEGA SOVEREIGN — Core Consolidation Script
=============================================
Recursief zoekt alle Omega-gerelateerde bestanden en kopieert
ze naar een geconsolideerde master directory.

Veilig: shutil.copy2 (metadata behouden, originelen intact).
Gebruik: python consolidate_omega.py
"""

import io
import os
import sys
import shutil
import time
from pathlib import Path

# Windows UTF-8
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(
        sys.stdout.buffer, encoding="utf-8", errors="replace"
    )

# === CONFIGURATIE ===

ROOT_DIR = Path(r"C:\Users\danny\danny-toolkit")
TARGET_DIR = ROOT_DIR / "Omega_Sovereign_Core"

# Directories die ALTIJD worden overgeslagen
SKIP_DIRS = {
    "venv311", "venv", ".venv", "env",
    "__pycache__", ".git", "node_modules",
    ".mypy_cache", ".pytest_cache", ".tox",
    "Omega_Sovereign_Core",  # voorkom zelf-kopie
}

# Bestandsnaam-patronen (lowercase matching)
TARGET_PATTERNS = [
    "skill_",
    "omega",
    "quest",
    "matrix",
    "pulse",
    "threat_report",
]

# Extensies die we willen (voorkom rommel zoals .pyc, .tmp)
ALLOWED_EXTENSIONS = {
    ".py", ".md", ".txt", ".json", ".log",
    ".yaml", ".yml", ".toml", ".cfg", ".ini",
    ".csv", ".html",
}


# === TERMINAL STYLING ===

class V:
    """Visuele constanten voor terminal output."""
    RST = "\033[0m"
    BLD = "\033[1m"
    DIM = "\033[2m"
    GRN = "\033[92m"
    CYN = "\033[96m"
    YLW = "\033[93m"
    RED = "\033[91m"
    MAG = "\033[95m"
    WHT = "\033[97m"
    LINE = f"{DIM}{'─' * 62}{RST}"
    DLINE = f"{DIM}{'═' * 62}{RST}"


def banner():
    print(f"""
{V.DLINE}
{V.BLD}{V.CYN}  ██████  ███    ███ ███████  ██████   █████  {V.RST}
{V.BLD}{V.CYN} ██    ██ ████  ████ ██      ██       ██   ██ {V.RST}
{V.BLD}{V.CYN} ██    ██ ██ ████ ██ █████   ██   ███ ███████ {V.RST}
{V.BLD}{V.CYN} ██    ██ ██  ██  ██ ██      ██    ██ ██   ██ {V.RST}
{V.BLD}{V.CYN}  ██████  ██      ██ ███████  ██████  ██   ██ {V.RST}
{V.DIM}       SOVEREIGN CORE — FILE CONSOLIDATION{V.RST}
{V.DLINE}
{V.DIM}  ROOT  : {V.WHT}{ROOT_DIR}{V.RST}
{V.DIM}  TARGET: {V.WHT}{TARGET_DIR}{V.RST}
{V.DIM}  SKIP  : {V.WHT}{', '.join(sorted(SKIP_DIRS))}{V.RST}
{V.LINE}""")


# === CORE LOGICA ===

def should_skip_dir(dirname: str) -> bool:
    """Check of een directory overgeslagen moet worden."""
    return dirname in SKIP_DIRS or dirname.startswith(".")


def matches_pattern(filename: str) -> bool:
    """Check of een bestandsnaam matcht met Omega-patronen."""
    lower = filename.lower()
    # Extensie check
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return False
    # Patroon check
    return any(pattern in lower for pattern in TARGET_PATTERNS)


def scan_files(root: Path) -> list[dict]:
    """Recursief zoeken naar Omega-bestanden."""
    gevonden = []

    for dirpath, dirnames, filenames in os.walk(root):
        # Filter directories IN-PLACE (voorkomt afdalen in skip dirs)
        dirnames[:] = [
            d for d in dirnames if not should_skip_dir(d)
        ]

        for fname in filenames:
            if matches_pattern(fname):
                full_path = Path(dirpath) / fname
                rel_path = full_path.relative_to(root)
                size = full_path.stat().st_size

                gevonden.append({
                    "absoluut": full_path,
                    "relatief": rel_path,
                    "naam": fname,
                    "grootte": size,
                })

    return gevonden


def categorize(bestanden: list[dict]) -> dict[str, list[dict]]:
    """Groepeer bestanden per patroon-categorie."""
    cats = {p: [] for p in TARGET_PATTERNS}
    for f in bestanden:
        lower = f["naam"].lower()
        for pattern in TARGET_PATTERNS:
            if pattern in lower:
                cats[pattern].append(f)
                break  # eerste match wint
    return cats


def format_size(size_bytes: int) -> str:
    """Menselijk leesbare bestandsgrootte."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


def copy_files(bestanden: list[dict], target: Path) -> tuple[int, int, int]:
    """
    Kopieer bestanden naar target met directory-structuur behoud.

    Returns: (gekopieerd, overgeslagen, fouten)
    """
    gekopieerd = 0
    overgeslagen = 0
    fouten = 0

    for f in bestanden:
        src = f["absoluut"]
        # Behoud relatieve padstructuur in target
        dest = target / f["relatief"]

        try:
            # Maak subdirectory aan indien nodig
            dest.parent.mkdir(parents=True, exist_ok=True)

            # Skip als identiek bestand al bestaat (zelfde grootte + mtime)
            if dest.exists():
                src_stat = src.stat()
                dst_stat = dest.stat()
                if (src_stat.st_size == dst_stat.st_size
                        and int(src_stat.st_mtime) == int(dst_stat.st_mtime)):
                    overgeslagen += 1
                    print(
                        f"  {V.DIM}[SKIP]{V.RST} {f['relatief']}"
                        f" {V.DIM}(ongewijzigd){V.RST}"
                    )
                    continue

            # Kopieer met metadata behoud
            shutil.copy2(src, dest)
            gekopieerd += 1
            print(
                f"  {V.GRN}[COPY]{V.RST} {f['relatief']}"
                f" {V.DIM}({format_size(f['grootte'])}){V.RST}"
            )

        except Exception as e:
            fouten += 1
            print(f"  {V.RED}[FOUT]{V.RST} {f['relatief']}: {e}")

    return gekopieerd, overgeslagen, fouten


# === MAIN ===

def main():
    start = time.time()
    banner()

    # --- FASE 1: SCAN ---
    print(f"\n{V.BLD}{V.MAG}  [FASE 1] SCANNING{V.RST}")
    print(V.LINE)

    bestanden = scan_files(ROOT_DIR)

    if not bestanden:
        print(f"\n  {V.YLW}Geen Omega-bestanden gevonden.{V.RST}")
        print(f"  Patronen gezocht: {', '.join(TARGET_PATTERNS)}")
        sys.exit(0)

    # Categoriseer en toon overzicht
    cats = categorize(bestanden)
    totaal_grootte = sum(f["grootte"] for f in bestanden)

    print(f"  {V.GRN}Gevonden: {len(bestanden)} bestanden{V.RST}"
          f" ({format_size(totaal_grootte)})\n")

    for pattern, files in cats.items():
        if files:
            print(
                f"  {V.CYN}{pattern:<16}{V.RST}"
                f" {V.BLD}{len(files):>4}{V.RST} bestanden"
                f" {V.DIM}({format_size(sum(f['grootte'] for f in files))}){V.RST}"
            )

    # --- FASE 2: TARGET SETUP ---
    print(f"\n{V.BLD}{V.MAG}  [FASE 2] TARGET DIRECTORY{V.RST}")
    print(V.LINE)

    created = not TARGET_DIR.exists()
    TARGET_DIR.mkdir(parents=True, exist_ok=True)

    if created:
        print(f"  {V.GRN}[MKDIR]{V.RST} {TARGET_DIR}")
    else:
        print(f"  {V.DIM}[EXISTS]{V.RST} {TARGET_DIR}")

    # --- FASE 3: COPY ---
    print(f"\n{V.BLD}{V.MAG}  [FASE 3] COPYING TO CORE{V.RST}")
    print(V.LINE)

    gekopieerd, overgeslagen, fouten = copy_files(bestanden, TARGET_DIR)

    # --- RAPPORT ---
    duur = time.time() - start

    print(f"\n{V.DLINE}")
    print(f"{V.BLD}{V.CYN}  CONSOLIDATION COMPLETE{V.RST}")
    print(V.DLINE)
    print(f"  {V.GRN}Gekopieerd  : {gekopieerd:>4}{V.RST}")
    if overgeslagen:
        print(f"  {V.DIM}Overgeslagen: {overgeslagen:>4} (ongewijzigd){V.RST}")
    if fouten:
        print(f"  {V.RED}Fouten      : {fouten:>4}{V.RST}")
    print(f"  {V.WHT}Totaal      : {len(bestanden):>4} bestanden"
          f" ({format_size(totaal_grootte)}){V.RST}")
    print(f"  {V.DIM}Duur        : {duur:.2f}s{V.RST}")
    print(f"  {V.DIM}Locatie     : {TARGET_DIR}{V.RST}")
    print(V.DLINE)

    if fouten:
        print(f"\n  {V.RED}LET OP: {fouten} bestand(en) niet gekopieerd!{V.RST}")
        sys.exit(1)
    else:
        print(f"\n  {V.GRN}Omega Sovereign Core is klaar.{V.RST}")
        sys.exit(0)


if __name__ == "__main__":
    main()

"""
Guard Verify — Verificatie van _validate_pad() security gate.
==============================================================
Simuleert 10 pad-validaties tegen TheLibrarian._validate_pad() en
rapporteert of bestanden binnen DOCS_DIR worden geaccepteerd en
bestanden buiten DOCS_DIR worden geblokkeerd.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from danny_toolkit.skills.librarian import TheLibrarian

ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

from config import DOCS_DIR

logger = logging.getLogger(__name__)


def main() -> int:
    """Verifieer _validate_pad() security gate met 10 pad-validaties."""
    librarian = TheLibrarian()
    docs_dir = Path(DOCS_DIR)

    print()
    print("  ╔══════════════════════════════════════════════════════════╗")
    print("  ║   GUARD VERIFY — _validate_pad() Security Gate Check   ║")
    print("  ╠══════════════════════════════════════════════════════════╣")

    # Test 1: Bestanden BINNEN DOCS_DIR → moeten True retourneren
    staging = docs_dir / "quest2_staging"
    if not staging.exists():
        print("  ║  WARN: quest2_staging niet gevonden, skip DOCS_DIR test ║")
        inside_files = []
    else:
        inside_files = list(staging.glob("*.py"))[:5]

    inside_pass = 0
    for f in inside_files:
        result = librarian._validate_pad(f)
        status = "GRANTED" if result else "BLOCKED"
        icon = "✅" if result else "❌"
        print(f"  ║  {icon} {status:>8}  {f.name:<40} ║")
        if result:
            inside_pass += 1

    # Test 2: Bestanden BUITEN DOCS_DIR → moeten False retourneren
    outside_files = [
        ROOT / "danny_toolkit" / "brain" / "synapse.py",
        ROOT / "danny_toolkit" / "core" / "config.py",
        ROOT / "swarm_engine.py",
        ROOT / "danny_toolkit" / "brain" / "central_brain.py",
        ROOT / "fastapi_server.py",
    ]

    outside_block = 0
    for f in outside_files:
        if not f.exists():
            continue
        result = librarian._validate_pad(f)
        status = "BLOCKED" if not result else "GRANTED"
        icon = "✅" if not result else "❌"
        print(f"  ║  {icon} {status:>8}  {f.name:<40} ║")
        if not result:
            outside_block += 1

    print("  ╠══════════════════════════════════════════════════════════╣")
    total_tests = len(inside_files) + len(outside_files)
    total_pass = inside_pass + outside_block
    verdict = "PASS" if total_pass == total_tests else "FAIL"
    print(f"  ║  VERDICT: {verdict}  ({total_pass}/{total_tests} correct)             ║")
    print(f"  ║  Inside DOCS_DIR:  {inside_pass}/{len(inside_files)} GRANTED (expected)         ║")
    print(f"  ║  Outside DOCS_DIR: {outside_block}/{len(outside_files)} BLOCKED (expected)         ║")
    print("  ╚══════════════════════════════════════════════════════════╝")
    print()

    return 0 if total_pass == total_tests else 1


if __name__ == "__main__":
    sys.exit(main())

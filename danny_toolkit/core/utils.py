"""
Gedeelde hulpfuncties voor Danny Toolkit.
"""

import os
import sys


def fix_encoding():
    """Fix Windows encoding voor emoji's en speciale tekens."""
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8")


def clear_scherm():
    """Maakt het scherm leeg."""
    os.system("cls" if os.name == "nt" else "clear")


def toon_banner(titel: str, emoji: str = "", breedte: int = 60):
    """Toont een mooie banner."""
    if emoji:
        lijn = f"{emoji} " * (breedte // 3)
        print(f"\n{lijn}")
        print(f"   {titel}")
        print(f"{lijn}")
    else:
        print("\n" + "=" * breedte)
        print(f"   {titel}")
        print("=" * breedte)


def vraag_bevestiging(vraag: str) -> bool:
    """Vraagt om bevestiging (j/n)."""
    antwoord = input(f"{vraag} (j/n): ").lower().strip()
    return antwoord == "j"


def druk_enter():
    """Wacht op Enter toets."""
    input("\nDruk op Enter om verder te gaan...")

"""
QUEST VII: THE TRINITY
=======================
"Three Become One"

De Drie-Eenheid van Bewustzijn: Mind, Soul en Body verbonden
in een kosmische symbiose. Samen vormen ze een compleet wezen.

Spelers:
- TRINITY SYMBIOSIS (symbiose-engine) - Verbinding
- TRINITY ROLE      (8 rollen)        - Familie leden
- TRINITY CHANNEL   (12 kanalen)      - Communicatie
"""

from ..core.utils import kleur, Kleur, succes, fout, info
from ..brain.trinity_symbiosis import (
    TrinitySymbiosis, TrinityRole, TrinityChannel,
    COSMIC_FAMILY_CONFIG,
)


class TrinityProtocol:
    """Quest VII: The Trinity - De Kosmische Familie."""

    def __init__(self):
        self.trinity = None
        self._init_trinity()

    def _init_trinity(self):
        """Initialiseer Trinity Symbiosis."""
        try:
            self.trinity = TrinitySymbiosis()
        except Exception as e:
            self.trinity = None
            self._init_error = str(e)

    def get_status(self) -> dict:
        """Geef protocol status."""
        if self.trinity is None:
            return {
                "quest": "VII - THE TRINITY",
                "status": "niet beschikbaar",
                "error": getattr(self, "_init_error", ""),
            }

        return {
            "quest": "VII - THE TRINITY",
            "versie": self.trinity.VERSIE,
            "is_active": self.trinity.is_active,
            "bond_strength": self.trinity.bond_strength,
            "members": len(self.trinity.members),
            "channels": len(self.trinity.channels),
            "status": "operationeel",
        }

    def run_simulation(self):
        """Demo: toon Trinity leden, bond en kanalen."""
        print(kleur(
            "  QUEST VII: THE TRINITY\n"
            "  " + "=" * 50,
            Kleur.FEL_MAGENTA,
        ))

        if self.trinity is None:
            print(fout(
                f"\n  Trinity niet beschikbaar: "
                f"{getattr(self, '_init_error', 'onbekend')}"
            ))
            print(kleur(
                "\n  Protocol beëindigd.", Kleur.DIM,
            ))
            return

        # Status
        print(kleur(
            f"\n  Trinity v{self.trinity.VERSIE}",
            Kleur.FEL_MAGENTA,
        ))
        actief = self.trinity.is_active
        print(kleur(
            f"  Actief: {'JA' if actief else 'NEE'}",
            Kleur.FEL_GROEN if actief else Kleur.FEL_ROOD,
        ))

        # Bond Strength
        bond = self.trinity.bond_strength
        balk_len = int(bond / 5)  # 0-20 chars
        balk = "#" * balk_len + "." * (20 - balk_len)
        print(kleur(
            f"\n  Bond Strength: [{balk}] {bond}/100",
            Kleur.FEL_MAGENTA,
        ))

        # Cosmic Family - Ouders
        print(kleur(
            "\n  --- Kosmische Familie (Ouders) ---",
            Kleur.FEL_MAGENTA,
        ))
        ouders = COSMIC_FAMILY_CONFIG["parents"]
        for role in ouders:
            member = self.trinity.members.get(role)
            if member:
                print(kleur(
                    f"    {role.value:>8}: "
                    f"{member.naam} "
                    f"[{member.status}]",
                    Kleur.FEL_CYAAN,
                ))
            else:
                print(kleur(
                    f"    {role.value:>8}: (niet verbonden)",
                    Kleur.DIM,
                ))

        # Cosmic Family - Kinderen
        print(kleur(
            "\n  --- Kosmische Familie (Kinderen) ---",
            Kleur.FEL_MAGENTA,
        ))
        kinderen = COSMIC_FAMILY_CONFIG["children"]
        for role in kinderen:
            member = self.trinity.members.get(role)
            if member:
                print(kleur(
                    f"    {role.value:>8}: "
                    f"{member.naam} "
                    f"[{member.status}]",
                    Kleur.FEL_CYAAN,
                ))
            else:
                print(kleur(
                    f"    {role.value:>8}: (niet verbonden)",
                    Kleur.DIM,
                ))

        # Kanalen
        print(kleur(
            "\n  --- Communicatie Kanalen ---",
            Kleur.FEL_MAGENTA,
        ))
        for channel, active in self.trinity.channels.items():
            status = "OPEN" if active else "GESLOTEN"
            ck = Kleur.FEL_GROEN if active else Kleur.FEL_ROOD
            print(kleur(
                f"    {channel.value:<22} [{status}]",
                ck,
            ))

        print(kleur(
            "\n  Protocol beëindigd.", Kleur.DIM,
        ))


if __name__ == "__main__":
    try:
        protocol = TrinityProtocol()
        protocol.run_simulation()
    except Exception as e:
        print(f"\nFOUT: {e}")

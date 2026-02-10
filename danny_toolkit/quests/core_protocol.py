"""
QUEST I: THE CORE
==================
"The Foundation of All Things"

Het fundament waarop alles gebouwd is: kleuren, utilities,
configuratie en de basisinfrastructuur van het ecosysteem.

Spelers:
- UTILS  (kleur, succes, fout, info) - Terminal communicatie
- KLEUR  (ANSI codes) - Visuele identiteit
- CONFIG (paden, API keys, thema's) - Systeemconfiguratie
"""

from ..core.utils import kleur, Kleur, succes, fout, info
from ..core.config import Config, Thema, Taal


class CoreProtocol:
    """Quest I: The Core - Het fundament van het ecosysteem."""

    def __init__(self):
        self.config = Config
        self.thema = Thema
        self.taal = Taal

    def get_status(self) -> dict:
        """Geef protocol status."""
        return {
            "quest": "I - THE CORE",
            "utils": ["kleur", "succes", "fout", "info"],
            "kleuren": len([
                k for k in dir(Kleur)
                if not k.startswith("_")
            ]),
            "themas": Thema.lijst(),
            "talen": list(Taal.TALEN.keys()),
            "data_dir": str(Config.DATA_DIR),
            "status": "operationeel",
        }

    def run_simulation(self):
        """Demo: test alle core utilities."""
        print(kleur(
            "  QUEST I: THE CORE\n"
            "  " + "=" * 50,
            Kleur.FEL_CYAAN,
        ))

        # Kleur demo
        print(kleur(
            "\n  --- Kleuren Palet ---",
            Kleur.FEL_CYAAN,
        ))
        kleuren_demo = [
            ("FEL_ROOD", Kleur.FEL_ROOD),
            ("FEL_GROEN", Kleur.FEL_GROEN),
            ("FEL_GEEL", Kleur.FEL_GEEL),
            ("FEL_BLAUW", Kleur.FEL_BLAUW),
            ("FEL_MAGENTA", Kleur.FEL_MAGENTA),
            ("FEL_CYAAN", Kleur.FEL_CYAAN),
        ]
        for naam, code in kleuren_demo:
            print(kleur(f"    {naam}", code))

        # Utility functies
        print(kleur(
            "\n  --- Utility Functies ---",
            Kleur.FEL_CYAAN,
        ))
        print(succes("  Test geslaagd!"))
        print(fout("  Test gefaald!"))
        print(info("  Informatief bericht."))

        # Config status
        print(kleur(
            "\n  --- Configuratie ---",
            Kleur.FEL_CYAAN,
        ))
        print(kleur(
            f"    Data dir: {Config.DATA_DIR}",
            Kleur.WIT,
        ))
        print(kleur(
            f"    Thema's:  {', '.join(Thema.lijst())}",
            Kleur.WIT,
        ))
        print(kleur(
            f"    Talen:    {', '.join(Taal.TALEN.keys())}",
            Kleur.WIT,
        ))

        has_groq = bool(Config.GROQ_API_KEY)
        has_anthropic = bool(Config.ANTHROPIC_API_KEY)
        print(kleur(
            f"    Groq key: {'JA' if has_groq else 'NEE'}",
            Kleur.FEL_GROEN if has_groq else Kleur.FEL_ROOD,
        ))
        print(kleur(
            f"    Anthropic key: "
            f"{'JA' if has_anthropic else 'NEE'}",
            Kleur.FEL_GROEN if has_anthropic
            else Kleur.FEL_ROOD,
        ))

        print(kleur(
            "\n  Protocol beëindigd.", Kleur.DIM,
        ))


if __name__ == "__main__":
    try:
        protocol = CoreProtocol()
        protocol.run_simulation()
    except Exception as e:
        print(f"\nFOUT: {e}")

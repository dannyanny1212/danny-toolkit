"""
QUEST V: THE BODY
==================
"The Organism Feeds and Burns"

Het metabolisme van het digitale organisme. Balans tussen
input (voeding) en output (verbranding) bepaalt de gezondheid.

Spelers:
- METABOLISME     (energie-engine)  - Levenskracht
- NUTRIENT LEVELS (5 voedingsstoffen) - Balans
- METABOLIC STATE (7 staten)        - Gezondheid
"""

from ..core.utils import kleur, Kleur, succes, fout, info
from ..daemon.metabolisme import (
    Metabolisme, MetabolicState, NutrientLevels,
)


class BodyProtocol:
    """Quest V: The Body - Het metabolisme."""

    def __init__(self):
        self.metabolisme = None
        self._init_metabolisme()

    def _init_metabolisme(self):
        """Initialiseer het Metabolisme."""
        try:
            self.metabolisme = Metabolisme()
        except Exception as e:
            self.metabolisme = None
            self._init_error = str(e)

    def get_status(self) -> dict:
        """Geef protocol status."""
        if self.metabolisme is None:
            return {
                "quest": "V - THE BODY",
                "status": "niet beschikbaar",
                "error": getattr(self, "_init_error", ""),
            }

        levels = self.metabolisme.nutrients
        state = self.metabolisme.state
        return {
            "quest": "V - THE BODY",
            "state": state.value,
            "levels": levels.to_dict(),
            "balance": round(levels.balance_score, 2),
            "gemiddeld": round(levels.total, 1),
            "status": "operationeel",
        }

    def run_simulation(self):
        """Demo: toon metabolische staat en niveaus."""
        print(kleur(
            "  QUEST V: THE BODY\n"
            "  " + "=" * 50,
            Kleur.FEL_GROEN,
        ))

        if self.metabolisme is None:
            print(fout(
                f"\n  Metabolisme niet beschikbaar: "
                f"{getattr(self, '_init_error', 'onbekend')}"
            ))
            print(kleur(
                "\n  Protocol beëindigd.", Kleur.DIM,
            ))
            return

        # Metabolische staat
        state = self.metabolisme.state
        state_kleuren = {
            MetabolicState.THRIVING: Kleur.FEL_MAGENTA,
            MetabolicState.GROWING: Kleur.FEL_GROEN,
            MetabolicState.STABLE: Kleur.FEL_CYAAN,
            MetabolicState.HUNGRY: Kleur.FEL_GEEL,
            MetabolicState.STARVING: Kleur.FEL_ROOD,
            MetabolicState.BLOATED: Kleur.FEL_GEEL,
            MetabolicState.BURNING: Kleur.FEL_ROOD,
        }
        sk = state_kleuren.get(state, Kleur.WIT)
        print(kleur(
            f"\n  Metabolische Staat: {state.value}",
            sk,
        ))

        # Nutriënt levels
        levels = self.metabolisme.nutrients
        print(kleur(
            "\n  --- Voedingsstoffen ---",
            Kleur.FEL_GROEN,
        ))

        nutrients = [
            ("Protein  (kennis)", levels.protein),
            ("Carbs    (energie)", levels.carbs),
            ("Vitamins (code)", levels.vitamins),
            ("Water    (rust)", levels.water),
            ("Fiber    (balans)", levels.fiber),
        ]

        for naam, waarde in nutrients:
            balk_len = int(waarde / 5)  # 0-20 chars
            balk = "#" * balk_len + "." * (20 - balk_len)
            if waarde >= 60:
                nk = Kleur.FEL_GROEN
            elif waarde >= 30:
                nk = Kleur.FEL_GEEL
            else:
                nk = Kleur.FEL_ROOD
            print(kleur(
                f"    {naam}: [{balk}] "
                f"{waarde:.0f}/100",
                nk,
            ))

        # Balans score
        print(kleur(
            f"\n  Balans Score: "
            f"{levels.balance_score:.2f}",
            Kleur.WIT,
        ))
        print(kleur(
            f"  Gemiddeld Niveau: {levels.total:.1f}",
            Kleur.WIT,
        ))

        # Alle mogelijke staten
        print(kleur(
            "\n  --- Mogelijke Staten ---",
            Kleur.FEL_GROEN,
        ))
        for ms in MetabolicState:
            marker = " <--" if ms == state else ""
            print(kleur(
                f"    {ms.value:>10}{marker}",
                Kleur.WIT,
            ))

        print(kleur(
            "\n  Protocol beëindigd.", Kleur.DIM,
        ))


if __name__ == "__main__":
    try:
        protocol = BodyProtocol()
        protocol.run_simulation()
    except Exception as e:
        print(f"\nFOUT: {e}")

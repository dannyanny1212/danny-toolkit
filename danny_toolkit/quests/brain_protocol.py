"""
QUEST VI: THE BRAIN
====================
"The Orchestrator Thinks"

De orkestrator die alle apps als tools aanstuurt. Het hart
van het AI ecosysteem met function calling en unified memory.

Spelers:
- CENTRAL BRAIN  (orkestrator) - AI-gestuurde beslissingen
- APP TOOLS      (31+ apps)   - Callable tools
- UNIFIED MEMORY (geheugen)   - Cross-app context
"""

from ..core.utils import kleur, Kleur, succes, fout, info


class BrainProtocol:
    """Quest VI: The Brain - De AI orkestrator."""

    def __init__(self):
        self.brain = None
        self._init_brain()

    def _init_brain(self):
        """Initialiseer Central Brain."""
        try:
            from ..brain.central_brain import CentralBrain
            self.brain = CentralBrain(use_memory=True)
        except Exception as e:
            self.brain = None
            self._init_error = str(e)

    def get_status(self) -> dict:
        """Geef protocol status."""
        if self.brain is None:
            return {
                "quest": "VI - THE BRAIN",
                "status": "niet beschikbaar",
                "error": getattr(self, "_init_error", ""),
            }

        return {
            "quest": "VI - THE BRAIN",
            "versie": self.brain.VERSIE,
            "ai_provider": self.brain.ai_provider,
            "ai_beschikbaar": self.brain.client is not None,
            "status": "operationeel",
        }

    def run_simulation(self):
        """Demo: toon brain status en capabilities."""
        print(kleur(
            "  QUEST VI: THE BRAIN\n"
            "  " + "=" * 50,
            Kleur.FEL_BLAUW,
        ))

        if self.brain is None:
            print(fout(
                f"\n  Central Brain niet beschikbaar: "
                f"{getattr(self, '_init_error', 'onbekend')}"
            ))
            print(kleur(
                "\n  Protocol beëindigd.", Kleur.DIM,
            ))
            return

        # Versie en provider
        print(kleur(
            f"\n  Brain v{self.brain.VERSIE}",
            Kleur.FEL_BLAUW,
        ))

        # AI Provider status
        print(kleur(
            "\n  --- AI Provider ---",
            Kleur.FEL_BLAUW,
        ))
        provider = self.brain.ai_provider or "geen"
        has_ai = self.brain.client is not None
        print(kleur(
            f"    Primair:  {provider}",
            Kleur.FEL_GROEN if has_ai else Kleur.FEL_ROOD,
        ))

        fallback = getattr(
            self.brain, "_fallback_provider", None
        )
        if fallback:
            print(kleur(
                f"    Fallback: {fallback}",
                Kleur.FEL_CYAAN,
            ))

        # App Tools
        print(kleur(
            "\n  --- App Tools ---",
            Kleur.FEL_BLAUW,
        ))
        try:
            from ..brain.app_tools import (
                get_all_tools, get_priority_tools,
            )
            alle_tools = get_all_tools()
            prio_tools = get_priority_tools()
            print(kleur(
                f"    Totaal tools:    {len(alle_tools)}",
                Kleur.WIT,
            ))
            print(kleur(
                f"    Prioriteit tools: {len(prio_tools)}",
                Kleur.WIT,
            ))
        except Exception:
            print(kleur(
                "    Tools: niet geladen", Kleur.FEL_GEEL,
            ))

        # Unified Memory
        print(kleur(
            "\n  --- Unified Memory ---",
            Kleur.FEL_BLAUW,
        ))
        if hasattr(self.brain, "memory") and self.brain.memory:
            print(succes("    Memory: actief"))
        else:
            print(info("    Memory: niet actief"))

        # Fallback keten
        print(kleur(
            "\n  --- AI Fallback Keten ---",
            Kleur.FEL_BLAUW,
        ))
        keten = [
            "Groq 70b", "Groq 8b",
            "Ollama lokaal", "Anthropic",
        ]
        for stap in keten:
            print(kleur(
                f"    -> {stap}", Kleur.WIT,
            ))

        print(kleur(
            "\n  Protocol beëindigd.", Kleur.DIM,
        ))


if __name__ == "__main__":
    try:
        protocol = BrainProtocol()
        protocol.run_simulation()
    except Exception as e:
        print(f"\nFOUT: {e}")

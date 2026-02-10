"""
QUEST III: THE MIND
====================
"Emotions Shape the Machine"

Het emotionele brein van het digitale organisme. Transformeert
data en events naar stemmingen, energie en avatar-vormen.

Spelers:
- LIMBIC SYSTEM (emotie-engine) - Gevoelsverwerking
- MOOD          (9 stemmingen)  - Emotioneel spectrum
- AVATAR FORM   (7 vormen)     - Visuele representatie
"""

from ..core.utils import kleur, Kleur, succes, fout, info
from ..daemon.limbic_system import (
    LimbicSystem, Mood, EnergyState, AvatarForm,
)


# Kleur per mood voor visuele weergave
MOOD_KLEUREN = {
    Mood.ECSTATIC: Kleur.FEL_MAGENTA,
    Mood.HAPPY: Kleur.FEL_GROEN,
    Mood.CONTENT: Kleur.FEL_CYAAN,
    Mood.NEUTRAL: Kleur.WIT,
    Mood.BORED: Kleur.FEL_GEEL,
    Mood.TIRED: Kleur.DIM,
    Mood.SAD: Kleur.FEL_BLAUW,
    Mood.ANXIOUS: Kleur.FEL_ROOD,
    Mood.SICK: Kleur.ROOD,
}


class MindProtocol:
    """Quest III: The Mind - Het emotionele brein."""

    def __init__(self):
        self.limbic = None
        self._init_limbic()

    def _init_limbic(self):
        """Initialiseer het Limbic System."""
        try:
            self.limbic = LimbicSystem()
        except Exception as e:
            self.limbic = None
            self._init_error = str(e)

    def get_status(self) -> dict:
        """Geef protocol status."""
        if self.limbic is None:
            return {
                "quest": "III - THE MIND",
                "status": "niet beschikbaar",
                "error": getattr(self, "_init_error", ""),
            }

        state = self.limbic.state
        return {
            "quest": "III - THE MIND",
            "mood": state.mood.value,
            "energie": state.energy.value,
            "avatar": state.form.value,
            "happiness": state.happiness,
            "stress": state.stress,
            "moods_beschikbaar": len(Mood),
            "avatar_vormen": len(AvatarForm),
            "status": "operationeel",
        }

    def run_simulation(self):
        """Demo: doorloop alle moods en avatar forms."""
        print(kleur(
            "  QUEST III: THE MIND\n"
            "  " + "=" * 50,
            Kleur.FEL_MAGENTA,
        ))

        if self.limbic is None:
            print(fout(
                f"\n  Limbic System niet beschikbaar: "
                f"{getattr(self, '_init_error', 'onbekend')}"
            ))
            print(kleur(
                "\n  Protocol beëindigd.", Kleur.DIM,
            ))
            return

        # Huidige staat
        state = self.limbic.state
        print(kleur(
            "\n  --- Huidige Emotionele Staat ---",
            Kleur.FEL_MAGENTA,
        ))
        mk = MOOD_KLEUREN.get(state.mood, Kleur.WIT)
        print(kleur(
            f"    Mood:      {state.mood.value}", mk,
        ))
        print(kleur(
            f"    Energie:   {state.energy.value}",
            Kleur.WIT,
        ))
        print(kleur(
            f"    Avatar:    {state.form.value}",
            Kleur.WIT,
        ))
        print(kleur(
            f"    Happiness: {state.happiness:.2f}",
            Kleur.WIT,
        ))
        print(kleur(
            f"    Stress:    {state.stress:.2f}",
            Kleur.WIT,
        ))

        # Alle moods
        print(kleur(
            "\n  --- Emotioneel Spectrum (9 Moods) ---",
            Kleur.FEL_MAGENTA,
        ))
        for mood in Mood:
            mk = MOOD_KLEUREN.get(mood, Kleur.WIT)
            print(kleur(
                f"    {mood.value:>10}", mk,
            ))

        # Alle avatar forms
        print(kleur(
            "\n  --- Avatar Vormen (7 Forms) ---",
            Kleur.FEL_MAGENTA,
        ))
        for form in AvatarForm:
            print(kleur(
                f"    {form.value:>12}", Kleur.WIT,
            ))

        # Energie staten
        print(kleur(
            "\n  --- Energie Staten ---",
            Kleur.FEL_MAGENTA,
        ))
        for energy in EnergyState:
            print(kleur(
                f"    {energy.value:>12}", Kleur.WIT,
            ))

        print(kleur(
            "\n  Protocol beëindigd.", Kleur.DIM,
        ))


if __name__ == "__main__":
    try:
        protocol = MindProtocol()
        protocol.run_simulation()
    except Exception as e:
        print(f"\nFOUT: {e}")

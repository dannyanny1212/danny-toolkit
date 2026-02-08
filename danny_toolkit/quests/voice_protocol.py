"""
Quest X: THE VOICE - De Stem van God.

Geeft Pixel een stem die verandert op basis van daemon mood.
Brug tussen Daemon Mood en EmotionalVoice engine.

Mood -> Emotion mapping:
  ECSTATIC -> EXCITED   (Hoog, snel, expressief)
  HAPPY    -> HAPPY     (Warm, licht sneller)
  CONTENT  -> NEUTRAL   (Stabiel, rustig)
  NEUTRAL  -> NEUTRAL   (Standaard)
  BORED    -> TIRED     (Traag, monotoon)
  TIRED    -> TIRED     (Langzaam, laag)
  SAD      -> SAD       (Diep, langzaam)
  ANXIOUS  -> WORRIED   (Sneller, onstabiel)
  SICK     -> SAD       (Diep, zwak)
"""

from ..core.utils import kleur, Kleur, info, succes, fout
from ..core.emotional_voice import EmotionalVoice, Emotion
from ..daemon.limbic_system import Mood


# Voorbeeldzinnen per mood (Nederlands)
MOOD_ZINNEN = {
    Mood.ECSTATIC: "Dit is ongelofelijk! Alles werkt perfect!",
    Mood.HAPPY: "Goedemorgen Danny! Fijne dag vandaag.",
    Mood.CONTENT: "Systemen draaien normaal. Alles onder controle.",
    Mood.NEUTRAL: "Ik luister. Wat wil je weten?",
    Mood.BORED: "Hmm... er is niet veel te doen...",
    Mood.TIRED: "Ik ben moe... maar ik help je graag.",
    Mood.SAD: "Het spijt me... er ging iets mis.",
    Mood.ANXIOUS: "Let op! Er is iets dat aandacht nodig heeft!",
    Mood.SICK: "Systeem is niet in orde... diagnose bezig.",
}


class VoiceProtocol:
    """Quest X: The Voice - Geef Pixel een stem."""

    MOOD_TO_EMOTION = {
        Mood.ECSTATIC: Emotion.EXCITED,
        Mood.HAPPY: Emotion.HAPPY,
        Mood.CONTENT: Emotion.NEUTRAL,
        Mood.NEUTRAL: Emotion.NEUTRAL,
        Mood.BORED: Emotion.TIRED,
        Mood.TIRED: Emotion.TIRED,
        Mood.SAD: Emotion.SAD,
        Mood.ANXIOUS: Emotion.WORRIED,
        Mood.SICK: Emotion.SAD,
    }

    def __init__(self):
        self.voice = EmotionalVoice(preferred_voice="nl")

    def mood_to_emotion(self, mood: Mood) -> Emotion:
        """Vertaal daemon mood naar voice emotion."""
        return self.MOOD_TO_EMOTION.get(mood, Emotion.NEUTRAL)

    def speak(self, text, mood=None):
        """Spreek tekst met mood-bepaalde emotie."""
        if mood is not None:
            emotion = self.mood_to_emotion(mood)
        else:
            emotion = None  # Auto-detect door voice engine
        self.voice.speak(text, emotion=emotion)

    def get_status(self):
        """Toon voice engine status."""
        return self.voice.get_status()

    def run_simulation(self):
        """Demo: doorloop alle 9 moods met voorbeeldzinnen."""
        print(kleur(
            "  QUEST X: THE VOICE - Mood Simulatie\n"
            "  " + "=" * 50,
            Kleur.FEL_MAGENTA,
        ))

        status = self.get_status()
        backend = status["active_backend"]
        print(kleur(
            f"\n  Backend: {backend}",
            Kleur.FEL_CYAAN,
        ))

        if backend == "none":
            print(fout(
                "\n  Geen voice backend beschikbaar!"
                "\n  Installeer: pip install edge-tts"
                " of pip install pyttsx3"
            ))
            print(info(
                "\n  Simulatie draait in tekst-modus...\n"
            ))

        print()

        for mood in Mood:
            emotion = self.mood_to_emotion(mood)
            zin = MOOD_ZINNEN.get(mood, "...")

            # Mood label met kleur
            mood_kleuren = {
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
            mk = mood_kleuren.get(mood, Kleur.WIT)

            print(kleur(
                f"  [{mood.value:>8}] -> {emotion.value:<8}"
                f"  \"{zin}\"",
                mk,
            ))

            if backend != "none":
                try:
                    self.voice.speak(zin, emotion=emotion)
                except Exception as e:
                    print(fout(f"    Fout: {e}"))

        print(kleur(
            "\n  " + "=" * 50,
            Kleur.FEL_MAGENTA,
        ))

        # Interactief: gebruiker kan zelf tekst invoeren
        print(kleur(
            "\n  Typ tekst om te spreken (leeg = stop):\n",
            Kleur.FEL_CYAAN,
        ))

        while True:
            try:
                tekst = input(
                    kleur("  Tekst: ", Kleur.FEL_GROEN)
                ).strip()
            except (EOFError, KeyboardInterrupt):
                break

            if not tekst:
                break

            # Spreek met auto-detect emotie
            self.speak(tekst)

        print(kleur(
            "\n  Voice simulatie beeindigd.",
            Kleur.DIM,
        ))

"""
Quest XII: THE DIALOGUE - Pixel Converseert.

Continue spraakdialoog: Pixel luistert, verwerkt, antwoordt
met stem, en luistert weer. Hands-free gesprekken.

De kroon op de voice-loop:
  Quest X (stem) + Quest XI (oren) = Quest XII (gesprek)

  [Danny spreekt] -> microfoon -> herkenning ->
  OmegaAI._verwerk_input() -> daemon response ->
  Pixel spreekt antwoord -> [luistert weer] -> ...

Dependencies (hergebruikt, geen nieuwe):
  SpeechRecognition + PyAudio (Quest XI)
  edge-tts / pyttsx3 (Quest X)
"""

from ..core.utils import kleur, Kleur, info, succes, fout


class DialogueProtocol:
    """Quest XII: The Dialogue - Pixel converseert."""

    def __init__(self):
        self._listener = None  # Lazy ListenerProtocol
        self._voice = None     # Lazy VoiceProtocol
        self.actief = False
        self.rondes = 0
        self.geschiedenis = []  # Lijst van (danny, pixel) tuples

    def _get_listener(self):
        """Lazy-init listener."""
        if self._listener is None:
            from .listener_protocol import ListenerProtocol
            self._listener = ListenerProtocol()
        return self._listener

    def _get_voice(self):
        """Lazy-init voice."""
        if self._voice is None:
            from .voice_protocol import VoiceProtocol
            self._voice = VoiceProtocol()
        return self._voice

    def get_status(self) -> dict:
        """Return dialogue status."""
        listener = self._get_listener()
        voice = self._get_voice()
        return {
            "actief": self.actief,
            "rondes": self.rondes,
            "listener_backend": listener.active_backend,
            "voice_backend": (
                voice.get_status()["active_backend"]
            ),
            "geschiedenis_lengte": len(self.geschiedenis),
        }

    def can_start(self) -> tuple[bool, str]:
        """Check of dialoog mogelijk is."""
        listener = self._get_listener()
        if listener.active_backend == "none":
            return False, (
                "Geen listener backend!"
                "\npip install SpeechRecognition pyaudio"
            )
        return True, "Gereed"

    def start(self, verwerk_fn=None, mood_fn=None):
        """
        Start continue dialoog-modus.

        Args:
            verwerk_fn: Callback(tekst) -> response string
                        (bijv. OmegaAI._verwerk_input)
            mood_fn:    Callback() -> Mood
                        (bijv. OmegaAI._get_mood)
        """
        listener = self._get_listener()
        voice = self._get_voice()
        voice_status = voice.get_status()
        has_voice = voice_status["active_backend"] != "none"

        self.actief = True
        self.rondes = 0

        # Banner
        print(kleur(
            "  QUEST XII: THE DIALOGUE\n"
            "  " + "=" * 50 + "\n"
            "\n"
            "  Pixel converseert. Spreek vrijuit.\n"
            "  Ctrl+C = stop dialoog\n",
            Kleur.FEL_MAGENTA,
        ))

        # Status
        print(kleur(
            f"  Listener: {listener.active_backend}",
            Kleur.CYAAN,
        ))
        print(kleur(
            f"  Voice:    {voice_status['active_backend']}",
            Kleur.CYAAN,
        ))
        print()

        while self.actief:
            self.rondes += 1
            try:
                # 1. Luister
                print(kleur(
                    f"  [{self.rondes}] ",
                    Kleur.DIM,
                ), end="")

                tekst = listener.listen(timeout=8)

                if not tekst:
                    print(info("Niets gehoord..."))
                    continue

                print(succes(f"Danny: \"{tekst}\""))

                # 2. Verwerk
                if verwerk_fn:
                    response = verwerk_fn(tekst)
                else:
                    response = f"Ik hoorde: {tekst}"

                # 3. Toon antwoord
                mood = mood_fn() if mood_fn else None
                print(kleur(
                    f"      Pixel: \"{response}\"",
                    Kleur.FEL_MAGENTA,
                ))

                # 4. Spreek antwoord
                if has_voice:
                    voice.speak(response, mood)

                # 5. Bewaar in geschiedenis
                self.geschiedenis.append(
                    (tekst, response)
                )

            except KeyboardInterrupt:
                self.actief = False

        # Einde
        print(kleur(
            f"\n  Dialoog beeindigd na"
            f" {self.rondes} rondes.",
            Kleur.DIM,
        ))
        if self.geschiedenis:
            print(kleur(
                f"  {len(self.geschiedenis)}"
                " uitwisselingen opgeslagen.",
                Kleur.DIM,
            ))

    def run_simulation(self):
        """Demo zonder OmegaAI koppeling."""
        kan, reden = self.can_start()
        if not kan:
            print(fout(f"  {reden}"))
            return

        # Start zonder verwerk_fn -> echo mode
        self.start(verwerk_fn=None, mood_fn=None)

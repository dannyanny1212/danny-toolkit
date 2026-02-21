"""
Quest XI: THE LISTENER - Pixel Hoort Danny.

Spraakherkenning via microfoon. Sluit de voice-loop:
  microfoon -> herkenning -> verwerking -> gesproken antwoord

Backend prioriteit:
  1. speech_recognition + Google STT (gratis, online)
  2. vosk (offline, vereist model download)
  3. none (graceful degrade)

Dependencies (optioneel, graceful degrade):
  pip install SpeechRecognition pyaudio
  pip install vosk  (+ model download voor offline)
"""

import logging

from ..core.utils import kleur, Kleur, info, succes, fout

logger = logging.getLogger(__name__)


class ListenerProtocol:
    """Quest XI: The Listener - Pixel hoort Danny."""

    def __init__(self):
        self._sr_available = self._check_speech_recognition()
        self._vosk_available = self._check_vosk()
        self.active_backend = self._select_backend()
        self._voice = None  # Lazy VoiceProtocol

    def _check_speech_recognition(self) -> bool:
        """Check of speech_recognition + PyAudio beschikbaar."""
        try:
            import speech_recognition
            # Test of PyAudio werkt (microfoon)
            speech_recognition.Recognizer()
            speech_recognition.Microphone()
            return True
        except (ImportError, OSError, AttributeError):
            return False

    def _check_vosk(self) -> bool:
        """Check of vosk beschikbaar is."""
        try:
            import vosk  # noqa: F401
            return True
        except ImportError:
            return False

    def _select_backend(self) -> str:
        """Selecteer beste beschikbare backend."""
        if self._sr_available:
            return "speech_recognition"
        elif self._vosk_available:
            return "vosk"
        else:
            return "none"

    def _get_voice(self):
        """Lazy-init voice voor gesproken antwoord."""
        if self._voice is None:
            from .voice_protocol import VoiceProtocol
            self._voice = VoiceProtocol()
        return self._voice

    def listen(self, timeout=5, taal="nl-NL") -> str | None:
        """
        Luister via microfoon, retourneer herkende tekst.
        Returns None als niets herkend.
        """
        if self.active_backend == "speech_recognition":
            return self._listen_sr(timeout, taal)
        elif self.active_backend == "vosk":
            return self._listen_vosk(timeout, taal)
        else:
            return None

    def _listen_sr(self, timeout, taal) -> str | None:
        """Luister via speech_recognition + Google STT."""
        import speech_recognition as sr

        r = sr.Recognizer()
        with sr.Microphone() as source:
            r.adjust_for_ambient_noise(source, duration=0.5)
            print(info("  Luisteren..."))
            try:
                audio = r.listen(
                    source,
                    timeout=timeout,
                    phrase_time_limit=15,
                )
            except sr.WaitTimeoutError:
                return None

        try:
            tekst = r.recognize_google(audio, language=taal)
            return tekst
        except (sr.UnknownValueError, sr.RequestError):
            return None

    def _listen_vosk(self, timeout, taal) -> str | None:
        """Luister via vosk (offline)."""
        try:
            import vosk
            import json as _json
            import pyaudio
        except ImportError:
            return None

        # Zoek vosk model
        from pathlib import Path
        model_pad = Path.home() / ".vosk" / "model"
        if not model_pad.exists():
            print(fout(
                "  Vosk model niet gevonden."
                f"\n  Verwacht in: {model_pad}"
                "\n  Download een model van:"
                "\n  https://alphacephei.com/vosk/models"
            ))
            return None

        try:
            model = vosk.Model(str(model_pad))
        except Exception as e:
            print(fout(f"  Vosk model fout: {e}"))
            return None

        rec = vosk.KaldiRecognizer(model, 16000)

        p = pyaudio.PyAudio()
        stream = p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            input=True,
            frames_per_buffer=8000,
        )
        stream.start_stream()

        print(info("  Luisteren (vosk)..."))

        import time
        start = time.time()
        tekst = None

        try:
            while time.time() - start < timeout:
                data = stream.read(4000, exception_on_overflow=False)
                if rec.AcceptWaveform(data):
                    result = _json.loads(rec.Result())
                    if result.get("text"):
                        tekst = result["text"]
                        break

            # Check partial result
            if tekst is None:
                result = _json.loads(rec.FinalResult())
                if result.get("text"):
                    tekst = result["text"]
        finally:
            stream.stop_stream()
            stream.close()
            p.terminate()

        return tekst

    def get_status(self) -> dict:
        """Return backend status."""
        return {
            "active_backend": self.active_backend,
            "speech_recognition": self._sr_available,
            "vosk": self._vosk_available,
        }

    def listen_and_respond(self, mood=None):
        """
        Luister -> herken tekst -> spreek antwoord terug.
        De volledige voice-loop.
        """
        tekst = self.listen()
        if tekst:
            print(succes(f"  Gehoord: \"{tekst}\""))
            # Spreek bevestiging terug
            voice = self._get_voice()
            voice.speak(f"Ik hoorde: {tekst}", mood)
            return tekst
        else:
            print(info("  Niets gehoord."))
            return None

    def run_simulation(self):
        """
        Demo: test microfoon en spraakherkenning.
        1. Toon backend status
        2. Luister-loop: gebruiker spreekt, Pixel herhaalt
        3. Optie: volledige voice-loop (luister + antwoord)
        """
        print(kleur(
            "  QUEST XI: THE LISTENER"
            " - Spraakherkenning Demo\n"
            "  " + "=" * 50,
            Kleur.FEL_CYAAN,
        ))

        status = self.get_status()
        backend = status["active_backend"]
        print(kleur(
            f"\n  Backend: {backend}",
            Kleur.FEL_CYAAN,
        ))

        if backend == "none":
            print(fout(
                "\n  Geen listener backend beschikbaar!"
                "\n  Installeer:"
                "\n    pip install SpeechRecognition pyaudio"
                "\n  Of voor offline:"
                "\n    pip install vosk"
            ))
            print(info(
                "\n  Simulatie kan niet draaien"
                " zonder microfoon-backend."
            ))
            return

        sr_status = "ACTIEF" if status["speech_recognition"] else "—"
        vosk_status = "ACTIEF" if status["vosk"] else "—"
        print(kleur(
            f"  speech_recognition: {sr_status}",
            Kleur.CYAAN,
        ))
        print(kleur(
            f"  vosk:               {vosk_status}",
            Kleur.CYAAN,
        ))

        print(kleur(
            "\n  Spreek iets (Ctrl+C = stop):\n",
            Kleur.FEL_GROEN,
        ))

        ronde = 0
        while True:
            ronde += 1
            try:
                print(kleur(
                    f"  [{ronde}] ",
                    Kleur.DIM,
                ), end="")

                tekst = self.listen()
                if tekst:
                    print(succes(
                        f"      Gehoord: \"{tekst}\""
                    ))
                    # Probeer terug te spreken
                    try:
                        voice = self._get_voice()
                        voice_status = voice.get_status()
                        if voice_status["active_backend"] != "none":
                            voice.speak(
                                f"Ik hoorde: {tekst}"
                            )
                            print(kleur(
                                f"      Pixel: "
                                f"\"Ik hoorde: {tekst}\"",
                                Kleur.FEL_MAGENTA,
                            ))
                    except Exception as e:
                        logger.debug("Voice playback failed during listener simulation: %s", e)
                else:
                    print(info("      Niets gehoord."))

            except KeyboardInterrupt:
                break

        print(kleur(
            "\n  Listener simulatie beeindigd.",
            Kleur.DIM,
        ))

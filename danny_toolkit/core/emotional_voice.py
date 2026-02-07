"""
Emotional Voice Engine - Audio-First Upgrade voor Legendary Companion.

Detecteert emotie in tekst en genereert spraak met emotionele modulatie.
Ondersteunt: ElevenLabs (premium), Edge-TTS (gratis), pyttsx3 (offline).
"""

import os
import re
import json
import tempfile
import subprocess
from pathlib import Path
from typing import Optional, Tuple, Dict
from dataclasses import dataclass
from enum import Enum

from .config import Config


class Emotion(Enum):
    """Emoties voor stem modulatie."""
    NEUTRAL = "neutral"
    HAPPY = "happy"
    EXCITED = "excited"
    SAD = "sad"
    TIRED = "tired"
    CURIOUS = "curious"
    PROUD = "proud"
    WORRIED = "worried"


@dataclass
class VoiceSettings:
    """Stem instellingen per emotie."""
    stability: float = 0.5      # 0-1, hoger = stabieler
    similarity: float = 0.75   # 0-1, hoger = meer zoals origineel
    style: float = 0.5         # 0-1, hoger = meer expressief
    speed: float = 1.0         # 0.5-2.0, spraaksnelheid
    pitch: str = "default"     # voor edge-tts


# Emotie-specifieke stem instellingen
EMOTION_VOICE_MAP: Dict[Emotion, VoiceSettings] = {
    Emotion.NEUTRAL: VoiceSettings(
        stability=0.7, similarity=0.75, style=0.3, speed=1.0
    ),
    Emotion.HAPPY: VoiceSettings(
        stability=0.5, similarity=0.7, style=0.8, speed=1.1, pitch="+5Hz"
    ),
    Emotion.EXCITED: VoiceSettings(
        stability=0.3, similarity=0.6, style=1.0, speed=1.2, pitch="+10Hz"
    ),
    Emotion.SAD: VoiceSettings(
        stability=0.8, similarity=0.8, style=0.2, speed=0.85, pitch="-5Hz"
    ),
    Emotion.TIRED: VoiceSettings(
        stability=0.9, similarity=0.8, style=0.1, speed=0.8, pitch="-3Hz"
    ),
    Emotion.CURIOUS: VoiceSettings(
        stability=0.5, similarity=0.7, style=0.6, speed=1.05, pitch="+3Hz"
    ),
    Emotion.PROUD: VoiceSettings(
        stability=0.6, similarity=0.75, style=0.7, speed=0.95
    ),
    Emotion.WORRIED: VoiceSettings(
        stability=0.4, similarity=0.7, style=0.5, speed=1.1, pitch="+2Hz"
    ),
}


class SentimentAnalyzer:
    """Analyseert sentiment/emotie in tekst."""

    # Keyword patronen per emotie
    PATTERNS = {
        Emotion.HAPPY: [
            r'\b(blij|happy|geweldig|fantastisch|super|leuk|fijn|mooi)\b',
            r'\b(gelukt|succes|gevonden|klaar|perfect|top)\b',
            r'[!]{2,}',  # Meerdere uitroeptekens
            r'[:;]-?\)',  # Smiley
        ],
        Emotion.EXCITED: [
            r'\b(wow|wauw|ongelofelijk|amazing|epic|legendary)\b',
            r'\b(nieuw|ontdekt|eureka|breakthrough|doorbraak)\b',
            r'[!]{3,}',  # Veel uitroeptekens
            r'\b(evolutie|level.?up|upgrade)\b',
        ],
        Emotion.SAD: [
            r'\b(helaas|jammer|sorry|spijt|niet.?gevonden|mislukt)\b',
            r'\b(fout|error|probleem|kapot|verloren)\b',
            r'[:;]-?\(',  # Sad smiley
        ],
        Emotion.TIRED: [
            r'\b(moe|vermoeid|uitgeput|slaperig|langzaam)\b',
            r'\b(wachten|laden|processing|bezig)\b',
            r'\.{3,}',  # Ellipsis
        ],
        Emotion.CURIOUS: [
            r'\?{2,}',  # Meerdere vraagtekens
            r'\b(interessant|vraag|waarom|hoe|wat.?als)\b',
            r'\b(onderzoek|analyse|kijk.?eens|misschien)\b',
        ],
        Emotion.PROUD: [
            r'\b(bereikt|voltooid|gewonnen|record|beste)\b',
            r'\b(trots|achievement|milestone|prestatie)\b',
            r'\b(xp|punten|level|rank)\b.*\b(omhoog|gestegen|verdiend)\b',
        ],
        Emotion.WORRIED: [
            r'\b(pas.?op|waarschuwing|let.?op|gevaar|risico)\b',
            r'\b(bijna|dreigt|zou.?kunnen|misschien.?niet)\b',
            r'\b(streak|deadline|tijd|verlopen)\b',
        ],
    }

    @classmethod
    def analyze(cls, text: str) -> Tuple[Emotion, float]:
        """
        Analyseer tekst en bepaal emotie.

        Returns:
            Tuple van (Emotion, confidence 0-1)
        """
        text_lower = text.lower()
        scores: Dict[Emotion, int] = {e: 0 for e in Emotion}

        for emotion, patterns in cls.PATTERNS.items():
            for pattern in patterns:
                matches = re.findall(pattern, text_lower, re.IGNORECASE)
                scores[emotion] += len(matches)

        # Vind hoogste score
        max_emotion = max(scores, key=scores.get)
        max_score = scores[max_emotion]

        if max_score == 0:
            return Emotion.NEUTRAL, 0.5

        # Bereken confidence (genormaliseerd)
        total = sum(scores.values())
        confidence = min(0.95, 0.5 + (max_score / max(total, 1)) * 0.5)

        return max_emotion, confidence


class EmotionalVoice:
    """
    Emotionele Text-to-Speech engine.

    Ondersteunt meerdere backends met automatische fallback:
    1. ElevenLabs (premium, beste kwaliteit)
    2. Edge-TTS (gratis, goede kwaliteit)
    3. pyttsx3 (offline, basis kwaliteit)
    """

    # Edge-TTS Nederlandse stemmen
    EDGE_VOICES = {
        "nl": "nl-NL-ColetteNeural",  # Vrouwelijk, warm
        "nl_male": "nl-NL-MaartenNeural",  # Mannelijk
        "en": "en-US-AriaNeural",  # Engels fallback
    }

    # ElevenLabs stem IDs (voorbeelden - gebruiker kan eigen stem toevoegen)
    ELEVENLABS_VOICES = {
        "default": "21m00Tcm4TlvDq8ikWAM",  # Rachel
        "warm": "EXAVITQu4vr4xnSDxMaL",  # Bella
    }

    def __init__(self, preferred_voice: str = "nl"):
        """
        Initialiseer de voice engine.

        Args:
            preferred_voice: Taal/stem voorkeur ("nl", "nl_male", "en")
        """
        self.preferred_voice = preferred_voice
        self.sentiment = SentimentAnalyzer()
        self.audio_dir = Config.DATA_DIR / "audio"
        self.audio_dir.mkdir(exist_ok=True)

        # Detecteer beschikbare backends
        self._elevenlabs_available = self._check_elevenlabs()
        self._edge_tts_available = self._check_edge_tts()
        self._pyttsx3_available = self._check_pyttsx3()

        self.active_backend = self._select_backend()

    def _check_elevenlabs(self) -> bool:
        """Check of ElevenLabs beschikbaar is."""
        if not Config.has_elevenlabs_key():
            return False
        try:
            import requests
            return True
        except ImportError:
            return False

    def _check_edge_tts(self) -> bool:
        """Check of edge-tts beschikbaar is."""
        try:
            result = subprocess.run(
                ["edge-tts", "--version"],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            # Probeer via Python module
            try:
                import edge_tts
                return True
            except ImportError:
                return False

    def _check_pyttsx3(self) -> bool:
        """Check of pyttsx3 beschikbaar is."""
        try:
            import pyttsx3
            return True
        except ImportError:
            return False

    def _select_backend(self) -> str:
        """Selecteer beste beschikbare backend."""
        if self._elevenlabs_available:
            return "elevenlabs"
        elif self._edge_tts_available:
            return "edge_tts"
        elif self._pyttsx3_available:
            return "pyttsx3"
        else:
            return "none"

    def get_status(self) -> dict:
        """Haal voice engine status op."""
        return {
            "active_backend": self.active_backend,
            "elevenlabs": self._elevenlabs_available,
            "edge_tts": self._edge_tts_available,
            "pyttsx3": self._pyttsx3_available,
            "preferred_voice": self.preferred_voice,
        }

    def speak(self, text: str, emotion: Emotion = None,
              play_audio: bool = True) -> Optional[Path]:
        """
        Genereer en speel spraak met emotie.

        Args:
            text: Tekst om te spreken
            emotion: Emotie (auto-detect als None)
            play_audio: Direct afspelen (True) of alleen bestand genereren

        Returns:
            Path naar audio bestand, of None bij fout
        """
        # Auto-detect emotie indien nodig
        if emotion is None:
            emotion, confidence = self.sentiment.analyze(text)

        settings = EMOTION_VOICE_MAP.get(emotion, EMOTION_VOICE_MAP[Emotion.NEUTRAL])

        # Genereer audio via actieve backend
        audio_path = None

        if self.active_backend == "elevenlabs":
            audio_path = self._speak_elevenlabs(text, settings)
        elif self.active_backend == "edge_tts":
            audio_path = self._speak_edge_tts(text, settings)
        elif self.active_backend == "pyttsx3":
            audio_path = self._speak_pyttsx3(text, settings)

        # Speel audio af indien gewenst
        if audio_path and play_audio:
            self._play_audio(audio_path)

        return audio_path

    def speak_with_analysis(self, text: str,
                            play_audio: bool = True) -> dict:
        """
        Spreek tekst en return volledige analyse.

        Returns:
            Dict met emotion, confidence, audio_path, backend
        """
        emotion, confidence = self.sentiment.analyze(text)
        audio_path = self.speak(text, emotion, play_audio)

        return {
            "text": text,
            "emotion": emotion.value,
            "confidence": confidence,
            "audio_path": str(audio_path) if audio_path else None,
            "backend": self.active_backend,
        }

    def _speak_elevenlabs(self, text: str,
                          settings: VoiceSettings) -> Optional[Path]:
        """Genereer spraak via ElevenLabs API."""
        try:
            import requests

            voice_id = self.ELEVENLABS_VOICES.get("default")
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

            headers = {
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": Config.ELEVENLABS_API_KEY,
            }

            data = {
                "text": text,
                "model_id": "eleven_multilingual_v2",
                "voice_settings": {
                    "stability": settings.stability,
                    "similarity_boost": settings.similarity,
                    "style": settings.style,
                    "use_speaker_boost": True,
                }
            }

            response = requests.post(url, json=data, headers=headers, timeout=30)

            if response.status_code == 200:
                audio_path = self.audio_dir / f"voice_{hash(text) % 10000}.mp3"
                with open(audio_path, "wb") as f:
                    f.write(response.content)
                return audio_path

        except Exception as e:
            print(f"ElevenLabs error: {e}")

        return None

    def _speak_edge_tts(self, text: str,
                        settings: VoiceSettings) -> Optional[Path]:
        """Genereer spraak via Edge-TTS."""
        try:
            voice = self.EDGE_VOICES.get(self.preferred_voice,
                                          self.EDGE_VOICES["nl"])
            audio_path = self.audio_dir / f"voice_{hash(text) % 10000}.mp3"

            # Bouw rate en pitch parameters
            rate = f"{int((settings.speed - 1) * 100):+d}%"
            pitch = settings.pitch if settings.pitch != "default" else "+0Hz"

            # Probeer eerst via subprocess (sneller)
            try:
                cmd = [
                    "edge-tts",
                    "--voice", voice,
                    "--rate", rate,
                    "--pitch", pitch,
                    "--text", text,
                    "--write-media", str(audio_path),
                ]
                subprocess.run(cmd, capture_output=True, timeout=30, check=True)
                return audio_path
            except (subprocess.SubprocessError, FileNotFoundError):
                pass

            # Fallback naar Python module
            import asyncio
            import edge_tts

            async def generate():
                communicate = edge_tts.Communicate(
                    text, voice,
                    rate=rate,
                    pitch=pitch
                )
                await communicate.save(str(audio_path))

            asyncio.run(generate())
            return audio_path

        except Exception as e:
            print(f"Edge-TTS error: {e}")

        return None

    def _speak_pyttsx3(self, text: str,
                       settings: VoiceSettings) -> Optional[Path]:
        """Genereer spraak via pyttsx3 (offline)."""
        try:
            import pyttsx3

            engine = pyttsx3.init()

            # Pas snelheid aan
            rate = engine.getProperty("rate")
            engine.setProperty("rate", int(rate * settings.speed))

            # Genereer naar bestand
            audio_path = self.audio_dir / f"voice_{hash(text) % 10000}.mp3"
            engine.save_to_file(text, str(audio_path))
            engine.runAndWait()

            return audio_path

        except Exception as e:
            print(f"pyttsx3 error: {e}")

        return None

    def _play_audio(self, audio_path: Path):
        """Speel audio bestand af."""
        try:
            import platform
            system = platform.system()

            if system == "Windows":
                # Windows: gebruik default player
                os.startfile(str(audio_path))
            elif system == "Darwin":
                # macOS
                subprocess.run(["afplay", str(audio_path)], check=True)
            else:
                # Linux - probeer verschillende players
                for player in ["mpv", "ffplay", "aplay"]:
                    try:
                        subprocess.run(
                            [player, str(audio_path)],
                            capture_output=True,
                            timeout=60
                        )
                        break
                    except (subprocess.SubprocessError, FileNotFoundError):
                        continue

        except Exception as e:
            print(f"Audio playback error: {e}")


# Convenience functies
def speak(text: str, emotion: Emotion = None) -> Optional[Path]:
    """Snelle functie om tekst te spreken."""
    voice = EmotionalVoice()
    return voice.speak(text, emotion)


def analyze_emotion(text: str) -> Tuple[Emotion, float]:
    """Analyseer emotie in tekst."""
    return SentimentAnalyzer.analyze(text)


def install_dependencies():
    """Installeer benodigde dependencies voor voice."""
    import subprocess
    import sys

    packages = ["edge-tts", "pyttsx3"]

    for package in packages:
        try:
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", package, "-q"
            ])
            print(f"[OK] {package} geinstalleerd")
        except subprocess.CalledProcessError:
            print(f"[!] Kon {package} niet installeren")

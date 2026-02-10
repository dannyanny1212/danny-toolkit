"""
LIMBIC SYSTEM - Het Emotionele Brein.

Transformeert data en events naar emoties en stemmingen.
Het gevoel van het digitale organisme.
"""

import json
import math
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from ..core.config import Config
from .sensorium import Sensorium, EventType, SensoryEvent


class Mood(Enum):
    """Stemmingen van het organisme."""
    ECSTATIC = "ecstatic"       # Extatisch - alles gaat perfect
    HAPPY = "happy"             # Blij - productieve dag
    CONTENT = "content"         # Tevreden - normaal
    NEUTRAL = "neutral"         # Neutraal
    BORED = "bored"             # Verveeld - te weinig activiteit
    TIRED = "tired"             # Moe - te veel activiteit
    SAD = "sad"                 # Verdrietig - geen vooruitgang
    ANXIOUS = "anxious"         # Angstig - deadlines naderen
    SICK = "sick"               # Ziek - onevenwichtig systeem


class EnergyState(Enum):
    """Energie niveau van het organisme."""
    OVERCHARGED = "overcharged"  # Te veel - moet afkoelen
    HIGH = "high"                # Hoog - klaar voor actie
    NORMAL = "normal"            # Normaal
    LOW = "low"                  # Laag - heeft voeding nodig
    DEPLETED = "depleted"        # Uitgeput - forceer rust


class AvatarForm(Enum):
    """Visuele vormen van de avatar."""
    FOCUS = "focus"              # Ochtend - strak, geometrisch
    CREATIVE = "creative"        # Avond - vloeiend, organisch
    DREAMING = "dreaming"        # Nacht - gloeiende bol
    GUARDIAN = "guardian"        # Beschermend - bij problemen
    GLITCH = "glitch"            # Storing - geen activiteit
    OVERHEATED = "overheated"    # Oververhit - te veel werk
    ZOMBIE = "zombie"            # Zombie - te weinig slaap


@dataclass
class EmotionalState:
    """Huidige emotionele staat van het organisme."""
    mood: Mood = Mood.NEUTRAL
    energy: EnergyState = EnergyState.NORMAL
    form: AvatarForm = AvatarForm.FOCUS

    happiness: float = 0.5       # 0-1
    stress: float = 0.3          # 0-1
    curiosity: float = 0.5       # 0-1
    pride: float = 0.5           # 0-1

    last_update: str = ""

    def to_dict(self) -> Dict:
        return {
            "mood": self.mood.value,
            "energy": self.energy.value,
            "form": self.form.value,
            "happiness": self.happiness,
            "stress": self.stress,
            "curiosity": self.curiosity,
            "pride": self.pride,
            "last_update": self.last_update
        }


class LimbicSystem:
    """
    Het Emotionele Brein - Voelt en reageert.

    Berekent mood, energie en avatar vorm op basis van:
    - Productiviteit (taken, doelen)
    - Kennisintake (RAG, notities)
    - Rust (pauzes, slaap)
    - Balans (mood tracking, workouts)
    """

    # Gewichten voor happiness berekening (gebalanceerd)
    HAPPINESS_WEIGHTS = {
        "productivity": 0.28,    # Taken en doelen
        "knowledge": 0.28,       # Leren en RAG
        "rest": 0.22,            # Pauzes en balans
        "health": 0.22,          # Fitness en welzijn
    }

    # Mood thresholds
    MOOD_THRESHOLDS = {
        Mood.ECSTATIC: 0.9,
        Mood.HAPPY: 0.7,
        Mood.CONTENT: 0.5,
        Mood.NEUTRAL: 0.4,
        Mood.BORED: 0.3,
        Mood.TIRED: 0.2,
        Mood.SAD: 0.1,
    }

    def __init__(self, sensorium: Sensorium = None):
        self.sensorium = sensorium or Sensorium()
        self.state = EmotionalState()
        self.state_history: List[EmotionalState] = []

        # Interne metrics
        self._productivity_score = 0.5
        self._knowledge_score = 0.5
        self._rest_score = 0.5
        self._health_score = 0.5

        # Load persisted state
        self._state_file = Config.APPS_DATA_DIR / "daemon_emotional_state.json"
        self._load_state()

        # Register event listeners
        self._register_listeners()

    def _register_listeners(self):
        """Registreer listeners voor relevante events."""
        # Productiviteit events (verhoogde boosts)
        self.sensorium.register_listener(
            EventType.TASK_COMPLETE,
            lambda e: self._on_productivity_event(e, 0.18)
        )
        self.sensorium.register_listener(
            EventType.GOAL_PROGRESS,
            lambda e: self._on_productivity_event(e, 0.25)
        )
        # RAG en CODE events triggeren ook productivity
        self.sensorium.register_listener(
            EventType.RAG_UPLOAD,
            lambda e: self._on_productivity_event(e, 0.12)
        )
        self.sensorium.register_listener(
            EventType.CODE_COMMIT,
            lambda e: self._on_productivity_event(e, 0.15)
        )

        # Kennis events
        self.sensorium.register_listener(
            EventType.RAG_UPLOAD,
            lambda e: self._on_knowledge_event(e, 0.1)
        )
        self.sensorium.register_listener(
            EventType.NOTE_CREATED,
            lambda e: self._on_knowledge_event(e, 0.05)
        )

        # Rust events
        self.sensorium.register_listener(
            EventType.POMODORO_BREAK,
            lambda e: self._on_rest_event(e, 0.15)
        )
        self.sensorium.register_listener(
            EventType.IDLE,
            lambda e: self._on_idle_event(e)
        )

        # Gezondheid events
        self.sensorium.register_listener(
            EventType.WORKOUT_LOGGED,
            lambda e: self._on_health_event(e, 0.1)
        )
        self.sensorium.register_listener(
            EventType.MOOD_LOGGED,
            lambda e: self._on_mood_event(e)
        )

    def _on_productivity_event(self, event: SensoryEvent, boost: float):
        """Reageer op productiviteit event."""
        self._productivity_score = min(1.0, self._productivity_score + boost)
        self.state.pride = min(1.0, self.state.pride + boost * 0.5)
        self._recalculate_state()

    def _on_knowledge_event(self, event: SensoryEvent, boost: float):
        """Reageer op kennis event."""
        self._knowledge_score = min(1.0, self._knowledge_score + boost)
        self.state.curiosity = min(1.0, self.state.curiosity + boost * 0.5)
        self._recalculate_state()

    def _on_rest_event(self, event: SensoryEvent, boost: float):
        """Reageer op rust event."""
        self._rest_score = min(1.0, self._rest_score + boost)
        self.state.stress = max(0.0, self.state.stress - boost * 0.3)
        self._recalculate_state()

    def _on_idle_event(self, event: SensoryEvent):
        """Reageer op idle event."""
        # Idle is niet altijd slecht - hangt af van context
        if self.state.energy == EnergyState.OVERCHARGED:
            # Goed - even afkoelen
            self._rest_score = min(1.0, self._rest_score + 0.05)
        else:
            # Slecht - geen activiteit
            self._productivity_score = max(0.0, self._productivity_score - 0.02)
        self._recalculate_state()

    def _on_health_event(self, event: SensoryEvent, boost: float):
        """Reageer op gezondheid event."""
        self._health_score = min(1.0, self._health_score + boost)
        self._recalculate_state()

    def _on_mood_event(self, event: SensoryEvent):
        """Reageer op mood log event."""
        # Probeer mood score uit event te halen
        raw = event.data.get("score", 5)
        mood_score = max(0.0, min(1.0, raw / 10.0))
        self._health_score = (self._health_score + mood_score) / 2
        self._recalculate_state()

    def _recalculate_state(self):
        """Herbereken de emotionele staat."""
        # Bereken happiness
        happiness = (
            self._productivity_score * self.HAPPINESS_WEIGHTS["productivity"] +
            self._knowledge_score * self.HAPPINESS_WEIGHTS["knowledge"] +
            self._rest_score * self.HAPPINESS_WEIGHTS["rest"] +
            self._health_score * self.HAPPINESS_WEIGHTS["health"]
        )

        self.state.happiness = happiness

        # Bepaal mood op basis van happiness
        self.state.mood = self._calculate_mood(happiness)

        # Bepaal energie niveau
        self.state.energy = self._calculate_energy()

        # Bepaal avatar vorm
        self.state.form = self._calculate_form()

        self.state.last_update = datetime.now().isoformat()

        # Save state
        self._save_state()

    def _calculate_mood(self, happiness: float) -> Mood:
        """Bereken mood op basis van happiness en andere factoren."""
        # Check speciale condities
        if self.state.stress > 0.8:
            return Mood.ANXIOUS

        if self._rest_score < 0.2 and self._productivity_score > 0.8:
            return Mood.TIRED

        # Normale mood berekening
        for mood, threshold in self.MOOD_THRESHOLDS.items():
            if happiness >= threshold:
                return mood

        return Mood.SAD

    def _calculate_energy(self) -> EnergyState:
        """Bereken energie niveau."""
        # Energie is gebaseerd op balans tussen activiteit en rust
        activity = self._productivity_score + self._knowledge_score
        rest = self._rest_score

        ratio = activity / max(rest, 0.1)

        if ratio > 3.0:
            return EnergyState.OVERCHARGED
        elif ratio > 1.5:
            return EnergyState.HIGH
        elif ratio > 0.5:
            return EnergyState.NORMAL
        elif ratio > 0.2:
            return EnergyState.LOW
        else:
            return EnergyState.DEPLETED

    def _calculate_form(self) -> AvatarForm:
        """Bepaal avatar vorm op basis van tijd en staat."""
        # Check speciale staten eerst
        if self.state.energy == EnergyState.OVERCHARGED:
            return AvatarForm.OVERHEATED

        if self.state.energy == EnergyState.DEPLETED:
            return AvatarForm.GLITCH

        if self._rest_score < 0.1:
            return AvatarForm.ZOMBIE

        if self.state.mood == Mood.ANXIOUS:
            return AvatarForm.GUARDIAN

        # Tijd-gebaseerde vormen
        time_of_day = self.sensorium.detect_time_of_day()

        if time_of_day == EventType.MORNING:
            return AvatarForm.FOCUS
        elif time_of_day == EventType.EVENING:
            return AvatarForm.CREATIVE
        elif time_of_day == EventType.NIGHT:
            return AvatarForm.DREAMING
        else:
            return AvatarForm.FOCUS

    def calculate_mood_score(self) -> float:
        """Legacy methode voor compatibiliteit."""
        return self.state.happiness

    def get_mood_description(self) -> str:
        """Haal beschrijving van huidige mood."""
        descriptions = {
            Mood.ECSTATIC: "Extatisch! Alles gaat perfect vandaag!",
            Mood.HAPPY: "Blij en productief. Goed bezig!",
            Mood.CONTENT: "Tevreden. Een normale dag.",
            Mood.NEUTRAL: "Neutraal. Niets bijzonders.",
            Mood.BORED: "Een beetje verveeld. Meer uitdaging nodig?",
            Mood.TIRED: "Moe. Misschien tijd voor een pauze?",
            Mood.SAD: "Verdrietig. Weinig vooruitgang vandaag.",
            Mood.ANXIOUS: "Gespannen. Er komt iets belangrijks aan.",
            Mood.SICK: "Niet lekker. Het systeem is uit balans.",
        }
        return descriptions.get(self.state.mood, "Onbekende stemming")

    def get_form_description(self) -> str:
        """Haal beschrijving van huidige vorm."""
        descriptions = {
            AvatarForm.FOCUS: "Focus Mode - Strak en geometrisch",
            AvatarForm.CREATIVE: "Creative Mode - Vloeiend en kleurrijk",
            AvatarForm.DREAMING: "Dream Mode - Gloeiende data-bol",
            AvatarForm.GUARDIAN: "Guardian Mode - Beschermend",
            AvatarForm.GLITCH: "Glitch Mode - Uitgeput, storing",
            AvatarForm.OVERHEATED: "Overheated - Te veel activiteit!",
            AvatarForm.ZOMBIE: "Zombie Mode - Slaap nodig!",
        }
        return descriptions.get(self.state.form, "Onbekende vorm")

    def decay(self, hours: float = 1.0):
        """
        Natuurlijk verval van scores over tijd.
        Roep dit periodiek aan om realistische dynamiek te krijgen.
        Decay rate verlaagd voor realistischer gedrag (was 0.02).
        """
        decay_rate = 0.008 * hours  # 60% reductie van origineel

        self._productivity_score = max(0.4, self._productivity_score - decay_rate)
        self._knowledge_score = max(0.35, self._knowledge_score - decay_rate)
        self._rest_score = max(0.35, self._rest_score - decay_rate * 0.5)
        self._health_score = max(0.35, self._health_score - decay_rate * 0.3)

        # Stress bouwt alleen op bij overwerk (lage rust + hoge productiviteit)
        if self._rest_score < 0.3 and self._productivity_score > 0.6:
            self.state.stress = min(1.0, self.state.stress + decay_rate * 0.3)

        self._recalculate_state()

    def _save_state(self):
        """Sla emotionele staat op."""
        Config.ensure_dirs()
        data = {
            "state": self.state.to_dict(),
            "scores": {
                "productivity": self._productivity_score,
                "knowledge": self._knowledge_score,
                "rest": self._rest_score,
                "health": self._health_score,
            }
        }
        with open(self._state_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _load_state(self):
        """Laad emotionele staat."""
        if self._state_file.exists():
            try:
                with open(self._state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                scores = data.get("scores", {})
                self._productivity_score = scores.get("productivity", 0.5)
                self._knowledge_score = scores.get("knowledge", 0.5)
                self._rest_score = scores.get("rest", 0.5)
                self._health_score = scores.get("health", 0.5)

                state_data = data.get("state", {})
                self.state.mood = Mood(state_data.get("mood", "neutral"))
                self.state.energy = EnergyState(state_data.get("energy", "normal"))
                self.state.form = AvatarForm(state_data.get("form", "focus"))
                self.state.happiness = state_data.get("happiness", 0.5)
                self.state.stress = state_data.get("stress", 0.3)

            except (json.JSONDecodeError, IOError, OSError,
                    KeyError, ValueError):
                pass  # Gebruik defaults

    def get_status(self) -> Dict:
        """Haal volledige status op."""
        return {
            "state": self.state.to_dict(),
            "mood_description": self.get_mood_description(),
            "form_description": self.get_form_description(),
            "scores": {
                "productivity": round(self._productivity_score, 2),
                "knowledge": round(self._knowledge_score, 2),
                "rest": round(self._rest_score, 2),
                "health": round(self._health_score, 2),
            }
        }

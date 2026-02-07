"""
SENSORIUM - De Zintuigen van het Digitale Organisme.

Luistert naar events van alle 35+ apps en voedt het brein.
"""

import json
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Callable, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
from collections import deque

from ..core.config import Config


class EventType(Enum):
    """Types van events die het organisme kan waarnemen."""
    # Voeding (Input)
    RAG_UPLOAD = "rag_upload"           # Kennis toegevoegd
    TASK_COMPLETE = "task_complete"     # Taak afgerond
    CODE_COMMIT = "code_commit"         # Code geschreven
    NOTE_CREATED = "note_created"       # Notitie gemaakt
    GOAL_PROGRESS = "goal_progress"     # Doel voortgang

    # Activiteit
    QUERY_ASKED = "query_asked"         # Vraag gesteld
    HUNT_STARTED = "hunt_started"       # Jacht gestart
    WORKOUT_LOGGED = "workout_logged"   # Workout gelogd
    EXPENSE_ADDED = "expense_added"     # Uitgave toegevoegd
    MOOD_LOGGED = "mood_logged"         # Stemming gelogd

    # Systeem
    APP_OPENED = "app_opened"           # App geopend
    APP_CLOSED = "app_closed"           # App gesloten
    POMODORO_BREAK = "pomodoro_break"   # Pauze genomen
    POMODORO_WORK = "pomodoro_work"     # Werk sessie

    # Tijd
    MORNING = "morning"                 # Ochtend detectie
    EVENING = "evening"                 # Avond detectie
    NIGHT = "night"                     # Nacht detectie
    IDLE = "idle"                       # Geen activiteit


@dataclass
class SensoryEvent:
    """Een waargenomen event."""
    type: EventType
    source: str                         # Welke app
    data: Dict = field(default_factory=dict)
    timestamp: str = ""
    importance: float = 0.5             # 0-1, hoe belangrijk

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class Sensorium:
    """
    De Zintuigen - Waarneemt alles wat er gebeurt.

    Monitort alle apps en detecteert patronen in gebruikersgedrag.
    """

    # Event gewichten voor metabolisme
    EVENT_NUTRITION = {
        EventType.RAG_UPLOAD: ("protein", 10),      # Groei
        EventType.NOTE_CREATED: ("protein", 5),
        EventType.TASK_COMPLETE: ("carbs", 8),      # Energie
        EventType.GOAL_PROGRESS: ("carbs", 12),
        EventType.CODE_COMMIT: ("vitamins", 10),    # Gezondheid
        EventType.WORKOUT_LOGGED: ("vitamins", 8),
        EventType.POMODORO_BREAK: ("rest", 15),     # Rust
        EventType.MOOD_LOGGED: ("balance", 5),      # Balans
    }

    def __init__(self, max_history: int = 1000):
        self.events: deque = deque(maxlen=max_history)
        self.listeners: Dict[EventType, List[Callable]] = {}
        self.last_activity: datetime = datetime.now()
        self.is_monitoring: bool = False
        self._monitor_thread: Optional[threading.Thread] = None

        # Stats
        self.stats = {
            "total_events": 0,
            "events_today": 0,
            "last_event_type": None,
            "active_apps": set(),
        }

        # Data paths voor monitoring
        self.data_paths = {
            "legendary_companion": Config.APPS_DATA_DIR / "legendary_companion.json",
            "goals_tracker": Config.APPS_DATA_DIR / "goals_tracker.json",
            "mood_tracker": Config.APPS_DATA_DIR / "mood_tracker.json",
            "fitness_tracker": Config.APPS_DATA_DIR / "fitness_tracker.json",
            "expense_tracker": Config.APPS_DATA_DIR / "expense_tracker.json",
            "pomodoro": Config.APPS_DATA_DIR / "pomodoro.json",
            "notities": Config.APPS_DATA_DIR / "notities.json",
            "agenda": Config.APPS_DATA_DIR / "agenda.json",
        }

        self._last_checksums: Dict[str, str] = {}

    def register_listener(self, event_type: EventType, callback: Callable):
        """Registreer een listener voor een event type."""
        if event_type not in self.listeners:
            self.listeners[event_type] = []
        self.listeners[event_type].append(callback)

    def emit(self, event: SensoryEvent):
        """Emit een event naar alle listeners."""
        self.events.append(event)
        self.last_activity = datetime.now()
        self.stats["total_events"] += 1
        self.stats["last_event_type"] = event.type.value

        # Notify listeners
        if event.type in self.listeners:
            for callback in self.listeners[event.type]:
                try:
                    callback(event)
                except Exception as e:
                    print(f"[Sensorium] Listener error: {e}")

    def sense_event(self, event_type: EventType, source: str,
                    data: Dict = None, importance: float = 0.5):
        """Registreer een nieuw event."""
        event = SensoryEvent(
            type=event_type,
            source=source,
            data=data or {},
            importance=importance
        )
        self.emit(event)
        return event

    def get_recent_events(self, minutes: int = 60,
                          event_type: EventType = None) -> List[SensoryEvent]:
        """Haal recente events op."""
        cutoff = datetime.now() - timedelta(minutes=minutes)
        recent = []

        for event in reversed(self.events):
            event_time = datetime.fromisoformat(event.timestamp)
            if event_time < cutoff:
                break
            if event_type is None or event.type == event_type:
                recent.append(event)

        return recent

    def get_nutrition_intake(self, hours: int = 24) -> Dict[str, float]:
        """Bereken voedingsinname van events."""
        nutrition = {
            "protein": 0,    # Kennis/groei
            "carbs": 0,      # Energie/taken
            "vitamins": 0,   # Gezondheid/code
            "rest": 0,       # Rust/pauzes
            "balance": 0,    # Balans/mood
        }

        cutoff = datetime.now() - timedelta(hours=hours)

        for event in self.events:
            event_time = datetime.fromisoformat(event.timestamp)
            if event_time < cutoff:
                continue

            if event.type in self.EVENT_NUTRITION:
                nutrient, amount = self.EVENT_NUTRITION[event.type]
                nutrition[nutrient] += amount

        return nutrition

    def detect_time_of_day(self) -> EventType:
        """Detecteer tijd van de dag."""
        hour = datetime.now().hour

        if 6 <= hour < 12:
            return EventType.MORNING
        elif 12 <= hour < 18:
            return EventType.EVENING  # Middag/namiddag
        elif 18 <= hour < 22:
            return EventType.EVENING
        else:
            return EventType.NIGHT

    def detect_idle(self, threshold_minutes: int = 30) -> bool:
        """Detecteer of gebruiker idle is."""
        idle_time = datetime.now() - self.last_activity
        return idle_time > timedelta(minutes=threshold_minutes)

    def _file_checksum(self, path: Path) -> str:
        """Bereken simpele checksum van bestand."""
        if not path.exists():
            return ""
        try:
            stat = path.stat()
            return f"{stat.st_size}_{stat.st_mtime}"
        except:
            return ""

    def _check_file_changes(self) -> List[SensoryEvent]:
        """Check op file wijzigingen in app data."""
        events = []

        for app_name, path in self.data_paths.items():
            current_checksum = self._file_checksum(path)
            last_checksum = self._last_checksums.get(app_name, "")

            if current_checksum and current_checksum != last_checksum:
                # File is gewijzigd
                self._last_checksums[app_name] = current_checksum

                # Bepaal event type op basis van app
                event_type = self._app_to_event_type(app_name)
                if event_type:
                    events.append(SensoryEvent(
                        type=event_type,
                        source=app_name,
                        data={"path": str(path)},
                        importance=0.6
                    ))

        return events

    def _app_to_event_type(self, app_name: str) -> Optional[EventType]:
        """Map app naar event type."""
        mapping = {
            "legendary_companion": EventType.RAG_UPLOAD,
            "goals_tracker": EventType.GOAL_PROGRESS,
            "mood_tracker": EventType.MOOD_LOGGED,
            "fitness_tracker": EventType.WORKOUT_LOGGED,
            "expense_tracker": EventType.EXPENSE_ADDED,
            "pomodoro": EventType.POMODORO_WORK,
            "notities": EventType.NOTE_CREATED,
        }
        return mapping.get(app_name)

    def start_monitoring(self, interval_seconds: int = 30):
        """Start achtergrond monitoring."""
        if self.is_monitoring:
            return

        self.is_monitoring = True

        def monitor_loop():
            while self.is_monitoring:
                try:
                    # Check file changes
                    events = self._check_file_changes()
                    for event in events:
                        self.emit(event)

                    # Check idle status
                    if self.detect_idle():
                        self.emit(SensoryEvent(
                            type=EventType.IDLE,
                            source="system",
                            importance=0.3
                        ))

                    # Check time of day
                    time_event = self.detect_time_of_day()
                    # Emit time event elke 30 min

                except Exception as e:
                    print(f"[Sensorium] Monitor error: {e}")

                time.sleep(interval_seconds)

        self._monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        self._monitor_thread.start()

    def stop_monitoring(self):
        """Stop achtergrond monitoring."""
        self.is_monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)

    def get_status(self) -> Dict:
        """Haal sensorium status op."""
        return {
            "is_monitoring": self.is_monitoring,
            "total_events": self.stats["total_events"],
            "last_event": self.stats["last_event_type"],
            "last_activity": self.last_activity.isoformat(),
            "is_idle": self.detect_idle(),
            "time_of_day": self.detect_time_of_day().value,
            "nutrition": self.get_nutrition_intake(24),
        }

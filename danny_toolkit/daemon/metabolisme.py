"""
METABOLISME - Het Energie Systeem.

Het organisme verbrandt en consumeert op basis van activiteit.
Balans is cruciaal voor gezondheid.
"""

import json
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from ..core.config import Config
from .sensorium import Sensorium, EventType


class MetabolicState(Enum):
    """Metabolische staten."""
    THRIVING = "thriving"        # Perfect balans
    GROWING = "growing"          # Goede intake, groeit
    STABLE = "stable"            # Stabiel, normaal
    HUNGRY = "hungry"            # Heeft voeding nodig
    STARVING = "starving"        # Kritiek - geen voeding
    BLOATED = "bloated"          # Te veel input
    BURNING = "burning"          # Hoge verbranding


@dataclass
class NutrientLevels:
    """Voedingsstoffen niveaus."""
    protein: float = 50.0        # Kennis/groei (0-100)
    carbs: float = 50.0          # Energie/taken (0-100)
    vitamins: float = 50.0       # Gezondheid/code (0-100)
    water: float = 50.0          # Rust/pauzes (0-100)
    fiber: float = 50.0          # Balans/consistentie (0-100)

    def to_dict(self) -> Dict:
        return {
            "protein": round(self.protein, 1),
            "carbs": round(self.carbs, 1),
            "vitamins": round(self.vitamins, 1),
            "water": round(self.water, 1),
            "fiber": round(self.fiber, 1),
        }

    @property
    def total(self) -> float:
        return (self.protein + self.carbs + self.vitamins +
                self.water + self.fiber) / 5

    @property
    def balance_score(self) -> float:
        """Hoe gebalanceerd zijn de niveaus (0-1)."""
        values = [self.protein, self.carbs, self.vitamins,
                  self.water, self.fiber]
        avg = sum(values) / len(values)
        variance = sum((v - avg) ** 2 for v in values) / len(values)
        # Lagere variance = betere balans
        return max(0, 1 - (variance / 1000))


class Metabolisme:
    """
    Het Metabolisme - Energie en Voeding.

    Beheert de "levenskracht" van het organisme:
    - Voeding intake van events
    - Verbranding over tijd
    - Balans tussen input en output
    - Gezondheid indicatoren
    """

    # Burn rates per uur
    BURN_RATES = {
        "protein": 2.0,      # Kennis vervaagt langzaam
        "carbs": 4.0,        # Energie verbruikt snel
        "vitamins": 1.5,     # Gezondheid stabiel
        "water": 3.0,        # Rust nodig regelmatig
        "fiber": 1.0,        # Consistentie bouwt op
    }

    # Max levels
    MAX_LEVEL = 100.0
    CRITICAL_LOW = 15.0
    WARNING_LOW = 30.0
    WARNING_HIGH = 85.0
    CRITICAL_HIGH = 95.0

    def __init__(self, sensorium: Sensorium = None):
        self.sensorium = sensorium or Sensorium()
        self.nutrients = NutrientLevels()
        self.state = MetabolicState.STABLE

        self.is_running = False
        self._metabolism_thread: Optional[threading.Thread] = None
        self._last_burn_time = datetime.now()

        # Stats
        self.stats = {
            "total_consumed": 0,
            "total_burned": 0,
            "time_in_states": {},
            "deficiencies": [],
        }

        # Load persisted state
        self._state_file = Config.APPS_DATA_DIR / "daemon_metabolism.json"
        self._load_state()

        # Register event listeners
        self._register_listeners()

    def _register_listeners(self):
        """Registreer listeners voor voeding events."""
        # Protein events (kennis)
        self.sensorium.register_listener(
            EventType.RAG_UPLOAD,
            lambda e: self.consume("protein", 15)
        )
        self.sensorium.register_listener(
            EventType.NOTE_CREATED,
            lambda e: self.consume("protein", 8)
        )
        self.sensorium.register_listener(
            EventType.QUERY_ASKED,
            lambda e: self.consume("protein", 3)
        )

        # Carbs events (energie/taken)
        self.sensorium.register_listener(
            EventType.TASK_COMPLETE,
            lambda e: self.consume("carbs", 12)
        )
        self.sensorium.register_listener(
            EventType.GOAL_PROGRESS,
            lambda e: self.consume("carbs", 18)
        )

        # Vitamins events (gezondheid/code)
        self.sensorium.register_listener(
            EventType.CODE_COMMIT,
            lambda e: self.consume("vitamins", 15)
        )
        self.sensorium.register_listener(
            EventType.WORKOUT_LOGGED,
            lambda e: self.consume("vitamins", 12)
        )

        # Water events (rust)
        self.sensorium.register_listener(
            EventType.POMODORO_BREAK,
            lambda e: self.consume("water", 20)
        )

        # Fiber events (consistentie)
        self.sensorium.register_listener(
            EventType.MOOD_LOGGED,
            lambda e: self.consume("fiber", 8)
        )

    def consume(self, nutrient: str, amount: float):
        """Consumeer een nutrient."""
        if not hasattr(self.nutrients, nutrient):
            return

        current = getattr(self.nutrients, nutrient)
        new_value = min(self.MAX_LEVEL, current + amount)
        setattr(self.nutrients, nutrient, new_value)

        self.stats["total_consumed"] += amount
        self._update_state()
        self._save_state()

    def burn(self, hours: float = 1.0):
        """Verbrand nutrients over tijd."""
        for nutrient, rate in self.BURN_RATES.items():
            if hasattr(self.nutrients, nutrient):
                current = getattr(self.nutrients, nutrient)
                burn_amount = rate * hours
                new_value = max(0, current - burn_amount)
                setattr(self.nutrients, nutrient, new_value)
                self.stats["total_burned"] += burn_amount

        self._update_state()
        self._save_state()

    def _update_state(self):
        """Update metabolische staat."""
        total = self.nutrients.total
        balance = self.nutrients.balance_score

        # Check voor kritieke tekorten
        deficiencies = self._check_deficiencies()

        if len(deficiencies) >= 3:
            self.state = MetabolicState.STARVING
        elif len(deficiencies) >= 1:
            self.state = MetabolicState.HUNGRY
        elif total > self.CRITICAL_HIGH:
            self.state = MetabolicState.BLOATED
        elif total > self.WARNING_HIGH and balance < 0.5:
            self.state = MetabolicState.BURNING
        elif total > 60 and balance > 0.7:
            self.state = MetabolicState.THRIVING
        elif total > 50:
            self.state = MetabolicState.GROWING
        else:
            self.state = MetabolicState.STABLE

        self.stats["deficiencies"] = deficiencies

    def _check_deficiencies(self) -> List[str]:
        """Check voor nutrient tekorten."""
        deficiencies = []

        for nutrient in ["protein", "carbs", "vitamins", "water", "fiber"]:
            level = getattr(self.nutrients, nutrient)
            if level < self.CRITICAL_LOW:
                deficiencies.append(nutrient)

        return deficiencies

    def get_hunger_level(self) -> Tuple[str, float]:
        """Haal honger niveau op."""
        total = self.nutrients.total

        if total < 20:
            return "starving", 1.0
        elif total < 35:
            return "very_hungry", 0.8
        elif total < 50:
            return "hungry", 0.6
        elif total < 65:
            return "peckish", 0.4
        elif total < 80:
            return "satisfied", 0.2
        else:
            return "full", 0.0

    def get_recommendations(self) -> List[str]:
        """Krijg aanbevelingen voor gezondheid."""
        recommendations = []

        if self.nutrients.protein < self.WARNING_LOW:
            recommendations.append("Upload wat documenten naar RAG - ik heb kennis nodig!")

        if self.nutrients.carbs < self.WARNING_LOW:
            recommendations.append("Werk aan je taken - ik heb energie nodig!")

        if self.nutrients.vitamins < self.WARNING_LOW:
            recommendations.append("Commit wat code of log een workout!")

        if self.nutrients.water < self.WARNING_LOW:
            recommendations.append("Neem een pauze - gebruik Pomodoro!")

        if self.nutrients.fiber < self.WARNING_LOW:
            recommendations.append("Log je mood - consistentie is belangrijk!")

        if self.nutrients.total > self.WARNING_HIGH:
            recommendations.append("Rustig aan! Te veel input, geef me tijd om te verwerken.")

        return recommendations

    def start_metabolism(self, burn_interval_minutes: int = 15):
        """Start het metabolisme proces."""
        if self.is_running:
            return

        self.is_running = True
        self._last_burn_time = datetime.now()

        def metabolism_loop():
            while self.is_running:
                try:
                    # Bereken verstreken tijd
                    now = datetime.now()
                    elapsed = (now - self._last_burn_time).total_seconds() / 3600
                    self._last_burn_time = now

                    # Verbrand
                    if elapsed > 0:
                        self.burn(elapsed)

                except Exception as e:
                    print(f"[Metabolisme] Error: {e}")

                time.sleep(burn_interval_minutes * 60)

        self._metabolism_thread = threading.Thread(
            target=metabolism_loop, daemon=True
        )
        self._metabolism_thread.start()

    def stop_metabolism(self):
        """Stop het metabolisme proces."""
        self.is_running = False
        if self._metabolism_thread:
            self._metabolism_thread.join(timeout=5)

    def _save_state(self):
        """Sla staat op."""
        Config.ensure_dirs()
        data = {
            "nutrients": self.nutrients.to_dict(),
            "state": self.state.value,
            "stats": self.stats,
            "last_update": datetime.now().isoformat(),
        }
        with open(self._state_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _load_state(self):
        """Laad staat."""
        if self._state_file.exists():
            try:
                with open(self._state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                nutrients = data.get("nutrients", {})
                self.nutrients.protein = nutrients.get("protein", 50)
                self.nutrients.carbs = nutrients.get("carbs", 50)
                self.nutrients.vitamins = nutrients.get("vitamins", 50)
                self.nutrients.water = nutrients.get("water", 50)
                self.nutrients.fiber = nutrients.get("fiber", 50)

                self.state = MetabolicState(data.get("state", "stable"))

            except (json.JSONDecodeError, IOError, OSError,
                    KeyError, ValueError):
                pass

    def get_status(self) -> Dict:
        """Haal volledige status op."""
        hunger_name, hunger_level = self.get_hunger_level()

        return {
            "state": self.state.value,
            "nutrients": self.nutrients.to_dict(),
            "total": round(self.nutrients.total, 1),
            "balance": round(self.nutrients.balance_score, 2),
            "hunger": hunger_name,
            "hunger_level": hunger_level,
            "deficiencies": self.stats["deficiencies"],
            "recommendations": self.get_recommendations(),
            "is_running": self.is_running,
        }

    def get_visual_bars(self) -> str:
        """Genereer visuele bars voor nutrients."""
        lines = []
        nutrients = [
            ("Protein (Kennis)", self.nutrients.protein),
            ("Carbs (Energie)", self.nutrients.carbs),
            ("Vitamins (Code)", self.nutrients.vitamins),
            ("Water (Rust)", self.nutrients.water),
            ("Fiber (Balans)", self.nutrients.fiber),
        ]

        for name, value in nutrients:
            filled = int(value / 5)  # 20 char bar
            empty = 20 - filled

            if value < self.CRITICAL_LOW:
                bar = f"[{'!' * filled}{' ' * empty}]"  # Critical
            elif value < self.WARNING_LOW:
                bar = f"[{'#' * filled}{' ' * empty}]"  # Warning
            else:
                bar = f"[{'=' * filled}{' ' * empty}]"  # Normal

            lines.append(f"  {name:20} {bar} {value:.0f}%")

        return "\n".join(lines)

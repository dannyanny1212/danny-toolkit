"""
SelfImprovementEngine - De kern van echte AI self-learning.

Dit systeem verzamelt learning signals uit alle componenten
en past parameters automatisch aan voor continue verbetering.

AUTHOR: Danny Toolkit
DATE: 7 februari 2026
STATUS: CORE SELF-LEARNING
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, asdict, field

try:
    from ..core.config import Config
    HAS_CONFIG = True
except ImportError:
    HAS_CONFIG = False


@dataclass
class LearningSignal:
    """Een learning signal van een component."""
    source: str  # "feedback", "performance", "daemon", "workflow"
    signal_type: str  # "positive", "negative", "neutral"
    strength: float  # 0.0 - 1.0
    target: str  # Which system should learn
    data: dict = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class Adaptation:
    """Een parameter adaptatie."""
    name: str
    old_value: float
    new_value: float
    signal_source: str
    signal_type: str
    timestamp: str


class SelfImprovementEngine:
    """
    Centraal engine voor AI self-improvement.

    Verzamelt signalen uit alle systemen en past
    parameters automatisch aan voor verbetering.

    Dit is het hart van de zelflerende AI.
    """

    def __init__(
        self,
        data_dir: Path = None,
        performance_analyzer=None,
        feedback_manager=None
    ):
        if data_dir is None and HAS_CONFIG:
            data_dir = Config.APPS_DATA_DIR
        elif data_dir is None:
            data_dir = Path("data/apps")

        self.data_dir = data_dir
        self.state_file = data_dir / "self_improvement_state.json"
        self.performance = performance_analyzer
        self.feedback = feedback_manager
        self._state = self._load()
        self._adaptations: Dict[str, dict] = {}

    def _load(self) -> dict:
        """Laad self-improvement state."""
        if self.state_file.exists():
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass

        return {
            "learning_cycles": 0,
            "total_adaptations": 0,
            "last_improvement": None,
            "parameter_history": {},
            "effectiveness_scores": {},
            "signals_processed": 0,
            "meta_learning": {
                "what_works": [],
                "what_fails": [],
                "experiments": [],
                "insights": []
            },
            "created": datetime.now().isoformat()
        }

    def save(self):
        """Sla state op naar bestand."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(self._state, f, indent=2, ensure_ascii=False)

    def register_adaptation(
        self,
        name: str,
        getter: Callable[[], float],
        setter: Callable[[float], None],
        bounds: tuple = (0.0, 1.0),
        learning_rate: float = 0.1,
        description: str = ""
    ):
        """
        Registreer een parameter die kan worden aangepast.

        Args:
            name: Naam van de parameter
            getter: Functie om huidige waarde op te halen
            setter: Functie om nieuwe waarde in te stellen
            bounds: (min, max) grenzen voor de waarde
            learning_rate: Snelheid van aanpassing (0-1)
            description: Beschrijving van de parameter
        """
        self._adaptations[name] = {
            "getter": getter,
            "setter": setter,
            "bounds": bounds,
            "learning_rate": learning_rate,
            "description": description,
            "history": []
        }

    def collect_signals(self) -> List[LearningSignal]:
        """
        Verzamel learning signals uit alle bronnen.

        Returns:
            Lijst van LearningSignal objecten
        """
        signals = []

        # 1. Feedback signals
        if self.feedback:
            try:
                fb_signals = self.feedback.get_learning_signals()
                for int_id, score in fb_signals.items():
                    signal_type = "positive" if score > 0.6 else (
                        "negative" if score < 0.4 else "neutral"
                    )
                    signals.append(LearningSignal(
                        source="feedback",
                        signal_type=signal_type,
                        strength=abs(score - 0.5) * 2,
                        target="response_quality",
                        data={"interaction_id": int_id, "score": score}
                    ))
            except Exception:
                pass

        # 2. Performance signals
        if self.performance:
            try:
                summary = self.performance.get_learning_summary()
                improvement_rate = summary.get("improvement_rate", 0.5)

                signal_type = "positive" if improvement_rate > 0.5 else (
                    "negative" if improvement_rate < 0.3 else "neutral"
                )

                signals.append(LearningSignal(
                    source="performance",
                    signal_type=signal_type,
                    strength=improvement_rate,
                    target="system_efficiency",
                    data=summary
                ))

                # Add signals for problem areas
                for problem in summary.get("areas_needing_work", []):
                    signals.append(LearningSignal(
                        source="performance",
                        signal_type="negative",
                        strength=problem.get("decline", 0.1),
                        target=problem.get("metric", "unknown"),
                        data=problem
                    ))

            except Exception:
                pass

        return signals

    def learn(self) -> dict:
        """
        Hoofdfunctie: Voer een learning cycle uit.

        1. Verzamel signalen
        2. Analyseer patronen
        3. Pas parameters aan
        4. Registreer resultaten

        Returns:
            Dict met learning resultaten
        """
        self._state["learning_cycles"] += 1

        # Collect signals
        signals = self.collect_signals()

        if not signals:
            return {
                "status": "no_signals",
                "adaptations": 0,
                "cycle": self._state["learning_cycles"]
            }

        # Analyze and adapt
        adaptations_made = 0
        adaptations_detail = []

        for signal in signals:
            if signal.strength > 0.2:  # Only act on meaningful signals
                adapted = self._apply_signal(signal)
                if adapted:
                    adaptations_made += 1
                    adaptations_detail.append(adapted)

        # Update state
        self._state["total_adaptations"] += adaptations_made
        self._state["signals_processed"] += len(signals)
        self._state["last_improvement"] = datetime.now().isoformat()

        # Record meta-learning insight if significant learning occurred
        if adaptations_made > 0:
            self.record_meta_learning(
                "experiment",
                f"Cycle {self._state['learning_cycles']}: "
                f"{adaptations_made} adaptations from {len(signals)} signals"
            )

        self.save()

        return {
            "status": "learned",
            "signals_processed": len(signals),
            "adaptations": adaptations_made,
            "adaptations_detail": adaptations_detail,
            "cycle": self._state["learning_cycles"]
        }

    def _apply_signal(self, signal: LearningSignal) -> Optional[dict]:
        """
        Pas een learning signal toe op relevante parameters.

        Returns:
            Dict met adaptatie details of None
        """
        # Find adaptable parameters for this signal target
        for name, adaptation in self._adaptations.items():
            # Check if this parameter is relevant for the signal target
            if signal.target in name or name in signal.target:
                try:
                    current = adaptation["getter"]()
                    lr = adaptation["learning_rate"]
                    bounds = adaptation["bounds"]

                    # Calculate adjustment
                    if signal.signal_type == "positive":
                        # Reinforce current direction
                        center = (bounds[0] + bounds[1]) / 2
                        if current > center:
                            adjustment = lr * signal.strength
                        else:
                            adjustment = -lr * signal.strength

                        new_value = current + adjustment

                    elif signal.signal_type == "negative":
                        # Move toward center (safe default)
                        center = (bounds[0] + bounds[1]) / 2
                        adjustment = (center - current) * lr * signal.strength
                        new_value = current + adjustment

                    else:  # neutral
                        # Small random exploration
                        import random
                        adjustment = (random.random() - 0.5) * lr * 0.1
                        new_value = current + adjustment

                    # Clamp to bounds
                    new_value = max(bounds[0], min(bounds[1], new_value))

                    # Only apply if change is significant
                    if abs(new_value - current) > 0.001:
                        adaptation["setter"](new_value)
                        adaptation["history"].append({
                            "timestamp": datetime.now().isoformat(),
                            "old": current,
                            "new": new_value,
                            "signal_type": signal.signal_type,
                            "signal_source": signal.source
                        })

                        # Track in state
                        if name not in self._state["parameter_history"]:
                            self._state["parameter_history"][name] = []
                        self._state["parameter_history"][name].append({
                            "value": new_value,
                            "timestamp": datetime.now().isoformat()
                        })

                        # Keep history manageable
                        if len(self._state["parameter_history"][name]) > 100:
                            self._state["parameter_history"][name] = \
                                self._state["parameter_history"][name][-100:]

                        return {
                            "parameter": name,
                            "old_value": round(current, 4),
                            "new_value": round(new_value, 4),
                            "signal_type": signal.signal_type,
                            "signal_source": signal.source
                        }

                except Exception as e:
                    # Log error but continue
                    print(f"Adaptation error for {name}: {e}")

        return None

    def get_improvement_report(self) -> dict:
        """Genereer rapport over self-improvement progress."""
        return {
            "total_cycles": self._state["learning_cycles"],
            "total_adaptations": self._state["total_adaptations"],
            "signals_processed": self._state["signals_processed"],
            "last_improvement": self._state["last_improvement"],
            "parameters_tracked": len(self._state["parameter_history"]),
            "registered_adaptations": len(self._adaptations),
            "meta_insights": {
                "working_strategies": len(
                    self._state["meta_learning"]["what_works"]
                ),
                "failed_strategies": len(
                    self._state["meta_learning"]["what_fails"]
                ),
                "active_experiments": len(
                    self._state["meta_learning"]["experiments"]
                ),
                "total_insights": len(
                    self._state["meta_learning"]["insights"]
                )
            }
        }

    def record_meta_learning(self, insight_type: str, insight: str):
        """
        Registreer meta-learning inzicht.

        Args:
            insight_type: "success", "failure", "experiment", "insight"
            insight: Beschrijving van het inzicht
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "insight": insight
        }

        if insight_type == "success":
            self._state["meta_learning"]["what_works"].append(entry)
        elif insight_type == "failure":
            self._state["meta_learning"]["what_fails"].append(entry)
        elif insight_type == "experiment":
            self._state["meta_learning"]["experiments"].append(entry)
        else:
            self._state["meta_learning"]["insights"].append(entry)

        # Keep lists manageable
        for key in ["what_works", "what_fails", "experiments", "insights"]:
            if len(self._state["meta_learning"][key]) > 50:
                self._state["meta_learning"][key] = \
                    self._state["meta_learning"][key][-50:]

        self.save()

    def get_parameter_history(self, name: str) -> List[dict]:
        """Haal history op voor een parameter."""
        return self._state["parameter_history"].get(name, [])

    def get_meta_learning_summary(self) -> dict:
        """Haal meta-learning samenvatting op."""
        ml = self._state["meta_learning"]
        return {
            "successful_strategies": len(ml["what_works"]),
            "failed_strategies": len(ml["what_fails"]),
            "experiments_run": len(ml["experiments"]),
            "insights_gained": len(ml["insights"]),
            "recent_insights": ml["insights"][-5:] if ml["insights"] else []
        }

    def reset_adaptations(self):
        """Reset alle geregistreerde adaptaties."""
        self._adaptations = {}

    def get_effectiveness_score(self, parameter: str) -> float:
        """
        Bereken hoe effectief een parameter is.

        Returns:
            Score 0-1 gebaseerd op positieve vs negatieve signalen
        """
        if parameter not in self._adaptations:
            return 0.5

        history = self._adaptations[parameter].get("history", [])
        if not history:
            return 0.5

        positive = sum(
            1 for h in history if h.get("signal_type") == "positive"
        )
        negative = sum(
            1 for h in history if h.get("signal_type") == "negative"
        )
        total = positive + negative

        if total == 0:
            return 0.5

        return positive / total


# === CLI voor testing ===

def _cli():
    """Test CLI voor SelfImprovementEngine."""
    from pathlib import Path

    print("SelfImprovementEngine Test CLI")
    print("=" * 40)

    engine = SelfImprovementEngine(Path("data/apps"))

    # Register a test parameter
    test_value = [0.5]  # Use list to allow mutation in closure

    engine.register_adaptation(
        "test_param",
        getter=lambda: test_value[0],
        setter=lambda v: test_value.__setitem__(0, v),
        bounds=(0.0, 1.0),
        learning_rate=0.1
    )

    # Run learning cycle
    result = engine.learn()
    print("\nLearning result:", result)
    print("\nReport:", engine.get_improvement_report())


if __name__ == "__main__":
    _cli()

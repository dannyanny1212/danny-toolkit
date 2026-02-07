"""
FeedbackManager - Centraal feedback systeem voor self-learning.

Dit systeem verzamelt user feedback op AI responses en gebruikt
deze om het learning systeem te verbeteren.

AUTHOR: Danny Toolkit
DATE: 7 februari 2026
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict
from dataclasses import dataclass, asdict

try:
    from ..core.config import Config
    HAS_CONFIG = True
except ImportError:
    HAS_CONFIG = False


@dataclass
class FeedbackEntry:
    """Een feedback entry van de gebruiker."""
    interaction_id: str
    timestamp: str
    rating: int  # 1-5 sterren
    helpful: bool
    category: str  # "correct", "incorrect", "partial", "excellent"
    comments: str = ""


class FeedbackManager:
    """
    Beheert user feedback voor echte self-learning.

    Verzamelt feedback op AI responses en berekent
    learning signals die teruggekoppeld worden naar
    andere systemen.
    """

    def __init__(self, data_dir: Path = None):
        if data_dir is None and HAS_CONFIG:
            data_dir = Config.APPS_DATA_DIR
        elif data_dir is None:
            data_dir = Path("data/apps")

        self.data_dir = data_dir
        self.feedback_file = data_dir / "feedback.json"
        self._data = self._load()

    def _load(self) -> dict:
        """Laad feedback data uit bestand."""
        if self.feedback_file.exists():
            try:
                with open(self.feedback_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass

        return {
            "entries": [],
            "stats": {
                "total_feedback": 0,
                "avg_rating": 0.0,
                "helpful_ratio": 0.0,
                "category_counts": {}
            },
            "last_update": None
        }

    def save(self):
        """Sla feedback data op naar bestand."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._data["last_update"] = datetime.now().isoformat()
        with open(self.feedback_file, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)

    def submit(
        self,
        interaction_id: str,
        rating: int,
        helpful: bool,
        category: str = "rated",
        comments: str = ""
    ) -> bool:
        """
        Submit feedback voor een interactie.

        Args:
            interaction_id: ID van de interactie
            rating: 1-5 sterren
            helpful: Was het antwoord nuttig?
            category: Type feedback (correct, incorrect, partial, excellent)
            comments: Optionele opmerkingen

        Returns:
            True als feedback succesvol opgeslagen
        """
        entry = FeedbackEntry(
            interaction_id=interaction_id,
            timestamp=datetime.now().isoformat(),
            rating=max(1, min(5, rating)),
            helpful=helpful,
            category=category,
            comments=comments
        )

        self._data["entries"].append(asdict(entry))
        self._update_stats()
        self.save()
        return True

    def _update_stats(self):
        """Update statistieken na nieuwe feedback."""
        entries = self._data["entries"]
        if not entries:
            return

        stats = self._data["stats"]
        stats["total_feedback"] = len(entries)
        stats["avg_rating"] = sum(e["rating"] for e in entries) / len(entries)
        stats["helpful_ratio"] = sum(
            1 for e in entries if e["helpful"]
        ) / len(entries)

        # Category counts
        category_counts = {}
        for entry in entries:
            cat = entry["category"]
            category_counts[cat] = category_counts.get(cat, 0) + 1
        stats["category_counts"] = category_counts

    def get_feedback_for(self, interaction_id: str) -> Optional[dict]:
        """Haal feedback op voor een specifieke interactie."""
        for entry in self._data["entries"]:
            if entry["interaction_id"] == interaction_id:
                return entry
        return None

    def get_recent_feedback(self, limit: int = 10) -> List[dict]:
        """Haal recente feedback op."""
        return self._data["entries"][-limit:]

    def get_stats(self) -> dict:
        """Haal feedback statistieken op."""
        return self._data["stats"].copy()

    def get_learning_signals(self) -> Dict[str, float]:
        """
        Bereken learning signals uit feedback.

        Returns:
            Dict met interaction_id -> score (0-1) mappings
        """
        if not self._data["entries"]:
            return {}

        signals = {}
        for entry in self._data["entries"]:
            int_id = entry["interaction_id"]
            # Convert rating (1-5) to score (0-1)
            # Rating 1 = 0.0, Rating 5 = 1.0
            signals[int_id] = (entry["rating"] - 1) / 4.0

        return signals

    def get_negative_patterns(self) -> List[dict]:
        """
        Vind patterns in negatieve feedback.

        Returns:
            Lijst van interacties met rating <= 2
        """
        return [
            entry for entry in self._data["entries"]
            if entry["rating"] <= 2
        ]

    def get_positive_patterns(self) -> List[dict]:
        """
        Vind patterns in positieve feedback.

        Returns:
            Lijst van interacties met rating >= 4
        """
        return [
            entry for entry in self._data["entries"]
            if entry["rating"] >= 4
        ]

    def calculate_improvement_trend(self) -> dict:
        """
        Bereken of feedback over tijd verbetert.

        Returns:
            Dict met trend informatie
        """
        entries = self._data["entries"]
        if len(entries) < 10:
            return {
                "sufficient_data": False,
                "trend": "unknown"
            }

        # Vergelijk eerste en laatste helft
        half = len(entries) // 2
        first_half = entries[:half]
        second_half = entries[half:]

        first_avg = sum(e["rating"] for e in first_half) / len(first_half)
        second_avg = sum(e["rating"] for e in second_half) / len(second_half)

        improvement = second_avg - first_avg

        return {
            "sufficient_data": True,
            "first_half_avg": round(first_avg, 2),
            "second_half_avg": round(second_avg, 2),
            "improvement": round(improvement, 2),
            "trend": "improving" if improvement > 0.2 else (
                "declining" if improvement < -0.2 else "stable"
            )
        }


# === CLI voor testing ===

def _cli():
    """Test CLI voor FeedbackManager."""
    from pathlib import Path

    print("FeedbackManager Test CLI")
    print("=" * 40)

    fm = FeedbackManager(Path("data/apps"))

    # Submit test feedback
    fm.submit("test_001", rating=4, helpful=True, category="correct")
    fm.submit("test_002", rating=5, helpful=True, category="excellent")
    fm.submit("test_003", rating=2, helpful=False, category="incorrect")

    print("\nStats:", fm.get_stats())
    print("\nLearning Signals:", fm.get_learning_signals())
    print("\nTrend:", fm.calculate_improvement_trend())


if __name__ == "__main__":
    _cli()

"""
InteractionTracker - Log en analyseer alle interacties.

Houdt bij:
- Elke chat interactie met context (geluk, energie, IQ)
- Success scores per interactie
- Gebruikerspatronen en voorkeuren
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..core.config import Config


class InteractionTracker:
    """Track alle interacties voor learning."""

    MAX_INTERACTIONS = 500

    def __init__(self):
        """Initialiseer InteractionTracker."""
        Config.ensure_dirs()
        self.data_dir = Config.APPS_DATA_DIR / "learning"
        self.data_dir.mkdir(exist_ok=True)
        self.interactions_file = self.data_dir / "interactions.json"
        self._data = self._load()

    def _load(self) -> dict:
        """Laad interacties van disk."""
        if self.interactions_file.exists():
            try:
                with open(self.interactions_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return self._create_empty()

    def _create_empty(self) -> dict:
        """Maak lege data structuur."""
        return {
            "version": "1.0",
            "created": datetime.now().isoformat(),
            "interactions": [],
            "stats": {
                "total": 0,
                "by_type": {},
                "avg_success": 0.0,
                "last_optimization": None,
            },
        }

    def save(self):
        """Sla data op naar disk."""
        if len(self._data["interactions"]) > self.MAX_INTERACTIONS:
            self._prune_old()
        with open(self.interactions_file, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)

    def _prune_old(self):
        """Verwijder oude interacties, behoud beste scores."""
        interactions = self._data["interactions"]
        interactions.sort(key=lambda x: x.get("success_score", 0), reverse=True)
        high_score = interactions[:100]
        recent = sorted(
            interactions[100:],
            key=lambda x: x.get("timestamp", ""),
            reverse=True,
        )[:self.MAX_INTERACTIONS - 100]

        self._data["interactions"] = high_score + recent

    def log_interaction(
        self,
        interaction_type: str,
        user_input: str,
        ai_output: str,
        context: Optional[dict] = None,
        success_score: float = 0.5,
    ) -> str:
        """Log een interactie.

        Args:
            interaction_type: Type interactie (chat, learn_rag, learn_news, etc.)
            user_input: Gebruikers input
            ai_output: AI response
            context: Optionele context (geluk, energie, IQ, etc.)
            success_score: Score 0-1 die aangeeft hoe succesvol de interactie was

        Returns:
            Interaction ID
        """
        interaction_id = f"int_{int(time.time())}_{len(self._data['interactions'])}"

        interaction = {
            "id": interaction_id,
            "type": interaction_type,
            "timestamp": datetime.now().isoformat(),
            "input": user_input,
            "output": ai_output,
            "context": context or {},
            "success_score": success_score,
        }

        self._data["interactions"].append(interaction)
        self._data["stats"]["total"] += 1

        by_type = self._data["stats"]["by_type"]
        by_type[interaction_type] = by_type.get(interaction_type, 0) + 1

        self._update_avg_success()
        self.save()

        return interaction_id

    def _update_avg_success(self):
        """Update gemiddelde success score."""
        scores = [i.get("success_score", 0.5) for i in self._data["interactions"]]
        if scores:
            self._data["stats"]["avg_success"] = sum(scores) / len(scores)

    def update_success_score(self, interaction_id: str, new_score: float):
        """Update de success score van een interactie."""
        for interaction in self._data["interactions"]:
            if interaction["id"] == interaction_id:
                interaction["success_score"] = new_score
                self._update_avg_success()
                self.save()
                return True
        return False

    def get_recent(self, n: int = 10, interaction_type: Optional[str] = None) -> list:
        """Haal recente interacties op."""
        interactions = self._data["interactions"]

        if interaction_type:
            interactions = [
                i for i in interactions if i["type"] == interaction_type
            ]

        interactions.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return interactions[:n]

    def get_successful(self, min_score: float = 0.8, n: int = 20) -> list:
        """Haal succesvolle interacties op."""
        interactions = [
            i for i in self._data["interactions"]
            if i.get("success_score", 0) >= min_score
        ]
        interactions.sort(key=lambda x: x.get("success_score", 0), reverse=True)
        return interactions[:n]

    def get_by_input(self, query: str) -> list:
        """Zoek interacties met vergelijkbare input."""
        query_lower = query.lower()
        results = []

        for interaction in self._data["interactions"]:
            input_lower = interaction.get("input", "").lower()
            if query_lower in input_lower or input_lower in query_lower:
                results.append(interaction)

        results.sort(key=lambda x: x.get("success_score", 0), reverse=True)
        return results

    def get_stats(self) -> dict:
        """Haal statistieken op."""
        return {
            "total_interactions": self._data["stats"]["total"],
            "by_type": self._data["stats"]["by_type"],
            "avg_success": self._data["stats"]["avg_success"],
            "stored_interactions": len(self._data["interactions"]),
        }

    def get_learning_insights(self) -> dict:
        """Analyseer interacties voor learning insights."""
        interactions = self._data["interactions"]

        if not interactions:
            return {"status": "no_data"}

        successful = [i for i in interactions if i.get("success_score", 0) >= 0.8]
        failed = [i for i in interactions if i.get("success_score", 0) < 0.3]

        input_lengths = [len(i.get("input", "")) for i in successful]
        output_lengths = [len(i.get("output", "")) for i in successful]

        return {
            "total": len(interactions),
            "successful_count": len(successful),
            "failed_count": len(failed),
            "success_rate": len(successful) / max(len(interactions), 1),
            "avg_successful_input_length": (
                sum(input_lengths) / max(len(input_lengths), 1)
            ),
            "avg_successful_output_length": (
                sum(output_lengths) / max(len(output_lengths), 1)
            ),
            "most_common_type": max(
                self._data["stats"]["by_type"],
                key=self._data["stats"]["by_type"].get,
                default="none",
            ),
        }

    def clear_old(self, days: int = 90) -> int:
        """Verwijder interacties ouder dan X dagen."""
        from datetime import timedelta

        cutoff = datetime.now() - timedelta(days=days)
        cutoff_str = cutoff.isoformat()

        original_count = len(self._data["interactions"])
        self._data["interactions"] = [
            i for i in self._data["interactions"]
            if i.get("timestamp", "") >= cutoff_str
            or i.get("success_score", 0) >= 0.8
        ]

        removed = original_count - len(self._data["interactions"])
        if removed > 0:
            self.save()
        return removed

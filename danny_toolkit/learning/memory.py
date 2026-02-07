"""
UnifiedMemory - Gecombineerd geheugensysteem.

Combineert VectorStore + permanente kennis + AI memory in een
unified interface voor semantic search over alle interacties.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..core.config import Config


class UnifiedMemory:
    """Unified Memory System dat alle kennisbronnen combineert."""

    def __init__(self):
        """Initialiseer UnifiedMemory met alle bronnen."""
        Config.ensure_dirs()
        self.memory_file = Config.APPS_DATA_DIR / "unified_memory.json"
        self._memory = self._load()

    def _load(self) -> dict:
        """Laad geheugen van disk."""
        if self.memory_file.exists():
            try:
                with open(self.memory_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return self._create_empty()

    def _create_empty(self) -> dict:
        """Maak lege geheugenstructuur."""
        return {
            "version": "1.0",
            "created": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "knowledge": {
                "facts": [],
                "sources": [],
                "learned_at": [],
                "usage_count": [],
                "success_scores": [],
            },
            "embeddings": [],
            "metadata": {
                "total_queries": 0,
                "total_hits": 0,
                "avg_relevance": 0.0,
            },
        }

    def save(self):
        """Sla geheugen op naar disk."""
        self._memory["last_updated"] = datetime.now().isoformat()
        with open(self.memory_file, "w", encoding="utf-8") as f:
            json.dump(self._memory, f, indent=2, ensure_ascii=False)

    def add_fact(
        self,
        fact: str,
        source: str = "unknown",
        success_score: float = 0.5,
    ):
        """Voeg een feit toe aan het geheugen."""
        knowledge = self._memory["knowledge"]

        if fact in knowledge["facts"]:
            idx = knowledge["facts"].index(fact)
            knowledge["usage_count"][idx] += 1
            old_score = knowledge["success_scores"][idx]
            knowledge["success_scores"][idx] = (old_score + success_score) / 2
            return False

        knowledge["facts"].append(fact)
        knowledge["sources"].append(source)
        knowledge["learned_at"].append(datetime.now().isoformat())
        knowledge["usage_count"].append(1)
        knowledge["success_scores"].append(success_score)

        self.save()
        return True

    def search(
        self,
        query: str,
        top_k: int = 5,
        min_score: float = 0.0,
    ) -> list[dict]:
        """Zoek relevante feiten met simple text matching.

        Voor echte semantic search zou dit embeddings moeten gebruiken,
        maar voor nu gebruiken we keyword matching.
        """
        results = []
        query_words = set(query.lower().split())
        knowledge = self._memory["knowledge"]

        for i, fact in enumerate(knowledge["facts"]):
            fact_words = set(fact.lower().split())
            overlap = len(query_words & fact_words)

            if overlap > 0:
                score = overlap / max(len(query_words), 1)
                if score >= min_score:
                    results.append({
                        "fact": fact,
                        "source": knowledge["sources"][i],
                        "score": score,
                        "usage_count": knowledge["usage_count"][i],
                        "success_score": knowledge["success_scores"][i],
                    })

        results.sort(key=lambda x: (x["score"], x["success_score"]), reverse=True)
        self._memory["metadata"]["total_queries"] += 1
        if results:
            self._memory["metadata"]["total_hits"] += 1

        return results[:top_k]

    def get_top_facts(self, n: int = 10) -> list[dict]:
        """Haal de meest relevante feiten op gebaseerd op usage en score."""
        knowledge = self._memory["knowledge"]
        facts_with_meta = []

        for i, fact in enumerate(knowledge["facts"]):
            facts_with_meta.append({
                "fact": fact,
                "source": knowledge["sources"][i],
                "usage_count": knowledge["usage_count"][i],
                "success_score": knowledge["success_scores"][i],
                "rank": knowledge["usage_count"][i] * knowledge["success_scores"][i],
            })

        facts_with_meta.sort(key=lambda x: x["rank"], reverse=True)
        return facts_with_meta[:n]

    def update_score(self, fact: str, new_score: float):
        """Update de success score van een feit."""
        knowledge = self._memory["knowledge"]
        if fact in knowledge["facts"]:
            idx = knowledge["facts"].index(fact)
            old_score = knowledge["success_scores"][idx]
            knowledge["success_scores"][idx] = (old_score * 0.7 + new_score * 0.3)
            self.save()

    def increment_usage(self, fact: str):
        """Verhoog usage count van een feit."""
        knowledge = self._memory["knowledge"]
        if fact in knowledge["facts"]:
            idx = knowledge["facts"].index(fact)
            knowledge["usage_count"][idx] += 1
            self.save()

    def get_stats(self) -> dict:
        """Haal statistieken op."""
        knowledge = self._memory["knowledge"]
        return {
            "total_facts": len(knowledge["facts"]),
            "total_queries": self._memory["metadata"]["total_queries"],
            "hit_rate": (
                self._memory["metadata"]["total_hits"]
                / max(self._memory["metadata"]["total_queries"], 1)
            ),
            "avg_success_score": (
                sum(knowledge["success_scores"])
                / max(len(knowledge["success_scores"]), 1)
            ),
        }

    def get_all_facts(self) -> list[str]:
        """Haal alle feiten op."""
        return self._memory["knowledge"]["facts"].copy()

    def remove_fact(self, fact: str) -> bool:
        """Verwijder een feit uit het geheugen."""
        knowledge = self._memory["knowledge"]
        if fact in knowledge["facts"]:
            idx = knowledge["facts"].index(fact)
            knowledge["facts"].pop(idx)
            knowledge["sources"].pop(idx)
            knowledge["learned_at"].pop(idx)
            knowledge["usage_count"].pop(idx)
            knowledge["success_scores"].pop(idx)
            self.save()
            return True
        return False

    def sync_with_huisdier(self, huisdier_kennis: dict):
        """Synchroniseer met bestaande huisdier kennis."""
        if "feiten" in huisdier_kennis:
            for feit in huisdier_kennis["feiten"]:
                self.add_fact(feit, source="huisdier_kennis", success_score=0.6)

    def export_to_huisdier(self) -> list[str]:
        """Exporteer top feiten naar huisdier formaat."""
        top_facts = self.get_top_facts(100)
        return [f["fact"] for f in top_facts]

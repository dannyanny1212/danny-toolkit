"""
KnowledgeOptimizer - Consolideer en optimaliseer kennis.

Features:
- Consolideer gerelateerde feiten
- Rank kennis op bruikbaarheid
- Verwijder verouderde/duplicaat kennis
- Intelligent pruning
"""

import json
from datetime import datetime, timedelta

from ..core.config import Config


class KnowledgeOptimizer:
    """Optimaliseer en consolideer kennis."""

    SIMILARITY_THRESHOLD = 0.6
    MAX_FACTS = 500
    STALE_DAYS = 90

    def __init__(self, unified_memory=None):
        """Initialiseer KnowledgeOptimizer.

        Args:
            unified_memory: Optionele UnifiedMemory instance voor directe toegang.
        """
        Config.ensure_dirs()
        self.data_dir = Config.APPS_DATA_DIR / "learning"
        self.data_dir.mkdir(exist_ok=True)
        self.optimizer_file = self.data_dir / "optimizer_state.json"
        self._state = self._load_state()
        self._memory = unified_memory

    def _load_state(self) -> dict:
        """Laad optimizer state."""
        if self.optimizer_file.exists():
            try:
                with open(self.optimizer_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {
            "version": "1.0",
            "last_optimization": None,
            "consolidations": 0,
            "duplicates_removed": 0,
            "stale_removed": 0,
            "optimization_history": [],
        }

    def _save_state(self):
        """Sla optimizer state op."""
        with open(self.optimizer_file, "w", encoding="utf-8") as f:
            json.dump(self._state, f, indent=2, ensure_ascii=False)

    def _text_similarity(self, text1: str, text2: str) -> float:
        """Bereken tekst similariteit via word overlap."""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = len(words1 & words2)
        union = len(words1 | words2)

        return intersection / union if union > 0 else 0.0

    def find_duplicates(self, facts: list[str]) -> list[tuple[int, int, float]]:
        """Vind duplicate feiten.

        Returns:
            Lijst van (index1, index2, similarity_score) tuples.
        """
        duplicates = []

        for i in range(len(facts)):
            for j in range(i + 1, len(facts)):
                sim = self._text_similarity(facts[i], facts[j])
                if sim >= self.SIMILARITY_THRESHOLD:
                    duplicates.append((i, j, sim))

        duplicates.sort(key=lambda x: x[2], reverse=True)
        return duplicates

    def consolidate_facts(
        self,
        facts: list[str],
        max_consolidations: int = 10,
    ) -> tuple[list[str], int]:
        """Consolideer gerelateerde feiten.

        Voegt feiten met hoge overlap samen tot meer complete feiten.

        Returns:
            (nieuwe_feiten_lijst, aantal_consolidaties)
        """
        duplicates = self.find_duplicates(facts)
        consolidated = 0
        removed_indices = set()

        for idx1, idx2, sim in duplicates[:max_consolidations]:
            if idx1 in removed_indices or idx2 in removed_indices:
                continue

            fact1 = facts[idx1]
            fact2 = facts[idx2]

            if len(fact1) >= len(fact2):
                merged = self._merge_facts(fact1, fact2)
                facts[idx1] = merged
                removed_indices.add(idx2)
            else:
                merged = self._merge_facts(fact2, fact1)
                facts[idx2] = merged
                removed_indices.add(idx1)

            consolidated += 1

        new_facts = [f for i, f in enumerate(facts) if i not in removed_indices]
        self._state["consolidations"] += consolidated
        self._save_state()

        return new_facts, consolidated

    def _merge_facts(self, primary: str, secondary: str) -> str:
        """Voeg twee feiten samen, behoud unieke info."""
        primary_words = set(primary.lower().split())
        secondary_words = secondary.lower().split()

        unique_info = []
        for word in secondary_words:
            if word not in primary_words and len(word) > 3:
                unique_info.append(word)

        if unique_info and len(unique_info) <= 5:
            if not primary.endswith("."):
                primary += "."
            primary += f" (ook: {', '.join(unique_info[:3])})"

        return primary

    def remove_duplicates(self, facts: list[str]) -> tuple[list[str], int]:
        """Verwijder exacte duplicaten.

        Returns:
            (unieke_feiten, aantal_verwijderd)
        """
        seen = set()
        unique = []

        for fact in facts:
            normalized = fact.lower().strip()
            if normalized not in seen:
                seen.add(normalized)
                unique.append(fact)

        removed = len(facts) - len(unique)
        self._state["duplicates_removed"] += removed
        self._save_state()

        return unique, removed

    def remove_stale(
        self,
        facts: list[str],
        learned_dates: list[str],
        usage_counts: list[int],
        max_age_days: int = None,
    ) -> tuple[list[str], list[str], list[int], int]:
        """Verwijder verouderde en ongebruikte feiten.

        Args:
            facts: Lijst van feiten
            learned_dates: ISO datum strings per feit
            usage_counts: Gebruik tellingen per feit
            max_age_days: Max leeftijd in dagen (default: STALE_DAYS)

        Returns:
            (filtered_facts, filtered_dates, filtered_counts, removed_count)
        """
        if max_age_days is None:
            max_age_days = self.STALE_DAYS

        cutoff = datetime.now() - timedelta(days=max_age_days)
        cutoff_str = cutoff.isoformat()

        new_facts = []
        new_dates = []
        new_counts = []

        for i, fact in enumerate(facts):
            date = learned_dates[i] if i < len(learned_dates) else ""
            count = usage_counts[i] if i < len(usage_counts) else 0

            if date >= cutoff_str or count >= 2:
                new_facts.append(fact)
                new_dates.append(date)
                new_counts.append(count)

        removed = len(facts) - len(new_facts)
        self._state["stale_removed"] += removed
        self._save_state()

        return new_facts, new_dates, new_counts, removed

    def rank_knowledge(
        self,
        facts: list[str],
        usage_counts: list[int],
        success_scores: list[float],
    ) -> list[tuple[str, float]]:
        """Rank feiten op bruikbaarheid.

        Returns:
            Lijst van (feit, rank_score) gesorteerd op score.
        """
        ranked = []

        for i, fact in enumerate(facts):
            usage = usage_counts[i] if i < len(usage_counts) else 0
            success = success_scores[i] if i < len(success_scores) else 0.5

            usage_normalized = min(usage / 10, 1.0)
            rank_score = (usage_normalized * 0.4) + (success * 0.6)
            ranked.append((fact, rank_score))

        ranked.sort(key=lambda x: x[1], reverse=True)
        return ranked

    def optimize_all(self, facts: list[str]) -> dict:
        """Voer volledige optimalisatie uit.

        Returns:
            Dict met optimalisatie resultaten.
        """
        original_count = len(facts)

        facts, dedup_count = self.remove_duplicates(facts)
        facts, consolidate_count = self.consolidate_facts(facts)

        if len(facts) > self.MAX_FACTS:
            facts = facts[:self.MAX_FACTS]
            trimmed = original_count - self.MAX_FACTS
        else:
            trimmed = 0

        self._state["last_optimization"] = datetime.now().isoformat()
        self._state["optimization_history"].append({
            "timestamp": datetime.now().isoformat(),
            "original_count": original_count,
            "final_count": len(facts),
            "duplicates_removed": dedup_count,
            "consolidated": consolidate_count,
            "trimmed": trimmed,
        })

        if len(self._state["optimization_history"]) > 50:
            self._state["optimization_history"] = (
                self._state["optimization_history"][-50:]
            )

        self._save_state()

        return {
            "original_count": original_count,
            "final_count": len(facts),
            "duplicates_removed": dedup_count,
            "consolidated": consolidate_count,
            "trimmed": trimmed,
            "optimized_facts": facts,
        }

    def get_stats(self) -> dict:
        """Haal optimizer statistieken op."""
        return {
            "last_optimization": self._state["last_optimization"],
            "total_consolidations": self._state["consolidations"],
            "total_duplicates_removed": self._state["duplicates_removed"],
            "total_stale_removed": self._state["stale_removed"],
            "optimization_runs": len(self._state["optimization_history"]),
        }

    def needs_optimization(self, fact_count: int) -> bool:
        """Check of optimalisatie nodig is."""
        if fact_count > self.MAX_FACTS:
            return True

        last = self._state["last_optimization"]
        if not last:
            return fact_count >= 50

        last_date = datetime.fromisoformat(last)
        days_since = (datetime.now() - last_date).days

        return days_since >= 7 and fact_count >= 100

    def suggest_improvements(self, facts: list[str]) -> list[str]:
        """Suggereer verbeteringen voor de kennisbank."""
        suggestions = []

        if len(facts) > self.MAX_FACTS * 0.8:
            suggestions.append(
                f"Kennisbank bijna vol ({len(facts)}/{self.MAX_FACTS}). "
                "Overweeg optimalisatie."
            )

        duplicates = self.find_duplicates(facts)
        if duplicates:
            suggestions.append(
                f"Er zijn {len(duplicates)} mogelijke duplicaten gevonden. "
                "Consolidatie wordt aanbevolen."
            )

        short_facts = [f for f in facts if len(f) < 20]
        if short_facts:
            suggestions.append(
                f"{len(short_facts)} zeer korte feiten gevonden. "
                "Overweeg deze te verwijderen of uit te breiden."
            )

        return suggestions

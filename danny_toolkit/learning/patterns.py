"""
PatternRecognizer - Herken patronen en cache succesvolle antwoorden.

Features:
- Detecteert veelgestelde vragen
- Cached succesvolle antwoorden voor instant response
- Leert gebruikersvoorkeuren
"""

import json
import re
from datetime import datetime
from typing import Optional

from ..core.config import Config


class PatternRecognizer:
    """Herken patronen in gebruikersinteracties."""

    MIN_CACHE_SCORE = 0.8
    MIN_FREQUENCY_FOR_CACHE = 3

    def __init__(self):
        """Initialiseer PatternRecognizer."""
        Config.ensure_dirs()
        self.data_dir = Config.APPS_DATA_DIR / "learning"
        self.data_dir.mkdir(exist_ok=True)
        self.patterns_file = self.data_dir / "patterns.json"
        self._data = self._load()

    def _load(self) -> dict:
        """Laad patterns van disk."""
        if self.patterns_file.exists():
            try:
                with open(self.patterns_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return self._create_empty()

    def _create_empty(self) -> dict:
        """Maak lege data structuur."""
        return {
            "version": "1.0",
            "created": datetime.now().isoformat(),
            "frequent_queries": {},
            "cached_responses": [],
            "user_preferences": {
                "humor": "medium",
                "detail_level": "medium",
                "topics": [],
                "language_style": "friendly",
            },
            "query_patterns": {},
            "stats": {
                "cache_hits": 0,
                "cache_misses": 0,
                "patterns_detected": 0,
            },
        }

    def save(self):
        """Sla data op naar disk."""
        with open(self.patterns_file, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)

    def _normalize_query(self, query: str) -> str:
        """Normaliseer query voor matching."""
        query = query.lower().strip()
        query = re.sub(r"[?!.,;:]", "", query)
        query = re.sub(r"\s+", " ", query)
        return query

    def record_query(self, query: str):
        """Registreer een query voor frequentie tracking."""
        normalized = self._normalize_query(query)

        if len(normalized) < 3:
            return

        freq = self._data["frequent_queries"]
        freq[normalized] = freq.get(normalized, 0) + 1
        self.save()

    def get_cached_response(self, query: str) -> Optional[str]:
        """Haal cached response op als beschikbaar.

        Returns:
            Response string als cache hit, None anders.
        """
        normalized = self._normalize_query(query)

        for cached in self._data["cached_responses"]:
            cached_query = cached.get("query", "")
            if self._queries_match(normalized, cached_query):
                cached["hits"] = cached.get("hits", 0) + 1
                cached["last_used"] = datetime.now().isoformat()
                self._data["stats"]["cache_hits"] += 1
                self.save()
                return cached["response"]

        self._data["stats"]["cache_misses"] += 1
        return None

    def _queries_match(self, q1: str, q2: str) -> bool:
        """Check of twee queries matchen."""
        if q1 == q2:
            return True

        words1 = set(q1.split())
        words2 = set(q2.split())

        if len(words1) < 2 or len(words2) < 2:
            return False

        overlap = len(words1 & words2)
        total = len(words1 | words2)

        return overlap / total >= 0.7

    def cache_response(
        self,
        query: str,
        response: str,
        score: float,
    ):
        """Cache een succesvolle response.

        Alleen responses met score >= MIN_CACHE_SCORE worden gecached.
        """
        if score < self.MIN_CACHE_SCORE:
            return False

        normalized = self._normalize_query(query)

        for cached in self._data["cached_responses"]:
            if self._queries_match(normalized, cached["query"]):
                if score > cached.get("score", 0):
                    cached["response"] = response
                    cached["score"] = score
                    cached["updated"] = datetime.now().isoformat()
                    self.save()
                return True

        if len(self._data["cached_responses"]) >= 100:
            self._data["cached_responses"].sort(
                key=lambda x: (x.get("score", 0), x.get("hits", 0)),
                reverse=True,
            )
            self._data["cached_responses"] = self._data["cached_responses"][:80]

        self._data["cached_responses"].append({
            "query": normalized,
            "response": response,
            "score": score,
            "hits": 0,
            "created": datetime.now().isoformat(),
            "last_used": datetime.now().isoformat(),
        })
        self.save()
        return True

    def get_frequent_queries(self, min_count: int = 3) -> list[tuple[str, int]]:
        """Haal veelgestelde vragen op."""
        freq = self._data["frequent_queries"]
        frequent = [(q, c) for q, c in freq.items() if c >= min_count]
        frequent.sort(key=lambda x: x[1], reverse=True)
        return frequent[:20]

    def detect_topic_preference(self, queries: list[str]) -> list[str]:
        """Detecteer topic voorkeuren uit queries."""
        topic_keywords = {
            "tech": ["python", "code", "ai", "machine", "learning", "api"],
            "science": ["wetenschap", "natuur", "fysica", "chemie", "biologie"],
            "games": ["spel", "game", "spelen", "punten", "score"],
            "weather": ["weer", "regen", "zon", "temperatuur", "wind"],
            "news": ["nieuws", "artikel", "bericht", "update"],
            "food": ["eten", "voedsel", "recept", "honger", "snack"],
            "health": ["gezondheid", "sport", "fitness", "energie"],
        }

        detected = {}
        for query in queries:
            query_lower = query.lower()
            for topic, keywords in topic_keywords.items():
                for kw in keywords:
                    if kw in query_lower:
                        detected[topic] = detected.get(topic, 0) + 1
                        break

        preferences = [t for t, c in detected.items() if c >= 2]
        if preferences:
            self._data["user_preferences"]["topics"] = preferences
            self.save()

        return preferences

    def update_preference(self, key: str, value):
        """Update een gebruikersvoorkeur."""
        if key in self._data["user_preferences"]:
            self._data["user_preferences"][key] = value
            self.save()

    def get_preferences(self) -> dict:
        """Haal gebruikersvoorkeuren op."""
        return self._data["user_preferences"].copy()

    def get_stats(self) -> dict:
        """Haal pattern statistieken op."""
        stats = self._data["stats"].copy()
        stats["cached_responses_count"] = len(self._data["cached_responses"])
        stats["unique_queries"] = len(self._data["frequent_queries"])

        total = stats["cache_hits"] + stats["cache_misses"]
        stats["cache_hit_rate"] = stats["cache_hits"] / max(total, 1)

        return stats

    def analyze_query_patterns(self) -> dict:
        """Analyseer query patronen voor inzichten."""
        queries = list(self._data["frequent_queries"].keys())

        question_words = ["wat", "hoe", "waarom", "wanneer", "wie", "waar"]
        question_counts = {w: 0 for w in question_words}

        for query in queries:
            for word in question_words:
                if query.startswith(word):
                    question_counts[word] += 1
                    break

        avg_length = (
            sum(len(q) for q in queries) / max(len(queries), 1)
        )

        return {
            "total_unique_queries": len(queries),
            "question_type_distribution": question_counts,
            "avg_query_length": avg_length,
            "most_frequent": self.get_frequent_queries(5),
        }

    def cleanup_old_cache(self, min_score: float = 0.5, max_age_days: int = 30):
        """Ruim oude of slechte cache entries op."""
        from datetime import timedelta

        cutoff = datetime.now() - timedelta(days=max_age_days)
        cutoff_str = cutoff.isoformat()

        original = len(self._data["cached_responses"])
        self._data["cached_responses"] = [
            c for c in self._data["cached_responses"]
            if c.get("score", 0) >= min_score
            and c.get("last_used", c.get("created", "")) >= cutoff_str
        ]

        removed = original - len(self._data["cached_responses"])
        if removed > 0:
            self.save()
        return removed

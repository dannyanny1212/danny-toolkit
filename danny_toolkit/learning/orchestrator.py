"""
LearningSystem - Centrale orchestrator voor self-learning.

Combineert alle learning componenten en biedt een unified interface
voor het virtueel huisdier systeem.
"""

from datetime import datetime
from typing import Optional

from .memory import UnifiedMemory
from .tracker import InteractionTracker
from .patterns import PatternRecognizer
from .optimizer import KnowledgeOptimizer


class LearningSystem:
    """Centrale learning orchestrator."""

    def __init__(self, huisdier_app=None):
        """Initialiseer LearningSystem.

        Args:
            huisdier_app: Optionele referentie naar VirtueelHuisdierApp.
        """
        self.huisdier = huisdier_app
        self.memory = UnifiedMemory()
        self.tracker = InteractionTracker()
        self.patterns = PatternRecognizer()
        self.optimizer = KnowledgeOptimizer(self.memory)

        self._initialized = True
        self._chat_count = 0

    def log_chat(
        self,
        user_input: str,
        ai_response: str,
        context: Optional[dict] = None,
    ) -> str:
        """Log een chat interactie.

        Args:
            user_input: Gebruikers input
            ai_response: AI response
            context: Optionele context (geluk, energie, IQ, etc.)

        Returns:
            Interaction ID
        """
        self.patterns.record_query(user_input)

        success_score = self._estimate_success_score(user_input, ai_response)

        interaction_id = self.tracker.log_interaction(
            interaction_type="chat",
            user_input=user_input,
            ai_output=ai_response,
            context=context,
            success_score=success_score,
        )

        if success_score >= 0.8:
            self.patterns.cache_response(user_input, ai_response, success_score)

        self._chat_count += 1
        if self._chat_count % 10 == 0:
            self._analyze_patterns()

        return interaction_id

    def _estimate_success_score(
        self,
        user_input: str,
        ai_response: str,
    ) -> float:
        """Schat de success score van een interactie.

        Heuristiek gebaseerd op response kwaliteit.
        """
        score = 0.5

        if len(ai_response) >= 20:
            score += 0.1
        if len(ai_response) >= 50:
            score += 0.1

        positive_indicators = [
            "bedankt", "dankje", "leuk", "goed", "super",
            "ja", "perfect", "geweldig", "cool",
        ]
        input_lower = user_input.lower()
        for indicator in positive_indicators:
            if indicator in input_lower:
                score += 0.1
                break

        if "?" not in ai_response and len(ai_response) > 30:
            score += 0.1

        return min(score, 1.0)

    def get_cached_response(self, query: str) -> Optional[str]:
        """Haal cached response op voor snelle antwoord.

        Returns:
            Cached response of None.
        """
        return self.patterns.get_cached_response(query)

    def log_learning(
        self,
        source: str,
        facts_learned: list[str],
        context: Optional[dict] = None,
    ):
        """Log een leer-sessie.

        Args:
            source: Bron (rag, news, weather, ai_conversation)
            facts_learned: Lijst van geleerde feiten
            context: Optionele context
        """
        for fact in facts_learned:
            self.memory.add_fact(fact, source=source, success_score=0.7)

        self.tracker.log_interaction(
            interaction_type=f"learn_{source}",
            user_input=f"Learning session: {source}",
            ai_output=f"Learned {len(facts_learned)} facts",
            context=context,
            success_score=0.8,
        )

    def log_rag_session(
        self,
        files_read: list[str],
        facts_learned: list[str],
        context: Optional[dict] = None,
    ):
        """Log een RAG leer-sessie."""
        self.log_learning("rag", facts_learned, context)
        for fact in facts_learned:
            self.tracker.log_interaction(
                interaction_type="learn_rag",
                user_input=f"Read from: {', '.join(files_read[:3])}",
                ai_output=fact,
                context=context,
                success_score=0.75,
            )

    def log_news_session(
        self,
        topics: list[str],
        facts_learned: list[str],
        context: Optional[dict] = None,
    ):
        """Log een nieuws leer-sessie."""
        self.log_learning("news", facts_learned, context)

    def log_weather_session(
        self,
        location: str,
        weather_info: str,
        context: Optional[dict] = None,
    ):
        """Log een weer leer-sessie."""
        self.tracker.log_interaction(
            interaction_type="learn_weather",
            user_input=f"Weather query: {location}",
            ai_output=weather_info,
            context=context,
            success_score=0.8,
        )

    def log_ai_conversation(
        self,
        questions: list[str],
        answers: list[str],
        lessons: list[str],
        context: Optional[dict] = None,
    ):
        """Log een AI gesprek sessie."""
        for lesson in lessons:
            self.memory.add_fact(lesson, source="ai_conversation", success_score=0.85)

        for q, a in zip(questions, answers):
            self.tracker.log_interaction(
                interaction_type="learn_ai_conversation",
                user_input=q,
                ai_output=a,
                context=context,
                success_score=0.85,
            )

    def _analyze_patterns(self):
        """Analyseer patronen na elke X chats."""
        recent = self.tracker.get_recent(20, interaction_type="chat")
        queries = [i["input"] for i in recent]
        self.patterns.detect_topic_preference(queries)

    def consolidate(self) -> int:
        """Consolideer gerelateerde kennis.

        Returns:
            Aantal geconsolideerde feiten.
        """
        facts = self.memory.get_all_facts()
        if len(facts) < 10:
            return 0

        new_facts, consolidated = self.optimizer.consolidate_facts(facts)

        if consolidated > 0:
            for fact in new_facts:
                self.memory.add_fact(fact, source="consolidated", success_score=0.7)

        return consolidated

    def remove_duplicates(self) -> int:
        """Verwijder duplicate feiten.

        Returns:
            Aantal verwijderde duplicaten.
        """
        facts = self.memory.get_all_facts()
        unique_facts, removed = self.optimizer.remove_duplicates(facts)
        return removed

    def rank_knowledge(self):
        """Rank alle kennis op bruikbaarheid."""
        stats = self.memory.get_stats()
        knowledge = self.memory._memory["knowledge"]

        if not knowledge["facts"]:
            return

        ranked = self.optimizer.rank_knowledge(
            knowledge["facts"],
            knowledge["usage_count"],
            knowledge["success_scores"],
        )

    def optimize(self) -> dict:
        """Voer volledige optimalisatie uit.

        Returns:
            Dict met optimalisatie resultaten.
        """
        facts = self.memory.get_all_facts()
        result = self.optimizer.optimize_all(facts)

        old_removed = self.tracker.clear_old(days=90)
        cache_removed = self.patterns.cleanup_old_cache()

        result["old_interactions_removed"] = old_removed
        result["cache_entries_removed"] = cache_removed

        return result

    def trigger_optimization(self) -> Optional[dict]:
        """Trigger optimalisatie als nodig.

        Returns:
            Optimalisatie resultaten of None als niet nodig.
        """
        facts = self.memory.get_all_facts()

        if self.optimizer.needs_optimization(len(facts)):
            return self.optimize()

        return None

    def get_context_for_chat(self) -> dict:
        """Haal relevante context op voor chat.

        Returns:
            Dict met relevante info voor AI context.
        """
        top_facts = self.memory.get_top_facts(5)
        preferences = self.patterns.get_preferences()
        insights = self.tracker.get_learning_insights()

        return {
            "top_knowledge": [f["fact"] for f in top_facts],
            "user_preferences": preferences,
            "interaction_insights": insights,
        }

    def search_knowledge(self, query: str, top_k: int = 5) -> list[dict]:
        """Zoek relevante kennis voor een query.

        Returns:
            Lijst van relevante feiten met metadata.
        """
        return self.memory.search(query, top_k=top_k)

    def get_stats(self) -> dict:
        """Haal volledige statistieken op."""
        return {
            "memory": self.memory.get_stats(),
            "tracker": self.tracker.get_stats(),
            "patterns": self.patterns.get_stats(),
            "optimizer": self.optimizer.get_stats(),
            "chat_count_this_session": self._chat_count,
        }

    def sync_with_huisdier(self, huisdier_data: dict):
        """Synchroniseer met huisdier kennis data."""
        if "kennis" in huisdier_data:
            self.memory.sync_with_huisdier(huisdier_data["kennis"])

    def export_to_huisdier(self) -> list[str]:
        """Exporteer geoptimaliseerde kennis naar huisdier formaat."""
        return self.memory.export_to_huisdier()

    def get_suggestions(self) -> list[str]:
        """Haal verbeteringssuggesties op."""
        facts = self.memory.get_all_facts()
        return self.optimizer.suggest_improvements(facts)

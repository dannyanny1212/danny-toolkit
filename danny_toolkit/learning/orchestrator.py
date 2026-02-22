"""
LearningSystem - Centrale orchestrator voor self-learning.

Combineert alle learning componenten en biedt een unified interface
voor het virtueel huisdier systeem.

Versie 2.0: Nu met FeedbackManager, PerformanceAnalyzer en
SelfImprovementEngine voor echte self-learning.
"""

from typing import Optional

from ..core.config import Config
from .memory import UnifiedMemory
from .tracker import InteractionTracker
from .patterns import PatternRecognizer
from .optimizer import KnowledgeOptimizer
from .feedback_manager import FeedbackManager
from .performance_analyzer import PerformanceAnalyzer
from .self_improvement import SelfImprovementEngine


class LearningSystem:
    """
    Centrale learning orchestrator.

    Versie 2.0: Nu met self-improvement engine voor echte AI learning.
    """

    def __init__(self, huisdier_app=None):
        """Initialiseer LearningSystem.

        Args:
            huisdier_app: Optionele referentie naar VirtueelHuisdierApp.
        """
        self.huisdier = huisdier_app

        # Core learning components
        self.memory = UnifiedMemory()
        self.tracker = InteractionTracker()
        self.patterns = PatternRecognizer()
        self.optimizer = KnowledgeOptimizer(self.memory)

        # NEW: Self-improvement components
        self.feedback = FeedbackManager(Config.APPS_DATA_DIR)
        self.performance = PerformanceAnalyzer(Config.APPS_DATA_DIR)
        self.improvement = SelfImprovementEngine(
            Config.APPS_DATA_DIR,
            self.performance,
            self.feedback
        )

        self._initialized = True
        self._chat_count = 0
        self._last_interaction_id = None

        # Register adaptable parameters
        self._register_adaptations()

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
        self._last_interaction_id = interaction_id

        if self._chat_count % 10 == 0:
            self._analyze_patterns()

        # Record performance metric
        self.performance.record(
            "learning",
            "chat_success",
            success_score
        )

        return interaction_id

    def _register_adaptations(self):
        """Registreer parameters die automatisch kunnen worden aangepast."""
        # Cache score threshold
        self.improvement.register_adaptation(
            "cache_score_threshold",
            getter=lambda: getattr(self.patterns, "_cache_threshold", 0.8),
            setter=lambda v: setattr(self.patterns, "_cache_threshold", v),
            bounds=(0.5, 0.95),
            learning_rate=0.05,
            description="Minimum score voor cache opslag"
        )

    def process_feedback(
        self,
        feedback_type: str,
        interaction_id: str = None
    ) -> dict:
        """
        Verwerk feedback commando van gebruiker.

        Args:
            feedback_type: "excellent", "good", "ok", "bad", "wrong"
            interaction_id: Optioneel interaction ID (anders laatste)

        Returns:
            Dict met resultaat
        """
        rating_map = {
            "excellent": (5, True, "excellent"),
            "good": (4, True, "correct"),
            "ok": (3, True, "partial"),
            "bad": (2, False, "unhelpful"),
            "wrong": (1, False, "incorrect"),
        }

        if feedback_type not in rating_map:
            return {"success": False, "error": "Onbekend feedback type"}

        rating, helpful, category = rating_map[feedback_type]

        # Use last interaction if no ID provided
        if not interaction_id:
            interaction_id = self._last_interaction_id

        if not interaction_id:
            recent = self.tracker.get_recent(1)
            if recent:
                interaction_id = recent[0].get("id")

        if not interaction_id:
            return {"success": False, "error": "Geen interactie gevonden"}

        # Apply feedback to tracker
        success = self.tracker.apply_feedback(
            interaction_id, rating, helpful, category
        )

        if success:
            # Also store in FeedbackManager
            self.feedback.submit(
                interaction_id, rating, helpful, category
            )

            # Trigger learning update
            self._apply_feedback_to_learning(interaction_id, rating, helpful)

            # Record performance metric
            self.performance.record(
                "feedback",
                "rating",
                rating / 5.0
            )

        return {
            "success": success,
            "interaction_id": interaction_id,
            "rating": rating,
            "category": category
        }

    def _apply_feedback_to_learning(
        self,
        interaction_id: str,
        rating: int,
        helpful: bool
    ):
        """Pas feedback toe op learning systemen."""
        # Get the interaction
        for interaction in self.tracker._data["interactions"]:
            if interaction.get("id") == interaction_id:
                user_input = interaction.get("input", "")

                # Update pattern cache quality
                if rating >= 4:
                    # Good response - reinforce cache
                    self.patterns.record_query(user_input)
                elif rating <= 2:
                    # Bad response - could add cache penalty here
                    pass

                # Update memory fact scores based on feedback
                actual_score = (rating / 5.0) * 0.8 + 0.2
                related_facts = self.memory.search(user_input, top_k=3)

                for fact_data in related_facts:
                    if helpful:
                        self.memory.increment_usage(fact_data["fact"])
                    self.memory.update_score(fact_data["fact"], actual_score)

                break

    def run_learning_cycle(self) -> dict:
        """
        Voer een complete learning cycle uit.

        Dit is het hart van de self-improvement:
        1. Verzamel performance metrics
        2. Run self-improvement engine
        3. Check optimalisatie behoefte

        Returns:
            Dict met learning resultaten
        """
        # 1. Record current stats as metrics
        stats = self.tracker.get_stats()
        self.performance.record(
            "learning",
            "total_interactions",
            stats.get("total_interactions", 0)
        )
        self.performance.record(
            "learning",
            "avg_success",
            stats.get("avg_success", 0.5)
        )

        # Record feedback stats
        fb_stats = self.feedback.get_stats()
        if fb_stats.get("total_feedback", 0) > 0:
            self.performance.record(
                "feedback",
                "avg_rating",
                fb_stats.get("avg_rating", 0) / 5.0
            )
            self.performance.record(
                "feedback",
                "helpful_ratio",
                fb_stats.get("helpful_ratio", 0)
            )

        # 2. Run self-improvement
        improvement_result = self.improvement.learn()

        # 3. Check if optimization needed
        optimization_result = None
        if self._should_optimize():
            optimization_result = self.optimize()

        return {
            "learning_cycle": improvement_result,
            "optimization": optimization_result,
            "performance_summary": self.performance.get_learning_summary()
        }

    def _should_optimize(self) -> bool:
        """Check of optimalisatie nodig is."""
        facts = self.memory.get_all_facts()
        return self.optimizer.needs_optimization(len(facts))

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
            "feedback": self.feedback.get_stats(),
            "performance": self.performance.get_learning_summary(),
            "improvement": self.improvement.get_improvement_report(),
            "chat_count_this_session": self._chat_count,
        }

    def get_self_improvement_report(self) -> dict:
        """Haal self-improvement rapport op."""
        return {
            "improvement_engine": self.improvement.get_improvement_report(),
            "feedback_trend": self.feedback.calculate_improvement_trend(),
            "performance_summary": self.performance.get_learning_summary(),
            "meta_learning": self.improvement.get_meta_learning_summary()
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

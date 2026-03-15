"""
Self-Learning System voor Danny Toolkit.


Dit systeem combineert alle AI-componenten tot een self-learning en
self-improving systeem dat:
- Alle interacties logt en analyseert
- Patronen herkent en succesvolle antwoorden cachet
- Kennis consolideert en optimaliseert
- Automatisch leert van gebruikersgedrag
- User feedback verzamelt en verwerkt
- Performance trends analyseert
- Parameters automatisch aanpast

Architectuur:
    LearningSystem (Orchestrator)
        ├── UnifiedMemory (Backbone)
        ├── InteractionTracker (Logging)
        ├── PatternRecognizer (Caching)
        ├── KnowledgeOptimizer (Consolidatie)
        ├── FeedbackManager (User Feedback)
        ├── PerformanceAnalyzer (Metrics)
        └── SelfImprovementEngine (Self-Learning Core)
"""

from __future__ import annotations

from danny_toolkit.learning.memory import UnifiedMemory
from danny_toolkit.learning.tracker import InteractionTracker
from danny_toolkit.learning.patterns import PatternRecognizer
from danny_toolkit.learning.optimizer import KnowledgeOptimizer
from danny_toolkit.learning.orchestrator import LearningSystem
from danny_toolkit.learning.feedback_manager import FeedbackManager
from danny_toolkit.learning.performance_analyzer import PerformanceAnalyzer
from danny_toolkit.learning.self_improvement import SelfImprovementEngine
import logging

logger = logging.getLogger(__name__)

__all__ = [
    "UnifiedMemory",
    "InteractionTracker",
    "PatternRecognizer",
    "KnowledgeOptimizer",
    "LearningSystem",
    "FeedbackManager",
    "PerformanceAnalyzer",
    "SelfImprovementEngine",
]

__version__ = "7.1.0"

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

from .memory import UnifiedMemory
from .tracker import InteractionTracker
from .patterns import PatternRecognizer
from .optimizer import KnowledgeOptimizer
from .orchestrator import LearningSystem
from .feedback_manager import FeedbackManager
from .performance_analyzer import PerformanceAnalyzer
from .self_improvement import SelfImprovementEngine

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

__version__ = "4.0.0"

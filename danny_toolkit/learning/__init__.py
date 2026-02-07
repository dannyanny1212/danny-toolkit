"""
Self-Learning System voor Virtueel Huisdier.

Dit systeem combineert alle AI-componenten tot een self-learning en
self-improving systeem dat:
- Alle interacties logt en analyseert
- Patronen herkent en succesvolle antwoorden cachet
- Kennis consolideert en optimaliseert
- Automatisch leert van gebruikersgedrag

Architectuur:
    LearningSystem (Orchestrator)
        ├── UnifiedMemory (Backbone)
        ├── InteractionTracker (Logging)
        ├── PatternRecognizer (Caching)
        └── KnowledgeOptimizer (Consolidatie)
"""

from .memory import UnifiedMemory
from .tracker import InteractionTracker
from .patterns import PatternRecognizer
from .optimizer import KnowledgeOptimizer
from .orchestrator import LearningSystem

__all__ = [
    "UnifiedMemory",
    "InteractionTracker",
    "PatternRecognizer",
    "KnowledgeOptimizer",
    "LearningSystem",
]

__version__ = "1.0.0"

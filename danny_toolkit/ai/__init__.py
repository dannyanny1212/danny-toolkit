"""AI module - RAG en AI systemen."""

from .mini_rag import MiniRAG
from .production_rag import ProductionRAG
from .nieuws_agent import NieuwsAgentApp
from .weer_agent import WeerAgentApp
from .claude_chat import ClaudeChatApp
from .vector_studio import VectorStudioApp
from .artificial_life import ArtificialLifeApp
from .nlp_studio import NLPStudioApp
from .advanced_questions import AdvancedQuestionsApp
from .ml_studio import MLStudioApp
from .knowledge_companion import KnowledgeCompanionApp
from .legendary_companion import LegendaryCompanionApp

__all__ = [
    "MiniRAG",
    "ProductionRAG",
    "NieuwsAgentApp",
    "WeerAgentApp",
    "ClaudeChatApp",
    "VectorStudioApp",
    "ArtificialLifeApp",
    "NLPStudioApp",
    "AdvancedQuestionsApp",
    "MLStudioApp",
    "KnowledgeCompanionApp",
    "LegendaryCompanionApp",
]

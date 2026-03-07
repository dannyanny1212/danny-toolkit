"""AI module - RAG en AI systemen.

Lazy imports — modules worden pas geladen bij eerste gebruik.
Voorkomt dat zware afhankelijkheden (Claude API, ProductionRAG)
stiekem geactiveerd worden wanneer een enkele AI-app geladen wordt.
"""

import importlib as _importlib

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

# Lazy import mapping: naam → (submodule, class_name)
_LAZY_MAP = {
    "MiniRAG": (".mini_rag", "MiniRAG"),
    "ProductionRAG": (".production_rag", "ProductionRAG"),
    "NieuwsAgentApp": (".nieuws_agent", "NieuwsAgentApp"),
    "WeerAgentApp": (".weer_agent", "WeerAgentApp"),
    "ClaudeChatApp": (".claude_chat", "ClaudeChatApp"),
    "VectorStudioApp": (".vector_studio", "VectorStudioApp"),
    "ArtificialLifeApp": (".artificial_life", "ArtificialLifeApp"),
    "NLPStudioApp": (".nlp_studio", "NLPStudioApp"),
    "AdvancedQuestionsApp": (".advanced_questions", "AdvancedQuestionsApp"),
    "MLStudioApp": (".ml_studio", "MLStudioApp"),
    "KnowledgeCompanionApp": (".knowledge_companion", "KnowledgeCompanionApp"),
    "LegendaryCompanionApp": (".legendary_companion", "LegendaryCompanionApp"),
}


def __getattr__(name: str):
    """Lazy import — laad module pas bij eerste toegang."""
    if name in _LAZY_MAP:
        sub, cls = _LAZY_MAP[name]
        mod = _importlib.import_module(sub, __package__)
        obj = getattr(mod, cls)
        # Cache in module globals zodat volgende keer direct beschikbaar
        globals()[name] = obj
        return obj
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

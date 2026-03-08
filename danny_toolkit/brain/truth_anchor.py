"""
TruthAnchor — CPU Cross-Encoder Fact Verification (v6.0 Invention).

Verifieert of LLM-antwoorden daadwerkelijk ondersteund worden door de
RAG-bronnen. Gebruikt een lichtgewicht Cross-Encoder (ms-marco-MiniLM)
die op CPU draait. Gate voor _rag_enrich in de swarm pipeline.
"""

from __future__ import annotations

import logging

try:
    from sentence_transformers import CrossEncoder
    HAS_CROSS_ENCODER = True
except ImportError:
    HAS_CROSS_ENCODER = False

from danny_toolkit.core.utils import Kleur

logger = logging.getLogger(__name__)


class TruthAnchor:
    """
    Verifies if an answer is actually supported by the documents.
    Uses CPU-friendly Cross-Encoder.
    """

    DEFAULT_DREMPEL = 0.45

    def __init__(self, drempel: object=None) -> None:
        """Initializes a Truth Anchor instance.

 Args:
     drempel: Optional; The drempel to use. Defaults to self.DEFAULT_DREMPEL if not provided.

 Returns:
     None 

 Raises:
     None"""
        print(f"{Kleur.CYAAN}⚓ Loading Truth Anchor...{Kleur.RESET}")
        if HAS_CROSS_ENCODER:
            self.model = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
        else:
            self.model = None
            logger.debug("TruthAnchor: sentence_transformers not available, verification disabled")
        self.drempel = drempel if drempel is not None else self.DEFAULT_DREMPEL

    def verify(self, answer: str, context_docs: list[str]) -> tuple[bool, float]:
        """
        Returns (grounded: bool, score: float) tuple.

        grounded is True if the answer is supported by context above threshold.
        score is the best cross-encoder similarity score.
        """
        if not context_docs or self.model is None:
            return (False, 0.0)

        # Prepare pairs: (Answer, Doc1), (Answer, Doc2)...
        pairs = [[answer, doc] for doc in context_docs]

        # Score similarity
        scores = self.model.predict(pairs)
        best_score = float(max(scores))

        print(f"⚓ Truth Confidence: {best_score:.2f}")

        return (best_score > self.drempel, best_score)

from sentence_transformers import CrossEncoder
from danny_toolkit.core.utils import Kleur


class TruthAnchor:
    """
    Verifies if an answer is actually supported by the documents.
    Uses CPU-friendly Cross-Encoder.
    """

    DEFAULT_DREMPEL = 0.45

    def __init__(self, drempel=None):
        print(f"{Kleur.CYAAN}⚓ Loading Truth Anchor...{Kleur.RESET}")
        self.model = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
        self.drempel = drempel if drempel is not None else self.DEFAULT_DREMPEL

    def verify(self, answer: str, context_docs: list[str]) -> tuple[bool, float]:
        """
        Returns (grounded: bool, score: float) tuple.

        grounded is True if the answer is supported by context above threshold.
        score is the best cross-encoder similarity score.
        """
        if not context_docs:
            return (False, 0.0)

        # Prepare pairs: (Answer, Doc1), (Answer, Doc2)...
        pairs = [[answer, doc] for doc in context_docs]

        # Score similarity
        scores = self.model.predict(pairs)
        best_score = float(max(scores))

        print(f"⚓ Truth Confidence: {best_score:.2f}")

        return (best_score > self.drempel, best_score)

from sentence_transformers import CrossEncoder
from danny_toolkit.core.utils import Kleur


class TruthAnchor:
    """
    Verifies if an answer is actually supported by the documents.
    Uses CPU-friendly Cross-Encoder.
    """
    def __init__(self):
        print(f"{Kleur.CYAAN}⚓ Loading Truth Anchor...{Kleur.RESET}")
        self.model = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')

    def verify(self, answer: str, context_docs: list[str]) -> bool:
        """
        Returns True if the answer is grounded in context.
        """
        if not context_docs:
            return False  # No context to support the claim

        # Prepare pairs: (Answer, Doc1), (Answer, Doc2)...
        pairs = [[answer, doc] for doc in context_docs]

        # Score similarity
        scores = self.model.predict(pairs)
        best_score = max(scores)

        print(f"⚓ Truth Confidence: {best_score:.2f}")

        # Threshold: < 0.2 usually means "I'm just guessing"
        return best_score > 0.2

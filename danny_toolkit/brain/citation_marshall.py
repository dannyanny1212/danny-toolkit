# danny_toolkit/brain/citation_marshall.py
"""
Citation Marshall — Strict RAG Verification (Hallucination Detection)
Uses TorchGPUEmbeddings masked mean pooling to mathematically verify
if AI-generated claims are supported by retrieved source documents.
"""

import logging
import re
from typing import List, Dict, Optional

try:
    import torch
    import numpy as np
    from danny_toolkit.core.embeddings import get_torch_embedder
    _HAS_DEPS = True
except ImportError:
    _HAS_DEPS = False

from danny_toolkit.core.utils import Kleur

logger = logging.getLogger(__name__)


class CitationMarshall:
    """
    THE CITATION MARSHALL
    ---------------------
    A post-processing layer that strictly validates AI claims against source text.
    Uses TorchGPUEmbeddings to calculate semantic entailment.

    Logic:
    1. Split AI response into sentences.
    2. Extract cited [DocID].
    3. Compare Sentence Vector vs. Doc Chunk Vector.
    4. If Similarity < THRESHOLD (0.65), redact or flag the sentence.
    """

    def __init__(self, embedding_provider: "TorchGPUEmbeddings" = None,
                 threshold: float = 0.65):
        if not _HAS_DEPS:
            raise ImportError(
                "CitationMarshall vereist 'torch', 'numpy' en 'transformers'. "
                "Installeer met: pip install torch numpy transformers"
            )
        self.embedder = embedding_provider or get_torch_embedder()
        self.threshold = threshold
        self.stats = {"verified": 0, "flagged": 0, "uncited": 0}

    def verify_response(self, ai_text: str, retrieved_docs: List[Dict]) -> str:
        """
        Parse AI text, verify citations against source docs, return sanitized text.

        Args:
            ai_text: The AI-generated response containing [1], [2] etc. citations
            retrieved_docs: List of dicts with 'content' key (source chunks)

        Returns:
            Verified text with low-confidence warnings injected
        """
        sentences = self._split_sentences(ai_text)
        verified_text = []

        print(f"{Kleur.BLAUW}[MARSHALL]{Kleur.RESET} Verifying {len(sentences)} claims...")

        for sentence in sentences:
            doc_id = self._extract_citation_id(sentence)

            if doc_id is not None and 0 <= doc_id < len(retrieved_docs):
                # Get source truth
                source_chunk = retrieved_docs[doc_id]["content"]

                # Calculate semantic entailment
                sim_score = self._calculate_entailment(sentence, source_chunk)

                if sim_score >= self.threshold:
                    verified_text.append(sentence)
                    self.stats["verified"] += 1
                    print(f"  {Kleur.GROEN}V Verified{Kleur.RESET} ({sim_score:.2f}): {sentence[:50]}...")
                else:
                    # Hallucination detected — flag but keep
                    redacted = (
                        f"{sentence} "
                        f"{Kleur.ROOD}[! Low Confidence: {sim_score:.2f}]{Kleur.RESET}"
                    )
                    verified_text.append(redacted)
                    self.stats["flagged"] += 1
                    logger.warning(
                        "Hallucination detected (%.2f): '%s' vs source doc %d",
                        sim_score, sentence[:60], doc_id
                    )
            else:
                # No citation — pass through
                verified_text.append(sentence)
                self.stats["uncited"] += 1

        return " ".join(verified_text)

    def _calculate_entailment(self, claim: str, evidence: str) -> float:
        """
        Cosine similarity between claim and evidence embeddings.
        Uses masked mean pooling (padding tokens excluded).
        """
        vectors = self.embedder.embed([claim, evidence])

        # Convert torch tensor to numpy
        if isinstance(vectors, torch.Tensor):
            vectors = vectors.numpy()

        v_claim = vectors[0]
        v_evidence = vectors[1]

        norm_c = np.linalg.norm(v_claim)
        norm_e = np.linalg.norm(v_evidence)

        if norm_c == 0 or norm_e == 0:
            return 0.0

        return float(np.dot(v_claim, v_evidence) / (norm_c * norm_e))

    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences on . ! ? boundaries."""
        return [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]

    def _extract_citation_id(self, text: str) -> Optional[int]:
        """Extract [1], [2] etc. and return 0-based index."""
        match = re.search(r'\[(\d+)\]', text)
        if match:
            return int(match.group(1)) - 1  # 1-based → 0-based
        return None

    def get_stats(self) -> Dict:
        """Return verification statistics."""
        total = sum(self.stats.values())
        return {
            **self.stats,
            "total": total,
            "trust_rate": f"{self.stats['verified'] / total * 100:.1f}%" if total > 0 else "N/A"
        }

    def reset_stats(self):
        """Reset verification counters."""
        self.stats = {"verified": 0, "flagged": 0, "uncited": 0}

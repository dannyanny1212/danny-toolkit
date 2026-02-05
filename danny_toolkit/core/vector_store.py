"""
Vector database met JSON backend.
"""

import json
import math
from pathlib import Path
from .config import Config
from .embeddings import EmbeddingProvider


class VectorStore:
    """
    Persistente vector store met JSON backend.
    Werkt altijd, geen externe dependencies.
    """

    def __init__(self, embedding_provider: EmbeddingProvider, db_file: Path = None):
        self.embedder = embedding_provider
        self.db_file = db_file or Config.VECTOR_DB_FILE
        self.documenten = {}

        # Laad bestaande data
        if self.db_file.exists():
            with open(self.db_file, "r", encoding="utf-8") as f:
                self.documenten = json.load(f)
            print(f"   [OK] Vector DB geladen ({len(self.documenten)} docs)")
        else:
            print(f"   [OK] Vector DB (nieuw)")

    def _opslaan(self):
        """Sla database op naar disk."""
        self.db_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.db_file, "w", encoding="utf-8") as f:
            json.dump(self.documenten, f, ensure_ascii=False, indent=2)

    def voeg_toe(self, documenten: list):
        """
        Voeg documenten toe.
        Args: documenten: List van {"id": str, "tekst": str, "metadata": dict}
        """
        if not documenten:
            return

        teksten = [d["tekst"] for d in documenten]
        embeddings = self.embedder.embed(teksten)

        for doc, emb in zip(documenten, embeddings):
            self.documenten[doc["id"]] = {
                "tekst": doc["tekst"],
                "metadata": doc.get("metadata", {}),
                "embedding": emb
            }

        self._opslaan()
        print(f"   [OK] {len(documenten)} documenten toegevoegd")

    def zoek(self, query: str, top_k: int = None) -> list:
        """Zoek relevante documenten met Cosine Similarity."""
        top_k = top_k or Config.TOP_K

        if not self.documenten:
            return []

        query_emb = self.embedder.embed_query(query)
        scores = []

        for doc_id, data in self.documenten.items():
            score = self._cosine_similarity(query_emb, data["embedding"])
            scores.append({
                "id": doc_id,
                "tekst": data["tekst"],
                "metadata": data["metadata"],
                "score": score
            })

        scores.sort(key=lambda x: x["score"], reverse=True)
        return scores[:top_k]

    def _cosine_similarity(self, vec1: list, vec2: list) -> float:
        """Bereken cosine similarity tussen twee vectoren."""
        dot = sum(a * b for a, b in zip(vec1, vec2))
        mag1 = math.sqrt(sum(a**2 for a in vec1))
        mag2 = math.sqrt(sum(b**2 for b in vec2))
        if mag1 == 0 or mag2 == 0:
            return 0.0
        return dot / (mag1 * mag2)

    def wis(self):
        """Wis alle documenten."""
        self.documenten = {}
        self._opslaan()

    def count(self) -> int:
        """Aantal documenten."""
        return len(self.documenten)

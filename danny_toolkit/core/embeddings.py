"""
Embedding providers voor RAG systemen.
"""

import math
import hashlib
from .config import Config


class EmbeddingProvider:
    """Basis klasse voor embedding providers."""
    dimensies: int = 0

    def embed(self, teksten: list) -> list:
        """Embed meerdere teksten."""
        raise NotImplementedError

    def embed_query(self, query: str) -> list:
        """Embed een enkele query."""
        return self.embed([query])[0]


class VoyageEmbeddings(EmbeddingProvider):
    """Productie embeddings met Voyage AI."""

    def __init__(self, api_key: str = None):
        import voyageai
        self.client = voyageai.Client(api_key=api_key or Config.VOYAGE_API_KEY)
        self.model = Config.VOYAGE_MODEL
        self.dimensies = 1024
        print(f"   [OK] Voyage AI ({self.model}, {self.dimensies}d)")

    def embed(self, teksten: list) -> list:
        """Embed teksten met Voyage AI."""
        result = self.client.embed(
            texts=teksten,
            model=self.model,
            input_type="document"
        )
        return result.embeddings

    def embed_query(self, query: str) -> list:
        """Embed query met Voyage AI."""
        result = self.client.embed(
            texts=[query],
            model=self.model,
            input_type="query"
        )
        return result.embeddings[0]


class HashEmbeddings(EmbeddingProvider):
    """
    Snelle hash-based embeddings (geen externe dependencies).
    Beter dan TF voor semantische similarity.
    """

    def __init__(self, dimensies: int = 256):
        self.dimensies = dimensies
        print(f"   [OK] Hash Embeddings ({dimensies}d)")

    def embed(self, teksten: list) -> list:
        """Embed teksten met hash-methode."""
        return [self._embed_one(t) for t in teksten]

    def _embed_one(self, tekst: str) -> list:
        """Hash-based embedding met n-gram features."""
        vector = [0.0] * self.dimensies

        # Normaliseer tekst
        tekst = tekst.lower()
        woorden = tekst.split()

        # Unigrams
        for woord in woorden:
            woord = "".join(c for c in woord if c.isalnum())
            if len(woord) > 2:
                h = int(hashlib.sha256(woord.encode()).hexdigest(), 16)
                vector[h % self.dimensies] += 1.0

        # Bigrams (voor betere context)
        for i in range(len(woorden) - 1):
            bigram = f"{woorden[i]}_{woorden[i+1]}"
            h = int(hashlib.sha256(bigram.encode()).hexdigest(), 16)
            vector[h % self.dimensies] += 0.5

        # Trigrams
        for i in range(len(woorden) - 2):
            trigram = f"{woorden[i]}_{woorden[i+1]}_{woorden[i+2]}"
            h = int(hashlib.sha256(trigram.encode()).hexdigest(), 16)
            vector[h % self.dimensies] += 0.25

        # L2 normalisatie
        norm = math.sqrt(sum(v**2 for v in vector))
        if norm > 0:
            vector = [v / norm for v in vector]

        return vector


def get_embedder(gebruik_voyage: bool = True) -> EmbeddingProvider:
    """Geeft de beste beschikbare embedding provider."""
    if gebruik_voyage and Config.has_voyage_key():
        try:
            return VoyageEmbeddings()
        except Exception as e:
            print(f"   [!] Voyage failed: {e}")
    return HashEmbeddings()

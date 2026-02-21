"""
Embedding providers voor RAG systemen.
Versie 2.0 - Met TF-IDF, caching en benchmarking.
"""

import logging
import math
import hashlib
import json
import threading
import time
from collections import Counter, OrderedDict
from pathlib import Path
from typing import List, Dict, Optional
from .config import Config

logger = logging.getLogger(__name__)


class EmbeddingProvider:
    """Basis klasse voor embedding providers."""
    dimensies: int = 0
    naam: str = "basis"

    def embed(self, teksten: list) -> list:
        """Embed meerdere teksten."""
        raise NotImplementedError

    def embed_query(self, query: str) -> list:
        """Embed een enkele query."""
        return self.embed([query])[0]


class VoyageEmbeddings(EmbeddingProvider):
    """Productie embeddings met Voyage AI."""

    naam = "voyage"

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

    naam = "hash"

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


class TFIDFEmbeddings(EmbeddingProvider):
    """
    TF-IDF gebaseerde embeddings.
    Goed voor keyword matching en document retrieval.
    """

    naam = "tfidf"

    def __init__(self, dimensies: int = 512, min_df: int = 1, max_df: float = 0.95):
        """
        Initialiseer TF-IDF embedder.

        Args:
            dimensies: Grootte van de output vector
            min_df: Minimum document frequentie
            max_df: Maximum document frequentie (fractie)
        """
        self.dimensies = dimensies
        self.min_df = min_df
        self.max_df = max_df

        # Vocabulary en IDF waarden
        self.vocabulary: Dict[str, int] = {}
        self.idf: Dict[str, float] = {}
        self.doc_count = 0

        print(f"   [OK] TF-IDF Embeddings ({dimensies}d)")

    def _tokenize(self, tekst: str) -> List[str]:
        """Tokenize tekst naar woorden."""
        tekst = tekst.lower()
        # Simpele tokenizatie
        woorden = []
        huidig = ""
        for char in tekst:
            if char.isalnum():
                huidig += char
            else:
                if len(huidig) > 2:
                    woorden.append(huidig)
                huidig = ""
        if len(huidig) > 2:
            woorden.append(huidig)
        return woorden

    def fit(self, documenten: List[str]):
        """
        Bouw vocabulary en bereken IDF waarden.

        Args:
            documenten: Lijst van teksten om te trainen
        """
        self.doc_count = len(documenten)
        doc_freq: Counter = Counter()

        # Tel document frequenties
        for doc in documenten:
            woorden = set(self._tokenize(doc))
            for woord in woorden:
                doc_freq[woord] += 1

        # Filter op min/max df
        max_docs = int(self.max_df * self.doc_count)

        # Bouw vocabulary (top N woorden op basis van frequentie)
        gefilterd = [
            (woord, freq) for woord, freq in doc_freq.items()
            if self.min_df <= freq <= max_docs
        ]
        gefilterd.sort(key=lambda x: -x[1])

        for idx, (woord, freq) in enumerate(gefilterd[:self.dimensies]):
            self.vocabulary[woord] = idx
            # IDF = log(N / df)
            self.idf[woord] = math.log(self.doc_count / freq)

        print(f"   [OK] TF-IDF getraind met {len(self.vocabulary)} termen")

    def embed(self, teksten: list) -> list:
        """Embed teksten met TF-IDF."""
        if not self.vocabulary:
            # Auto-fit als nog niet getraind
            self.fit(teksten)

        return [self._embed_one(t) for t in teksten]

    def _embed_one(self, tekst: str) -> list:
        """Bereken TF-IDF vector voor een tekst."""
        vector = [0.0] * self.dimensies

        woorden = self._tokenize(tekst)
        if not woorden:
            return vector

        # Tel term frequenties
        tf = Counter(woorden)
        max_tf = max(tf.values())

        # Bereken TF-IDF
        for woord, count in tf.items():
            if woord in self.vocabulary:
                idx = self.vocabulary[woord]
                # Genormaliseerde TF * IDF
                tfidf = (count / max_tf) * self.idf.get(woord, 0)
                vector[idx] = tfidf

        # L2 normalisatie
        norm = math.sqrt(sum(v**2 for v in vector))
        if norm > 0:
            vector = [v / norm for v in vector]

        return vector


# =============================================================================
# CACHING
# =============================================================================

class EmbeddingCache:
    """
    Cache voor embeddings om herberekeningen te voorkomen.
    """

    _SAVE_INTERVAL = 50  # auto-save every N writes

    def __init__(self, cache_bestand: Path = None, max_grootte: int = 10000):
        """
        Initialiseer cache.

        Args:
            cache_bestand: Pad naar cache bestand
            max_grootte: Maximum aantal gecachte embeddings
        """
        self.cache_bestand = cache_bestand or (
            Config.RAG_DATA_DIR / "embedding_cache.json"
        )
        self.max_grootte = max_grootte
        self.cache: OrderedDict[str, list] = OrderedDict()
        self.hits = 0
        self.misses = 0
        self._writes_since_save = 0

        self._laad()

    def _hash_tekst(self, tekst: str, provider: str) -> str:
        """Genereer hash voor tekst + provider."""
        content = f"{provider}:{tekst}"
        return hashlib.sha256(content.encode()).hexdigest()

    def _laad(self):
        """Laad cache van disk."""
        if self.cache_bestand.exists():
            try:
                with open(self.cache_bestand, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.cache = OrderedDict(data.get("cache", {}))
                    self.hits = data.get("hits", 0)
                    self.misses = data.get("misses", 0)
            except (json.JSONDecodeError, IOError):
                self.cache = OrderedDict()

    def _opslaan(self):
        """Sla cache op naar disk."""
        self.cache_bestand.parent.mkdir(parents=True, exist_ok=True)
        with open(self.cache_bestand, "w", encoding="utf-8") as f:
            json.dump({
                "cache": self.cache,
                "hits": self.hits,
                "misses": self.misses
            }, f)

    def get(self, tekst: str, provider: str) -> Optional[list]:
        """
        Haal embedding uit cache (LRU: verplaatst naar einde).

        Returns:
            Embedding of None als niet gecached
        """
        key = self._hash_tekst(tekst, provider)
        if key in self.cache:
            self.hits += 1
            self.cache.move_to_end(key)
            return self.cache[key]
        self.misses += 1
        return None

    def set(self, tekst: str, provider: str, embedding: list):
        """Voeg embedding toe aan cache."""
        key = self._hash_tekst(tekst, provider)

        # Move existing key to end (LRU) or evict oldest if full
        if key in self.cache:
            self.cache.move_to_end(key)
        elif len(self.cache) >= self.max_grootte:
            # Verwijder oudste 10% (least recently used)
            te_verwijderen = self.max_grootte // 10 or 1
            for _ in range(min(te_verwijderen, len(self.cache))):
                self.cache.popitem(last=False)

        self.cache[key] = embedding

        # Auto-save periodiek
        self._writes_since_save += 1
        if self._writes_since_save >= self._SAVE_INTERVAL:
            self._opslaan()
            self._writes_since_save = 0

    def opslaan(self):
        """Expliciet opslaan."""
        self._opslaan()

    def wis(self):
        """Wis de hele cache."""
        self.cache = OrderedDict()
        self.hits = 0
        self.misses = 0
        self._writes_since_save = 0
        self._opslaan()

    def statistieken(self) -> dict:
        """Retourneer cache statistieken."""
        totaal = self.hits + self.misses
        hit_rate = (self.hits / totaal * 100) if totaal > 0 else 0

        return {
            "grootte": len(self.cache),
            "max_grootte": self.max_grootte,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": f"{hit_rate:.1f}%"
        }


class CachedEmbeddingProvider(EmbeddingProvider):
    """Wrapper die caching toevoegt aan een embedding provider."""

    def __init__(self, provider: EmbeddingProvider, cache: EmbeddingCache = None):
        """
        Initialiseer gecachte provider.

        Args:
            provider: De onderliggende embedding provider
            cache: Optionele bestaande cache
        """
        self.provider = provider
        self.cache = cache or EmbeddingCache()
        self.dimensies = provider.dimensies
        self.naam = f"cached_{provider.naam}"

    def embed(self, teksten: list) -> list:
        """Embed teksten met caching."""
        resultaten = []
        niet_gecached = []
        niet_gecached_indices = []

        # Check cache
        for i, tekst in enumerate(teksten):
            cached = self.cache.get(tekst, self.provider.naam)
            if cached is not None:
                resultaten.append(cached)
            else:
                resultaten.append(None)  # Placeholder
                niet_gecached.append(tekst)
                niet_gecached_indices.append(i)

        # Bereken niet-gecachte embeddings
        if niet_gecached:
            nieuwe_embeddings = self.provider.embed(niet_gecached)

            for idx, embedding in zip(niet_gecached_indices, nieuwe_embeddings):
                resultaten[idx] = embedding
                self.cache.set(teksten[idx], self.provider.naam, embedding)

        return resultaten

    def embed_query(self, query: str) -> list:
        """Embed query met caching."""
        cached = self.cache.get(query, self.provider.naam)
        if cached is not None:
            return cached

        embedding = self.provider.embed_query(query)
        self.cache.set(query, self.provider.naam, embedding)
        return embedding

    def opslaan_cache(self):
        """Sla cache op."""
        self.cache.opslaan()


# =============================================================================
# CHROMADB ADAPTER
# =============================================================================


class VoyageChromaEmbedding:
    """ChromaDB-compatibele wrapper voor Voyage AI.

    Implementeert chromadb EmbeddingFunction protocol:
    __call__(input: Documents) -> Embeddings

    """

    def __init__(self):
        import voyageai
        self.client = voyageai.Client(
            api_key=Config.VOYAGE_API_KEY
        )
        self.model = Config.VOYAGE_MODEL

    def name(self):
        """ChromaDB protocol: unieke naam."""
        return "VoyageChromaEmbedding"

    def __call__(self, input):
        """ChromaDB embedding interface.

        Retry bij rate limits met korte backoff.
        """
        for poging in range(5):
            try:
                result = self.client.embed(
                    texts=input,
                    model=self.model,
                    input_type="document",
                )
                return result.embeddings
            except (ConnectionError, TimeoutError, OSError) as e:
                logger.warning("Voyage API netwerk fout (poging %d): %s", poging + 1, e)
                time.sleep(5 * (poging + 1))
            except Exception as e:
                naam = type(e).__name__
                if "RateLimit" in naam or "429" in str(e):
                    logger.warning("Voyage API rate limit (poging %d)", poging + 1)
                    time.sleep(5 * (poging + 1))
                else:
                    raise
        raise RuntimeError(
            "Voyage API rate limit na 5 pogingen"
        )


def get_chroma_embed_fn():
    """Geeft ChromaDB embedding functie.

    Voyage AI als key beschikbaar, anders
    SentenceTransformer fallback.
    """
    if Config.has_voyage_key():
        try:
            return VoyageChromaEmbedding()
        except Exception as e:
            logger.warning("VoyageChromaEmbedding mislukt, fallback naar SentenceTransformer: %s", e)
    # Fallback
    from chromadb.utils.embedding_functions import (
        SentenceTransformerEmbeddingFunction,
    )
    return SentenceTransformerEmbeddingFunction(
        model_name="sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
    )


# =============================================================================
# BENCHMARKING
# =============================================================================

class EmbeddingBenchmark:
    """Benchmark tool voor embedding providers."""

    def __init__(self):
        self.resultaten: List[dict] = []

    def benchmark_provider(self, provider: EmbeddingProvider, teksten: List[str],
                          naam: str = None) -> dict:
        """
        Benchmark een provider.

        Args:
            provider: Te benchmarken provider
            teksten: Lijst van teksten om te embedden
            naam: Optionele naam voor het resultaat

        Returns:
            Benchmark resultaten
        """
        naam = naam or provider.naam

        # Warmup
        if teksten:
            provider.embed([teksten[0]])

        # Timing
        start = time.perf_counter()
        embeddings = provider.embed(teksten)
        eind = time.perf_counter()

        totale_tijd = eind - start
        per_tekst = totale_tijd / len(teksten) if teksten else 0

        resultaat = {
            "naam": naam,
            "dimensies": provider.dimensies,
            "aantal_teksten": len(teksten),
            "totale_tijd_ms": round(totale_tijd * 1000, 2),
            "tijd_per_tekst_ms": round(per_tekst * 1000, 2),
            "teksten_per_seconde": round(len(teksten) / totale_tijd, 1) if totale_tijd > 0 else 0
        }

        self.resultaten.append(resultaat)
        return resultaat

    def vergelijk(self, providers: List[EmbeddingProvider], teksten: List[str]) -> str:
        """
        Vergelijk meerdere providers.

        Returns:
            Geformatteerde vergelijkingstabel
        """
        self.resultaten = []

        for provider in providers:
            self.benchmark_provider(provider, teksten)

        # Format als tabel
        lijnen = []
        lijnen.append("=" * 70)
        lijnen.append("EMBEDDING BENCHMARK RESULTATEN")
        lijnen.append("=" * 70)
        lijnen.append(f"Aantal teksten: {len(teksten)}")
        lijnen.append("-" * 70)
        lijnen.append(f"{'Provider':<20} {'Dim':>6} {'Totaal (ms)':>12} "
                     f"{'Per tekst':>12} {'Per sec':>10}")
        lijnen.append("-" * 70)

        for r in self.resultaten:
            lijnen.append(
                f"{r['naam']:<20} {r['dimensies']:>6} "
                f"{r['totale_tijd_ms']:>12.2f} {r['tijd_per_tekst_ms']:>12.2f} "
                f"{r['teksten_per_seconde']:>10.1f}"
            )

        lijnen.append("=" * 70)

        return "\n".join(lijnen)

    def similarity_test(self, provider: EmbeddingProvider,
                        tekst1: str, tekst2: str) -> float:
        """
        Test similarity tussen twee teksten.

        Returns:
            Cosine similarity score
        """
        emb1 = provider.embed_query(tekst1)
        emb2 = provider.embed_query(tekst2)

        # Cosine similarity
        dot = sum(a * b for a, b in zip(emb1, emb2))
        mag1 = math.sqrt(sum(a**2 for a in emb1))
        mag2 = math.sqrt(sum(b**2 for b in emb2))

        if mag1 == 0 or mag2 == 0:
            return 0.0
        return dot / (mag1 * mag2)


# =============================================================================
# FACTORY FUNCTIE
# =============================================================================

def get_embedder(gebruik_voyage: bool = True,
                 gebruik_cache: bool = True,
                 tfidf_fallback: bool = False) -> EmbeddingProvider:
    """
    Geeft de beste beschikbare embedding provider.

    Args:
        gebruik_voyage: Probeer Voyage AI te gebruiken
        gebruik_cache: Voeg caching toe
        tfidf_fallback: Gebruik TF-IDF als fallback (anders Hash)

    Returns:
        Embedding provider
    """
    provider = None

    if gebruik_voyage and Config.has_voyage_key():
        try:
            provider = VoyageEmbeddings()
        except Exception as e:
            print(f"   [!] Voyage failed: {e}")

    if provider is None:
        if tfidf_fallback:
            provider = TFIDFEmbeddings()
        else:
            provider = HashEmbeddings()

    if gebruik_cache:
        provider = CachedEmbeddingProvider(provider)

    return provider


def lijst_providers() -> List[str]:
    """Lijst van beschikbare provider namen."""
    providers = ["hash", "tfidf"]
    if Config.has_voyage_key():
        providers.insert(0, "voyage")
    return providers


# =============================================================================
# GPU-ACCELERATED EMBEDDING PROVIDER
# =============================================================================

try:
    from transformers import AutoTokenizer, AutoModel
    from transformers import logging as transformers_logging
    transformers_logging.set_verbosity_error()
    import torch
    from danny_toolkit.core.gpu import get_device
    _HAS_TORCH_GPU = True
except ImportError:
    _HAS_TORCH_GPU = False


class TorchGPUEmbeddings(EmbeddingProvider):
    """
    GPU-accelerated embedding provider using HuggingFace models.
    Returns CPU tensors so FAISS (CPU or GPU) can consume them.
    """

    naam = "torch_gpu"

    def __init__(self, model_name: str = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"):
        if not _HAS_TORCH_GPU:
            raise ImportError("TorchGPUEmbeddings vereist 'transformers' en 'torch'. Installeer met: pip install transformers torch")
        self.model_name = model_name
        self.device = get_device()
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModel.from_pretrained(model_name).to(self.device)
        self.model.eval()
        self.dimensies = self.model.config.hidden_size

    def _masked_mean_pool(self, last_hidden_state, attention_mask):
        """Mean pooling met attention mask (negeert padding tokens)."""
        mask = attention_mask.unsqueeze(-1).float()
        summed = (last_hidden_state * mask).sum(dim=1)
        counts = mask.sum(dim=1).clamp(min=1e-9)
        return summed / counts

    def _embed_batch(self, texts):
        """Embed een enkele batch teksten."""
        enc = self.tokenizer(
            texts,
            padding=True,
            truncation=True,
            return_tensors="pt"
        ).to(self.device)
        out = self.model(**enc)
        emb = self._masked_mean_pool(out.last_hidden_state, enc["attention_mask"])
        return emb.detach().cpu()

    def embed(self, texts, batch_size: int = 32):
        with torch.inference_mode():
            if len(texts) <= batch_size:
                return self._embed_batch(texts)

            all_emb = []
            for i in range(0, len(texts), batch_size):
                all_emb.append(self._embed_batch(texts[i:i + batch_size]))
            return torch.cat(all_emb, dim=0)


# =============================================================================
# SINGLETON FACTORY — TorchGPUEmbeddings
# =============================================================================

_torch_gpu_instance = None
_torch_gpu_lock = threading.Lock()


def get_torch_embedder(
    model_name: str = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
) -> "TorchGPUEmbeddings":
    """Singleton TorchGPUEmbeddings — laadt het model slechts één keer."""
    global _torch_gpu_instance
    if _torch_gpu_instance is None:
        with _torch_gpu_lock:
            if _torch_gpu_instance is None:
                _torch_gpu_instance = TorchGPUEmbeddings(model_name)
    return _torch_gpu_instance

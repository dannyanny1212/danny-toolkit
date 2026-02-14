# danny_toolkit/core/index_store.py — Persistent FAISS index + metadata
import json
import numpy as np
import faiss
from pathlib import Path

DEFAULT_STORE = Path.home() / ".danny-toolkit" / "index"


class IndexStore:
    """Persistent FAISS index with document metadata."""

    def __init__(self, store_dir: str = None):
        self.store_dir = Path(store_dir) if store_dir else DEFAULT_STORE
        self.store_dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.store_dir / "faiss.index"
        self.meta_path = self.store_dir / "metadata.json"
        self.vectors_path = self.store_dir / "vectors.npy"
        self.index = None
        self.metadata = []

    def build(self, vectors: np.ndarray, metadata: list[dict]):
        """Build and save a new index from vectors + metadata."""
        dim = vectors.shape[1]
        n = vectors.shape[0]

        # Use flat index for small datasets, IVF for larger
        if n < 256:
            self.index = faiss.IndexFlatL2(dim)
        else:
            nlist = min(n // 4, 1024)
            self.index = faiss.index_factory(dim, f"IVF{nlist},Flat", faiss.METRIC_L2)
            self.index.train(vectors)

        self.index.add(vectors)
        self.metadata = metadata
        self._vectors = vectors
        self._save()

    def append(self, vectors: np.ndarray, metadata: list[dict]):
        """Append vectors + metadata to the existing index, or create a new one."""
        if not self.exists():
            self.build(vectors, metadata)
            return

        self._load()
        old_vectors = np.load(self.vectors_path)
        all_vectors = np.vstack([old_vectors, vectors]).astype("float32")
        all_metadata = self.metadata + metadata

        self.index = None  # Reset zodat build() een nieuwe index maakt
        self.build(all_vectors, all_metadata)
        print(f"  Index uitgebreid: {all_vectors.shape[0]} chunks totaal")

    def search(self, query_vec: np.ndarray, k: int = 5) -> list[dict]:
        """Search the index and return results with metadata."""
        self._load()
        k = min(k, self.index.ntotal)
        D, I = self.index.search(query_vec, k)

        results = []
        for rank, idx in enumerate(I[0]):
            if idx < 0 or idx >= len(self.metadata):
                continue
            meta = self.metadata[idx]
            results.append({
                "rank": rank + 1,
                "text": meta["text"],
                "source": meta["source"],
                "chunk": meta["chunk"],
                "distance": float(D[0][rank]),
            })
        return results

    def _save(self):
        faiss.write_index(self.index, str(self.index_path))
        with open(self.meta_path, "w", encoding="utf-8") as f:
            json.dump(self.metadata, f, ensure_ascii=False)
        if hasattr(self, "_vectors"):
            np.save(self.vectors_path, self._vectors)
        print(f"  Index opgeslagen: {self.store_dir}")

    def _load(self):
        if self.index is not None:
            return
        if not self.index_path.exists():
            raise FileNotFoundError(
                "Geen index gevonden. Draai eerst: danny index <directory>"
            )
        self.index = faiss.read_index(str(self.index_path))
        with open(self.meta_path, "r", encoding="utf-8") as f:
            self.metadata = json.load(f)
        print(f"  Index geladen: {self.index.ntotal} chunks")

    def exists(self) -> bool:
        return self.index_path.exists() and self.meta_path.exists()

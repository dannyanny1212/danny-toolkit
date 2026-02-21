# danny_toolkit/core/index_store.py — Persistent FAISS index + metadata
from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    import numpy as np
    import faiss
    _HAS_FAISS = True
except ImportError:
    _HAS_FAISS = False

DEFAULT_STORE = Path.home() / ".danny-toolkit" / "index"

SCHEMA_VERSION = 1


class IndexStore:
    """Persistent FAISS index with document metadata."""

    def __init__(self, store_dir: str = None):
        if not _HAS_FAISS:
            raise ImportError("IndexStore vereist 'numpy' en 'faiss-cpu'. Installeer met: pip install numpy faiss-cpu")
        self.store_dir = Path(store_dir) if store_dir else DEFAULT_STORE
        self.store_dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.store_dir / "faiss.index"
        self.meta_path = self.store_dir / "metadata.json"
        self.vectors_path = self.store_dir / "vectors.npy"
        self.index = None
        self.metadata = []
        self._schema_version = SCHEMA_VERSION

    @staticmethod
    def _hash(text: str) -> str:
        """MD5-hash van chunk-tekst voor deduplicatie."""
        return hashlib.md5(text.encode()).hexdigest()

    def build(self, vectors: np.ndarray, metadata: list[dict]):
        """Build and save a new index from vectors + metadata."""
        # Zorg dat elke metadata entry een hash heeft
        for m in metadata:
            if "hash" not in m:
                m["hash"] = self._hash(m.get("text", ""))

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
        """Append vectors + metadata to the existing index, or create a new one.

        Deduplicatie via MD5-hash: chunks die al bestaan worden geskipt.
        """
        # Zorg dat nieuwe chunks een hash hebben
        for m in metadata:
            if "hash" not in m:
                m["hash"] = self._hash(m.get("text", ""))

        if not self.exists():
            self.build(vectors, metadata)
            return

        self._load()

        # Bestaande hashes ophalen
        existing_hashes = {m.get("hash") for m in self.metadata if "hash" in m}

        # Filter duplicaten
        new_indices = [
            i for i, m in enumerate(metadata)
            if m["hash"] not in existing_hashes
        ]
        n_skipped = len(metadata) - len(new_indices)

        if not new_indices:
            print(f"  {n_skipped} duplicaten geskipt, 0 nieuwe chunks")
            return

        new_vectors = vectors[new_indices]
        new_metadata = [metadata[i] for i in new_indices]

        old_vectors = np.load(self.vectors_path)
        all_vectors = np.vstack([old_vectors, new_vectors]).astype("float32")
        all_metadata = self.metadata + new_metadata

        self.index = None  # Reset zodat build() een nieuwe index maakt
        self.build(all_vectors, all_metadata)
        if n_skipped > 0:
            print(f"  {n_skipped} duplicaten geskipt, {len(new_indices)} nieuwe chunks")
        print(f"  Index uitgebreid: {all_vectors.shape[0]} chunks totaal")

    def search(self, query_vec: np.ndarray, k: int = 5) -> list[dict]:
        """Search the index and return results with metadata."""
        self._load()
        # Verhoog nprobe voor IVF indices zodat meer clusters doorzocht worden
        if hasattr(self.index, "nprobe"):
            self.index.nprobe = min(10, getattr(self.index, "nlist", 10))
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
                "hash": meta.get("hash", ""),
                "distance": float(D[0][rank]),
            })
        return results

    def _save(self):
        faiss.write_index(self.index, str(self.index_path))
        wrapper = {
            "schema_version": SCHEMA_VERSION,
            "chunks": self.metadata,
        }
        with open(self.meta_path, "w", encoding="utf-8") as f:
            json.dump(wrapper, f, ensure_ascii=False)
        if hasattr(self, "_vectors"):
            np.save(self.vectors_path, self._vectors)
        self._schema_version = SCHEMA_VERSION
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
            raw = json.load(f)
        # Backwards-compatible: plain list = schema v0, dict met schema_version = die versie
        if isinstance(raw, list):
            self.metadata = raw
            self._schema_version = 0
        elif isinstance(raw, dict) and "schema_version" in raw:
            self._schema_version = raw["schema_version"]
            self.metadata = raw.get("chunks", [])
        else:
            self.metadata = raw if isinstance(raw, list) else []
            self._schema_version = 0
        print(f"  Index geladen: {self.index.ntotal} chunks")

    def exists(self) -> bool:
        return self.index_path.exists() and self.meta_path.exists()

    def stats(self) -> dict:
        """Retourneer statistieken over de index."""
        self._load()

        sources = list({m.get("source", "") for m in self.metadata if m.get("source")})
        domains = []
        for src in sources:
            if src.startswith("http://") or src.startswith("https://"):
                try:
                    from urllib.parse import urlparse
                    domain = urlparse(src).netloc
                    if domain and domain not in domains:
                        domains.append(domain)
                except Exception as e:
                    logger.debug("URL parsing mislukt: %s", e)

        has_hashes = sum(1 for m in self.metadata if m.get("hash"))

        # Index type detectie
        index_type = "Flat"
        try:
            # IVF indices hebben een nlist attribuut via de quantizer
            if hasattr(self.index, "nlist"):
                index_type = "IVFFlat"
        except Exception as e:
            logger.debug("Index type detectie mislukt: %s", e)

        # Bestandsgroottes
        vectors_size_mb = 0.0
        if self.vectors_path.exists():
            vectors_size_mb = round(self.vectors_path.stat().st_size / (1024 * 1024), 2)

        metadata_size_mb = 0.0
        if self.meta_path.exists():
            metadata_size_mb = round(self.meta_path.stat().st_size / (1024 * 1024), 2)

        return {
            "total_chunks": len(self.metadata),
            "total_sources": len(sources),
            "sources": sorted(sources),
            "domains": sorted(domains),
            "has_hashes": has_hashes,
            "schema_version": self._schema_version,
            "index_type": index_type,
            "vectors_size_mb": vectors_size_mb,
            "metadata_size_mb": metadata_size_mb,
        }

    def verify(self) -> dict:
        """Verifieer consistentie van de index."""
        self._load()

        checks = []

        # 1. vectors.npy rijen == len(metadata)
        vectors_count = 0
        if self.vectors_path.exists():
            vecs = np.load(self.vectors_path)
            vectors_count = vecs.shape[0]

        meta_count = len(self.metadata)
        checks.append({
            "name": "vectors_count == metadata_count",
            "passed": vectors_count == meta_count,
            "detail": f"vectors={vectors_count}, metadata={meta_count}",
        })

        # 2. vectors.npy rijen == index.ntotal
        faiss_total = self.index.ntotal if self.index else 0
        checks.append({
            "name": "vectors_count == faiss_ntotal",
            "passed": vectors_count == faiss_total,
            "detail": f"vectors={vectors_count}, faiss={faiss_total}",
        })

        # 3. Missing hashes (legacy entries)
        missing_hashes = sum(1 for m in self.metadata if not m.get("hash"))
        checks.append({
            "name": "missing_hashes",
            "passed": missing_hashes == 0,
            "detail": f"{missing_hashes} chunks zonder hash",
        })

        # 4. Duplicate hashes
        from collections import Counter
        hash_counts = Counter(m.get("hash") for m in self.metadata if m.get("hash"))
        duplicate_hashes = sum(1 for h, c in hash_counts.items() if c > 1)
        checks.append({
            "name": "duplicate_hashes",
            "passed": duplicate_hashes == 0,
            "detail": f"{duplicate_hashes} hashes komen >1x voor",
        })

        # 5. Empty texts
        empty_texts = sum(1 for m in self.metadata if not m.get("text", "").strip())
        checks.append({
            "name": "empty_texts",
            "passed": empty_texts == 0,
            "detail": f"{empty_texts} chunks met lege tekst",
        })

        # 6. Missing sources
        missing_sources = sum(1 for m in self.metadata if not m.get("source"))
        checks.append({
            "name": "missing_sources",
            "passed": missing_sources == 0,
            "detail": f"{missing_sources} chunks zonder source",
        })

        # 7. Schema versie
        checks.append({
            "name": "schema_version",
            "passed": self._schema_version >= SCHEMA_VERSION,
            "detail": f"v{self._schema_version} (huidig: v{SCHEMA_VERSION})",
        })

        ok = all(c["passed"] for c in checks)
        return {"ok": ok, "checks": checks}

    def upgrade(self) -> dict:
        """Unified diagnose + reparatie pipeline.

        Detecteert automatisch wat er mis is en fixt alles in één pass:
        - Schema migratie (v0 → v1)
        - Backfill ontbrekende hashes
        - Verwijder duplicaten
        - Verwijder lege chunks
        - Rebuild FAISS index
        """
        self._load()
        vectors = np.load(self.vectors_path)

        old_schema = self._schema_version
        original_count = len(self.metadata)

        # 1. Backfill ontbrekende hashes
        hashes_added = 0
        for m in self.metadata:
            if not m.get("hash"):
                m["hash"] = self._hash(m.get("text", ""))
                hashes_added += 1

        # 2. Verwijder lege chunks
        non_empty = [
            (i, m) for i, m in enumerate(self.metadata)
            if m.get("text", "").strip()
        ]
        empty_removed = original_count - len(non_empty)
        if empty_removed > 0:
            keep_indices = [i for i, _ in non_empty]
            vectors = vectors[keep_indices].astype("float32")
            self.metadata = [m for _, m in non_empty]

        # 3. Dedup: houd eerste voorkomen, verwijder latere duplicaten
        seen_hashes = set()
        dedup_indices = []
        for i, m in enumerate(self.metadata):
            h = m["hash"]
            if h not in seen_hashes:
                seen_hashes.add(h)
                dedup_indices.append(i)

        duplicates_removed = len(self.metadata) - len(dedup_indices)
        if duplicates_removed > 0:
            vectors = vectors[dedup_indices].astype("float32")
            self.metadata = [self.metadata[i] for i in dedup_indices]

        # 4. Rebuild FAISS index + save (save schrijft schema v1 wrapper)
        self.index = None
        self.build(vectors, self.metadata)

        return {
            "old_schema": old_schema,
            "new_schema": SCHEMA_VERSION,
            "original_count": original_count,
            "final_count": len(self.metadata),
            "hashes_added": hashes_added,
            "duplicates_removed": duplicates_removed,
            "empty_removed": empty_removed,
            "rebuilt": True,
        }

    def repair(self) -> dict:
        """Repareer de index (backwards compat — delegeert naar upgrade()).

        Retourneert hetzelfde formaat als voorheen voor backwards compatibiliteit.
        """
        result = self.upgrade()
        return {
            "original_count": result["original_count"],
            "final_count": result["final_count"],
            "hashes_added": result["hashes_added"],
            "duplicates_removed": result["duplicates_removed"],
        }

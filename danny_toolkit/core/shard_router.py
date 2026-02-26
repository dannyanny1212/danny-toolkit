"""
ShardRouter — Matrix Sharding voor ChromaDB collecties.

Verdeelt documenten over drie gespecialiseerde shards:
- danny_code: broncode (.py, .js, .ts, .java, .go, .rs, .c, .cpp, .h)
- danny_docs: documentatie (.txt, .md, .html, .pdf)
- danny_data: data/config (.json, .csv, .yaml, .yml, .toml, .xml, .cfg, .ini, .log)

Singleton via get_shard_router().
Backward compatible: Config.SHARD_ENABLED=False (default) = legacy danny_knowledge.
"""

import logging
import os
import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

from danny_toolkit.core.config import Config

# ─── Constanten ──────────────────────────────────────

SHARD_CODE = "danny_code"
SHARD_DOCS = "danny_docs"
SHARD_DATA = "danny_data"
LEGACY_COLLECTION = "danny_knowledge"

ALL_SHARDS = [SHARD_CODE, SHARD_DOCS, SHARD_DATA]

EXTENSIE_ROUTING: Dict[str, str] = {
    # Code
    ".py": SHARD_CODE,
    ".js": SHARD_CODE,
    ".ts": SHARD_CODE,
    ".java": SHARD_CODE,
    ".go": SHARD_CODE,
    ".rs": SHARD_CODE,
    ".c": SHARD_CODE,
    ".cpp": SHARD_CODE,
    ".h": SHARD_CODE,
    # Docs
    ".txt": SHARD_DOCS,
    ".md": SHARD_DOCS,
    ".html": SHARD_DOCS,
    ".pdf": SHARD_DOCS,
    # Data
    ".json": SHARD_DATA,
    ".csv": SHARD_DATA,
    ".yaml": SHARD_DATA,
    ".yml": SHARD_DATA,
    ".toml": SHARD_DATA,
    ".xml": SHARD_DATA,
    ".cfg": SHARD_DATA,
    ".ini": SHARD_DATA,
    ".log": SHARD_DATA,
}


@dataclass
class ShardStatistiek:
    """Statistieken voor één shard."""
    naam: str
    aantal_chunks: int = 0
    extensies: List[str] = field(default_factory=list)


# ═══════════════════════════════════════════════════════
# ShardRouter
# ═══════════════════════════════════════════════════════

class ShardRouter:
    """Matrix shard router voor ChromaDB collecties.

    Verdeelt documenten over code/docs/data shards
    op basis van bestandsextensie. Fan-out queries
    over meerdere shards met merge op distance.
    """

    def __init__(self):
        """Initializes a new instance of the class.

 Attributes:
  _collections (Dict[str, Any]): A dictionary to store collections.
  _client: The client object, initially set to None.
  _embed_fn: The embedding function, initially set to None.
  _lock (threading.Lock): A lock object for thread synchronization."""
        self._collections: Dict[str, Any] = {}
        self._client = None
        self._embed_fn = None
        self._lock = threading.Lock()

    def _ensure_client(self):
        """Lazy init ChromaDB client + embedding functie."""
        if self._client is not None:
            return True
        # Skip in test mode
        if os.environ.get("DANNY_TEST_MODE") == "1":
            return False
        try:
            import chromadb
            from danny_toolkit.core.embeddings import (
                get_chroma_embed_fn,
            )
            from pathlib import Path
            import sys
            import io as _io

            chroma_dir = str(Config.RAG_DATA_DIR / "chromadb")
            self._client = chromadb.PersistentClient(
                path=chroma_dir
            )

            # Suppress model load spam
            _old_out = sys.stdout
            _old_err = sys.stderr
            sys.stdout = _io.StringIO()
            sys.stderr = _io.StringIO()
            try:
                self._embed_fn = get_chroma_embed_fn()
            finally:
                sys.stdout = _old_out
                sys.stderr = _old_err

            return True
        except Exception as e:
            logger.debug("ShardRouter ChromaDB init fout: %s", e)
            return False

    def _get_collection(self, shard_naam: str):
        """Haal of maak een shard collectie."""
        if shard_naam in self._collections:
            return self._collections[shard_naam]

        if not self._ensure_client():
            return None

        try:
            coll = self._client.get_or_create_collection(
                name=shard_naam,
                embedding_function=self._embed_fn,
                metadata={
                    "description": f"Danny Toolkit Shard: {shard_naam}",
                },
            )
            self._collections[shard_naam] = coll
            return coll
        except Exception as e:
            logger.debug("ShardRouter collectie fout %s: %s", shard_naam, e)
            return None

    # ─── Routing ─────────────────────────────────────

    def route_document(self, metadata: Dict[str, Any]) -> str:
        """Bepaal doelshard op basis van metadata extensie.

        Args:
            metadata: Document metadata met 'extensie' veld.

        Returns:
            Shard naam (danny_code/danny_docs/danny_data).
        """
        try:
            extensie = metadata.get("extensie", "")
            return EXTENSIE_ROUTING.get(extensie, SHARD_DOCS)
        except Exception as e:
            logger.debug("ShardRouter route_document fout: %s", e)
            return SHARD_DOCS

    # ─── Ingest ──────────────────────────────────────

    def ingest(
        self,
        documenten: List[Dict[str, Any]],
        embed_fn: Optional[Callable] = None,
    ) -> Dict[str, int]:
        """Groepeer documenten per shard en batch-upsert.

        Args:
            documenten: Lijst van dicts met 'id', 'tekst', 'metadata'.
            embed_fn: Optionele embedding functie (anders intern).

        Returns:
            Dict van shard naam -> aantal ingested chunks.
        """
        if not getattr(Config, "SHARD_ENABLED", False):
            return {}

        # Groepeer per shard
        per_shard: Dict[str, List[Dict]] = {s: [] for s in ALL_SHARDS}
        for doc in documenten:
            shard = self.route_document(doc.get("metadata", {}))
            per_shard[shard].append(doc)

        resultaat: Dict[str, int] = {}

        for shard_naam, docs in per_shard.items():
            if not docs:
                resultaat[shard_naam] = 0
                continue

            coll = self._get_collection(shard_naam)
            if coll is None:
                resultaat[shard_naam] = 0
                continue

            try:
                ids = [d["id"] for d in docs]
                documents = [d["tekst"] for d in docs]
                metadatas = [d.get("metadata", {}) for d in docs]

                coll.upsert(
                    ids=ids,
                    documents=documents,
                    metadatas=metadatas,
                )
                resultaat[shard_naam] = len(ids)
            except Exception as e:
                logger.debug("ShardRouter ingest fout %s: %s", shard_naam, e)
                resultaat[shard_naam] = 0

        # NeuralBus event
        try:
            from danny_toolkit.core.neural_bus import (
                get_bus, EventTypes,
            )
            bus = get_bus()
            bus.publish(
                EventTypes.SHARD_QUERY_ROUTED,
                {"actie": "ingest", "resultaat": resultaat},
                bron="ShardRouter",
            )
        except Exception as e:
            logger.debug("ShardRouter NeuralBus fout: %s", e)

        return resultaat

    # ─── Zoeken ──────────────────────────────────────

    def zoek(
        self,
        query: str,
        top_k: int = 5,
        shards: Optional[List[str]] = None,
        min_score: float = 0.0,
    ) -> List[Dict[str, Any]]:
        """Fan-out zoeken over meerdere shards, merge op distance.

        Args:
            query: Zoekquery tekst.
            top_k: Aantal resultaten.
            shards: Welke shards doorzoeken (None = alle).
            min_score: Minimum score drempel.

        Returns:
            Gesorteerde lijst van resultaat-dicts.
        """
        if not getattr(Config, "SHARD_ENABLED", False):
            return []

        zoek_shards = shards or ALL_SHARDS
        alle_resultaten = []

        for shard_naam in zoek_shards:
            coll = self._get_collection(shard_naam)
            if coll is None:
                continue
            try:
                count = coll.count()
                if count == 0:
                    continue
                n = min(top_k, count)
                results = coll.query(
                    query_texts=[query],
                    n_results=n,
                    include=["documents", "metadatas", "distances"],
                )
                docs = results["documents"][0]
                metas = results["metadatas"][0]
                dists = results["distances"][0]

                for doc, meta, dist in zip(docs, metas, dists):
                    if min_score and dist > min_score:
                        continue
                    alle_resultaten.append({
                        "tekst": doc,
                        "metadata": meta,
                        "distance": dist,
                        "shard": shard_naam,
                    })
            except Exception as e:
                logger.debug("ShardRouter zoek fout %s: %s", shard_naam, e)

        # Sorteer op distance (lager = beter)
        alle_resultaten.sort(key=lambda x: x["distance"])

        top = alle_resultaten[:top_k]

        # Phase 37: track fragment access
        if top:
            try:
                from danny_toolkit.core.self_pruning import (
                    get_self_pruning,
                )
                sp = get_self_pruning()
                per_shard: Dict[str, List[str]] = {}
                for r in top:
                    s = r.get("shard", "")
                    fid = r.get("metadata", {}).get("id", "")
                    if s and fid:
                        per_shard.setdefault(s, []).append(fid)
                for s, ids in per_shard.items():
                    sp.registreer_toegang(ids, s)
            except Exception as e:
                logger.debug("ShardRouter SelfPruning toegang: %s", e)

        return top

    # ─── Migratie ────────────────────────────────────

    def migreer(self, batch_size: int = 500) -> Dict[str, int]:
        """Eenmalige migratie vanuit legacy danny_knowledge.

        Leest alle documenten uit danny_knowledge en
        distribueert ze over de juiste shards.

        Args:
            batch_size: Aantal documenten per batch.

        Returns:
            Dict van shard naam -> aantal gemigreerde chunks.
        """
        if not self._ensure_client():
            return {}

        try:
            legacy = self._client.get_collection(
                name=LEGACY_COLLECTION,
                embedding_function=self._embed_fn,
            )
        except Exception as e:
            logger.debug("ShardRouter legacy collectie niet gevonden: %s", e)
            return {}

        totaal = legacy.count()
        if totaal == 0:
            return {}

        resultaat: Dict[str, int] = {s: 0 for s in ALL_SHARDS}
        offset = 0

        while offset < totaal:
            try:
                batch = legacy.get(
                    limit=batch_size,
                    offset=offset,
                    include=["documents", "metadatas"],
                )

                ids = batch["ids"]
                docs = batch["documents"]
                metas = batch["metadatas"]

                if not ids:
                    break

                # Groepeer per shard
                per_shard: Dict[str, tuple] = {
                    s: ([], [], []) for s in ALL_SHARDS
                }
                for id_, doc, meta in zip(ids, docs, metas):
                    shard = self.route_document(meta or {})
                    s_ids, s_docs, s_metas = per_shard[shard]
                    s_ids.append(id_)
                    s_docs.append(doc)
                    s_metas.append(meta or {})

                # Upsert per shard
                for shard_naam, (s_ids, s_docs, s_metas) in per_shard.items():
                    if not s_ids:
                        continue
                    coll = self._get_collection(shard_naam)
                    if coll is None:
                        continue
                    coll.upsert(
                        ids=s_ids,
                        documents=s_docs,
                        metadatas=s_metas,
                    )
                    resultaat[shard_naam] += len(s_ids)

                offset += len(ids)
            except Exception as e:
                logger.debug("ShardRouter migratie batch fout: %s", e)
                break

        # NeuralBus event
        try:
            from danny_toolkit.core.neural_bus import (
                get_bus, EventTypes,
            )
            bus = get_bus()
            bus.publish(
                EventTypes.SHARD_MIGRATION_COMPLETE,
                {"resultaat": resultaat, "totaal": totaal},
                bron="ShardRouter",
            )
        except Exception as e:
            logger.debug("ShardRouter NeuralBus migratie event fout: %s", e)

        return resultaat

    # ─── Statistieken ────────────────────────────────

    def statistieken(self) -> List[ShardStatistiek]:
        """Haal statistieken op per shard.

        Returns:
            Lijst van ShardStatistiek per shard.
        """
        stats = []
        for shard_naam in ALL_SHARDS:
            coll = self._get_collection(shard_naam)
            if coll is None:
                stats.append(ShardStatistiek(naam=shard_naam))
                continue
            try:
                count = coll.count()
                stats.append(ShardStatistiek(
                    naam=shard_naam,
                    aantal_chunks=count,
                ))
            except Exception as e:
                logger.debug("ShardRouter stats fout %s: %s", shard_naam, e)
                stats.append(ShardStatistiek(naam=shard_naam))
        return stats


# ─── Singleton ───────────────────────────────────────

_router_instance: Optional[ShardRouter] = None
_router_lock = threading.Lock()


def get_shard_router() -> ShardRouter:
    """Verkrijg de singleton ShardRouter instantie."""
    global _router_instance
    if _router_instance is None:
        with _router_lock:
            if _router_instance is None:
                _router_instance = ShardRouter()
    return _router_instance

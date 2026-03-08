"""
SelfPruning — Aggressive Vector Store Maintenance.

Houdt de ChromaDB vector matrix compact via drie mechanismen:
1. Entropy Threshold — fragmenten ver van actieve clusters flaggen
2. Recency Decay — ongebruikte fragmenten archiveren naar cold_storage
3. Redundancy Check — semantische duplicaten vernietigen (oudste sterft)

AccessTracker vult de ontbrekende observability gap: ChromaDB trackt
geen access patterns. SQLite-backed met WAL mode.

Gebruik:
    from danny_toolkit.core.self_pruning import get_self_pruning

    pruner = get_self_pruning()
    pruner.registreer_toegang(["chunk_1", "chunk_2"], "danny_docs")
    resultaat = pruner.prune()
"""

from __future__ import annotations

import logging
import math
import os
import sqlite3
import threading
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from danny_toolkit.core.config import Config

logger = logging.getLogger(__name__)

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

try:
    import chromadb
    HAS_CHROMADB = True
except ImportError:
    HAS_CHROMADB = False

try:
    import danny_toolkit.core.embeddings
    HAS_EMBEDDINGS = True
except ImportError:
    HAS_EMBEDDINGS = False

try:
    import danny_toolkit.core.memory_interface
    HAS_MEMORY_INTERFACE = True
except ImportError:
    HAS_MEMORY_INTERFACE = False

try:
    import danny_toolkit.core.neural_bus
    HAS_NEURAL_BUS = True
except ImportError:
    HAS_NEURAL_BUS = False

try:
    import danny_toolkit.core.shard_router
    HAS_SHARD_ROUTER = True
except ImportError:
    HAS_SHARD_ROUTER = False



# ═══════════════════════════════════════════════════════════
# AccessTracker — SQLite-backed fragment observability
# ═══════════════════════════════════════════════════════════

class AccessTracker:
    """Trackt access patterns voor ChromaDB fragmenten.

    Vult de ontbrekende observability gap: ChromaDB heeft geen
    timestamp/access metadata. SQLite WAL mode, thread-safe.
    """

    def __init__(self, db_path: Optional[str] = None) -> None:
        """Initializes the object with a database path.

 Args:
  db_path: Optional path to the database file. If not provided, a default path will be used.

 Returns:
  None"""
        self._db_path = db_path or str(Config.DATA_DIR / "self_pruning.db")
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self) -> None:
        """Maak database en tabel aan."""
        try:
            os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
            conn = sqlite3.connect(self._db_path, timeout=Config.SQLITE_CONNECT_TIMEOUT)
            Config.apply_sqlite_perf(conn)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS fragment_access (
                    fragment_id TEXT NOT NULL,
                    shard TEXT NOT NULL,
                    last_accessed TEXT NOT NULL,
                    access_count INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (fragment_id, shard)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_fa_last_accessed
                ON fragment_access (last_accessed)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_fa_shard
                ON fragment_access (shard)
            """)
            conn.commit()
            conn.close()
        except Exception as e:
            logger.debug("AccessTracker DB init fout: %s", e)

    def _connect(self) -> sqlite3.Connection:
        """Connect."""
        conn = sqlite3.connect(self._db_path, timeout=Config.SQLITE_CONNECT_TIMEOUT)
        Config.apply_sqlite_perf(conn)
        conn.row_factory = sqlite3.Row
        return conn

    def registreer_toegang(self, fragment_ids: List[str], shard: str) -> None:
        """Registreer dat fragmenten zijn geraadpleegd.

        UPSERT: bestaande rijen krijgen updated last_accessed en
        access_count+1. Nieuwe rijen worden aangemaakt.
        """
        if not fragment_ids:
            return
        nu = datetime.now().isoformat()
        with self._lock:
            try:
                conn = self._connect()
                for fid in fragment_ids:
                    conn.execute("""
                        INSERT INTO fragment_access
                            (fragment_id, shard, last_accessed, access_count, created_at)
                        VALUES (?, ?, ?, 1, ?)
                        ON CONFLICT(fragment_id, shard) DO UPDATE SET
                            last_accessed = ?,
                            access_count = access_count + 1
                    """, (fid, shard, nu, nu, nu))
                conn.commit()
                conn.close()
            except Exception as e:
                logger.debug("AccessTracker registreer_toegang fout: %s", e)

    def registreer_creatie(self, fragment_ids: List[str], shard: str) -> None:
        """Registreer nieuw aangemaakte fragmenten.

        Stelt access_count=0 en last_accessed=now. Geeft een
        grace period van RECENCY_DECAY_DAYS voordat cold migration.
        """
        if not fragment_ids:
            return
        nu = datetime.now().isoformat()
        with self._lock:
            try:
                conn = self._connect()
                for fid in fragment_ids:
                    conn.execute("""
                        INSERT INTO fragment_access
                            (fragment_id, shard, last_accessed, access_count, created_at)
                        VALUES (?, ?, ?, 0, ?)
                        ON CONFLICT(fragment_id, shard) DO UPDATE SET
                            last_accessed = ?,
                            access_count = access_count
                    """, (fid, shard, nu, nu, nu))
                conn.commit()
                conn.close()
            except Exception as e:
                logger.debug("AccessTracker registreer_creatie fout: %s", e)

    def haal_stale_fragmenten(self, dagen: int = 14) -> List[dict]:
        """Haal fragmenten op die langer dan `dagen` niet zijn geraadpleegd.

        Returns:
            Lijst van dicts met fragment_id, shard, last_accessed, access_count.
        """
        grens = (datetime.now() - timedelta(days=dagen)).isoformat()
        with self._lock:
            try:
                conn = self._connect()
                cursor = conn.execute("""
                    SELECT fragment_id, shard, last_accessed, access_count
                    FROM fragment_access
                    WHERE last_accessed < ? AND shard != ?
                """, (grens, Config.COLD_STORAGE_COLLECTION))
                rijen = [dict(r) for r in cursor.fetchall()]
                conn.close()
                return rijen
            except Exception as e:
                logger.debug("AccessTracker haal_stale fout: %s", e)
                return []

    def haal_actieve_fragmenten(self, dagen: int = 14) -> List[str]:
        """Haal fragment IDs op die recent zijn geraadpleegd.

        Returns:
            Lijst van fragment_id strings.
        """
        grens = (datetime.now() - timedelta(days=dagen)).isoformat()
        with self._lock:
            try:
                conn = self._connect()
                cursor = conn.execute("""
                    SELECT fragment_id FROM fragment_access
                    WHERE last_accessed >= ? AND shard != ?
                """, (grens, Config.COLD_STORAGE_COLLECTION))
                ids = [r["fragment_id"] for r in cursor.fetchall()]
                conn.close()
                return ids
            except Exception as e:
                logger.debug("AccessTracker haal_actieve fout: %s", e)
                return []

    def update_shard(self, fragment_id: str, oud_shard: str, nieuw_shard: str) -> None:
        """Update de shard van een fragment (na cold migratie)."""
        nu = datetime.now().isoformat()
        with self._lock:
            try:
                conn = self._connect()
                conn.execute("""
                    UPDATE fragment_access
                    SET shard = ?, last_accessed = ?
                    WHERE fragment_id = ? AND shard = ?
                """, (nieuw_shard, nu, fragment_id, oud_shard))
                conn.commit()
                conn.close()
            except Exception as e:
                logger.debug("AccessTracker update_shard fout: %s", e)

    def verwijder(self, fragment_ids: List[str], shard: str) -> None:
        """Verwijder fragmenten uit de tracker (na destructie)."""
        if not fragment_ids:
            return
        with self._lock:
            try:
                conn = self._connect()
                placeholders = ",".join("?" * len(fragment_ids))
                conn.execute(f"""
                    DELETE FROM fragment_access
                    WHERE fragment_id IN ({placeholders}) AND shard = ?
                """, (*fragment_ids, shard))
                conn.commit()
                conn.close()
            except Exception as e:
                logger.debug("AccessTracker verwijder fout: %s", e)

    def totaal_gevolgd(self) -> int:
        """Totaal aantal gevolgde fragmenten."""
        with self._lock:
            try:
                conn = self._connect()
                cursor = conn.execute(
                    "SELECT COUNT(*) AS c FROM fragment_access"
                )
                count = cursor.fetchone()["c"]
                conn.close()
                return count
            except Exception as e:
                logger.debug("AccessTracker totaal fout: %s", e)
                return 0


# ═══════════════════════════════════════════════════════════
# EntropieScanner — Low-value fragment detection
# ═══════════════════════════════════════════════════════════

class EntropieScanner:
    """Detecteert fragmenten die ver van actieve clusters liggen.

    Berekent een centroid van actieve embeddings en flagged
    fragmenten met cosine distance > drempel.
    """

    def __init__(self, drempel: float = 0.85) -> None:
        """Init  ."""
        self.drempel = drempel

    @staticmethod
    def _cosine_distance(a: List[float], b: List[float]) -> float:
        """Bereken cosine distance tussen twee vectoren.

        Pure Python fallback als numpy niet beschikbaar is.
        Returns: 1 - cosine_similarity (0 = identiek, 2 = tegengesteld).
        """
        if HAS_NUMPY:
            va = np.array(a, dtype=np.float32)
            vb = np.array(b, dtype=np.float32)
            norm_a = np.linalg.norm(va)
            norm_b = np.linalg.norm(vb)
            if norm_a == 0 or norm_b == 0:
                return 1.0
            return float(1.0 - np.dot(va, vb) / (norm_a * norm_b))
        else:
            dot = sum(x * y for x, y in zip(a, b))
            norm_a = math.sqrt(sum(x * x for x in a))
            norm_b = math.sqrt(sum(x * x for x in b))
            if norm_a == 0 or norm_b == 0:
                return 1.0
            return 1.0 - dot / (norm_a * norm_b)

    @staticmethod
    def _bereken_centroid(embeddings: List[List[float]]) -> Optional[List[float]]:
        """Bereken L2-genormaliseerde centroid van embeddings."""
        if not embeddings:
            return None
        if HAS_NUMPY:
            matrix = np.array(embeddings, dtype=np.float32)
            centroid = matrix.mean(axis=0)
            norm = np.linalg.norm(centroid)
            if norm > 0:
                centroid = centroid / norm
            return centroid.tolist()
        else:
            dim = len(embeddings[0])
            centroid = [0.0] * dim
            for emb in embeddings:
                for i in range(dim):
                    centroid[i] += emb[i]
            n = len(embeddings)
            centroid = [c / n for c in centroid]
            norm = math.sqrt(sum(c * c for c in centroid))
            if norm > 0:
                centroid = [c / norm for c in centroid]
            return centroid

    def scan(
        self,
        shard: str,
        actieve_ids: List[str],
        alle_ids: List[str],
        collection: Any,
    ) -> List[str]:
        """Scan een shard voor low-entropy fragmenten.

        Args:
            shard: Naam van de shard.
            actieve_ids: IDs van recent geraadpleegde fragmenten.
            alle_ids: Alle IDs in de shard.
            collection: ChromaDB Collection object.

        Returns:
            Lijst van geflaggde fragment IDs.
        """
        if len(alle_ids) < 10:
            return []

        # Bepaal niet-actieve IDs
        actieve_set = set(actieve_ids)
        niet_actief = [fid for fid in alle_ids if fid not in actieve_set]
        if not niet_actief:
            return []

        # Haal actieve embeddings voor centroid
        actieve_in_shard = [fid for fid in actieve_ids if fid in set(alle_ids)]
        if not actieve_in_shard:
            return []

        try:
            actieve_data = collection.get(
                ids=actieve_in_shard[:500],
                include=["embeddings"],
            )
            actieve_embs = actieve_data.get("embeddings", [])
            if not actieve_embs:
                return []
        except Exception as e:
            logger.debug("EntropieScanner actieve embeddings fout %s: %s", shard, e)
            return []

        centroid = self._bereken_centroid(actieve_embs)
        if not centroid:
            return []

        # Batch check niet-actieve fragmenten
        geflagd = []
        batch_size = 100
        for i in range(0, len(niet_actief), batch_size):
            batch_ids = niet_actief[i:i + batch_size]
            try:
                batch_data = collection.get(
                    ids=batch_ids,
                    include=["embeddings"],
                )
                batch_embs = batch_data.get("embeddings", [])
                batch_returned_ids = batch_data.get("ids", [])
                for fid, emb in zip(batch_returned_ids, batch_embs):
                    if emb:
                        dist = self._cosine_distance(emb, centroid)
                        if dist > self.drempel:
                            geflagd.append(fid)
            except Exception as e:
                logger.debug("EntropieScanner batch fout %s: %s", shard, e)

        return geflagd


# ═══════════════════════════════════════════════════════════
# RedundantieDetector — Semantic dedup (Ouroboros)
# ═══════════════════════════════════════════════════════════

class RedundantieDetector:
    """Detecteert semantische duplicaten in een shard.

    Paren met cosine similarity > drempel worden gedetecteerd.
    Het oudste fragment (op basis van AccessTracker created_at)
    wordt aangemerkt voor vernietiging.
    """

    def __init__(self, drempel: float = 0.90) -> None:
        """Init  ."""
        self.drempel = drempel

    def detecteer(
        self,
        shard: str,
        collection: Any,
        tracker: AccessTracker,
        batch_size: int = 100,
    ) -> List[Tuple[str, str, float]]:
        """Detecteer redundante paren in een shard.

        Args:
            shard: Naam van de shard.
            collection: ChromaDB Collection object.
            tracker: AccessTracker voor created_at lookup.
            batch_size: Aantal fragmenten per batch.

        Returns:
            Lijst van (te_verwijderen_id, duplicaat_van_id, similarity).
        """
        try:
            count = collection.count()
            if count < 2:
                return []
        except Exception as e:
            logger.debug("RedundantieDetector count fout %s: %s", shard, e)
            return []

        # Haal alle fragmenten in batches
        alle_ids: List[str] = []
        alle_embs: List[List[float]] = []

        offset = 0
        while offset < count:
            try:
                batch = collection.get(
                    limit=batch_size,
                    offset=offset,
                    include=["embeddings"],
                )
                ids = batch.get("ids", [])
                embs = batch.get("embeddings", [])
                if not ids:
                    break
                alle_ids.extend(ids)
                alle_embs.extend(embs)
                offset += len(ids)
            except Exception as e:
                logger.debug("RedundantieDetector batch fout %s: %s", shard, e)
                break

        if len(alle_ids) < 2:
            return []

        # Bereken similarity matrix
        paren = self._vind_duplicaten(alle_ids, alle_embs)

        if not paren:
            return []

        # Bepaal welke te vernietigen (oudste van elk paar)
        resultaat = []
        vernietigd_set: set = set()

        for id_a, id_b, sim in paren:
            if id_a in vernietigd_set or id_b in vernietigd_set:
                continue
            # Oudste wordt vernietigd
            oudste = self._bepaal_oudste(id_a, id_b, tracker, shard)
            behouden = id_b if oudste == id_a else id_a
            resultaat.append((oudste, behouden, sim))
            vernietigd_set.add(oudste)

        return resultaat

    def _vind_duplicaten(
        self,
        ids: List[str],
        embeddings: List[List[float]],
    ) -> List[Tuple[str, str, float]]:
        """Vind paren met similarity > drempel."""
        paren = []

        if HAS_NUMPY and len(ids) <= 2000:
            # Volledige matrix — O(n²) maar snel via numpy
            matrix = np.array(embeddings, dtype=np.float32)
            norms = np.linalg.norm(matrix, axis=1, keepdims=True)
            norms = np.where(norms == 0, 1, norms)
            genormaliseerd = matrix / norms
            sim_matrix = genormaliseerd @ genormaliseerd.T

            for i in range(len(ids)):
                for j in range(i + 1, len(ids)):
                    if sim_matrix[i, j] > self.drempel:
                        paren.append((ids[i], ids[j], float(sim_matrix[i, j])))
        else:
            # Pure Python fallback — alleen adjacent pairs O(n)
            for i in range(len(ids) - 1):
                sim = self._cosine_similarity(embeddings[i], embeddings[i + 1])
                if sim > self.drempel:
                    paren.append((ids[i], ids[i + 1], sim))

        return paren

    @staticmethod
    def _cosine_similarity(a: List[float], b: List[float]) -> float:
        """Bereken cosine similarity tussen twee vectoren."""
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    @staticmethod
    def _bepaal_oudste(
        id_a: str,
        id_b: str,
        tracker: AccessTracker,
        shard: str,
    ) -> str:
        """Bepaal het oudste fragment van een paar via AccessTracker."""
        try:
            conn = tracker._connect()
            cursor = conn.execute("""
                SELECT fragment_id, created_at FROM fragment_access
                WHERE fragment_id IN (?, ?) AND shard = ?
                ORDER BY created_at ASC
                LIMIT 1
            """, (id_a, id_b, shard))
            row = cursor.fetchone()
            conn.close()
            if row:
                return row["fragment_id"]
        except Exception as e:
            logger.debug("RedundantieDetector oudste lookup fout: %s", e)
        # Fallback: eerste is oudste
        return id_a


# ═══════════════════════════════════════════════════════════
# ColdStorageMigrator — Stale fragment archival
# ═══════════════════════════════════════════════════════════

class ColdStorageMigrator:
    """Archiveert stale fragmenten naar een cold_storage collectie.

    Fragmenten die langer dan verval_dagen niet zijn geraadpleegd
    worden gemigreerd naar de danny_cold collectie.
    """

    def __init__(
        self,
        client: Any = None,
        embed_fn: Any = None,
        verval_dagen: int = 14,
    ) -> None:
        """Init  ."""
        self._client = client
        self._embed_fn = embed_fn
        self.verval_dagen = verval_dagen
        self._cold_collection = None

    def _get_cold_collection(self) -> None:
        """Lazy init cold storage collectie."""
        if self._cold_collection is not None:
            return self._cold_collection
        if self._client is None:
            return None
        try:
            self._cold_collection = self._client.get_or_create_collection(
                name=Config.COLD_STORAGE_COLLECTION,
                embedding_function=self._embed_fn,
                metadata={"description": "Danny Cold Storage — gearchiveerde fragmenten"},
            )
            return self._cold_collection
        except Exception as e:
            logger.debug("ColdStorageMigrator cold collectie fout: %s", e)
            return None

    def migreer(
        self,
        fragment_ids: List[str],
        bron_collection: Any,
        shard: str,
        tracker: Optional[AccessTracker] = None,
    ) -> int:
        """Migreer stale fragmenten naar cold storage.

        Args:
            fragment_ids: IDs van te archiveren fragmenten.
            bron_collection: ChromaDB bron-collectie.
            shard: Naam van de bron-shard.
            tracker: Optionele AccessTracker voor shard update.

        Returns:
            Aantal gemigreerde fragmenten.
        """
        if not fragment_ids:
            return 0

        cold = self._get_cold_collection()
        if cold is None:
            return 0

        gemigreerd = 0
        batch_size = 100
        nu = datetime.now().isoformat()

        for i in range(0, len(fragment_ids), batch_size):
            batch_ids = fragment_ids[i:i + batch_size]
            try:
                # Haal data op van bron
                data = bron_collection.get(
                    ids=batch_ids,
                    include=["documents", "metadatas", "embeddings"],
                )
                ids = data.get("ids", [])
                docs = data.get("documents", [])
                metas = data.get("metadatas", [])
                embs = data.get("embeddings", [])

                if not ids:
                    continue

                # Verrijk metadata
                enriched_metas = []
                for meta in metas:
                    m = dict(meta) if meta else {}
                    m["cold_archived_at"] = nu
                    m["original_shard"] = shard
                    enriched_metas.append(m)

                # Upsert naar cold
                upsert_kwargs = {
                    "ids": ids,
                    "documents": docs,
                    "metadatas": enriched_metas,
                }
                if embs:
                    upsert_kwargs["embeddings"] = embs
                cold.upsert(**upsert_kwargs)

                # Verwijder uit bron
                bron_collection.delete(ids=ids)

                # Update tracker
                if tracker:
                    for fid in ids:
                        tracker.update_shard(fid, shard, Config.COLD_STORAGE_COLLECTION)

                gemigreerd += len(ids)
            except Exception as e:
                logger.debug("ColdStorageMigrator migratie batch fout %s: %s", shard, e)

        return gemigreerd

    def zoek_cold(self, query: str, top_k: int = 3) -> List[dict]:
        """Doorzoek cold storage.

        Args:
            query: Zoekquery tekst.
            top_k: Aantal resultaten.

        Returns:
            Lijst van resultaat-dicts.
        """
        cold = self._get_cold_collection()
        if cold is None:
            return []
        try:
            count = cold.count()
            if count == 0:
                return []
            n = min(top_k, count)
            results = cold.query(
                query_texts=[query],
                n_results=n,
                include=["documents", "metadatas", "distances"],
            )
            docs = results["documents"][0]
            metas = results["metadatas"][0]
            dists = results["distances"][0]
            return [
                {"tekst": doc, "metadata": meta, "distance": dist}
                for doc, meta, dist in zip(docs, metas, dists)
            ]
        except Exception as e:
            logger.debug("ColdStorageMigrator zoek_cold fout: %s", e)
            return []


# ═══════════════════════════════════════════════════════════
# SelfPruning — Orchestrator
# ═══════════════════════════════════════════════════════════

class SelfPruning:
    """Orchestreert de volledige vector store maintenance cyclus.

    Combineert AccessTracker, EntropieScanner, RedundantieDetector
    en ColdStorageMigrator in één prune() aanroep.
    """

    def __init__(self) -> None:
        """Init  ."""
        self.tracker = AccessTracker()
        self.entropie = EntropieScanner(drempel=Config.ENTROPY_THRESHOLD)
        self.redundantie = RedundantieDetector(drempel=Config.REDUNDANCY_THRESHOLD)
        self._migrator: Optional[ColdStorageMigrator] = None
        self._client = None
        self._embed_fn = None
        self._collections: Dict[str, Any] = {}
        self._lock = threading.Lock()

    def _ensure_chromadb(self) -> bool:
        """Lazy init ChromaDB client."""
        if self._client is not None:
            return True
        if os.environ.get("DANNY_TEST_MODE") == "1":
            return False
        try:
            pass  # import moved to top-level
            pass  # import moved to top-level

            chroma_dir = str(Config.RAG_DATA_DIR / "chromadb")
            self._client = chromadb.PersistentClient(path=chroma_dir)
            self._embed_fn = get_chroma_embed_fn()
            self._migrator = ColdStorageMigrator(
                client=self._client,
                embed_fn=self._embed_fn,
                verval_dagen=Config.RECENCY_DECAY_DAYS,
            )
            return True
        except Exception as e:
            logger.debug("SelfPruning ChromaDB init fout: %s", e)
            return False

    def _get_collection(self, shard: str) -> None:
        """Haal een ChromaDB collectie op."""
        if shard in self._collections:
            return self._collections[shard]
        if not self._ensure_chromadb():
            return None
        try:
            coll = self._client.get_or_create_collection(
                name=shard,
                embedding_function=self._embed_fn,
            )
            self._collections[shard] = coll
            return coll
        except Exception as e:
            logger.debug("SelfPruning collectie fout %s: %s", shard, e)
            return None

    # ─── Public API ───────────────────────────────────

    def registreer_toegang(self, fragment_ids: List[str], shard: str) -> None:
        """Registreer dat fragmenten zijn geraadpleegd."""
        try:
            self.tracker.registreer_toegang(fragment_ids, shard)
        except Exception as e:
            logger.debug("SelfPruning registreer_toegang fout: %s", e)

    def registreer_creatie(self, fragment_ids: List[str], shard: str) -> None:
        """Registreer nieuw aangemaakte fragmenten."""
        try:
            self.tracker.registreer_creatie(fragment_ids, shard)
        except Exception as e:
            logger.debug("SelfPruning registreer_creatie fout: %s", e)

    def prune(self) -> dict:
        """Voer een volledige prune cyclus uit.

        Returns:
            Dict met resultaten:
            - gearchiveerd: aantal naar cold storage
            - vernietigd: aantal duplicaten verwijderd
            - entropie_geflagd: aantal low-entropy fragmenten
            - duur_ms: uitvoertijd in milliseconden
        """
        if not Config.PRUNING_ENABLED:
            return {
                "gearchiveerd": 0,
                "vernietigd": 0,
                "entropie_geflagd": 0,
                "duur_ms": 0,
                "overgeslagen": True,
            }

        start = time.time()
        resultaat = {
            "gearchiveerd": 0,
            "vernietigd": 0,
            "entropie_geflagd": 0,
            "duur_ms": 0,
        }

        # Bepaal shards
        pass  # import moved to top-level
        shards = list(ALL_SHARDS)

        # NeuralBus: PRUNING_STARTED
        self._bus_publish("PRUNING_STARTED", {
            "shards": shards,
            "drempels": {
                "entropy": Config.ENTROPY_THRESHOLD,
                "redundantie": Config.REDUNDANCY_THRESHOLD,
                "verval_dagen": Config.RECENCY_DECAY_DAYS,
            },
        })

        # Bootstrap: registreer onbekende fragmenten
        self._bootstrap_onbekend(shards)

        for shard in shards:
            coll = self._get_collection(shard)
            if coll is None:
                continue

            try:
                count = coll.count()
                if count == 0:
                    continue
            except Exception as e:
                logger.debug("SelfPruning count fout %s: %s", shard, e)
                continue

            # Haal alle IDs
            try:
                alle_data = coll.get(include=[])
                alle_ids = alle_data.get("ids", [])
            except Exception as e:
                logger.debug("SelfPruning get IDs fout %s: %s", shard, e)
                continue

            # a. EntropieScanner
            actieve_ids = self.tracker.haal_actieve_fragmenten(
                dagen=Config.RECENCY_DECAY_DAYS
            )
            entropie_flagged = self.entropie.scan(
                shard, actieve_ids, alle_ids, coll,
            )
            resultaat["entropie_geflagd"] += len(entropie_flagged)

            # b. RedundantieDetector
            duplicaten = self.redundantie.detecteer(
                shard, coll, self.tracker,
            )
            if duplicaten:
                destroy_ids = [d[0] for d in duplicaten]
                try:
                    coll.delete(ids=destroy_ids)
                    self.tracker.verwijder(destroy_ids, shard)
                    resultaat["vernietigd"] += len(destroy_ids)

                    self._bus_publish("FRAGMENT_DESTROYED", {
                        "aantal": len(destroy_ids),
                        "shard": shard,
                        "reden": "redundantie",
                        "paren": [
                            {
                                "vernietigd": d[0],
                                "duplicaat_van": d[1],
                                "similarity": round(d[2], 4),
                            }
                            for d in duplicaten[:10]
                        ],
                    })
                except Exception as e:
                    logger.debug("SelfPruning destroy fout %s: %s", shard, e)

            # c. ColdStorageMigrator
            stale = self.tracker.haal_stale_fragmenten(
                dagen=Config.RECENCY_DECAY_DAYS
            )
            shard_stale = [s for s in stale if s["shard"] == shard]
            stale_ids = [s["fragment_id"] for s in shard_stale]

            if stale_ids and self._migrator:
                gemigreerd = self._migrator.migreer(
                    stale_ids, coll, shard, self.tracker,
                )
                resultaat["gearchiveerd"] += gemigreerd

                if gemigreerd > 0:
                    self._bus_publish("FRAGMENT_ARCHIVED", {
                        "aantal": gemigreerd,
                        "shard": shard,
                        "reden": "recency_decay",
                    })

        duur_ms = int((time.time() - start) * 1000)
        resultaat["duur_ms"] = duur_ms

        # NeuralBus: PRUNING_COMPLETE
        self._bus_publish("PRUNING_COMPLETE", resultaat)

        # CorticalStack audit log
        self._log_cortical(resultaat)

        return resultaat

    def statistieken(self) -> dict:
        """Haal pruning statistieken op.

        Returns:
            Dict met tracker stats en configuratie.
        """
        try:
            return {
                "totaal_gevolgd": self.tracker.totaal_gevolgd(),
                "entropy_drempel": self.entropie.drempel,
                "redundantie_drempel": self.redundantie.drempel,
                "verval_dagen": Config.RECENCY_DECAY_DAYS,
                "pruning_enabled": Config.PRUNING_ENABLED,
                "cold_collection": Config.COLD_STORAGE_COLLECTION,
            }
        except Exception as e:
            logger.debug("SelfPruning statistieken fout: %s", e)
            return {"pruning_enabled": False}

    # ─── Private helpers ──────────────────────────────

    def _bootstrap_onbekend(self, shards: List[str]) -> None:
        """Bootstrap: registreer onbekende fragmenten in de tracker.

        Eerste keer prune(): bestaande fragmenten krijgen
        created_at=now, access_count=0. Dit geeft een grace
        period voordat cold migration begint.
        """
        for shard in shards:
            coll = self._get_collection(shard)
            if coll is None:
                continue
            try:
                alle_data = coll.get(include=[])
                alle_ids = alle_data.get("ids", [])
                if not alle_ids:
                    continue
                # Registreer alleen IDs die nog niet in de tracker staan
                self.tracker.registreer_creatie(alle_ids, shard)
            except Exception as e:
                logger.debug("SelfPruning bootstrap fout %s: %s", shard, e)

    def _bus_publish(self, event_naam: str, data: dict) -> None:
        """Publiceer event naar NeuralBus."""
        try:
            pass  # import moved to top-level
            bus = get_bus()
            event_type = getattr(EventTypes, event_naam, event_naam.lower())
            bus.publish(event_type, data, bron="SelfPruning")
        except Exception as e:
            logger.debug("SelfPruning NeuralBus publish fout: %s", e)

    def _log_cortical(self, resultaat: dict) -> None:
        """Log prune resultaat naar CorticalStack."""
        pass  # import moved to top-level
        log_to_cortical(
            actor="self_pruning",
            action="prune_complete",
            details={
                "gearchiveerd": resultaat["gearchiveerd"],
                "vernietigd": resultaat["vernietigd"],
                "entropie_geflagd": resultaat["entropie_geflagd"],
                "duur_ms": resultaat["duur_ms"],
            },
        )


# ─── Singleton ────────────────────────────────────────────

_pruning_instance: Optional[SelfPruning] = None
_pruning_lock = threading.Lock()


def get_self_pruning() -> SelfPruning:
    """Verkrijg de singleton SelfPruning instantie."""
    global _pruning_instance
    if _pruning_instance is None:
        with _pruning_lock:
            if _pruning_instance is None:
                _pruning_instance = SelfPruning()
    return _pruning_instance

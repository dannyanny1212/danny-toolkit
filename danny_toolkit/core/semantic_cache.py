"""
SemanticCache — Vector-based LLM response cache met per-agent configuratie.

Gebruikt Voyage 256d MRL embeddings voor cosine-similarity matching.
Fallback naar SHA-256 exact-match als embeddings niet beschikbaar zijn.

Singleton via get_semantic_cache(). Thread-safe (SQLite WAL).

Gebruik:
    from danny_toolkit.core.semantic_cache import get_semantic_cache

    sc = get_semantic_cache()
    hit = sc.lookup("GhostWriter", query)
    if hit:
        # hit = {"content": "...", "type": "text", "metadata": {...}}
        return SwarmPayload(agent="GhostWriter", **hit)
    # ... LLM call ...
    sc.store("GhostWriter", query, response, payload_type="text", payload_meta={})
"""

import hashlib
import json
import logging
import os
import sqlite3
import struct
import threading
import time
from pathlib import Path
from typing import Dict, Optional

from danny_toolkit.core.config import Config

logger = logging.getLogger(__name__)

# Optionele dependencies
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False


class SemanticCache:
    """Vector-based LLM response cache met per-agent configuratie."""

    # Per-agent configuratie: {agent_naam: (ttl_sec, similarity_threshold)}
    AGENT_CONFIG = {
        "GhostWriter":  (3600, 0.90),   # 1 uur, hoge threshold (exacte code-match)
        "Artificer":    (1800, 0.82),   # 30 min, medium (skill-patronen)
        "Strategist":   (1200, 0.85),   # 20 min, medium-hoog
        "EchoAgent":    (600,  0.95),   # 10 min, zeer hoog (simpele antwoorden)
        "MemexAgent":   (900,  0.88),   # 15 min, hoog (RAG context)
    }

    # Agents die NOOIT gecacht worden
    BLACKLIST = {
        "CentralBrain",        # Moet altijd vers (gebruiker-facing)
        "VoidWalker",          # Web research = altijd vers
        "Tribunal",            # Verificatie mag niet gecacht
        "AdversarialTribunal", # Verificatie mag niet gecacht
        "#@*VirtualTwin",      # Shadow sandbox = experimenteel
    }

    _MAX_ENTRIES_PER_AGENT = 500
    _EVICT_INTERVAL = 100  # Elke N writes, verwijder verlopen entries

    def __init__(self, db_path: Path = None):
        """Initializes a new instance of the class.

 Args:
   db_path: Optional path to the database file. Defaults to a file named "semantic_cache.db" in the Config.DATA_DIR.

 Returns:
   None

 Note:
   The database directory is created if it does not exist. 
   The embedding provider is lazily initialized. 
   Various instance variables are initialized to track database performance metrics."""
        self._db_path = db_path or (Config.DATA_DIR / "semantic_cache.db")
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._write_count = 0
        self._total_hits = 0
        self._total_misses = 0

        # Embedding provider (lazy init)
        self._embed_provider = None
        self._embed_init_tried = False

        self._init_db()

    def _init_db(self):
        """Maak SQLite database + tabel aan."""
        try:
            conn = sqlite3.connect(str(self._db_path), timeout=5)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=3000")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent TEXT NOT NULL,
                    query_hash TEXT NOT NULL,
                    query_text TEXT NOT NULL,
                    embedding BLOB,
                    response TEXT NOT NULL,
                    created REAL NOT NULL,
                    ttl_seconds INTEGER NOT NULL,
                    hits INTEGER DEFAULT 0
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_agent_created
                ON cache_entries (agent, created)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_agent_hash
                ON cache_entries (agent, query_hash)
            """)
            # Migratie: payload_type + payload_meta kolommen (v6.3.0)
            for col, default in [
                ("payload_type", "'text'"),
                ("payload_meta", "'{}'"),
            ]:
                try:
                    conn.execute(
                        f"ALTER TABLE cache_entries ADD COLUMN {col} TEXT DEFAULT {default}"
                    )
                except sqlite3.OperationalError:
                    pass  # kolom bestaat al
            conn.commit()
            conn.close()
        except Exception as e:
            logger.debug("SemanticCache DB init failed: %s", e)

    def _get_conn(self) -> sqlite3.Connection:
        """Open een SQLite connectie."""
        conn = sqlite3.connect(str(self._db_path), timeout=5)
        conn.execute("PRAGMA busy_timeout=3000")
        return conn

    def _get_embed_provider(self):
        """Lazy init van CachedEmbeddingProvider."""
        if self._embed_init_tried:
            return self._embed_provider
        self._embed_init_tried = True
        try:
            from danny_toolkit.core.embeddings import VoyageEmbeddings, CachedEmbeddingProvider
            voyage = VoyageEmbeddings()
            self._embed_provider = CachedEmbeddingProvider(voyage)
            logger.debug("SemanticCache: Voyage embedding provider geladen")
        except Exception as e:
            logger.debug("SemanticCache: Embedding provider niet beschikbaar: %s", e)
            self._embed_provider = None
        return self._embed_provider

    @staticmethod
    def _query_hash(query: str) -> str:
        """SHA-256 hash van query tekst."""
        return hashlib.sha256(query.strip().lower().encode("utf-8")).hexdigest()

    @staticmethod
    def _embedding_to_blob(embedding: list) -> bytes:
        """Converteer float-lijst naar compact BLOB (float32)."""
        return struct.pack(f"{len(embedding)}f", *embedding)

    @staticmethod
    def _blob_to_embedding(blob: bytes) -> list:
        """Converteer BLOB terug naar float-lijst."""
        count = len(blob) // 4
        return list(struct.unpack(f"{count}f", blob))

    @staticmethod
    def _cosine_similarity(a: list, b: list) -> float:
        """Cosine similarity tussen twee vectoren."""
        if HAS_NUMPY:
            va = np.array(a, dtype=np.float32)
            vb = np.array(b, dtype=np.float32)
            dot = np.dot(va, vb)
            na = np.linalg.norm(va)
            nb = np.linalg.norm(vb)
            if na == 0 or nb == 0:
                return 0.0
            return float(dot / (na * nb))
        else:
            # Pure Python fallback
            dot = sum(x * y for x, y in zip(a, b))
            na = sum(x * x for x in a) ** 0.5
            nb = sum(x * x for x in b) ** 0.5
            if na == 0 or nb == 0:
                return 0.0
            return dot / (na * nb)

    def lookup(self, agent_naam: str, query: str) -> Optional[dict]:
        """Zoek een gecacht antwoord via vector similarity.

        Returns:
            Dict met {"content", "type", "metadata"}, of None bij miss.
        """
        if agent_naam in self.BLACKLIST:
            return None
        config = self.AGENT_CONFIG.get(agent_naam)
        if config is None:
            return None

        ttl, threshold = config
        now = time.time()
        qhash = self._query_hash(query)

        try:
            # Probeer vector-based lookup
            provider = self._get_embed_provider()
            if provider is not None:
                query_emb = provider.embed_query(query)
                return self._vector_lookup(
                    agent_naam, query_emb, threshold, ttl, now
                )
            else:
                # Fallback: exacte hash match
                return self._hash_lookup(agent_naam, qhash, ttl, now)
        except Exception as e:
            logger.debug("SemanticCache lookup fout: %s", e)
            # Ultieme fallback
            try:
                return self._hash_lookup(agent_naam, qhash, ttl, now)
            except Exception as e2:
                logger.debug("SemanticCache hash fallback fout: %s", e2)
                return None

    def _vector_lookup(self, agent: str, query_emb: list,
                       threshold: float, ttl: int, now: float
                       ) -> Optional[dict]:
        """Vector similarity lookup tegen recente entries."""
        with self._lock:
            conn = self._get_conn()
            try:
                rows = conn.execute(
                    """SELECT id, embedding, response, created, ttl_seconds,
                            hits, payload_type, payload_meta
                       FROM cache_entries
                       WHERE agent = ? AND embedding IS NOT NULL
                       ORDER BY created DESC LIMIT 50""",
                    (agent,),
                ).fetchall()

                best_score = 0.0
                best_row = None

                for row_id, blob, response, created, row_ttl, hits, p_type, p_meta in rows:
                    # TTL check
                    if now - created > row_ttl:
                        continue
                    cached_emb = self._blob_to_embedding(blob)
                    score = self._cosine_similarity(query_emb, cached_emb)
                    if score > best_score:
                        best_score = score
                        best_row = (row_id, response, hits, p_type, p_meta)

                if best_row and best_score >= threshold:
                    row_id, response, hits, p_type, p_meta = best_row
                    conn.execute(
                        "UPDATE cache_entries SET hits = ? WHERE id = ?",
                        (hits + 1, row_id),
                    )
                    conn.commit()
                    self._total_hits += 1
                    meta = {}
                    try:
                        meta = json.loads(p_meta) if p_meta else {}
                    except (json.JSONDecodeError, TypeError):
                        pass
                    return {
                        "content": response,
                        "type": p_type or "text",
                        "metadata": meta,
                    }

                self._total_misses += 1
                return None
            finally:
                conn.close()

    def _hash_lookup(self, agent: str, qhash: str,
                     ttl: int, now: float) -> Optional[dict]:
        """Exacte hash lookup (fallback wanneer embeddings niet beschikbaar)."""
        with self._lock:
            conn = self._get_conn()
            try:
                row = conn.execute(
                    """SELECT id, response, created, ttl_seconds, hits,
                            payload_type, payload_meta
                       FROM cache_entries
                       WHERE agent = ? AND query_hash = ?
                       ORDER BY created DESC LIMIT 1""",
                    (agent, qhash),
                ).fetchone()

                if row is None:
                    self._total_misses += 1
                    return None

                row_id, response, created, row_ttl, hits, p_type, p_meta = row
                if now - created > row_ttl:
                    self._total_misses += 1
                    return None

                conn.execute(
                    "UPDATE cache_entries SET hits = ? WHERE id = ?",
                    (hits + 1, row_id),
                )
                conn.commit()
                self._total_hits += 1
                meta = {}
                try:
                    meta = json.loads(p_meta) if p_meta else {}
                except (json.JSONDecodeError, TypeError):
                    pass
                return {
                    "content": response,
                    "type": p_type or "text",
                    "metadata": meta,
                }
            finally:
                conn.close()

    def store(self, agent_naam: str, query: str, response: str,
              payload_type: str = "text", payload_meta: dict = None):
        """Sla een LLM response op in de cache (inclusief payload staat).

        Skip als agent geblacklist, niet geconfigureerd,
        of response te kort (<20 chars).
        """
        if agent_naam in self.BLACKLIST:
            return
        config = self.AGENT_CONFIG.get(agent_naam)
        if config is None:
            return
        if not response or len(response) < 20:
            return

        ttl, _ = config
        qhash = self._query_hash(query)
        now = time.time()

        # Serialiseer metadata (strip niet-cacheable velden)
        meta_json = "{}"
        if payload_meta:
            cacheable = {
                k: v for k, v in payload_meta.items()
                if k not in ("cached", "trace_id", "fout_context", "error_type")
            }
            try:
                meta_json = json.dumps(cacheable, default=str)
            except (TypeError, ValueError):
                meta_json = "{}"

        # Probeer embedding te genereren
        embedding_blob = None
        try:
            provider = self._get_embed_provider()
            if provider is not None:
                emb = provider.embed_query(query)
                embedding_blob = self._embedding_to_blob(emb)
        except Exception as e:
            logger.debug("SemanticCache embed voor store mislukt: %s", e)

        with self._lock:
            try:
                conn = self._get_conn()
                conn.execute(
                    """INSERT INTO cache_entries
                       (agent, query_hash, query_text, embedding, response,
                        created, ttl_seconds, hits, payload_type, payload_meta)
                       VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?)""",
                    (agent_naam, qhash, query[:500], embedding_blob,
                     response, now, ttl, payload_type or "text", meta_json),
                )
                conn.commit()

                # FIFO eviction per agent
                count = conn.execute(
                    "SELECT COUNT(*) FROM cache_entries WHERE agent = ?",
                    (agent_naam,),
                ).fetchone()[0]
                if count > self._MAX_ENTRIES_PER_AGENT:
                    overschot = count - self._MAX_ENTRIES_PER_AGENT
                    conn.execute(
                        """DELETE FROM cache_entries WHERE id IN (
                               SELECT id FROM cache_entries
                               WHERE agent = ?
                               ORDER BY created ASC LIMIT ?
                           )""",
                        (agent_naam, overschot),
                    )
                    conn.commit()

                conn.close()
            except Exception as e:
                logger.debug("SemanticCache store fout: %s", e)
                return

        # Periodieke eviction van verlopen entries
        self._write_count += 1
        if self._write_count >= self._EVICT_INTERVAL:
            self._write_count = 0
            self.evict_expired()

    def evict_expired(self):
        """Verwijder alle verlopen cache entries."""
        now = time.time()
        with self._lock:
            try:
                conn = self._get_conn()
                deleted = conn.execute(
                    "DELETE FROM cache_entries WHERE (created + ttl_seconds) < ?",
                    (now,),
                ).rowcount
                conn.commit()
                conn.close()
                if deleted:
                    logger.debug("SemanticCache: %d verlopen entries verwijderd", deleted)
            except Exception as e:
                logger.debug("SemanticCache evict fout: %s", e)

    def stats(self) -> dict:
        """Cache statistieken per agent en totaal."""
        try:
            conn = self._get_conn()
            rows = conn.execute(
                """SELECT agent, COUNT(*) as cnt, SUM(hits) as total_hits
                   FROM cache_entries GROUP BY agent"""
            ).fetchall()

            total_entries = 0
            total_hits = 0
            per_agent = {}
            for agent, cnt, hits in rows:
                hits = hits or 0
                per_agent[agent] = {
                    "entries": cnt,
                    "hits": hits,
                }
                total_entries += cnt
                total_hits += hits

            # DB grootte
            db_size_kb = 0
            if self._db_path.exists():
                db_size_kb = round(self._db_path.stat().st_size / 1024, 1)

            conn.close()

            total_lookups = self._total_hits + self._total_misses
            return {
                "total_entries": total_entries,
                "total_hits": total_hits,
                "session_hits": self._total_hits,
                "session_misses": self._total_misses,
                "session_hit_rate": (
                    round(self._total_hits / max(total_lookups, 1) * 100, 1)
                ),
                "db_size_kb": db_size_kb,
                "per_agent": per_agent,
            }
        except Exception as e:
            logger.debug("SemanticCache stats fout: %s", e)
            return {"total_entries": 0, "total_hits": 0, "error": str(e)}

    def clear(self, agent: str = None):
        """Wis cache entries. Optioneel per agent."""
        with self._lock:
            try:
                conn = self._get_conn()
                if agent:
                    conn.execute(
                        "DELETE FROM cache_entries WHERE agent = ?",
                        (agent,),
                    )
                else:
                    conn.execute("DELETE FROM cache_entries")
                conn.commit()
                conn.close()
            except Exception as e:
                logger.debug("SemanticCache clear fout: %s", e)


# -- Singleton --

_sc_instance: Optional[SemanticCache] = None
_sc_lock = threading.Lock()


def get_semantic_cache() -> SemanticCache:
    """Singleton accessor voor SemanticCache."""
    global _sc_instance
    if _sc_instance is None:
        with _sc_lock:
            if _sc_instance is None:
                _sc_instance = SemanticCache()
    return _sc_instance

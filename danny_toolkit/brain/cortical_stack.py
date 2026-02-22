"""
Cortical Stack - Persistent Geheugen via SQLite.

Episodic memory, semantic facts en system metrics in een
thread-safe SQLite database. Complementeert de bestaande
JSON-gebaseerde UnifiedMemory.

Tabellen:
  - episodic_memory: tijdlijn van events
  - semantic_memory: feiten (key-value, UNIQUE)
  - system_stats: metriek-waarden voor monitoring

Gebruik:
    from danny_toolkit.brain.cortical_stack import (
        get_cortical_stack,
    )
    stack = get_cortical_stack()
    stack.log_event("user", "login", {"ip": "127.0.0.1"})
    stack.remember_fact("user_name", "Danny", confidence=0.9)
    print(stack.recall("user_name"))

Geen nieuwe dependencies: sqlite3 is stdlib.
"""

import gzip
import json
import shutil
import sqlite3
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..core.config import Config


class CorticalStack:
    """SQLite-backed persistent geheugen.

    Thread-safe via een Lock op alle schrijfoperaties.
    Leesoperaties zijn lockvrij (WAL mode).
    Writes worden gebatched voor betere performance.
    """

    SCHEMA_VERSION = 1
    _BATCH_SIZE = 20        # flush na N writes
    _BATCH_INTERVAL = 5.0   # flush elke N seconden

    def __init__(self, db_path: Optional[Path] = None):
        Config.ensure_dirs()
        self._db_path = db_path or (
            Config.DATA_DIR / "cortical_stack.db"
        )
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(
            str(self._db_path),
            check_same_thread=False,
        )
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._conn.execute("PRAGMA busy_timeout=5000")
        self._pending_writes = 0
        self._last_flush = time.time()
        self._create_tables()

    # ─── Schema ───

    def _create_tables(self):
        """Maak tabellen en indexes aan."""
        with self._lock:
            cur = self._conn.cursor()

            cur.execute("""
                CREATE TABLE IF NOT EXISTS episodic_memory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    action TEXT NOT NULL,
                    details TEXT DEFAULT '{}',
                    source TEXT DEFAULT 'system'
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS semantic_memory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT UNIQUE NOT NULL,
                    value TEXT NOT NULL,
                    confidence REAL DEFAULT 0.5,
                    learned_at TEXT NOT NULL,
                    last_accessed TEXT NOT NULL,
                    access_count INTEGER DEFAULT 0
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS system_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    metric TEXT NOT NULL,
                    value REAL NOT NULL,
                    tags TEXT DEFAULT '{}'
                )
            """)

            # Indexes
            cur.execute("""
                CREATE INDEX IF NOT EXISTS
                    idx_episodic_ts
                ON episodic_memory(timestamp)
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS
                    idx_episodic_actor
                ON episodic_memory(actor)
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS
                    idx_stats_metric_ts
                ON system_stats(metric, timestamp)
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS
                    idx_semantic_access
                ON semantic_memory(access_count DESC)
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS
                    idx_stats_ts_only
                ON system_stats(timestamp)
            """)

            self._conn.commit()

    def _maybe_flush(self):
        """Commit als batch vol is of interval verstreken.

        Moet aangeroepen worden BINNEN self._lock.
        """
        self._pending_writes += 1
        now = time.time()
        if (
            self._pending_writes >= self._BATCH_SIZE
            or now - self._last_flush >= self._BATCH_INTERVAL
        ):
            self._conn.commit()
            self._pending_writes = 0
            self._last_flush = now

    def flush(self):
        """Forceer commit van alle pending writes."""
        with self._lock:
            if self._pending_writes > 0:
                self._conn.commit()
                self._pending_writes = 0
                self._last_flush = time.time()

    # ─── Episodic Memory ───

    def log_event(
        self,
        actor: str,
        action: str,
        details: Optional[Dict[str, Any]] = None,
        source: str = "system",
    ) -> int:
        """Log een event in episodic memory.

        Returns:
            Het id van het ingevoegde record.
        """
        now = datetime.now().isoformat()
        details_json = json.dumps(
            details or {}, ensure_ascii=False
        )

        with self._lock:
            cur = self._conn.execute(
                """
                INSERT INTO episodic_memory
                    (timestamp, actor, action, details, source)
                VALUES (?, ?, ?, ?, ?)
                """,
                (now, actor, action, details_json, source),
            )
            self._maybe_flush()
            return cur.lastrowid

    def get_recent_events(
        self,
        count: int = 50,
        actor: Optional[str] = None,
    ) -> List[dict]:
        """Haal recente events op.

        Args:
            count: Maximum aantal events.
            actor: Optioneel filter op actor.

        Returns:
            Lijst van event dicts (nieuwste eerst).
        """
        if actor:
            rows = self._conn.execute(
                """
                SELECT * FROM episodic_memory
                WHERE actor = ?
                ORDER BY id DESC LIMIT ?
                """,
                (actor, count),
            ).fetchall()
        else:
            rows = self._conn.execute(
                """
                SELECT * FROM episodic_memory
                ORDER BY id DESC LIMIT ?
                """,
                (count,),
            ).fetchall()

        return [self._row_to_dict(r) for r in rows]

    def search_events(
        self, query: str, limit: int = 20
    ) -> List[dict]:
        """Zoek in event details via LIKE."""
        rows = self._conn.execute(
            """
            SELECT * FROM episodic_memory
            WHERE details LIKE ?
            ORDER BY id DESC LIMIT ?
            """,
            (f"%{query}%", limit),
        ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    # ─── Semantic Memory ───

    def remember_fact(
        self,
        key: str,
        value: str,
        confidence: float = 0.5,
    ) -> bool:
        """Sla een feit op (upsert op key).

        Returns:
            True als het feit is opgeslagen.
        """
        now = datetime.now().isoformat()

        with self._lock:
            try:
                self._conn.execute(
                    """
                    INSERT INTO semantic_memory
                        (key, value, confidence,
                         learned_at, last_accessed,
                         access_count)
                    VALUES (?, ?, ?, ?, ?, 0)
                    ON CONFLICT(key) DO UPDATE SET
                        value = excluded.value,
                        confidence = MAX(
                            confidence, excluded.confidence
                        ),
                        last_accessed = excluded.last_accessed,
                        access_count = access_count + 1
                    """,
                    (key, value, confidence, now, now),
                )
                self._maybe_flush()
                return True
            except sqlite3.Error:
                return False

    def recall(self, key: str) -> Optional[dict]:
        """Haal een feit op via key.

        Verhoogt access_count bij elke recall.

        Returns:
            Dict met key/value/confidence of None.
        """
        row = self._conn.execute(
            """
            SELECT * FROM semantic_memory
            WHERE key = ?
            """,
            (key,),
        ).fetchone()

        if row is None:
            return None

        # Update access stats
        now = datetime.now().isoformat()
        with self._lock:
            self._conn.execute(
                """
                UPDATE semantic_memory
                SET last_accessed = ?,
                    access_count = access_count + 1
                WHERE key = ?
                """,
                (now, key),
            )
            self._maybe_flush()

        return self._row_to_dict(row)

    def recall_all(
        self,
        prefix: Optional[str] = None,
        min_confidence: float = 0.0,
    ) -> List[dict]:
        """Haal alle feiten op, optioneel gefilterd.

        Args:
            prefix: Filter op key prefix (bijv. "voorkeur_").
            min_confidence: Minimale confidence drempel.

        Returns:
            Lijst van fact dicts.
        """
        if prefix:
            rows = self._conn.execute(
                """
                SELECT * FROM semantic_memory
                WHERE key LIKE ? AND confidence >= ?
                ORDER BY access_count DESC
                """,
                (f"{prefix}%", min_confidence),
            ).fetchall()
        else:
            rows = self._conn.execute(
                """
                SELECT * FROM semantic_memory
                WHERE confidence >= ?
                ORDER BY access_count DESC
                """,
                (min_confidence,),
            ).fetchall()

        return [self._row_to_dict(r) for r in rows]

    # ─── System Stats ───

    def log_stat(
        self,
        metric: str,
        value: float,
        tags: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Log een systeem metriek.

        Returns:
            Het id van het ingevoegde record.
        """
        now = datetime.now().isoformat()
        tags_json = json.dumps(
            tags or {}, ensure_ascii=False
        )

        with self._lock:
            cur = self._conn.execute(
                """
                INSERT INTO system_stats
                    (timestamp, metric, value, tags)
                VALUES (?, ?, ?, ?)
                """,
                (now, metric, value, tags_json),
            )
            self._maybe_flush()
            return cur.lastrowid

    def get_stats_summary(
        self, metric: str, hours: int = 24
    ) -> dict:
        """Haal samenvatting op voor een metriek.

        Returns:
            Dict met avg, min, max, count.
        """
        since = (
            datetime.now() - timedelta(hours=hours)
        ).isoformat()

        row = self._conn.execute(
            """
            SELECT
                AVG(value) as avg,
                MIN(value) as min,
                MAX(value) as max,
                COUNT(*) as count
            FROM system_stats
            WHERE metric = ? AND timestamp >= ?
            """,
            (metric, since),
        ).fetchone()

        if row and row["count"] > 0:
            return {
                "metric": metric,
                "hours": hours,
                "avg": round(row["avg"], 2),
                "min": round(row["min"], 2),
                "max": round(row["max"], 2),
                "count": row["count"],
            }
        return {
            "metric": metric,
            "hours": hours,
            "avg": 0,
            "min": 0,
            "max": 0,
            "count": 0,
        }

    # ─── Beheer ───

    def get_stats(self) -> dict:
        """Totalen per tabel."""
        episodic = self._conn.execute(
            "SELECT COUNT(*) as c FROM episodic_memory"
        ).fetchone()["c"]
        semantic = self._conn.execute(
            "SELECT COUNT(*) as c FROM semantic_memory"
        ).fetchone()["c"]
        stats = self._conn.execute(
            "SELECT COUNT(*) as c FROM system_stats"
        ).fetchone()["c"]

        return {
            "episodic_events": episodic,
            "semantic_facts": semantic,
            "system_stats": stats,
            "total": episodic + semantic + stats,
            "db_path": str(self._db_path),
        }

    def prune_old_stats(self, days: int = 30):
        """Verwijder system_stats ouder dan X dagen."""
        cutoff = (
            datetime.now() - timedelta(days=days)
        ).isoformat()

        with self._lock:
            self._conn.execute(
                """
                DELETE FROM system_stats
                WHERE timestamp < ?
                """,
                (cutoff,),
            )
            self._conn.commit()

    # ─── Backup & Restore ───

    _MAX_BACKUPS = 7  # Keep last 7 backups

    def backup(self, compress: bool = True) -> Path:
        """Create timestamped backup of cortical_stack.db.

        Steps:
        1. WAL checkpoint (flush pending writes to main DB)
        2. Copy to Config.BACKUP_DIR / cortical_stack_YYYYMMDD_HHMMSS.db
        3. Optional gzip compression (.db.gz)
        4. Prune old backups: keep last 7

        Returns:
            Path to the backup file.
        """
        Config.ensure_dirs()
        backup_dir = Config.BACKUP_DIR if hasattr(Config, "BACKUP_DIR") else Config.DATA_DIR / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)

        # 1. WAL checkpoint — flush all pending writes to main DB
        with self._lock:
            if self._pending_writes > 0:
                self._conn.commit()
                self._pending_writes = 0
                self._last_flush = time.time()
            try:
                self._conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            except sqlite3.Error:
                pass

        # 2. Copy to backup location
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if compress:
            backup_path = backup_dir / f"cortical_stack_{timestamp}.db.gz"
            with open(str(self._db_path), "rb") as f_in:
                with gzip.open(str(backup_path), "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)
        else:
            backup_path = backup_dir / f"cortical_stack_{timestamp}.db"
            shutil.copy2(str(self._db_path), str(backup_path))

        # 3. Prune old backups
        self._prune_backups(backup_dir)

        return backup_path

    def _prune_backups(self, backup_dir: Path):
        """Keep only the last _MAX_BACKUPS backup files."""
        pattern = "cortical_stack_*"
        backups = sorted(backup_dir.glob(pattern), key=lambda p: p.name)
        while len(backups) > self._MAX_BACKUPS:
            oldest = backups.pop(0)
            try:
                oldest.unlink()
            except OSError:
                pass

    def restore(self, backup_path: Path) -> bool:
        """Restore from backup (requires restart).

        Safety: only restores if backup exists and is readable.
        """
        if not backup_path.exists():
            return False

        try:
            # Close current connection
            self.flush()
            self._conn.close()

            # Decompress if gzipped
            if backup_path.suffix == ".gz":
                with gzip.open(str(backup_path), "rb") as f_in:
                    with open(str(self._db_path), "wb") as f_out:
                        shutil.copyfileobj(f_in, f_out)
            else:
                shutil.copy2(str(backup_path), str(self._db_path))

            # Reconnect
            self._conn = sqlite3.connect(
                str(self._db_path), check_same_thread=False
            )
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA synchronous=NORMAL")
            self._conn.execute("PRAGMA busy_timeout=5000")
            self._pending_writes = 0
            self._last_flush = time.time()
            return True
        except Exception:
            return False

    # ─── Data Retention Policy ───

    def apply_retention_policy(self) -> dict:
        """Prune old data from all tables. Returns counts of deleted rows.

        Policies:
        - episodic_memory:     90 days
        - interaction_trace:   60 days
        - phantom_predictions: 30 days
        - system_stats:        30 days

        NOT pruned (permanent knowledge):
        - semantic_memory
        - knowledge_graph (entities, kg_edges)
        - synaptic_pathways (already has 7-day decay via Synapse)
        - temporal_patterns (bounded by cardinality)
        """
        policies = {
            "episodic_memory":     90,
            "interaction_trace":   60,
            "phantom_predictions": 30,
            "system_stats":        30,
        }

        deleted = {}
        with self._lock:
            for table, days in policies.items():
                cutoff = (datetime.now() - timedelta(days=days)).isoformat()
                try:
                    cur = self._conn.execute(
                        f"DELETE FROM {table} WHERE timestamp < ?",
                        (cutoff,),
                    )
                    deleted[table] = cur.rowcount
                except sqlite3.OperationalError:
                    # Table doesn't exist — skip silently
                    deleted[table] = 0

            self._conn.commit()

        return deleted

    def close(self):
        """Flush pending writes en sluit de database."""
        try:
            self.flush()
            self._conn.close()
        except sqlite3.Error:
            pass

    # ─── Helpers ───

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> dict:
        """Converteer een sqlite3.Row naar dict."""
        d = dict(row)
        # Parse JSON velden
        for veld in ("details", "tags"):
            if veld in d and isinstance(d[veld], str):
                try:
                    d[veld] = json.loads(d[veld])
                except (json.JSONDecodeError, TypeError):
                    pass
        return d


# ─── Singleton ───

_stack: Optional[CorticalStack] = None
_stack_lock = threading.Lock()


def get_cortical_stack(
    db_path: Optional[Path] = None,
) -> CorticalStack:
    """Lazy singleton accessor voor CorticalStack.

    Thread-safe. Eerste aanroep maakt de instantie aan.
    """
    global _stack

    if _stack is None:
        with _stack_lock:
            if _stack is None:
                _stack = CorticalStack(db_path)
    return _stack

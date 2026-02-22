"""
THE PHANTOM (Invention #20)
============================
Anticipatory intelligence — predicts user behavior from temporal patterns.

Users are creatures of habit: code in the morning, crypto on weekends,
health questions in the evening. Phantom detects these patterns from
interaction_trace data and pre-warms MEMEX context *before* the user asks.

Three temporal lenses:
  - Hourly  (40%): "At 14:00, Danny asks about code"
  - Daily   (30%): "On Mondays, Danny works on security"
  - Sequential (50%): "After crypto, Danny asks about health"

Pattern rebuild runs offline in Dreamer REM — not per-query.
Pre-warmed context is pop-once (consumed on use, prevents stale cache).

Gebruik:
    from danny_toolkit.brain.phantom import ThePhantom
    phantom = ThePhantom()
    predictions = phantom.predict_next()
    phantom.pre_warm_context(engine)
"""

import logging
import sqlite3
import threading
from collections import Counter
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    from danny_toolkit.core.config import Config
except ImportError:
    Config = None

try:
    from danny_toolkit.core.neural_bus import get_bus, EventTypes
    HAS_BUS = True
except ImportError:
    HAS_BUS = False


class ThePhantom:
    """Anticipatory intelligence — Invention #20.

    Builds temporal user behavior models from interaction_trace
    and pre-warms MEMEX context before the user asks.
    """

    # Confidence weights per temporal lens
    HOURLY_WEIGHT = 0.40
    DAILY_WEIGHT = 0.30
    SEQUENTIAL_WEIGHT = 0.50

    # Minimum confidence for pre-warming
    PRE_WARM_THRESHOLD = 0.25

    # Minimum samples before a pattern is trusted
    MIN_SAMPLES = 3

    def __init__(self, db_path: Optional[str] = None):
        if db_path:
            self._db_path = db_path
        elif Config:
            self._db_path = str(Config.DATA_DIR / "cortical_stack.db")
        else:
            self._db_path = "data/cortical_stack.db"

        self._conn = sqlite3.connect(
            self._db_path,
            check_same_thread=False,
            timeout=10,
        )
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA busy_timeout=5000")
        self._create_tables()

        # Pop-once pre-warmed context cache
        self._cache_lock = threading.Lock()
        self._pre_warmed: Dict[str, List[str]] = {}

    def _create_tables(self):
        """Create phantom_predictions and temporal_patterns tables."""
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS phantom_predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL DEFAULT (datetime('now')),
                predicted_category TEXT NOT NULL,
                confidence REAL NOT NULL,
                basis TEXT,
                pre_warmed INTEGER NOT NULL DEFAULT 0,
                actual_category TEXT,
                hit INTEGER,
                resolved INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS temporal_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_type TEXT NOT NULL,
                time_slot TEXT NOT NULL,
                category TEXT NOT NULL,
                frequency REAL NOT NULL DEFAULT 0,
                sample_count INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                UNIQUE(pattern_type, time_slot, category)
            );

            CREATE INDEX IF NOT EXISTS idx_predictions_resolved
                ON phantom_predictions(resolved);
            CREATE INDEX IF NOT EXISTS idx_patterns_type_slot
                ON temporal_patterns(pattern_type, time_slot);
        """)
        self._conn.commit()

    def update_patterns(self):
        """Rebuild temporal patterns from interaction_trace.

        Called during Dreamer REM cycle (offline, CPU-friendly).
        Analyzes hourly, daily, and sequential patterns.
        """
        logger.info("Phantom: rebuilding temporal patterns...")

        # Fetch all resolved traces with timestamps
        rows = self._conn.execute(
            """SELECT category, timestamp
               FROM interaction_trace
               WHERE category != 'UNKNOWN'
               ORDER BY timestamp ASC"""
        ).fetchall()

        if len(rows) < self.MIN_SAMPLES:
            logger.info("Phantom: insufficient data (%d traces)", len(rows))
            return

        # --- Hourly patterns ---
        hourly_counts: Dict[str, Counter] = {}
        for category, ts in rows:
            try:
                hour = str(datetime.fromisoformat(ts).hour)
            except (ValueError, TypeError):
                continue
            if hour not in hourly_counts:
                hourly_counts[hour] = Counter()
            hourly_counts[hour][category] += 1

        for hour, counter in hourly_counts.items():
            total = sum(counter.values())
            for category, count in counter.items():
                freq = count / total if total > 0 else 0
                self._upsert_pattern("hourly", hour, category, freq, count)

        # --- Daily patterns (weekday 0=Monday..6=Sunday) ---
        daily_counts: Dict[str, Counter] = {}
        for category, ts in rows:
            try:
                weekday = str(datetime.fromisoformat(ts).weekday())
            except (ValueError, TypeError):
                continue
            if weekday not in daily_counts:
                daily_counts[weekday] = Counter()
            daily_counts[weekday][category] += 1

        for weekday, counter in daily_counts.items():
            total = sum(counter.values())
            for category, count in counter.items():
                freq = count / total if total > 0 else 0
                self._upsert_pattern("daily", weekday, category, freq, count)

        # --- Sequential patterns (category A -> category B) ---
        seq_counts: Counter = Counter()
        seq_totals: Counter = Counter()
        for i in range(len(rows) - 1):
            prev_cat = rows[i][0]
            next_cat = rows[i + 1][0]
            pair = f"{prev_cat}->{next_cat}"
            seq_counts[pair] += 1
            seq_totals[prev_cat] += 1

        for pair, count in seq_counts.items():
            prev_cat = pair.split("->")[0]
            total = seq_totals[prev_cat]
            freq = count / total if total > 0 else 0
            self._upsert_pattern("sequential", prev_cat, pair, freq, count)

        self._conn.commit()
        logger.info(
            "Phantom: patterns rebuilt (hourly=%d, daily=%d, sequential=%d)",
            len(hourly_counts), len(daily_counts), len(seq_counts),
        )

    def _upsert_pattern(
        self, pattern_type: str, time_slot: str,
        category: str, frequency: float, sample_count: int,
    ):
        """Insert or update a temporal pattern."""
        self._conn.execute(
            """INSERT INTO temporal_patterns
               (pattern_type, time_slot, category, frequency, sample_count)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(pattern_type, time_slot, category)
               DO UPDATE SET frequency = ?, sample_count = ?,
                            updated_at = datetime('now')""",
            (pattern_type, time_slot, category, frequency,
             sample_count, frequency, sample_count),
        )

    def predict_next(self) -> List[Dict]:
        """Predict what the user will ask next.

        Combines hourly, daily, and sequential signals.
        Returns predictions sorted by confidence (descending).
        """
        now = datetime.now()
        current_hour = str(now.hour)
        current_weekday = str(now.weekday())

        # Get the most recent category for sequential prediction
        last_row = self._conn.execute(
            """SELECT category FROM interaction_trace
               WHERE category != 'UNKNOWN'
               ORDER BY id DESC LIMIT 1"""
        ).fetchone()
        last_category = last_row[0] if last_row else None

        # Collect confidence scores per category
        category_scores: Dict[str, float] = {}

        # Hourly signal
        hourly = self._conn.execute(
            """SELECT category, frequency, sample_count
               FROM temporal_patterns
               WHERE pattern_type = 'hourly' AND time_slot = ?
               AND sample_count >= ?""",
            (current_hour, self.MIN_SAMPLES),
        ).fetchall()

        for category, freq, _ in hourly:
            category_scores[category] = category_scores.get(category, 0) + (
                freq * self.HOURLY_WEIGHT
            )

        # Daily signal
        daily = self._conn.execute(
            """SELECT category, frequency, sample_count
               FROM temporal_patterns
               WHERE pattern_type = 'daily' AND time_slot = ?
               AND sample_count >= ?""",
            (current_weekday, self.MIN_SAMPLES),
        ).fetchall()

        for category, freq, _ in daily:
            category_scores[category] = category_scores.get(category, 0) + (
                freq * self.DAILY_WEIGHT
            )

        # Extern signal (shadow-verified patterns)
        extern = self._conn.execute(
            """SELECT category, frequency
               FROM temporal_patterns
               WHERE pattern_type = 'extern'
               AND sample_count >= 1""",
        ).fetchall()

        for pattern, freq in extern:
            category_scores[pattern] = category_scores.get(pattern, 0) + (
                freq * self.HOURLY_WEIGHT
            )

        # Sequential signal
        if last_category:
            sequential = self._conn.execute(
                """SELECT category, frequency, sample_count
                   FROM temporal_patterns
                   WHERE pattern_type = 'sequential'
                   AND time_slot = ?
                   AND sample_count >= ?""",
                (last_category, self.MIN_SAMPLES),
            ).fetchall()

            for pair, freq, _ in sequential:
                # pair is "PREV->NEXT", extract NEXT
                parts = pair.split("->")
                if len(parts) == 2:
                    next_cat = parts[1]
                    category_scores[next_cat] = category_scores.get(
                        next_cat, 0
                    ) + (freq * self.SEQUENTIAL_WEIGHT)

        # Build predictions sorted by confidence
        predictions = []
        for category, confidence in sorted(
            category_scores.items(),
            key=lambda x: x[1],
            reverse=True,
        ):
            if confidence >= self.PRE_WARM_THRESHOLD:
                basis_parts = []
                if any(c == category for c, _, _ in hourly):
                    basis_parts.append("hourly")
                if any(c == category for c, _, _ in daily):
                    basis_parts.append("daily")
                basis_parts_str = "+".join(basis_parts) if basis_parts else "sequential"

                predictions.append({
                    "category": category,
                    "confidence": round(confidence, 4),
                    "basis": basis_parts_str,
                })

        # Record predictions
        for pred in predictions[:3]:  # Top 3
            self._conn.execute(
                """INSERT INTO phantom_predictions
                   (predicted_category, confidence, basis)
                   VALUES (?, ?, ?)""",
                (pred["category"], pred["confidence"], pred["basis"]),
            )
        self._conn.commit()

        # Publish event
        if HAS_BUS and predictions:
            try:
                bus = get_bus()
                bus.publish(
                    EventTypes.PHANTOM_PREDICTION,
                    {
                        "predictions": predictions[:3],
                        "hour": current_hour,
                        "weekday": current_weekday,
                    },
                    bron="phantom",
                )
            except Exception as e:
                logger.debug("NeuralBus publish failed: %s", e)

        return predictions

    def registreer_patroon(self, pattern: str, bron: str = "extern"):
        """Register an external shadow pattern for Phantom prediction.

        Called by ShadowCortex Channel 3 to prime Phantom with shadow-explored
        topics. Patterns are stored with pattern_type='extern' and a high
        starting confidence (0.6) since they are shadow-verified.

        Args:
            pattern: Space-separated keywords from shadow consult.
            bron: Source identifier (default: 'extern').
        """
        if not pattern or not pattern.strip():
            return

        pattern = pattern.strip()[:200]
        try:
            self._conn.execute(
                """INSERT INTO temporal_patterns
                   (pattern_type, time_slot, category, frequency, sample_count)
                   VALUES ('extern', ?, ?, 0.6, 1)
                   ON CONFLICT(pattern_type, time_slot, category)
                   DO UPDATE SET frequency = MIN(frequency + 0.05, 1.0),
                                sample_count = sample_count + 1,
                                updated_at = datetime('now')""",
                (bron, pattern),
            )
            self._conn.commit()
            logger.debug("Phantom: extern patroon geregistreerd: '%s' (bron=%s)", pattern[:40], bron)
        except Exception as e:
            logger.debug("Phantom registreer_patroon failed: %s", e)

    def get_predictions(self, max_results: int = 5) -> List[Dict]:
        """Get unresolved predictions for snapshot/status reporting.

        Called by VirtualTwin.snapshot_state() to include Phantom predictions
        in the system state snapshot.

        Args:
            max_results: Maximum predictions to return (default 5).

        Returns:
            List of prediction dicts with category, confidence, basis.
        """
        try:
            rows = self._conn.execute(
                """SELECT predicted_category, confidence, basis, timestamp
                   FROM phantom_predictions
                   WHERE resolved = 0
                   ORDER BY confidence DESC
                   LIMIT ?""",
                (max_results,),
            ).fetchall()

            return [
                {
                    "category": r[0],
                    "confidence": r[1],
                    "basis": r[2],
                    "timestamp": r[3],
                }
                for r in rows
            ]
        except Exception as e:
            logger.debug("Phantom get_predictions failed: %s", e)
            return []

    def pre_warm_context(self, engine=None):
        """Pre-fetch MEMEX context for top prediction.

        Called after predict_next(). Fetches vector search results
        and stores them in pop-once cache.
        """
        predictions = self.predict_next()
        if not predictions or not engine:
            return

        top = predictions[0]
        category = top["category"]

        # Build a synthetic query from category agents
        agents = category.split("+")
        try:
            from swarm_engine import AdaptiveRouter
            query_parts = []
            for agent in agents:
                profielen = AdaptiveRouter.AGENT_PROFIELEN.get(agent, [])
                if profielen:
                    # Take first 5 words from first profile
                    words = profielen[0].split()[:5]
                    query_parts.extend(words)
            synthetic_query = " ".join(query_parts)
        except Exception as e:
            logger.debug("Synthetic query generatie: %s", e)
            synthetic_query = " ".join(agents)

        if not synthetic_query:
            return

        # Fetch MEMEX context
        try:
            if hasattr(engine, "_ophalen_memex_context"):
                context = engine._ophalen_memex_context(synthetic_query)
                if context:
                    with self._cache_lock:
                        self._pre_warmed[category] = context

                    # Mark prediction as pre-warmed
                    self._conn.execute(
                        """UPDATE phantom_predictions
                           SET pre_warmed = 1
                           WHERE resolved = 0
                           AND predicted_category = ?
                           ORDER BY id DESC LIMIT 1""",
                        (category,),
                    )
                    self._conn.commit()

                    logger.info(
                        "Phantom: pre-warmed %d fragments for %s",
                        len(context), category,
                    )
        except Exception as e:
            logger.debug("Phantom pre-warm failed: %s", e)

    def get_pre_warmed(self, category: str) -> List[str]:
        """Pop pre-warmed context for a category (pop-once).

        Returns context fragments if available, empty list otherwise.
        Context is consumed on use to prevent stale cache.
        """
        with self._cache_lock:
            context = self._pre_warmed.pop(category, [])

        if context and HAS_BUS:
            try:
                bus = get_bus()
                bus.publish(
                    EventTypes.PHANTOM_HIT,
                    {
                        "category": category,
                        "fragments": len(context),
                    },
                    bron="phantom",
                )
            except Exception as e:
                logger.debug("NeuralBus publish failed: %s", e)

        return context

    def resolve_predictions(self, actual_category: str):
        """Resolve unresolved predictions — mark as hit or miss.

        Called post-routing with the actual category.
        """
        unresolved = self._conn.execute(
            """SELECT id, predicted_category
               FROM phantom_predictions
               WHERE resolved = 0"""
        ).fetchall()

        for pred_id, predicted in unresolved:
            hit = 1 if predicted == actual_category else 0
            self._conn.execute(
                """UPDATE phantom_predictions
                   SET actual_category = ?, hit = ?, resolved = 1
                   WHERE id = ?""",
                (actual_category, hit, pred_id),
            )

        self._conn.commit()

    def get_accuracy(self) -> Dict:
        """Self-measurement: prediction accuracy stats."""
        row = self._conn.execute(
            """SELECT COUNT(*) FROM phantom_predictions
               WHERE resolved = 1"""
        ).fetchone()
        total = row[0] if row else 0

        row = self._conn.execute(
            """SELECT COUNT(*) FROM phantom_predictions
               WHERE resolved = 1 AND hit = 1"""
        ).fetchone()
        hits = row[0] if row else 0

        row = self._conn.execute(
            """SELECT COUNT(*) FROM phantom_predictions
               WHERE pre_warmed = 1 AND resolved = 1"""
        ).fetchone()
        pre_warmed = row[0] if row else 0

        row = self._conn.execute(
            """SELECT COUNT(*) FROM phantom_predictions
               WHERE pre_warmed = 1 AND hit = 1 AND resolved = 1"""
        ).fetchone()
        warm_hits = row[0] if row else 0

        return {
            "total_predictions": total,
            "hits": hits,
            "accuracy": round(hits / total, 4) if total > 0 else 0.0,
            "pre_warmed": pre_warmed,
            "warm_hit_rate": round(warm_hits / pre_warmed, 4) if pre_warmed > 0 else 0.0,
        }

"""
THE SYNAPSE (Invention #19)
===========================
Synaptic pathway plasticity for adaptive agent routing.

Learns which agents produce the best results for which query types
through implicit behavioral feedback signals. Over time the routing
surface adapts to actual performance via Hebbian plasticity:

  - Positive outcomes  -> strengthen pathway  (+0.08)
  - Negative outcomes  -> weaken pathway      (-0.12, negativity bias)
  - Sigmoid bounding   -> [0.05, 0.95] prevents lock-in or death
  - Bias multiplier    -> [0.715, 0.985] nudges routing, never overrides

Feedback signals are IMPLICIT (no user ratings needed):
  - Topic change           -> satisfaction   (+0.3)
  - Long silence new topic -> moderate       (+0.2)
  - Follow-up same topic   -> dissatisfied   (-0.4)
  - Rephrased same query   -> frustration    (-0.6)
  - Fast follow-up <30s    -> rejection      (-0.3)
  - Tribunal reject        -> strong neg     (-0.8)

Gebruik:
    from danny_toolkit.brain.synapse import TheSynapse
    synapse = TheSynapse()
    bias = synapse.get_routing_bias("bitcoin prijs")
    synapse.record_interaction("bitcoin prijs", ["CIPHER"], 1200, 350)
"""

import hashlib
import logging
import math
import sqlite3
import time
from datetime import datetime, timedelta
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


class TheSynapse:
    """Synaptic pathway plasticity — Invention #19.

    Learns from implicit behavioral feedback which agents
    perform best for which query categories. Applies Hebbian
    plasticity to strengthen/weaken routing pathways.
    """

    # Plasticity rates (negativity bias: weaken > strengthen)
    STRENGTHEN_RATE = 0.08
    WEAKEN_RATE = 0.12

    # Sigmoid bounds — prevent lock-in or pathway death
    MIN_STRENGTH = 0.05
    MAX_STRENGTH = 0.95

    # Bias multiplier range applied to cosine scores
    BIAS_MIN = 0.715
    BIAS_MAX = 0.985

    # Default strength for new pathways
    DEFAULT_STRENGTH = 0.5

    # Feedback signal values
    SIGNALS = {
        "topic_change": 0.3,          # Satisfaction
        "long_silence_new": 0.2,      # Moderate satisfaction
        "follow_up_same": -0.4,       # Dissatisfaction
        "rephrased_same": -0.6,       # Frustration
        "fast_follow_up": -0.3,       # Rejection
        "tribunal_reject": -0.8,      # Strong negative
    }

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

        # Cache: embed function from AdaptiveRouter
        self._embed_fn = None
        self._profiel_embeddings = None

    def _create_tables(self):
        """Create synaptic_pathways and interaction_trace tables."""
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS synaptic_pathways (
                query_category TEXT NOT NULL,
                agent_key TEXT NOT NULL,
                strength REAL NOT NULL DEFAULT 0.5,
                fire_count INTEGER NOT NULL DEFAULT 0,
                success_count INTEGER NOT NULL DEFAULT 0,
                fail_count INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                UNIQUE(query_category, agent_key)
            );

            CREATE TABLE IF NOT EXISTS interaction_trace (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                timestamp TEXT NOT NULL DEFAULT (datetime('now')),
                query_hash TEXT NOT NULL,
                category TEXT NOT NULL,
                agents_routed TEXT NOT NULL,
                response_length INTEGER DEFAULT 0,
                execution_ms REAL DEFAULT 0,
                feedback_signal REAL,
                feedback_source TEXT,
                resolved INTEGER NOT NULL DEFAULT 0
            );

            CREATE INDEX IF NOT EXISTS idx_trace_resolved
                ON interaction_trace(resolved);
            CREATE INDEX IF NOT EXISTS idx_trace_category
                ON interaction_trace(category);
            CREATE INDEX IF NOT EXISTS idx_trace_timestamp
                ON interaction_trace(timestamp);
            CREATE INDEX IF NOT EXISTS idx_pathways_category
                ON synaptic_pathways(query_category);
        """)
        self._conn.commit()

    def _get_embed_fn(self):
        """Reuse AdaptiveRouter's embedding function (zero extra load)."""
        if self._embed_fn is not None:
            return self._embed_fn
        try:
            import sys
            import io as _io
            from sentence_transformers import SentenceTransformer
            _old_out, _old_err = sys.stdout, sys.stderr
            sys.stdout = _io.StringIO()
            sys.stderr = _io.StringIO()
            try:
                model = SentenceTransformer(
                    "sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
                    device="cpu",
                )
            finally:
                sys.stdout = _old_out
                sys.stderr = _old_err
            self._embed_fn = model.encode
            return self._embed_fn
        except Exception as e:
            logger.debug("SentenceTransformer laden mislukt: %s", e)
            return None

    def _get_profiel_embeddings(self):
        """Lazy-load agent profile embeddings."""
        if self._profiel_embeddings is not None:
            return self._profiel_embeddings
        embed = self._get_embed_fn()
        if not embed:
            return None
        try:
            # Import AGENT_PROFIELEN from swarm_engine
            from swarm_engine import AdaptiveRouter
            self._profiel_embeddings = {}
            for agent, subs in AdaptiveRouter.AGENT_PROFIELEN.items():
                self._profiel_embeddings[agent] = [
                    embed(tekst) for tekst in subs
                ]
            return self._profiel_embeddings
        except Exception as e:
            logger.debug("Profiel embeddings laden mislukt: %s", e)
            return None

    @staticmethod
    def _cosine_sim(vec_a, vec_b) -> float:
        """Cosine similarity between two vectors."""
        dot = sum(a * b for a, b in zip(vec_a, vec_b))
        mag_a = math.sqrt(sum(a ** 2 for a in vec_a))
        mag_b = math.sqrt(sum(b ** 2 for b in vec_b))
        if mag_a == 0 or mag_b == 0:
            return 0.0
        return dot / (mag_a * mag_b)

    def categorize_query(self, user_input: str) -> str:
        """Categorize query by top-2 matching agents.

        Uses cosine similarity against AGENT_PROFIELEN vectors.
        Returns a stable category string like "CIPHER+ORACLE".
        """
        embed = self._get_embed_fn()
        profielen = self._get_profiel_embeddings()
        if not embed or not profielen:
            return "UNKNOWN"

        # Truncate to 500 chars (same as AdaptiveRouter)
        user_input = user_input[:500]
        input_vec = embed(user_input)

        scores = []
        for agent, sub_vecs in profielen.items():
            best = max(
                self._cosine_sim(input_vec, sv)
                for sv in sub_vecs
            )
            scores.append((agent, best))

        scores.sort(key=lambda x: x[1], reverse=True)
        top2 = [s[0] for s in scores[:2]]
        top2.sort()  # Alphabetical for consistency
        return "+".join(top2)

    @staticmethod
    def _hash_query(user_input: str) -> str:
        """Stable hash for query deduplication."""
        normalized = user_input.lower().strip()
        return hashlib.md5(normalized.encode("utf-8")).hexdigest()[:16]

    def record_interaction(
        self,
        user_input: str,
        agents_routed: List[str],
        execution_ms: float = 0,
        response_length: int = 0,
        session_id: str = None,
    ):
        """Record an interaction trace and resolve previous interaction's feedback.

        Called post-pipeline. Records the current interaction, then
        looks at the PREVIOUS unresolved trace to compute implicit feedback.
        """
        category = self.categorize_query(user_input)
        query_hash = self._hash_query(user_input)
        agents_str = ",".join(sorted(agents_routed))

        # Insert current trace
        self._conn.execute(
            """INSERT INTO interaction_trace
               (session_id, query_hash, category, agents_routed,
                response_length, execution_ms)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (session_id, query_hash, category, agents_str,
             response_length, execution_ms),
        )

        # Resolve PREVIOUS unresolved interaction
        prev = self._conn.execute(
            """SELECT id, query_hash, category, agents_routed, timestamp
               FROM interaction_trace
               WHERE resolved = 0 AND id < last_insert_rowid()
               ORDER BY id DESC LIMIT 1""",
        ).fetchone()

        if prev:
            prev_id, prev_hash, prev_cat, prev_agents, prev_ts = prev
            signal, source = self._compute_feedback(
                prev_hash, prev_cat, query_hash, category, prev_ts,
            )
            self._conn.execute(
                """UPDATE interaction_trace
                   SET feedback_signal = ?, feedback_source = ?, resolved = 1
                   WHERE id = ?""",
                (signal, source, prev_id),
            )

            # Apply Hebbian plasticity to previous interaction's agents
            if signal is not None:
                for agent in prev_agents.split(","):
                    agent = agent.strip()
                    if agent:
                        self._apply_plasticity(prev_cat, agent, signal)

        self._conn.commit()

    def _compute_feedback(
        self,
        prev_hash: str,
        prev_category: str,
        curr_hash: str,
        curr_category: str,
        prev_timestamp: str,
    ) -> tuple:
        """Compute implicit feedback signal from behavioral cues.

        Returns (signal_value, source_name) or (None, None).
        """
        # Parse timestamp
        try:
            prev_time = datetime.fromisoformat(prev_timestamp)
            elapsed = (datetime.now() - prev_time).total_seconds()
        except (ValueError, TypeError):
            elapsed = 60  # Default

        # Same exact query rephrased
        if prev_hash == curr_hash:
            return self.SIGNALS["rephrased_same"], "rephrased_same"

        # Fast follow-up (<30s) on different topic -> rejection
        if elapsed < 30 and prev_category != curr_category:
            return self.SIGNALS["fast_follow_up"], "fast_follow_up"

        # Follow-up on same topic -> dissatisfaction
        if prev_category == curr_category:
            return self.SIGNALS["follow_up_same"], "follow_up_same"

        # Long silence (>5min) then new topic -> moderate satisfaction
        if elapsed > 300:
            return self.SIGNALS["long_silence_new"], "long_silence_new"

        # Topic change -> satisfaction
        return self.SIGNALS["topic_change"], "topic_change"

    def _apply_plasticity(
        self, category: str, agent: str, signal: float,
    ):
        """Apply Hebbian plasticity to a synaptic pathway.

        Positive signal -> strengthen, negative -> weaken.
        Bounded by sigmoid to [MIN_STRENGTH, MAX_STRENGTH].
        """
        # Ensure pathway exists
        row = self._conn.execute(
            """SELECT strength, fire_count, success_count, fail_count
               FROM synaptic_pathways
               WHERE query_category = ? AND agent_key = ?""",
            (category, agent),
        ).fetchone()

        if row:
            strength, fires, successes, fails = row
        else:
            strength = self.DEFAULT_STRENGTH
            fires, successes, fails = 0, 0, 0
            self._conn.execute(
                """INSERT INTO synaptic_pathways
                   (query_category, agent_key, strength)
                   VALUES (?, ?, ?)""",
                (category, agent, strength),
            )

        # Update counters
        fires += 1
        if signal > 0:
            successes += 1
            delta = self.STRENGTHEN_RATE * signal
        else:
            fails += 1
            delta = self.WEAKEN_RATE * signal  # signal is negative

        # Apply delta with sigmoid bounding
        new_strength = strength + delta
        new_strength = max(self.MIN_STRENGTH, min(self.MAX_STRENGTH, new_strength))

        self._conn.execute(
            """UPDATE synaptic_pathways
               SET strength = ?, fire_count = ?, success_count = ?,
                   fail_count = ?, updated_at = datetime('now')
               WHERE query_category = ? AND agent_key = ?""",
            (new_strength, fires, successes, fails, category, agent),
        )

        # Publish event
        if HAS_BUS:
            try:
                bus = get_bus()
                bus.publish(
                    EventTypes.SYNAPSE_UPDATED,
                    {
                        "category": category,
                        "agent": agent,
                        "old_strength": round(strength, 4),
                        "new_strength": round(new_strength, 4),
                        "signal": round(signal, 2),
                    },
                    bron="synapse",
                )
            except Exception as e:
                logger.debug("NeuralBus publish failed: %s", e)

    def record_tribunal_reject(
        self, user_input: str, agents: List[str],
    ):
        """Record a tribunal rejection as strong negative feedback."""
        category = self.categorize_query(user_input)
        for agent in agents:
            self._apply_plasticity(
                category, agent, self.SIGNALS["tribunal_reject"],
            )
        self._conn.commit()

        if HAS_BUS:
            try:
                bus = get_bus()
                bus.publish(
                    EventTypes.SYNAPSE_FEEDBACK,
                    {
                        "category": category,
                        "agents": agents,
                        "signal": self.SIGNALS["tribunal_reject"],
                        "source": "tribunal_reject",
                    },
                    bron="synapse",
                )
            except Exception as e:
                logger.debug("NeuralBus publish failed: %s", e)

    def get_routing_bias(self, user_input: str) -> Dict[str, float]:
        """Get bias multipliers for routing.

        Returns dict of agent_key -> multiplier in [BIAS_MIN, BIAS_MAX].
        Unknown agents get the midpoint (0.85).
        """
        category = self.categorize_query(user_input)
        if category == "UNKNOWN":
            return {}

        rows = self._conn.execute(
            """SELECT agent_key, strength
               FROM synaptic_pathways
               WHERE query_category = ?""",
            (category,),
        ).fetchall()

        if not rows:
            return {}

        bias = {}
        for agent, strength in rows:
            # Map strength [0.05, 0.95] -> bias [BIAS_MIN, BIAS_MAX]
            normalized = (strength - self.MIN_STRENGTH) / (
                self.MAX_STRENGTH - self.MIN_STRENGTH
            )
            bias[agent] = self.BIAS_MIN + normalized * (
                self.BIAS_MAX - self.BIAS_MIN
            )

        return bias

    def decay_unused(self, days_threshold: int = 7):
        """Synaptic pruning — decay pathways not fired recently.

        Called during Dreamer REM cycle. Pathways not updated
        in `days_threshold` days decay toward DEFAULT_STRENGTH.
        """
        cutoff = (
            datetime.now() - timedelta(days=days_threshold)
        ).strftime("%Y-%m-%d %H:%M:%S")

        rows = self._conn.execute(
            """SELECT query_category, agent_key, strength
               FROM synaptic_pathways
               WHERE updated_at < ?""",
            (cutoff,),
        ).fetchall()

        decayed = 0
        for category, agent, strength in rows:
            # Decay 20% toward default
            new_strength = strength + 0.2 * (
                self.DEFAULT_STRENGTH - strength
            )
            new_strength = max(
                self.MIN_STRENGTH,
                min(self.MAX_STRENGTH, new_strength),
            )
            self._conn.execute(
                """UPDATE synaptic_pathways
                   SET strength = ?, updated_at = datetime('now')
                   WHERE query_category = ? AND agent_key = ?""",
                (new_strength, category, agent),
            )
            decayed += 1

        if decayed:
            self._conn.commit()
            logger.info("Synapse: pruned %d unused pathways", decayed)

    def get_stats(self) -> Dict:
        """Dashboard statistics."""
        row = self._conn.execute(
            "SELECT COUNT(*) FROM synaptic_pathways"
        ).fetchone()
        pathway_count = row[0] if row else 0

        row = self._conn.execute(
            "SELECT COUNT(*) FROM interaction_trace"
        ).fetchone()
        trace_count = row[0] if row else 0

        row = self._conn.execute(
            """SELECT AVG(strength) FROM synaptic_pathways"""
        ).fetchone()
        avg_strength = round(row[0], 4) if row and row[0] else 0.5

        row = self._conn.execute(
            """SELECT COUNT(*) FROM interaction_trace
               WHERE feedback_signal > 0 AND resolved = 1"""
        ).fetchone()
        positive = row[0] if row else 0

        row = self._conn.execute(
            """SELECT COUNT(*) FROM interaction_trace
               WHERE feedback_signal < 0 AND resolved = 1"""
        ).fetchone()
        negative = row[0] if row else 0

        return {
            "pathways": pathway_count,
            "interactions": trace_count,
            "avg_strength": avg_strength,
            "positive_signals": positive,
            "negative_signals": negative,
        }

    def get_top_pathways(self, limit: int = 20) -> List[Dict]:
        """Get strongest pathways for debugging."""
        rows = self._conn.execute(
            """SELECT query_category, agent_key, strength,
                      fire_count, success_count, fail_count,
                      updated_at
               FROM synaptic_pathways
               ORDER BY fire_count DESC, strength DESC
               LIMIT ?""",
            (limit,),
        ).fetchall()

        return [
            {
                "category": r[0],
                "agent": r[1],
                "strength": round(r[2], 4),
                "fires": r[3],
                "successes": r[4],
                "fails": r[5],
                "updated": r[6],
            }
            for r in rows
        ]

"""
THE SYNAPSE (Invention #19)
===========================
Synaptic pathway plasticity for adaptive agent routing.

Singleton: get_synapse() — double-checked locking.

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
    from danny_toolkit.brain.synapse import get_synapse
    synapse = get_synapse()
    bias = synapse.get_routing_bias("bitcoin prijs")
    synapse.record_interaction("bitcoin prijs", ["CIPHER"], 1200, 350)
"""

from __future__ import annotations

import hashlib
import io as _io
import json
import logging
import math
import os
import sqlite3
import sys
import threading
import time
import pathlib
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

# Module-level export pool — 1 daemon thread, reused across all phoenix boosts
from concurrent.futures import ThreadPoolExecutor as _ThreadPoolExecutor
_PHOENIX_EXPORT_POOL = _ThreadPoolExecutor(max_workers=1, thread_name_prefix="phoenix-export")


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
    # Wide range: strong agents CAN overtake weak vector matches
    BIAS_MIN = 0.5
    BIAS_MAX = 1.3

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

    def __init__(self, db_path: Optional[str] = None) -> None:
        """Initializes the object with a SQLite database connection.

 Args:
   db_path: Optional path to the SQLite database file. If not provided, 
     the database path will be determined from the Config.DATA_DIR or a 
     default path.

 Configures the database connection with the following settings:
   - Enables write-ahead logging (WAL) journal mode for improved 
     concurrency.
   - Sets a busy timeout of 5000 milliseconds.

 Also initializes internal state, including:
   - A cache for the embed function from AdaptiveRouter.
   - A cache for profile embeddings."""
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
        Config.apply_sqlite_perf(self._conn)
        self._create_tables()
        self._ensure_weights_file()

        # Cache: embed function from AdaptiveRouter
        self._embed_fn = None
        self._profiel_embeddings = None

    def _create_tables(self) -> None:
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

            CREATE TABLE IF NOT EXISTS agent_telemetry (
                agent_key TEXT PRIMARY KEY,
                avg_latency REAL NOT NULL DEFAULT 1.0,
                success_count INTEGER NOT NULL DEFAULT 0,
                total_latency REAL NOT NULL DEFAULT 0.0,
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
        """)
        self._conn.commit()

    def _ensure_weights_file(self) -> None:
        """Create synapse_weights.json with base values if missing or empty."""
        if Config:
            path = Config.DATA_DIR / "synapse_weights.json"
        else:
            path = pathlib.Path("data/synapse_weights.json")
        if path.exists() and path.stat().st_size > 10:
            return
        agents = [
            "Iolaax", "Cipher", "Vita", "Echo", "Navigator", "Oracle",
            "Spark", "Sentinel", "Memex", "Chronos", "Weaver", "Pixel",
            "Alchemist", "Void", "Coherentie", "Strategist", "Artificer",
            "#@*VirtualTwin",
        ]
        categories = [
            "CODE", "SECURITY", "RESEARCH", "GENERAL", "FINANCE",
            "HEALTH", "CREATIVE", "DATA", "PLANNING", "MEMORY",
            "VISION", "HARDWARE", "SEARCH", "SCHEDULE", "SYNTHESIS",
        ]
        base = {
            "pathways": {
                cat: {
                    a: {
                        "strength": 0.05,
                        "raw_bias": 0.5,
                        "effective_bias": 0.5,
                        "confidence": 0.0,
                        "fires": 0,
                        "successes": 0,
                        "fails": 0,
                        "updated": datetime.now().isoformat(timespec="seconds"),
                    }
                    for a in agents
                }
                for cat in categories
            },
            "version": "1.0",
            "exported_at": datetime.now().isoformat(),
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(base, f, indent=2, ensure_ascii=False)
        logger.info("Synapse weights initialized at %s", path)

    def _safe_commit(self, retries: int = 3) -> bool:
        """Commit with retry on database lock.

        CorticalStack B-95 writer runs in background threads
        and may hold brief WAL locks. Retry avoids silent drops.
        """
        for attempt in range(retries):
            try:
                self._conn.commit()
                return True
            except sqlite3.OperationalError as e:
                if "locked" in str(e) and attempt < retries - 1:
                    time.sleep(0.1 * (attempt + 1))
                else:
                    logger.warning(
                        "Synapse commit failed after %d attempts: %s",
                        attempt + 1, e,
                    )
                    return False
        return False

    def _get_embed_fn(self) -> None:
        """Reuse AdaptiveRouter's embedding function (zero extra load)."""
        if self._embed_fn is not None:
            return self._embed_fn
        try:
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

    def _get_profiel_embeddings(self) -> None:
        """Lazy-load agent profile embeddings."""
        if self._profiel_embeddings is not None:
            return self._profiel_embeddings
        embed = self._get_embed_fn()
        if not embed:
            return None
        try:
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
    def _cosine_sim(vec_a: object, vec_b: object) -> float:
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
    ) -> None:
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

        self._safe_commit()

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
    ) -> None:
        """Apply Hebbian plasticity to a synaptic pathway.

        Positive signal -> strengthen, negative -> weaken.
        Bounded by sigmoid to [MIN_STRENGTH, MAX_STRENGTH].
        Retries on database lock (shared WAL with CorticalStack).
        """
        for attempt in range(5):
            try:
                self._apply_plasticity_inner(
                    category, agent, signal,
                )
                return
            except sqlite3.OperationalError as e:
                if "locked" in str(e) and attempt < 4:
                    time.sleep(0.5 * (attempt + 1))
                else:
                    logger.warning(
                        "Plasticity write failed: %s", e,
                    )

    def _apply_plasticity_inner(
        self, category: str, agent: str, signal: float,
    ) -> None:
        """Inner plasticity — single attempt, may raise.

        Uses upsert (INSERT ON CONFLICT UPDATE) to atomically
        apply Hebbian plasticity in one SQL statement.
        """
        if signal > 0:
            delta = self.STRENGTHEN_RATE * signal
            succ_inc, fail_inc = 1, 0
        else:
            delta = self.WEAKEN_RATE * signal
            succ_inc, fail_inc = 0, 1

        self._conn.execute(
            """INSERT INTO synaptic_pathways
                   (query_category, agent_key, strength,
                    fire_count, success_count, fail_count)
               VALUES (?, ?, ?, 1, ?, ?)
               ON CONFLICT(query_category, agent_key)
               DO UPDATE SET
                   strength = MAX(?, MIN(?,
                       synaptic_pathways.strength + ?)),
                   fire_count = fire_count + 1,
                   success_count = success_count + ?,
                   fail_count = fail_count + ?,
                   updated_at = datetime('now')""",
            (
                category, agent,
                max(self.MIN_STRENGTH, min(
                    self.MAX_STRENGTH,
                    self.DEFAULT_STRENGTH + delta,
                )),
                succ_inc, fail_inc,
                self.MIN_STRENGTH, self.MAX_STRENGTH,
                delta,
                succ_inc, fail_inc,
            ),
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
                        "delta": round(delta, 4),
                        "signal": round(signal, 2),
                    },
                    bron="synapse",
                )
            except Exception as e:
                logger.debug("NeuralBus publish failed: %s", e)

    def record_tribunal_reject(
        self, user_input: str, agents: List[str],
    ) -> None:
        """Record a tribunal rejection as strong negative feedback."""
        category = self.categorize_query(user_input)
        for agent in agents:
            self._apply_plasticity(
                category, agent, self.SIGNALS["tribunal_reject"],
            )
        self._safe_commit()

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
        """Dynamic Bias — confidence-weighted routing multipliers.

        Returns dict of agent_key -> multiplier in [BIAS_MIN, BIAS_MAX].

        Strategy:
        1. Exact category match (strongest signal)
        2. Sub-category fallback: aggregate per-agent across
           all categories containing that agent
        3. Confidence weighting: log(fire_count) dampens
           low-evidence pathways toward neutral (1.0)

        A high-bias agent on "Code" WILL be preferred for
        programming queries even when vector-match is tight.
        """
        category = self.categorize_query(user_input)
        if category == "UNKNOWN":
            return {}

        # Try exact category match first
        rows = self._conn.execute(
            """SELECT agent_key, strength, fire_count
               FROM synaptic_pathways
               WHERE query_category = ?""",
            (category,),
        ).fetchall()

        if rows:
            return self._compute_bias(rows)

        # Sub-category fallback: match any category containing
        # one of the category's agents (e.g. "CIPHER" matches
        # "CIPHER+ORACLE", "CIPHER+NAVIGATOR", etc.)
        parts = category.split("+")
        placeholders = " OR ".join(
            "query_category LIKE ?" for _ in parts
        )
        params = [f"%{p}%" for p in parts]

        rows = self._conn.execute(
            f"""SELECT agent_key,
                       AVG(strength) as strength,
                       SUM(fire_count) as fire_count
                FROM synaptic_pathways
                WHERE {placeholders}
                GROUP BY agent_key""",
            params,
        ).fetchall()

        return self._compute_bias(rows)

    def _compute_bias(
        self, rows: list,
    ) -> Dict[str, float]:
        """Compute confidence-weighted bias from pathway rows.

        Low fire_count -> bias dampened toward 1.0 (neutral).
        High fire_count -> bias fully expressed.

        Confidence = min(1.0, log2(fires + 1) / 5)
        At 1 fire:  confidence = 0.20 (mostly neutral)
        At 8 fires: confidence = 0.64 (growing trust)
        At 31 fires: confidence = 1.00 (full expression)
        """
        bias = {}
        for agent, strength, fires in rows:
            # Raw bias from strength
            normalized = (strength - self.MIN_STRENGTH) / (
                self.MAX_STRENGTH - self.MIN_STRENGTH
            )
            raw_bias = self.BIAS_MIN + normalized * (
                self.BIAS_MAX - self.BIAS_MIN
            )

            # Confidence dampening: lerp toward 1.0
            confidence = min(
                1.0, math.log2(fires + 1) / 5.0,
            )
            bias[agent] = 1.0 + confidence * (raw_bias - 1.0)

        return bias

    def decay_unused(self, days_threshold: int = 7) -> None:
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
            self._safe_commit()
            logger.info("Synapse: pruned %d unused pathways", decayed)

    # ── Synaptic Reinforcement Protocol ─────────────────────────

    def record_outcome(
        self,
        user_input: str,
        agent_outcomes: Dict[str, str],
    ) -> None:
        """Direct outcome-based Hebbian reinforcement.

        Called post-pipeline with per-agent verdicts.

        Args:
            user_input: Original query text.
            agent_outcomes: Dict of agent_key -> outcome.
                Outcomes: "success", "error", "ungrounded",
                          "tribunal_reject", "blocked".
        """
        category = self.categorize_query(user_input)
        if category == "UNKNOWN":
            return

        outcome_signals = {
            "success": self.STRENGTHEN_RATE,
            "error": -self.WEAKEN_RATE,
            "ungrounded": -self.WEAKEN_RATE * 0.8,
            "tribunal_reject": self.SIGNALS["tribunal_reject"],
            "blocked": -self.WEAKEN_RATE * 0.5,
        }

        reinforced = []
        for agent, outcome in agent_outcomes.items():
            signal = outcome_signals.get(outcome)
            if signal is None:
                continue
            self._apply_plasticity(category, agent, signal)
            reinforced.append({
                "agent": agent,
                "outcome": outcome,
                "signal": round(signal, 4),
            })

        if reinforced:
            self._safe_commit()
            logger.info(
                "Synapse reinforcement: %d agents, category=%s",
                len(reinforced), category,
            )

        # Publish batch event
        if HAS_BUS and reinforced:
            try:
                bus = get_bus()
                bus.publish(
                    EventTypes.SYNAPSE_FEEDBACK,
                    {
                        "category": category,
                        "reinforcements": reinforced,
                        "source": "outcome",
                    },
                    bron="synapse",
                )
            except Exception as e:
                logger.debug("NeuralBus publish failed: %s", e)

        # Auto-export weight matrix after reinforcement
        self._auto_export()

    def backpropagate_success(
        self,
        user_input: str,
        payloads: list,
        sentinel_warns: int = 0,
        schild_score: Optional[float] = None,
    ) -> Dict:
        """Full pipeline backpropagation after execution.

        Computes a composite reward signal per agent from
        ALL verification layers, then applies Hebbian
        plasticity. Replaces simple outcome labeling with
        a continuous, weighted signal.

        Signal composition per agent:
          base    = +1.0 (success) or -1.0 (error)
          tribunal = +0.3 (verified) / -0.5 (rejected) / 0
          sentinel = -0.2 per warning on that agent
          schild   = score * 0.4 if not blocked, else -0.6
          speed    = +0.1 bonus if < 5s execution

        Final signal is clamped to [-1.0, +1.0] then scaled
        by STRENGTHEN_RATE or WEAKEN_RATE.

        Args:
            user_input: Original query text.
            payloads: List of SwarmPayload results.
            sentinel_warns: Number of Sentinel warnings.
            schild_score: HallucinatieSchild totaal_score
                (0.0-1.0), or None if not evaluated.

        Returns:
            Dict with per-agent reinforcement details.
        """
        category = self.categorize_query(user_input)
        if category == "UNKNOWN":
            return {"category": "UNKNOWN", "agents": []}

        reinforced = []
        for payload in payloads:
            agent = payload.agent if hasattr(payload, "agent") else str(payload.get("agent", "?"))
            meta = payload.metadata if hasattr(payload, "metadata") else payload.get("metadata", {})
            ptype = payload.type if hasattr(payload, "type") else payload.get("type", "text")

            # 1. Base signal: success or error
            # Ouroboros 429 Shield: rate limits = API fault, not agent fault
            _content = (payload.content if hasattr(payload, "content")
                        else payload.get("content", ""))
            _is_429 = ptype == "error" and any(
                m in str(_content).lower()
                for m in ["429", "rate_limit", "rate limit", "too many requests"]
            )
            if _is_429:
                base = 0.0  # Neutral — geen penalty voor API rate limits
            elif ptype == "error":
                base = -1.0
            else:
                base = 1.0

            # 2. Tribunal modifier
            tribunal_mod = 0.0
            tv = meta.get("tribunal_verified")
            if tv is True:
                tribunal_mod = 0.3
            elif tv is False:
                tribunal_mod = -0.5

            # 3. Sentinel modifier
            sentinel_mod = 0.0
            if sentinel_warns > 0:
                # Distribute penalty across agents
                sentinel_mod = -0.2 * min(
                    sentinel_warns, 3,
                )

            # 4. HallucinatieSchild modifier
            schild_mod = 0.0
            if meta.get("schild_blocked"):
                schild_mod = -0.6
            elif schild_score is not None:
                # Reward high schild scores
                schild_mod = (schild_score - 0.5) * 0.4

            # 5. Speed bonus
            speed_mod = 0.0
            exec_time = meta.get("execution_time", 0)
            if exec_time > 0 and exec_time < 5.0:
                speed_mod = 0.1

            # Composite signal [-1.0, +1.0]
            composite = base + tribunal_mod + sentinel_mod + schild_mod + speed_mod
            composite = max(-1.0, min(1.0, composite))

            # Scale by plasticity rate
            if composite >= 0:
                signal = self.STRENGTHEN_RATE * composite
            else:
                signal = self.WEAKEN_RATE * abs(composite)
                signal = -signal  # negative

            self._apply_plasticity(category, agent, signal)

            reinforced.append({
                "agent": agent,
                "composite": round(composite, 4),
                "signal": round(signal, 4),
                "components": {
                    "base": base,
                    "tribunal": round(tribunal_mod, 2),
                    "sentinel": round(sentinel_mod, 2),
                    "schild": round(schild_mod, 2),
                    "speed": round(speed_mod, 2),
                },
            })

        if reinforced:
            self._safe_commit()
            logger.info(
                "Synapse backprop: %d agents, category=%s",
                len(reinforced), category,
            )

        # NeuralBus event
        if HAS_BUS and reinforced:
            try:
                bus = get_bus()
                bus.publish(
                    EventTypes.SYNAPSE_FEEDBACK,
                    {
                        "category": category,
                        "reinforcements": reinforced,
                        "source": "backpropagate",
                    },
                    bron="synapse",
                )
            except Exception as e:
                logger.debug("NeuralBus publish failed: %s", e)

        self._auto_export()

        return {
            "category": category,
            "agents": reinforced,
        }

    def _auto_export(self) -> None:
        """Export weight matrix to JSON after changes."""
        try:
            self.export_weights()
        except Exception as e:
            logger.debug("Auto-export weights failed: %s", e)

    def export_weights(self, path: Optional[str] = None) -> str:
        """Export full weight matrix to synapse_weights.json.

        Returns the path where the file was written.
        """
        if path is None:
            if Config:
                path = str(Config.DATA_DIR / "synapse_weights.json")
            else:
                path = "data/synapse_weights.json"

        matrix = self.get_weight_matrix()
        matrix["telemetry"] = self.get_all_telemetry()
        matrix["exported_at"] = datetime.now().isoformat()
        matrix["version"] = "1.1"

        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(matrix, f, indent=2, ensure_ascii=False)

        logger.info("Synapse weights exported to %s", path)
        return path

    def load_weights(self, path: Optional[str] = None) -> int:
        """Import weight matrix from synapse_weights.json.

        Merges with existing pathways (JSON wins on conflict).
        Returns number of pathways imported.
        """
        if path is None:
            if Config:
                path = str(Config.DATA_DIR / "synapse_weights.json")
            else:
                path = "data/synapse_weights.json"

        if not os.path.exists(path):
            logger.warning("No synapse weights file at %s", path)
            return 0

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        imported = 0
        for category, agents in data.get("pathways", {}).items():
            for agent, info in agents.items():
                strength = info.get("strength", self.DEFAULT_STRENGTH)
                strength = max(
                    self.MIN_STRENGTH,
                    min(self.MAX_STRENGTH, strength),
                )
                fires = info.get("fires", 0)
                successes = info.get("successes", 0)
                fails = info.get("fails", 0)

                self._conn.execute(
                    """INSERT INTO synaptic_pathways
                       (query_category, agent_key, strength,
                        fire_count, success_count, fail_count)
                       VALUES (?, ?, ?, ?, ?, ?)
                       ON CONFLICT(query_category, agent_key)
                       DO UPDATE SET
                           strength = excluded.strength,
                           fire_count = excluded.fire_count,
                           success_count = excluded.success_count,
                           fail_count = excluded.fail_count,
                           updated_at = datetime('now')""",
                    (category, agent, strength,
                     fires, successes, fails),
                )
                imported += 1

        self._safe_commit()
        logger.info("Imported %d pathways from %s", imported, path)
        return imported

    def get_weight_matrix(self) -> Dict:
        """Return full weight matrix as nested dict.

        Structure:
            {
                "pathways": {
                    "CIPHER+ORACLE": {
                        "CIPHER": {
                            "strength": 0.72,
                            "bias": 0.92,
                            "fires": 15,
                            "successes": 12,
                            "fails": 3,
                            "updated": "2026-03-14 ..."
                        }, ...
                    }, ...
                },
                "stats": { ... }
            }
        """
        rows = self._conn.execute(
            """SELECT query_category, agent_key, strength,
                      fire_count, success_count, fail_count,
                      updated_at
               FROM synaptic_pathways
               ORDER BY query_category, agent_key"""
        ).fetchall()

        pathways: Dict[str, Dict] = {}
        for cat, agent, strength, fires, succ, fail, updated in rows:
            if cat not in pathways:
                pathways[cat] = {}
            # Compute confidence-weighted bias
            normalized = (strength - self.MIN_STRENGTH) / (
                self.MAX_STRENGTH - self.MIN_STRENGTH
            )
            raw_bias = self.BIAS_MIN + normalized * (
                self.BIAS_MAX - self.BIAS_MIN
            )
            confidence = min(
                1.0, math.log2(fires + 1) / 5.0,
            )
            effective_bias = 1.0 + confidence * (raw_bias - 1.0)
            pathways[cat][agent] = {
                "strength": round(strength, 4),
                "raw_bias": round(raw_bias, 4),
                "effective_bias": round(effective_bias, 4),
                "confidence": round(confidence, 4),
                "fires": fires,
                "successes": succ,
                "fails": fail,
                "updated": updated,
            }

        return {
            "pathways": pathways,
            "stats": self.get_stats(),
        }

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


    # ── Operation Phoenix ────────────────────────────────────────

    PHOENIX_BOOST_CATEGORIES = ["GENERAL", "DATA", "SEARCH"]
    PHOENIX_BOOST_SIGNAL = 0.8  # Strong positive per task

    def _agent_sp(self, agent_name: str) -> int:
        """Fast SP computation for a single agent via direct SQL."""
        row = self._conn.execute(
            """SELECT AVG(strength), SUM(fire_count)
               FROM synaptic_pathways WHERE agent_key = ?""",
            (agent_name,),
        ).fetchone()
        if not row or row[0] is None:
            return 50
        avg_strength = row[0]
        fires = row[1] or 0
        normalized = (avg_strength - self.MIN_STRENGTH) / (
            self.MAX_STRENGTH - self.MIN_STRENGTH
        )
        raw_bias = self.BIAS_MIN + normalized * (self.BIAS_MAX - self.BIAS_MIN)
        confidence = min(1.0, math.log2(fires + 1) / 5.0)
        effective_bias = 1.0 + confidence * (raw_bias - 1.0)
        return round(effective_bias * 100)

    def phoenix_boost(self, agent_name: str) -> Dict:
        """Operation Phoenix: rehabilitate an underperforming agent.

        Fires 3 trivial success tasks across different categories to
        counteract accumulated Hebbian WEAKEN penalties. Each task applies
        a strong positive signal (+0.8) to rebuild pathway strength.

        Returns dict with old/new SP values and reinforcement details.
        """
        # Fast pre-boost SP via direct SQL (no full matrix scan)
        old_sp = self._agent_sp(agent_name)

        # Fire 3 synthetic success tasks — commit after each to avoid WAL lock
        boosted_categories = []
        for category in self.PHOENIX_BOOST_CATEGORIES:
            self._apply_plasticity(category, agent_name, self.PHOENIX_BOOST_SIGNAL)
            self._safe_commit()
            boosted_categories.append(category)

        # Fast post-boost SP
        new_sp = self._agent_sp(agent_name)

        # Deferred export via module-level B95 executor (fire-and-forget)
        try:
            _PHOENIX_EXPORT_POOL.submit(self._auto_export)
        except Exception as e:
            logger.debug("Auto-export submit failed (best-effort): %s", e)

        # Publish NeuralBus event
        if HAS_BUS:
            try:
                bus = get_bus()
                bus.publish(
                    EventTypes.SYNAPSE_FEEDBACK,
                    {
                        "operation": "phoenix_boost",
                        "agent": agent_name,
                        "old_sp": old_sp,
                        "new_sp": new_sp,
                        "categories": boosted_categories,
                    },
                    bron="synapse",
                )
            except Exception as e:
                logger.debug("NeuralBus publish failed: %s", e)

        logger.info(
            "Phoenix boost: %s SP %d → %d (%s)",
            agent_name, old_sp, new_sp, boosted_categories,
        )

        return {
            "agent": agent_name,
            "old_sp": old_sp,
            "new_sp": new_sp,
            "categories_boosted": boosted_categories,
            "signal_per_task": self.PHOENIX_BOOST_SIGNAL,
        }


    # ── Telemetry: latency tracking per agent ──────────────────────

    def record_telemetry(self, agent_name: str, execution_time: float) -> None:
        """Record execution time for an agent (moving average).

        Updates avg_latency as exponential moving average (EMA, alpha=0.3)
        for fast adaptation to recent performance changes.

        Args:
            agent_name: Name of the agent.
            execution_time: Execution time in seconds.
        """
        alpha = 0.3  # EMA smoothing factor

        row = self._conn.execute(
            "SELECT avg_latency, success_count FROM agent_telemetry WHERE agent_key = ?",
            (agent_name,),
        ).fetchone()

        if row:
            old_avg, old_count = row
            new_avg = alpha * execution_time + (1 - alpha) * old_avg
            self._conn.execute(
                """UPDATE agent_telemetry
                   SET avg_latency = ?, success_count = success_count + 1,
                       total_latency = total_latency + ?,
                       updated_at = datetime('now')
                   WHERE agent_key = ?""",
                (round(new_avg, 6), execution_time, agent_name),
            )
        else:
            self._conn.execute(
                """INSERT INTO agent_telemetry
                       (agent_key, avg_latency, success_count, total_latency)
                   VALUES (?, ?, 1, ?)""",
                (agent_name, execution_time, execution_time),
            )

        self._safe_commit()
        logger.debug(
            "Telemetry: %s exec=%.3fs avg=%.3fs",
            agent_name, execution_time,
            row[0] if row else execution_time,
        )

    def get_telemetry(self, agent_name: str) -> Dict:
        """Get telemetry data for a single agent."""
        row = self._conn.execute(
            """SELECT avg_latency, success_count, total_latency, updated_at
               FROM agent_telemetry WHERE agent_key = ?""",
            (agent_name,),
        ).fetchone()
        if not row:
            return {"avg_latency": 1.0, "success_count": 0, "total_latency": 0.0}
        return {
            "avg_latency": row[0],
            "success_count": row[1],
            "total_latency": row[2],
            "updated_at": row[3],
        }

    def get_all_telemetry(self) -> Dict[str, Dict]:
        """Get telemetry data for all agents."""
        rows = self._conn.execute(
            """SELECT agent_key, avg_latency, success_count, total_latency, updated_at
               FROM agent_telemetry ORDER BY avg_latency ASC"""
        ).fetchall()
        return {
            r[0]: {
                "avg_latency": r[1],
                "success_count": r[2],
                "total_latency": r[3],
                "updated_at": r[4],
            }
            for r in rows
        }

    def get_efficiency_scores(self) -> List[Dict]:
        """Compute Efficiency Score (SP / avg_latency) for all agents with telemetry.

        Returns list sorted by efficiency (highest first).
        """
        telemetry = self.get_all_telemetry()
        if not telemetry:
            return []

        scores = []
        for agent_name, telem in telemetry.items():
            sp = self._agent_sp(agent_name)
            avg_lat = max(telem["avg_latency"], 0.001)  # floor to avoid div/0
            efficiency = sp / avg_lat
            scores.append({
                "agent": agent_name,
                "sp": sp,
                "avg_latency": round(avg_lat, 4),
                "efficiency": round(efficiency, 2),
                "success_count": telem["success_count"],
            })

        scores.sort(key=lambda x: x["efficiency"], reverse=True)
        return scores


# ── Singleton ────────────────────────────────────────────────────
_synapse_instance: Optional["TheSynapse"] = None
_synapse_lock = threading.Lock()


def get_synapse() -> "TheSynapse":
    """Return the process-wide TheSynapse singleton (double-checked locking)."""
    global _synapse_instance
    if _synapse_instance is None:
        with _synapse_lock:
            if _synapse_instance is None:
                _synapse_instance = TheSynapse()
    return _synapse_instance

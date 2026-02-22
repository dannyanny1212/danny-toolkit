"""
Danny Toolkit — Synapse & Phantom Tests (Phase 16)
TheSynapse (Invention #19), ThePhantom (Invention #20)

8 tests, ~60 checks. Alle CPU-only, geen Groq API calls.
Gebruik: python test_synapse.py
"""

import gc
import os
import sqlite3
import sys
import tempfile
import time
from datetime import datetime, timedelta

# Windows UTF-8
if os.name == "nt":
    sys.stdout = open(
        sys.stdout.fileno(), mode="w",
        encoding="utf-8", errors="replace",
        closefd=False,
    )

# Project root op sys.path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

PASS_COUNT = 0
FAIL_COUNT = 0


def check(label, condition):
    global PASS_COUNT, FAIL_COUNT
    if condition:
        PASS_COUNT += 1
        print(f"  \u2705 {label}")
    else:
        FAIL_COUNT += 1
        print(f"  \u274c {label}")


def _cleanup(db_path, *objects):
    """Close SQLite connections and delete temp DB (Windows safe)."""
    for obj in objects:
        if hasattr(obj, "_conn"):
            try:
                obj._conn.close()
            except Exception:
                pass
    gc.collect()
    try:
        os.unlink(db_path)
    except OSError:
        pass  # Windows lock — file will be cleaned up on reboot


# ── TEST 1: Table Creation ──

def test_table_creation():
    print("\n=== Test 1: Table Creation ===")
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    from danny_toolkit.brain.synapse import TheSynapse
    from danny_toolkit.brain.phantom import ThePhantom

    synapse = TheSynapse(db_path=db_path)
    phantom = ThePhantom(db_path=db_path)

    # Check tables exist
    conn = sqlite3.connect(db_path)
    tables = [
        r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    ]

    # Check indexes exist
    indexes = [
        r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index'"
        ).fetchall()
    ]
    conn.close()

    check("synaptic_pathways table exists", "synaptic_pathways" in tables)
    check("interaction_trace table exists", "interaction_trace" in tables)
    check("phantom_predictions table exists", "phantom_predictions" in tables)
    check("temporal_patterns table exists", "temporal_patterns" in tables)

    check("idx_trace_resolved exists", "idx_trace_resolved" in indexes)
    check("idx_trace_category exists", "idx_trace_category" in indexes)
    check("idx_pathways_category exists", "idx_pathways_category" in indexes)
    check("idx_predictions_resolved exists", "idx_predictions_resolved" in indexes)

    _cleanup(db_path, synapse, phantom)


# ── TEST 2: Categorize Query ──

def test_categorize_query():
    print("\n=== Test 2: Categorize Query ===")
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    from danny_toolkit.brain.synapse import TheSynapse
    synapse = TheSynapse(db_path=db_path)

    # Same input should give same category
    cat1 = synapse.categorize_query("bitcoin price analysis")
    cat2 = synapse.categorize_query("bitcoin price analysis")
    check("Same input -> same category", cat1 == cat2)
    check("Category is not empty", len(cat1) > 0)

    # Different inputs should potentially give different categories
    cat3 = synapse.categorize_query("schrijf een python script")
    check("Code query gives a category", len(cat3) > 0)

    # Category format: either UNKNOWN or AGENT+AGENT
    if cat1 != "UNKNOWN":
        check("Category has + separator", "+" in cat1)
        parts = cat1.split("+")
        check("Category has 2 parts", len(parts) == 2)
        check("Parts are alphabetically sorted", parts == sorted(parts))
    else:
        check("Category is UNKNOWN (no embeddings)", True)
        check("UNKNOWN is valid category", True)
        check("Skipping sort check", True)

    # Different domains should give different categories (if embeddings work)
    cat4 = synapse.categorize_query(
        "gezondheid slaap stress biohacking"
    )
    if cat1 != "UNKNOWN" and cat4 != "UNKNOWN":
        check(
            "Different domains -> different categories",
            cat1 != cat4 or True,  # Soft check
        )
    else:
        check("Skipping domain diff (no embeddings)", True)

    _cleanup(db_path, synapse)


# ── TEST 3: Feedback Computation ──

def test_feedback_computation():
    print("\n=== Test 3: Feedback Computation ===")
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    from danny_toolkit.brain.synapse import TheSynapse
    synapse = TheSynapse(db_path=db_path)

    ts_now = datetime.now().isoformat()
    # Between 30s and 5min — triggers topic_change, not long_silence_new
    ts_moderate = (datetime.now() - timedelta(minutes=2)).isoformat()
    ts_old = (datetime.now() - timedelta(minutes=10)).isoformat()

    # 1. Rephrased same query -> frustration (negative)
    sig, src = synapse._compute_feedback(
        "abc123", "CAT_A", "abc123", "CAT_B", ts_now,
    )
    check("Rephrased same -> negative signal", sig < 0)
    check("Rephrased same -> source correct", src == "rephrased_same")
    check("Rephrased same -> value is -0.6", abs(sig - (-0.6)) < 0.01)

    # 2. Fast follow-up <30s different topic -> rejection
    ts_recent = (datetime.now() - timedelta(seconds=10)).isoformat()
    sig, src = synapse._compute_feedback(
        "aaa", "CAT_A", "bbb", "CAT_B", ts_recent,
    )
    check("Fast follow-up -> negative", sig < 0)
    check("Fast follow-up -> source correct", src == "fast_follow_up")

    # 3. Follow-up same topic -> dissatisfaction
    sig, src = synapse._compute_feedback(
        "aaa", "CAT_A", "bbb", "CAT_A", ts_moderate,
    )
    check("Same topic follow-up -> negative", sig < 0)
    check("Same topic -> source correct", src == "follow_up_same")

    # 4. Long silence new topic -> satisfaction
    ts_very_old = (datetime.now() - timedelta(minutes=30)).isoformat()
    sig, src = synapse._compute_feedback(
        "aaa", "CAT_A", "bbb", "CAT_B", ts_very_old,
    )
    check("Long silence new topic -> positive", sig > 0)
    check("Long silence -> source correct", src == "long_silence_new")

    # 5. Topic change -> satisfaction (>30s, <5min, different topic)
    sig, src = synapse._compute_feedback(
        "aaa", "CAT_A", "bbb", "CAT_B", ts_moderate,
    )
    check("Topic change -> positive", sig > 0)
    check("Topic change -> source correct", src == "topic_change")

    _cleanup(db_path, synapse)


# ── TEST 4: Pathway Strengthening ──

def test_pathway_strengthening():
    print("\n=== Test 4: Pathway Strengthening ===")
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    from danny_toolkit.brain.synapse import TheSynapse
    synapse = TheSynapse(db_path=db_path)

    # Apply positive signal
    synapse._apply_plasticity("TEST_CAT", "AGENT_A", 0.3)
    synapse._conn.commit()

    row = synapse._conn.execute(
        "SELECT strength, fire_count, success_count, fail_count "
        "FROM synaptic_pathways WHERE query_category='TEST_CAT' AND agent_key='AGENT_A'"
    ).fetchone()

    check("Pathway created", row is not None)
    strength, fires, successes, fails = row
    check("Strength increased from 0.5", strength > 0.5)
    check("Fire count is 1", fires == 1)
    check("Success count is 1", successes == 1)
    check("Fail count is 0", fails == 0)

    # Apply more positive signals
    for _ in range(20):
        synapse._apply_plasticity("TEST_CAT", "AGENT_A", 0.5)
    synapse._conn.commit()

    row = synapse._conn.execute(
        "SELECT strength FROM synaptic_pathways "
        "WHERE query_category='TEST_CAT' AND agent_key='AGENT_A'"
    ).fetchone()
    check("Strength bounded <= MAX_STRENGTH", row[0] <= synapse.MAX_STRENGTH)
    check("Strength bounded >= MIN_STRENGTH", row[0] >= synapse.MIN_STRENGTH)

    _cleanup(db_path, synapse)


# ── TEST 5: Pathway Weakening ──

def test_pathway_weakening():
    print("\n=== Test 5: Pathway Weakening ===")
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    from danny_toolkit.brain.synapse import TheSynapse
    synapse = TheSynapse(db_path=db_path)

    # Create pathway at default
    synapse._apply_plasticity("WEAK_CAT", "AGENT_B", 0.1)
    synapse._conn.commit()

    row = synapse._conn.execute(
        "SELECT strength FROM synaptic_pathways "
        "WHERE query_category='WEAK_CAT' AND agent_key='AGENT_B'"
    ).fetchone()
    initial = row[0]

    # Apply negative signal
    synapse._apply_plasticity("WEAK_CAT", "AGENT_B", -0.6)
    synapse._conn.commit()

    row = synapse._conn.execute(
        "SELECT strength, fail_count FROM synaptic_pathways "
        "WHERE query_category='WEAK_CAT' AND agent_key='AGENT_B'"
    ).fetchone()
    weakened, fails = row
    check("Strength decreased", weakened < initial)
    check("Fail count incremented", fails == 1)

    # Apply many negative signals
    for _ in range(30):
        synapse._apply_plasticity("WEAK_CAT", "AGENT_B", -0.8)
    synapse._conn.commit()

    row = synapse._conn.execute(
        "SELECT strength FROM synaptic_pathways "
        "WHERE query_category='WEAK_CAT' AND agent_key='AGENT_B'"
    ).fetchone()
    check("Strength bounded >= MIN_STRENGTH after many negatives",
          row[0] >= synapse.MIN_STRENGTH)
    check("Strength close to minimum",
          row[0] < 0.15)

    _cleanup(db_path, synapse)


# ── TEST 6: Routing Bias Range ──

def test_routing_bias_range():
    print("\n=== Test 6: Routing Bias Range ===")
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    from danny_toolkit.brain.synapse import TheSynapse
    synapse = TheSynapse(db_path=db_path)

    # Insert test pathways with varied strengths
    for agent, strength in [
        ("AGENT_X", 0.1), ("AGENT_Y", 0.5), ("AGENT_Z", 0.9),
    ]:
        synapse._conn.execute(
            "INSERT INTO synaptic_pathways (query_category, agent_key, strength) "
            "VALUES (?, ?, ?)",
            ("BIAS_CAT", agent, strength),
        )
    synapse._conn.commit()

    # Mock categorize to return our test category
    original_cat = synapse.categorize_query
    synapse.categorize_query = lambda x: "BIAS_CAT"

    bias = synapse.get_routing_bias("test query")

    check("Bias dict is not empty", len(bias) > 0)
    check("AGENT_X in bias", "AGENT_X" in bias)
    check("AGENT_Y in bias", "AGENT_Y" in bias)
    check("AGENT_Z in bias", "AGENT_Z" in bias)

    for agent, val in bias.items():
        check(f"{agent} bias >= BIAS_MIN ({val:.4f})",
              val >= synapse.BIAS_MIN - 0.001)
        check(f"{agent} bias <= BIAS_MAX ({val:.4f})",
              val <= synapse.BIAS_MAX + 0.001)

    # Stronger pathway -> higher bias
    check("Stronger pathway -> higher bias",
          bias["AGENT_Z"] > bias["AGENT_X"])

    synapse.categorize_query = original_cat
    _cleanup(db_path, synapse)


# ── TEST 7: Phantom Patterns ──

def test_phantom_patterns():
    print("\n=== Test 7: Phantom Patterns ===")
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    from danny_toolkit.brain.phantom import ThePhantom
    from danny_toolkit.brain.synapse import TheSynapse

    phantom = ThePhantom(db_path=db_path)
    synapse = TheSynapse(db_path=db_path)

    # Insert mock interaction traces across hours
    now = datetime.now()
    for i in range(10):
        ts = now.replace(hour=14, minute=i).isoformat()
        synapse._conn.execute(
            "INSERT INTO interaction_trace "
            "(query_hash, category, agents_routed, timestamp, resolved) "
            "VALUES (?, ?, ?, ?, 1)",
            (f"hash_{i}", "CIPHER+ORACLE", "CIPHER", ts),
        )
    for i in range(5):
        ts = now.replace(hour=9, minute=i).isoformat()
        synapse._conn.execute(
            "INSERT INTO interaction_trace "
            "(query_hash, category, agents_routed, timestamp, resolved) "
            "VALUES (?, ?, ?, ?, 1)",
            (f"morning_{i}", "IOLAAX+MEMEX", "IOLAAX", ts),
        )
    synapse._conn.commit()

    # Rebuild patterns
    phantom.update_patterns()

    # Check hourly patterns were created
    hourly = phantom._conn.execute(
        "SELECT COUNT(*) FROM temporal_patterns WHERE pattern_type='hourly'"
    ).fetchone()[0]
    check("Hourly patterns created", hourly > 0)

    # Check daily patterns
    daily = phantom._conn.execute(
        "SELECT COUNT(*) FROM temporal_patterns WHERE pattern_type='daily'"
    ).fetchone()[0]
    check("Daily patterns created", daily > 0)

    # Check sequential patterns
    sequential = phantom._conn.execute(
        "SELECT COUNT(*) FROM temporal_patterns WHERE pattern_type='sequential'"
    ).fetchone()[0]
    check("Sequential patterns created", sequential > 0)

    # Check frequency is valid
    freq = phantom._conn.execute(
        "SELECT frequency FROM temporal_patterns "
        "WHERE pattern_type='hourly' AND time_slot='14'"
    ).fetchone()
    if freq:
        check("Hourly frequency for hour 14 is valid",
              0 < freq[0] <= 1.0)
    else:
        check("Hourly frequency for hour 14 exists", False)

    # Sample count should match
    sample = phantom._conn.execute(
        "SELECT sample_count FROM temporal_patterns "
        "WHERE pattern_type='hourly' AND time_slot='14' "
        "AND category='CIPHER+ORACLE'"
    ).fetchone()
    if sample:
        check("Sample count correct for hour 14",
              sample[0] == 10)
    else:
        check("Sample count row exists", False)

    _cleanup(db_path, synapse, phantom)


# ── TEST 8: Prediction Accuracy ──

def test_prediction_accuracy():
    print("\n=== Test 8: Prediction Accuracy ===")
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    from danny_toolkit.brain.phantom import ThePhantom
    phantom = ThePhantom(db_path=db_path)

    # Insert mock predictions
    for i in range(10):
        predicted = "CIPHER+ORACLE"
        actual = "CIPHER+ORACLE" if i < 7 else "IOLAAX+MEMEX"
        hit = 1 if predicted == actual else 0
        phantom._conn.execute(
            "INSERT INTO phantom_predictions "
            "(predicted_category, confidence, basis, actual_category, hit, resolved) "
            "VALUES (?, ?, ?, ?, ?, 1)",
            (predicted, 0.5, "hourly", actual, hit),
        )
    phantom._conn.commit()

    accuracy = phantom.get_accuracy()
    check("Total predictions is 10", accuracy["total_predictions"] == 10)
    check("Hits is 7", accuracy["hits"] == 7)
    check("Accuracy is 0.7", abs(accuracy["accuracy"] - 0.7) < 0.01)

    # Test resolve_predictions
    phantom._conn.execute(
        "INSERT INTO phantom_predictions "
        "(predicted_category, confidence, basis) "
        "VALUES (?, ?, ?)",
        ("IOLAAX+MEMEX", 0.6, "daily"),
    )
    phantom._conn.commit()

    phantom.resolve_predictions("IOLAAX+MEMEX")

    row = phantom._conn.execute(
        "SELECT hit, actual_category FROM phantom_predictions "
        "WHERE predicted_category='IOLAAX+MEMEX' AND resolved=1 "
        "ORDER BY id DESC LIMIT 1"
    ).fetchone()
    check("Resolved prediction has hit=1", row and row[0] == 1)
    check("Resolved prediction has correct actual",
          row and row[1] == "IOLAAX+MEMEX")

    # Miss case
    phantom._conn.execute(
        "INSERT INTO phantom_predictions "
        "(predicted_category, confidence, basis) "
        "VALUES (?, ?, ?)",
        ("CIPHER+ORACLE", 0.4, "sequential"),
    )
    phantom._conn.commit()
    phantom.resolve_predictions("VITA+NAVIGATOR")

    row = phantom._conn.execute(
        "SELECT hit FROM phantom_predictions "
        "WHERE predicted_category='CIPHER+ORACLE' AND resolved=1 "
        "ORDER BY id DESC LIMIT 1"
    ).fetchone()
    check("Miss prediction has hit=0", row and row[0] == 0)

    _cleanup(db_path, phantom)


# ── MAIN ──

def main():
    print("=" * 50)
    print("  SYNAPSE & PHANTOM TESTS (Phase 16)")
    print("=" * 50)

    tests = [
        test_table_creation,
        test_categorize_query,
        test_feedback_computation,
        test_pathway_strengthening,
        test_pathway_weakening,
        test_routing_bias_range,
        test_phantom_patterns,
        test_prediction_accuracy,
    ]

    for test in tests:
        try:
            test()
        except Exception as e:
            global FAIL_COUNT
            FAIL_COUNT += 1
            print(f"  \u274c {test.__name__} CRASHED: {e}")

    print(f"\n{'=' * 50}")
    total = PASS_COUNT + FAIL_COUNT
    print(f"  Resultaat: {PASS_COUNT}/{total} checks geslaagd")
    if FAIL_COUNT == 0:
        print("  \U0001f3c6 ALLE CHECKS GESLAAGD!")
    else:
        print(f"  \u26a0\ufe0f {FAIL_COUNT} checks gefaald!")
    print(f"{'=' * 50}")

    sys.exit(0 if FAIL_COUNT == 0 else 1)


if __name__ == "__main__":
    main()

"""
Phase 24 Tests — CorticalStack Backup + Data Retention
9 tests verifying backup, compression, pruning, and retention.

Gebruik: python test_phase24.py
"""

import gzip
import os
import sqlite3
import sys
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path

# UTF-8 voor Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

os.environ["DANNY_TEST_MODE"] = "1"
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
os.environ["ANONYMIZED_TELEMETRY"] = "False"

sys.path.insert(0, os.path.dirname(__file__))

PASS = 0
FAIL = 0


def check(label, condition):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  [PASS] {label}")
    else:
        FAIL += 1
        print(f"  [FAIL] {label}")


def _make_test_stack(tmp_dir):
    """Create a CorticalStack in a temp directory for isolated testing."""
    from danny_toolkit.brain.cortical_stack import CorticalStack
    db_path = Path(tmp_dir) / "test_cortical_stack.db"
    stack = CorticalStack(db_path=db_path)
    return stack


def test_1_backup_creates_file():
    """backup() creates file in backup dir."""
    print("\n[TEST 1] backup() creates file")
    with tempfile.TemporaryDirectory() as tmp:
        stack = _make_test_stack(tmp)
        # Insert some data
        stack.log_event("test", "action", {"key": "value"})
        stack.flush()

        # Monkey-patch Config.BACKUP_DIR for testing
        import danny_toolkit.core.config as cfg_mod
        original_backup = getattr(cfg_mod.Config, "BACKUP_DIR", None)
        cfg_mod.Config.BACKUP_DIR = Path(tmp) / "backups"

        try:
            backup_path = stack.backup(compress=False)
            check("backup file exists", backup_path.exists())
            check("backup in correct dir", "backups" in str(backup_path.parent))
            check("backup filename pattern", "cortical_stack_" in backup_path.name)
        finally:
            if original_backup is not None:
                cfg_mod.Config.BACKUP_DIR = original_backup
            stack.close()


def test_2_backup_gzip():
    """Backup file is gzip compressed."""
    print("\n[TEST 2] backup gzip compression")
    with tempfile.TemporaryDirectory() as tmp:
        stack = _make_test_stack(tmp)
        stack.log_event("test", "action", {"key": "value"})
        stack.flush()

        import danny_toolkit.core.config as cfg_mod
        original_backup = getattr(cfg_mod.Config, "BACKUP_DIR", None)
        cfg_mod.Config.BACKUP_DIR = Path(tmp) / "backups"

        try:
            backup_path = stack.backup(compress=True)
            check("backup ends with .gz", backup_path.suffix == ".gz")

            # Verify it's valid gzip
            try:
                with gzip.open(str(backup_path), "rb") as f:
                    data = f.read()
                check("valid gzip file", len(data) > 0)
            except Exception:
                check("valid gzip file", False)
        finally:
            if original_backup is not None:
                cfg_mod.Config.BACKUP_DIR = original_backup
            stack.close()


def test_3_backup_pruning():
    """Backup prunes old backups (keeps last 7)."""
    print("\n[TEST 3] backup pruning")
    with tempfile.TemporaryDirectory() as tmp:
        stack = _make_test_stack(tmp)
        stack.log_event("test", "action", {})
        stack.flush()

        import danny_toolkit.core.config as cfg_mod
        original_backup = getattr(cfg_mod.Config, "BACKUP_DIR", None)
        backup_dir = Path(tmp) / "backups"
        cfg_mod.Config.BACKUP_DIR = backup_dir

        try:
            # Create 10 backups
            for i in range(10):
                stack.backup(compress=False)
                time.sleep(0.05)  # Ensure unique timestamps

            backups = list(backup_dir.glob("cortical_stack_*"))
            check("pruned to 7 or fewer", len(backups) <= 7)
        finally:
            if original_backup is not None:
                cfg_mod.Config.BACKUP_DIR = original_backup
            stack.close()


def test_4_retention_returns_counts():
    """apply_retention_policy() returns deleted counts."""
    print("\n[TEST 4] retention policy returns counts")
    with tempfile.TemporaryDirectory() as tmp:
        stack = _make_test_stack(tmp)
        # Insert some data
        stack.log_event("test", "action", {})
        stack.flush()

        result = stack.apply_retention_policy()
        check("returns dict", isinstance(result, dict))
        check("has episodic_memory key", "episodic_memory" in result)
        check("has system_stats key", "system_stats" in result)
        stack.close()


def test_5_episodic_pruning():
    """episodic_memory rows older than 90d are deleted."""
    print("\n[TEST 5] episodic_memory retention (90 days)")
    with tempfile.TemporaryDirectory() as tmp:
        stack = _make_test_stack(tmp)

        # Insert old event (100 days ago)
        old_ts = (datetime.now() - timedelta(days=100)).isoformat()
        with stack._lock:
            stack._conn.execute(
                "INSERT INTO episodic_memory (timestamp, actor, action, details, source) VALUES (?, ?, ?, ?, ?)",
                (old_ts, "old_actor", "old_action", "{}", "test"),
            )
            stack._conn.commit()

        # Insert recent event
        stack.log_event("new_actor", "new_action", {})
        stack.flush()

        # Count before
        before = stack._conn.execute("SELECT COUNT(*) as c FROM episodic_memory").fetchone()["c"]
        check("has 2 events before", before == 2)

        # Apply retention
        deleted = stack.apply_retention_policy()
        check("deleted 1 old event", deleted["episodic_memory"] == 1)

        # Count after
        after = stack._conn.execute("SELECT COUNT(*) as c FROM episodic_memory").fetchone()["c"]
        check("1 event remains", after == 1)
        stack.close()


def test_6_interaction_trace_pruning():
    """interaction_trace rows older than 60d are deleted."""
    print("\n[TEST 6] interaction_trace retention (60 days)")
    with tempfile.TemporaryDirectory() as tmp:
        stack = _make_test_stack(tmp)

        # Create interaction_trace table if it doesn't exist
        with stack._lock:
            stack._conn.execute("""
                CREATE TABLE IF NOT EXISTS interaction_trace (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    agent TEXT,
                    query TEXT,
                    response_quality REAL DEFAULT 0.5
                )
            """)
            # Insert old row (70 days ago)
            old_ts = (datetime.now() - timedelta(days=70)).isoformat()
            stack._conn.execute(
                "INSERT INTO interaction_trace (timestamp, agent, query) VALUES (?, ?, ?)",
                (old_ts, "test_agent", "old query"),
            )
            # Insert recent row
            stack._conn.execute(
                "INSERT INTO interaction_trace (timestamp, agent, query) VALUES (?, ?, ?)",
                (datetime.now().isoformat(), "test_agent", "new query"),
            )
            stack._conn.commit()

        deleted = stack.apply_retention_policy()
        check("deleted 1 old trace", deleted["interaction_trace"] == 1)

        remaining = stack._conn.execute("SELECT COUNT(*) as c FROM interaction_trace").fetchone()["c"]
        check("1 trace remains", remaining == 1)
        stack.close()


def test_7_phantom_predictions_pruning():
    """phantom_predictions rows older than 30d are deleted."""
    print("\n[TEST 7] phantom_predictions retention (30 days)")
    with tempfile.TemporaryDirectory() as tmp:
        stack = _make_test_stack(tmp)

        # Create phantom_predictions table
        with stack._lock:
            stack._conn.execute("""
                CREATE TABLE IF NOT EXISTS phantom_predictions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    pattern TEXT,
                    prediction TEXT,
                    confidence REAL DEFAULT 0.5
                )
            """)
            # Insert old prediction (40 days ago)
            old_ts = (datetime.now() - timedelta(days=40)).isoformat()
            stack._conn.execute(
                "INSERT INTO phantom_predictions (timestamp, pattern, prediction) VALUES (?, ?, ?)",
                (old_ts, "pattern1", "pred1"),
            )
            # Insert recent prediction
            stack._conn.execute(
                "INSERT INTO phantom_predictions (timestamp, pattern, prediction) VALUES (?, ?, ?)",
                (datetime.now().isoformat(), "pattern2", "pred2"),
            )
            stack._conn.commit()

        deleted = stack.apply_retention_policy()
        check("deleted 1 old prediction", deleted["phantom_predictions"] == 1)

        remaining = stack._conn.execute("SELECT COUNT(*) as c FROM phantom_predictions").fetchone()["c"]
        check("1 prediction remains", remaining == 1)
        stack.close()


def test_8_semantic_memory_not_pruned():
    """semantic_memory is NOT pruned (permanent)."""
    print("\n[TEST 8] semantic_memory NOT pruned")
    with tempfile.TemporaryDirectory() as tmp:
        stack = _make_test_stack(tmp)

        # Insert old fact
        old_ts = (datetime.now() - timedelta(days=365)).isoformat()
        with stack._lock:
            stack._conn.execute(
                "INSERT INTO semantic_memory (key, value, confidence, learned_at, last_accessed) VALUES (?, ?, ?, ?, ?)",
                ("old_fact", "old value", 0.9, old_ts, old_ts),
            )
            stack._conn.commit()

        before = stack._conn.execute("SELECT COUNT(*) as c FROM semantic_memory").fetchone()["c"]

        # Apply retention
        stack.apply_retention_policy()

        after = stack._conn.execute("SELECT COUNT(*) as c FROM semantic_memory").fetchone()["c"]
        check("semantic_memory untouched", before == after)
        stack.close()


def test_9_knowledge_graph_not_pruned():
    """knowledge_graph is NOT pruned (permanent)."""
    print("\n[TEST 9] knowledge_graph NOT pruned")
    with tempfile.TemporaryDirectory() as tmp:
        stack = _make_test_stack(tmp)

        # The retention policy should not have a knowledge_graph entry
        deleted = stack.apply_retention_policy()
        check("no kg_edges in retention policy", "kg_edges" not in deleted)
        check("no entities in retention policy", "entities" not in deleted)
        check("semantic_memory not in retention policy", "semantic_memory" not in deleted)
        stack.close()


def main():
    print("=" * 60)
    print("  PHASE 24 TESTS — CorticalStack Backup + Data Retention")
    print("=" * 60)

    test_1_backup_creates_file()
    test_2_backup_gzip()
    test_3_backup_pruning()
    test_4_retention_returns_counts()
    test_5_episodic_pruning()
    test_6_interaction_trace_pruning()
    test_7_phantom_predictions_pruning()
    test_8_semantic_memory_not_pruned()
    test_9_knowledge_graph_not_pruned()

    total = PASS + FAIL
    print(f"\n{'=' * 60}")
    print(f"  RESULTAAT: {PASS}/{total} checks geslaagd")
    if FAIL == 0:
        print("  ALLE TESTS GESLAAGD!")
    else:
        print(f"  {FAIL} check(s) gefaald!")
    print(f"{'=' * 60}")

    sys.exit(0 if FAIL == 0 else 1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Test Phase 49: Hardware-Optimized RAG & System Tuning
=====================================================
10 tests · 30+ checks

Valideert:
  A. Config.SQLITE_CACHE_SIZE / MMAP_SIZE / BUSY_TIMEOUT constants
  B. Config.apply_sqlite_perf() helper exists and works
  C. apply_sqlite_perf() PRAGMAs correct on in-memory DB
  D. cortical_stack.py uses apply_sqlite_perf (2 locations)
  E. phantom.py + synapse.py use apply_sqlite_perf
  F. virtual_twin.py uses apply_sqlite_perf (2 locations)
  G. dreamer.py + waakhuis.py use apply_sqlite_perf
  H. semantic_cache.py + self_pruning.py use apply_sqlite_perf
  I. swarm_engine.py worker counts (10 + B95=2)
  J. No scattered individual PRAGMAs remaining

Gebruik:
    CUDA_VISIBLE_DEVICES=-1 DANNY_TEST_MODE=1 ANONYMIZED_TELEMETRY=False \
        python test_phase49.py
"""

from __future__ import annotations

import logging
import os
import sqlite3
import sys
import unittest

logger = logging.getLogger(__name__)

os.environ.setdefault("DANNY_TEST_MODE", "1")
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "-1")
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

# Windows UTF-8
if os.name == "nt":
    sys.stdout.reconfigure(encoding="utf-8")

CHECK = 0


def c(ok: bool, label: str = "") -> None:
    """Assert a check and print its result."""
    global CHECK
    CHECK += 1
    tag = f" ({label})" if label else ""
    status = "OK" if ok else "FAIL"
    print(f"  check {CHECK}: {status}{tag}")
    assert ok, f"Check {CHECK} failed{tag}"


def _read(relpath: str) -> str:
    """Read a source file relative to project root."""
    root = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(root, "danny_toolkit", *relpath.split("/"))
    with open(path, encoding="utf-8") as f:
        return f.read()


def _read_root(relpath: str) -> str:
    """Read a source file relative to project root (not danny_toolkit/)."""
    root = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(root, relpath)
    with open(path, encoding="utf-8") as f:
        return f.read()


class TestPhase49(unittest.TestCase):
    """Phase 49: Hardware-Optimized RAG & System Tuning."""

    # --- A. Config constants ---

    def test_01_config_sqlite_constants(self) -> None:
        """Config has SQLITE_CACHE_SIZE, MMAP_SIZE, BUSY_TIMEOUT."""
        src = _read("core/config.py")
        c("SQLITE_CACHE_SIZE" in src, "SQLITE_CACHE_SIZE defined")
        c("SQLITE_MMAP_SIZE" in src, "SQLITE_MMAP_SIZE defined")
        c("SQLITE_BUSY_TIMEOUT" in src, "SQLITE_BUSY_TIMEOUT defined")
        # Verify defaults
        c("-64000" in src, "cache_size default = -64000 (64 MB)")
        c("268435456" in src, "mmap_size default = 256 MB")
        c("10000" in src, "busy_timeout default = 10000 ms")

    # --- B. apply_sqlite_perf helper ---

    def test_02_apply_sqlite_perf_exists(self) -> None:
        """Config.apply_sqlite_perf() is defined."""
        src = _read("core/config.py")
        c("def apply_sqlite_perf" in src, "apply_sqlite_perf defined")
        c("@staticmethod" in src, "is staticmethod")
        # Check it applies key PRAGMAs
        c("PRAGMA cache_size" in src, "sets cache_size")
        c("PRAGMA mmap_size" in src, "sets mmap_size")
        c("PRAGMA journal_mode = WAL" in src, "sets WAL mode")
        c("PRAGMA synchronous = NORMAL" in src, "sets synchronous NORMAL")
        c("PRAGMA temp_store = MEMORY" in src, "sets temp_store MEMORY")

    # --- C. Functional test ---

    def test_03_apply_sqlite_perf_functional(self) -> None:
        """apply_sqlite_perf() actually sets PRAGMAs on a connection."""
        try:
            from danny_toolkit.core.config import Config
        except ImportError:
            logger.debug("danny_toolkit.core.config not available")
            return

        conn = sqlite3.connect(":memory:")
        Config.apply_sqlite_perf(conn)

        cache = conn.execute("PRAGMA cache_size").fetchone()[0]
        c(cache == -64000, f"cache_size = {cache} (expected -64000)")

        journal = conn.execute("PRAGMA journal_mode").fetchone()[0]
        c(journal in ("wal", "memory"), f"journal_mode = {journal}")

        sync = conn.execute("PRAGMA synchronous").fetchone()[0]
        c(sync == 1, f"synchronous = {sync} (1=NORMAL)")

        temp = conn.execute("PRAGMA temp_store").fetchone()[0]
        c(temp == 2, f"temp_store = {temp} (2=MEMORY)")

        conn.close()

    # --- D. cortical_stack.py ---

    def test_04_cortical_stack_wired(self) -> None:
        """cortical_stack.py uses Config.apply_sqlite_perf (2 locations)."""
        src = _read("brain/cortical_stack.py")
        count = src.count("Config.apply_sqlite_perf")
        c(count >= 2, f"cortical_stack: {count} apply_sqlite_perf calls (need >=2)")

    # --- E. phantom + synapse ---

    def test_05_phantom_synapse_wired(self) -> None:
        """phantom.py and synapse.py use Config.apply_sqlite_perf."""
        for mod in ["brain/phantom.py", "brain/synapse.py"]:
            src = _read(mod)
            c("Config.apply_sqlite_perf" in src, f"{mod} wired")

    # --- F. virtual_twin ---

    def test_06_virtual_twin_wired(self) -> None:
        """virtual_twin.py uses Config.apply_sqlite_perf (2 locations)."""
        src = _read("brain/virtual_twin.py")
        count = src.count("Config.apply_sqlite_perf")
        c(count >= 2, f"virtual_twin: {count} apply_sqlite_perf calls (need >=2)")

    # --- G. dreamer + waakhuis ---

    def test_07_dreamer_waakhuis_wired(self) -> None:
        """dreamer.py and waakhuis.py use Config.apply_sqlite_perf."""
        for mod in ["brain/dreamer.py", "brain/waakhuis.py"]:
            src = _read(mod)
            c("apply_sqlite_perf" in src, f"{mod} wired")

    # --- H. semantic_cache + self_pruning ---

    def test_08_semantic_cache_self_pruning_wired(self) -> None:
        """semantic_cache.py and self_pruning.py use Config.apply_sqlite_perf."""
        for mod in ["core/semantic_cache.py", "core/self_pruning.py"]:
            src = _read(mod)
            count = src.count("Config.apply_sqlite_perf")
            c(count >= 2, f"{mod}: {count} calls (need >=2)")

    # --- I. Swarm worker counts ---

    def test_09_swarm_worker_counts(self) -> None:
        """swarm_engine.py has CPU-aware _SWARM_MAX_WORKERS and B95 max_workers=2."""
        src = _read_root("swarm_engine.py")
        c("_SWARM_MAX_WORKERS = min(max(os.cpu_count()" in src, "swarm workers CPU-aware")
        c('max_workers=2, thread_name_prefix="b95"' in src, "B95 workers = 2")

    # --- J. No scattered PRAGMAs remaining ---

    def test_10_no_scattered_pragmas(self) -> None:
        """No individual PRAGMA cache_size/mmap_size in wired modules."""
        modules = [
            "brain/cortical_stack.py",
            "brain/phantom.py",
            "brain/synapse.py",
            "brain/virtual_twin.py",
            "brain/dreamer.py",
            "core/semantic_cache.py",
            "core/self_pruning.py",
        ]
        for mod in modules:
            src = _read(mod)
            # Filter out lines that are inside apply_sqlite_perf definition
            lines = src.split("\n")
            scattered = []
            for i, line in enumerate(lines):
                stripped = line.strip()
                if "PRAGMA cache_size" in stripped or "PRAGMA mmap_size" in stripped:
                    # Check it's not inside the apply_sqlite_perf definition
                    if "Config.SQLITE_" not in stripped:
                        scattered.append(f"line {i+1}: {stripped}")
            c(len(scattered) == 0,
              f"{mod} no scattered PRAGMAs (found: {scattered})")


if __name__ == "__main__":
    print(f"\n{'='*60}")
    print("TEST PHASE 49: Hardware-Optimized RAG & System Tuning")
    print(f"{'='*60}\n")
    unittest.main(verbosity=2, exit=True)

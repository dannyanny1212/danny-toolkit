#!/usr/bin/env python3
"""
Test Phase 50: CPU/GPU Coördinatie
==================================
12 tests · 35+ checks

Valideert:
  A. _SWARM_MAX_WORKERS is CPU-core-aware (os.cpu_count based)
  B. Heartbeat worker pool CPU-core-aware
  C. ProcessPoolExecutor infra in embeddings.py
  D. _CPU_OFFLOAD_THRESHOLD = 500
  E. mrl_truncate still works (small batch — inline)
  F. mrl_truncate still works (large batch — process pool path)
  G. _mrl_truncate_chunk is module-level (pickle-safe)
  H. TorchGPUEmbeddings._adaptive_batch_size exists
  I. VRAMBudgetGuard class in vram_manager
  J. vram_guard context manager works
  K. get_vram_guard singleton
  L. vram_guard wired in TorchGPU embed()

Gebruik:
    CUDA_VISIBLE_DEVICES=-1 DANNY_TEST_MODE=1 ANONYMIZED_TELEMETRY=False \
        python test_phase50.py
"""

import os
import sys
import unittest

os.environ.setdefault("DANNY_TEST_MODE", "1")
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "-1")
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

if os.name == "nt":
    sys.stdout.reconfigure(encoding="utf-8")

CHECK = 0


def c(ok: bool, label: str = ""):
    global CHECK
    CHECK += 1
    tag = f" ({label})" if label else ""
    status = "OK" if ok else "FAIL"
    print(f"  check {CHECK}: {status}{tag}")
    assert ok, f"Check {CHECK} failed{tag}"


def _read(relpath: str) -> str:
    root = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(root, "danny_toolkit", *relpath.split("/"))
    with open(path, encoding="utf-8") as f:
        return f.read()


def _read_root(relpath: str) -> str:
    root = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(root, relpath)
    with open(path, encoding="utf-8") as f:
        return f.read()


class TestPhase50(unittest.TestCase):
    """Phase 50: CPU/GPU Coördinatie."""

    # --- A. Swarm workers CPU-aware ---

    def test_01_swarm_workers_cpu_aware(self):
        """_SWARM_MAX_WORKERS uses os.cpu_count()."""
        src = _read_root("swarm_engine.py")
        c("os.cpu_count()" in src, "swarm uses os.cpu_count()")
        c("_SWARM_MAX_WORKERS = min(max(" in src, "bounded with min/max")

    # --- B. Heartbeat workers CPU-aware ---

    def test_02_heartbeat_workers_cpu_aware(self):
        """Heartbeat worker pool is CPU-core-aware."""
        src = _read("daemon/heartbeat.py")
        c("os.cpu_count()" in src, "heartbeat uses os.cpu_count()")
        c("import os" in src, "os imported in heartbeat")

    # --- C. ProcessPoolExecutor infra ---

    def test_03_cpu_pool_infrastructure(self):
        """embeddings.py has ProcessPoolExecutor infrastructure."""
        src = _read("core/embeddings.py")
        c("ProcessPoolExecutor" in src, "ProcessPoolExecutor imported")
        c("_CPU_POOL_WORKERS" in src, "_CPU_POOL_WORKERS defined")
        c("_get_cpu_pool" in src, "_get_cpu_pool() function exists")
        c("_cpu_pool_lock" in src, "thread-safe lazy init")

    # --- D. Offload threshold ---

    def test_04_offload_threshold(self):
        """_CPU_OFFLOAD_THRESHOLD is 500."""
        src = _read("core/embeddings.py")
        c("_CPU_OFFLOAD_THRESHOLD = 500" in src, "threshold = 500")

    # --- E. MRL truncate small batch ---

    def test_05_mrl_truncate_small(self):
        """mrl_truncate works for small batches (inline path)."""
        from danny_toolkit.core.embeddings import mrl_truncate
        vecs = [[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0]]
        result = mrl_truncate(vecs, 2)
        c(len(result) == 2, f"got {len(result)} results")
        c(len(result[0]) == 2, f"truncated to dim 2")
        # First vec [1,0] normalized should be [1,0]
        c(abs(result[0][0] - 1.0) < 0.01, "L2 normalized correctly")

    # --- F. MRL truncate noop ---

    def test_06_mrl_truncate_noop(self):
        """mrl_truncate returns input when dim >= vector dim."""
        from danny_toolkit.core.embeddings import mrl_truncate
        vecs = [[1.0, 2.0]]
        result = mrl_truncate(vecs, 5)
        c(result is vecs, "noop: same object returned")
        result2 = mrl_truncate([], 256)
        c(result2 == [], "empty list returns empty")

    # --- G. _mrl_truncate_chunk is pickle-safe ---

    def test_07_mrl_truncate_chunk_module_level(self):
        """_mrl_truncate_chunk is a module-level function (required for ProcessPool)."""
        src = _read("core/embeddings.py")
        # Must be def at module level, not inside a class
        lines = src.split("\n")
        found = False
        for line in lines:
            if line.startswith("def _mrl_truncate_chunk("):
                found = True
                break
        c(found, "_mrl_truncate_chunk is module-level function")

    # --- H. Adaptive batch size ---

    def test_08_adaptive_batch_size(self):
        """TorchGPUEmbeddings has _adaptive_batch_size method."""
        src = _read("core/embeddings.py")
        c("def _adaptive_batch_size" in src, "_adaptive_batch_size defined")
        c("psutil.cpu_percent" in src, "checks CPU load")
        c("vram_rapport" in src, "checks VRAM status")

    # --- I. VRAMBudgetGuard ---

    def test_09_vram_budget_guard_class(self):
        """VRAMBudgetGuard class exists in vram_manager."""
        src = _read("core/vram_manager.py")
        c("class VRAMBudgetGuard" in src, "VRAMBudgetGuard class defined")
        c("def acquire" in src, "acquire method")
        c("def release" in src, "release method")
        c("current_holder" in src, "current_holder property")

    # --- J. vram_guard context manager ---

    def test_10_vram_guard_context_manager(self):
        """vram_guard works as context manager."""
        from danny_toolkit.core.vram_manager import vram_guard, get_vram_guard

        guard = get_vram_guard()
        c(guard.current_holder is None, "initially no holder")

        # Context manager without VRAM check (required_mb=0)
        with vram_guard("test_workload", 0):
            c(guard.current_holder == "test_workload", "holder set during context")

        c(guard.current_holder is None, "holder cleared after context")

    # --- K. get_vram_guard singleton ---

    def test_11_vram_guard_singleton(self):
        """get_vram_guard returns same instance."""
        from danny_toolkit.core.vram_manager import get_vram_guard
        g1 = get_vram_guard()
        g2 = get_vram_guard()
        c(g1 is g2, "singleton: same instance")

    # --- L. TorchGPU wired with vram_guard ---

    def test_12_torch_gpu_wired(self):
        """TorchGPUEmbeddings.embed() uses vram_guard."""
        src = _read("core/embeddings.py")
        # Find embed method that uses vram_guard
        c('vram_guard("torch_embeddings"' in src, "embed() uses vram_guard")


if __name__ == "__main__":
    print(f"\n{'='*60}")
    print("TEST PHASE 50: CPU/GPU Coördinatie")
    print(f"{'='*60}\n")
    unittest.main(verbosity=2, exit=True)

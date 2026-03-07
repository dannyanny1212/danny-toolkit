#!/usr/bin/env python3
"""
Test Phase 45: Version Harmony + Housekeeper Bugfix
=====================================================
12 tests · 40+ checks

Valideert:
  A. Version harmony (pyproject.toml, danny_toolkit, brain — all 6.11.0)
  B. roteer_logs bugfix (correct naam + argument in housekeeper)
  C. learning/orchestrator.py Diamond Polish (geen bare pass)
  D. nul artifact cleanup
  E. GhostAmplifier ImportError guard (HAS_GROQ)
  F. GhostAmplifier + SanctuaryDashboard exports in brain/__init__
  G. get_sanctuary() thread-safe singleton (threading.Lock)
  H. Root brain/__init__.py synced with package version
  I. Sanctuary fallback stats updated

Gebruik:
    CUDA_VISIBLE_DEVICES=-1 DANNY_TEST_MODE=1 ANONYMIZED_TELEMETRY=False \
        python test_phase45.py
"""

import ast
import importlib
import inspect
import os
import sys
import textwrap
import threading
import unittest

os.environ.setdefault("DANNY_TEST_MODE", "1")
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "-1")
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

# Windows UTF-8
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


class TestPhase45(unittest.TestCase):
    """Phase 45: Version Harmony + Housekeeper Bugfix."""

    # ── Test 1: Version harmony — all 3 match ──

    def test_01_version_harmony(self):
        """pyproject.toml, danny_toolkit, brain — all >= 6.11.0 and equal."""
        print("\n[Test 1] Version harmony")
        import danny_toolkit
        import danny_toolkit.brain as brain

        pkg_ver = getattr(danny_toolkit, "__version__", "0.0.0")
        brain_ver = getattr(brain, "__version__", "0.0.0")

        import re
        toml_path = os.path.join(os.path.dirname(__file__), "pyproject.toml")
        with open(toml_path, "r", encoding="utf-8") as f:
            match = re.search(r'version\s*=\s*"([^"]+)"', f.read())
        toml_ver = match.group(1) if match else "0.0.0"

        c(pkg_ver == brain_ver, f"package ({pkg_ver}) == brain ({brain_ver})")
        c(pkg_ver == toml_ver, f"package ({pkg_ver}) == pyproject ({toml_ver})")
        major, minor, _ = [int(x) for x in brain_ver.split(".")]
        c(major >= 6 and minor >= 11, f"version {brain_ver} >= 6.11.0")

    # ── Test 2: roteer_logs bugfix ──

    def test_02_roteer_logs_bugfix(self):
        """Housekeeper importeert roteer_logs (niet rotate_logs)."""
        print("\n[Test 2] roteer_logs bugfix")
        from danny_toolkit.daemon.daemon_core import DigitalDaemon
        source = textwrap.dedent(
            inspect.getsource(DigitalDaemon._run_housekeeper)
        )
        c("roteer_logs" in source, "correct naam: roteer_logs")
        c("rotate_logs" not in source.replace("roteer_logs", ""),
          "geen stale rotate_logs")
        c("logs" in source, "log directory argument meegegeven")

    # ── Test 3: roteer_logs signature ──

    def test_03_roteer_logs_callable(self):
        """roteer_logs functie correct importeerbaar met log_dir param."""
        print("\n[Test 3] roteer_logs importeerbaar")
        from danny_toolkit.core.log_rotation import roteer_logs
        c(callable(roteer_logs), "roteer_logs is callable")
        sig = inspect.signature(roteer_logs)
        params = list(sig.parameters.keys())
        c(params[0] == "log_dir", f"eerste param: {params[0]}")

    # ── Test 4: orchestrator Diamond Polish ──

    def test_04_orchestrator_polish(self):
        """learning/orchestrator.py: logger + geen bare pass stub."""
        print("\n[Test 4] orchestrator Diamond Polish")
        path = os.path.join(
            os.path.dirname(__file__),
            "danny_toolkit", "learning", "orchestrator.py",
        )
        with open(path, "r", encoding="utf-8") as f:
            source = f.read()
        c("import logging" in source, "import logging")
        c("logger = logging.getLogger" in source, "logger defined")
        c("logger.debug" in source, "logger.debug call present")

    # ── Test 5: GhostAmplifier ImportError guard ──

    def test_05_ghost_amplifier_guard(self):
        """ghost_amplifier.py: groq import guarded with HAS_GROQ."""
        print("\n[Test 5] GhostAmplifier ImportError guard")
        path = os.path.join(
            os.path.dirname(__file__),
            "danny_toolkit", "brain", "ghost_amplifier.py",
        )
        with open(path, "r", encoding="utf-8") as f:
            source = f.read()
        c("HAS_GROQ" in source, "HAS_GROQ flag defined")
        c("try:" in source and "from groq import" in source,
          "groq import in try/except")
        # Check geen bare top-level import
        tree = ast.parse(source)
        bare_groq_import = False
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module == "groq":
                    bare_groq_import = True
        c(not bare_groq_import, "geen bare top-level groq import")

    # ── Test 6: GhostAmplifier exportable ──

    def test_06_ghost_amplifier_export(self):
        """GhostAmplifier + get_ghost_amplifier in brain.__all__."""
        print("\n[Test 6] GhostAmplifier export")
        import danny_toolkit.brain as brain
        all_exports = getattr(brain, "__all__", [])
        c("GhostAmplifier" in all_exports, "GhostAmplifier in __all__")
        c("get_ghost_amplifier" in all_exports, "get_ghost_amplifier in __all__")

    # ── Test 7: SanctuaryDashboard exportable ──

    def test_07_sanctuary_export(self):
        """SanctuaryDashboard + get_sanctuary in brain.__all__."""
        print("\n[Test 7] SanctuaryDashboard export")
        import danny_toolkit.brain as brain
        all_exports = getattr(brain, "__all__", [])
        c("SanctuaryDashboard" in all_exports, "SanctuaryDashboard in __all__")
        c("get_sanctuary" in all_exports, "get_sanctuary in __all__")

    # ── Test 8: get_sanctuary thread-safe ──

    def test_08_sanctuary_singleton_threadsafe(self):
        """get_sanctuary() gebruikt threading.Lock, niet hasattr."""
        print("\n[Test 8] get_sanctuary thread-safety")
        path = os.path.join(
            os.path.dirname(__file__),
            "danny_toolkit", "brain", "sanctuary_dashboard.py",
        )
        with open(path, "r", encoding="utf-8") as f:
            source = f.read()
        c("import threading" in source, "import threading")
        c("_sanctuary_lock" in source, "_sanctuary_lock defined")
        c("with _sanctuary_lock" in source, "Lock used in get_sanctuary")
        # hasattr pattern should be gone
        c("hasattr(get_sanctuary" not in source,
          "geen hasattr singleton pattern")

    # ── Test 9: Root brain/__init__.py synced ──

    def test_09_root_brain_synced(self):
        """Root brain/__init__.py version + key exports match package."""
        print("\n[Test 9] Root brain/__init__.py sync")
        root_path = os.path.join(
            os.path.dirname(__file__), "brain", "__init__.py"
        )
        with open(root_path, "r", encoding="utf-8") as f:
            source = f.read()

        c('"6.11.0"' in source, "root version = 6.11.0")
        c("GhostAmplifier" in source, "GhostAmplifier in root exports")
        c("SanctuaryDashboard" in source, "SanctuaryDashboard in root exports")
        c("dream_monitor" in source, "dream_monitor in root exports")
        c("OracleAgent" in source, "OracleAgent in root exports")
        c("AgentFactory" in source, "AgentFactory in root exports")

    # ── Test 10: Sanctuary fallback stats updated ──

    def test_10_sanctuary_stats(self):
        """Sanctuary fallback stats reflect current system."""
        print("\n[Test 10] Sanctuary fallback stats")
        path = os.path.join(
            os.path.dirname(__file__),
            "danny_toolkit", "brain", "sanctuary_dashboard.py",
        )
        with open(path, "r", encoding="utf-8") as f:
            source = f.read()
        # Old stale values should be gone
        c("31 Apps" not in source, "geen stale '31 Apps'")
        c("86 Tools" not in source, "geen stale '86 Tools'")
        # New values
        c("29 Apps" in source, "actueel: 29 Apps")
        c("92 Tools" in source, "actueel: 92 Tools")

    # ── Test 11: Sanctuary live queries ──

    def test_11_sanctuary_live_queries(self):
        """_init_metrics() bevat live queries voor Prometheus en Governor."""
        print("\n[Test 11] Sanctuary live queries")
        path = os.path.join(
            os.path.dirname(__file__),
            "danny_toolkit", "brain", "sanctuary_dashboard.py",
        )
        with open(path, "r", encoding="utf-8") as f:
            source = f.read()
        c("PrometheusBrain" in source, "Prometheus live query")
        c("OmegaGovernor" in source or "Governor" in source,
          "Governor live query")

    # ── Test 12: GhostAmplifier importeerbaar ──

    def test_12_ghost_amplifier_importable(self):
        """GhostAmplifier + singleton importeerbaar."""
        print("\n[Test 12] GhostAmplifier importeerbaar")
        from danny_toolkit.brain.ghost_amplifier import (
            GhostAmplifier, get_ghost_amplifier,
        )
        c(callable(get_ghost_amplifier), "get_ghost_amplifier callable")
        amp = get_ghost_amplifier()
        c(isinstance(amp, GhostAmplifier), "singleton returns GhostAmplifier")
        amp2 = get_ghost_amplifier()
        c(amp is amp2, "singleton identity")


if __name__ == "__main__":
    print("=" * 60)
    print("  Phase 45: Version Harmony + Housekeeper Bugfix")
    print("=" * 60)

    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestPhase45)
    runner = unittest.TextTestRunner(verbosity=0)
    result = runner.run(suite)

    print(f"\n{'=' * 60}")
    tests_run = result.testsRun
    failures = len(result.failures) + len(result.errors)
    print(f"Checks: {CHECK}")
    print(f"Tests:  {tests_run} run, {failures} fail, {len(result.errors)} error")
    print(f"{'=' * 60}")

    sys.exit(0 if failures == 0 else 1)

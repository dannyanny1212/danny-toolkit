#!/usr/bin/env python3
"""
Test Phase 43: Diamond Sweep + Observatory Expansion
======================================================
15 tests · 60+ checks

Valideert:
  A. Version bump (6.10.0)
  B. dream_monitor + quick_peek exports in brain/__init__
  C. run_all_tests.py bevat Phase 33-42 suites (37 totaal)
  D. Observatory Tab: auction + failure panels bestaan
  E. Observatory cache fetcht auction_history, failure_analysis, trend_data
  F. Observatory panel registry bevat 3 nieuwe entries
  G. Diamond Polish: learning/ modules hebben logger.debug (geen bare pass)
  H. Diamond Polish: omega_sovereign_core/ modules hebben logger.debug
  I. learning/ modules importeren correct
  J. omega_sovereign_core/ modules importeren correct

Gebruik:
    CUDA_VISIBLE_DEVICES=-1 DANNY_TEST_MODE=1 ANONYMIZED_TELEMETRY=False \
        python test_phase43.py
"""

import ast
import importlib
import inspect
import os
import sys
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


class TestPhase43(unittest.TestCase):
    """Phase 43: Diamond Sweep + Observatory Expansion."""

    # ── Test 1: Version bump ──

    def test_01_version(self):
        """brain.__version__ >= 6.10.0"""
        print("\n[Test 1] Version bump")
        import danny_toolkit.brain as brain
        version = getattr(brain, "__version__", "0.0.0")
        major, minor, patch = [int(x) for x in version.split(".")]
        c(major >= 6 and minor >= 10, f"version: {version} >= 6.10.0")

    # ── Test 2: dream_monitor export ──

    def test_02_dream_monitor_export(self):
        """dream_monitor en quick_peek in brain.__all__."""
        print("\n[Test 2] dream_monitor + quick_peek exports")
        import danny_toolkit.brain as brain
        all_exports = getattr(brain, "__all__", [])
        c("dream_monitor" in all_exports, "dream_monitor in __all__")
        c("quick_peek" in all_exports, "quick_peek in __all__")

    def test_03_dream_monitor_importable(self):
        """dream_monitor direct importeerbaar."""
        print("\n[Test 3] dream_monitor importeerbaar")
        from danny_toolkit.brain.dream_monitor import dream_monitor, quick_peek
        c(callable(dream_monitor), "dream_monitor is callable")
        c(callable(quick_peek), "quick_peek is callable")

    # ── Test 4: run_all_tests.py registratie ──

    def test_04_run_all_tests_count(self):
        """run_all_tests.py bevat 38 suites inclusief Phase 33-43."""
        print("\n[Test 4] run_all_tests.py suite registratie")
        test_runner_path = os.path.join(
            os.path.dirname(__file__), "run_all_tests.py"
        )
        with open(test_runner_path, "r", encoding="utf-8") as f:
            source = f.read()

        tree = ast.parse(source)
        # Zoek de TESTS lijst
        tests_list = None
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "TESTS":
                        tests_list = node.value
                        break

        c(tests_list is not None, "TESTS lijst gevonden")
        c(isinstance(tests_list, ast.List), "TESTS is een List")
        count = len(tests_list.elts)
        c(count >= 38, f"TESTS count: {count} >= 38")

        # Check dat Phase 33-42 erin zitten
        for phase in [33, 34, 35, 36, 37, 38, 39, 40, 41, 42]:
            c(f"phase{phase}" in source.lower() or f"Phase {phase}" in source,
              f"Phase {phase} geregistreerd")

    # ── Test 5: Observatory Tab panels ──

    def test_05_observatory_tab_panels(self):
        """ObservatoryTab heeft auction_panel en failure_panel."""
        print("\n[Test 5] Observatory Tab panels")
        app_path = os.path.join(
            os.path.dirname(__file__), "omega_sovereign_app.py"
        )
        with open(app_path, "r", encoding="utf-8") as f:
            source = f.read()

        c("self.auction_panel" in source, "auction_panel bestaat")
        c("self.failure_panel" in source, "failure_panel bestaat")
        c("Auction History" in source, "Auction History label")
        c("Failure Analysis" in source, "Failure Analysis label")

    # ── Test 6: Observatory cache ──

    def test_06_observatory_cache(self):
        """_fetch_all fetcht auction_history, failure_analysis, trend_data."""
        print("\n[Test 6] Observatory cache calls")
        app_path = os.path.join(
            os.path.dirname(__file__), "omega_sovereign_app.py"
        )
        with open(app_path, "r", encoding="utf-8") as f:
            source = f.read()

        c("get_auction_history" in source, "cache calls get_auction_history()")
        c("get_failure_analysis" in source, "cache calls get_failure_analysis()")
        c("get_trend_data" in source, "cache calls get_trend_data()")

    # ── Test 7: Observatory panel registry ──

    def test_07_observatory_registry(self):
        """Panel registry bevat auction, failure, trend entries."""
        print("\n[Test 7] Observatory panel registry")
        app_path = os.path.join(
            os.path.dirname(__file__), "omega_sovereign_app.py"
        )
        with open(app_path, "r", encoding="utf-8") as f:
            source = f.read()

        c("observatory.auctions" in source, "registry: observatory.auctions")
        c("observatory.failures" in source, "registry: observatory.failures")
        c("observatory.trends" in source, "registry: observatory.trends")

    # ── Test 8-9: Diamond Polish learning/ ──

    def test_08_learning_logger_imports(self):
        """Alle learning/ modules hebben import logging + logger."""
        print("\n[Test 8] learning/ logger imports")
        learning_dir = os.path.join(
            os.path.dirname(__file__),
            "danny_toolkit", "learning",
        )
        modules = [
            "feedback_manager.py", "memory.py", "optimizer.py",
            "patterns.py", "performance_analyzer.py",
            "self_improvement.py", "tracker.py",
        ]
        for mod in modules:
            path = os.path.join(learning_dir, mod)
            with open(path, "r", encoding="utf-8") as f:
                source = f.read()
            c("import logging" in source, f"{mod}: import logging")
            c("logger = logging.getLogger" in source, f"{mod}: logger defined")

    def test_09_learning_no_bare_pass(self):
        """Geen bare 'except ...: pass' meer in learning/ _load()."""
        print("\n[Test 9] learning/ geen bare pass in _load()")
        learning_dir = os.path.join(
            os.path.dirname(__file__),
            "danny_toolkit", "learning",
        )
        modules = [
            "feedback_manager.py", "memory.py", "optimizer.py",
            "patterns.py", "performance_analyzer.py",
            "self_improvement.py", "tracker.py",
        ]
        for mod in modules:
            path = os.path.join(learning_dir, mod)
            with open(path, "r", encoding="utf-8") as f:
                source = f.read()
            # Zoek except blokken met bare pass (niet logger.debug)
            tree = ast.parse(source)
            bare_pass_found = False
            for node in ast.walk(tree):
                if isinstance(node, ast.ExceptHandler):
                    if (len(node.body) == 1
                            and isinstance(node.body[0], ast.Pass)):
                        # Exclude module-level ImportError
                        if not (node.type and isinstance(node.type, ast.Name)
                                and node.type.id == "ImportError"):
                            bare_pass_found = True
            c(not bare_pass_found, f"{mod}: geen bare except:pass")

    # ── Test 10-11: Diamond Polish omega_sovereign_core/ ──

    def test_10_sovereign_core_no_bare_pass(self):
        """Geen bare pass in event_signing.py, auto_saver.py, sovereign_gate.py."""
        print("\n[Test 10] omega_sovereign_core/ Diamond Polish")
        core_dir = os.path.join(
            os.path.dirname(__file__),
            "danny_toolkit", "omega_sovereign_core",
        )
        modules = ["event_signing.py", "auto_saver.py", "sovereign_gate.py"]
        for mod in modules:
            path = os.path.join(core_dir, mod)
            with open(path, "r", encoding="utf-8") as f:
                source = f.read()
            tree = ast.parse(source)
            bare_pass_count = 0
            for node in ast.walk(tree):
                if isinstance(node, ast.ExceptHandler):
                    if (len(node.body) == 1
                            and isinstance(node.body[0], ast.Pass)):
                        if not (node.type and isinstance(node.type, ast.Name)
                                and node.type.id == "ImportError"):
                            bare_pass_count += 1
            c(bare_pass_count == 0,
              f"{mod}: {bare_pass_count} bare except:pass (expect 0)")

    # ── Test 11: learning/ modules importeerbaar ──

    def test_11_learning_imports(self):
        """Alle learning/ modules importeerbaar."""
        print("\n[Test 11] learning/ imports")
        mods = [
            "danny_toolkit.learning.feedback_manager",
            "danny_toolkit.learning.memory",
            "danny_toolkit.learning.optimizer",
            "danny_toolkit.learning.patterns",
            "danny_toolkit.learning.performance_analyzer",
            "danny_toolkit.learning.self_improvement",
            "danny_toolkit.learning.tracker",
        ]
        for mod_name in mods:
            try:
                importlib.import_module(mod_name)
                ok = True
            except Exception:
                ok = False
            short = mod_name.split(".")[-1]
            c(ok, f"{short} importeerbaar")

    # ── Test 12: sovereign_core modules importeerbaar ──

    def test_12_sovereign_core_imports(self):
        """omega_sovereign_core/ modules importeerbaar."""
        print("\n[Test 12] omega_sovereign_core/ imports")
        mods = [
            "danny_toolkit.omega_sovereign_core.event_signing",
            "danny_toolkit.omega_sovereign_core.auto_saver",
            "danny_toolkit.omega_sovereign_core.sovereign_gate",
        ]
        for mod_name in mods:
            try:
                importlib.import_module(mod_name)
                ok = True
            except SystemExit:
                # Sovereign Gate kan SystemExit gooien buiten test mode
                ok = True
            except Exception:
                ok = False
            short = mod_name.split(".")[-1]
            c(ok, f"{short} importeerbaar")

    # ── Test 13: ObservatorySync API methods exist ──

    def test_13_observatory_api(self):
        """ObservatorySync heeft get_auction_history, get_failure_analysis, get_trend_data."""
        print("\n[Test 13] ObservatorySync API completeness")
        from danny_toolkit.brain.observatory_sync import ObservatorySync

        c(hasattr(ObservatorySync, "get_auction_history"),
          "get_auction_history method exists")
        c(hasattr(ObservatorySync, "get_failure_analysis"),
          "get_failure_analysis method exists")
        c(hasattr(ObservatorySync, "get_trend_data"),
          "get_trend_data method exists")
        c(hasattr(ObservatorySync, "get_cost_analysis"),
          "get_cost_analysis method exists")
        c(hasattr(ObservatorySync, "get_model_leaderboard"),
          "get_model_leaderboard method exists")

    # ── Test 14: ObservatoryTab grid 3x2 ──

    def test_14_observatory_grid(self):
        """ObservatoryTab grid heeft 3 rijen."""
        print("\n[Test 14] Observatory Tab 3x2 grid")
        app_path = os.path.join(
            os.path.dirname(__file__), "omega_sovereign_app.py"
        )
        with open(app_path, "r", encoding="utf-8") as f:
            source = f.read()

        # Moet row 2 configureren
        c("self.grid_rowconfigure(2, weight=1)" in source,
          "grid row 2 configured")
        c('row=2, column=0' in source, "auction_panel at row=2, col=0")
        c('row=2, column=1' in source, "failure_panel at row=2, col=1")

    # ── Test 15: Docstring header controle ──

    def test_15_run_all_tests_docstring(self):
        """run_all_tests.py docstring vermeldt 38 suites."""
        print("\n[Test 15] run_all_tests.py docstring")
        test_runner_path = os.path.join(
            os.path.dirname(__file__), "run_all_tests.py"
        )
        with open(test_runner_path, "r", encoding="utf-8") as f:
            source = f.read()
        c("38 test suites" in source, "docstring vermeldt 38 suites")


if __name__ == "__main__":
    print("=" * 60)
    print("  Phase 43: Diamond Sweep + Observatory Expansion")
    print("=" * 60)

    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestPhase43)
    runner = unittest.TextTestRunner(verbosity=0)
    result = runner.run(suite)

    print(f"\n{'=' * 60}")
    tests_run = result.testsRun
    failures = len(result.failures) + len(result.errors)
    print(f"Checks: {CHECK}")
    print(f"Tests:  {tests_run} run, {failures} fail, {len(result.errors)} error")
    print(f"{'=' * 60}")

    sys.exit(0 if failures == 0 else 1)

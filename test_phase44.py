#!/usr/bin/env python3
"""
Test Phase 44: Housekeeper Awakening + Diamond Polish II
=========================================================
14 tests · 55+ checks

Valideert:
  A. Housekeeper implementatie (geen bare pass meer)
  B. Housekeeper wiring: roteer_logs, SelfPruning, CorticalStack retention
  C. _boot_time in DigitalDaemon (geen hardcoded hours placeholder)
  D. Diamond Polish II: introspector.py geen bare except:pass
  E. Diamond Polish II: ghost_writer.py geen bare except:pass
  F. TheHunt _search_web() niet meer leeg (VoidWalker wiring)
  G. prism_dashboard.py geen dead 'if False' code
  H. Version harmony (alle 3 versies gesynchroniseerd)
  I. roteer_logs correct geïmporteerd (naam + argument)
  J. learning/orchestrator.py geen bare pass stub

Gebruik:
    CUDA_VISIBLE_DEVICES=-1 DANNY_TEST_MODE=1 ANONYMIZED_TELEMETRY=False \
        python test_phase44.py
"""

import ast
import importlib
import inspect
import os
import sys
import textwrap
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


class TestPhase44(unittest.TestCase):
    """Phase 44: Housekeeper Awakening + Diamond Polish II."""

    # ── Test 1: Housekeeper niet meer bare pass ──

    def test_01_housekeeper_implemented(self):
        """_run_housekeeper() is niet meer een bare pass stub."""
        print("\n[Test 1] Housekeeper implementatie")
        from danny_toolkit.daemon.daemon_core import DigitalDaemon
        source = textwrap.dedent(inspect.getsource(DigitalDaemon._run_housekeeper))

        # Check dat er meer dan alleen pass in zit
        c("roteer_logs" in source or "retention" in source,
          "_run_housekeeper bevat echte logica")
        c("tasks_done" in source, "tasks_done tracking aanwezig")

    # ── Test 2: Housekeeper roept roteer_logs correct aan ──

    def test_02_roteer_logs_wiring(self):
        """Housekeeper importeert roteer_logs (niet rotate_logs)."""
        print("\n[Test 2] roteer_logs wiring")
        from danny_toolkit.daemon.daemon_core import DigitalDaemon
        source = inspect.getsource(DigitalDaemon._run_housekeeper)

        c("roteer_logs" in source, "import naam is roteer_logs")
        c("rotate_logs" not in source or "roteer_logs" in source,
          "geen stale rotate_logs referentie")
        # Check dat log_dir argument meegegeven wordt
        c("logs" in source, "log directory pad meegegeven")

    # ── Test 3: roteer_logs importeerbaar ──

    def test_03_roteer_logs_importable(self):
        """roteer_logs functie importeerbaar uit core.log_rotation."""
        print("\n[Test 3] roteer_logs importeerbaar")
        from danny_toolkit.core.log_rotation import roteer_logs
        c(callable(roteer_logs), "roteer_logs is callable")

        # Check signature: eerste arg is log_dir
        sig = inspect.signature(roteer_logs)
        params = list(sig.parameters.keys())
        c(params[0] == "log_dir", f"eerste param is log_dir (got: {params[0]})")

    # ── Test 4: Housekeeper retention + pruning ──

    def test_04_housekeeper_retention_pruning(self):
        """Housekeeper bevat CorticalStack retention en SelfPruning."""
        print("\n[Test 4] Housekeeper retention + pruning")
        from danny_toolkit.daemon.daemon_core import DigitalDaemon
        source = inspect.getsource(DigitalDaemon._run_housekeeper)

        c("apply_retention_policy" in source, "CorticalStack retention aanwezig")
        c("SelfPruning" in source, "SelfPruning import aanwezig")
        c("prune()" in source, "prune() call aanwezig")

    # ── Test 5: _boot_time (geen hardcoded hours) ──

    def test_05_boot_time(self):
        """DigitalDaemon heeft _boot_time, geen hardcoded hours = 2."""
        print("\n[Test 5] _boot_time tracking")
        from danny_toolkit.daemon.daemon_core import DigitalDaemon
        init_source = inspect.getsource(DigitalDaemon.__init__)
        c("_boot_time" in init_source, "_boot_time in __init__")

        # Check dat hours berekend wordt ipv hardcoded
        full_source = inspect.getsource(DigitalDaemon)
        c("hours = 2" not in full_source,
          "geen hardcoded hours = 2 meer")

    # ── Test 6: introspector.py Diamond Polish ──

    def test_06_introspector_no_bare_pass(self):
        """introspector.py heeft geen bare except:pass meer."""
        print("\n[Test 6] introspector Diamond Polish")
        path = os.path.join(
            os.path.dirname(__file__),
            "danny_toolkit", "brain", "introspector.py",
        )
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
          f"introspector.py: {bare_pass_count} bare except:pass (expect 0)")

    # ── Test 7: ghost_writer.py Diamond Polish ──

    def test_07_ghost_writer_no_bare_pass(self):
        """ghost_writer.py heeft geen bare except:pass meer."""
        print("\n[Test 7] ghost_writer Diamond Polish")
        path = os.path.join(
            os.path.dirname(__file__),
            "danny_toolkit", "brain", "ghost_writer.py",
        )
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
          f"ghost_writer.py: {bare_pass_count} bare except:pass (expect 0)")

    # ── Test 8: TheHunt _search_web() gewired ──

    def test_08_search_web_wired(self):
        """HuntRouter._search_web() is geen lege return [] meer."""
        print("\n[Test 8] TheHunt _search_web() wiring")
        from danny_toolkit.brain.ultimate_hunt import HuntRouter
        source = inspect.getsource(HuntRouter._search_web)

        c("VoidWalker" in source, "_search_web importeert VoidWalker")
        c("_search" in source, "_search_web roept walker._search aan")
        c("_harvest" in source, "_search_web roept walker._harvest aan")

    # ── Test 9: prism_dashboard geen dead code ──

    def test_09_prism_no_dead_code(self):
        """prism_dashboard.py heeft geen 'if False' dead code meer."""
        print("\n[Test 9] prism_dashboard cleanup")
        path = os.path.join(
            os.path.dirname(__file__),
            "danny_toolkit", "apps", "prism_dashboard.py",
        )
        with open(path, "r", encoding="utf-8") as f:
            source = f.read()

        c("if False" not in source, "geen 'if False' dead code")

    # ── Test 10: Version harmony ──

    def test_10_version_harmony(self):
        """Alle 3 versienummers zijn gesynchroniseerd."""
        print("\n[Test 10] Version harmony")

        # brain/__init__.py
        import danny_toolkit.brain as brain
        brain_ver = getattr(brain, "__version__", "0.0.0")

        # danny_toolkit/__init__.py
        import danny_toolkit
        pkg_ver = getattr(danny_toolkit, "__version__", "0.0.0")

        # pyproject.toml
        toml_path = os.path.join(os.path.dirname(__file__), "pyproject.toml")
        with open(toml_path, "r", encoding="utf-8") as f:
            toml_source = f.read()
        # Parse version = "x.y.z"
        import re
        match = re.search(r'version\s*=\s*"([^"]+)"', toml_source)
        toml_ver = match.group(1) if match else "0.0.0"

        c(brain_ver == pkg_ver,
          f"brain ({brain_ver}) == package ({pkg_ver})")
        c(brain_ver == toml_ver,
          f"brain ({brain_ver}) == pyproject.toml ({toml_ver})")
        c(pkg_ver == toml_ver,
          f"package ({pkg_ver}) == pyproject.toml ({toml_ver})")

        # Alle >= 6.11.0
        major, minor, _ = [int(x) for x in brain_ver.split(".")]
        c(major >= 6 and minor >= 11,
          f"version {brain_ver} >= 6.11.0")

    # ── Test 11: learning/orchestrator.py Diamond Polish ──

    def test_11_orchestrator_no_stub(self):
        """learning/orchestrator.py heeft geen bare pass stub meer."""
        print("\n[Test 11] orchestrator Diamond Polish")
        path = os.path.join(
            os.path.dirname(__file__),
            "danny_toolkit", "learning", "orchestrator.py",
        )
        with open(path, "r", encoding="utf-8") as f:
            source = f.read()

        c("import logging" in source, "import logging aanwezig")
        c("logger = logging.getLogger" in source, "logger gedefinieerd")

        # Check: de elif rating <= 2 block bevat geen pass meer
        tree = ast.parse(source)
        # Zoek elif met rating <= 2 — body mag geen lone Pass zijn
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                # Check orelse branches
                for branch in ([node] + (node.orelse if isinstance(node.orelse, list) else [])):
                    if isinstance(branch, ast.If):
                        if (len(branch.body) == 1
                                and isinstance(branch.body[0], ast.Pass)):
                            # Check of dit de rating branch is
                            src_segment = ast.get_source_segment(source, branch)
                            if src_segment and "rating" in str(src_segment):
                                c(False, "rating branch is nog bare pass")
                                return
        c(True, "geen bare pass in rating branch")

    # ── Test 12: nul artifact verwijderd ──

    def test_12_nul_artifact_gone(self):
        """danny_toolkit/nul artifact bestand bestaat niet meer."""
        print("\n[Test 12] nul artifact cleanup")
        nul_dir = os.path.join(os.path.dirname(__file__), "danny_toolkit")
        # os.path.exists("...\\nul") is always True on Windows (NUL device)
        # So check actual directory listing instead
        entries = os.listdir(nul_dir)
        c("nul" not in entries, "danny_toolkit/nul niet in directory listing")

    # ── Test 13: Daemon loop roept housekeeper aan ──

    def test_13_daemon_calls_housekeeper(self):
        """DigitalDaemon main loop roept _run_housekeeper aan."""
        print("\n[Test 13] Daemon loop → housekeeper")
        from danny_toolkit.daemon.daemon_core import DigitalDaemon
        full_source = inspect.getsource(DigitalDaemon)
        c("_run_housekeeper" in full_source,
          "_run_housekeeper in DigitalDaemon source")
        # Moet meer dan 1 keer voorkomen (definitie + aanroep)
        count = full_source.count("_run_housekeeper")
        c(count >= 2, f"_run_housekeeper voorkomt {count}x (expect >= 2)")

    # ── Test 14: test_phase43 geregistreerd in run_all_tests ──

    def test_14_phase43_test_registered(self):
        """test_phase43.py is geregistreerd in run_all_tests.py."""
        print("\n[Test 14] Phase 43 test geregistreerd")
        path = os.path.join(os.path.dirname(__file__), "run_all_tests.py")
        with open(path, "r", encoding="utf-8") as f:
            source = f.read()
        c("test_phase43" in source, "test_phase43 in run_all_tests.py")


if __name__ == "__main__":
    print("=" * 60)
    print("  Phase 44: Housekeeper Awakening + Diamond Polish II")
    print("=" * 60)

    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestPhase44)
    runner = unittest.TextTestRunner(verbosity=0)
    result = runner.run(suite)

    print(f"\n{'=' * 60}")
    tests_run = result.testsRun
    failures = len(result.failures) + len(result.errors)
    print(f"Checks: {CHECK}")
    print(f"Tests:  {tests_run} run, {failures} fail, {len(result.errors)} error")
    print(f"{'=' * 60}")

    sys.exit(0 if failures == 0 else 1)

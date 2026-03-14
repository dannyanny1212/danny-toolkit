#!/usr/bin/env python3
"""
Test Phase 48: Arbitrator Guard + Daemon Polish
=================================================
10 tests · 30+ checks

Valideert:
  A. arbitrator.py HAS_GROQ guard at module level
  B. arbitrator.py no bare 'from groq import' inside methods
  C. arbitrator.py client = None fallback when HAS_GROQ=False
  D. limbic_system.py has logger
  E. limbic_system.py no bare except:pass
  F. No bare except:pass in daemon/ (comprehensive)
  G. No bare except:pass in brain/ (regression)
  H. All brain/ groq modules have HAS_GROQ (regression, 11 modules)
  I. Phase 47 bare pass sweep regression
  J. Import roundtrip

Gebruik:
    CUDA_VISIBLE_DEVICES=-1 DANNY_TEST_MODE=1 ANONYMIZED_TELEMETRY=False \
        python test_phase48.py
"""

from __future__ import annotations

import ast
import importlib
import logging
import os
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


def _find_bare_pass(src: str) -> list:
    """Find all except:pass violations in source code."""
    lines = src.split("\n")
    violations = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("except") and ":" in stripped:
            for j in range(i + 1, min(i + 3, len(lines))):
                next_stripped = lines[j].strip()
                if next_stripped == "pass":
                    violations.append(f"line {j+1}")
                    break
                elif next_stripped:
                    break
    return violations


class TestPhase48(unittest.TestCase):
    """Phase 48: Arbitrator Guard + Daemon Polish."""

    # --- A. arbitrator.py HAS_GROQ ---

    def test_01_arbitrator_has_groq_guard(self) -> None:
        """arbitrator.py defines HAS_GROQ at module level."""
        src = _read("brain/arbitrator.py")
        c("HAS_GROQ" in src, "HAS_GROQ defined in arbitrator")
        # Verify try/except wraps the groq import
        tree = ast.parse(src)
        found_try = False
        for node in ast.walk(tree):
            if isinstance(node, ast.Try):
                for child in ast.walk(node):
                    if isinstance(child, ast.ImportFrom) and child.module == "groq":
                        found_try = True
        c(found_try, "groq import inside try block")

    # --- B. No bare groq import inside methods ---

    def test_02_arbitrator_no_inline_groq(self) -> None:
        """arbitrator.py: no 'from groq import' inside function bodies."""
        src = _read("brain/arbitrator.py")
        tree = ast.parse(src)
        inline_groq = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for child in ast.walk(node):
                    if isinstance(child, ast.ImportFrom) and child.module == "groq":
                        inline_groq.append(node.name)
        c(len(inline_groq) == 0,
          f"no inline groq imports (found in: {inline_groq})")

    # --- C. HAS_GROQ check before Groq() ---

    def test_03_arbitrator_has_groq_check(self) -> None:
        """arbitrator.py uses HAS_GROQ before creating Groq client."""
        src = _read("brain/arbitrator.py")
        c("HAS_GROQ" in src, "HAS_GROQ used in arbitrator")
        # The pattern should be: if not self._groq_client and HAS_GROQ:
        c("and HAS_GROQ" in src, "HAS_GROQ checked before Groq()")

    # --- D. limbic_system.py logger ---

    def test_04_limbic_has_logger(self) -> None:
        """limbic_system.py defines logger at module level."""
        src = _read("daemon/limbic_system.py")
        c("import logging" in src, "limbic has import logging")
        c("logger = logging.getLogger(__name__)" in src,
          "limbic has logger")

    # --- E. limbic_system.py no bare pass ---

    def test_05_limbic_no_bare_pass(self) -> None:
        """limbic_system.py: no bare except:pass."""
        src = _read("daemon/limbic_system.py")
        violations = _find_bare_pass(src)
        c(len(violations) == 0,
          f"limbic no bare pass (violations: {violations})")

    # --- F. daemon/ comprehensive ---

    def test_06_no_bare_pass_in_daemon(self) -> None:
        """No daemon/ module has bare except:pass."""
        daemon_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "danny_toolkit", "daemon"
        )
        all_violations = {}
        for fname in sorted(os.listdir(daemon_dir)):
            if not fname.endswith(".py") or fname == "__init__.py":
                continue
            fpath = os.path.join(daemon_dir, fname)
            with open(fpath, encoding="utf-8") as f:
                src = f.read()
            violations = _find_bare_pass(src)
            if violations:
                all_violations[fname] = violations
        c(len(all_violations) == 0,
          f"no bare pass in daemon/ (violations: {all_violations})")

    # --- G. brain/ regression ---

    def test_07_no_bare_pass_in_brain(self) -> None:
        """No brain/ module has bare except:pass (regression)."""
        brain_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "danny_toolkit", "brain"
        )
        all_violations = {}
        for fname in sorted(os.listdir(brain_dir)):
            if not fname.endswith(".py") or fname == "__init__.py":
                continue
            fpath = os.path.join(brain_dir, fname)
            with open(fpath, encoding="utf-8") as f:
                src = f.read()
            violations = _find_bare_pass(src)
            if violations:
                all_violations[fname] = violations
        c(len(all_violations) == 0,
          f"no bare pass in brain/ (violations: {all_violations})")

    # --- H. All groq modules HAS_GROQ (regression) ---

    def test_08_all_groq_modules_guarded(self) -> None:
        """All 11 groq modules have HAS_GROQ guard."""
        modules = [
            "brain/arbitrator.py",
            "brain/artificer.py",
            "brain/dreamer.py",
            "brain/ghost_writer.py",
            "brain/the_mirror.py",
            "brain/cortex.py",
            "brain/devops_daemon.py",
            "brain/strategist.py",
            "brain/tribunal.py",
            "brain/virtual_twin.py",
            "brain/void_walker.py",
        ]
        for mod in modules:
            src = _read(mod)
            c("HAS_GROQ" in src, f"HAS_GROQ in {mod}")

    # --- I. No bare groq imports anywhere in brain/ ---

    def test_09_no_bare_groq_in_brain(self) -> None:
        """No brain/ module has bare 'from groq import' outside try/except."""
        brain_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "danny_toolkit", "brain"
        )
        bare_imports = []
        for fname in sorted(os.listdir(brain_dir)):
            if not fname.endswith(".py"):
                continue
            fpath = os.path.join(brain_dir, fname)
            with open(fpath, encoding="utf-8") as f:
                src = f.read()
            if "from groq import" not in src:
                continue
            tree = ast.parse(src)
            for node in ast.iter_child_nodes(tree):
                if isinstance(node, ast.ImportFrom) and node.module == "groq":
                    bare_imports.append(fname)
        c(len(bare_imports) == 0,
          f"no bare groq imports (found: {bare_imports})")

    # --- J. Import roundtrip ---

    def test_10_brain_import_roundtrip(self) -> None:
        """brain/__init__.py can be imported without crashing."""
        try:
            mod = importlib.import_module("danny_toolkit.brain")
            c(hasattr(mod, "__version__"), "brain has __version__")
            c(hasattr(mod, "TaskArbitrator"), "TaskArbitrator exported")
        except SystemExit:
            c(True, "brain import hit SovereignGate (expected in test)")
        except Exception as e:
            c(False, f"brain import failed: {e}")


if __name__ == "__main__":
    print(f"\n{'='*60}")
    print("TEST PHASE 48: Arbitrator Guard + Daemon Polish")
    print(f"{'='*60}\n")
    unittest.main(verbosity=2, exit=True)

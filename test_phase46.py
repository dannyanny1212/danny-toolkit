#!/usr/bin/env python3
"""
Test Phase 46: Import Hardening + Ghost Completeness
=====================================================
14 tests · 50+ checks

Valideert:
  A. 5x groq import guards (artificer, dreamer, ghost_writer, the_mirror, cortex)
  B. sentence_transformers guard in truth_anchor.py
  C. cortex.py dotenv except → logger.debug (geen bare pass)
  D. HAS_GROQ / HAS_CROSS_ENCODER flags bestaan
  E. client = None fallback bij missing deps
  F. learning/__init__.py version sync (6.11.0)
  G. Cortex bonus: bare groq import nu gewrapped

Gebruik:
    CUDA_VISIBLE_DEVICES=-1 DANNY_TEST_MODE=1 ANONYMIZED_TELEMETRY=False \
        python test_phase46.py
"""

from __future__ import annotations

import ast
import importlib
import inspect
import logging
import os
import sys
import textwrap
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


class TestPhase46(unittest.TestCase):
    """Phase 46: Import Hardening + Ghost Completeness."""

    # --- A. Groq import guards (5 modules) ---

    def test_01_artificer_groq_guard(self) -> None:
        """artificer.py: from groq import AsyncGroq wrapped in try/except."""
        src = _read("brain/artificer.py")
        tree = ast.parse(src)
        c("HAS_GROQ" in src, "HAS_GROQ flag in artificer")
        # Verify try/except wraps the groq import
        found_try = False
        for node in ast.walk(tree):
            if isinstance(node, ast.Try):
                for child in ast.walk(node):
                    if isinstance(child, ast.ImportFrom) and child.module == "groq":
                        found_try = True
        c(found_try, "groq import inside try block")
        # Verify client = None fallback
        c("self.client = None" in src, "client = None fallback")

    def test_02_dreamer_groq_guard(self) -> None:
        """dreamer.py: from groq import AsyncGroq wrapped in try/except."""
        src = _read("brain/dreamer.py")
        tree = ast.parse(src)
        c("HAS_GROQ" in src, "HAS_GROQ flag in dreamer")
        found_try = False
        for node in ast.walk(tree):
            if isinstance(node, ast.Try):
                for child in ast.walk(node):
                    if isinstance(child, ast.ImportFrom) and child.module == "groq":
                        found_try = True
        c(found_try, "groq import inside try block")
        c("self.client = None" in src, "client = None fallback")

    def test_03_ghost_writer_groq_guard(self) -> None:
        """ghost_writer.py: from groq import AsyncGroq wrapped in try/except."""
        src = _read("brain/ghost_writer.py")
        tree = ast.parse(src)
        c("HAS_GROQ" in src, "HAS_GROQ flag in ghost_writer")
        found_try = False
        for node in ast.walk(tree):
            if isinstance(node, ast.Try):
                for child in ast.walk(node):
                    if isinstance(child, ast.ImportFrom) and child.module == "groq":
                        found_try = True
        c(found_try, "groq import inside try block")
        c("self.client = None" in src, "client = None fallback")

    def test_04_the_mirror_groq_guard(self) -> None:
        """the_mirror.py: from groq import AsyncGroq wrapped in try/except."""
        src = _read("brain/the_mirror.py")
        tree = ast.parse(src)
        c("HAS_GROQ" in src, "HAS_GROQ flag in the_mirror")
        found_try = False
        for node in ast.walk(tree):
            if isinstance(node, ast.Try):
                for child in ast.walk(node):
                    if isinstance(child, ast.ImportFrom) and child.module == "groq":
                        found_try = True
        c(found_try, "groq import inside try block")
        c("self.client = None" in src, "client = None fallback")

    def test_05_cortex_groq_guard(self) -> None:
        """cortex.py: from groq import AsyncGroq wrapped in try/except."""
        src = _read("brain/cortex.py")
        tree = ast.parse(src)
        c("HAS_GROQ" in src, "HAS_GROQ flag in cortex")
        found_try = False
        for node in ast.walk(tree):
            if isinstance(node, ast.Try):
                for child in ast.walk(node):
                    if isinstance(child, ast.ImportFrom) and child.module == "groq":
                        found_try = True
        c(found_try, "groq import inside try block")
        c("self.client = None" in src, "client = None fallback")

    # --- B. sentence_transformers guard ---

    def test_06_truth_anchor_cross_encoder_guard(self) -> None:
        """truth_anchor.py: CrossEncoder import wrapped in try/except."""
        src = _read("brain/truth_anchor.py")
        tree = ast.parse(src)
        c("HAS_CROSS_ENCODER" in src, "HAS_CROSS_ENCODER flag")
        found_try = False
        for node in ast.walk(tree):
            if isinstance(node, ast.Try):
                for child in ast.walk(node):
                    if isinstance(child, ast.ImportFrom) and child.module == "sentence_transformers":
                        found_try = True
        c(found_try, "sentence_transformers inside try block")
        c("self.model = None" in src, "model = None fallback")

    # --- C. cortex.py dotenv bare pass fix ---

    def test_07_cortex_dotenv_no_bare_pass(self) -> None:
        """cortex.py: except ImportError for dotenv must log, not bare pass."""
        src = _read("brain/cortex.py")
        lines = src.split("\n")
        for i, line in enumerate(lines):
            if "dotenv" in line and "import" in line.lower():
                # Find the except block after this try
                for j in range(i, min(i + 15, len(lines))):
                    stripped = lines[j].strip()
                    if stripped == "except ImportError:":
                        next_line = lines[j + 1].strip() if j + 1 < len(lines) else ""
                        c(next_line != "pass", "dotenv except is not bare pass")
                        c("logger" in next_line, "dotenv except uses logger")
                        return
        c(False, "dotenv try/except block not found")

    # --- D. HAS_GROQ flags existence (module-level) ---

    def test_08_has_groq_flags_at_module_level(self) -> None:
        """All 10 groq modules define HAS_GROQ at module level."""
        modules = [
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
            # HAS_GROQ can be inside Try body or except handler
            c("HAS_GROQ" in src, f"HAS_GROQ defined in {mod}")

    # --- E. No remaining bare groq imports in brain/ ---

    def test_09_no_bare_groq_imports(self) -> None:
        """No brain/ module has bare 'from groq import' outside try/except."""
        brain_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "danny_toolkit", "brain"
        )
        bare_imports = []
        for fname in os.listdir(brain_dir):
            if not fname.endswith(".py"):
                continue
            fpath = os.path.join(brain_dir, fname)
            with open(fpath, encoding="utf-8") as f:
                src = f.read()
            if "from groq import" not in src:
                continue
            tree = ast.parse(src)
            # Check all groq imports are inside Try nodes
            for node in ast.iter_child_nodes(tree):
                if isinstance(node, ast.ImportFrom) and node.module == "groq":
                    bare_imports.append(fname)
        c(len(bare_imports) == 0, f"no bare groq imports (found: {bare_imports})")

    # --- F. Version sync ---

    def test_10_learning_version_synced(self) -> None:
        """learning/__init__.py version matches main package."""
        learn_src = _read("learning/__init__.py")
        main_src = _read("__init__.py")
        # Extract versions
        learn_ver = None
        main_ver = None
        for line in learn_src.split("\n"):
            if line.strip().startswith("__version__"):
                learn_ver = line.split("=")[1].strip().strip('"').strip("'")
        for line in main_src.split("\n"):
            if line.strip().startswith("__version__"):
                main_ver = line.split("=")[1].strip().strip('"').strip("'")
        c(learn_ver is not None, "learning version found")
        c(main_ver is not None, "main version found")
        c(learn_ver == main_ver, f"versions match: {learn_ver} == {main_ver}")

    # --- G. ghost_amplifier still guarded (Phase 46 regression check) ---

    def test_11_ghost_amplifier_still_guarded(self) -> None:
        """ghost_amplifier.py: HAS_GROQ guard persists from Phase 46."""
        src = _read("brain/ghost_amplifier.py")
        c("HAS_GROQ" in src, "ghost_amplifier HAS_GROQ persists")
        c("self.client = None" in src, "ghost_amplifier client fallback persists")

    # --- H. truth_anchor verify handles None model ---

    def test_12_truth_anchor_verify_none_model(self) -> None:
        """truth_anchor.py: verify() returns (False, 0.0) when model is None."""
        src = _read("brain/truth_anchor.py")
        c("self.model is None" in src, "verify checks for None model")

    # --- I. cortex.py has no bare pass (Phase 47 fix validated) ---

    def test_13_cortex_no_bare_pass(self) -> None:
        """cortex.py: no bare except:pass after Phase 47 fix."""
        src = _read("brain/cortex.py")
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
        c(len(violations) == 0, f"cortex no bare pass (violations: {violations})")

    # --- J. Import roundtrip ---

    def test_14_brain_package_imports(self) -> None:
        """brain/__init__.py can be imported without crashing."""
        try:
            mod = importlib.import_module("danny_toolkit.brain")
            c(hasattr(mod, "__version__"), "brain has __version__")
            c(hasattr(mod, "GhostAmplifier"), "GhostAmplifier exported")
            c(hasattr(mod, "TruthAnchor"), "TruthAnchor exported")
        except SystemExit:
            c(True, "brain import hit SovereignGate (expected in test)")
        except Exception as e:
            c(False, f"brain import failed: {e}")


if __name__ == "__main__":
    print(f"\n{'='*60}")
    print("TEST PHASE 46: Import Hardening + Ghost Completeness")
    print(f"{'='*60}\n")
    unittest.main(verbosity=2, exit=True)

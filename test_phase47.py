#!/usr/bin/env python3
"""
Test Phase 47: Diamond Polish III — Bare Pass Sweep
=====================================================
10 tests · 40+ checks

Valideert:
  A. Geen bare except:pass in brain/ (comprehensive sweep)
  B. Geen bare except:pass in core/config.py en core/env_bootstrap.py
  C. Alle dotenv blocks loggen via logger.debug()
  D. central_brain.py heeft logger
  E. unified_memory.py heeft logger
  F. tribunal.py logger verplaatst boven dotenv
  G. env_bootstrap.py heeft logger
  H. Regression: Phase 47 groq guards intact

Gebruik:
    CUDA_VISIBLE_DEVICES=-1 DANNY_TEST_MODE=1 ANONYMIZED_TELEMETRY=False \
        python test_phase47.py
"""

from __future__ import annotations

import ast
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


class TestPhase47(unittest.TestCase):
    """Phase 47: Diamond Polish III — Bare Pass Sweep."""

    # --- A. Comprehensive brain/ sweep ---

    def test_01_no_bare_pass_in_brain(self) -> None:
        """No brain/ module has bare except:pass."""
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

    # --- B. core/ sweep ---

    def test_02_no_bare_pass_in_config(self) -> None:
        """core/config.py: no bare except:pass."""
        src = _read("core/config.py")
        violations = _find_bare_pass(src)
        c(len(violations) == 0, f"config.py clean (violations: {violations})")

    def test_03_no_bare_pass_in_env_bootstrap(self) -> None:
        """core/env_bootstrap.py: no bare except:pass."""
        src = _read("core/env_bootstrap.py")
        violations = _find_bare_pass(src)
        c(len(violations) == 0, f"env_bootstrap.py clean (violations: {violations})")

    # --- C. dotenv blocks log ---

    def test_04_dotenv_blocks_log(self) -> None:
        """All dotenv except blocks use logger.debug()."""
        dotenv_files = [
            "brain/central_brain.py",
            "brain/cortex.py",
            "brain/tribunal.py",
            "brain/strategist.py",
            "core/config.py",
            "core/env_bootstrap.py",
        ]
        for mod in dotenv_files:
            src = _read(mod)
            lines = src.split("\n")
            for i, line in enumerate(lines):
                if "dotenv" in line and "import" in line.lower():
                    # Find the except block
                    for j in range(i, min(i + 15, len(lines))):
                        stripped = lines[j].strip()
                        if stripped.startswith("except") and "ImportError" in stripped:
                            next_line = lines[j + 1].strip() if j + 1 < len(lines) else ""
                            c(next_line != "pass", f"{mod} dotenv not bare pass")
                            c("logger" in next_line, f"{mod} dotenv uses logger")
                            break
                    break

    # --- D. Logger presence in fixed modules ---

    def test_05_central_brain_has_logger(self) -> None:
        """central_brain.py defines logger at module level."""
        src = _read("brain/central_brain.py")
        c("logger = logging.getLogger(__name__)" in src,
          "central_brain has logger")

    def test_06_unified_memory_has_logger(self) -> None:
        """unified_memory.py defines logger at module level."""
        src = _read("brain/unified_memory.py")
        c("logger = logging.getLogger(__name__)" in src,
          "unified_memory has logger")

    def test_07_tribunal_logger_before_dotenv(self) -> None:
        """tribunal.py: logger defined before dotenv block."""
        src = _read("brain/tribunal.py")
        logger_pos = src.find("logger = logging.getLogger(__name__)")
        dotenv_pos = src.find("from dotenv import load_dotenv")
        c(logger_pos != -1, "tribunal has logger")
        c(dotenv_pos == -1 or logger_pos < dotenv_pos,
          "tribunal logger before dotenv")

    def test_08_env_bootstrap_has_logger(self) -> None:
        """env_bootstrap.py defines logger at module level."""
        src = _read("core/env_bootstrap.py")
        c("logger = logging.getLogger(__name__)" in src,
          "env_bootstrap has logger")

    # --- E. Regression: groq guards intact ---

    def test_09_groq_guards_intact(self) -> None:
        """All 10 groq modules still have HAS_GROQ guard."""
        modules = [
            "brain/artificer.py", "brain/dreamer.py",
            "brain/ghost_writer.py", "brain/the_mirror.py",
            "brain/cortex.py", "brain/devops_daemon.py",
            "brain/strategist.py", "brain/tribunal.py",
            "brain/virtual_twin.py", "brain/void_walker.py",
        ]
        for mod in modules:
            src = _read(mod)
            c("HAS_GROQ" in src, f"HAS_GROQ in {mod}")

    # --- F. Specific fixes validated ---

    def test_10_specific_fixes(self) -> None:
        """Key fixes validated: JSON parse, KeyError, OSError, ValueError."""
        # oracle.py — JSON parse logs
        oracle = _read("brain/oracle.py")
        c("Oracle list direct parse failed" in oracle, "oracle list parse logs")
        c("Oracle dict direct parse failed" in oracle, "oracle dict parse logs")

        # trinity_omega.py — KeyError logs
        trinity = _read("brain/trinity_omega.py")
        c("Unknown CosmicRole" in trinity, "trinity KeyError logs")

        # governor_state.py — OSError logs
        gov = _read("brain/governor_state.py")
        c("Governor backup rotation failed" in gov, "governor OSError logs")

        # singularity.py — ValueError logs
        sing = _read("brain/singularity.py")
        c("Tuner latency parse" in sing, "singularity ValueError logs")

        # central_brain.py — JSON parse logs
        cb = _read("brain/central_brain.py")
        c("Function call parse attempt failed" in cb, "central_brain JSON logs")


if __name__ == "__main__":
    print(f"\n{'='*60}")
    print("TEST PHASE 47: Diamond Polish III — Bare Pass Sweep")
    print(f"{'='*60}\n")
    unittest.main(verbosity=2, exit=True)

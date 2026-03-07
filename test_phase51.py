#!/usr/bin/env python3
"""
Test Phase 51: Type-Hint Hardening + Version Sync
==================================================
10 tests · 30+ checks

Valideert:
  A. virtual_twin.py AsyncGroq type hints are string literals
  B. 7 modules have from __future__ import annotations
  C. No bare X | None in runtime class annotations without future import
  D. Version sync: learning/__init__.py matches brain/__init__.py
  E. No bare AsyncGroq/Groq type hints outside try/except guards
  F. Future annotations don't break imports

Gebruik:
    CUDA_VISIBLE_DEVICES=-1 DANNY_TEST_MODE=1 ANONYMIZED_TELEMETRY=False \
        python test_phase51.py
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


class TestPhase51(unittest.TestCase):
    """Phase 51: Type-Hint Hardening + Version Sync."""

    # --- A. AsyncGroq string literals ---

    def test_01_virtual_twin_asyncgroq_string_hints(self):
        """virtual_twin.py uses string literal type hints for AsyncGroq."""
        src = _read("brain/virtual_twin.py")
        # Should use -> "AsyncGroq" (quoted), not -> AsyncGroq (bare)
        c('"AsyncGroq"' in src, 'uses "AsyncGroq" string literal')
        # Should NOT have bare -> AsyncGroq: (unquoted) in method signatures
        lines = src.split("\n")
        bare_hints = [
            (i + 1, line.strip())
            for i, line in enumerate(lines)
            if ") -> AsyncGroq:" in line and '"AsyncGroq"' not in line
        ]
        c(len(bare_hints) == 0, f"no bare AsyncGroq hints (found: {bare_hints})")

    # --- B. Future annotations in 7 modules ---

    def test_02_future_annotations_embeddings(self):
        """core/embeddings.py has from __future__ import annotations."""
        src = _read("core/embeddings.py")
        c("from __future__ import annotations" in src, "embeddings.py")

    def test_03_future_annotations_remaining(self):
        """6 other modules have from __future__ import annotations."""
        modules = [
            "core/groq_retry.py",
            "brain/file_guard.py",
            "quests/listener_protocol.py",
            "core/vram_manager.py",
            "core/web_scraper.py",
            "brain/security/utils.py",
        ]
        for mod in modules:
            src = _read(mod)
            c("from __future__ import annotations" in src, mod)

    # --- C. No bare X | None without future import ---

    def test_04_no_unsafe_union_syntax(self):
        """No module uses X | None syntax without from __future__ import annotations."""
        import re
        # Scan all .py files in brain/ and core/ for X | None
        for subdir in ["brain", "core"]:
            base = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "danny_toolkit", subdir,
            )
            for root_dir, _, files in os.walk(base):
                for fname in files:
                    if not fname.endswith(".py"):
                        continue
                    fpath = os.path.join(root_dir, fname)
                    with open(fpath, encoding="utf-8") as f:
                        content = f.read()
                    # Check if file uses union syntax
                    if re.search(r'\w+ \| None', content):
                        has_future = "from __future__ import annotations" in content
                        rel = os.path.relpath(fpath, os.path.dirname(os.path.abspath(__file__)))
                        c(has_future, f"{rel} has future annotations (uses X | None)")

    # --- D. Version sync ---

    def test_05_version_sync(self):
        """learning/__init__.py version matches brain/__init__.py."""
        brain_src = _read("brain/__init__.py")
        learning_root = _read_root("learning/__init__.py")
        # Extract versions
        import re
        brain_ver = re.search(r'__version__\s*=\s*"([^"]+)"', brain_src)
        learn_ver = re.search(r'__version__\s*=\s*"([^"]+)"', learning_root)
        c(brain_ver is not None, "brain has __version__")
        c(learn_ver is not None, "learning has __version__")
        if brain_ver and learn_ver:
            c(brain_ver.group(1) == learn_ver.group(1),
              f"versions match: brain={brain_ver.group(1)} learning={learn_ver.group(1)}")

    # --- E. No bare Groq type hints in function signatures ---

    def test_06_no_bare_groq_type_hints(self):
        """No function signatures use bare AsyncGroq/Groq without string quotes."""
        import re
        modules_with_groq = [
            "brain/virtual_twin.py",
            "brain/arbitrator.py",
        ]
        for mod in modules_with_groq:
            src = _read(mod)
            lines = src.split("\n")
            bare = []
            for i, line in enumerate(lines):
                stripped = line.strip()
                # Match: ) -> AsyncGroq: or ) -> Groq: without quotes
                if re.search(r'\)\s*->\s*(?:Async)?Groq\s*:', stripped):
                    if '"AsyncGroq"' not in stripped and '"Groq"' not in stripped:
                        bare.append(f"line {i+1}: {stripped}")
            c(len(bare) == 0, f"{mod} no bare Groq hints ({bare})")

    # --- F. Future annotations don't break imports ---

    def test_07_embeddings_import(self):
        """embeddings.py can be imported without errors."""
        try:
            from danny_toolkit.core.embeddings import mrl_truncate
            c(callable(mrl_truncate), "mrl_truncate importable")
        except Exception as e:
            c(False, f"import failed: {e}")

    def test_08_vram_manager_import(self):
        """vram_manager.py can be imported without errors."""
        try:
            from danny_toolkit.core.vram_manager import vram_guard, get_vram_guard
            c(callable(get_vram_guard), "get_vram_guard importable")
            c(vram_guard is not None, "vram_guard importable")
        except Exception as e:
            c(False, f"import failed: {e}")

    def test_09_groq_retry_import(self):
        """groq_retry.py can be imported without errors."""
        try:
            from danny_toolkit.core import groq_retry
            c(groq_retry is not None, "groq_retry importable")
        except Exception as e:
            c(False, f"import failed: {e}")

    def test_10_file_guard_import(self):
        """file_guard.py can be imported without errors."""
        try:
            from danny_toolkit.brain.file_guard import FileGuard
            c(FileGuard is not None, "FileGuard importable")
        except Exception as e:
            c(False, f"import failed: {e}")


if __name__ == "__main__":
    print(f"\n{'='*60}")
    print("TEST PHASE 51: Type-Hint Hardening + Version Sync")
    print(f"{'='*60}\n")
    unittest.main(verbosity=2, exit=True)

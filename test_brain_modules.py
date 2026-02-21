"""
Danny Toolkit — Brain Module Tests (Phase 11C)
GhostWriter, TheMirror, TheOracleEye

8 tests, ~45+ checks. Alle CPU-only, geen Groq API calls.
Gebruik: python test_brain_modules.py
"""

import asyncio
import inspect
import json
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Windows UTF-8
if os.name == "nt":
    sys.stdout = open(
        sys.stdout.fileno(), mode="w",
        encoding="utf-8", errors="replace",
        closefd=False,
    )

# Project root op sys.path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

PASS_COUNT = 0
FAIL_COUNT = 0


def check(label, condition):
    global PASS_COUNT, FAIL_COUNT
    if condition:
        PASS_COUNT += 1
        print(f"  ✅ {label}")
    else:
        FAIL_COUNT += 1
        print(f"  ❌ {label}")


# ── HELPERS ──

class FakeStack:
    """Minimale CorticalStack stub met in-memory SQLite."""
    def __init__(self):
        self._conn = sqlite3.connect(":memory:")
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS episodic_memory (
                id INTEGER PRIMARY KEY,
                timestamp TEXT,
                actor TEXT,
                action TEXT,
                details TEXT,
                source TEXT
            )
        """)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS system_stats (
                id INTEGER PRIMARY KEY,
                timestamp TEXT,
                metric TEXT,
                value REAL
            )
        """)
        self._conn.commit()

    def get_recent_events(self, count=10):
        return []

    def log_event(self, **kwargs):
        pass

    def flush(self):
        pass

    def remember_fact(self, key, value, conf):
        pass

    def recall_all(self, min_confidence=0.0):
        return []

    def search_events(self, query, limit=5):
        return []


def _make_fake_stack():
    return FakeStack()


# ── TESTS ──

class TestGhostWriter(unittest.TestCase):
    """Tests voor GhostWriter (Invention #9)."""

    def test_ghost_writer_init(self):
        """GhostWriter importeerbaar, haunt() en _inspect_file() zijn async."""
        print("\n🧪 test_ghost_writer_init")
        from danny_toolkit.brain.ghost_writer import GhostWriter

        check("GhostWriter importeerbaar", True)

        gw = GhostWriter()
        check("haunt() is coroutine",
              asyncio.iscoroutinefunction(gw.haunt))
        check("_inspect_file() is coroutine",
              asyncio.iscoroutinefunction(gw._inspect_file))
        check("watch_dir bevat danny_toolkit",
              "danny_toolkit" in gw.watch_dir)
        check("client is AsyncGroq",
              type(gw.client).__name__ == "AsyncGroq")
        check("model is llama-4-scout or qwen3",
              "llama-4-scout" in gw.model or "qwen" in gw.model)

    def test_ghost_writer_ast_scan(self):
        """_inspect_file() vindt functies zonder docstring."""
        print("\n🧪 test_ghost_writer_ast_scan")
        from danny_toolkit.brain.ghost_writer import GhostWriter

        # Maak een temp .py bestand met functies
        code = (
            "def has_doc():\n"
            "    '''Ik heb een docstring.'''\n"
            "    pass\n\n"
            "def no_doc():\n"
            "    pass\n\n"
            "def also_no_doc(x):\n"
            "    return x + 1\n"
        )
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False,
            encoding="utf-8",
        ) as f:
            f.write(code)
            tmp_path = f.name

        try:
            gw = GhostWriter()
            # Mock de Groq client zodat _generate_docstring niet echt aanroept
            found_undoc = []
            original_generate = gw._generate_docstring

            async def fake_generate(node, source):
                found_undoc.append(node.name)
                return "Fake docstring"

            gw._generate_docstring = fake_generate
            asyncio.run(gw._inspect_file(tmp_path))

            check("Vindt undocumented functions",
                  len(found_undoc) >= 2)
            check("no_doc gevonden",
                  "no_doc" in found_undoc)
            check("also_no_doc gevonden",
                  "also_no_doc" in found_undoc)
            check("has_doc NIET gevonden",
                  "has_doc" not in found_undoc)
        finally:
            os.unlink(tmp_path)


class TestTheMirror(unittest.TestCase):
    """Tests voor TheMirror (Invention #8)."""

    def test_the_mirror_init(self):
        """TheMirror importeerbaar, reflect() is async."""
        print("\n🧪 test_the_mirror_init")
        from danny_toolkit.brain.the_mirror import TheMirror

        check("TheMirror importeerbaar", True)

        m = TheMirror()
        check("reflect() is coroutine",
              asyncio.iscoroutinefunction(m.reflect))
        check("profile_path bevat user_profile.json",
              "user_profile.json" in str(m.profile_path))
        check("load_profile() returns dict",
              isinstance(m.load_profile(), dict))
        check("client is AsyncGroq",
              type(m.client).__name__ == "AsyncGroq")

    def test_the_mirror_load_save(self):
        """save_profile() + load_profile() round-trip."""
        print("\n🧪 test_the_mirror_load_save")
        from danny_toolkit.brain.the_mirror import TheMirror

        m = TheMirror()

        # Gebruik temp file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False,
        ) as f:
            tmp_path = f.name

        try:
            m.profile_path = Path(tmp_path)

            test_data = {
                "coding_style": "async-first",
                "knowledge_level": "expert",
                "current_goal": "build jarvis",
                "tone_preference": "direct",
            }
            # save_profile verwacht een JSON string
            m.save_profile(json.dumps(test_data))

            loaded = m.load_profile()
            check("Round-trip werkt",
                  loaded == test_data)
            check("coding_style correct",
                  loaded.get("coding_style") == "async-first")
            check("knowledge_level correct",
                  loaded.get("knowledge_level") == "expert")
            check("get_context_injection() returns string",
                  isinstance(m.get_context_injection(), str))
            check("Context injection bevat 'async-first'",
                  "async-first" in m.get_context_injection())
        finally:
            os.unlink(tmp_path)


class TestOracleEye(unittest.TestCase):
    """Tests voor TheOracleEye (Invention #18)."""

    def test_oracle_eye_init(self):
        """TheOracleEye importeerbaar, HourForecast velden."""
        print("\n🧪 test_oracle_eye_init")
        from danny_toolkit.brain.oracle_eye import (
            TheOracleEye, HourForecast,
        )

        check("TheOracleEye importeerbaar", True)
        check("HourForecast importeerbaar", True)

        # HourForecast velden
        fields = {
            f.name for f in
            HourForecast.__dataclass_fields__.values()
        }
        for expected in [
            "uur", "verwachte_queries", "verwachte_cpu",
            "verwachte_ram", "aanbevolen_model", "confidence",
        ]:
            check(f"HourForecast has field '{expected}'",
                  expected in fields)

        # generate_daily_forecast method exists
        check("generate_daily_forecast() exists",
              hasattr(TheOracleEye, "generate_daily_forecast"))
        check("forecast_next_hours() exists",
              hasattr(TheOracleEye, "forecast_next_hours"))

    @patch(
        "danny_toolkit.brain.oracle_eye.get_cortical_stack",
        side_effect=lambda: _make_fake_stack(),
    )
    @patch(
        "danny_toolkit.brain.oracle_eye.HAS_STACK",
        True,
    )
    def test_oracle_eye_patterns_empty(
        self, mock_stack, *args
    ):
        """analyze_patterns() met lege stack geeft lege/24-uur dict."""
        print("\n🧪 test_oracle_eye_patterns_empty")
        from danny_toolkit.brain.oracle_eye import TheOracleEye

        eye = TheOracleEye()
        eye._stack = _make_fake_stack()
        eye._cache = {}

        patterns = eye.analyze_patterns(days=7)
        check("analyze_patterns returns dict",
              isinstance(patterns, dict))
        check("24 uren in result",
              len(patterns) == 24)
        check("Uur 0 avg_queries is 0",
              patterns.get(0, {}).get("avg_queries", -1) == 0.0)

    def test_oracle_eye_model_advice(self):
        """_kies_model() returns correct model at different loads."""
        print("\n🧪 test_oracle_eye_model_advice")
        from danny_toolkit.brain.oracle_eye import TheOracleEye

        eye = TheOracleEye.__new__(TheOracleEye)
        eye._HIGH_CPU_THRESHOLD = 70.0
        eye._HIGH_QUERY_THRESHOLD = 50

        # Lage belasting → primary (llama-4-scout)
        model_low = eye._kies_model(30.0, 10)
        check("Low load -> llama-4-scout",
              "llama-4-scout" in model_low)

        # Hoge CPU → fallback (qwen3-32b)
        model_high_cpu = eye._kies_model(80.0, 10)
        check("High CPU -> qwen3-32b",
              "qwen3-32b" in model_high_cpu)

        # Hoge queries → fallback (qwen3-32b)
        model_high_q = eye._kies_model(30.0, 60)
        check("High queries -> qwen3-32b",
              "qwen3-32b" in model_high_q)

        # Beide hoog → fallback (qwen3-32b)
        model_both = eye._kies_model(90.0, 100)
        check("Both high -> qwen3-32b",
              "qwen3-32b" in model_both)

        # Grenswaarden (exact threshold = not exceeded → primary)
        model_edge = eye._kies_model(70.0, 50)
        check("Edge case (exact threshold) -> llama-4-scout",
              "llama-4-scout" in model_edge)

    @patch(
        "danny_toolkit.brain.oracle_eye.get_cortical_stack",
        side_effect=lambda: _make_fake_stack(),
    )
    @patch(
        "danny_toolkit.brain.oracle_eye.HAS_STACK",
        True,
    )
    def test_cortex_get_stats(self, mock_stack, *args):
        """TheCortex.get_stats() returns 6 keys."""
        print("\n🧪 test_cortex_get_stats")
        from danny_toolkit.brain.cortex import TheCortex

        with patch(
            "danny_toolkit.brain.cortex.get_cortical_stack",
            side_effect=lambda: _make_fake_stack(),
        ), patch(
            "danny_toolkit.brain.cortex.HAS_STACK",
            True,
        ):
            cortex = TheCortex()
            cortex._stack = _make_fake_stack()
            # Maak tabellen op de fake stack
            cortex._ensure_tables()

            stats = cortex.get_stats()
            check("get_stats returns dict",
                  isinstance(stats, dict))
            expected_keys = [
                "graph_nodes", "graph_edges",
                "db_entities", "db_triples",
                "has_networkx", "has_stack",
            ]
            for key in expected_keys:
                check(f"stats has key '{key}'",
                      key in stats)
            check("db_entities is int",
                  isinstance(stats.get("db_entities", None), int))


# ── RUNNER ──

if __name__ == "__main__":
    print("=" * 60)
    print("  BRAIN MODULE TESTS (Phase 11C)")
    print("  GhostWriter, TheMirror, TheOracleEye, TheCortex")
    print("=" * 60)

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(TestGhostWriter))
    suite.addTests(loader.loadTestsFromTestCase(TestTheMirror))
    suite.addTests(loader.loadTestsFromTestCase(TestOracleEye))

    runner = unittest.TextTestRunner(verbosity=0)
    result = runner.run(suite)

    print(f"\n{'=' * 60}")
    print(f"  Checks: {PASS_COUNT} passed, {FAIL_COUNT} failed")
    total_tests = result.testsRun
    failures = len(result.failures) + len(result.errors)
    print(f"  Tests:  {total_tests - failures}/{total_tests} passed")
    print(f"{'=' * 60}")

    sys.exit(0 if failures == 0 and FAIL_COUNT == 0 else 1)

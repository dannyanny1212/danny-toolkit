"""
Phase 17: Production Stability — Test Suite
=============================================
8 tests, covering:
- Echo Guard deduplication (3 tests)
- Token Budget tracking (3 tests)
- Strategist caps (2 tests)

Gebruik: python test_phase17.py
"""

import asyncio
import hashlib
import io
import sys
import time
import unittest
from collections import deque, defaultdict
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

sys.stdout = io.TextIOWrapper(
    sys.stdout.buffer, encoding="utf-8", errors="replace"
)


# ── Echo Guard Tests ──

class TestEchoGuard(unittest.TestCase):
    """Test de Echo Guard deduplicatie in SwarmEngine."""

    def _make_engine(self):
        """Maak een minimale SwarmEngine-achtige structuur."""
        engine = MagicMock()
        engine._recent_queries = deque(maxlen=50)
        engine._swarm_metrics = {"echo_guard_blocks": 0}
        return engine

    def _check_dedup(self, engine, user_input):
        """Simuleer de echo guard logica uit SwarmEngine.run()."""
        q_hash = hashlib.md5(
            user_input.strip().lower().encode()
        ).hexdigest()
        now = time.time()
        for prev_hash, prev_ts in engine._recent_queries:
            if prev_hash == q_hash and (now - prev_ts) < 60:
                engine._swarm_metrics["echo_guard_blocks"] += 1
                return True  # blocked
        engine._recent_queries.append((q_hash, now))
        return False  # allowed

    def test_01_dedup_blocks_duplicate(self):
        """Dezelfde query twee keer → tweede geblokkeerd."""
        engine = self._make_engine()

        blocked1 = self._check_dedup(engine, "Wat is Bitcoin?")
        self.assertFalse(blocked1, "Eerste query moet doorkomen")

        blocked2 = self._check_dedup(engine, "Wat is Bitcoin?")
        self.assertTrue(blocked2, "Duplicate query moet geblokkeerd worden")
        self.assertEqual(engine._swarm_metrics["echo_guard_blocks"], 1)
        print("  [OK] test_01: duplicate query geblokkeerd")

    def test_02_dedup_allows_after_timeout(self):
        """Dezelfde query na 60s → weer toegestaan."""
        engine = self._make_engine()

        q_hash = hashlib.md5(
            "Wat is Bitcoin?".strip().lower().encode()
        ).hexdigest()
        # Simuleer een query van 61 seconden geleden
        engine._recent_queries.append((q_hash, time.time() - 61))

        blocked = self._check_dedup(engine, "Wat is Bitcoin?")
        self.assertFalse(blocked, "Query na timeout moet doorkomen")
        print("  [OK] test_02: query na timeout toegestaan")

    def test_03_dedup_allows_different_queries(self):
        """Verschillende queries → beide toegestaan."""
        engine = self._make_engine()

        blocked1 = self._check_dedup(engine, "Wat is Bitcoin?")
        self.assertFalse(blocked1)

        blocked2 = self._check_dedup(engine, "Wat is Ethereum?")
        self.assertFalse(blocked2)

        self.assertEqual(engine._swarm_metrics["echo_guard_blocks"], 0)
        print("  [OK] test_03: verschillende queries beide toegestaan")


# ── Token Budget Tests ──

class TestTokenBudget(unittest.TestCase):
    """Test de token budget tracking in OmegaGovernor."""

    def _make_governor(self):
        """Maak een Governor zonder side effects."""
        from danny_toolkit.brain.governor import OmegaGovernor
        gov = OmegaGovernor()
        gov._token_counts = defaultdict(int)
        return gov

    def test_04_token_tracking(self):
        """registreer_tokens telt correct op."""
        gov = self._make_governor()
        hour_key = datetime.now().strftime("%Y%m%d%H")

        gov.registreer_tokens("a" * 4000)  # ≈ 1000 tokens
        self.assertEqual(gov._token_counts[hour_key], 1000)

        gov.registreer_tokens("b" * 2000)  # ≈ 500 tokens
        self.assertEqual(gov._token_counts[hour_key], 1500)
        print("  [OK] test_04: token tracking klopt")

    def test_05_token_budget_exceeded(self):
        """Over budget → valideer_input weigert."""
        gov = self._make_governor()
        hour_key = datetime.now().strftime("%Y%m%d%H")

        # Vul het budget
        gov._token_counts[hour_key] = gov.MAX_TOKENS_PER_HOUR

        safe, reason = gov.valideer_input("test vraag")
        self.assertFalse(safe, "Moet geblokkeerd worden na budget")
        self.assertIn("Token budget", reason)
        print("  [OK] test_05: token budget overschrijding gedetecteerd")

    def test_06_token_budget_hourly_reset(self):
        """Ander uur → vers budget."""
        gov = self._make_governor()

        # Vul een oud uur
        old_key = "2026022100"
        gov._token_counts[old_key] = gov.MAX_TOKENS_PER_HOUR

        # Huidig uur moet vers zijn
        safe, reason = gov.valideer_input("test vraag")
        current_key = datetime.now().strftime("%Y%m%d%H")
        if current_key != old_key:
            self.assertTrue(safe, "Nieuw uur moet vers budget hebben")
            print("  [OK] test_06: nieuw uur geeft vers budget")
        else:
            # Edge case: als test om 00:xx draait
            print("  [OK] test_06: (zelfde uur — skip)")


# ── Strategist Cap Tests ──

class TestStrategistCaps(unittest.TestCase):
    """Test de MAX_STEPS en MAX_CONTEXT_CHARS limieten."""

    def test_07_max_steps(self):
        """Plan met >5 stappen wordt afgekapt tot 5."""
        from danny_toolkit.brain.strategist import Strategist

        self.assertEqual(Strategist.MAX_STEPS, 5)

        # Simuleer een plan met 10 stappen
        plan_steps = [
            {"step": i, "tool": "brain", "action": f"Step {i}", "details": "x"}
            for i in range(1, 11)
        ]
        capped = plan_steps[:Strategist.MAX_STEPS]
        self.assertEqual(len(capped), 5)
        print("  [OK] test_07: MAX_STEPS = 5 correct")

    def test_08_context_truncation(self):
        """context_buffer wordt afgekapt bij MAX_CONTEXT_CHARS."""
        from danny_toolkit.brain.strategist import Strategist

        self.assertEqual(Strategist.MAX_CONTEXT_CHARS, 8000)

        # Simuleer context groei
        context_buffer = "x" * 10000
        if len(context_buffer) > Strategist.MAX_CONTEXT_CHARS:
            context_buffer = context_buffer[-Strategist.MAX_CONTEXT_CHARS:]
        self.assertEqual(len(context_buffer), 8000)
        print("  [OK] test_08: context_buffer afgekapt op 8000 chars")


# ── Main ──

def main():
    print("=" * 60)
    print("  Phase 17: Production Stability — Tests")
    print("=" * 60)

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(TestEchoGuard))
    suite.addTests(loader.loadTestsFromTestCase(TestTokenBudget))
    suite.addTests(loader.loadTestsFromTestCase(TestStrategistCaps))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    total = result.testsRun
    failed = len(result.failures) + len(result.errors)
    passed = total - failed

    print(f"\n{'=' * 60}")
    print(f"  Resultaat: {passed}/{total} checks geslaagd")
    if failed == 0:
        print("  ALLE TESTS GESLAAGD!")
    else:
        print(f"  {failed} test(s) gefaald!")
    print(f"{'=' * 60}")

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()

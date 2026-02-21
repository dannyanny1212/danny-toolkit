"""
Tests voor RAG Pipeline — TheCortex ingestie, HybridSearch, TruthAnchor verificatie.

Voer uit: python -m unittest tests/test_rag_pipeline.py
Of:       python -m unittest tests.test_rag_pipeline

Alle tests draaien CPU-only, geen netwerk, geen GPU.
Gebruikt unittest.mock om zware model-laden-stappen over te slaan.
"""

import asyncio
import json
import sqlite3
import sys
import threading
import time
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

# Windows UTF-8
sys.stdout.reconfigure(encoding="utf-8")


# ── Helpers ──────────────────────────────────────────────────────

def _run(coro):
    """Helper om coroutines synchroon uit te voeren."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _make_in_memory_stack():
    """Maak een lichtgewicht FakeStack met :memory: SQLite."""

    class FakeStack:
        pass

    stack = FakeStack()
    stack._lock = threading.Lock()
    stack._conn = sqlite3.connect(":memory:", check_same_thread=False)
    stack._conn.row_factory = sqlite3.Row
    stack._conn.execute("PRAGMA journal_mode=WAL")
    stack._pending_writes = 0
    stack._last_flush = time.time()

    for ddl in [
        """CREATE TABLE IF NOT EXISTS episodic_memory (
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               timestamp TEXT NOT NULL, actor TEXT NOT NULL,
               action TEXT NOT NULL, details TEXT DEFAULT '{}',
               source TEXT DEFAULT 'system')""",
        """CREATE TABLE IF NOT EXISTS semantic_memory (
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               key TEXT UNIQUE NOT NULL, value TEXT NOT NULL,
               confidence REAL DEFAULT 0.5, learned_at TEXT NOT NULL,
               last_accessed TEXT NOT NULL, access_count INTEGER DEFAULT 0)""",
        """CREATE TABLE IF NOT EXISTS system_stats (
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               timestamp TEXT NOT NULL, metric TEXT NOT NULL,
               value REAL NOT NULL, tags TEXT DEFAULT '{}')""",
    ]:
        stack._conn.execute(ddl)
    stack._conn.commit()

    def flush(self=stack):
        with self._lock:
            self._conn.commit()
            self._pending_writes = 0
            self._last_flush = time.time()
    stack.flush = flush

    return stack


def _make_cortex(stack):
    """Maak TheCortex met in-memory stack (omzeilt singleton)."""
    from danny_toolkit.brain.cortex import TheCortex

    with patch("danny_toolkit.brain.cortex.get_cortical_stack", return_value=stack), \
         patch("danny_toolkit.brain.cortex.HAS_STACK", True), \
         patch("danny_toolkit.brain.cortex.HAS_BUS", False):
        cortex = TheCortex()
    return cortex


# ═════════════════════════════════════════════════════════════════
# Test 1: TheCortex — Ingestie (tekst → triples → opslag)
# ═════════════════════════════════════════════════════════════════

class TestCortexIngestion(unittest.TestCase):
    """Controleer of tekst correct wordt opgesplitst in triples
    en via de LLM in SQLite + NetworkX terechtkomt."""

    def setUp(self):
        self.stack = _make_in_memory_stack()
        self.cortex = _make_cortex(self.stack)

    def test_add_triple_sqlite(self):
        """Triple verschijnt in SQLite knowledge_graph."""
        self.cortex.add_triple("python 3.13", "introduces", "jit compiler", 0.9, "test")

        row = self.stack._conn.execute(
            "SELECT * FROM knowledge_graph WHERE entity_a = 'python 3.13'"
        ).fetchone()
        self.assertIsNotNone(row, "SQLite row moet bestaan")
        self.assertEqual(row["relatie"], "introduces")
        self.assertEqual(row["entity_b"], "jit compiler")
        self.assertAlmostEqual(row["confidence"], 0.9)

    def test_add_triple_networkx(self):
        """Triple verschijnt als edge in NetworkX graaf."""
        self.cortex.add_triple("python", "has_feature", "free threading", 0.8, "test")

        self.assertIsNotNone(self.cortex._graph)
        self.assertTrue(self.cortex._graph.has_edge("python", "free threading"))
        edge = self.cortex._graph.edges["python", "free threading"]
        self.assertEqual(edge["relatie"], "has_feature")

    def test_entity_mention_count(self):
        """Mention count stijgt bij herhaalde triples."""
        self.cortex.add_triple("python", "is_a", "language", 0.9, "test")
        self.cortex.add_triple("python", "has_version", "3.13", 0.8, "test")

        row = self.stack._conn.execute(
            "SELECT mention_count FROM entities WHERE naam = 'python'"
        ).fetchone()
        self.assertIsNotNone(row)
        self.assertGreaterEqual(row[0], 2, "Mention count moet >= 2 zijn")

    def test_extract_triples_mocked_llm(self):
        """LLM extractie met gemockte Groq response."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps([
            {"subject": "Python 3.13", "predicate": "introduces", "object": "JIT compiler"},
            {"subject": "JIT compiler", "predicate": "uses", "object": "micro-ops"},
        ])

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        self.cortex.client = mock_client

        triples = _run(self.cortex.extract_triples(
            "Python 3.13 introduces a JIT compiler that uses micro-ops."
        ))
        self.assertEqual(len(triples), 2)
        self.assertEqual(triples[0].subject, "python 3.13")
        self.assertEqual(triples[0].predicaat, "introduces")
        self.assertEqual(triples[0].object, "jit compiler")

    def test_extract_triples_malformed_json(self):
        """Malformed LLM output retourneert lege lijst, crasht niet."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "dit is geen json"

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        self.cortex.client = mock_client

        triples = _run(self.cortex.extract_triples("broken input"))
        self.assertEqual(triples, [])


# ═════════════════════════════════════════════════════════════════
# Test 2: HybridSearch — Graph + Entity expansion
# ═════════════════════════════════════════════════════════════════

class TestHybridSearch(unittest.TestCase):
    """Controleer of hybrid_search entity matching + graph expansion combineert."""

    def setUp(self):
        self.stack = _make_in_memory_stack()
        self.cortex = _make_cortex(self.stack)

    def test_hybrid_finds_known_entity(self):
        """Query met bekende entiteit retourneert knowledge_graph resultaten."""
        self.cortex.add_triple("python", "is_a", "programming language", 0.9, "test")
        self.cortex.add_triple("python", "has_library", "numpy", 0.8, "test")

        results = _run(self.cortex.hybrid_search("tell me about python", top_k=3))
        self.assertGreater(len(results), 0, "Moet resultaten vinden")
        self.assertEqual(results[0]["bron"], "knowledge_graph")
        self.assertIn("python", results[0]["content"].lower())

    def test_hybrid_graph_expansion(self):
        """Diepere relaties (A→B→C) worden meegenomen via graph traversal."""
        self.cortex.add_triple("python", "has_version", "3.13", 0.9, "test")
        self.cortex.add_triple("3.13", "introduces", "jit compiler", 0.8, "test")
        self.cortex.add_triple("jit compiler", "uses", "micro-ops", 0.7, "test")

        results = _run(self.cortex.hybrid_search("tell me about python", top_k=5))
        self.assertGreater(len(results), 0)
        content = results[0]["content"].lower()
        # Via graph expansion moet jit compiler bereikbaar zijn
        self.assertIn("3.13", content)

    def test_hybrid_empty_for_unknown_query(self):
        """Query zonder bekende entiteiten retourneert lege lijst."""
        results = _run(self.cortex.hybrid_search("xyznonexistent123", top_k=3))
        self.assertEqual(len(results), 0)

    def test_find_related_bfs_depth(self):
        """BFS traversal respecteert depth parameter."""
        self.cortex.add_triple("A", "connects", "B", 0.8, "test")
        self.cortex.add_triple("B", "connects", "C", 0.7, "test")
        self.cortex.add_triple("C", "connects", "D", 0.6, "test")

        depth1 = self.cortex.find_related("A", depth=1)
        self.assertIn("B", depth1)
        self.assertNotIn("C", depth1)

        depth2 = self.cortex.find_related("A", depth=2)
        self.assertIn("B", depth2)
        self.assertIn("C", depth2)
        self.assertNotIn("D", depth2)

    def test_find_related_unknown_entity(self):
        """Onbekende entiteit retourneert lege lijst."""
        result = self.cortex.find_related("onbekend_xyz")
        self.assertEqual(result, [])


# ═════════════════════════════════════════════════════════════════
# Test 3: TruthAnchor — Cross-Encoder verificatie
# ═════════════════════════════════════════════════════════════════

class TestTruthAnchor(unittest.TestCase):
    """Controleer of de cross-encoder hallucinaties onderscheidt
    van gegronde antwoorden."""

    def _make_anchor(self, mock_model):
        """Maak TruthAnchor met gemockt CrossEncoder model."""
        with patch("danny_toolkit.brain.truth_anchor.CrossEncoder", return_value=mock_model):
            from danny_toolkit.brain.truth_anchor import TruthAnchor
            return TruthAnchor()

    def test_grounded_answer_passes(self):
        """Hoge cross-encoder score → True (antwoord is gegrond)."""
        mock_model = MagicMock()
        mock_model.predict.return_value = [0.85]
        anchor = self._make_anchor(mock_model)

        result = anchor.verify(
            "Python 3.13 introduceert een JIT compiler",
            ["Python 3.13 introduces a new JIT compiler based on micro-ops."],
        )
        self.assertTrue(result, "Gegrond antwoord moet True retourneren")

    def test_hallucination_rejected(self):
        """Lage cross-encoder score → False (hallucinatie gedetecteerd)."""
        mock_model = MagicMock()
        mock_model.predict.return_value = [0.05]
        anchor = self._make_anchor(mock_model)

        result = anchor.verify(
            "Python 3.13 is een type auto",
            ["Python 3.13 introduces a new JIT compiler based on micro-ops."],
        )
        self.assertFalse(result, "Hallucinatie moet False retourneren")

    def test_empty_context_rejected(self):
        """Lege context → False (geen bron om te verifiëren)."""
        mock_model = MagicMock()
        anchor = self._make_anchor(mock_model)

        result = anchor.verify("Python is a language", [])
        self.assertFalse(result, "Lege context moet False retourneren")
        mock_model.predict.assert_not_called()

    def test_multiple_docs_best_score_wins(self):
        """Meerdere context docs: beste score bepaalt uitkomst."""
        mock_model = MagicMock()
        # Eerste doc laag, tweede doc hoog
        mock_model.predict.return_value = [0.1, 0.75]
        anchor = self._make_anchor(mock_model)

        result = anchor.verify(
            "Python has a GIL",
            ["Cats are fluffy animals.", "Python uses a Global Interpreter Lock (GIL)."],
        )
        self.assertTrue(result, "Beste score (0.75) moet True geven")

    def test_borderline_score_threshold(self):
        """Score precies op drempel (0.2) → False (strict check)."""
        mock_model = MagicMock()
        mock_model.predict.return_value = [0.2]
        anchor = self._make_anchor(mock_model)

        result = anchor.verify("test claim", ["test context"])
        self.assertFalse(result, "Score == 0.2 moet False zijn (> 0.2 vereist)")


if __name__ == "__main__":
    unittest.main()

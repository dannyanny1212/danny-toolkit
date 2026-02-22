"""
Tests voor RAG Pipeline — TheCortex, TruthAnchor, BlackBox, VoidWalker.

Voer uit: python test_rag_pipeline.py

Alle tests draaien CPU-only, geen netwerk, geen GPU.
Gebruikt unittest.mock om externe dependencies te mocken.
"""

import asyncio
import json
import os
import sqlite3
import sys
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# Windows UTF-8
sys.stdout.reconfigure(encoding="utf-8")

# Test-mode env
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "-1")
os.environ.setdefault("DANNY_TEST_MODE", "1")
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

# Zorg dat project root op sys.path staat
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

geslaagd = 0
mislukt = 0
checks = 0


def check(naam, conditie):
    """Verificatie helper."""
    global geslaagd, mislukt, checks
    checks += 1
    if conditie:
        geslaagd += 1
        print(f"  [OK] {naam}")
    else:
        mislukt += 1
        print(f"  [X]  {naam}")


# ── Helpers ──

def _make_in_memory_stack():
    """Maak een lichtgewicht object met :memory: SQLite als CorticalStack stand-in."""
    import threading

    class FakeStack:
        pass

    stack = FakeStack()
    stack._lock = threading.Lock()
    stack._conn = sqlite3.connect(":memory:", check_same_thread=False)
    stack._conn.row_factory = sqlite3.Row
    stack._conn.execute("PRAGMA journal_mode=WAL")
    stack._pending_writes = 0
    stack._last_flush = time.time()

    # Maak tabellen (episodic, semantic, system_stats)
    stack._conn.execute("""
        CREATE TABLE IF NOT EXISTS episodic_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            actor TEXT NOT NULL,
            action TEXT NOT NULL,
            details TEXT DEFAULT '{}',
            source TEXT DEFAULT 'system'
        )
    """)
    stack._conn.execute("""
        CREATE TABLE IF NOT EXISTS semantic_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE NOT NULL,
            value TEXT NOT NULL,
            confidence REAL DEFAULT 0.5,
            learned_at TEXT NOT NULL,
            last_accessed TEXT NOT NULL,
            access_count INTEGER DEFAULT 0
        )
    """)
    stack._conn.execute("""
        CREATE TABLE IF NOT EXISTS system_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            metric TEXT NOT NULL,
            value REAL NOT NULL,
            tags TEXT DEFAULT '{}'
        )
    """)
    stack._conn.commit()

    def flush(self=stack):
        with self._lock:
            self._conn.commit()
            self._pending_writes = 0
            self._last_flush = time.time()
    stack.flush = flush

    return stack


def _run(coro):
    """Helper om coroutines synchroon uit te voeren."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _make_cortex(stack):
    """Maak een TheCortex met in-memory stack (omzeilt singleton)."""
    from danny_toolkit.brain.cortex import TheCortex

    with patch("danny_toolkit.brain.cortex.get_cortical_stack", return_value=stack), \
         patch("danny_toolkit.brain.cortex.HAS_STACK", True), \
         patch("danny_toolkit.brain.cortex.HAS_BUS", False):
        cortex = TheCortex()
    return cortex


# ═══════════════════════════════════════════════════
# Test 1: TheCortex — add_triple
# ═══════════════════════════════════════════════════

def test_cortex_add_triple():
    """TheCortex triple storage + NetworkX sync."""
    print("\n=== Test 1: TheCortex — add_triple ===")

    stack = _make_in_memory_stack()
    cortex = _make_cortex(stack)

    cortex.add_triple("python", "is_a", "language", 0.9, "test")

    # Check SQLite row
    row = stack._conn.execute(
        "SELECT * FROM knowledge_graph WHERE entity_a = 'python'"
    ).fetchone()
    check("SQLite row exists", row is not None)
    check("Relatie correct", row["relatie"] == "is_a")
    check("Entity_b correct", row["entity_b"] == "language")
    check("Confidence correct", row["confidence"] == 0.9)

    # Check NetworkX edge
    has_graph = cortex._graph is not None
    check("NetworkX graph aanwezig", has_graph)
    if has_graph:
        check("NetworkX edge exists", cortex._graph.has_edge("python", "language"))

    # Check entity mention_count
    ent = stack._conn.execute(
        "SELECT mention_count FROM entities WHERE naam = 'python'"
    ).fetchone()
    check("Entity mention_count >= 1", ent is not None and ent[0] >= 1)


# ═══════════════════════════════════════════════════
# Test 2: TheCortex — find_related (BFS)
# ═══════════════════════════════════════════════════

def test_cortex_find_related():
    """Graph traversal via BFS."""
    print("\n=== Test 2: TheCortex — find_related ===")

    stack = _make_in_memory_stack()
    cortex = _make_cortex(stack)

    # A → B, B → C, B → D
    cortex.add_triple("A", "connects", "B", 0.8, "test")
    cortex.add_triple("B", "connects", "C", 0.7, "test")
    cortex.add_triple("B", "connects", "D", 0.6, "test")

    # depth=2 should find B, C, D
    related_2 = cortex.find_related("A", depth=2)
    check("depth=2 vindt B", "B" in related_2)
    check("depth=2 vindt C", "C" in related_2)
    check("depth=2 vindt D", "D" in related_2)

    # depth=1 should only find B
    related_1 = cortex.find_related("A", depth=1)
    check("depth=1 vindt B", "B" in related_1)
    check("depth=1 vindt NIET C", "C" not in related_1)

    # unknown entity
    related_none = cortex.find_related("unknown")
    check("unknown retourneert []", related_none == [])


# ═══════════════════════════════════════════════════
# Test 3: TheCortex — hybrid_search
# ═══════════════════════════════════════════════════

def test_cortex_hybrid_search():
    """Combined vector + graph search."""
    print("\n=== Test 3: TheCortex — hybrid_search ===")

    stack = _make_in_memory_stack()
    cortex = _make_cortex(stack)

    # Populate
    cortex.add_triple("python", "is_a", "programming language", 0.9, "test")
    cortex.add_triple("python", "has_library", "numpy", 0.8, "test")

    # Query met bekende entiteit
    results = _run(cortex.hybrid_search("tell me about python", top_k=3))
    check("Resultaten gevonden", len(results) > 0)
    if results:
        check("Bron is knowledge_graph", results[0].get("bron") == "knowledge_graph")
        check("Content bevat data", len(results[0].get("content", "")) > 0)

    # Lege query
    empty = _run(cortex.hybrid_search("xyznonexistent123", top_k=3))
    check("Onbekende query retourneert []", len(empty) == 0)


# ═══════════════════════════════════════════════════
# Test 4: TheCortex — extract_triples (mocked LLM)
# ═══════════════════════════════════════════════════

def test_cortex_extract_triples():
    """LLM extraction met mocked Groq."""
    print("\n=== Test 4: TheCortex — extract_triples ===")

    stack = _make_in_memory_stack()

    # Mock LLM response
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = json.dumps([
        {"subject": "Python", "predicate": "is_a", "object": "programming language"},
        {"subject": "NumPy", "predicate": "used_for", "object": "numerical computing"},
    ])

    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    cortex = _make_cortex(stack)
    cortex.client = mock_client

    triples = _run(cortex.extract_triples("Python is a programming language used with NumPy"))
    check("Twee triples geextraheerd", len(triples) == 2)
    if triples:
        check("Eerste subject correct", triples[0].subject == "python")
        check("Eerste predicaat correct", triples[0].predicaat == "is_a")
        check("Eerste object correct", triples[0].object == "programming language")

    # Test malformed JSON
    bad_response = MagicMock()
    bad_response.choices = [MagicMock()]
    bad_response.choices[0].message.content = "dit is geen json"
    mock_client.chat.completions.create = AsyncMock(return_value=bad_response)

    bad_triples = _run(cortex.extract_triples("broken"))
    check("Malformed JSON retourneert []", bad_triples == [])


# ═══════════════════════════════════════════════════
# Test 5: TruthAnchor — verify
# ═══════════════════════════════════════════════════

def test_truth_anchor_verify():
    """Cross-encoder verification met mocked model."""
    print("\n=== Test 5: TruthAnchor — verify ===")

    mock_model = MagicMock()

    with patch("danny_toolkit.brain.truth_anchor.CrossEncoder", return_value=mock_model):
        from danny_toolkit.brain.truth_anchor import TruthAnchor
        anchor = TruthAnchor()

        # Hoge score -> True (verify retourneert (bool, float) tuple)
        mock_model.predict.return_value = [0.8]
        grounded_good, score_good = anchor.verify("Python is a language", ["Python is a programming language"])
        check("Hoge score -> True", grounded_good is True)
        check("Hoge score waarde", score_good >= 0.45)

        # Lage score -> False
        mock_model.predict.return_value = [0.1]
        grounded_bad, score_bad = anchor.verify("Python is a language", ["Cats are fluffy animals"])
        check("Lage score -> False", grounded_bad is False)
        check("Lage score waarde", score_bad < 0.45)

        # Lege context -> False
        grounded_empty, score_empty = anchor.verify("anything", [])
        check("Lege context -> False", grounded_empty is False)
        check("Lege context score", score_empty == 0.0)


# ═══════════════════════════════════════════════════
# Test 6: BlackBox — record and retrieve
# ═══════════════════════════════════════════════════

def test_black_box_record_and_retrieve():
    """Failure memory record + retrieval."""
    print("\n=== Test 6: BlackBox — record and retrieve ===")

    mock_store = MagicMock()
    # documenten must be truthy for retrieve_warnings to proceed
    mock_store.documenten = {"doc1": {"tekst": "test"}}
    mock_store.voeg_toe = MagicMock()
    mock_store.zoek = MagicMock(return_value=[{
        "tekst": "test prompt",
        "metadata": {
            "type": "failure_lesson",
            "lesson": "hallucinated facts about quantum computing",
        },
        "score": 0.8,
    }])

    mock_embedder = MagicMock()

    with patch("danny_toolkit.brain.black_box.HAS_VECTOR", True), \
         patch("danny_toolkit.brain.black_box.get_torch_embedder", return_value=mock_embedder), \
         patch("danny_toolkit.brain.black_box.VectorStore", return_value=mock_store):
        from danny_toolkit.brain.black_box import BlackBox
        bb = BlackBox()

        # Record a crash
        bb.record_crash("test prompt", "bad answer", "hallucinated facts")
        check("voeg_toe() aangeroepen", mock_store.voeg_toe.called)

        # Controleer structuur van de aanroep
        call_args = mock_store.voeg_toe.call_args[0][0]
        check("Record heeft id", "id" in call_args[0])
        check("Record heeft tekst", call_args[0]["tekst"] == "test prompt")
        check("Record heeft metadata.lesson", call_args[0]["metadata"]["lesson"] == "hallucinated facts")

        # Retrieve warnings
        warning = bb.retrieve_warnings("similar prompt")
        check("Warning bevat PAST MISTAKE of IMMUNE", "PAST MISTAKE" in warning or "IMMUNE" in warning)
        check("Warning bevat lesson tekst", "hallucinated facts" in warning)


# ═══════════════════════════════════════════════════
# Test 7: BlackBox — empty (geen failures)
# ═══════════════════════════════════════════════════

def test_black_box_empty():
    """Geen failures recorded."""
    print("\n=== Test 7: BlackBox — empty ===")

    mock_store = MagicMock()
    mock_store.documenten = {}  # Empty = falsy, retrieve_warnings returns ""
    mock_store.zoek = MagicMock(return_value=[])

    mock_embedder = MagicMock()

    with patch("danny_toolkit.brain.black_box.HAS_VECTOR", True), \
         patch("danny_toolkit.brain.black_box.get_torch_embedder", return_value=mock_embedder), \
         patch("danny_toolkit.brain.black_box.VectorStore", return_value=mock_store):
        from danny_toolkit.brain.black_box import BlackBox
        bb = BlackBox()

        # Empty retrieve
        warning = bb.retrieve_warnings("anything")
        check("Lege warning bij geen failures", warning == "")

        # Stats
        stats = bb.get_stats()
        check("recorded_failures is 0", stats["recorded_failures"] == 0)


# ═══════════════════════════════════════════════════
# Test 8: VoidWalker — fill_knowledge_gap (fully mocked)
# ═══════════════════════════════════════════════════

def test_void_walker_fill_gap():
    """Research pipeline met gemockte dependencies."""
    print("\n=== Test 8: VoidWalker — fill_knowledge_gap ===")

    # Mock DDGS search (used as context manager: with DDGS() as ddgs)
    mock_ddgs_instance = MagicMock()
    mock_ddgs_instance.text.return_value = [
        {"title": "Test Article", "href": "https://example.com/test"},
        {"title": "Another Source", "href": "https://docs.example.com/ref"},
    ]
    mock_ddgs_class = MagicMock()
    mock_ddgs_class.return_value.__enter__ = MagicMock(return_value=mock_ddgs_instance)
    mock_ddgs_class.return_value.__exit__ = MagicMock(return_value=False)

    # Mock scraper
    mock_scrape = MagicMock(return_value=[
        {"text": "This is scraped content about the test topic with useful information."}
    ])

    # Mock Groq digest
    mock_groq_response = MagicMock()
    mock_groq_response.choices = [MagicMock()]
    mock_groq_response.choices[0].message.content = "Synthesized knowledge about test topic."

    mock_groq_client = AsyncMock()
    mock_groq_client.chat.completions.create = AsyncMock(return_value=mock_groq_response)

    # Mock VectorStore
    mock_store = MagicMock()
    mock_store.documenten = {}
    mock_store.voeg_toe = MagicMock()

    mock_embedder = MagicMock()

    with patch("danny_toolkit.brain.void_walker.HAS_DDGS", True), \
         patch("danny_toolkit.brain.void_walker.DDGS", mock_ddgs_class, create=True), \
         patch("danny_toolkit.brain.void_walker.HAS_SCRAPER", True), \
         patch("danny_toolkit.brain.void_walker.scrape_url", mock_scrape, create=True), \
         patch("danny_toolkit.brain.void_walker.HAS_VECTOR", True), \
         patch("danny_toolkit.brain.void_walker.get_torch_embedder", return_value=mock_embedder, create=True), \
         patch("danny_toolkit.brain.void_walker.VectorStore", return_value=mock_store, create=True), \
         patch("danny_toolkit.brain.void_walker.AsyncGroq", return_value=mock_groq_client, create=True):
        from danny_toolkit.brain.void_walker import VoidWalker
        walker = VoidWalker()
        walker.client = mock_groq_client

        result = _run(walker.fill_knowledge_gap("test topic"))
        check("Result is een string", isinstance(result, str))
        check("Result bevat digest", "Synthesized knowledge" in result)
        check("VectorStore.voeg_toe() aangeroepen", mock_store.voeg_toe.called)

        # Controleer zoekquery
        check("DDGS.text() aangeroepen", mock_ddgs_instance.text.called)
        check("scrape_url aangeroepen", mock_scrape.called)


# ═══════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════

def main():
    print("=" * 60)
    print("  DANNY TOOLKIT — RAG PIPELINE TESTS")
    print("=" * 60)

    tests = [
        test_cortex_add_triple,
        test_cortex_find_related,
        test_cortex_hybrid_search,
        test_cortex_extract_triples,
        test_truth_anchor_verify,
        test_black_box_record_and_retrieve,
        test_black_box_empty,
        test_void_walker_fill_gap,
    ]

    for test_fn in tests:
        try:
            test_fn()
        except Exception as e:
            global mislukt, checks
            checks += 1
            mislukt += 1
            print(f"  [X]  {test_fn.__name__} CRASHED: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n{'=' * 60}")
    print(f"  RESULTAAT: {geslaagd} geslaagd, {mislukt} mislukt, {checks} checks")
    print(f"{'=' * 60}")

    if mislukt == 0:
        print("  ALLE TESTS GESLAAGD!")
    else:
        print(f"  {mislukt} test(s) gefaald!")

    sys.exit(0 if mislukt == 0 else 1)


if __name__ == "__main__":
    main()

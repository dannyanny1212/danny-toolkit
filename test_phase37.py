"""
Phase 37 Tests — SELF PRUNING: Aggressive Vector Store Maintenance.

18 tests, ~70 checks:
  Tests 1-3:   Module imports, singletons, Config constanten
  Tests 4-6:   AccessTracker: UPSERT, stale query, actieve query, thread-safety
  Tests 7-8:   EntropieScanner: centroid berekening, cosine distance, flagging
  Tests 9-10:  RedundantieDetector: pairwise similarity, oudste vernietigen
  Tests 11-12: ColdStorageMigrator: migratie flow, metadata enrichment
  Tests 13-14: NeuralBus: 4 nieuwe events, payload correctheid
  Tests 15-16: CorticalStack audit logging, prune() resultaat
  Tests 17-18: Feature flag (PRUNING_ENABLED), versie check, module integrity
"""

import os
import sys
import tempfile
import threading
import time

sys.stdout = __import__("io").TextIOWrapper(
    sys.stdout.buffer, encoding="utf-8", errors="replace",
)

# Test-mode env
os.environ.setdefault("DANNY_TEST_MODE", "1")
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "-1")
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

passed = 0
failed = 0


def check(beschrijving: str, conditie: bool):
    global passed, failed
    if conditie:
        passed += 1
        print(f"  OK  {beschrijving}")
    else:
        failed += 1
        print(f"  FAIL  {beschrijving}")


# ═══════════════════════════════════════════════════
# Tests 1-3: Module imports, singletons, Config
# ═══════════════════════════════════════════════════

def test_1_module_import():
    """self_pruning module importeert correct."""
    print("\n[Test 1] Module import")
    import danny_toolkit.core.self_pruning as mod

    check("Module importeert", mod is not None)
    check("AccessTracker class bestaat", hasattr(mod, "AccessTracker"))
    check("EntropieScanner class bestaat", hasattr(mod, "EntropieScanner"))
    check("RedundantieDetector class bestaat", hasattr(mod, "RedundantieDetector"))
    check("ColdStorageMigrator class bestaat", hasattr(mod, "ColdStorageMigrator"))
    check("SelfPruning class bestaat", hasattr(mod, "SelfPruning"))
    check("get_self_pruning functie bestaat", hasattr(mod, "get_self_pruning"))


def test_2_singleton():
    """get_self_pruning() retourneert dezelfde instantie."""
    print("\n[Test 2] Singleton")
    from danny_toolkit.core.self_pruning import get_self_pruning, SelfPruning

    sp1 = get_self_pruning()
    sp2 = get_self_pruning()
    check("Singleton is SelfPruning", isinstance(sp1, SelfPruning))
    check("Zelfde instantie", sp1 is sp2)
    check("Heeft tracker", hasattr(sp1, "tracker"))
    check("Heeft entropie", hasattr(sp1, "entropie"))
    check("Heeft redundantie", hasattr(sp1, "redundantie"))


def test_3_config_constanten():
    """Config bevat alle pruning constanten."""
    print("\n[Test 3] Config constanten")
    from danny_toolkit.core.config import Config

    check("PRUNING_ENABLED bestaat", hasattr(Config, "PRUNING_ENABLED"))
    check("PRUNING_ENABLED is bool", isinstance(Config.PRUNING_ENABLED, bool))
    check("ENTROPY_THRESHOLD bestaat", hasattr(Config, "ENTROPY_THRESHOLD"))
    check("ENTROPY_THRESHOLD is float", isinstance(Config.ENTROPY_THRESHOLD, float))
    check("ENTROPY_THRESHOLD default 0.85", Config.ENTROPY_THRESHOLD == 0.85)
    check("REDUNDANCY_THRESHOLD bestaat", hasattr(Config, "REDUNDANCY_THRESHOLD"))
    check("REDUNDANCY_THRESHOLD default 0.90", Config.REDUNDANCY_THRESHOLD == 0.90)
    check("RECENCY_DECAY_DAYS bestaat", hasattr(Config, "RECENCY_DECAY_DAYS"))
    check("RECENCY_DECAY_DAYS default 14", Config.RECENCY_DECAY_DAYS == 14)
    check("COLD_STORAGE_COLLECTION bestaat", hasattr(Config, "COLD_STORAGE_COLLECTION"))
    check("COLD_STORAGE_COLLECTION is danny_cold",
          Config.COLD_STORAGE_COLLECTION == "danny_cold")


# ═══════════════════════════════════════════════════
# Tests 4-6: AccessTracker
# ═══════════════════════════════════════════════════

def _maak_temp_tracker():
    """Maak een AccessTracker met temp DB."""
    from danny_toolkit.core.self_pruning import AccessTracker
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    return AccessTracker(db_path=path), path


def test_4_tracker_upsert():
    """AccessTracker UPSERT patroon werkt correct."""
    print("\n[Test 4] AccessTracker UPSERT")
    tracker, path = _maak_temp_tracker()

    # Eerste registratie
    tracker.registreer_toegang(["frag_1", "frag_2"], "danny_docs")
    check("Totaal na eerste registratie = 2", tracker.totaal_gevolgd() == 2)

    # Tweede registratie (UPSERT — access_count+1)
    tracker.registreer_toegang(["frag_1"], "danny_docs")
    check("Totaal na UPSERT nog steeds 2", tracker.totaal_gevolgd() == 2)

    # Controleer access_count via directe DB query
    import sqlite3
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT access_count FROM fragment_access WHERE fragment_id=?",
        ("frag_1",),
    ).fetchone()
    conn.close()
    check("access_count frag_1 = 2", row and row["access_count"] == 2)

    os.unlink(path)


def test_5_tracker_stale_actief():
    """AccessTracker haal_stale_fragmenten en haal_actieve_fragmenten."""
    print("\n[Test 5] AccessTracker stale/actief queries")
    tracker, path = _maak_temp_tracker()

    # Maak fragmenten aan
    tracker.registreer_creatie(["recent_1"], "danny_code")
    tracker.registreer_creatie(["old_1"], "danny_code")

    # Manipuleer last_accessed voor old_1 naar 30 dagen geleden
    import sqlite3
    from datetime import datetime, timedelta
    oud = (datetime.now() - timedelta(days=30)).isoformat()
    conn = sqlite3.connect(path)
    conn.execute(
        "UPDATE fragment_access SET last_accessed=?, created_at=? WHERE fragment_id=?",
        (oud, oud, "old_1"),
    )
    conn.commit()
    conn.close()

    stale = tracker.haal_stale_fragmenten(dagen=14)
    stale_ids = [s["fragment_id"] for s in stale]
    check("old_1 is stale", "old_1" in stale_ids)
    check("recent_1 is NIET stale", "recent_1" not in stale_ids)

    actieve = tracker.haal_actieve_fragmenten(dagen=14)
    check("recent_1 is actief", "recent_1" in actieve)
    check("old_1 is NIET actief", "old_1" not in actieve)

    os.unlink(path)


def test_6_tracker_thread_safety():
    """AccessTracker is thread-safe."""
    print("\n[Test 6] AccessTracker thread-safety")
    tracker, path = _maak_temp_tracker()

    fouten = []

    def schrijf(prefix, n):
        try:
            for i in range(n):
                tracker.registreer_toegang([f"{prefix}_{i}"], "danny_docs")
        except Exception as e:
            fouten.append(e)

    threads = [
        threading.Thread(target=schrijf, args=("a", 50)),
        threading.Thread(target=schrijf, args=("b", 50)),
        threading.Thread(target=schrijf, args=("c", 50)),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    check("Geen fouten bij concurrent schrijven", len(fouten) == 0)
    totaal = tracker.totaal_gevolgd()
    check(f"Totaal = 150 (was {totaal})", totaal == 150)

    # Verwijder test
    tracker.verwijder(["a_0", "a_1"], "danny_docs")
    check("Verwijder verlaagt totaal", tracker.totaal_gevolgd() == 148)

    os.unlink(path)


# ═══════════════════════════════════════════════════
# Tests 7-8: EntropieScanner
# ═══════════════════════════════════════════════════

def test_7_cosine_distance_centroid():
    """EntropieScanner cosine distance en centroid berekening."""
    print("\n[Test 7] Cosine distance en centroid")
    from danny_toolkit.core.self_pruning import EntropieScanner

    scanner = EntropieScanner(drempel=0.85)

    # Identieke vectoren → distance 0
    a = [1.0, 0.0, 0.0]
    dist_same = scanner._cosine_distance(a, a)
    check(f"Identieke vectoren: distance ~0 (was {dist_same:.4f})",
          abs(dist_same) < 0.001)

    # Orthogonale vectoren → distance 1
    b = [0.0, 1.0, 0.0]
    dist_orth = scanner._cosine_distance(a, b)
    check(f"Orthogonale vectoren: distance ~1 (was {dist_orth:.4f})",
          abs(dist_orth - 1.0) < 0.001)

    # Tegengestelde vectoren → distance 2
    c = [-1.0, 0.0, 0.0]
    dist_opp = scanner._cosine_distance(a, c)
    check(f"Tegengestelde vectoren: distance ~2 (was {dist_opp:.4f})",
          abs(dist_opp - 2.0) < 0.001)

    # Centroid berekening
    embeddings = [[1.0, 0.0], [0.0, 1.0]]
    centroid = scanner._bereken_centroid(embeddings)
    check("Centroid heeft 2 dimensies", len(centroid) == 2)
    # Gemiddelde = [0.5, 0.5], genormaliseerd = [0.707, 0.707]
    import math
    expected = 1.0 / math.sqrt(2.0)
    check(f"Centroid[0] ~0.707 (was {centroid[0]:.4f})",
          abs(centroid[0] - expected) < 0.01)
    check(f"Centroid[1] ~0.707 (was {centroid[1]:.4f})",
          abs(centroid[1] - expected) < 0.01)


def test_8_entropie_flagging():
    """EntropieScanner flagged fragmenten ver van centroid."""
    print("\n[Test 8] Entropie flagging")
    from danny_toolkit.core.self_pruning import EntropieScanner

    scanner = EntropieScanner(drempel=0.5)  # Lage drempel voor test

    # Mock collection — 12 fragmenten (>10 minimum voor scan)
    class MockCollection:
        def __init__(self):
            self._data = {
                "active_1": [1.0, 0.0, 0.0],
                "active_2": [0.9, 0.1, 0.0],
                "active_3": [0.95, 0.05, 0.0],
                "active_4": [0.85, 0.15, 0.0],
                "active_5": [0.92, 0.08, 0.0],
                "active_6": [0.88, 0.12, 0.0],
                "active_7": [0.91, 0.09, 0.0],
                "active_8": [0.87, 0.13, 0.0],
                "outlier_1": [0.0, 0.0, 1.0],  # Ver van cluster
                "normal_1": [0.8, 0.2, 0.0],   # Dicht bij cluster
                "normal_2": [0.82, 0.18, 0.0],
                "normal_3": [0.78, 0.22, 0.0],
            }

        def get(self, ids=None, include=None):
            if ids:
                return {
                    "ids": [i for i in ids if i in self._data],
                    "embeddings": [self._data[i] for i in ids if i in self._data],
                }
            return {"ids": list(self._data.keys()), "embeddings": list(self._data.values())}

    coll = MockCollection()
    alle_ids = list(coll._data.keys())
    actieve_ids = [k for k in alle_ids if k.startswith("active_")]

    geflagd = scanner.scan("danny_test", actieve_ids, alle_ids, coll)
    check("outlier_1 is geflagd", "outlier_1" in geflagd)
    check("normal_1 is NIET geflagd", "normal_1" not in geflagd)
    check("Actieve IDs zijn nooit geflagd", "active_1" not in geflagd)


# ═══════════════════════════════════════════════════
# Tests 9-10: RedundantieDetector
# ═══════════════════════════════════════════════════

def test_9_pairwise_similarity():
    """RedundantieDetector vindt duplicaat-paren."""
    print("\n[Test 9] Pairwise similarity detectie")
    from danny_toolkit.core.self_pruning import RedundantieDetector

    detector = RedundantieDetector(drempel=0.95)

    # Bijna identieke vectoren
    import math
    ids = ["chunk_1", "chunk_2", "chunk_3"]
    embeddings = [
        [1.0, 0.0, 0.0],        # chunk_1
        [0.999, 0.01, 0.0],     # chunk_2 — bijna identiek aan chunk_1
        [0.0, 1.0, 0.0],        # chunk_3 — totaal anders
    ]

    paren = detector._vind_duplicaten(ids, embeddings)
    check("Minstens 1 paar gevonden", len(paren) >= 1)
    if paren:
        ids_in_paren = {paren[0][0], paren[0][1]}
        check("chunk_1 in duplicaat paar", "chunk_1" in ids_in_paren)
        check("chunk_2 in duplicaat paar", "chunk_2" in ids_in_paren)
        check("Similarity > 0.95", paren[0][2] > 0.95)


def test_10_oudste_vernietigen():
    """RedundantieDetector vernietigt het oudste fragment."""
    print("\n[Test 10] Oudste fragment detectie")
    from danny_toolkit.core.self_pruning import RedundantieDetector

    detector = RedundantieDetector(drempel=0.90)
    tracker, path = _maak_temp_tracker()

    # Registreer fragmenten met verschillende created_at
    tracker.registreer_creatie(["oud_chunk"], "danny_code")

    # Manipuleer created_at
    import sqlite3
    from datetime import datetime, timedelta
    oud = (datetime.now() - timedelta(days=60)).isoformat()
    conn = sqlite3.connect(path)
    conn.execute(
        "UPDATE fragment_access SET created_at=? WHERE fragment_id=?",
        (oud, "oud_chunk"),
    )
    conn.commit()
    conn.close()

    tracker.registreer_creatie(["nieuw_chunk"], "danny_code")

    oudste = detector._bepaal_oudste("oud_chunk", "nieuw_chunk", tracker, "danny_code")
    check("Oudste is oud_chunk", oudste == "oud_chunk")

    os.unlink(path)


# ═══════════════════════════════════════════════════
# Tests 11-12: ColdStorageMigrator
# ═══════════════════════════════════════════════════

def test_11_migratie_flow():
    """ColdStorageMigrator migreert fragmenten correct."""
    print("\n[Test 11] Cold storage migratie flow")
    from danny_toolkit.core.self_pruning import ColdStorageMigrator

    # Mock collections
    class MockBronCollection:
        def __init__(self):
            self.data = {
                "stale_1": {"doc": "tekst 1", "meta": {"extensie": ".py"}, "emb": [0.1, 0.2]},
                "stale_2": {"doc": "tekst 2", "meta": {"extensie": ".md"}, "emb": [0.3, 0.4]},
            }
            self.deleted_ids = []

        def get(self, ids=None, include=None):
            filtered = {k: v for k, v in self.data.items() if k in (ids or [])}
            return {
                "ids": list(filtered.keys()),
                "documents": [v["doc"] for v in filtered.values()],
                "metadatas": [v["meta"] for v in filtered.values()],
                "embeddings": [v["emb"] for v in filtered.values()],
            }

        def delete(self, ids=None):
            self.deleted_ids.extend(ids or [])
            for i in ids or []:
                self.data.pop(i, None)

    class MockColdCollection:
        def __init__(self):
            self.upserted = []

        def upsert(self, **kwargs):
            self.upserted.append(kwargs)

    bron = MockBronCollection()
    cold = MockColdCollection()

    migrator = ColdStorageMigrator(verval_dagen=14)
    migrator._cold_collection = cold  # Inject mock

    tracker, path = _maak_temp_tracker()
    tracker.registreer_creatie(["stale_1", "stale_2"], "danny_code")

    gemigreerd = migrator.migreer(
        ["stale_1", "stale_2"], bron, "danny_code", tracker,
    )

    check(f"2 fragmenten gemigreerd (was {gemigreerd})", gemigreerd == 2)
    check("Bron IDs verwijderd", len(bron.deleted_ids) == 2)
    check("Cold collection heeft upsert", len(cold.upserted) == 1)

    os.unlink(path)


def test_12_metadata_enrichment():
    """ColdStorageMigrator voegt cold_archived_at en original_shard toe."""
    print("\n[Test 12] Metadata enrichment")
    from danny_toolkit.core.self_pruning import ColdStorageMigrator

    class MockBron:
        def get(self, ids=None, include=None):
            return {
                "ids": ["frag_x"],
                "documents": ["test doc"],
                "metadatas": [{"extensie": ".py", "bron": "test.py"}],
                "embeddings": [[0.1, 0.2]],
            }
        def delete(self, ids=None):
            pass

    class MockCold:
        def __init__(self):
            self.last_upsert = None
        def upsert(self, **kwargs):
            self.last_upsert = kwargs

    cold = MockCold()
    migrator = ColdStorageMigrator(verval_dagen=14)
    migrator._cold_collection = cold

    migrator.migreer(["frag_x"], MockBron(), "danny_docs")

    check("Cold upsert uitgevoerd", cold.last_upsert is not None)
    if cold.last_upsert:
        meta = cold.last_upsert["metadatas"][0]
        check("cold_archived_at in metadata", "cold_archived_at" in meta)
        check("original_shard = danny_docs", meta.get("original_shard") == "danny_docs")
        check("Originele metadata behouden", meta.get("extensie") == ".py")
        check("Embeddings meegestuurd", "embeddings" in cold.last_upsert)


# ═══════════════════════════════════════════════════
# Tests 13-14: NeuralBus events
# ═══════════════════════════════════════════════════

def test_13_neuralbus_events():
    """NeuralBus heeft alle 4 Phase 37 event types."""
    print("\n[Test 13] NeuralBus event types")
    from danny_toolkit.core.neural_bus import EventTypes

    check("PRUNING_STARTED bestaat", hasattr(EventTypes, "PRUNING_STARTED"))
    check("FRAGMENT_ARCHIVED bestaat", hasattr(EventTypes, "FRAGMENT_ARCHIVED"))
    check("FRAGMENT_DESTROYED bestaat", hasattr(EventTypes, "FRAGMENT_DESTROYED"))
    check("PRUNING_COMPLETE bestaat", hasattr(EventTypes, "PRUNING_COMPLETE"))

    # Waarden zijn strings
    check("PRUNING_STARTED is string",
          isinstance(EventTypes.PRUNING_STARTED, str))
    check("PRUNING_COMPLETE is string",
          isinstance(EventTypes.PRUNING_COMPLETE, str))


def test_14_neuralbus_payload():
    """NeuralBus events worden correct gepubliceerd."""
    print("\n[Test 14] NeuralBus payload correctheid")
    from danny_toolkit.core.neural_bus import get_bus, EventTypes

    bus = get_bus()
    ontvangen = []

    def handler(event):
        ontvangen.append(event)

    bus.subscribe(EventTypes.PRUNING_COMPLETE, handler)

    payload = {
        "gearchiveerd": 5,
        "vernietigd": 2,
        "entropie_geflagd": 3,
        "duur_ms": 1234,
    }
    bus.publish(EventTypes.PRUNING_COMPLETE, payload, bron="SelfPruning")

    check("Event ontvangen", len(ontvangen) == 1)
    if ontvangen:
        check("Bron is SelfPruning", ontvangen[0].bron == "SelfPruning")
        check("gearchiveerd=5", ontvangen[0].data.get("gearchiveerd") == 5)
        check("vernietigd=2", ontvangen[0].data.get("vernietigd") == 2)

    bus.unsubscribe(EventTypes.PRUNING_COMPLETE, handler)


# ═══════════════════════════════════════════════════
# Tests 15-16: CorticalStack logging, prune()
# ═══════════════════════════════════════════════════

def test_15_cortical_logging():
    """SelfPruning logt naar CorticalStack."""
    print("\n[Test 15] CorticalStack audit logging")
    from danny_toolkit.core.self_pruning import SelfPruning
    import inspect

    source = inspect.getsource(SelfPruning._log_cortical)
    check("log_event aanroep aanwezig", "log_event" in source)
    check("actor=self_pruning", "self_pruning" in source)
    check("prune_complete event", "prune_complete" in source)
    check("gearchiveerd in detail", "gearchiveerd" in source)


def test_16_prune_disabled():
    """prune() retourneert early als PRUNING_ENABLED=False."""
    print("\n[Test 16] prune() met PRUNING_ENABLED=False")
    from danny_toolkit.core.self_pruning import SelfPruning
    from danny_toolkit.core.config import Config

    # Bewaar origineel
    orig = Config.PRUNING_ENABLED

    try:
        Config.PRUNING_ENABLED = False
        sp = SelfPruning()
        result = sp.prune()
        check("overgeslagen=True", result.get("overgeslagen") is True)
        check("gearchiveerd=0", result.get("gearchiveerd") == 0)
        check("vernietigd=0", result.get("vernietigd") == 0)
        check("entropie_geflagd=0", result.get("entropie_geflagd") == 0)
        check("duur_ms=0", result.get("duur_ms") == 0)
    finally:
        Config.PRUNING_ENABLED = orig


# ═══════════════════════════════════════════════════
# Tests 17-18: Feature flag, versie, integrity
# ═══════════════════════════════════════════════════

def test_17_feature_flag():
    """PRUNING_ENABLED feature flag wordt gelezen uit env."""
    print("\n[Test 17] Feature flag")
    from danny_toolkit.core.config import Config

    # Default (test mode) = False
    check("PRUNING_ENABLED default=False in test", Config.PRUNING_ENABLED is False)

    # Statistieken API
    from danny_toolkit.core.self_pruning import SelfPruning
    sp = SelfPruning()
    stats = sp.statistieken()
    check("statistieken retourneert dict", isinstance(stats, dict))
    check("totaal_gevolgd in stats", "totaal_gevolgd" in stats)
    check("entropy_drempel in stats", "entropy_drempel" in stats)
    check("pruning_enabled in stats", "pruning_enabled" in stats)


def test_18_module_integrity():
    """Alle gewijzigde modules importeren zonder fouten."""
    print("\n[Test 18] Module integrity & versie check")
    modules = [
        "danny_toolkit.core.self_pruning",
        "danny_toolkit.core.neural_bus",
        "danny_toolkit.core.config",
        "danny_toolkit.core.shard_router",
    ]
    for mod in modules:
        try:
            __import__(mod)
            check(f"{mod} importeert OK", True)
        except Exception as e:
            check(f"{mod} importeert OK ({e})", False)

    # Versie check
    from danny_toolkit.brain import __version__
    check(f"brain versie = 6.4.0 (was {__version__})", __version__ == "6.4.0")

    # Integratie check: swarm_engine referentie
    import inspect
    from swarm_engine import MemexAgent
    source = inspect.getsource(MemexAgent._search_chromadb)
    check("self_pruning in _search_chromadb", "self_pruning" in source)

    # Integratie check: shard_router referentie
    from danny_toolkit.core.shard_router import ShardRouter
    zoek_src = inspect.getsource(ShardRouter.zoek)
    check("self_pruning in ShardRouter.zoek", "self_pruning" in zoek_src)

    # Integratie check: dreamer referentie
    from danny_toolkit.brain.dreamer import Dreamer
    rem_src = inspect.getsource(Dreamer.rem_cycle)
    check("self_pruning in rem_cycle", "self_pruning" in rem_src)
    check("5.12 stap in rem_cycle", "5.12" in rem_src)


# ═══════════════════════════════════════════════════
# RUNNER
# ═══════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("Phase 37 — SELF PRUNING: Aggressive Vector Store Maintenance")
    print("=" * 60)

    tests = [
        test_1_module_import,
        test_2_singleton,
        test_3_config_constanten,
        test_4_tracker_upsert,
        test_5_tracker_stale_actief,
        test_6_tracker_thread_safety,
        test_7_cosine_distance_centroid,
        test_8_entropie_flagging,
        test_9_pairwise_similarity,
        test_10_oudste_vernietigen,
        test_11_migratie_flow,
        test_12_metadata_enrichment,
        test_13_neuralbus_events,
        test_14_neuralbus_payload,
        test_15_cortical_logging,
        test_16_prune_disabled,
        test_17_feature_flag,
        test_18_module_integrity,
    ]

    for t in tests:
        try:
            t()
        except Exception as e:
            failed += 1
            print(f"  FAIL  {t.__name__}: {e}")

    print("\n" + "=" * 60)
    total = passed + failed
    print(f"Resultaat: {passed}/{total} checks geslaagd")
    if failed:
        print(f"  {failed} GEFAALD")
        sys.exit(1)
    else:
        print("  ALLE CHECKS GESLAAGD")
        sys.exit(0)

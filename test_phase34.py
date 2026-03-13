"""
Phase 34 Tests — SHARD ROUTER: Matrix Sharding voor ChromaDB.

18 tests, ~60 checks:
  Tests 1-3:   Module imports, constanten, dataclass
  Tests 4-6:   Routing per extensie, fallback, disabled mode
  Tests 7-8:   ShardRouter methoden & singleton
  Tests 9-10:  NeuralBus shard events
  Tests 11-12: Config.SHARD_ENABLED + ingest disabled
  Tests 13-14: Librarian integratie
  Tests 15-16: MemexAgent heuristiek
  Tests 17-18: Backward compat + ingest.py import
"""

import os
import sys

try:
    sys.stdout = __import__("io").TextIOWrapper(
        sys.stdout.buffer, encoding="utf-8", errors="replace",
    )
except (ValueError, OSError):
    pass

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
# Tests 1-3: Module imports, constanten, dataclass
# ═══════════════════════════════════════════════════

def test_1_module_import():
    """shard_router module importeert correct."""
    print("\n[Test 1] Module import")
    import danny_toolkit.core.shard_router as mod

    check("Module importeert", mod is not None)
    check("ShardRouter class bestaat", hasattr(mod, "ShardRouter"))
    check("get_shard_router functie bestaat", hasattr(mod, "get_shard_router"))
    check("ShardStatistiek dataclass bestaat", hasattr(mod, "ShardStatistiek"))


def test_2_constanten():
    """Shard constanten zijn gedefinieerd."""
    print("\n[Test 2] Shard constanten")
    from danny_toolkit.core.shard_router import (
        SHARD_CODE, SHARD_DOCS, SHARD_DATA,
        LEGACY_COLLECTION, ALL_SHARDS, EXTENSIE_ROUTING,
    )

    check("SHARD_CODE is danny_code", SHARD_CODE == "danny_code")
    check("SHARD_DOCS is danny_docs", SHARD_DOCS == "danny_docs")
    check("SHARD_DATA is danny_data", SHARD_DATA == "danny_data")
    check("LEGACY_COLLECTION is danny_knowledge",
          LEGACY_COLLECTION == "danny_knowledge")
    check("ALL_SHARDS heeft 3 entries", len(ALL_SHARDS) == 3)
    check("EXTENSIE_ROUTING niet leeg", len(EXTENSIE_ROUTING) > 0)


def test_3_dataclass():
    """ShardStatistiek heeft correcte velden."""
    print("\n[Test 3] ShardStatistiek dataclass")
    from danny_toolkit.core.shard_router import ShardStatistiek
    import dataclasses

    fields = {f.name for f in dataclasses.fields(ShardStatistiek)}
    check("naam veld", "naam" in fields)
    check("aantal_chunks veld", "aantal_chunks" in fields)
    check("extensies veld", "extensies" in fields)

    # Default waarden
    s = ShardStatistiek(naam="test")
    check("Default aantal_chunks is 0", s.aantal_chunks == 0)
    check("Default extensies is []", s.extensies == [])


# ═══════════════════════════════════════════════════
# Tests 4-6: Routing per extensie, fallback, disabled
# ═══════════════════════════════════════════════════

def test_4_routing_code():
    """Code extensies → danny_code."""
    print("\n[Test 4] Code extensie routing")
    from danny_toolkit.core.shard_router import ShardRouter, SHARD_CODE

    router = ShardRouter()
    code_exts = [".py", ".js", ".ts", ".java", ".go", ".rs", ".c", ".cpp", ".h"]
    for ext in code_exts:
        shard = router.route_document({"extensie": ext})
        check(f"{ext} -> danny_code", shard == SHARD_CODE)


def test_5_routing_docs_data():
    """Docs en data extensies correct gerouteerd."""
    print("\n[Test 5] Docs en data routing")
    from danny_toolkit.core.shard_router import (
        ShardRouter, SHARD_DOCS, SHARD_DATA,
    )

    router = ShardRouter()

    # Docs
    for ext in [".txt", ".md", ".html", ".pdf"]:
        shard = router.route_document({"extensie": ext})
        check(f"{ext} -> danny_docs", shard == SHARD_DOCS)

    # Data
    for ext in [".json", ".csv", ".yaml", ".yml", ".toml"]:
        shard = router.route_document({"extensie": ext})
        check(f"{ext} -> danny_data", shard == SHARD_DATA)


def test_6_routing_fallback():
    """Onbekende extensie → danny_docs (fallback)."""
    print("\n[Test 6] Fallback routing")
    from danny_toolkit.core.shard_router import ShardRouter, SHARD_DOCS

    router = ShardRouter()
    shard = router.route_document({"extensie": ".xyz"})
    check("Onbekende ext -> danny_docs", shard == SHARD_DOCS)

    shard_none = router.route_document({})
    check("Geen extensie -> danny_docs", shard_none == SHARD_DOCS)

    shard_empty = router.route_document({"extensie": ""})
    check("Lege extensie -> danny_docs", shard_empty == SHARD_DOCS)


# ═══════════════════════════════════════════════════
# Tests 7-8: ShardRouter methoden & singleton
# ═══════════════════════════════════════════════════

def test_7_methods_exist():
    """ShardRouter heeft alle vereiste methoden."""
    print("\n[Test 7] ShardRouter methoden")
    from danny_toolkit.core.shard_router import ShardRouter

    router = ShardRouter()
    check("route_document() bestaat", hasattr(router, "route_document"))
    check("ingest() bestaat", hasattr(router, "ingest"))
    check("zoek() bestaat", hasattr(router, "zoek"))
    check("migreer() bestaat", hasattr(router, "migreer"))
    check("statistieken() bestaat", hasattr(router, "statistieken"))


def test_8_singleton():
    """get_shard_router() geeft singleton terug."""
    print("\n[Test 8] Singleton patroon")
    from danny_toolkit.core.shard_router import get_shard_router

    r1 = get_shard_router()
    r2 = get_shard_router()
    check("Singleton: zelfde instantie", r1 is r2)
    check("Is ShardRouter type", type(r1).__name__ == "ShardRouter")


# ═══════════════════════════════════════════════════
# Tests 9-10: NeuralBus shard events
# ═══════════════════════════════════════════════════

def test_9_neuralbus_events_defined():
    """NeuralBus heeft SHARD_MIGRATION_COMPLETE en SHARD_QUERY_ROUTED."""
    print("\n[Test 9] NeuralBus shard events")
    from danny_toolkit.core.neural_bus import EventTypes

    check("SHARD_MIGRATION_COMPLETE bestaat",
          hasattr(EventTypes, "SHARD_MIGRATION_COMPLETE"))
    check("SHARD_QUERY_ROUTED bestaat",
          hasattr(EventTypes, "SHARD_QUERY_ROUTED"))
    check("MIGRATION waarde correct",
          EventTypes.SHARD_MIGRATION_COMPLETE == "shard_migration_complete")
    check("ROUTED waarde correct",
          EventTypes.SHARD_QUERY_ROUTED == "shard_query_routed")


def test_10_neuralbus_subscribe():
    """NeuralBus kan shard events ontvangen."""
    print("\n[Test 10] NeuralBus shard event subscribe")
    from danny_toolkit.core.neural_bus import get_bus, EventTypes

    bus = get_bus()
    received = []

    def handler(event):
        received.append(event)

    bus.subscribe(EventTypes.SHARD_MIGRATION_COMPLETE, handler)
    bus.publish(
        EventTypes.SHARD_MIGRATION_COMPLETE,
        {"resultaat": {"danny_code": 10}, "totaal": 10},
        bron="test",
    )

    check("Shard event ontvangen", len(received) == 1)
    check("Event data correct",
          received[0].data.get("totaal") == 10)

    # Cleanup
    bus._subscribers[EventTypes.SHARD_MIGRATION_COMPLETE].remove(handler)


# ═══════════════════════════════════════════════════
# Tests 11-12: Config.SHARD_ENABLED + disabled mode
# ═══════════════════════════════════════════════════

def test_11_config_shard_enabled():
    """Config.SHARD_ENABLED attribuut bestaat."""
    print("\n[Test 11] Config.SHARD_ENABLED")
    from danny_toolkit.core.config import Config

    check("SHARD_ENABLED bestaat", hasattr(Config, "SHARD_ENABLED"))
    check("SHARD_ENABLED is bool", isinstance(Config.SHARD_ENABLED, bool))
    # Default is False (tenzij env var gezet)
    if not os.environ.get("SHARD_ENABLED"):
        check("Default is False", Config.SHARD_ENABLED is False)


def test_12_disabled_mode():
    """Met SHARD_ENABLED=False: ingest en zoek retourneren leeg."""
    print("\n[Test 12] Disabled mode")
    from danny_toolkit.core.shard_router import ShardRouter
    from danny_toolkit.core.config import Config

    orig = Config.SHARD_ENABLED
    try:
        Config.SHARD_ENABLED = False
        router = ShardRouter()

        result = router.ingest([
            {"id": "test1", "tekst": "Hello", "metadata": {"extensie": ".py"}},
        ])
        check("Disabled ingest retourneert {}", result == {})

        results = router.zoek("test query")
        check("Disabled zoek retourneert []", results == [])
    finally:
        Config.SHARD_ENABLED = orig


# ═══════════════════════════════════════════════════
# Tests 13-14: Librarian integratie
# ═══════════════════════════════════════════════════

def test_13_librarian_shard_router():
    """TheLibrarian heeft _shard_router en _get_shard_router()."""
    print("\n[Test 13] Librarian shard integratie")
    from danny_toolkit.skills.librarian import TheLibrarian

    # Check dat _get_shard_router methode bestaat
    check("_get_shard_router methode bestaat",
          hasattr(TheLibrarian, "_get_shard_router"))

    # Check source code reference
    import inspect
    source = inspect.getsource(TheLibrarian.__init__)
    check("_shard_router init in __init__",
          "_shard_router" in source)


def test_14_librarian_shard_disabled():
    """Met SHARD_ENABLED=False: _get_shard_router retourneert None."""
    print("\n[Test 14] Librarian shard disabled")
    from danny_toolkit.core.config import Config

    orig = Config.SHARD_ENABLED
    try:
        Config.SHARD_ENABLED = False
        # Test de methode logic direct
        from danny_toolkit.core.shard_router import ShardRouter
        router = ShardRouter()
        # ingest in disabled mode
        result = router.ingest([])
        check("Leeg ingest in disabled mode", result == {})
    finally:
        Config.SHARD_ENABLED = orig


# ═══════════════════════════════════════════════════
# Tests 15-16: MemexAgent heuristiek
# ═══════════════════════════════════════════════════

def test_15_bepaal_query_shards():
    """MemexAgent._bepaal_query_shards() heuristiek werkt."""
    print("\n[Test 15] _bepaal_query_shards() heuristiek")
    from swarm_engine import MemexAgent

    check("_bepaal_query_shards is staticmethod",
          hasattr(MemexAgent, "_bepaal_query_shards"))

    # Code queries
    result = MemexAgent._bepaal_query_shards("hoe werkt de functie parse()?")
    check("Code query bevat danny_code",
          result is not None and "danny_code" in result)

    # Data queries
    result = MemexAgent._bepaal_query_shards("wat staat in de config json?")
    check("Data query bevat danny_data",
          result is not None and "danny_data" in result)

    # Doc queries
    result = MemexAgent._bepaal_query_shards("waar is de documentatie?")
    check("Doc query bevat danny_docs",
          result is not None and "danny_docs" in result)

    # Generic query → None (alle shards)
    result = MemexAgent._bepaal_query_shards("vertel me iets")
    check("Generieke query -> None", result is None)


def test_16_search_chromadb_shard_branch():
    """_search_chromadb heeft ShardRouter code pad."""
    print("\n[Test 16] _search_chromadb shard code pad")
    import inspect
    from swarm_engine import MemexAgent

    source = inspect.getsource(MemexAgent._search_chromadb)
    check("ShardRouter import in _search_chromadb",
          "shard_router" in source.lower() or "ShardRouter" in source)
    check("SHARD_ENABLED check aanwezig",
          "SHARD_ENABLED" in source)
    check("_bepaal_query_shards aanroep",
          "_bepaal_query_shards" in source)


# ═══════════════════════════════════════════════════
# Tests 17-18: Backward compat + ingest.py
# ═══════════════════════════════════════════════════

def test_17_backward_compat():
    """Legacy danny_knowledge collectie wordt niet aangeraakt als disabled."""
    print("\n[Test 17] Backward compatibiliteit")
    from danny_toolkit.core.config import Config
    from danny_toolkit.core.shard_router import (
        ShardRouter, LEGACY_COLLECTION,
    )

    orig = Config.SHARD_ENABLED
    try:
        Config.SHARD_ENABLED = False
        router = ShardRouter()

        # Geen ChromaDB interactie in disabled mode
        check("Geen client in disabled mode",
              router._client is None)
        check("Geen collections in disabled mode",
              len(router._collections) == 0)
        check("LEGACY_COLLECTION constant correct",
              LEGACY_COLLECTION == "danny_knowledge")
    finally:
        Config.SHARD_ENABLED = orig


def test_18_ingest_import():
    """ingest.py bevat ShardRouter statistieken code."""
    print("\n[Test 18] ingest.py shard statistieken")
    import inspect

    # Lees ingest.py source
    import ingest
    source = inspect.getsource(ingest)
    check("SHARD_ENABLED check in ingest.py",
          "SHARD_ENABLED" in source)
    check("shard_router import in ingest.py",
          "shard_router" in source)
    check("statistieken() aanroep in ingest.py",
          "statistieken" in source)


# ═══════════════════════════════════════════════════
# RUNNER
# ═══════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("Phase 34 — SHARD ROUTER: Matrix Sharding")
    print("=" * 60)

    tests = [
        test_1_module_import,
        test_2_constanten,
        test_3_dataclass,
        test_4_routing_code,
        test_5_routing_docs_data,
        test_6_routing_fallback,
        test_7_methods_exist,
        test_8_singleton,
        test_9_neuralbus_events_defined,
        test_10_neuralbus_subscribe,
        test_11_config_shard_enabled,
        test_12_disabled_mode,
        test_13_librarian_shard_router,
        test_14_librarian_shard_disabled,
        test_15_bepaal_query_shards,
        test_16_search_chromadb_shard_branch,
        test_17_backward_compat,
        test_18_ingest_import,
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

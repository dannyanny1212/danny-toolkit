"""
Phase 38 — FULL-SPECTRUM ACTIVATION
====================================
Test suite: 20 tests, ~90 checks

Pillars:
  1. Omega Observatory (FastAPI endpoints + CLI commands)
  2. ErrorTaxonomy Actuator (retry logic + error ring buffer)
  3. GhostWriter Write-Back (CorticalStack dedup, dry_run)
  4. Cortex Activator (hybrid_search in MEMEX + REM maintenance)
"""

import ast
import os
import sys
import tempfile
import threading
import time

os.environ.setdefault("DANNY_TEST_MODE", "1")
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "-1")
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

passed = 0
failed = 0


def check(label, condition):
    global passed, failed
    if condition:
        print(f"  OK  {label}")
        passed += 1
    else:
        print(f"  FAIL  {label}")
        failed += 1


# ═══════════════════════════════════════════════════
# TEST 1-3: CONFIG CONSTANTS
# ═══════════════════════════════════════════════════

def test_1_config_cortex():
    """Config: CORTEX_ENRICHMENT_ENABLED."""
    print("\n[Test 1] Config: CORTEX_ENRICHMENT_ENABLED")
    from danny_toolkit.core.config import Config
    check("CORTEX_ENRICHMENT_ENABLED bestaat", hasattr(Config, "CORTEX_ENRICHMENT_ENABLED"))
    check("CORTEX_ENRICHMENT_ENABLED is bool", isinstance(Config.CORTEX_ENRICHMENT_ENABLED, bool))


def test_2_config_ghostwriter():
    """Config: GHOSTWRITER_* constanten."""
    print("\n[Test 2] Config: GHOSTWRITER_* constanten")
    from danny_toolkit.core.config import Config
    check("GHOSTWRITER_DRY_RUN bestaat", hasattr(Config, "GHOSTWRITER_DRY_RUN"))
    check("GHOSTWRITER_DRY_RUN is bool", isinstance(Config.GHOSTWRITER_DRY_RUN, bool))
    check("GHOSTWRITER_MAX_PER_CYCLE bestaat", hasattr(Config, "GHOSTWRITER_MAX_PER_CYCLE"))
    check("GHOSTWRITER_MAX_PER_CYCLE is int", isinstance(Config.GHOSTWRITER_MAX_PER_CYCLE, int))
    check("GHOSTWRITER_MAX_PER_CYCLE default 10", Config.GHOSTWRITER_MAX_PER_CYCLE == 10)


def test_3_config_existing():
    """Config: bestaande Phase 37 constanten intact."""
    print("\n[Test 3] Config: Phase 37 constanten intact")
    from danny_toolkit.core.config import Config
    check("PRUNING_ENABLED bestaat", hasattr(Config, "PRUNING_ENABLED"))
    check("ENTROPY_THRESHOLD = 0.85", Config.ENTROPY_THRESHOLD == 0.85)
    check("REDUNDANCY_THRESHOLD = 0.90", Config.REDUNDANCY_THRESHOLD == 0.90)
    check("RECENCY_DECAY_DAYS = 14", Config.RECENCY_DECAY_DAYS == 14)


# ═══════════════════════════════════════════════════
# TEST 4-5: FASTAPI RESPONSE MODELS
# ═══════════════════════════════════════════════════

def test_4_fastapi_observatory_models():
    """FastAPI: Observatory Pydantic response models."""
    print("\n[Test 4] FastAPI: Observatory response models")
    import fastapi_server as fs
    check("AuditRapportResponse", hasattr(fs, "AuditRapportResponse"))
    check("AuditSchendingResponse", hasattr(fs, "AuditSchendingResponse"))
    check("ShardStatistiekResponse", hasattr(fs, "ShardStatistiekResponse"))
    check("FoutDefinitieResponse", hasattr(fs, "FoutDefinitieResponse"))
    check("FoutContextResponse", hasattr(fs, "FoutContextResponse"))
    check("PruningStatsResponse", hasattr(fs, "PruningStatsResponse"))
    check("BusStatsResponse", hasattr(fs, "BusStatsResponse"))


def test_5_fastapi_models_instantiate():
    """FastAPI: response models instantieerbaar."""
    print("\n[Test 5] FastAPI: response models instantieerbaar")
    from fastapi_server import (
        AuditRapportResponse, ShardStatistiekResponse,
        FoutDefinitieResponse, PruningStatsResponse, BusStatsResponse,
    )
    ar = AuditRapportResponse()
    check("AuditRapportResponse veilig=True default", ar.veilig is True)
    ss = ShardStatistiekResponse(naam="test")
    check("ShardStatistiekResponse naam=test", ss.naam == "test")
    check("ShardStatistiekResponse chunks=0 default", ss.aantal_chunks == 0)
    fd = FoutDefinitieResponse(naam="TestError", ernst="kritiek",
                                strategie="blokkeer", beschrijving="Test")
    check("FoutDefinitieResponse naam=TestError", fd.naam == "TestError")
    ps = PruningStatsResponse()
    check("PruningStatsResponse enabled=False default", ps.pruning_enabled is False)
    bs = BusStatsResponse()
    check("BusStatsResponse subscribers=0 default", bs.subscribers == 0)


# ═══════════════════════════════════════════════════
# TEST 6-7: FASTAPI ENDPOINT ROUTES
# ═══════════════════════════════════════════════════

def test_6_fastapi_observatory_routes():
    """FastAPI: Observatory routes geregistreerd."""
    print("\n[Test 6] FastAPI: Observatory routes")
    import fastapi_server as fs
    app = fs.app
    routes = [r.path for r in app.routes if hasattr(r, "path")]
    check("/api/v1/config/audit", "/api/v1/config/audit" in routes)
    check("/api/v1/shards/stats", "/api/v1/shards/stats" in routes)
    check("/api/v1/errors/taxonomy", "/api/v1/errors/taxonomy" in routes)
    check("/api/v1/errors/recent", "/api/v1/errors/recent" in routes)
    check("/api/v1/pruning/stats", "/api/v1/pruning/stats" in routes)
    check("/api/v1/pruning/run", "/api/v1/pruning/run" in routes)
    check("/api/v1/bus/stats", "/api/v1/bus/stats" in routes)


def test_7_fastapi_existing_routes():
    """FastAPI: bestaande routes intact."""
    print("\n[Test 7] FastAPI: bestaande routes intact")
    import fastapi_server as fs
    routes = [r.path for r in fs.app.routes if hasattr(r, "path")]
    check("/api/v1/query", "/api/v1/query" in routes)
    check("/api/v1/health", "/api/v1/health" in routes)
    check("/api/v1/trace/{trace_id}", "/api/v1/trace/{trace_id}" in routes)
    check("/api/v1/traces", "/api/v1/traces" in routes)


# ═══════════════════════════════════════════════════
# TEST 8-9: ERROR TAXONOMY ACTUATOR
# ═══════════════════════════════════════════════════

def test_8_error_taxonomy_retry_safe():
    """ErrorTaxonomy: is_retry_safe + classificeer."""
    print("\n[Test 8] ErrorTaxonomy: retry classificatie")
    from danny_toolkit.core.error_taxonomy import (
        is_retry_safe, classificeer, FoutErnst, HerstelStrategie,
    )
    # TimeoutError → retry_max=1, VOORBIJGAAND, RETRY
    check("TimeoutError is retry safe", is_retry_safe("TimeoutError"))
    d = classificeer("TimeoutError")
    check("TimeoutError ernst=VOORBIJGAAND", d.ernst == FoutErnst.VOORBIJGAAND)
    check("TimeoutError strategie=RETRY", d.strategie == HerstelStrategie.RETRY)
    check("TimeoutError retry_max=1", d.retry_max == 1)

    # ConnectionError → retry_max=2
    check("ConnectionError is retry safe", is_retry_safe("ConnectionError"))
    d2 = classificeer("ConnectionError")
    check("ConnectionError retry_max=2", d2.retry_max == 2)

    # ValueError → HERSTELBAAR, SKIP, niet retry safe
    check("ValueError is NOT retry safe", not is_retry_safe("ValueError"))

    # PromptInjectionError → BEVEILIGING, BLOKKEER
    d3 = classificeer("PromptInjectionError")
    check("PromptInjection ernst=BEVEILIGING", d3.ernst == FoutErnst.BEVEILIGING)
    check("PromptInjection strategie=BLOKKEER", d3.strategie == HerstelStrategie.BLOKKEER)


def test_9_error_ring_buffer():
    """SwarmEngine: error ring buffer + get_recent_errors."""
    print("\n[Test 9] SwarmEngine: error ring buffer")
    from swarm_engine import _record_error_context, get_recent_errors, _ERROR_HISTORY

    # Clear buffer
    _ERROR_HISTORY.clear()
    check("Buffer start leeg", len(_ERROR_HISTORY) == 0)

    # Simuleer FoutContext objecten
    from danny_toolkit.core.error_taxonomy import maak_fout_context
    fc1 = maak_fout_context(TimeoutError("test1"), "Agent1", "trace1")
    fc2 = maak_fout_context(ValueError("test2"), "Agent2", "trace2")
    _record_error_context(fc1)
    _record_error_context(fc2)

    check("Buffer heeft 2 entries", len(_ERROR_HISTORY) == 2)
    recent = get_recent_errors(count=10)
    check("get_recent_errors retourneert lijst", isinstance(recent, list))
    check("Nieuwste eerst (Agent2)", recent[0].agent == "Agent2")
    check("Oudste laatst (Agent1)", recent[1].agent == "Agent1")

    # Cleanup
    _ERROR_HISTORY.clear()


# ═══════════════════════════════════════════════════
# TEST 10-11: ERROR_CLASSIFIED NEURALBUS EVENT
# ═══════════════════════════════════════════════════

def test_10_error_classified_event():
    """NeuralBus: ERROR_CLASSIFIED event type bestaat."""
    print("\n[Test 10] NeuralBus: ERROR_CLASSIFIED event")
    from danny_toolkit.core.neural_bus import EventTypes
    check("ERROR_CLASSIFIED bestaat", hasattr(EventTypes, "ERROR_CLASSIFIED"))
    check("ERROR_CLASSIFIED is string", isinstance(EventTypes.ERROR_CLASSIFIED, str))


def test_11_publish_error_classified():
    """SwarmEngine: _publish_error_classified publiceert event."""
    print("\n[Test 11] SwarmEngine: _publish_error_classified")
    from danny_toolkit.core.neural_bus import get_bus, EventTypes
    from danny_toolkit.core.error_taxonomy import maak_fout_context
    from swarm_engine import SwarmEngine, _ERROR_HISTORY

    bus = get_bus()
    bus.reset()
    _ERROR_HISTORY.clear()

    # Maak een engine instantie
    try:
        from danny_toolkit.brain.trinity_omega import PrometheusBrain
        brain = PrometheusBrain()
    except Exception:
        brain = None
    engine = SwarmEngine(brain)

    fc = maak_fout_context(ConnectionError("test"), "TestAgent", "trace99")
    engine._publish_error_classified(fc)

    # Check NeuralBus
    history = bus.get_history(EventTypes.ERROR_CLASSIFIED, count=5)
    check("Event ontvangen op NeuralBus", len(history) >= 1)
    if history:
        evt = history[0]
        check("Bron is swarm_engine", evt.bron == "swarm_engine")
        check("fout_type in data", evt.data.get("fout_type") == "ConnectionError")
        check("agent in data", evt.data.get("agent") == "TestAgent")

    # Check ring buffer
    check("FoutContext in ring buffer", len(_ERROR_HISTORY) >= 1)

    bus.reset()
    _ERROR_HISTORY.clear()


# ═══════════════════════════════════════════════════
# TEST 12-13: GHOSTWRITER WRITE-BACK
# ═══════════════════════════════════════════════════

def test_12_ghostwriter_write_back():
    """GhostWriter: _write_back voegt docstring toe."""
    print("\n[Test 12] GhostWriter: _write_back")
    from danny_toolkit.brain.ghost_writer import GhostWriter
    gw = GhostWriter()

    # Maak een temp Python bestand
    source = 'def hello():\n    return "world"\n'
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py",
                                      delete=False, encoding="utf-8",
                                      dir=tempfile.gettempdir()) as f:
        f.write(source)
        tmp_path = f.name

    try:
        tree = ast.parse(source)
        func_node = None
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "hello":
                func_node = node
                break

        check("Functie node gevonden", func_node is not None)

        succes = gw._write_back(tmp_path, source, func_node, "Say hello to the world.")
        check("_write_back retourneert True", succes is True)

        # Lees terug en verifieer
        with open(tmp_path, "r", encoding="utf-8") as f:
            new_source = f.read()

        check("Docstring aanwezig in output", '"""Say hello to the world."""' in new_source)

        # Verifieer dat het nog steeds geldig Python is
        try:
            ast.parse(new_source)
            check("Output is geldig Python", True)
        except SyntaxError:
            check("Output is geldig Python", False)
    finally:
        os.unlink(tmp_path)


def test_13_ghostwriter_dry_run_param():
    """GhostWriter: haunt() accepteert dry_run + max_functies."""
    print("\n[Test 13] GhostWriter: haunt parameters")
    from danny_toolkit.brain.ghost_writer import GhostWriter
    import inspect
    sig = inspect.signature(GhostWriter.haunt)
    params = list(sig.parameters.keys())
    check("dry_run parameter", "dry_run" in params)
    check("max_functies parameter", "max_functies" in params)

    # Check defaults
    check("dry_run default=True", sig.parameters["dry_run"].default is True)
    check("max_functies default=10", sig.parameters["max_functies"].default == 10)

    # Check _write_back method exists
    check("_write_back method", hasattr(GhostWriter, "_write_back"))
    check("_already_processed method", hasattr(GhostWriter, "_already_processed"))
    check("_log_suggestion method", hasattr(GhostWriter, "_log_suggestion"))


# ═══════════════════════════════════════════════════
# TEST 14-15: CORTEX ACTIVATOR
# ═══════════════════════════════════════════════════

def test_14_cortex_in_swarm_pipeline():
    """SwarmEngine: _cortex init + CORTEX_ENRICHMENT_ENABLED check."""
    print("\n[Test 14] SwarmEngine: Cortex in pipeline")
    from swarm_engine import SwarmEngine

    try:
        from danny_toolkit.brain.trinity_omega import PrometheusBrain
        brain = PrometheusBrain()
    except Exception:
        brain = None
    engine = SwarmEngine(brain)

    check("_cortex attribuut bestaat", hasattr(engine, "_cortex"))
    check("_cortex start als None", engine._cortex is None)
    check("cortex_enrichments in metrics",
          "cortex_enrichments" in engine._swarm_metrics)

    # Check dat 4.5 step in run() source voorkomt
    import swarm_engine as se_mod
    source = inspect.getsource(se_mod.SwarmEngine.run)
    check("cortex_expand in run()", "cortex_expand" in source)
    check("hybrid_search in run()", "hybrid_search" in source)


def test_15_cortex_in_dreamer():
    """Dreamer: step 5.13 Cortex maintenance."""
    print("\n[Test 15] Dreamer: step 5.13 Cortex maintenance")
    import inspect
    from danny_toolkit.brain.dreamer import Dreamer
    source = inspect.getsource(Dreamer.rem_cycle)
    check("5.13 in rem_cycle", "5.13" in source)
    check("cortex_maintenance in rem_cycle", "cortex_maintenance" in source)
    check("confidence < 0.2 in rem_cycle", "confidence < 0.2" in source)


# ═══════════════════════════════════════════════════
# TEST 16-17: RETRY METRICS + DREAMER GHOSTWRITER
# ═══════════════════════════════════════════════════

def test_16_retry_metrics():
    """SwarmEngine: retry metrics in _swarm_metrics."""
    print("\n[Test 16] SwarmEngine: retry metrics")
    from swarm_engine import SwarmEngine

    try:
        from danny_toolkit.brain.trinity_omega import PrometheusBrain
        brain = PrometheusBrain()
    except Exception:
        brain = None
    engine = SwarmEngine(brain)

    check("error_retries_attempted in metrics",
          "error_retries_attempted" in engine._swarm_metrics)
    check("error_retries_succeeded in metrics",
          "error_retries_succeeded" in engine._swarm_metrics)
    check("error_retries_attempted = 0",
          engine._swarm_metrics["error_retries_attempted"] == 0)


def test_17_dreamer_ghostwriter_wiring():
    """Dreamer: GhostWriter met dry_run + max_functies."""
    print("\n[Test 17] Dreamer: GhostWriter wiring")
    import inspect
    from danny_toolkit.brain.dreamer import Dreamer
    source = inspect.getsource(Dreamer.rem_cycle)
    check("dry_run in rem_cycle", "dry_run" in source)
    check("GHOSTWRITER_DRY_RUN in rem_cycle", "GHOSTWRITER_DRY_RUN" in source)
    check("GHOSTWRITER_MAX_PER_CYCLE in rem_cycle", "GHOSTWRITER_MAX_PER_CYCLE" in source)
    check("max_functies in rem_cycle", "max_functies" in source)


# ═══════════════════════════════════════════════════
# TEST 18-19: CLI COMMANDS + NEURALBUS
# ═══════════════════════════════════════════════════

def test_18_cli_commands():
    """CLI: audit, pruning, shards functies bestaan."""
    print("\n[Test 18] CLI: Observatory commands")
    import cli as cli_mod
    check("show_audit functie", hasattr(cli_mod, "show_audit"))
    check("show_pruning functie", hasattr(cli_mod, "show_pruning"))
    check("show_shards functie", hasattr(cli_mod, "show_shards"))

    # Check source voor command routing
    import inspect
    source = inspect.getsource(cli_mod)
    check('cmd == "audit" in cli', 'cmd == "audit"' in source)
    check('cmd == "pruning" in cli', 'cmd == "pruning"' in source)
    check('cmd == "shards" in cli', 'cmd == "shards"' in source)


def test_19_neuralbus_all_events():
    """NeuralBus: alle Phase 35-38 event types."""
    print("\n[Test 19] NeuralBus: alle event types")
    from danny_toolkit.core.neural_bus import EventTypes
    phase_events = [
        # Phase 35
        "ERROR_CLASSIFIED",
        # Phase 36
        "REQUEST_TRACE_COMPLETE",
        # Phase 37
        "PRUNING_STARTED", "FRAGMENT_ARCHIVED",
        "FRAGMENT_DESTROYED", "PRUNING_COMPLETE",
    ]
    for evt in phase_events:
        check(f"{evt} bestaat", hasattr(EventTypes, evt))


# ═══════════════════════════════════════════════════
# TEST 20: VERSION BUMP + MODULE INTEGRITY
# ═══════════════════════════════════════════════════

def test_20_version_and_integrity():
    """Brain versie 6.5.0 + module integrity."""
    print("\n[Test 20] Versie 6.5.0 + module integrity")
    import danny_toolkit.brain as brain_pkg
    check(f"__version__ = {brain_pkg.__version__} (>= 6.5.0)",
          brain_pkg.__version__ >= "6.5.0")

    # Module imports
    modules = [
        "danny_toolkit.core.config",
        "danny_toolkit.core.neural_bus",
        "danny_toolkit.core.error_taxonomy",
        "danny_toolkit.core.request_tracer",
        "danny_toolkit.core.self_pruning",
        "danny_toolkit.core.shard_router",
        "danny_toolkit.brain.ghost_writer",
        "danny_toolkit.brain.dreamer",
    ]
    for m in modules:
        try:
            __import__(m)
            check(f"{m} importeert OK", True)
        except Exception as e:
            check(f"{m} importeert OK ({e})", False)

    # swarm_engine + fastapi_server
    try:
        import swarm_engine
        check("swarm_engine importeert OK", True)
    except Exception as e:
        check(f"swarm_engine importeert OK ({e})", False)

    try:
        import fastapi_server
        check("fastapi_server importeert OK", True)
    except Exception as e:
        check(f"fastapi_server importeert OK ({e})", False)

    # Retry logic in _timed_dispatch source
    import inspect
    source = inspect.getsource(swarm_engine.SwarmEngine._timed_dispatch)
    check("is_retry_safe in _timed_dispatch", "is_retry_safe" in source)
    check("_publish_error_classified in _timed_dispatch",
          "_publish_error_classified" in source)
    check("error_retries_attempted in _timed_dispatch",
          "error_retries_attempted" in source)


# ═══════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════

if __name__ == "__main__":
    import inspect

    print("=" * 60)
    print("Phase 38 — FULL-SPECTRUM ACTIVATION")
    print("=" * 60)

    test_1_config_cortex()
    test_2_config_ghostwriter()
    test_3_config_existing()
    test_4_fastapi_observatory_models()
    test_5_fastapi_models_instantiate()
    test_6_fastapi_observatory_routes()
    test_7_fastapi_existing_routes()
    test_8_error_taxonomy_retry_safe()
    test_9_error_ring_buffer()
    test_10_error_classified_event()
    test_11_publish_error_classified()
    test_12_ghostwriter_write_back()
    test_13_ghostwriter_dry_run_param()
    test_14_cortex_in_swarm_pipeline()
    test_15_cortex_in_dreamer()
    test_16_retry_metrics()
    test_17_dreamer_ghostwriter_wiring()
    test_18_cli_commands()
    test_19_neuralbus_all_events()
    test_20_version_and_integrity()

    print(f"\n{'=' * 60}")
    print(f"Resultaat: {passed}/{passed + failed} checks geslaagd")
    if failed == 0:
        print("  ALLE CHECKS GESLAAGD")
    else:
        print(f"  {failed} GEFAALD")
    print("=" * 60)
    sys.exit(1 if failed > 0 else 0)

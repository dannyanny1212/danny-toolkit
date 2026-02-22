"""
Phase 26: Pipeline Metrics + Startup Validation — Tests
========================================================
10 tests, ~30 checks.

Valideert:
- A1: _AGENT_PIPELINE_METRICS module-level dict
- A2: get_pipeline_metrics() callable
- A3: _record_agent_metric() stores data
- A4: Error tracking in metrics
- A5: get_stats() includes new keys
- A6: ResponseCache.stats() returns expected keys
- B1: valideer_opstart() rapport structuur
- B2: Missing GROQ_API_KEY -> fataal
- B3: DATA_DIR schrijfbaar check
- B4: Governor.enforce_api_keys includes GROQ
"""

import io
import os
import sys
import threading
import time
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# Test-mode env
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "-1")
os.environ.setdefault("DANNY_TEST_MODE", "1")
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("DANNY_TEST_MODE", "1")

geslaagd = 0
mislukt = 0


def check(naam, conditie, detail=""):
    global geslaagd, mislukt
    if conditie:
        geslaagd += 1
        print(f"  [OK] {naam}")
    else:
        mislukt += 1
        print(f"  [FAIL] {naam} {detail}")


# ==================================================================
# Test 1: _AGENT_PIPELINE_METRICS is module-level dict
# ==================================================================
print("\n=== Test 1: _AGENT_PIPELINE_METRICS module-level dict ===")
try:
    from swarm_engine import _AGENT_PIPELINE_METRICS, _METRICS_LOCK
    check("_AGENT_PIPELINE_METRICS is dict", isinstance(_AGENT_PIPELINE_METRICS, dict))
    check("_METRICS_LOCK is threading.Lock", isinstance(_METRICS_LOCK, type(threading.Lock())))
except Exception as e:
    check("Test 1 import", False, str(e))

# ==================================================================
# Test 2: get_pipeline_metrics() returns dict
# ==================================================================
print("\n=== Test 2: get_pipeline_metrics() callable ===")
try:
    from swarm_engine import get_pipeline_metrics
    check("get_pipeline_metrics is callable", callable(get_pipeline_metrics))
    result = get_pipeline_metrics()
    check("returns dict", isinstance(result, dict))
except Exception as e:
    check("Test 2", False, str(e))

# ==================================================================
# Test 3: _record_agent_metric() stores data
# ==================================================================
print("\n=== Test 3: _record_agent_metric() stores data ===")
try:
    from swarm_engine import SwarmEngine, _AGENT_PIPELINE_METRICS, _METRICS_LOCK

    # Clear metrics voor schone test
    with _METRICS_LOCK:
        _AGENT_PIPELINE_METRICS.clear()

    # Maak engine met mock brain
    class MockBrain:
        is_online = True
        governor = None
        nodes = {}
    engine = SwarmEngine.__new__(SwarmEngine)
    engine.brain = MockBrain()

    engine._record_agent_metric("TestAgent", 150.5)
    metrics = get_pipeline_metrics()
    check("TestAgent in metrics", "TestAgent" in metrics)
    check("calls == 1", metrics["TestAgent"]["calls"] == 1)
    check("avg_ms == 150.5", metrics["TestAgent"]["avg_ms"] == 150.5)
    check("errors == 0", metrics["TestAgent"]["errors"] == 0)
    check("success_rate == 100.0", metrics["TestAgent"]["success_rate"] == 100.0)
except Exception as e:
    check("Test 3", False, str(e))

# ==================================================================
# Test 4: Error tracking in metrics
# ==================================================================
print("\n=== Test 4: Error tracking ===")
try:
    with _METRICS_LOCK:
        _AGENT_PIPELINE_METRICS.clear()

    engine._record_agent_metric("FailAgent", 200.0, error=ValueError("test fout"))
    metrics = get_pipeline_metrics()
    check("errors == 1", metrics["FailAgent"]["errors"] == 1)
    check("last_error bevat 'test fout'", "test fout" in metrics["FailAgent"]["last_error"])

    # Succesvolle call na error
    engine._record_agent_metric("FailAgent", 100.0)
    metrics = get_pipeline_metrics()
    check("errors stays 1 after success", metrics["FailAgent"]["errors"] == 1)
    check("calls == 2", metrics["FailAgent"]["calls"] == 2)
except Exception as e:
    check("Test 4", False, str(e))

# ==================================================================
# Test 5: get_stats() includes new keys
# ==================================================================
print("\n=== Test 5: get_stats() includes new keys ===")
try:
    # Bouw een minimale SwarmEngine
    engine2 = SwarmEngine.__new__(SwarmEngine)
    engine2._query_count = 0
    engine2._total_time = 0.0
    engine2.agents = {}
    engine2._swarm_metrics = {}

    stats = engine2.get_stats()
    check("agent_metrics in stats", "agent_metrics" in stats)
    check("response_cache in stats", "response_cache" in stats)
    check("agent_metrics is dict", isinstance(stats["agent_metrics"], dict))
    check("response_cache is dict", isinstance(stats["response_cache"], dict))
except Exception as e:
    check("Test 5", False, str(e))

# ==================================================================
# Test 6: ResponseCache.stats() returns expected keys
# ==================================================================
print("\n=== Test 6: ResponseCache.stats() ===")
try:
    from danny_toolkit.core.response_cache import get_response_cache
    cache = get_response_cache()
    stats = cache.stats()
    check("hits in stats", "hits" in stats)
    check("misses in stats", "misses" in stats)
    check("hit_rate in stats", "hit_rate" in stats)
    check("entries in stats", "entries" in stats)
except Exception as e:
    check("Test 6", False, str(e))

# ==================================================================
# Test 7: valideer_opstart() rapport structuur
# ==================================================================
print("\n=== Test 7: valideer_opstart() rapport structuur ===")
try:
    from danny_toolkit.core.startup_validator import valideer_opstart
    rapport = valideer_opstart()
    check("rapport is dict", isinstance(rapport, dict))
    check("status in rapport", "status" in rapport)
    check("checks in rapport", "checks" in rapport)
    check("fouten in rapport", "fouten" in rapport)
    check("waarschuwingen in rapport", "waarschuwingen" in rapport)
except Exception as e:
    check("Test 7", False, str(e))

# ==================================================================
# Test 8: Missing GROQ_API_KEY -> fataal status
# ==================================================================
print("\n=== Test 8: Missing GROQ_API_KEY -> fataal ===")
try:
    # Bewaar en verwijder key
    original_key = os.environ.pop("GROQ_API_KEY", None)
    # Verwijder ook genummerde keys om geen false positive te krijgen
    saved_keys = {}
    for k in list(os.environ.keys()):
        if k.startswith("GROQ_API_KEY"):
            saved_keys[k] = os.environ.pop(k)

    rapport = valideer_opstart()
    check("status is FATAAL", rapport["status"] == "FATAAL")
    check("fouten niet leeg", len(rapport["fouten"]) > 0)

    # Herstel keys
    for k, v in saved_keys.items():
        os.environ[k] = v
    if original_key:
        os.environ["GROQ_API_KEY"] = original_key
except Exception as e:
    # Herstel keys bij error
    for k, v in saved_keys.items():
        os.environ[k] = v
    if original_key:
        os.environ["GROQ_API_KEY"] = original_key
    check("Test 8", False, str(e))

# ==================================================================
# Test 9: DATA_DIR schrijfbaar check
# ==================================================================
print("\n=== Test 9: DATA_DIR schrijfbaar ===")
try:
    rapport = valideer_opstart()
    dir_checks = [c for c in rapport["checks"] if c["naam"] == "DATA_DIR_schrijfbaar"]
    check("DATA_DIR check aanwezig", len(dir_checks) == 1)
    check("DATA_DIR is OK", dir_checks[0]["status"] == "OK")
except Exception as e:
    check("Test 9", False, str(e))

# ==================================================================
# Test 10: Governor.enforce_api_keys includes GROQ
# ==================================================================
print("\n=== Test 10: Governor GROQ key check ===")
try:
    from danny_toolkit.brain.governor import OmegaGovernor
    gov = OmegaGovernor()
    rapport = gov.enforce_api_keys()
    check("GROQ_API_KEY in rapport", "GROQ_API_KEY" in rapport)
except Exception as e:
    check("Test 10", False, str(e))


# ==================================================================
# RESULTAAT
# ==================================================================
print(f"\n{'=' * 50}")
print(f"  Phase 26: {geslaagd} geslaagd, {mislukt} mislukt")
print(f"{'=' * 50}")

sys.exit(0 if mislukt == 0 else 1)

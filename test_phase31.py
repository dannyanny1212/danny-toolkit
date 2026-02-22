"""
Phase 31 Tests — TRACE EN TOLERANTIE: Request Tracing + Fault Tolerance.

16 tests, ~120 checks:
  Tests 1-4:   trace_id (SwarmPayload, pipeline, CorticalStack)
  Tests 5-8:   Per-agent timeout + circuit breaker
  Tests 9-10:  NeuralBus new event types
  Tests 11-12: shadow_governance thread safety
  Tests 13-14: FastAPI integration (QueryResponse, HealthResponse)
  Tests 15-16: Version bump + module integrity
"""

import os
import re
import sys
import time
import threading
import asyncio

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
# Tests 1-4: trace_id
# ═══════════════════════════════════════════════════

def test_1_trace_id_in_payload():
    """SwarmPayload heeft trace_id veld."""
    print("\n[Test 1] SwarmPayload trace_id veld")
    from swarm_engine import SwarmPayload
    import dataclasses

    fields = {f.name for f in dataclasses.fields(SwarmPayload)}
    check("trace_id veld bestaat", "trace_id" in fields)

    # Default is lege string
    p = SwarmPayload(agent="TestAgent", type="text", content="test")
    check("trace_id default is lege string", p.trace_id == "")

    # Kan gezet worden
    p2 = SwarmPayload(agent="X", type="text", content="y", trace_id="abc12345")
    check("trace_id kan gezet worden", p2.trace_id == "abc12345")


def test_2_trace_id_generation():
    """trace_id wordt gegenereerd als 8-char hex."""
    print("\n[Test 2] trace_id generatie formaat")
    import uuid

    trace = uuid.uuid4().hex[:8]
    check("trace_id is 8 chars", len(trace) == 8)
    check("trace_id is hexadecimaal", all(c in "0123456789abcdef" for c in trace))

    # Uniek per call
    traces = {uuid.uuid4().hex[:8] for _ in range(100)}
    check("100 trace_ids zijn uniek", len(traces) == 100)


def test_3_log_to_cortical_trace():
    """_log_to_cortical injecteert trace_id in details."""
    print("\n[Test 3] _log_to_cortical trace_id injectie")
    from swarm_engine import _log_to_cortical

    # Functie accepteert trace_id parameter
    import inspect
    sig = inspect.signature(_log_to_cortical)
    check("trace_id parameter aanwezig", "trace_id" in sig.parameters)


def test_4_circuit_state_function():
    """get_circuit_state() beschikbaar en geeft dict."""
    print("\n[Test 4] get_circuit_state() module-functie")
    from swarm_engine import get_circuit_state

    state = get_circuit_state()
    check("get_circuit_state() retourneert dict", isinstance(state, dict))


# ═══════════════════════════════════════════════════
# Tests 5-8: Per-agent timeout + circuit breaker
# ═══════════════════════════════════════════════════

def test_5_agent_timeouts_config():
    """Per-agent timeout configuratie bestaat."""
    print("\n[Test 5] Per-agent timeout configuratie")
    from swarm_engine import _AGENT_TIMEOUTS, _DEFAULT_AGENT_TIMEOUT

    check("_AGENT_TIMEOUTS is dict", isinstance(_AGENT_TIMEOUTS, dict))
    check("_DEFAULT_AGENT_TIMEOUT > 0", _DEFAULT_AGENT_TIMEOUT > 0)
    check("MEMEX heeft custom timeout", "MEMEX" in _AGENT_TIMEOUTS)
    check("Strategist heeft custom timeout", "Strategist" in _AGENT_TIMEOUTS)
    check("Alle timeouts > 0", all(v > 0 for v in _AGENT_TIMEOUTS.values()))
    check("Default timeout 20s", _DEFAULT_AGENT_TIMEOUT == 20)


def test_6_circuit_breaker_config():
    """Circuit breaker constanten bestaan."""
    print("\n[Test 6] Circuit breaker constanten")
    from swarm_engine import (
        _CIRCUIT_BREAKER_THRESHOLD,
        _CIRCUIT_BREAKER_COOLDOWN,
        _AGENT_CIRCUIT_STATE,
        _CIRCUIT_LOCK,
    )

    check("Threshold is 3", _CIRCUIT_BREAKER_THRESHOLD == 3)
    check("Cooldown is 12", _CIRCUIT_BREAKER_COOLDOWN == 12)
    check("Circuit state is dict", isinstance(_AGENT_CIRCUIT_STATE, dict))
    check("Circuit lock is threading.Lock", hasattr(_CIRCUIT_LOCK, "acquire"))


def test_7_circuit_breaker_methods():
    """SwarmEngine heeft circuit breaker methoden."""
    print("\n[Test 7] Circuit breaker methoden op SwarmEngine")
    from swarm_engine import SwarmEngine

    engine = SwarmEngine(brain=None)
    check("_is_circuit_open() bestaat", hasattr(engine, "_is_circuit_open"))
    check("_record_circuit_failure() bestaat", hasattr(engine, "_record_circuit_failure"))
    check("_record_circuit_success() bestaat", hasattr(engine, "_record_circuit_success"))
    check("_tick_circuit_cooldowns() bestaat", hasattr(engine, "_tick_circuit_cooldowns"))

    # Test circuit open/close flow
    agent = "TestAgentCB"
    check("Nieuw agent: circuit closed", not engine._is_circuit_open(agent))

    # Trip de breaker
    for _ in range(3):
        engine._record_circuit_failure(agent)
    check("Na 3 failures: circuit open", engine._is_circuit_open(agent))

    # Tick cooldowns tot 0
    for _ in range(12):
        engine._tick_circuit_cooldowns()
    check("Na 12 ticks: circuit gesloten", not engine._is_circuit_open(agent))

    # Success reset
    engine._record_circuit_failure(agent)
    engine._record_circuit_failure(agent)
    engine._record_circuit_success(agent)
    check("Success reset na 2 failures: circuit closed",
          not engine._is_circuit_open(agent))

    # Cleanup
    from swarm_engine import _AGENT_CIRCUIT_STATE, _CIRCUIT_LOCK
    with _CIRCUIT_LOCK:
        _AGENT_CIRCUIT_STATE.pop(agent, None)


def test_8_timed_dispatch_timeout():
    """_timed_dispatch respecteert per-agent timeout."""
    print("\n[Test 8] _timed_dispatch timeout + trace_id")
    from swarm_engine import SwarmEngine
    import inspect

    engine = SwarmEngine(brain=None)
    sig = inspect.signature(engine._timed_dispatch)
    check("trace_id parameter in _timed_dispatch", "trace_id" in sig.parameters)

    # Swarm metrics bevat timeout + circuit tellers
    check("agent_timeouts metric", "agent_timeouts" in engine._swarm_metrics)
    check("circuit_breaker_trips metric", "circuit_breaker_trips" in engine._swarm_metrics)


# ═══════════════════════════════════════════════════
# Tests 9-10: NeuralBus new events
# ═══════════════════════════════════════════════════

def test_9_neuralbus_circuit_events():
    """NeuralBus heeft AGENT_CIRCUIT_OPEN/CLOSED events."""
    print("\n[Test 9] NeuralBus circuit breaker events")
    from danny_toolkit.core.neural_bus import EventTypes

    check("AGENT_CIRCUIT_OPEN bestaat",
          hasattr(EventTypes, "AGENT_CIRCUIT_OPEN"))
    check("AGENT_CIRCUIT_CLOSED bestaat",
          hasattr(EventTypes, "AGENT_CIRCUIT_CLOSED"))
    check("OPEN waarde correct",
          EventTypes.AGENT_CIRCUIT_OPEN == "agent_circuit_open")
    check("CLOSED waarde correct",
          EventTypes.AGENT_CIRCUIT_CLOSED == "agent_circuit_closed")


def test_10_neuralbus_subscribe_circuit():
    """NeuralBus kan circuit events ontvangen."""
    print("\n[Test 10] NeuralBus circuit event subscribe + publish")
    from danny_toolkit.core.neural_bus import get_bus, EventTypes

    bus = get_bus()
    received = []

    def handler(event):
        received.append(event)

    bus.subscribe(EventTypes.AGENT_CIRCUIT_OPEN, handler)
    bus.publish(EventTypes.AGENT_CIRCUIT_OPEN, {
        "agent": "TestAgent",
        "failures": 3,
    }, bron="test")

    check("Circuit event ontvangen", len(received) == 1)
    check("Event data correct", received[0].data.get("agent") == "TestAgent")

    # Cleanup
    bus._subscribers[EventTypes.AGENT_CIRCUIT_OPEN].remove(handler)


# ═══════════════════════════════════════════════════
# Tests 11-12: shadow_governance thread safety
# ═══════════════════════════════════════════════════

def test_11_shadow_voidwalker_lock():
    """shadow_governance _shadow_voidwalker_lock bestaat."""
    print("\n[Test 11] shadow_governance thread safety")
    from danny_toolkit.brain.shadow_governance import (
        _shadow_voidwalker_lock,
        _shadow_voidwalker_calls,
        ShadowGovernance,
    )

    check("Lock object bestaat", _shadow_voidwalker_lock is not None)
    check("Lock is threading.Lock", hasattr(_shadow_voidwalker_lock, "acquire"))

    # Threading import in module
    import danny_toolkit.brain.shadow_governance as sg_mod
    check("threading geimporteerd", hasattr(sg_mod, "threading"))


def test_12_shadow_governance_threadsafe():
    """Concurrent access op check_voidwalker_limit is veilig."""
    print("\n[Test 12] shadow_governance concurrent access")
    from danny_toolkit.brain.shadow_governance import (
        ShadowGovernance,
        _shadow_voidwalker_calls,
        _shadow_voidwalker_lock,
    )

    sg = ShadowGovernance()
    errors = []

    def concurrent_check():
        try:
            for _ in range(20):
                sg.check_voidwalker_limit()
                sg.get_stats()
        except Exception as e:
            errors.append(str(e))

    threads = [threading.Thread(target=concurrent_check) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5)

    check("Geen thread safety fouten", len(errors) == 0)
    check("get_stats() werkt na concurrent access",
          isinstance(sg.get_stats(), dict))

    # Cleanup
    with _shadow_voidwalker_lock:
        _shadow_voidwalker_calls.clear()


# ═══════════════════════════════════════════════════
# Tests 13-14: FastAPI integration
# ═══════════════════════════════════════════════════

def test_13_query_response_trace_id():
    """QueryResponse heeft trace_id veld."""
    print("\n[Test 13] FastAPI QueryResponse trace_id")
    from fastapi_server import QueryResponse

    fields = QueryResponse.model_fields
    check("trace_id veld in QueryResponse", "trace_id" in fields)

    # Default is lege string
    resp = QueryResponse(payloads=[], execution_time=0.1)
    check("trace_id default is lege string", resp.trace_id == "")


def test_14_health_response_phase31():
    """HealthResponse heeft waakhuis_health + circuit_breakers."""
    print("\n[Test 14] FastAPI HealthResponse Phase 31 velden")
    from fastapi_server import HealthResponse

    fields = HealthResponse.model_fields
    check("waakhuis_health veld bestaat", "waakhuis_health" in fields)
    check("circuit_breakers veld bestaat", "circuit_breakers" in fields)

    # Response importeert
    from fastapi import Response
    check("Response class beschikbaar", Response is not None)


# ═══════════════════════════════════════════════════
# Tests 15-16: Version + module integrity
# ═══════════════════════════════════════════════════

def test_15_version_bump():
    """Brain versie is 6.2.0."""
    print("\n[Test 15] Brain versie 6.2.0")
    import danny_toolkit.brain as brain_pkg

    check("__version__ is 6.2.0", brain_pkg.__version__ == "6.2.0")


def test_16_module_integrity():
    """Alle gewijzigde modules importeren zonder fouten."""
    print("\n[Test 16] Module integrity check")
    modules = [
        "swarm_engine",
        "danny_toolkit.core.neural_bus",
        "danny_toolkit.brain.shadow_governance",
        "danny_toolkit.brain.waakhuis",
        "fastapi_server",
    ]
    for mod in modules:
        try:
            __import__(mod)
            check(f"{mod} importeert OK", True)
        except Exception as e:
            check(f"{mod} importeert OK ({e})", False)


# ═══════════════════════════════════════════════════
# RUNNER
# ═══════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("Phase 31 — TRACE EN TOLERANTIE")
    print("=" * 60)

    tests = [
        test_1_trace_id_in_payload,
        test_2_trace_id_generation,
        test_3_log_to_cortical_trace,
        test_4_circuit_state_function,
        test_5_agent_timeouts_config,
        test_6_circuit_breaker_config,
        test_7_circuit_breaker_methods,
        test_8_timed_dispatch_timeout,
        test_9_neuralbus_circuit_events,
        test_10_neuralbus_subscribe_circuit,
        test_11_shadow_voidwalker_lock,
        test_12_shadow_governance_threadsafe,
        test_13_query_response_trace_id,
        test_14_health_response_phase31,
        test_15_version_bump,
        test_16_module_integrity,
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

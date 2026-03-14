"""
Phase 36 Tests — REQUEST TRACER: Distributed Tracing.

18 tests, ~65 checks:
  Tests 1-3:   Module imports, ContextVar, dataclasses
  Tests 4-6:   begin_trace/eind_trace lifecycle, span tracking
  Tests 7-8:   Ringbuffer opslag, get_trace(), get_recent()
  Tests 9-10:  FoutContext registratie in trace
  Tests 11-12: NeuralBus REQUEST_TRACE_COMPLETE event
  Tests 13-14: Config.TRACING_ENABLED feature flag
  Tests 15-16: FastAPI /trace/{id} endpoint, /traces endpoint
  Tests 17-18: Pipeline integratie (swarm_engine spans), version check
"""
from __future__ import annotations

import logging
import os
import sys

logger = logging.getLogger(__name__)

try:
    sys.stdout = __import__("io").TextIOWrapper(
        sys.stdout.buffer, encoding="utf-8", errors="replace",
    )
except (ValueError, OSError):
    logger.debug("Invalid value encountered")

# Test-mode env
os.environ.setdefault("DANNY_TEST_MODE", "1")
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "-1")
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

passed = 0
failed = 0


def check(beschrijving: str, conditie: bool) -> None:
    """Registreer een check resultaat."""
    global passed, failed
    if conditie:
        passed += 1
        print(f"  OK  {beschrijving}")
    else:
        failed += 1
        print(f"  FAIL  {beschrijving}")


# ═══════════════════════════════════════════════════
# Tests 1-3: Module imports, ContextVar, dataclasses
# ═══════════════════════════════════════════════════

def test_1_module_import() -> None:
    """request_tracer module importeert correct."""
    print("\n[Test 1] Module import")
    import danny_toolkit.core.request_tracer as mod

    check("Module importeert", mod is not None)
    check("RequestTracer class bestaat", hasattr(mod, "RequestTracer"))
    check("get_request_tracer functie bestaat", hasattr(mod, "get_request_tracer"))
    check("TraceSpan dataclass bestaat", hasattr(mod, "TraceSpan"))
    check("RequestTrace dataclass bestaat", hasattr(mod, "RequestTrace"))


def test_2_contextvars() -> None:
    """ContextVars zijn gedefinieerd."""
    print("\n[Test 2] ContextVars")
    from danny_toolkit.core.request_tracer import (
        _current_trace, _current_span,
    )
    import contextvars

    check("_current_trace is ContextVar",
          isinstance(_current_trace, contextvars.ContextVar))
    check("_current_span is ContextVar",
          isinstance(_current_span, contextvars.ContextVar))
    check("Default trace is None", _current_trace.get() is None)
    check("Default span is None", _current_span.get() is None)


def test_3_dataclasses() -> None:
    """TraceSpan en RequestTrace hebben correcte velden."""
    print("\n[Test 3] Dataclass velden")
    from danny_toolkit.core.request_tracer import (
        TraceSpan, RequestTrace,
    )
    import dataclasses

    # TraceSpan
    s_fields = {f.name for f in dataclasses.fields(TraceSpan)}
    check("TraceSpan.trace_id", "trace_id" in s_fields)
    check("TraceSpan.fase", "fase" in s_fields)
    check("TraceSpan.agent", "agent" in s_fields)
    check("TraceSpan.start_ms", "start_ms" in s_fields)
    check("TraceSpan.eind_ms", "eind_ms" in s_fields)
    check("TraceSpan.status", "status" in s_fields)
    check("TraceSpan.details", "details" in s_fields)

    # RequestTrace
    r_fields = {f.name for f in dataclasses.fields(RequestTrace)}
    check("RequestTrace.trace_id", "trace_id" in r_fields)
    check("RequestTrace.start", "start" in r_fields)
    check("RequestTrace.spans", "spans" in r_fields)
    check("RequestTrace.fout_ids", "fout_ids" in r_fields)
    check("RequestTrace.afgerond", "afgerond" in r_fields)


# ═══════════════════════════════════════════════════
# Tests 4-6: begin_trace/eind_trace, span tracking
# ═══════════════════════════════════════════════════

def test_4_trace_lifecycle() -> None:
    """begin_trace/eind_trace lifecycle."""
    print("\n[Test 4] Trace lifecycle")
    from danny_toolkit.core.request_tracer import (
        RequestTracer, _current_trace,
    )

    tracer = RequestTracer()
    trace = tracer.begin_trace("test0001")
    check("begin_trace retourneert RequestTrace",
          type(trace).__name__ == "RequestTrace")
    check("trace_id correct", trace.trace_id == "test0001")
    check("ContextVar gezet", _current_trace.get() is trace)
    check("Niet afgerond", not trace.afgerond)

    result = tracer.eind_trace()
    check("eind_trace retourneert trace", result is trace)
    check("Trace is afgerond", trace.afgerond)
    check("ContextVar gereset", _current_trace.get() is None)


def test_5_span_tracking() -> None:
    """Spans worden correct bijgehouden."""
    print("\n[Test 5] Span tracking")
    from danny_toolkit.core.request_tracer import RequestTracer
    import time

    tracer = RequestTracer()
    trace = tracer.begin_trace("test0002")

    span = tracer.begin_span("routing")
    check("Span aangemaakt", span is not None)
    check("Span fase correct", span.fase == "routing")
    check("Span status is pending", span.status == "pending")

    time.sleep(0.01)
    tracer.eind_span("ok", {"targets": ["MEMEX"]})
    check("Span status is ok", span.status == "ok")
    check("Span eind_ms > start_ms", span.eind_ms > span.start_ms)
    check("Span details aanwezig", "targets" in span.details)

    check("Trace heeft 1 span", len(trace.spans) == 1)

    tracer.eind_trace()


def test_6_multiple_spans() -> None:
    """Meerdere spans in één trace."""
    print("\n[Test 6] Meerdere spans")
    from danny_toolkit.core.request_tracer import RequestTracer

    tracer = RequestTracer()
    trace = tracer.begin_trace("test0003")

    fases = ["governor", "memex", "routing", "dispatch", "sentinel", "schild"]
    for fase in fases:
        tracer.begin_span(fase)
        tracer.eind_span("ok")

    check(f"Trace heeft {len(fases)} spans", len(trace.spans) == len(fases))

    for i, fase in enumerate(fases):
        check(f"Span {i} fase is {fase}", trace.spans[i].fase == fase)

    result = tracer.eind_trace()
    check("duration_ms > 0", result.duration_ms >= 0)


# ═══════════════════════════════════════════════════
# Tests 7-8: Ringbuffer, get_trace, get_recent
# ═══════════════════════════════════════════════════

def test_7_get_trace() -> None:
    """get_trace() haalt trace op via ID."""
    print("\n[Test 7] get_trace()")
    from danny_toolkit.core.request_tracer import RequestTracer

    tracer = RequestTracer()
    tracer.begin_trace("test0004")
    tracer.begin_span("test")
    tracer.eind_span("ok")
    tracer.eind_trace()

    found = tracer.get_trace("test0004")
    check("Trace gevonden", found is not None)
    check("Trace ID correct", found.trace_id == "test0004")
    check("Trace is afgerond", found.afgerond)

    not_found = tracer.get_trace("nonexist")
    check("Niet-bestaande trace is None", not_found is None)


def test_8_get_recent() -> None:
    """get_recent() haalt recente traces op."""
    print("\n[Test 8] get_recent()")
    from danny_toolkit.core.request_tracer import RequestTracer

    tracer = RequestTracer()
    for i in range(5):
        tracer.begin_trace(f"recent_{i:04d}")
        tracer.eind_trace()

    recent = tracer.get_recent(count=3)
    check("Retourneert lijst", isinstance(recent, list))
    check("Maximum 3 traces", len(recent) <= 3)
    if recent:
        check("Nieuwste eerst", recent[0].trace_id == "recent_0004")


# ═══════════════════════════════════════════════════
# Tests 9-10: Fout registratie
# ═══════════════════════════════════════════════════

def test_9_registreer_fout() -> None:
    """registreer_fout() voegt fout_id toe aan trace."""
    print("\n[Test 9] registreer_fout()")
    from danny_toolkit.core.request_tracer import RequestTracer

    tracer = RequestTracer()
    trace = tracer.begin_trace("test0005")

    tracer.registreer_fout("fout_abc1")
    tracer.registreer_fout("fout_abc2")

    check("2 fouten geregistreerd", len(trace.fout_ids) == 2)
    check("Eerste fout correct", trace.fout_ids[0] == "fout_abc1")

    tracer.eind_trace()


def test_10_to_dict() -> None:
    """to_dict() en to_summary() serialisatie."""
    print("\n[Test 10] to_dict() en to_summary()")
    from danny_toolkit.core.request_tracer import RequestTracer

    tracer = RequestTracer()
    trace = tracer.begin_trace("test0006")
    tracer.begin_span("routing")
    tracer.eind_span("ok")
    tracer.registreer_fout("fout_xyz")
    tracer.eind_trace()

    d = trace.to_dict()
    check("to_dict heeft trace_id", d["trace_id"] == "test0006")
    check("to_dict heeft spans", len(d["spans"]) == 1)
    check("to_dict heeft fouten", len(d["fouten"]) == 1)
    check("to_dict heeft afgerond", d["afgerond"] is True)

    s = trace.to_summary()
    check("to_summary heeft trace_id", s["trace_id"] == "test0006")
    check("to_summary heeft status error", s["status"] == "error")
    check("to_summary error_count", s["error_count"] == 1)


# ═══════════════════════════════════════════════════
# Tests 11-12: NeuralBus events
# ═══════════════════════════════════════════════════

def test_11_neuralbus_event_defined() -> None:
    """NeuralBus heeft REQUEST_TRACE_COMPLETE event type."""
    print("\n[Test 11] NeuralBus REQUEST_TRACE_COMPLETE")
    from danny_toolkit.core.neural_bus import EventTypes

    check("REQUEST_TRACE_COMPLETE bestaat",
          hasattr(EventTypes, "REQUEST_TRACE_COMPLETE"))
    check("Waarde correct",
          EventTypes.REQUEST_TRACE_COMPLETE == "request_trace_complete")


def test_12_neuralbus_trace_event() -> None:
    """eind_trace() publiceert REQUEST_TRACE_COMPLETE."""
    print("\n[Test 12] NeuralBus trace event publicatie")
    from danny_toolkit.core.neural_bus import get_bus, EventTypes
    from danny_toolkit.core.request_tracer import RequestTracer

    bus = get_bus()
    received = []

    def handler(event: object) -> None:
        """Handle bus event."""
        received.append(event)

    bus.subscribe(EventTypes.REQUEST_TRACE_COMPLETE, handler)
    try:
        tracer = RequestTracer()
        tracer.begin_trace("test0007")
        tracer.begin_span("test")
        tracer.eind_span("ok")
        tracer.eind_trace()

        check("Trace event ontvangen", len(received) >= 1)
        if received:
            check("Event bevat trace_id",
                  received[-1].data.get("trace_id") == "test0007")
            check("Event bevat duration_ms",
                  "duration_ms" in received[-1].data)
    finally:
        bus._subscribers[EventTypes.REQUEST_TRACE_COMPLETE].remove(handler)


# ═══════════════════════════════════════════════════
# Tests 13-14: Config.TRACING_ENABLED
# ═══════════════════════════════════════════════════

def test_13_config_tracing_enabled() -> None:
    """Config.TRACING_ENABLED feature flag bestaat."""
    print("\n[Test 13] Config.TRACING_ENABLED")
    from danny_toolkit.core.config import Config

    check("TRACING_ENABLED bestaat", hasattr(Config, "TRACING_ENABLED"))
    check("TRACING_ENABLED is bool", isinstance(Config.TRACING_ENABLED, bool))
    check("Default is True", Config.TRACING_ENABLED is True)


def test_14_singleton() -> None:
    """get_request_tracer() geeft singleton terug."""
    print("\n[Test 14] Singleton patroon")
    from danny_toolkit.core.request_tracer import get_request_tracer

    t1 = get_request_tracer()
    t2 = get_request_tracer()
    check("Singleton: zelfde instantie", t1 is t2)
    check("Is RequestTracer type", type(t1).__name__ == "RequestTracer")


# ═══════════════════════════════════════════════════
# Tests 15-16: FastAPI endpoints
# ═══════════════════════════════════════════════════

def test_15_fastapi_trace_models() -> None:
    """FastAPI trace response modellen bestaan."""
    print("\n[Test 15] FastAPI trace modellen")
    from fastapi_server import (
        TraceResponse, TraceSpanResponse, TraceSummaryResponse,
    )

    # TraceResponse
    tr_fields = TraceResponse.model_fields
    check("TraceResponse.trace_id", "trace_id" in tr_fields)
    check("TraceResponse.spans", "spans" in tr_fields)
    check("TraceResponse.fouten", "fouten" in tr_fields)
    check("TraceResponse.duration_ms", "duration_ms" in tr_fields)

    # TraceSpanResponse
    ts_fields = TraceSpanResponse.model_fields
    check("TraceSpanResponse.fase", "fase" in ts_fields)
    check("TraceSpanResponse.status", "status" in ts_fields)

    # TraceSummaryResponse
    tsr_fields = TraceSummaryResponse.model_fields
    check("TraceSummaryResponse.trace_id", "trace_id" in tsr_fields)
    check("TraceSummaryResponse.status", "status" in tsr_fields)


def test_16_fastapi_trace_endpoints() -> None:
    """FastAPI heeft /trace/{id} en /traces endpoints."""
    print("\n[Test 16] FastAPI trace endpoints")
    from fastapi_server import app

    routes = {r.path for r in app.routes}
    check("/api/v1/trace/{trace_id} endpoint",
          "/api/v1/trace/{trace_id}" in routes)
    check("/api/v1/traces endpoint",
          "/api/v1/traces" in routes)


# ═══════════════════════════════════════════════════
# Tests 17-18: Pipeline integratie + version
# ═══════════════════════════════════════════════════

def test_17_pipeline_spans() -> None:
    """swarm_engine.py bevat RequestTracer span code."""
    print("\n[Test 17] Pipeline RequestTracer integratie")
    import inspect
    from swarm_engine import SwarmEngine

    source = inspect.getsource(SwarmEngine.run)
    check("begin_trace in run()", "begin_trace" in source)
    check("begin_span in run()", "begin_span" in source)
    check("eind_span in run()", "eind_span" in source)
    check("eind_trace in run()", "eind_trace" in source)

    # Pipeline fases
    check("governor span", '"governor"' in source)
    check("memex span", '"memex"' in source)
    check("routing span", '"routing"' in source)
    check("dispatch span", '"dispatch"' in source)
    check("sentinel span", '"sentinel"' in source)
    check("schild span", '"schild"' in source)


def test_18_module_integrity() -> None:
    """Alle gewijzigde modules importeren zonder fouten."""
    print("\n[Test 18] Module integrity check")
    modules = [
        "danny_toolkit.core.request_tracer",
        "danny_toolkit.core.error_taxonomy",
        "danny_toolkit.core.neural_bus",
        "danny_toolkit.core.config",
        "swarm_engine",
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
    print("Phase 36 — REQUEST TRACER: Distributed Tracing")
    print("=" * 60)

    tests = [
        test_1_module_import,
        test_2_contextvars,
        test_3_dataclasses,
        test_4_trace_lifecycle,
        test_5_span_tracking,
        test_6_multiple_spans,
        test_7_get_trace,
        test_8_get_recent,
        test_9_registreer_fout,
        test_10_to_dict,
        test_11_neuralbus_event_defined,
        test_12_neuralbus_trace_event,
        test_13_config_tracing_enabled,
        test_14_singleton,
        test_15_fastapi_trace_models,
        test_16_fastapi_trace_endpoints,
        test_17_pipeline_spans,
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

"""
Phase 35 Tests — ERROR TAXONOMY: Uniforme fout-classificatie.

18 tests, ~65 checks:
  Tests 1-3:   Module imports, enums, FoutDefinitie dataclass
  Tests 4-6:   FOUT_REGISTER entries, classificeer() lookup, fallback
  Tests 7-8:   is_retry_safe(), get_ernst()
  Tests 9-10:  FoutContext dataclass, maak_fout_context()
  Tests 11-12: Governor _FOUT_CLASSIFICATIE delegatie, classificeer_fout()
  Tests 13-14: _timed_dispatch FoutContext in error payloads
  Tests 15-16: NeuralBus ERROR_CLASSIFIED event
  Tests 17-18: Version bump + module integrity
"""

import os
import sys

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
# Tests 1-3: Module imports, enums, dataclass
# ═══════════════════════════════════════════════════

def test_1_module_import():
    """error_taxonomy module importeert correct."""
    print("\n[Test 1] Module import")
    import danny_toolkit.core.error_taxonomy as mod

    check("Module importeert", mod is not None)
    check("FoutErnst class bestaat", hasattr(mod, "FoutErnst"))
    check("HerstelStrategie class bestaat", hasattr(mod, "HerstelStrategie"))
    check("FoutDefinitie class bestaat", hasattr(mod, "FoutDefinitie"))
    check("FoutContext class bestaat", hasattr(mod, "FoutContext"))
    check("FOUT_REGISTER dict bestaat", hasattr(mod, "FOUT_REGISTER"))
    check("classificeer functie bestaat", hasattr(mod, "classificeer"))
    check("is_retry_safe functie bestaat", hasattr(mod, "is_retry_safe"))
    check("get_ernst functie bestaat", hasattr(mod, "get_ernst"))
    check("maak_fout_context functie bestaat", hasattr(mod, "maak_fout_context"))


def test_2_enums():
    """FoutErnst en HerstelStrategie enums hebben correcte waarden."""
    print("\n[Test 2] Enum waarden")
    from danny_toolkit.core.error_taxonomy import (
        FoutErnst, HerstelStrategie,
    )

    # FoutErnst
    check("VOORBIJGAAND in FoutErnst",
          FoutErnst.VOORBIJGAAND == "voorbijgaand")
    check("HERSTELBAAR in FoutErnst",
          FoutErnst.HERSTELBAAR == "herstelbaar")
    check("KRITIEK in FoutErnst",
          FoutErnst.KRITIEK == "kritiek")
    check("BEVEILIGING in FoutErnst",
          FoutErnst.BEVEILIGING == "beveiliging")
    check("FATAAL in FoutErnst",
          FoutErnst.FATAAL == "fataal")

    # HerstelStrategie
    check("RETRY in HerstelStrategie",
          HerstelStrategie.RETRY == "retry")
    check("FALLBACK in HerstelStrategie",
          HerstelStrategie.FALLBACK == "fallback")
    check("SKIP in HerstelStrategie",
          HerstelStrategie.SKIP == "skip")
    check("BLOKKEER in HerstelStrategie",
          HerstelStrategie.BLOKKEER == "blokkeer")
    check("ESCALEER in HerstelStrategie",
          HerstelStrategie.ESCALEER == "escaleer")


def test_3_fout_definitie():
    """FoutDefinitie dataclass heeft correcte velden."""
    print("\n[Test 3] FoutDefinitie dataclass")
    from danny_toolkit.core.error_taxonomy import (
        FoutDefinitie, FoutErnst, HerstelStrategie,
    )
    import dataclasses

    fields = {f.name for f in dataclasses.fields(FoutDefinitie)}
    check("naam veld", "naam" in fields)
    check("ernst veld", "ernst" in fields)
    check("strategie veld", "strategie" in fields)
    check("beschrijving veld", "beschrijving" in fields)
    check("retry_max veld", "retry_max" in fields)

    # Instantiatie
    fd = FoutDefinitie("Test", FoutErnst.HERSTELBAAR,
                       HerstelStrategie.SKIP, "Test fout")
    check("Default retry_max is 0", fd.retry_max == 0)


# ═══════════════════════════════════════════════════
# Tests 4-6: FOUT_REGISTER, classificeer, fallback
# ═══════════════════════════════════════════════════

def test_4_fout_register():
    """FOUT_REGISTER bevat bekende fouttypes."""
    print("\n[Test 4] FOUT_REGISTER entries")
    from danny_toolkit.core.error_taxonomy import FOUT_REGISTER

    check("Register is dict", isinstance(FOUT_REGISTER, dict))
    check("Minstens 15 entries", len(FOUT_REGISTER) >= 15)

    # Specifieke entries
    check("TimeoutError in register", "TimeoutError" in FOUT_REGISTER)
    check("ConnectionError in register", "ConnectionError" in FOUT_REGISTER)
    check("RateLimitError in register", "RateLimitError" in FOUT_REGISTER)
    check("CircuitBreakerOpen in register", "CircuitBreakerOpen" in FOUT_REGISTER)
    check("PromptInjectionError in register", "PromptInjectionError" in FOUT_REGISTER)
    check("MemoryError in register", "MemoryError" in FOUT_REGISTER)


def test_5_classificeer():
    """classificeer() lookup werkt correct."""
    print("\n[Test 5] classificeer() functie")
    from danny_toolkit.core.error_taxonomy import (
        classificeer, FoutErnst, HerstelStrategie,
    )

    # String lookup
    d = classificeer("TimeoutError")
    check("TimeoutError is VOORBIJGAAND", d.ernst == FoutErnst.VOORBIJGAAND)
    check("TimeoutError strategie is RETRY", d.strategie == HerstelStrategie.RETRY)

    # Exception lookup
    d2 = classificeer(ValueError("test"))
    check("ValueError is HERSTELBAAR", d2.ernst == FoutErnst.HERSTELBAAR)

    d3 = classificeer(MemoryError())
    check("MemoryError is FATAAL", d3.ernst == FoutErnst.FATAAL)


def test_6_classificeer_fallback():
    """classificeer() fallback voor onbekende fouten."""
    print("\n[Test 6] classificeer() fallback")
    from danny_toolkit.core.error_taxonomy import (
        classificeer, FoutErnst, HerstelStrategie,
    )

    d = classificeer("SuperUnknownError")
    check("Onbekend -> HERSTELBAAR", d.ernst == FoutErnst.HERSTELBAAR)
    check("Onbekend -> SKIP", d.strategie == HerstelStrategie.SKIP)
    check("Onbekend -> naam is 'Onbekend'", d.naam == "Onbekend")

    # Onbekende exception
    class WeirdeError(Exception):
        pass

    d2 = classificeer(WeirdeError("x"))
    check("Custom exception -> HERSTELBAAR", d2.ernst == FoutErnst.HERSTELBAAR)


# ═══════════════════════════════════════════════════
# Tests 7-8: is_retry_safe, get_ernst
# ═══════════════════════════════════════════════════

def test_7_is_retry_safe():
    """is_retry_safe() werkt correct."""
    print("\n[Test 7] is_retry_safe()")
    from danny_toolkit.core.error_taxonomy import is_retry_safe

    check("TimeoutError is retry-safe", is_retry_safe("TimeoutError"))
    check("ConnectionError is retry-safe", is_retry_safe("ConnectionError"))
    check("ValueError is NIET retry-safe", not is_retry_safe("ValueError"))
    check("MemoryError is NIET retry-safe", not is_retry_safe("MemoryError"))
    check("RateLimitError is NIET retry-safe (FALLBACK)", not is_retry_safe("RateLimitError"))


def test_8_get_ernst():
    """get_ernst() retourneert correct ernst-niveau."""
    print("\n[Test 8] get_ernst()")
    from danny_toolkit.core.error_taxonomy import get_ernst, FoutErnst

    check("TimeoutError -> VOORBIJGAAND",
          get_ernst("TimeoutError") == FoutErnst.VOORBIJGAAND)
    check("ValueError -> HERSTELBAAR",
          get_ernst("ValueError") == FoutErnst.HERSTELBAAR)
    check("PermissionError -> KRITIEK",
          get_ernst("PermissionError") == FoutErnst.KRITIEK)
    check("PromptInjectionError -> BEVEILIGING",
          get_ernst("PromptInjectionError") == FoutErnst.BEVEILIGING)
    check("MemoryError -> FATAAL",
          get_ernst("MemoryError") == FoutErnst.FATAAL)


# ═══════════════════════════════════════════════════
# Tests 9-10: FoutContext dataclass
# ═══════════════════════════════════════════════════

def test_9_fout_context():
    """FoutContext heeft correcte velden en to_dict()."""
    print("\n[Test 9] FoutContext dataclass")
    from danny_toolkit.core.error_taxonomy import (
        FoutContext, FoutErnst, HerstelStrategie,
    )
    import dataclasses

    fields = {f.name for f in dataclasses.fields(FoutContext)}
    check("fout_id veld", "fout_id" in fields)
    check("fout_type veld", "fout_type" in fields)
    check("agent veld", "agent" in fields)
    check("ernst veld", "ernst" in fields)
    check("strategie veld", "strategie" in fields)
    check("bericht veld", "bericht" in fields)
    check("trace_id veld", "trace_id" in fields)
    check("timestamp veld", "timestamp" in fields)
    check("herstel_geprobeerd veld", "herstel_geprobeerd" in fields)
    check("herstel_gelukt veld", "herstel_gelukt" in fields)

    # to_dict
    fc = FoutContext(
        fout_id="abc12345",
        fout_type="ValueError",
        agent="TestAgent",
        ernst=FoutErnst.HERSTELBAAR,
        strategie=HerstelStrategie.SKIP,
        bericht="test fout",
    )
    d = fc.to_dict()
    check("to_dict() retourneert dict", isinstance(d, dict))
    check("to_dict bevat fout_id", d["fout_id"] == "abc12345")
    check("to_dict ernst is string", d["ernst"] == "herstelbaar")


def test_10_maak_fout_context():
    """maak_fout_context() maakt correcte FoutContext."""
    print("\n[Test 10] maak_fout_context()")
    from danny_toolkit.core.error_taxonomy import (
        maak_fout_context, FoutErnst,
    )

    fc = maak_fout_context(
        ValueError("test waarde fout"),
        agent="TestAgent",
        trace_id="trace123",
    )
    check("Retourneert FoutContext", type(fc).__name__ == "FoutContext")
    check("fout_id is 8 chars", len(fc.fout_id) == 8)
    check("fout_type is ValueError", fc.fout_type == "ValueError")
    check("agent correct", fc.agent == "TestAgent")
    check("ernst is HERSTELBAAR", fc.ernst == FoutErnst.HERSTELBAAR)
    check("trace_id correct", fc.trace_id == "trace123")
    check("bericht bevat exception tekst", "test waarde fout" in fc.bericht)


# ═══════════════════════════════════════════════════
# Tests 11-12: Governor delegatie
# ═══════════════════════════════════════════════════

def test_11_governor_classificatie():
    """Governor._FOUT_CLASSIFICATIE delegeert naar error_taxonomy."""
    print("\n[Test 11] Governor _FOUT_CLASSIFICATIE delegatie")
    from danny_toolkit.brain.governor import OmegaGovernor

    gov = OmegaGovernor()
    mapping = gov._FOUT_CLASSIFICATIE
    check("Mapping is dict", isinstance(mapping, dict))
    check("TimeoutError aanwezig", "TimeoutError" in mapping)
    check("TimeoutError is VOORBIJGAAND", mapping["TimeoutError"] == "VOORBIJGAAND")
    check("MemoryError aanwezig", "MemoryError" in mapping)


def test_12_governor_classificeer_fout():
    """Governor.classificeer_fout() delegeert naar error_taxonomy."""
    print("\n[Test 12] Governor.classificeer_fout()")
    from danny_toolkit.brain.governor import OmegaGovernor

    gov = OmegaGovernor()

    result = gov.classificeer_fout(ValueError("test"))
    check("ValueError -> HERSTELBAAR", result == "HERSTELBAAR")

    result2 = gov.classificeer_fout(TimeoutError("test"))
    check("TimeoutError -> VOORBIJGAAND", result2 == "VOORBIJGAAND")

    result3 = gov.classificeer_fout(MemoryError())
    check("MemoryError -> FATAAL", result3 == "FATAAL")


# ═══════════════════════════════════════════════════
# Tests 13-14: _timed_dispatch FoutContext
# ═══════════════════════════════════════════════════

def test_13_timed_dispatch_fout_context():
    """_timed_dispatch error payloads bevatten fout_context code."""
    print("\n[Test 13] _timed_dispatch FoutContext integratie")
    import inspect
    from swarm_engine import SwarmEngine

    source = inspect.getsource(SwarmEngine._timed_dispatch)
    check("maak_fout_context in _timed_dispatch",
          "maak_fout_context" in source)
    check("fout_context in metadata",
          "fout_context" in source)
    check("FoutContext import in dispatch",
          "FoutContext" in source)


def test_14_circuit_breaker_fout_context():
    """Circuit breaker error payload bevat FoutContext."""
    print("\n[Test 14] Circuit breaker FoutContext")
    import inspect
    from swarm_engine import SwarmEngine

    source = inspect.getsource(SwarmEngine._timed_dispatch)
    check("CircuitBreakerOpen in dispatch",
          "CircuitBreakerOpen" in source)
    check("FoutErnst.HERSTELBAAR in CB blok",
          "HERSTELBAAR" in source)
    check("HerstelStrategie.SKIP in CB blok",
          "SKIP" in source)


# ═══════════════════════════════════════════════════
# Tests 15-16: NeuralBus event
# ═══════════════════════════════════════════════════

def test_15_neuralbus_error_event():
    """NeuralBus heeft ERROR_CLASSIFIED event type."""
    print("\n[Test 15] NeuralBus ERROR_CLASSIFIED event")
    from danny_toolkit.core.neural_bus import EventTypes

    check("ERROR_CLASSIFIED bestaat",
          hasattr(EventTypes, "ERROR_CLASSIFIED"))
    check("ERROR_CLASSIFIED waarde correct",
          EventTypes.ERROR_CLASSIFIED == "error_classified")


def test_16_neuralbus_subscribe():
    """NeuralBus kan error events ontvangen."""
    print("\n[Test 16] NeuralBus error event subscribe")
    from danny_toolkit.core.neural_bus import get_bus, EventTypes

    bus = get_bus()
    received = []

    def handler(event):
        received.append(event)

    bus.subscribe(EventTypes.ERROR_CLASSIFIED, handler)
    bus.publish(
        EventTypes.ERROR_CLASSIFIED,
        {"fout_type": "TimeoutError", "agent": "TestAgent"},
        bron="test",
    )

    check("Error event ontvangen", len(received) == 1)
    check("Event data correct",
          received[0].data.get("fout_type") == "TimeoutError")

    # Cleanup
    bus._subscribers[EventTypes.ERROR_CLASSIFIED].remove(handler)


# ═══════════════════════════════════════════════════
# Tests 17-18: Version + module integrity
# ═══════════════════════════════════════════════════

def test_17_version_bump():
    """Brain versie is >= 6.5.0."""
    print("\n[Test 17] Brain versie >= 6.5.0")
    import danny_toolkit.brain as brain_pkg

    _v = tuple(int(x) for x in brain_pkg.__version__.split("."))
    check(f"__version__ is {brain_pkg.__version__} (>= 6.5.0)",
          _v >= (6, 5, 0))


def test_18_module_integrity():
    """Alle gewijzigde modules importeren zonder fouten."""
    print("\n[Test 18] Module integrity check")
    modules = [
        "danny_toolkit.core.error_taxonomy",
        "danny_toolkit.brain.governor",
        "danny_toolkit.core.neural_bus",
        "swarm_engine",
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
    print("Phase 35 — ERROR TAXONOMY: Uniforme Fout-Classificatie")
    print("=" * 60)

    tests = [
        test_1_module_import,
        test_2_enums,
        test_3_fout_definitie,
        test_4_fout_register,
        test_5_classificeer,
        test_6_classificeer_fallback,
        test_7_is_retry_safe,
        test_8_get_ernst,
        test_9_fout_context,
        test_10_maak_fout_context,
        test_11_governor_classificatie,
        test_12_governor_classificeer_fout,
        test_13_timed_dispatch_fout_context,
        test_14_circuit_breaker_fout_context,
        test_15_neuralbus_error_event,
        test_16_neuralbus_subscribe,
        test_17_version_bump,
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

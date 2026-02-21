"""
Test Brain Integrations — Phase 9+10 Verificatie
=================================================

Valideert de 6 brain inventions die in Phases 7-9 gewired zijn:
1. Strategist agent routing (AGENT_PROFIELEN + ROUTE_MAP)
2. Artificer agent routing (AGENT_PROFIELEN + ROUTE_MAP)
3. DevOpsDaemon.check_api_health() (async)
4. AdversarialTribunal.adeliberate() (async)
5. SwarmEngine._tribunal_verify (callable)
6. Dreamer._research_failures (method)
7. SwarmEngine.get_stats() extended metrics (9C/9D)
8. NeuralBus brain event types (Phase 7A)

Gebruik: python test_brain_integrations.py
"""

import inspect
import os
import sys
import time

# Windows UTF-8 fix
if os.name == "nt":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# Voeg project root toe aan path
sys.path.insert(0, os.path.dirname(__file__))

from swarm_engine import (
    SwarmEngine,
    AdaptiveRouter,
)


def _print_checks(checks):
    """Print check resultaten en return True als OK."""
    passed = 0
    failed = 0
    for name, ok in checks:
        icon = "[OK]" if ok else "[FAIL]"
        if ok:
            passed += 1
        else:
            failed += 1
        print(f"  {icon} {name}")

    print(
        f"\n  Resultaat: {passed}/{passed + failed}"
        f" geslaagd"
    )
    return failed == 0


def test_strategist_agent_routing():
    """Test 1: STRATEGIST profiel en ROUTE_MAP keywords."""
    print("\n" + "=" * 60)
    print("  TEST 1: Strategist Agent Routing")
    print("=" * 60)

    checks = []

    # AGENT_PROFIELEN bevat STRATEGIST
    profielen = AdaptiveRouter.AGENT_PROFIELEN
    checks.append((
        "STRATEGIST in AGENT_PROFIELEN",
        "STRATEGIST" in profielen,
    ))

    # ROUTE_MAP bevat STRATEGIST
    route_map = SwarmEngine.ROUTE_MAP
    checks.append((
        "STRATEGIST in ROUTE_MAP",
        "STRATEGIST" in route_map,
    ))

    # ROUTE_MAP keywords bevatten verwachte termen
    keywords = route_map.get("STRATEGIST", [])
    for term in ["missie", "strategie", "orchestreer"]:
        checks.append((
            f"ROUTE_MAP bevat '{term}'",
            term in keywords,
        ))

    # Profiel tekst bevat verwachte woorden
    profiel_text = " ".join(
        s for s in profielen.get("STRATEGIST", [])
    ).lower()
    for word in ["plan", "mission", "strategy"]:
        checks.append((
            f"Profiel bevat '{word}'",
            word in profiel_text,
        ))

    return _print_checks(checks)


def test_artificer_agent_routing():
    """Test 2: ARTIFICER profiel en ROUTE_MAP keywords."""
    print("\n" + "=" * 60)
    print("  TEST 2: Artificer Agent Routing")
    print("=" * 60)

    checks = []

    profielen = AdaptiveRouter.AGENT_PROFIELEN
    checks.append((
        "ARTIFICER in AGENT_PROFIELEN",
        "ARTIFICER" in profielen,
    ))

    route_map = SwarmEngine.ROUTE_MAP
    checks.append((
        "ARTIFICER in ROUTE_MAP",
        "ARTIFICER" in route_map,
    ))

    keywords = route_map.get("ARTIFICER", [])
    for term in ["forge", "smeed", "maak een tool"]:
        checks.append((
            f"ROUTE_MAP bevat '{term}'",
            term in keywords,
        ))

    profiel_text = " ".join(
        s for s in profielen.get("ARTIFICER", [])
    ).lower()
    for word in ["forge", "tool", "script"]:
        checks.append((
            f"Profiel bevat '{word}'",
            word in profiel_text,
        ))

    return _print_checks(checks)


def test_devops_health_check():
    """Test 3: DevOpsDaemon.check_api_health() bestaat en is async."""
    print("\n" + "=" * 60)
    print("  TEST 3: DevOpsDaemon Health Check")
    print("=" * 60)

    checks = []

    try:
        from danny_toolkit.brain.devops_daemon import (
            DevOpsDaemon,
        )
        checks.append((
            "DevOpsDaemon importeerbaar", True,
        ))
        checks.append((
            "check_api_health bestaat",
            hasattr(DevOpsDaemon, "check_api_health"),
        ))
        method = getattr(
            DevOpsDaemon, "check_api_health", None,
        )
        checks.append((
            "check_api_health is coroutine function",
            inspect.iscoroutinefunction(method),
        ))
    except ImportError as e:
        checks.append((
            f"DevOpsDaemon import: {e}", False,
        ))

    return _print_checks(checks)


def test_adversarial_adeliberate():
    """Test 4: AdversarialTribunal.adeliberate() bestaat en is async."""
    print("\n" + "=" * 60)
    print("  TEST 4: AdversarialTribunal.adeliberate()")
    print("=" * 60)

    checks = []

    try:
        from danny_toolkit.brain.adversarial_tribunal import (
            AdversarialTribunal,
        )
        checks.append((
            "AdversarialTribunal importeerbaar", True,
        ))
        checks.append((
            "adeliberate bestaat",
            hasattr(AdversarialTribunal, "adeliberate"),
        ))
        method = getattr(
            AdversarialTribunal, "adeliberate", None,
        )
        checks.append((
            "adeliberate is coroutine function",
            inspect.iscoroutinefunction(method),
        ))
        # deliberate (sync) moet ook bestaan
        checks.append((
            "deliberate (sync) bestaat",
            hasattr(AdversarialTribunal, "deliberate"),
        ))
    except ImportError as e:
        checks.append((
            f"AdversarialTribunal import: {e}", False,
        ))

    return _print_checks(checks)


def test_tribunal_verify_method():
    """Test 5: SwarmEngine._tribunal_verify is callable."""
    print("\n" + "=" * 60)
    print("  TEST 5: Tribunal Verify Method")
    print("=" * 60)

    checks = []

    checks.append((
        "_tribunal_verify bestaat op SwarmEngine",
        hasattr(SwarmEngine, "_tribunal_verify"),
    ))
    method = getattr(
        SwarmEngine, "_tribunal_verify", None,
    )
    checks.append((
        "_tribunal_verify is callable",
        callable(method),
    ))
    checks.append((
        "_tribunal_verify is coroutine function",
        inspect.iscoroutinefunction(method),
    ))

    # _tribunal property moet ook bestaan
    checks.append((
        "_tribunal property bestaat",
        isinstance(
            getattr(SwarmEngine, "_tribunal", None),
            property,
        ),
    ))

    return _print_checks(checks)


def test_dreamer_research_step():
    """Test 6: Dreamer._research_failures methode bestaat."""
    print("\n" + "=" * 60)
    print("  TEST 6: Dreamer Research Failures Step")
    print("=" * 60)

    checks = []

    try:
        from danny_toolkit.brain.dreamer import Dreamer
        checks.append((
            "Dreamer importeerbaar", True,
        ))
        checks.append((
            "_research_failures bestaat",
            hasattr(Dreamer, "_research_failures"),
        ))
        method = getattr(
            Dreamer, "_research_failures", None,
        )
        checks.append((
            "_research_failures is coroutine function",
            inspect.iscoroutinefunction(method),
        ))
        # rem_cycle moet ook bestaan
        checks.append((
            "rem_cycle bestaat",
            hasattr(Dreamer, "rem_cycle"),
        ))
        checks.append((
            "rem_cycle is coroutine function",
            inspect.iscoroutinefunction(
                getattr(Dreamer, "rem_cycle", None)
            ),
        ))
    except ImportError as e:
        checks.append((
            f"Dreamer import: {e}", False,
        ))

    return _print_checks(checks)


def test_get_stats_extended():
    """Test 7: get_stats() bevat alle 6 _swarm_metrics keys."""
    print("\n" + "=" * 60)
    print("  TEST 7: Extended get_stats() Metrics")
    print("=" * 60)

    checks = []

    engine = SwarmEngine()
    stats = engine.get_stats()

    # Originele 4 keys
    for key in [
        "queries_processed", "active_agents",
        "avg_response_ms", "registered_agents",
    ]:
        checks.append((
            f"stats bevat '{key}'",
            key in stats,
        ))

    # Nieuwe 6 metrics keys
    for key in [
        "fast_track_hits", "governor_blocks",
        "triples_extracted", "tribunal_verified",
        "tribunal_warnings", "tribunal_errors",
    ]:
        checks.append((
            f"stats bevat '{key}'",
            key in stats,
        ))

    # Totaal moet >= 10 keys zijn
    checks.append((
        f"stats heeft >= 10 keys ({len(stats)})",
        len(stats) >= 10,
    ))

    # Alle nieuwe metrics starten op 0
    checks.append((
        "nieuwe metrics starten op 0",
        all(
            stats.get(k, -1) == 0
            for k in [
                "fast_track_hits", "governor_blocks",
                "triples_extracted",
                "tribunal_verified",
                "tribunal_warnings",
                "tribunal_errors",
            ]
        ),
    ))

    return _print_checks(checks)


def test_neural_bus_brain_events():
    """Test 8: EventTypes bevat MISSION_STARTED, STEP_COMPLETED, FORGE_SUCCESS."""
    print("\n" + "=" * 60)
    print("  TEST 8: NeuralBus Brain Event Types")
    print("=" * 60)

    checks = []

    try:
        from danny_toolkit.core.neural_bus import (
            EventTypes,
        )
        checks.append((
            "EventTypes importeerbaar", True,
        ))
        for attr in [
            "MISSION_STARTED",
            "STEP_COMPLETED",
            "FORGE_SUCCESS",
        ]:
            checks.append((
                f"EventTypes.{attr} bestaat",
                hasattr(EventTypes, attr),
            ))

        # Waarden moeten non-empty strings zijn
        for attr in [
            "MISSION_STARTED",
            "STEP_COMPLETED",
            "FORGE_SUCCESS",
        ]:
            val = getattr(EventTypes, attr, None)
            checks.append((
                f"EventTypes.{attr} is non-empty str",
                isinstance(val, str) and len(val) > 0,
            ))
    except ImportError as e:
        checks.append((
            f"EventTypes import: {e}", False,
        ))

    return _print_checks(checks)


def main():
    """Draai alle Brain Integration tests."""
    print()
    print("=" * 60)
    print("  BRAIN INTEGRATIONS TEST — Phase 9+10")
    print("=" * 60)

    start = time.time()
    results = []

    results.append((
        "Strategist Agent Routing",
        test_strategist_agent_routing(),
    ))
    results.append((
        "Artificer Agent Routing",
        test_artificer_agent_routing(),
    ))
    results.append((
        "DevOpsDaemon Health Check",
        test_devops_health_check(),
    ))
    results.append((
        "AdversarialTribunal adeliberate",
        test_adversarial_adeliberate(),
    ))
    results.append((
        "Tribunal Verify Method",
        test_tribunal_verify_method(),
    ))
    results.append((
        "Dreamer Research Step",
        test_dreamer_research_step(),
    ))
    results.append((
        "Extended get_stats() Metrics",
        test_get_stats_extended(),
    ))
    results.append((
        "NeuralBus Brain Events",
        test_neural_bus_brain_events(),
    ))

    duur = time.time() - start

    print("\n" + "=" * 60)
    print("  EINDRESULTAAT")
    print("=" * 60)

    passed = 0
    failed = 0
    for name, ok in results:
        icon = "[OK]" if ok else "[FAIL]"
        if ok:
            passed += 1
        else:
            failed += 1
        print(f"  {icon} {name}")

    print(f"\n  {passed}/{len(results)} tests geslaagd"
          f" ({duur:.1f}s)")

    if failed == 0:
        print("  ALLE TESTS GESLAAGD!")
    else:
        print(f"  {failed} test(s) gefaald!")

    print("=" * 60)
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()

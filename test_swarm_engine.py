"""
Test Swarm Engine — v5.0 OOP + Asyncio Verificatie
====================================================

Test de SwarmEngine architectuur:
1. SwarmPayload dataclass
2. Fast-Track regex routing
3. Multi-intent keyword routing
4. EchoAgent (geen AI)
5. Agent classes (BrainAgent, Cipher, Vita, etc.)
6. SwarmEngine orchestrator (zonder brain)
7. SwarmEngine orchestrator (met brain, echte AI)
8. Parallelle executie (asyncio.gather)

Gebruik: python test_swarm_engine.py
"""

import sys
import os
import io
import time
import asyncio

# Windows UTF-8 fix
if os.name == "nt":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# Voeg project root toe aan path
sys.path.insert(0, os.path.dirname(__file__))

from swarm_engine import (
    SwarmPayload,
    SwarmEngine,
    EchoAgent,
    BrainAgent,
    CipherAgent,
    VitaAgent,
    AlchemistAgent,
    IolaaxAgent,
    _fast_track_check,
    _crypto_metrics,
    _health_chart,
    _data_chart,
    _code_media,
    run_swarm_sync,
)


def test_payload_dataclass():
    """Test 1: SwarmPayload structuur."""
    print("\n" + "=" * 60)
    print("  TEST 1: SwarmPayload Dataclass")
    print("=" * 60)

    checks = []

    # Basis aanmaak
    p = SwarmPayload(
        agent="Test", type="text",
        content="Hallo",
    )
    checks.append((
        "agent veld correct",
        p.agent == "Test",
    ))
    checks.append((
        "type veld correct",
        p.type == "text",
    ))
    checks.append((
        "content veld correct",
        p.content == "Hallo",
    ))
    checks.append((
        "timestamp automatisch gezet",
        p.timestamp > 0,
    ))
    checks.append((
        "metadata default is dict",
        isinstance(p.metadata, dict)
        and len(p.metadata) == 0,
    ))

    # Met metadata
    p2 = SwarmPayload(
        agent="Cipher", type="metrics",
        content="data",
        metadata={"execution_time": 2.5},
    )
    checks.append((
        "metadata bewaard",
        p2.metadata["execution_time"] == 2.5,
    ))

    return _print_checks(checks)


def test_fast_track():
    """Test 2: Fast-Track regex routing."""
    print("\n" + "=" * 60)
    print("  TEST 2: Fast-Track Regex Routing")
    print("=" * 60)

    checks = []

    # Begroetingen → Echo payload
    for greeting in ["hallo", "hoi", "hey", "hi",
                     "goedemorgen", "yo", "bedankt"]:
        result = _fast_track_check(greeting)
        checks.append((
            f"'{greeting}' → Echo payload",
            result is not None
            and result.agent == "Echo",
        ))

    # Complexe input → None
    result = _fast_track_check(
        "Analyseer de bitcoin markt en geef advies"
    )
    checks.append((
        "complexe input → None",
        result is None,
    ))

    # Lange begroeting → None (> 5 woorden)
    result = _fast_track_check(
        "hallo hoe gaat het vandaag met jou vriend"
    )
    checks.append((
        "lange begroeting (>5 woorden) → None",
        result is None,
    ))

    return _print_checks(checks)


def test_keyword_routing():
    """Test 3: Multi-intent keyword routing."""
    print("\n" + "=" * 60)
    print("  TEST 3: Multi-Intent Keyword Routing")
    print("=" * 60)

    checks = []
    engine = SwarmEngine(brain=None)

    # Single intent
    targets = asyncio.run(
        engine.route("bitcoin prijs analyse")
    )
    checks.append((
        "bitcoin → CIPHER",
        "CIPHER" in targets,
    ))

    targets = asyncio.run(
        engine.route("debug mijn python code")
    )
    checks.append((
        "code → IOLAAX",
        "IOLAAX" in targets,
    ))

    targets = asyncio.run(
        engine.route("gezondheid en slaap analyse")
    )
    checks.append((
        "gezondheid → VITA",
        "VITA" in targets,
    ))

    targets = asyncio.run(
        engine.route("search online informatie")
    )
    checks.append((
        "search → NAVIGATOR",
        "NAVIGATOR" in targets,
    ))

    # Multi-intent
    targets = asyncio.run(
        engine.route("bitcoin prijs en search nieuws")
    )
    checks.append((
        "multi: CIPHER + NAVIGATOR",
        "CIPHER" in targets
        and "NAVIGATOR" in targets,
    ))
    checks.append((
        "multi: exact 2 targets",
        len(targets) == 2,
    ))

    targets = asyncio.run(
        engine.route(
            "debug code en beveilig de firewall"
        )
    )
    checks.append((
        "multi: IOLAAX + SENTINEL",
        "IOLAAX" in targets
        and "SENTINEL" in targets,
    ))

    # Fallback naar ECHO
    targets = asyncio.run(
        engine.route("willekeurige onzin blabla")
    )
    checks.append((
        "onbekend → fallback ECHO",
        targets == ["ECHO"],
    ))

    return _print_checks(checks)


def test_echo_agent():
    """Test 4: EchoAgent zonder AI."""
    print("\n" + "=" * 60)
    print("  TEST 4: EchoAgent (geen AI)")
    print("=" * 60)

    checks = []
    agent = EchoAgent("Echo", "Interface")

    # Process retourneert SwarmPayload
    payload = asyncio.run(
        agent.process("hallo", brain=None)
    )
    checks.append((
        "retourneert SwarmPayload",
        isinstance(payload, SwarmPayload),
    ))
    checks.append((
        "agent == 'Echo'",
        payload.agent == "Echo",
    ))
    checks.append((
        "type == 'text'",
        payload.type == "text",
    ))
    checks.append((
        "content is een response",
        payload.content in EchoAgent.RESPONSES,
    ))

    # Meerdere calls → random responses
    responses = set()
    for _ in range(20):
        p = asyncio.run(
            agent.process("test", brain=None)
        )
        responses.add(p.content)
    checks.append((
        "random variatie (>1 unieke)",
        len(responses) > 1,
    ))

    return _print_checks(checks)


def test_agent_classes():
    """Test 5: Agent class hierarchie."""
    print("\n" + "=" * 60)
    print("  TEST 5: Agent Class Hierarchie")
    print("=" * 60)

    checks = []

    from danny_toolkit.brain.trinity_omega import (
        CosmicRole,
    )

    # BrainAgent zonder brain → "Brain offline"
    agent = BrainAgent(
        "Test", "Testing", CosmicRole.ECHO,
    )
    payload = asyncio.run(
        agent.process("test", brain=None)
    )
    checks.append((
        "BrainAgent zonder brain → offline",
        "Brain offline" in payload.content,
    ))

    # CipherAgent erft van BrainAgent
    cipher = CipherAgent(
        "Cipher", "Finance", CosmicRole.CIPHER,
    )
    checks.append((
        "CipherAgent is BrainAgent",
        isinstance(cipher, BrainAgent),
    ))
    payload = asyncio.run(
        cipher.process("bitcoin", brain=None)
    )
    checks.append((
        "Cipher type == 'metrics'",
        payload.type == "metrics",
    ))
    checks.append((
        "Cipher heeft media metadata",
        "media" in payload.metadata,
    ))

    # VitaAgent
    vita = VitaAgent(
        "Vita", "Health", CosmicRole.VITA,
    )
    payload = asyncio.run(
        vita.process("gezondheid", brain=None)
    )
    checks.append((
        "Vita type == 'area_chart'",
        payload.type == "area_chart",
    ))

    # AlchemistAgent
    alch = AlchemistAgent(
        "Alchemist", "Data", CosmicRole.ALCHEMIST,
    )
    payload = asyncio.run(
        alch.process("data analyse", brain=None)
    )
    checks.append((
        "Alchemist type == 'bar_chart'",
        payload.type == "bar_chart",
    ))

    # IolaaxAgent zonder code → type blijft text
    iolaax = IolaaxAgent(
        "Iolaax", "Engineer", CosmicRole.IOLAAX,
    )
    payload = asyncio.run(
        iolaax.process("debug", brain=None)
    )
    checks.append((
        "Iolaax zonder code → type 'text'",
        payload.type == "text",
    ))

    return _print_checks(checks)


def test_engine_no_brain():
    """Test 6: SwarmEngine zonder brain."""
    print("\n" + "=" * 60)
    print("  TEST 6: SwarmEngine (zonder brain)")
    print("=" * 60)

    checks = []
    logs = []

    def callback(msg):
        logs.append(msg)

    # Fast-track
    payloads = run_swarm_sync(
        "hallo", brain=None, callback=callback,
    )
    checks.append((
        "fast-track → 1 payload",
        len(payloads) == 1,
    ))
    checks.append((
        "fast-track → Echo",
        payloads[0].agent == "Echo",
    ))
    checks.append((
        "callback logs ontvangen",
        len(logs) > 0,
    ))
    checks.append((
        "SWARM COMPLETE in logs",
        any("COMPLETE" in l for l in logs),
    ))

    # Complexe query zonder brain
    logs.clear()
    payloads = run_swarm_sync(
        "bitcoin analyse", brain=None,
        callback=callback,
    )
    checks.append((
        "zonder brain → payload aanwezig",
        len(payloads) >= 1,
    ))
    checks.append((
        "zonder brain → Brain offline",
        "Brain offline" in payloads[0].content,
    ))

    # Multi-intent zonder brain
    logs.clear()
    payloads = run_swarm_sync(
        "bitcoin prijs en search nieuws",
        brain=None, callback=callback,
    )
    checks.append((
        "multi-intent → 2 payloads",
        len(payloads) == 2,
    ))
    agents = {p.agent for p in payloads}
    checks.append((
        "multi-intent → Cipher + Navigator",
        "Cipher" in agents
        and "Navigator" in agents,
    ))

    return _print_checks(checks)


def test_media_generators():
    """Test 7: Media generators in swarm_engine."""
    print("\n" + "=" * 60)
    print("  TEST 7: Media Generators")
    print("=" * 60)

    checks = []

    # Crypto metrics
    media = _crypto_metrics()
    checks.append((
        "crypto: type == 'metrics'",
        media["type"] == "metrics",
    ))
    checks.append((
        "crypto: 4 tickers",
        len(media["metrics"]) == 4,
    ))

    # Health chart
    media = _health_chart()
    checks.append((
        "health: type == 'area_chart'",
        media["type"] == "area_chart",
    ))

    # Data chart
    media = _data_chart()
    checks.append((
        "data: type == 'bar_chart'",
        media["type"] == "bar_chart",
    ))

    # Code media
    media = _code_media(
        "```python\nx = 1\n```"
    )
    checks.append((
        "code: block gedetecteerd",
        media is not None
        and media["type"] == "code",
    ))

    media = _code_media("geen code hier")
    checks.append((
        "code: geen block → None",
        media is None,
    ))

    return _print_checks(checks)


def test_engine_with_brain():
    """Test 8: SwarmEngine met echte PrometheusBrain."""
    print("\n" + "=" * 60)
    print("  TEST 8: SwarmEngine (met brain, echte AI)")
    print("=" * 60)

    from contextlib import redirect_stdout
    from danny_toolkit.brain.trinity_omega import (
        PrometheusBrain,
    )

    buf = io.StringIO()
    with redirect_stdout(buf):
        brain = PrometheusBrain()

    checks = []
    logs = []

    def callback(msg):
        logs.append(msg)

    # Fast-track met brain (governor + echo)
    payloads = run_swarm_sync(
        "hoi", brain, callback=callback,
    )
    checks.append((
        "fast-track met brain → Echo",
        len(payloads) == 1
        and payloads[0].agent == "Echo",
    ))
    checks.append((
        "Governor SAFE in logs",
        any("SAFE" in l for l in logs),
    ))

    # Single agent met brain
    logs.clear()
    buf = io.StringIO()
    with redirect_stdout(buf):
        payloads = run_swarm_sync(
            "bitcoin blockchain analyse",
            brain, callback=callback,
        )
    checks.append((
        "cipher → content niet leeg",
        len(payloads) >= 1
        and len(payloads[0].content) > 10,
    ))
    checks.append((
        "cipher → type metrics",
        payloads[0].type == "metrics",
    ))
    checks.append((
        "cipher → media in metadata",
        "media" in payloads[0].metadata,
    ))
    checks.append((
        "Chronos in logs",
        any("Chronos" in l for l in logs),
    ))

    # Multi-intent met brain (parallel)
    logs.clear()
    start = time.time()
    buf = io.StringIO()
    with redirect_stdout(buf):
        payloads = run_swarm_sync(
            "crypto wallet en search informatie",
            brain, callback=callback,
        )
    elapsed = time.time() - start

    checks.append((
        "multi-intent → 2 payloads",
        len(payloads) == 2,
    ))
    agents = [p.agent for p in payloads]
    checks.append((
        "multi-intent → Cipher + Navigator",
        "Cipher" in agents
        and "Navigator" in agents,
    ))
    checks.append((
        "Nexus routing in logs",
        any("Nexus" in l for l in logs),
    ))
    checks.append((
        "SWARM COMPLETE in logs",
        any("COMPLETE" in l for l in logs),
    ))

    return _print_checks(checks)


# --- HELPER ---

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


def main():
    """Draai alle Swarm Engine tests."""
    print()
    print("=" * 60)
    print("  SWARM ENGINE TEST — v5.0 OOP + Asyncio")
    print("=" * 60)

    start = time.time()
    results = []

    # Unit tests (geen brain nodig)
    results.append((
        "SwarmPayload Dataclass",
        test_payload_dataclass(),
    ))
    results.append((
        "Fast-Track Regex",
        test_fast_track(),
    ))
    results.append((
        "Multi-Intent Routing",
        test_keyword_routing(),
    ))
    results.append((
        "EchoAgent",
        test_echo_agent(),
    ))
    results.append((
        "Agent Hierarchie",
        test_agent_classes(),
    ))
    results.append((
        "Engine zonder Brain",
        test_engine_no_brain(),
    ))
    results.append((
        "Media Generators",
        test_media_generators(),
    ))

    # Integratie test (laadt brain)
    results.append((
        "Engine met Brain (AI)",
        test_engine_with_brain(),
    ))

    elapsed = time.time() - start
    passed = sum(1 for _, ok in results if ok)
    total = len(results)

    print()
    print("=" * 60)
    print("  EINDRESULTAAT")
    print("=" * 60)
    for name, ok in results:
        icon = "[OK]" if ok else "[FAIL]"
        print(f"  {icon} {name}")
    print(
        f"\n  {passed}/{total} tests geslaagd"
        f" ({elapsed:.1f}s)"
    )
    print("=" * 60)

    if passed < total:
        print("\n  SOMMIGE TESTS GEFAALD!")
        sys.exit(1)
    else:
        print("\n  ALLE TESTS GESLAAGD!")


if __name__ == "__main__":
    main()

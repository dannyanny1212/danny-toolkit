"""
Test Full Chain - Chain of Command Verificatie
==============================================

Uitgebreide test van de multi-node orchestratie:
1. DOMAIN_KEYWORDS detectie
2. chain_of_command() flow
3. Multi-domein queries
4. Single-domein fallback
5. Lege query fallback naar Weaver

Gebruik: python -m danny_toolkit.test_full_chain
"""

import sys
import time

from danny_toolkit.brain.trinity_omega import (
    PrometheusBrain,
    CosmicRole,
)


def test_domain_detection(brain: PrometheusBrain):
    """Test 1: DOMAIN_KEYWORDS multi-domein detectie."""
    print("\n" + "=" * 60)
    print("  TEST 1: Domain Detection (keyword matching)")
    print("=" * 60)

    cases = [
        (
            "Bitcoin prijs en stress-niveau",
            {CosmicRole.CIPHER, CosmicRole.VITA},
        ),
        (
            "Zoek kennis over blockchain history",
            {CosmicRole.CIPHER, CosmicRole.ARCHIVIST,
             CosmicRole.ECHO},
        ),
        (
            "Brainstorm creatief idee voor security",
            {CosmicRole.SPARK, CosmicRole.SENTINEL},
        ),
        (
            "Schedule een cronjob voor data cleanup",
            {CosmicRole.CHRONOS, CosmicRole.VOID},
        ),
        (
            "Hallo wereld",
            set(),  # geen domeinen
        ),
    ]

    passed = 0
    failed = 0

    for query, expected_roles in cases:
        result = brain._detect_domains(query)
        found_roles = set(result.keys())

        ok = expected_roles == found_roles
        icon = "[OK]" if ok else "[FAIL]"

        if ok:
            passed += 1
        else:
            failed += 1

        print(f"\n  {icon} \"{query}\"")
        if ok:
            names = [r.name for r in found_roles]
            print(f"       -> {', '.join(names) or '(geen)'}")
        else:
            expected = [r.name for r in expected_roles]
            found = [r.name for r in found_roles]
            print(f"       Verwacht: {', '.join(expected)}")
            print(f"       Gevonden: {', '.join(found)}")

    print(f"\n  Resultaat: {passed}/{passed + failed} geslaagd")
    return failed == 0


def test_chain_multi_domain(brain: PrometheusBrain):
    """Test 2: Chain of Command met multi-domein query."""
    print("\n" + "=" * 60)
    print("  TEST 2: Chain of Command - Multi-Domain")
    print("=" * 60)

    query = (
        "Wat is de huidige Bitcoin prijs en wat "
        "betekent dat voor mijn stress-niveau?"
    )
    result = brain.chain_of_command(query)

    checks = []

    # Check 1: query in result
    checks.append((
        "query in result",
        result["query"] == query,
    ))

    # Check 2: Pixel is ontvanger
    checks.append((
        "ontvanger is Pixel",
        result["ontvanger"] == "Pixel",
    ))

    # Check 3: Iolaax is analyse
    checks.append((
        "analyse is Iolaax",
        result["analyse"] == "Iolaax",
    ))

    # Check 4: minstens 2 sub-taken (Cipher + Vita)
    checks.append((
        "minstens 2 sub-taken",
        len(result["sub_taken"]) >= 2,
    ))

    # Check 5: Cipher betrokken
    cipher_found = any(
        st["node"] == "Cipher"
        for st in result["sub_taken"]
    )
    checks.append((
        "Cipher in sub-taken",
        cipher_found,
    ))

    # Check 6: Vita betrokken
    vita_found = any(
        st["node"] == "Vita"
        for st in result["sub_taken"]
    )
    checks.append((
        "Vita in sub-taken",
        vita_found,
    ))

    # Check 7: nodes_betrokken bevat minstens 4
    checks.append((
        "minstens 4 nodes betrokken",
        len(result["nodes_betrokken"]) >= 4,
    ))

    # Check 8: Pixel en Iolaax in nodes_betrokken
    checks.append((
        "Pixel + Iolaax in nodes_betrokken",
        "Pixel" in result["nodes_betrokken"]
        and "Iolaax" in result["nodes_betrokken"],
    ))

    # Check 9: synthese is niet leeg
    checks.append((
        "synthese niet leeg",
        len(result["synthese"]) > 0,
    ))

    # Check 10: execution_time > 0
    checks.append((
        "execution_time > 0",
        result["execution_time"] > 0,
    ))

    passed = 0
    failed = 0
    for name, ok in checks:
        icon = "[OK]" if ok else "[FAIL]"
        if ok:
            passed += 1
        else:
            failed += 1
        print(f"  {icon} {name}")

    print(f"\n  Resultaat: {passed}/{passed + failed} geslaagd")
    return failed == 0


def test_chain_single_domain(brain: PrometheusBrain):
    """Test 3: Chain of Command met single-domein query."""
    print("\n" + "=" * 60)
    print("  TEST 3: Chain of Command - Single Domain")
    print("=" * 60)

    query = "Analyseer de HRV health data van vandaag"
    result = brain.chain_of_command(query)

    checks = []

    # Vita moet de enige specialist zijn
    vita_found = any(
        st["node"] == "Vita"
        for st in result["sub_taken"]
    )
    checks.append((
        "Vita in sub-taken",
        vita_found,
    ))

    # Pixel + Iolaax altijd aanwezig
    checks.append((
        "Pixel + Iolaax in flow",
        "Pixel" in result["nodes_betrokken"]
        and "Iolaax" in result["nodes_betrokken"],
    ))

    passed = 0
    failed = 0
    for name, ok in checks:
        icon = "[OK]" if ok else "[FAIL]"
        if ok:
            passed += 1
        else:
            failed += 1
        print(f"  {icon} {name}")

    print(f"\n  Resultaat: {passed}/{passed + failed} geslaagd")
    return failed == 0


def test_chain_no_domain(brain: PrometheusBrain):
    """Test 4: Chain of Command zonder herkenbaar domein."""
    print("\n" + "=" * 60)
    print("  TEST 4: Chain of Command - Geen Domein (Fallback)")
    print("=" * 60)

    query = "Hallo, hoe gaat het met je?"
    result = brain.chain_of_command(query)

    checks = []

    # Fallback naar Pixel
    pixel_found = any(
        st["node"] == "Pixel"
        for st in result["sub_taken"]
    )
    checks.append((
        "Fallback naar Pixel",
        pixel_found,
    ))

    # Nog steeds Pixel + Iolaax in flow
    checks.append((
        "Pixel + Iolaax in flow",
        "Pixel" in result["nodes_betrokken"]
        and "Iolaax" in result["nodes_betrokken"],
    ))

    passed = 0
    failed = 0
    for name, ok in checks:
        icon = "[OK]" if ok else "[FAIL]"
        if ok:
            passed += 1
        else:
            failed += 1
        print(f"  {icon} {name}")

    print(f"\n  Resultaat: {passed}/{passed + failed} geslaagd")
    return failed == 0


def test_chain_three_domains(brain: PrometheusBrain):
    """Test 5: Chain of Command met 3 domeinen."""
    print("\n" + "=" * 60)
    print("  TEST 5: Chain of Command - 3 Domeinen")
    print("=" * 60)

    query = (
        "Zoek kennis over blockchain history "
        "en de impact op gezondheid"
    )
    result = brain.chain_of_command(query)

    checks = []

    # Minstens 3 sub-taken
    checks.append((
        "minstens 3 sub-taken",
        len(result["sub_taken"]) >= 3,
    ))

    # Cipher, Echo/Archivist, Vita betrokken
    node_names = [st["node"] for st in result["sub_taken"]]
    checks.append((
        "Cipher betrokken",
        "Cipher" in node_names,
    ))
    checks.append((
        "Vita betrokken",
        "Vita" in node_names,
    ))
    checks.append((
        "Memex of Echo betrokken",
        "Memex" in node_names or "Echo" in node_names,
    ))

    passed = 0
    failed = 0
    for name, ok in checks:
        icon = "[OK]" if ok else "[FAIL]"
        if ok:
            passed += 1
        else:
            failed += 1
        print(f"  {icon} {name}")

    print(f"\n  Resultaat: {passed}/{passed + failed} geslaagd")
    return failed == 0


def test_hub_spoke_pipeline(brain: PrometheusBrain):
    """Test 6: Hub & Spoke routing pipeline."""
    print("\n" + "=" * 60)
    print("  TEST 6: Hub & Spoke Pipeline")
    print("=" * 60)

    checks = []

    # Test A: Casual -> Echo (geen Weaver)
    result = brain.route_task("Hallo, hoe gaat het?")
    checks.append((
        "Casual -> Echo",
        "Echo" in result.assigned_to,
    ))

    # Test B: Code -> Iolaax (+ Weaver synthese)
    result = brain.route_task(
        "Debug mijn Python code"
    )
    checks.append((
        "Code -> Iolaax",
        "Iolaax" in result.assigned_to,
    ))

    # Test C: Crypto -> Cipher
    result = brain.route_task(
        "Bitcoin blockchain analyse"
    )
    checks.append((
        "Crypto -> Cipher",
        "Cipher" in result.assigned_to,
    ))

    # Test D: Health -> Vita
    result = brain.route_task(
        "Analyseer mijn HRV data"
    )
    checks.append((
        "Health -> Vita",
        "Vita" in result.assigned_to,
    ))

    # Test E: Search -> Navigator
    result = brain.route_task(
        "Zoek op wat quantum computing is"
    )
    checks.append((
        "Search -> Navigator",
        "Navigator" in result.assigned_to,
    ))

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
    """Draai alle Chain of Command tests."""
    print()
    print("=" * 60)
    print("  FULL CHAIN TEST - Chain of Command Verificatie")
    print("=" * 60)
    print()

    start = time.time()
    brain = PrometheusBrain()

    results = []

    results.append(("Domain Detection", test_domain_detection(brain)))
    results.append(("Multi-Domain CoC", test_chain_multi_domain(brain)))
    results.append(("Single-Domain CoC", test_chain_single_domain(brain)))
    results.append(("No-Domain Fallback", test_chain_no_domain(brain)))
    results.append(("3-Domain CoC", test_chain_three_domains(brain)))
    results.append(("Hub & Spoke Pipeline", test_hub_spoke_pipeline(brain)))

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
    print(f"\n  {passed}/{total} tests geslaagd ({elapsed:.1f}s)")
    print("=" * 60)

    if passed < total:
        print("\n  SOMMIGE TESTS GEFAALD!")
        sys.exit(1)
    else:
        print("\n  ALLE TESTS GESLAAGD!")


if __name__ == "__main__":
    main()

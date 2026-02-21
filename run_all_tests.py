"""
Danny Toolkit — Master Test Runner
Draait alle 8 test suites in volgorde en geeft een totaaloverzicht.

Gebruik: python run_all_tests.py
"""

import io
import subprocess
import sys
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

PROJECT_ROOT = sys.path[0] or "."

TESTS = [
    {"naam": "NeuralBus",         "cmd": [sys.executable, f"{PROJECT_ROOT}/test_neural_bus.py"]},
    {"naam": "Proactive",         "cmd": [sys.executable, f"{PROJECT_ROOT}/test_proactive.py"]},
    {"naam": "Singularity",       "cmd": [sys.executable, f"{PROJECT_ROOT}/test_singularity.py"]},
    {"naam": "CLI",               "cmd": [sys.executable, f"{PROJECT_ROOT}/test_cli.py"]},
    {"naam": "Neural Hub",        "cmd": [sys.executable, f"{PROJECT_ROOT}/test_neural_hub.py"]},
    {"naam": "Swarm Engine",      "cmd": [sys.executable, f"{PROJECT_ROOT}/test_swarm_engine.py"]},
    {"naam": "Full Chain",        "cmd": [sys.executable, "-m", "danny_toolkit.test_full_chain"], "cwd": PROJECT_ROOT},
    {"naam": "Cosmic Awareness",  "cmd": [sys.executable, "-m", "danny_toolkit.test_cosmic_awareness"], "cwd": PROJECT_ROOT},
]

BREEDTE = 60


def run_test(test: dict) -> dict:
    naam = test["naam"]
    print(f"\n{'=' * BREEDTE}")
    print(f"  ▶ {naam}")
    print(f"{'=' * BREEDTE}")

    start = time.time()
    try:
        result = subprocess.run(
            test["cmd"],
            cwd=test.get("cwd", PROJECT_ROOT),
            capture_output=False,
            timeout=600,
        )
        duur = time.time() - start
        geslaagd = result.returncode == 0
    except subprocess.TimeoutExpired:
        duur = time.time() - start
        geslaagd = False
        print(f"  TIMEOUT na {duur:.0f}s")
    except Exception as e:
        duur = time.time() - start
        geslaagd = False
        print(f"  ERROR: {e}")

    status = "PASS" if geslaagd else "FAIL"
    print(f"\n  {'✅' if geslaagd else '❌'} {naam}: {status} ({duur:.1f}s)")

    return {"naam": naam, "geslaagd": geslaagd, "duur": duur}


def main():
    print(f"{'=' * BREEDTE}")
    print(f"  DANNY TOOLKIT — MASTER TEST RUNNER")
    print(f"  {len(TESTS)} test suites")
    print(f"{'=' * BREEDTE}")

    totaal_start = time.time()
    resultaten = []

    for test in TESTS:
        resultaten.append(run_test(test))

    totaal_duur = time.time() - totaal_start
    geslaagd = sum(1 for r in resultaten if r["geslaagd"])
    mislukt = len(resultaten) - geslaagd

    print(f"\n\n{'=' * BREEDTE}")
    print(f"  EINDRESULTAAT")
    print(f"{'=' * BREEDTE}")

    for r in resultaten:
        icon = "✅" if r["geslaagd"] else "❌"
        print(f"  {icon} {r['naam']:<25} {r['duur']:>6.1f}s")

    print(f"{'─' * BREEDTE}")
    print(f"  Totaal: {geslaagd}/{len(resultaten)} geslaagd ({totaal_duur:.1f}s)")

    if mislukt == 0:
        print(f"\n  🏆 ALLE TESTS GESLAAGD!")
    else:
        print(f"\n  ⚠️  {mislukt} suite(s) gefaald!")

    print(f"{'=' * BREEDTE}")

    sys.exit(0 if mislukt == 0 else 1)


if __name__ == "__main__":
    main()

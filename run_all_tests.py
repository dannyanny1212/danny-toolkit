"""
Danny Toolkit — Master Test Runner
Draait alle 26 test suites in volgorde en geeft een totaaloverzicht.

Gebruik: python run_all_tests.py
"""

import gc
import io
import os
import subprocess
import sys
import time
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

PROJECT_ROOT = sys.path[0] or "."

# Laad .env zodat API keys beschikbaar zijn in subprocess-env
try:
    from dotenv import load_dotenv
    load_dotenv(Path(PROJECT_ROOT) / ".env", override=True)
except ImportError:
    pass

# Locked interpreter — voorkomt CUDA 0xC0000005 door DLL mismatch
PYTHON = os.path.join(PROJECT_ROOT, "venv311", "Scripts", "python.exe")
if not os.path.isfile(PYTHON):
    PYTHON = sys.executable  # fallback

TESTS = [
    {"naam": "NeuralBus",         "cmd": [PYTHON, f"{PROJECT_ROOT}/test_neural_bus.py"]},
    {"naam": "Proactive",         "cmd": [PYTHON, f"{PROJECT_ROOT}/test_proactive.py"]},
    {"naam": "Singularity",       "cmd": [PYTHON, f"{PROJECT_ROOT}/test_singularity.py"]},
    {"naam": "CLI",               "cmd": [PYTHON, f"{PROJECT_ROOT}/test_cli.py"]},
    {"naam": "Neural Hub",        "cmd": [PYTHON, f"{PROJECT_ROOT}/test_neural_hub.py"]},
    {"naam": "Swarm Engine",      "cmd": [PYTHON, f"{PROJECT_ROOT}/test_swarm_engine.py"]},
    {"naam": "Full Chain",        "cmd": [PYTHON, "-m", "danny_toolkit.test_full_chain"], "cwd": PROJECT_ROOT},
    {"naam": "Cosmic Awareness",  "cmd": [PYTHON, "-m", "danny_toolkit.test_cosmic_awareness"], "cwd": PROJECT_ROOT},
    {"naam": "RAG Pipeline",      "cmd": [PYTHON, f"{PROJECT_ROOT}/test_rag_pipeline.py"]},
    {"naam": "Brain Integrations", "cmd": [PYTHON, f"{PROJECT_ROOT}/test_brain_integrations.py"]},
    {"naam": "Brain Modules",      "cmd": [PYTHON, f"{PROJECT_ROOT}/test_brain_modules.py"]},
    {"naam": "Synapse & Phantom",  "cmd": [PYTHON, f"{PROJECT_ROOT}/test_synapse.py"]},
    {"naam": "Phase 17 Stability", "cmd": [PYTHON, f"{PROJECT_ROOT}/test_phase17.py"]},
    {"naam": "SmartKeyManager",    "cmd": [PYTHON, f"{PROJECT_ROOT}/test_key_manager.py"]},
    {"naam": "Phase 19 Config",    "cmd": [PYTHON, f"{PROJECT_ROOT}/test_phase19.py"]},
    {"naam": "Phase 20 WebGUI",    "cmd": [PYTHON, f"{PROJECT_ROOT}/test_phase20.py"]},
    {"naam": "Phase 21 Sandbox",   "cmd": [PYTHON, f"{PROJECT_ROOT}/test_phase21.py"]},
    {"naam": "Phase 22 MemSafety", "cmd": [PYTHON, f"{PROJECT_ROOT}/test_phase22.py"]},
    {"naam": "Phase 23 Cache+Queue","cmd": [PYTHON, f"{PROJECT_ROOT}/test_phase23.py"]},
    {"naam": "Phase 24 Backup+Ret", "cmd": [PYTHON, f"{PROJECT_ROOT}/test_phase24.py"]},
    {"naam": "Phase 25 OpHarden",  "cmd": [PYTHON, f"{PROJECT_ROOT}/test_phase25.py"]},
    {"naam": "Phase 26 Metrics+Val","cmd": [PYTHON, f"{PROJECT_ROOT}/test_phase26.py"]},
    {"naam": "Phase 27 Resilience", "cmd": [PYTHON, f"{PROJECT_ROOT}/test_phase27.py"]},
    {"naam": "Phase 28 Observability", "cmd": [PYTHON, f"{PROJECT_ROOT}/test_phase28.py"]},
    {"naam": "Embeddings MRL",       "cmd": [PYTHON, f"{PROJECT_ROOT}/test_embeddings_mrl.py"]},
    {"naam": "Phase 29 VirtualTwin", "cmd": [PYTHON, f"{PROJECT_ROOT}/test_phase29.py"]},
]

BREEDTE = 60


def run_test(test: dict) -> dict:
    naam = test["naam"]
    print(f"\n{'=' * BREEDTE}")
    print(f"  ▶ {naam}")
    print(f"{'=' * BREEDTE}")

    # Schone env per subprocess — voorkomt CUDA VRAM-conflict (0xC0000005)
    # Tests draaien op CPU; productie gebruikt GPU
    clean_env = os.environ.copy()
    clean_env["PYTHONIOENCODING"] = "utf-8"
    clean_env["CUDA_VISIBLE_DEVICES"] = "0"
    clean_env["ANONYMIZED_TELEMETRY"] = "False"  # ChromaDB posthog crash preventie
    clean_env["DANNY_TEST_MODE"] = "1"  # Skip ChromaDB PersistentClient (Rust FFI crash in subprocess)

    start = time.time()
    try:
        proc = subprocess.Popen(
            test["cmd"],
            cwd=test.get("cwd", PROJECT_ROOT),
            env=clean_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
        for line in proc.stdout:
            print(line, end="", flush=True)
        proc.stdout.close()
        proc.wait(timeout=150)
        duur = time.time() - start
        geslaagd = proc.returncode == 0
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
        # VRAM purge tussen suites — voorkomt CUDA segfaults
        gc.collect()
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except ImportError:
            pass

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

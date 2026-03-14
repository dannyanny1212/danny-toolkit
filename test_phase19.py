"""
Phase 19 Tests — Model Config Centralization
=============================================
Verifieert dat alle brain modules hun model strings uit Config halen,
niet hardcoded.

6 tests, standalone uitvoerbaar: python test_phase19.py
"""
from __future__ import annotations

import io
import logging
import os
import re
import sys

logger = logging.getLogger(__name__)

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (ValueError, OSError):
    logger.debug("Invalid value encountered")

# Test-mode env
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "-1")
os.environ.setdefault("DANNY_TEST_MODE", "1")
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

passed = 0
failed = 0


def check(label: str, condition: bool) -> None:
    """Registreer een check resultaat."""
    global passed, failed
    if condition:
        passed += 1
        print(f"  OK  {label}")
    else:
        failed += 1
        print(f"  FAIL  {label}")


print("=" * 60)
print("  Phase 19: Model Config Centralization")
print("=" * 60)

# ── Test 1: Config has model attrs ──
print("\n[1] Config heeft LLM_MODEL en LLM_FALLBACK_MODEL")
from danny_toolkit.core.config import Config

check("Config.LLM_MODEL exists", hasattr(Config, "LLM_MODEL"))
check("Config.LLM_FALLBACK_MODEL exists", hasattr(Config, "LLM_FALLBACK_MODEL"))
check("LLM_MODEL is non-empty string", isinstance(Config.LLM_MODEL, str) and len(Config.LLM_MODEL) > 5)
check("LLM_FALLBACK_MODEL is non-empty string", isinstance(Config.LLM_FALLBACK_MODEL, str) and len(Config.LLM_FALLBACK_MODEL) > 5)

# ── Test 2: CentralBrain uses Config ──
print("\n[2] CentralBrain gebruikt Config modellen")
from danny_toolkit.brain.central_brain import CentralBrain

check("GROQ_MODEL_PRIMARY == Config.LLM_MODEL", CentralBrain.GROQ_MODEL_PRIMARY == Config.LLM_MODEL)
check("GROQ_MODEL_FALLBACK == Config.LLM_FALLBACK_MODEL", CentralBrain.GROQ_MODEL_FALLBACK == Config.LLM_FALLBACK_MODEL)

# ── Test 3: Tribunal uses Config ──
print("\n[3] Tribunal gebruikt Config modellen")
from danny_toolkit.brain.tribunal import Tribunal

t = Tribunal()
check("Tribunal.worker_model == Config.LLM_MODEL", t.worker_model == Config.LLM_MODEL)
check("Tribunal.auditor_model == Config.LLM_FALLBACK_MODEL", t.auditor_model == Config.LLM_FALLBACK_MODEL)

# ── Test 4: KeyManager MODEL_LIMITS keys match Config ──
print("\n[4] KeyManager MODEL_LIMITS sleutels matchen Config")
from danny_toolkit.core.key_manager import MODEL_LIMITS

check("Config.LLM_MODEL in MODEL_LIMITS", Config.LLM_MODEL in MODEL_LIMITS)
check("Config.LLM_FALLBACK_MODEL in MODEL_LIMITS", Config.LLM_FALLBACK_MODEL in MODEL_LIMITS)

# ── Test 5: OracleEye returns Config models ──
print("\n[5] OracleEye retourneert Config modellen")
from danny_toolkit.brain.oracle_eye import TheOracleEye

eye = TheOracleEye()
low_load = {"cpu": 10.0, "ram": 30.0, "queries_last_hour": 5}
high_load = {"cpu": 90.0, "ram": 80.0, "queries_last_hour": 100}

model_low = eye.suggest_model(low_load, forecast=[])
model_high = eye.suggest_model(high_load, forecast=[])

check("Low load → Config.LLM_MODEL", model_low == Config.LLM_MODEL)
check("High load → Config.LLM_FALLBACK_MODEL", model_high == Config.LLM_FALLBACK_MODEL)

# ── Test 6: Scan brain/ for zero remaining hardcoded model strings ──
print("\n[6] Geen hardcoded model strings in brain/")
brain_dir = os.path.join(os.path.dirname(__file__), "danny_toolkit", "brain")
hardcoded_files = []
pattern = re.compile(r'"meta-llama/llama-4-scout-17b-16e-instruct"|"qwen/qwen3-32b"')

# config_auditor.py bevat validation allowlists (geen model selectie)
ALLOWLIST_FILES = {"config_auditor.py"}
for fname in os.listdir(brain_dir):
    if fname.endswith(".py") and fname not in ALLOWLIST_FILES:
        fpath = os.path.join(brain_dir, fname)
        with open(fpath, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        if pattern.search(content):
            hardcoded_files.append(fname)

check("Zero hardcoded model strings in brain/", len(hardcoded_files) == 0)
if hardcoded_files:
    print(f"    Gevonden in: {', '.join(hardcoded_files)}")

# ── Resultaat ──
print(f"\n{'=' * 60}")
total = passed + failed
print(f"  Resultaat: {passed}/{total} checks geslaagd")
if failed == 0:
    print("  🏆 Phase 19: ALL CHECKS PASSED")
else:
    print(f"  ⚠️  {failed} check(s) gefaald!")
print(f"{'=' * 60}")

if __name__ == "__main__":
    sys.exit(0 if failed == 0 else 1)

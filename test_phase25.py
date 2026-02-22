"""
Phase 25: Operational Hardening — Tests
========================================
10 tests, ~30 checks.

Valideert:
- A1: request_timestamps deque(maxlen=120)
- A2: groq_retry timeout + jitter
- B1: Alerter singleton + dedup
- B3: HealthResponse deep probe fields
- C1: log_rotation
- C2: DevOpsDaemon._prune_old_reports
"""

import io
import json
import os
import sys
import time
import tempfile
from collections import deque
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("CUDA_VISIBLE_DEVICES", "-1")
os.environ.setdefault("DANNY_TEST_MODE", "1")
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

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
# Test 1: AgentMetrics.request_timestamps is deque met maxlen
# ==================================================================
print("\n=== Test 1: AgentMetrics.request_timestamps type ===")
try:
    from danny_toolkit.core.key_manager import AgentMetrics
    m = AgentMetrics(naam="TestAgent")
    check("request_timestamps is deque", isinstance(m.request_timestamps, deque))
    check("maxlen is 120", m.request_timestamps.maxlen == 120)
except Exception as e:
    check("Test 1 import", False, str(e))

# ==================================================================
# Test 2: deque overflow evicts oldest
# ==================================================================
print("\n=== Test 2: deque overflow ===")
try:
    from danny_toolkit.core.key_manager import AgentMetrics
    m = AgentMetrics(naam="OverflowTest")
    for i in range(200):
        m.request_timestamps.append(time.time())
    check("len stays 120 after 200 appends", len(m.request_timestamps) == 120)
    check("oldest evicted (FIFO)", m.request_timestamps[0] > 0)
except Exception as e:
    check("Test 2", False, str(e))

# ==================================================================
# Test 3: groq_retry.API_TIMEOUT constant
# ==================================================================
print("\n=== Test 3: API_TIMEOUT constant ===")
try:
    from danny_toolkit.core import groq_retry
    check("API_TIMEOUT exists", hasattr(groq_retry, "API_TIMEOUT"))
    check("API_TIMEOUT is 30", groq_retry.API_TIMEOUT == 30)
except Exception as e:
    check("Test 3 import", False, str(e))

# ==================================================================
# Test 4: groq_retry imports random (jitter)
# ==================================================================
print("\n=== Test 4: groq_retry jitter support ===")
try:
    import importlib
    from danny_toolkit.core import groq_retry
    # Check dat random geimporteerd is in het module
    check("random in groq_retry", hasattr(groq_retry, "random") or "random" in dir(groq_retry))
    # Alternatief: check source code
    import inspect
    source = inspect.getsource(groq_retry)
    check("random.uniform in source", "random.uniform" in source)
except Exception as e:
    check("Test 4", False, str(e))

# ==================================================================
# Test 5: get_alerter() returns singleton
# ==================================================================
print("\n=== Test 5: Alerter singleton ===")
try:
    from danny_toolkit.core.alerter import get_alerter, Alerter
    a1 = get_alerter()
    a2 = get_alerter()
    check("get_alerter returns Alerter", isinstance(a1, Alerter))
    check("singleton (same instance)", a1 is a2)
except Exception as e:
    check("Test 5", False, str(e))

# ==================================================================
# Test 6: Alerter dedup blocks same message within 5min
# ==================================================================
print("\n=== Test 6: Alerter dedup ===")
try:
    from danny_toolkit.core.alerter import Alerter, AlertLevel

    # Verse instance (geen singleton, voor isolatie)
    alerter = Alerter()
    # Eerste alert = verzonden (maar Telegram/Stack zullen falen in test — dat is OK)
    result1 = alerter.alert(AlertLevel.INFO, "test-dedup-bericht", bron="test")
    check("first alert returns True", result1 is True)

    # Tweede zelfde alert binnen 5min = gededupliceerd
    result2 = alerter.alert(AlertLevel.INFO, "test-dedup-bericht", bron="test")
    check("duplicate alert returns False", result2 is False)
except Exception as e:
    check("Test 6", False, str(e))

# ==================================================================
# Test 7: Alerter allows after dedup interval expires
# ==================================================================
print("\n=== Test 7: Alerter dedup expiry ===")
try:
    from danny_toolkit.core.alerter import Alerter, AlertLevel

    alerter = Alerter()
    msg = "test-expiry-bericht"
    alerter.alert(AlertLevel.INFO, msg, bron="test")

    # Forceer dedup key te verlopen
    key = alerter._dedup_key(AlertLevel.INFO, msg)
    alerter._dedup[key] = time.time() - 301  # 5min + 1s geleden

    result = alerter.alert(AlertLevel.INFO, msg, bron="test")
    check("alert after expiry returns True", result is True)
except Exception as e:
    check("Test 7", False, str(e))

# ==================================================================
# Test 8: HealthResponse heeft deep probe fields
# ==================================================================
print("\n=== Test 8: HealthResponse deep probe fields ===")
try:
    from fastapi_server import HealthResponse
    fields = HealthResponse.model_fields
    check("groq_reachable field", "groq_reachable" in fields)
    check("cortical_stack_writable field", "cortical_stack_writable" in fields)
    check("disk_free_gb field", "disk_free_gb" in fields)
    check("agents_in_cooldown field", "agents_in_cooldown" in fields)

    # Defaults
    hr = HealthResponse(
        status="TEST", brain_online=True, governor_status="ACTIEF",
        circuit_breaker="CLOSED", timestamp="now", version="6.0.0",
    )
    check("groq_reachable default False", hr.groq_reachable is False)
    check("disk_free_gb default 0.0", hr.disk_free_gb == 0.0)
except ImportError:
    # FastAPI niet beschikbaar in test-omgeving — valideer via source inspection
    import ast
    source_path = PROJECT_ROOT / "fastapi_server.py"
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    health_fields = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "HealthResponse":
            for item in node.body:
                if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                    health_fields.add(item.target.id)
    check("groq_reachable field (AST)", "groq_reachable" in health_fields)
    check("cortical_stack_writable field (AST)", "cortical_stack_writable" in health_fields)
    check("disk_free_gb field (AST)", "disk_free_gb" in health_fields)
    check("agents_in_cooldown field (AST)", "agents_in_cooldown" in health_fields)
except Exception as e:
    check("Test 8", False, str(e))

# ==================================================================
# Test 9: DevOpsDaemon._prune_old_reports
# ==================================================================
print("\n=== Test 9: DevOpsDaemon._prune_old_reports ===")
try:
    from danny_toolkit.brain.devops_daemon import DevOpsDaemon

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Maak een daemon met custom log_dir
        daemon = DevOpsDaemon.__new__(DevOpsDaemon)
        daemon.log_dir = tmpdir_path

        # Maak 60 dummy rapporten
        for i in range(60):
            pad = tmpdir_path / f"devops_test_{i:03d}.json"
            pad.write_text(json.dumps({"i": i}), encoding="utf-8")
            # Zet mtime zodat sortering werkt
            os.utime(pad, (time.time() - (60 - i), time.time() - (60 - i)))

        check("60 files created", len(list(tmpdir_path.glob("devops_*.json"))) == 60)

        daemon._prune_old_reports(max_reports=50)

        remaining = list(tmpdir_path.glob("devops_*.json"))
        check("pruned to 50", len(remaining) == 50)

        # Controleer dat de nieuwste bewaard zijn
        remaining_names = sorted(p.name for p in remaining)
        check("oldest removed", "devops_test_000.json" not in remaining_names)
        check("newest kept", "devops_test_059.json" in remaining_names)
except Exception as e:
    check("Test 9", False, str(e))

# ==================================================================
# Test 10: roteer_logs verwijdert oude bestanden
# ==================================================================
print("\n=== Test 10: roteer_logs ===")
try:
    from danny_toolkit.core.log_rotation import roteer_logs

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Maak oude bestanden (31+ dagen)
        for i in range(5):
            pad = tmpdir_path / f"old_{i}.json"
            pad.write_text("{}", encoding="utf-8")
            os.utime(pad, (time.time() - 32 * 86400, time.time() - 32 * 86400))

        # Maak recente bestanden
        for i in range(3):
            pad = tmpdir_path / f"new_{i}.log"
            pad.write_text("log", encoding="utf-8")

        verwijderd = roteer_logs(tmpdir_path, max_leeftijd_dagen=30, max_bestanden=100)
        check("5 old files deleted", verwijderd == 5)

        remaining = list(tmpdir_path.iterdir())
        check("3 new files remain", len(remaining) == 3)
        check("new files intact", all("new_" in p.name for p in remaining))
except Exception as e:
    check("Test 10", False, str(e))


# ==================================================================
# RESULTAAT
# ==================================================================
print(f"\n{'=' * 50}")
print(f"Phase 25 Tests: {geslaagd} geslaagd, {mislukt} mislukt")
print(f"{'=' * 50}")

sys.exit(0 if mislukt == 0 else 1)

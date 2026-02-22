"""
Phase 28 Tests — Observability Hardening.

10 tests, ~30 checks:
  1-3. Exception hygiene (no bare except Exception: pass)
  4-5. CorticalStack DB metrics
  6-8. Alerter history + stats
  9-10. Telegram bot new commands
"""

import os
import re
import sys
import tempfile
import time

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

BARE_EXCEPT_RE = re.compile(
    r"except\s+Exception\s*:\s*\n\s*pass\b"
)


def check(beschrijving: str, conditie: bool):
    global passed, failed
    if conditie:
        passed += 1
        print(f"  OK  {beschrijving}")
    else:
        failed += 1
        print(f"  FAIL  {beschrijving}")


def _count_bare_excepts(filepath: str) -> int:
    """Tel bare `except Exception:\\n    pass` patronen in een bestand."""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    return len(BARE_EXCEPT_RE.findall(content))


# ─── Test 1: fastapi_server.py no bare except:pass ───

def test_1_fastapi_no_bare_except():
    print("\n[Test 1] fastapi_server.py — no bare except:pass")
    path = os.path.join(PROJECT_ROOT, "fastapi_server.py")
    check("fastapi_server.py exists", os.path.isfile(path))
    count = _count_bare_excepts(path)
    check(f"bare except:pass count == 0 (found {count})", count == 0)


# ─── Test 2: daemon_heartbeat.py no bare except:pass ───

def test_2_daemon_no_bare_except():
    print("\n[Test 2] daemon_heartbeat.py — no bare except:pass")
    path = os.path.join(PROJECT_ROOT, "daemon_heartbeat.py")
    check("daemon_heartbeat.py exists", os.path.isfile(path))
    count = _count_bare_excepts(path)
    check(f"bare except:pass count == 0 (found {count})", count == 0)


# ─── Test 3: brain modules no bare except:pass ───

def test_3_brain_modules_no_bare_except():
    print("\n[Test 3] brain modules — no bare except:pass")
    modules = [
        os.path.join(PROJECT_ROOT, "danny_toolkit", "brain", "dreamer.py"),
        os.path.join(PROJECT_ROOT, "danny_toolkit", "brain", "phantom.py"),
        os.path.join(PROJECT_ROOT, "danny_toolkit", "brain", "cortical_stack.py"),
        os.path.join(PROJECT_ROOT, "danny_toolkit", "core", "log_rotation.py"),
    ]
    for path in modules:
        naam = os.path.basename(path)
        count = _count_bare_excepts(path)
        check(f"{naam} bare except:pass == 0 (found {count})", count == 0)


# ─── Test 4: CorticalStack get_db_metrics() ───

def test_4_cortical_db_metrics():
    print("\n[Test 4] CorticalStack get_db_metrics()")
    from danny_toolkit.brain.cortical_stack import CorticalStack

    # Gebruik temp DB
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_stack.db")
        stack = CorticalStack(db_path=db_path)

        check("get_db_metrics is callable", callable(getattr(stack, "get_db_metrics", None)))

        metrics = stack.get_db_metrics()
        check("get_db_metrics returns dict", isinstance(metrics, dict))

        expected_keys = {
            "db_size_bytes", "db_size_mb", "wal_size_bytes",
            "pending_writes", "batch_size", "last_flush_ago_s",
        }
        missing = expected_keys - set(metrics.keys())
        check(f"all 6 keys present (missing: {missing or 'none'})", len(missing) == 0)

        stack.close()


# ─── Test 5: CorticalStack get_stats() includes DB metrics ───

def test_5_cortical_stats_merged():
    print("\n[Test 5] CorticalStack get_stats() includes DB metrics")
    from danny_toolkit.brain.cortical_stack import CorticalStack

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_stack.db")
        stack = CorticalStack(db_path=db_path)

        stats = stack.get_stats()
        check("db_size_mb in get_stats()", "db_size_mb" in stats)
        check("episodic_events in get_stats()", "episodic_events" in stats)
        check("pending_writes in get_stats()", "pending_writes" in stats)

        stack.close()


# ─── Test 6: Alerter get_history() ───

def test_6_alerter_history():
    print("\n[Test 6] Alerter get_history()")
    from danny_toolkit.core.alerter import Alerter, AlertLevel

    alerter = Alerter()

    # Fire 3 alerts
    alerter.alert(AlertLevel.INFO, "test alert 1", bron="test")
    alerter.alert(AlertLevel.WAARSCHUWING, "test alert 2", bron="test")
    alerter.alert(AlertLevel.KRITIEK, "test alert 3", bron="test")

    history = alerter.get_history()
    check(f"history length >= 3 (got {len(history)})", len(history) >= 3)

    # Check keys in first item
    if history:
        item = history[0]
        has_keys = all(k in item for k in ("timestamp", "niveau", "bericht", "bron"))
        check("history items have required keys", has_keys)
    else:
        check("history items have required keys", False)

    # Filter by niveau
    filtered = alerter.get_history(niveau=AlertLevel.INFO)
    check(f"filtered history (info) has items", len(filtered) >= 1)

    # Nieuwste eerst
    if len(history) >= 2:
        check("history is newest-first", history[0]["timestamp"] >= history[-1]["timestamp"])
    else:
        check("history is newest-first", True)


# ─── Test 7: Alerter get_alert_stats() ───

def test_7_alerter_stats():
    print("\n[Test 7] Alerter get_alert_stats()")
    from danny_toolkit.core.alerter import Alerter, AlertLevel

    alerter = Alerter()
    alerter.alert(AlertLevel.INFO, "stats test a", bron="test")
    alerter.alert(AlertLevel.INFO, "stats test b", bron="test")
    alerter.alert(AlertLevel.KRITIEK, "stats test c", bron="test")

    stats = alerter.get_alert_stats()
    check(f"info count >= 2 (got {stats.get('info', 0)})", stats.get("info", 0) >= 2)
    check(f"kritiek count >= 1 (got {stats.get('kritiek', 0)})", stats.get("kritiek", 0) >= 1)
    check("mislukt key exists", "mislukt" in stats)


# ─── Test 8: Alerter clear_history() ───

def test_8_alerter_clear():
    print("\n[Test 8] Alerter clear_history()")
    from danny_toolkit.core.alerter import Alerter, AlertLevel

    alerter = Alerter()
    alerter.alert(AlertLevel.INFO, "clear test", bron="test")
    check("history not empty before clear", len(alerter.get_history()) > 0)

    alerter.clear_history()
    check("history empty after clear", len(alerter.get_history()) == 0)

    stats = alerter.get_alert_stats()
    check("stats reset after clear", stats.get("info", 0) == 0)


# ─── Test 9: Telegram bot has new handlers ───

def test_9_telegram_handlers():
    print("\n[Test 9] Telegram bot — /health, /metrics, /logs handlers")
    path = os.path.join(PROJECT_ROOT, "telegram_bot.py")
    with open(path, "r", encoding="utf-8") as f:
        source = f.read()

    check("cmd_health function defined", "async def cmd_health(" in source)
    check("cmd_metrics function defined", "async def cmd_metrics(" in source)
    check("cmd_logs function defined", "async def cmd_logs(" in source)


# ─── Test 10: Telegram /start help text ───

def test_10_telegram_help_text():
    print("\n[Test 10] Telegram /start help text — new commands listed")
    path = os.path.join(PROJECT_ROOT, "telegram_bot.py")
    with open(path, "r", encoding="utf-8") as f:
        source = f.read()

    check("/health in help text", "/health" in source)
    check("/metrics in help text", "/metrics" in source)
    check("/logs" in source and "[N]" in source, True)


# ─── Runner ───

def main():
    global passed, failed

    print("=" * 60)
    print("  PHASE 28 TESTS — Observability Hardening")
    print("=" * 60)

    test_1_fastapi_no_bare_except()
    test_2_daemon_no_bare_except()
    test_3_brain_modules_no_bare_except()
    test_4_cortical_db_metrics()
    test_5_cortical_stats_merged()
    test_6_alerter_history()
    test_7_alerter_stats()
    test_8_alerter_clear()
    test_9_telegram_handlers()
    test_10_telegram_help_text()

    total = passed + failed
    print(f"\n{'=' * 60}")
    print(f"  Resultaat: {passed}/{total} checks geslaagd")

    if failed == 0:
        print("  ALLE TESTS GESLAAGD")
    else:
        print(f"  {failed} check(s) gefaald!")

    print(f"{'=' * 60}")
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()

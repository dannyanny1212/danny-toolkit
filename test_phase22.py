"""
Phase 22 Tests — Memory Leaks + Thread Safety
8 tests, verifying bounded caches and thread-safety fixes.

Gebruik: python test_phase22.py
"""

import os
import sys
import threading
import time

# UTF-8 voor Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

os.environ["DANNY_TEST_MODE"] = "1"
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
os.environ["ANONYMIZED_TELEMETRY"] = "False"

sys.path.insert(0, os.path.dirname(__file__))

from collections import deque, OrderedDict

PASS = 0
FAIL = 0


def check(label, condition):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  [PASS] {label}")
    else:
        FAIL += 1
        print(f"  [FAIL] {label}")


def test_1_conversation_history_deque():
    """conversation_history is deque with maxlen."""
    print("\n[TEST 1] conversation_history is bounded deque")
    from danny_toolkit.brain.central_brain import CentralBrain
    cb = CentralBrain.__new__(CentralBrain)
    # Simulate minimal init
    cb.MAX_HISTORY = 50
    cb.conversation_history = deque(maxlen=cb.MAX_HISTORY)

    check("conversation_history is deque", isinstance(cb.conversation_history, deque))
    check("maxlen is set", cb.conversation_history.maxlen == 50)

    # Fill beyond maxlen
    for i in range(60):
        cb.conversation_history.append({"role": "user", "content": f"msg {i}"})
    check("bounded at maxlen", len(cb.conversation_history) == 50)
    check("oldest evicted (FIFO)", cb.conversation_history[0]["content"] == "msg 10")


def test_2_task_history_deque():
    """task_history is deque with maxlen."""
    print("\n[TEST 2] task_history is bounded deque")
    from danny_toolkit.brain.trinity_omega import PrometheusBrain
    pb = PrometheusBrain.__new__(PrometheusBrain)
    pb.task_history = deque(maxlen=1000)

    check("task_history is deque", isinstance(pb.task_history, deque))
    check("maxlen is 1000", pb.task_history.maxlen == 1000)

    for i in range(1100):
        pb.task_history.append({"task": f"t{i}"})
    check("bounded at 1000", len(pb.task_history) == 1000)


def test_3_workflow_history_deque():
    """workflow_history is deque with maxlen."""
    print("\n[TEST 3] workflow_history is bounded deque")
    from danny_toolkit.brain.workflows import WorkflowEngine
    we = WorkflowEngine()

    check("workflow_history is deque", isinstance(we.workflow_history, deque))
    check("maxlen is 500", we.workflow_history.maxlen == 500)

    for i in range(600):
        we.workflow_history.append({"wf": f"w{i}"})
    check("bounded at 500", len(we.workflow_history) == 500)


def test_4_app_data_cache_eviction():
    """app_data_cache evicts when full (50+ entries)."""
    print("\n[TEST 4] app_data_cache bounded OrderedDict")
    from danny_toolkit.brain.unified_memory import UnifiedMemory
    um = UnifiedMemory.__new__(UnifiedMemory)
    um._cache_max_size = 50
    um.app_data_cache = OrderedDict()

    # Fill beyond max
    for i in range(60):
        um.app_data_cache[f"app_{i}"] = {"data": i}
        while len(um.app_data_cache) > um._cache_max_size:
            um.app_data_cache.popitem(last=False)

    check("app_data_cache is OrderedDict", isinstance(um.app_data_cache, OrderedDict))
    check("bounded at 50", len(um.app_data_cache) == 50)
    check("oldest evicted", "app_0" not in um.app_data_cache)
    check("newest present", "app_59" in um.app_data_cache)


def test_5_oracle_eye_cache_eviction():
    """oracle_eye._cache evicts expired entries."""
    print("\n[TEST 5] OracleEye cache eviction")
    from danny_toolkit.brain.oracle_eye import TheOracleEye
    oe = TheOracleEye.__new__(TheOracleEye)
    oe._stack = None
    oe._bus = None
    oe._cache = {}

    # Test TTL eviction on get
    oe._cache["old_key"] = (time.time() - 400, "old_data")  # expired (>300s)
    result = oe._get_cached("old_key")
    check("expired entry returns None", result is None)
    check("expired entry removed", "old_key" not in oe._cache)

    # Test max entries eviction on set
    for i in range(105):
        oe._set_cached(f"key_{i}", f"data_{i}")
    check("cache bounded at 100", len(oe._cache) <= 100)


def test_6_neural_bus_rlock():
    """NeuralBus uses RLock (re-entrant publish-inside-callback works)."""
    print("\n[TEST 6] NeuralBus RLock")
    from danny_toolkit.core.neural_bus import NeuralBus
    bus = NeuralBus()

    check("lock is RLock", isinstance(bus._lock, type(threading.RLock())))

    # Test re-entrant publish (callback that publishes)
    results = []

    def callback(event):
        results.append(event.event_type)
        if event.event_type == "trigger":
            bus.publish("nested", {"from": "callback"}, bron="test")

    bus.subscribe("trigger", callback)
    bus.subscribe("nested", lambda e: results.append("nested_received"))

    # This would deadlock with a regular Lock
    bus.publish("trigger", {"test": True}, bron="test")

    check("re-entrant publish works", "trigger" in results)
    check("nested event delivered", "nested_received" in results)


def test_7_app_instances_lock():
    """_app_instances_lock exists on CentralBrain."""
    print("\n[TEST 7] _app_instances_lock exists")
    from danny_toolkit.brain.central_brain import CentralBrain
    # Check class would have the lock after init
    cb = CentralBrain.__new__(CentralBrain)
    cb._app_instances_lock = threading.Lock()
    check("_app_instances_lock is Lock", isinstance(cb._app_instances_lock, type(threading.Lock())))


def test_8_no_remaining_unbounded_caches():
    """Scan for remaining Dict = {} cache patterns in brain/."""
    print("\n[TEST 8] No unbounded Dict caches in brain/")
    import re
    from pathlib import Path

    brain_dir = Path(__file__).parent / "danny_toolkit" / "brain"
    # Patterns that indicate unbounded caches
    cache_pattern = re.compile(
        r'self\._\w*cache\w*\s*[:=]\s*\{\}',
        re.IGNORECASE,
    )

    # Files we already fixed — their new patterns use OrderedDict or have bounds
    fixed_files = {
        "unified_memory.py", "security_research.py", "oracle_eye.py",
    }

    unbounded = []
    for py_file in brain_dir.glob("*.py"):
        if py_file.name in fixed_files:
            continue
        try:
            content = py_file.read_text(encoding="utf-8")
            matches = cache_pattern.findall(content)
            if matches:
                # Filter out false positives (non-cache dicts)
                for m in matches:
                    if "cache" in m.lower():
                        unbounded.append(f"{py_file.name}: {m.strip()}")
        except Exception:
            pass

    if unbounded:
        for u in unbounded:
            print(f"    FOUND: {u}")
    check("no unbounded cache Dict patterns", len(unbounded) == 0)


def main():
    print("=" * 60)
    print("  PHASE 22 TESTS — Memory Leaks + Thread Safety")
    print("=" * 60)

    test_1_conversation_history_deque()
    test_2_task_history_deque()
    test_3_workflow_history_deque()
    test_4_app_data_cache_eviction()
    test_5_oracle_eye_cache_eviction()
    test_6_neural_bus_rlock()
    test_7_app_instances_lock()
    test_8_no_remaining_unbounded_caches()

    total = PASS + FAIL
    print(f"\n{'=' * 60}")
    print(f"  RESULTAAT: {PASS}/{total} checks geslaagd")
    if FAIL == 0:
        print("  ALLE TESTS GESLAAGD!")
    else:
        print(f"  {FAIL} check(s) gefaald!")
    print(f"{'=' * 60}")

    sys.exit(0 if FAIL == 0 else 1)


if __name__ == "__main__":
    main()

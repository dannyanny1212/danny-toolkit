"""
Phase 23 Tests — LLM Response Cache + Rate Limit Queuing
8 tests verifying cache and queue behavior.

Gebruik: python test_phase23.py
"""

import asyncio
import os
import sys
import time

# UTF-8 voor Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

os.environ["DANNY_TEST_MODE"] = "1"
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
os.environ["ANONYMIZED_TELEMETRY"] = "False"

sys.path.insert(0, os.path.dirname(__file__))

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


def test_1_cache_store_retrieve():
    """ResponseCache stores and retrieves by hash."""
    print("\n[TEST 1] ResponseCache store and retrieve")
    from danny_toolkit.core.response_cache import ResponseCache

    cache = ResponseCache()
    model = "test-model"
    messages = [{"role": "user", "content": "hello"}]
    temperature = 0.3

    # Store
    cache.put(model, messages, temperature, "test response")

    # Retrieve
    result = cache.get(model, messages, temperature)
    check("cached response returned", result == "test response")

    # Different messages = miss
    result2 = cache.get(model, [{"role": "user", "content": "bye"}], temperature)
    check("different messages = miss", result2 is None)


def test_2_cache_ttl_expiration():
    """ResponseCache TTL expiration works."""
    print("\n[TEST 2] ResponseCache TTL expiration")
    from danny_toolkit.core.response_cache import ResponseCache

    cache = ResponseCache()
    model = "test-model"
    messages = [{"role": "user", "content": "ttl test"}]

    # Store with 1-second TTL
    cache.put(model, messages, 0.1, "short-lived", ttl=1)

    # Should be available immediately
    result = cache.get(model, messages, 0.1)
    check("available before TTL", result == "short-lived")

    # Wait for expiration
    time.sleep(1.1)
    result = cache.get(model, messages, 0.1)
    check("expired after TTL", result is None)


def test_3_cache_eviction():
    """ResponseCache evicts oldest when full (>200)."""
    print("\n[TEST 3] ResponseCache eviction at capacity")
    from danny_toolkit.core.response_cache import ResponseCache

    cache = ResponseCache()
    cache._MAX_ENTRIES = 10  # Smaller for testing

    # Fill beyond capacity
    for i in range(15):
        cache.put("model", [{"role": "user", "content": f"msg{i}"}], 0.1, f"resp{i}")

    stats = cache.stats()
    check("bounded at max entries", stats["entries"] <= 10)

    # Oldest should be evicted
    oldest = cache.get("model", [{"role": "user", "content": "msg0"}], 0.1)
    check("oldest evicted", oldest is None)

    # Newest should still be present
    newest = cache.get("model", [{"role": "user", "content": "msg14"}], 0.1)
    check("newest present", newest == "resp14")


def test_4_cache_skip_high_temperature():
    """ResponseCache skips caching for high temperature (>0.4)."""
    print("\n[TEST 4] ResponseCache skips high temperature")
    from danny_toolkit.core.response_cache import ResponseCache

    cache = ResponseCache()

    # High temperature should not be cached
    cache.put("model", [{"role": "user", "content": "creative"}], 0.9, "random output")
    result = cache.get("model", [{"role": "user", "content": "creative"}], 0.9)
    check("high temp not cached", result is None)

    # Low temperature should be cached
    cache.put("model", [{"role": "user", "content": "deterministic"}], 0.2, "stable output")
    result = cache.get("model", [{"role": "user", "content": "deterministic"}], 0.2)
    check("low temp cached", result == "stable output")


def test_5_async_enqueue_pass():
    """async_enqueue() returns True when not throttled."""
    print("\n[TEST 5] async_enqueue passes when not throttled")
    from danny_toolkit.core.key_manager import SmartKeyManager

    km = SmartKeyManager.__new__(SmartKeyManager)
    km._initialized = False
    km.__init__()
    km.reset_counters()

    async def run():
        mag, reden = await km.async_enqueue("TestAgent", None)
        return mag, reden

    mag, reden = asyncio.run(run())
    check("returns True", mag is True)
    check("reason is OK", reden == "OK")


def test_6_async_enqueue_waits():
    """async_enqueue() waits and retries when throttled."""
    print("\n[TEST 6] async_enqueue waits on throttle")
    from danny_toolkit.core.key_manager import SmartKeyManager

    km = SmartKeyManager.__new__(SmartKeyManager)
    km._initialized = False
    km.__init__()
    km.reset_counters()

    # Force agent into cooldown for 2 seconds
    agent = km._get_agent("SlowAgent")
    agent.cooldown_tot = time.time() + 2.0

    async def run():
        start = time.time()
        mag, reden = await km.async_enqueue("SlowAgent", None)
        elapsed = time.time() - start
        return mag, reden, elapsed

    mag, reden, elapsed = asyncio.run(run())
    check("returns True after wait", mag is True)
    check("waited ~2 seconds", 1.5 <= elapsed <= 4.0)


def test_7_async_enqueue_timeout():
    """async_enqueue() times out after MAX_QUEUE_WAIT."""
    print("\n[TEST 7] async_enqueue timeout")
    from danny_toolkit.core.key_manager import SmartKeyManager

    km = SmartKeyManager.__new__(SmartKeyManager)
    km._initialized = False
    km.__init__()
    km.reset_counters()
    km.MAX_QUEUE_WAIT = 2.0  # Short for testing

    # Force agent into long cooldown
    agent = km._get_agent("BlockedAgent")
    agent.cooldown_tot = time.time() + 60.0  # Way beyond queue wait

    async def run():
        start = time.time()
        mag, reden = await km.async_enqueue("BlockedAgent", None)
        elapsed = time.time() - start
        return mag, reden, elapsed

    mag, reden, elapsed = asyncio.run(run())
    check("returns False on timeout", mag is False)
    check("reason mentions timeout", "timeout" in reden.lower())
    check("elapsed ~2 seconds", 1.5 <= elapsed <= 4.0)


def test_8_groq_retry_cache_integration():
    """groq_call_async() checks cache before API call."""
    print("\n[TEST 8] groq_retry cache integration")
    # Verify the import chain works
    try:
        from danny_toolkit.core.groq_retry import HAS_RESPONSE_CACHE
        check("HAS_RESPONSE_CACHE importable", True)
        check("response cache flag is True", HAS_RESPONSE_CACHE is True)
    except ImportError as e:
        check(f"import failed: {e}", False)
        check("response cache flag", False)

    # Verify the function signature accepts the expected parameters
    import inspect
    from danny_toolkit.core.groq_retry import groq_call_async
    sig = inspect.signature(groq_call_async)
    params = list(sig.parameters.keys())
    check("groq_call_async has temperature param", "temperature" in params)


def main():
    print("=" * 60)
    print("  PHASE 23 TESTS — LLM Response Cache + Rate Limit Queue")
    print("=" * 60)

    test_1_cache_store_retrieve()
    test_2_cache_ttl_expiration()
    test_3_cache_eviction()
    test_4_cache_skip_high_temperature()
    test_5_async_enqueue_pass()
    test_6_async_enqueue_waits()
    test_7_async_enqueue_timeout()
    test_8_groq_retry_cache_integration()

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

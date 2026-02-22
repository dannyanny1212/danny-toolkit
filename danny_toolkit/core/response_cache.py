"""
ResponseCache — Hash-based LLM response cache with TTL.

Caches deterministic (temperature <= 0.4) API responses to avoid
redundant calls. Bounded at 200 entries with FIFO eviction.

Singleton via get_response_cache(). Thread-safe.

Gebruik:
    from danny_toolkit.core.response_cache import get_response_cache

    cache = get_response_cache()
    hit = cache.get(model, messages, temperature)
    if hit:
        return hit
    # ... API call ...
    cache.put(model, messages, temperature, response)
"""

import hashlib
import json
import logging
import threading
import time
from collections import OrderedDict
from typing import Optional

logger = logging.getLogger(__name__)


class ResponseCache:
    """Hash-based LLM response cache with TTL."""

    _MAX_ENTRIES = 200
    _DEFAULT_TTL = 300  # 5 minutes
    _MAX_TEMPERATURE = 0.4  # Only cache deterministic-ish responses

    def __init__(self):
        self._cache: OrderedDict[str, tuple] = OrderedDict()  # hash -> (timestamp, ttl, response)
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

    def _make_key(self, model: str, messages: list, temperature: float) -> str:
        """Deterministic hash from model + messages + temperature."""
        raw = json.dumps(
            {"m": model, "msgs": messages, "t": temperature},
            sort_keys=True,
            ensure_ascii=False,
        )
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def get(self, model: str, messages: list, temperature: float) -> Optional[str]:
        """Look up cached response.

        Returns cached response string or None on miss/expiry.
        """
        if temperature > self._MAX_TEMPERATURE:
            return None

        key = self._make_key(model, messages, temperature)

        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                self._misses += 1
                return None

            ts, ttl, response = entry
            if time.time() - ts > ttl:
                # Expired
                del self._cache[key]
                self._misses += 1
                return None

            # Move to end (LRU refresh)
            self._cache.move_to_end(key)
            self._hits += 1
            return response

    def put(
        self,
        model: str,
        messages: list,
        temperature: float,
        response: str,
        ttl: int = None,
    ):
        """Store a response in the cache.

        Only caches when temperature <= _MAX_TEMPERATURE.
        """
        if temperature > self._MAX_TEMPERATURE:
            return
        if not response:
            return

        key = self._make_key(model, messages, temperature)
        effective_ttl = ttl if ttl is not None else self._DEFAULT_TTL

        with self._lock:
            self._cache[key] = (time.time(), effective_ttl, response)
            self._cache.move_to_end(key)

            # FIFO eviction when full
            while len(self._cache) > self._MAX_ENTRIES:
                self._cache.popitem(last=False)

    def stats(self) -> dict:
        """Return cache statistics."""
        with self._lock:
            return {
                "entries": len(self._cache),
                "max_entries": self._MAX_ENTRIES,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": (
                    round(self._hits / max(self._hits + self._misses, 1) * 100, 1)
                ),
            }

    def clear(self):
        """Clear all cached entries."""
        with self._lock:
            self._cache.clear()


# -- Singleton --

_cache_instance: Optional[ResponseCache] = None
_cache_lock = threading.Lock()


def get_response_cache() -> ResponseCache:
    """Singleton accessor voor ResponseCache."""
    global _cache_instance
    if _cache_instance is None:
        with _cache_lock:
            if _cache_instance is None:
                _cache_instance = ResponseCache()
    return _cache_instance

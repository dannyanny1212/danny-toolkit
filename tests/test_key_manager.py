"""Tests voor SmartKeyManager — Multi-Core Groq engine.

Test: singleton, key discovery, throttle, blacklist,
round-robin, priority cooldown, parallel_complete.
"""
from __future__ import annotations

import os
import sys
import time
import threading
import asyncio
from unittest.mock import patch

import pytest

# Ensure project root on path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


# ─── Fixtures ───

FAKE_KEYS = {
    "GROQ_API_KEY": "gsk_test_primary_key_00000000000000000000",
    "GROQ_API_KEY_USER": "gsk_test_user_key_000000000000000000000",
    "GROQ_API_KEY_VERIFY": "gsk_test_verify_key_0000000000000000000",
    "GROQ_API_KEY_RESEARCH": "gsk_test_research_key_00000000000000000",
    "GROQ_API_KEY_WALKER": "gsk_test_walker_key_000000000000000000",
    "GROQ_API_KEY_FORGE": "gsk_test_forge_key_00000000000000000000",
    "GROQ_API_KEY_OVERNIGHT": "gsk_test_overnight_key_0000000000000000",
    "GROQ_API_KEY_KNOWLEDGE": "gsk_test_knowledge_key_0000000000000000",
    "GROQ_API_KEY_RESERVE_1": "gsk_test_reserve1_key_00000000000000000",
    "GROQ_API_KEY_RESERVE_2": "gsk_test_reserve2_key_00000000000000000",
    "GROQ_API_KEY_RESERVE_3": "gsk_test_reserve3_key_00000000000000000",
}


@pytest.fixture(autouse=True)
def _reset_singleton():
    """Reset SmartKeyManager singleton voor elke test."""
    import danny_toolkit.core.key_manager as km_mod
    km_mod._manager_instance = None
    km_mod._manager_lock = threading.Lock()
    # Also reset class-level singleton
    km_mod.SmartKeyManager._instance = None
    yield
    km_mod._manager_instance = None
    km_mod.SmartKeyManager._instance = None


@pytest.fixture
def km():
    """SmartKeyManager met fake keys."""
    with patch.dict(os.environ, FAKE_KEYS, clear=False):
        from danny_toolkit.core.key_manager import SmartKeyManager
        return SmartKeyManager()


# ─── Test: Singleton ───

def test_singleton_returns_same_instance():
    """SmartKeyManager is een singleton."""
    with patch.dict(os.environ, FAKE_KEYS, clear=False):
        from danny_toolkit.core.key_manager import SmartKeyManager
        a = SmartKeyManager()
        b = SmartKeyManager()
        assert a is b


def test_singleton_thread_safe():
    """Singleton is thread-safe — parallelle threads krijgen dezelfde instantie."""
    instances = []

    def _create():
        with patch.dict(os.environ, FAKE_KEYS, clear=False):
            from danny_toolkit.core.key_manager import SmartKeyManager
            instances.append(SmartKeyManager())

    threads = [threading.Thread(target=_create) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(set(id(i) for i in instances)) == 1


# ─── Test: Key Discovery ───

def test_discovers_all_keys(km):
    """Vindt alle 11 fake keys uit environment."""
    assert len(km._keys) >= 11


def test_all_keys_start_with_gsk(km):
    """Elke key begint met gsk_."""
    for key in km._keys:
        assert key.startswith("gsk_")


def test_no_duplicates(km):
    """Geen dubbele keys in de pool."""
    assert len(km._keys) == len(set(km._keys))


# ─── Test: Key Selection (Round-Robin) ───

def test_get_key_returns_valid_key(km):
    """get_key() retourneert een key uit de pool."""
    key = km.get_key("TestAgent")
    assert key in km._keys


def test_round_robin_distributes(km):
    """Meerdere get_key() calls distribueren over keys."""
    keys_seen = set()
    for i in range(20):
        keys_seen.add(km.get_key(f"Agent_{i}"))
    # Moet meer dan 1 unieke key teruggeven
    assert len(keys_seen) > 1


# ─── Test: Blacklist ───

def test_blacklist_removes_key(km):
    """Geblackliste key wordt niet meer geselecteerd."""
    bad_key = km._keys[0]
    km.blacklist_key(bad_key)

    assert bad_key not in km._active_keys()
    assert len(km._active_keys()) == len(km._keys) - 1

    # get_key mag de bad key niet meer teruggeven
    for _ in range(50):
        assert km.get_key("TestAgent") != bad_key


def test_blacklist_all_falls_back(km):
    """Als alle keys geblacklist zijn, fallback naar eerste key."""
    for key in km._keys:
        km.blacklist_key(key)
    # Noodgreep: retourneert toch iets
    result = km.get_key("TestAgent")
    assert result  # niet leeg


# ─── Test: Throttle ───

def test_throttle_allows_first_request(km):
    """Eerste request wordt altijd doorgelaten."""
    ok, reason = km.check_throttle("TestAgent")
    assert ok is True
    assert reason == ""


def test_throttle_blocks_after_rpm_limit(km):
    """Na RPM limiet wordt de agent geblokkeerd."""
    model = "meta-llama/llama-4-scout-17b-16e-instruct"
    for _ in range(30):  # RPM=30 voor dit model
        km.registreer_request("TestAgent")

    ok, reason = km.check_throttle("TestAgent", model)
    assert ok is False
    assert "RPM" in reason


def test_throttle_tpm_near_limit(km):
    """Bij 90% TPM wordt de agent geblokkeerd."""
    model = "meta-llama/llama-4-scout-17b-16e-instruct"
    # Simuleer 27K tokens (90% van 30K TPM)
    km.registreer_tokens("TestAgent", "x" * (27_000 * 4))

    ok, reason = km.check_throttle("TestAgent", model)
    assert ok is False
    assert "TPM" in reason


# ─── Test: Priority Cooldown ───

def test_429_sets_cooldown(km):
    """429 registratie zet cooldown op basis van prioriteit."""
    km.registreer_429("CentralBrain")  # prio 0 → 2s cooldown
    agent = km._get_agent("CentralBrain")
    assert agent.cooldown_tot > time.time()
    assert agent.totaal_429s == 1


def test_priority_cooldown_duration(km):
    """Hogere prioriteit = kortere cooldown."""
    km.registreer_429("CentralBrain")  # prio 0 → 2s
    km.registreer_429("VoidWalker")    # prio 3 → 15s

    cb = km._get_agent("CentralBrain")
    vw = km._get_agent("VoidWalker")

    # VoidWalker cooldown moet langer zijn
    cb_remaining = cb.cooldown_tot - time.time()
    vw_remaining = vw.cooldown_tot - time.time()
    assert vw_remaining > cb_remaining


# ─── Test: Status ───

def test_get_status_structure(km):
    """get_status() retourneert correcte structuur."""
    status = km.get_status()
    assert "keys_beschikbaar" in status
    assert "keys_actief" in status
    assert "keys_blacklisted" in status
    assert "globale_429s" in status
    assert "agents" in status
    assert status["keys_beschikbaar"] >= 11
    assert status["keys_actief"] >= 11
    assert status["keys_blacklisted"] == 0


def test_status_reflects_blacklist(km):
    """Status toont blacklisted keys."""
    km.blacklist_key(km._keys[0])
    status = km.get_status()
    assert status["keys_blacklisted"] == 1
    assert status["keys_actief"] == status["keys_beschikbaar"] - 1


# ─── Test: Reset ───

def test_reset_counters(km):
    """reset_counters() wist alle metrieken."""
    km.registreer_request("TestAgent")
    km.registreer_429("TestAgent")
    km.reset_counters()
    assert len(km._agents) == 0
    assert km._global_429_count == 0

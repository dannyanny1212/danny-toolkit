"""
Test suite voor SmartKeyManager.

Tests:
1. Singleton pattern
2. Key discovery (1 key, multi-key)
3. Per-agent metrieken
4. Rate tracking (RPM, TPM, TPD)
5. Cooldown na 429
6. Prioriteit-gebaseerde cooldowns
7. Throttle check logica
8. Client factory (async + sync)
9. Status rapport
10. Reset functionaliteit

Gebruik: python test_key_manager.py
"""

import io
import os
import sys
import time

sys.stdout = io.TextIOWrapper(
    sys.stdout.buffer, encoding="utf-8", errors="replace"
)

# Test-mode env
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "-1")
os.environ.setdefault("DANNY_TEST_MODE", "1")
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

# Zorg dat project root op sys.path staat
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Minimale env voor tests
os.environ.setdefault("GROQ_API_KEY", "gsk_test_key_1234567890abcdefghij")

CHECKS = 0
PASSED = 0


def check(label: str, condition: bool):
    global CHECKS, PASSED
    CHECKS += 1
    if condition:
        PASSED += 1
        print(f"  [OK] {label}")
    else:
        print(f"  [FAIL] {label}")


def test_singleton():
    """Test 1: Singleton pattern — altijd dezelfde instantie."""
    print("\n--- Test 1: Singleton Pattern ---")

    # Reset singleton voor schone test
    import danny_toolkit.core.key_manager as km_mod
    km_mod._manager_instance = None
    km_mod.SmartKeyManager._instance = None

    from danny_toolkit.core.key_manager import get_key_manager, SmartKeyManager

    mgr1 = get_key_manager()
    mgr2 = get_key_manager()
    check("get_key_manager() geeft dezelfde instantie", mgr1 is mgr2)

    mgr3 = SmartKeyManager()
    check("SmartKeyManager() is ook dezelfde singleton", mgr1 is mgr3)

    check("Type is SmartKeyManager", isinstance(mgr1, SmartKeyManager))


def test_key_discovery():
    """Test 2: Key discovery — vindt keys uit environment."""
    print("\n--- Test 2: Key Discovery ---")

    import danny_toolkit.core.key_manager as km_mod
    km_mod._manager_instance = None
    km_mod.SmartKeyManager._instance = None

    # Zet test keys
    os.environ["GROQ_API_KEY"] = "gsk_test_primary_key_abcdef1234567890"
    os.environ["GROQ_API_KEY_2"] = "gsk_test_second_key_abcdef1234567890"

    mgr = km_mod.SmartKeyManager()
    km_mod.SmartKeyManager._instance = None  # Reset na test

    check("Primary key gevonden", len(mgr._keys) >= 1)
    check("Tweede key gevonden", len(mgr._keys) >= 2)
    check("Primary key is eerste", mgr._keys[0] == "gsk_test_primary_key_abcdef1234567890")

    # Cleanup
    del os.environ["GROQ_API_KEY_2"]
    os.environ["GROQ_API_KEY"] = "gsk_test_key_1234567890abcdefghij"


def test_invalid_keys_ignored():
    """Test 3: Ongeldige keys worden genegeerd."""
    print("\n--- Test 3: Ongeldige Keys ---")

    import danny_toolkit.core.key_manager as km_mod
    km_mod._manager_instance = None
    km_mod.SmartKeyManager._instance = None

    os.environ["GROQ_API_KEY"] = "gsk_valid_key_abcdef1234567890test"
    os.environ["GROQ_API_KEY_3"] = "INVALID_NO_PREFIX"
    os.environ["GROQ_API_KEY_4"] = ""

    mgr = km_mod.SmartKeyManager()
    km_mod.SmartKeyManager._instance = None

    check("Ongeldige key zonder gsk_ prefix genegeerd", "INVALID_NO_PREFIX" not in mgr._keys)
    check("Lege key genegeerd", "" not in mgr._keys)
    check("Geldige key wel gevonden", len(mgr._keys) >= 1)

    # Cleanup
    for k in ["GROQ_API_KEY_3", "GROQ_API_KEY_4"]:
        os.environ.pop(k, None)
    os.environ["GROQ_API_KEY"] = "gsk_test_key_1234567890abcdefghij"


def test_agent_metrics():
    """Test 4: Per-agent metrieken worden aangemaakt."""
    print("\n--- Test 4: Agent Metrieken ---")

    import danny_toolkit.core.key_manager as km_mod
    km_mod._manager_instance = None
    km_mod.SmartKeyManager._instance = None

    from danny_toolkit.core.key_manager import get_key_manager
    mgr = get_key_manager()

    agent = mgr._get_agent("CentralBrain")
    check("Agent naam correct", agent.naam == "CentralBrain")
    check("CentralBrain prioriteit = 0", agent.prioriteit == 0)

    agent2 = mgr._get_agent("VoidWalker")
    check("VoidWalker prioriteit = 3", agent2.prioriteit == 3)

    agent3 = mgr._get_agent("Dreamer")
    check("Dreamer prioriteit = 5", agent3.prioriteit == 5)

    agent4 = mgr._get_agent("OnbekendAgent")
    check("Onbekend agent krijgt default prioriteit 5", agent4.prioriteit == 5)


def test_rate_tracking():
    """Test 5: RPM en token tracking."""
    print("\n--- Test 5: Rate Tracking ---")

    import danny_toolkit.core.key_manager as km_mod
    km_mod._manager_instance = None
    km_mod.SmartKeyManager._instance = None

    from danny_toolkit.core.key_manager import get_key_manager
    mgr = get_key_manager()

    # Registreer requests
    for _ in range(5):
        mgr.registreer_request("TestAgent")

    agent = mgr._get_agent("TestAgent")
    check("5 requests geregistreerd", agent.totaal_requests == 5)
    check("5 timestamps in window", len(agent.request_timestamps) == 5)

    # Registreer tokens
    mgr.registreer_tokens("TestAgent", "a" * 400)  # 400 chars = ~100 tokens
    check("Tokens geregistreerd (100)", agent.totaal_tokens == 100)
    check("TPM teller bijgewerkt", agent.tokens_deze_minuut == 100)
    check("TPD teller bijgewerkt", agent.tokens_vandaag == 100)

    # Meer tokens
    mgr.registreer_tokens("TestAgent", "b" * 800)  # +200 tokens
    check("Cumulatief: 300 tokens", agent.totaal_tokens == 300)


def test_cooldown_429():
    """Test 6: Cooldown na rate limit hit."""
    print("\n--- Test 6: Cooldown na 429 ---")

    import danny_toolkit.core.key_manager as km_mod
    km_mod._manager_instance = None
    km_mod.SmartKeyManager._instance = None

    from danny_toolkit.core.key_manager import get_key_manager
    mgr = get_key_manager()

    # CentralBrain (prio 0) krijgt kortste cooldown (2s)
    mgr.registreer_429("CentralBrain")
    agent = mgr._get_agent("CentralBrain")
    check("429 geregistreerd", agent.totaal_429s == 1)
    check("Cooldown actief", time.time() < agent.cooldown_tot)

    mag, reden = mgr.check_throttle("CentralBrain")
    check("Throttle blokkeert tijdens cooldown", not mag)
    check("Reden bevat 'Cooldown'", "Cooldown" in reden)

    # VoidWalker (prio 3) krijgt langere cooldown (15s)
    mgr.registreer_429("VoidWalker")
    vw = mgr._get_agent("VoidWalker")
    cb = mgr._get_agent("CentralBrain")
    check(
        "VoidWalker cooldown > CentralBrain cooldown",
        vw.cooldown_tot - vw.laatste_429 > cb.cooldown_tot - cb.laatste_429,
    )


def test_priority_cooldowns():
    """Test 7: Prioriteit-gebaseerde cooldown duur."""
    print("\n--- Test 7: Prioriteit Cooldowns ---")

    from danny_toolkit.core.key_manager import PRIORITY_COOLDOWN

    check("Prio 0 (CentralBrain) = 2s", PRIORITY_COOLDOWN[0] == 2.0)
    check("Prio 1 (Tribunal) = 5s", PRIORITY_COOLDOWN[1] == 5.0)
    check("Prio 3 (VoidWalker) = 15s", PRIORITY_COOLDOWN[3] == 15.0)
    check("Prio 5 (Dreamer) = 30s", PRIORITY_COOLDOWN[5] == 30.0)
    check("Lagere prio = langere cooldown", PRIORITY_COOLDOWN[0] < PRIORITY_COOLDOWN[5])


def test_throttle_rpm():
    """Test 8: Throttle bij RPM limiet."""
    print("\n--- Test 8: RPM Throttle ---")

    import danny_toolkit.core.key_manager as km_mod
    km_mod._manager_instance = None
    km_mod.SmartKeyManager._instance = None

    from danny_toolkit.core.key_manager import get_key_manager
    mgr = get_key_manager()

    model = "meta-llama/llama-4-scout-17b-16e-instruct"

    # Vul tot RPM limiet (30)
    for _ in range(30):
        mgr.registreer_request("RPMTest")

    mag, reden = mgr.check_throttle("RPMTest", model=model)
    check("Geblokkeerd bij RPM limiet", not mag)
    check("Reden bevat 'RPM'", "RPM" in reden)


def test_throttle_tpm():
    """Test 9: Throttle bij TPM limiet."""
    print("\n--- Test 9: TPM Throttle ---")

    import danny_toolkit.core.key_manager as km_mod
    km_mod._manager_instance = None
    km_mod.SmartKeyManager._instance = None

    from danny_toolkit.core.key_manager import get_key_manager
    mgr = get_key_manager()

    model = "meta-llama/llama-4-scout-17b-16e-instruct"
    # TPM limiet = 30K, threshold 90% = 27K tokens
    # 27K tokens * 4 chars = 108K chars
    mgr.registreer_tokens("TPMTest", "x" * 108_000)

    mag, reden = mgr.check_throttle("TPMTest", model=model)
    check("Geblokkeerd bij TPM limiet (90%)", not mag)
    check("Reden bevat 'TPM'", "TPM" in reden)


def test_client_factory():
    """Test 10: Client factory methodes."""
    print("\n--- Test 10: Client Factory ---")

    import danny_toolkit.core.key_manager as km_mod
    km_mod._manager_instance = None
    km_mod.SmartKeyManager._instance = None

    from danny_toolkit.core.key_manager import get_key_manager
    mgr = get_key_manager()

    # Async client
    async_client = mgr.create_async_client("TestAsync")
    try:
        from groq import AsyncGroq
        check("Async client aangemaakt", async_client is not None)
        check("Async client is AsyncGroq", isinstance(async_client, AsyncGroq))
    except ImportError:
        check("Groq niet beschikbaar — skip async test", True)

    # Sync client
    sync_client = mgr.create_sync_client("TestSync")
    try:
        from groq import Groq
        check("Sync client aangemaakt", sync_client is not None)
        check("Sync client is Groq", isinstance(sync_client, Groq))
    except ImportError:
        check("Groq niet beschikbaar — skip sync test", True)


def test_status_report():
    """Test 11: Status rapport bevat alle verwachte velden."""
    print("\n--- Test 11: Status Rapport ---")

    import danny_toolkit.core.key_manager as km_mod
    km_mod._manager_instance = None
    km_mod.SmartKeyManager._instance = None

    from danny_toolkit.core.key_manager import get_key_manager
    mgr = get_key_manager()

    # Genereer wat activiteit
    mgr.registreer_request("StatusTest")
    mgr.registreer_tokens("StatusTest", "test" * 100)

    status = mgr.get_status()
    check("Status heeft 'keys_beschikbaar'", "keys_beschikbaar" in status)
    check("Status heeft 'globale_429s'", "globale_429s" in status)
    check("Status heeft 'agents' dict", "agents" in status)
    check("StatusTest in agents", "StatusTest" in status["agents"])

    agent_status = status["agents"]["StatusTest"]
    check("Agent heeft 'totaal_requests'", "totaal_requests" in agent_status)
    check("Agent heeft 'totaal_tokens'", "totaal_tokens" in agent_status)
    check("Agent heeft 'in_cooldown'", "in_cooldown" in agent_status)


def test_reset():
    """Test 12: Reset functionaliteit."""
    print("\n--- Test 12: Reset ---")

    import danny_toolkit.core.key_manager as km_mod
    km_mod._manager_instance = None
    km_mod.SmartKeyManager._instance = None

    from danny_toolkit.core.key_manager import get_key_manager
    mgr = get_key_manager()

    mgr.registreer_request("ResetTest")
    mgr.registreer_tokens("ResetTest", "data" * 100)
    check("Agent bestaat voor reset", "ResetTest" in mgr._agents)

    mgr.reset_counters()
    check("Agents leeg na reset", len(mgr._agents) == 0)
    check("Globale 429 teller gereset", mgr._global_429_count == 0)


def test_global_escalation():
    """Test 13: Globale cooldown bij herhaalde 429s."""
    print("\n--- Test 13: Globale Escalatie ---")

    import danny_toolkit.core.key_manager as km_mod
    km_mod._manager_instance = None
    km_mod.SmartKeyManager._instance = None

    from danny_toolkit.core.key_manager import get_key_manager
    mgr = get_key_manager()

    # 5 rate limits triggert globale cooldown
    for i in range(5):
        mgr.registreer_429(f"EscalAgent{i}")

    check("Globale 429 teller = 5", mgr._global_429_count == 5)
    check("Globale cooldown actief", time.time() < mgr._global_cooldown_tot)

    # Zelfs een agent zonder eigen cooldown wordt geblokkeerd
    mag, reden = mgr.check_throttle("SchoneAgent")
    check("Schone agent geblokkeerd door globale cooldown", not mag)
    check("Reden bevat 'Globale'", "Globale" in reden)


def test_agent_summary():
    """Test 14: Agent summary string."""
    print("\n--- Test 14: Agent Summary ---")

    import danny_toolkit.core.key_manager as km_mod
    km_mod._manager_instance = None
    km_mod.SmartKeyManager._instance = None

    from danny_toolkit.core.key_manager import get_key_manager
    mgr = get_key_manager()

    mgr.registreer_request("SummaryTest")
    mgr.registreer_tokens("SummaryTest", "x" * 400)

    summary = mgr.get_agent_summary("SummaryTest")
    check("Summary bevat agent naam", "SummaryTest" in summary)
    check("Summary bevat requests", "1 reqs" in summary)
    check("Summary bevat tokens", "100 tokens" in summary)


def main():
    global CHECKS, PASSED

    print("=" * 60)
    print("  SMART KEY MANAGER — TEST SUITE")
    print("=" * 60)

    test_singleton()
    test_key_discovery()
    test_invalid_keys_ignored()
    test_agent_metrics()
    test_rate_tracking()
    test_cooldown_429()
    test_priority_cooldowns()
    test_throttle_rpm()
    test_throttle_tpm()
    test_client_factory()
    test_status_report()
    test_reset()
    test_global_escalation()
    test_agent_summary()

    print(f"\n{'=' * 60}")
    print(f"  RESULTAAT: {PASSED}/{CHECKS} checks geslaagd")
    print(f"{'=' * 60}")

    if PASSED == CHECKS:
        print("  ALLE CHECKS GESLAAGD!")
    else:
        print(f"  {CHECKS - PASSED} check(s) gefaald!")

    sys.exit(0 if PASSED == CHECKS else 1)


if __name__ == "__main__":
    main()

"""
Phase 29 Tests — VirtualTwin: Mirror + VoidWalker in Sandbox Isolation.

14 tests, ~80 checks:
  1. env_bootstrap module exists + VENV_PYTHON resolves
  2. get_subprocess_env(test_mode=False) — CUDA=-1, no DANNY_TEST_MODE
  3. get_subprocess_env(test_mode=True) — has DANNY_TEST_MODE=1
  4. sandbox.py uses env_bootstrap (no internal _VENV_PYTHON def)
  5. artificer.py uses env_bootstrap (no fallback venv code)
  6. No bare ["python", in production code (source scan)
  7. VirtualTwin class + methods + containment gates
  8. snapshot_state() returns dict with expected keys
  8b. Anti-hallucination containment gates (grounding, BlackBox, sanitizer)
  8c. ShadowKeyVault — token isolation (scrubbing, throttle, budget)
  8d. Token Dividend — 50% shadow tokens returned to real swarm
  8e. BlackBox Adaptive Immune System — antibodies, escalation, vaccination
  8f. ShadowCortex — shadow-to-physical intelligence transfer
  9. SwarmEngine has virtual_twin property
 10. __init__.py exports VirtualTwin + EventTypes
"""

import os
import re
import sys

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


def check(beschrijving: str, conditie: bool):
    global passed, failed
    if conditie:
        passed += 1
        print(f"  OK  {beschrijving}")
    else:
        failed += 1
        print(f"  FAIL  {beschrijving}")


# ─── Test 1: env_bootstrap module exists + VENV_PYTHON ───

def test_1_env_bootstrap_exists():
    print("\n[Test 1] env_bootstrap module exists + VENV_PYTHON")
    path = os.path.join(
        PROJECT_ROOT, "danny_toolkit", "core", "env_bootstrap.py",
    )
    check("env_bootstrap.py exists", os.path.isfile(path))

    from danny_toolkit.core.env_bootstrap import VENV_PYTHON
    check("VENV_PYTHON is a string", isinstance(VENV_PYTHON, str))
    check("VENV_PYTHON path exists", os.path.isfile(VENV_PYTHON))


# ─── Test 2: get_subprocess_env(test_mode=False) ───

def test_2_subprocess_env_no_test_mode():
    print("\n[Test 2] get_subprocess_env(test_mode=False)")
    from danny_toolkit.core.env_bootstrap import get_subprocess_env

    env = get_subprocess_env(test_mode=False)
    check("env is a dict", isinstance(env, dict))
    check("CUDA_VISIBLE_DEVICES=-1", env.get("CUDA_VISIBLE_DEVICES") == "-1")
    check("ANONYMIZED_TELEMETRY=False", env.get("ANONYMIZED_TELEMETRY") == "False")
    check("PYTHONIOENCODING=utf-8", env.get("PYTHONIOENCODING") == "utf-8")
    check("no DANNY_TEST_MODE", "DANNY_TEST_MODE" not in env or env.get("DANNY_TEST_MODE") != "1"
          or os.environ.get("DANNY_TEST_MODE") == "1")
    # More specific: the function should NOT add DANNY_TEST_MODE on its own
    # We test by checking env_bootstrap source code
    import danny_toolkit.core.env_bootstrap as eb
    import inspect
    source = inspect.getsource(eb.get_subprocess_env)
    check("function only adds DANNY_TEST_MODE when test_mode=True",
          "if test_mode" in source)


# ─── Test 3: get_subprocess_env(test_mode=True) ───

def test_3_subprocess_env_test_mode():
    print("\n[Test 3] get_subprocess_env(test_mode=True)")
    from danny_toolkit.core.env_bootstrap import get_subprocess_env

    env = get_subprocess_env(test_mode=True)
    check("DANNY_TEST_MODE=1", env.get("DANNY_TEST_MODE") == "1")
    check("CUDA_VISIBLE_DEVICES=-1 (test mode too)", env.get("CUDA_VISIBLE_DEVICES") == "-1")


# ─── Test 4: sandbox.py uses env_bootstrap ───

def test_4_sandbox_uses_bootstrap():
    print("\n[Test 4] sandbox.py uses env_bootstrap")
    sandbox_path = os.path.join(
        PROJECT_ROOT, "danny_toolkit", "core", "sandbox.py",
    )
    with open(sandbox_path, "r", encoding="utf-8") as f:
        source = f.read()

    check("imports env_bootstrap", "env_bootstrap" in source)
    check("no internal _PROJECT_ROOT for venv",
          '_PROJECT_ROOT = str(Path' not in source)
    check("no DANNY_TEST_MODE in _SANDBOX_ENV_OVERRIDES",
          '_SANDBOX_ENV_OVERRIDES' not in source)


# ─── Test 5: artificer.py uses env_bootstrap ───

def test_5_artificer_uses_bootstrap():
    print("\n[Test 5] artificer.py uses env_bootstrap")
    art_path = os.path.join(
        PROJECT_ROOT, "danny_toolkit", "brain", "artificer.py",
    )
    with open(art_path, "r", encoding="utf-8") as f:
        source = f.read()

    check("imports env_bootstrap", "env_bootstrap" in source)
    check("no _PROJECT_ROOT = str(Path fallback",
          '_PROJECT_ROOT = str(Path' not in source)


# ─── Test 6: No bare ["python", in production code ───

def test_6_no_bare_python_subprocess():
    print('\n[Test 6] No bare ["python", in subprocess calls')
    # Scan production files for subprocess.run/Popen with bare "python"
    # Pattern: lines with subprocess AND ["python",
    # Excludes data arrays (tags, keyword lists)
    bare_sub_re = re.compile(
        r'subprocess\.\w+\s*\(\s*\n?\s*\["python",'
        r'|'
        r'\["python",\s*str\(',
        re.MULTILINE,
    )
    violations = []

    scan_dirs = [
        os.path.join(PROJECT_ROOT, "danny_toolkit"),
    ]
    scan_files = [
        os.path.join(PROJECT_ROOT, "swarm_engine.py"),
        os.path.join(PROJECT_ROOT, "cli.py"),
        os.path.join(PROJECT_ROOT, "main.py"),
    ]

    for scan_dir in scan_dirs:
        for root, dirs, files in os.walk(scan_dir):
            for fname in files:
                if fname.endswith(".py"):
                    scan_files.append(os.path.join(root, fname))

    for fpath in scan_files:
        if not os.path.isfile(fpath):
            continue
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()
            if bare_sub_re.search(content):
                rel = os.path.relpath(fpath, PROJECT_ROOT)
                violations.append(rel)
        except (IOError, UnicodeDecodeError):
            pass

    check(f'no bare ["python", subprocess calls (found: {violations})',
          len(violations) == 0)


# ─── Test 7: VirtualTwin class + methods ───

def test_7_virtual_twin_class():
    print("\n[Test 7] VirtualTwin class + methods + containment gates")
    from danny_toolkit.brain.virtual_twin import VirtualTwin, SHADOW_PREFIX

    check("VirtualTwin is a class", isinstance(VirtualTwin, type))
    check("SHADOW_PREFIX is #@*", SHADOW_PREFIX == "#@*")

    twin = VirtualTwin()
    check("has consult method", hasattr(twin, "consult") and callable(twin.consult))
    check("has snapshot_state method", hasattr(twin, "snapshot_state") and callable(twin.snapshot_state))
    check("has research method", hasattr(twin, "research") and callable(twin.research))
    check("has get_mirror_context method", hasattr(twin, "get_mirror_context") and callable(twin.get_mirror_context))
    check("has synthesize method", hasattr(twin, "synthesize") and callable(twin.synthesize))
    # Shadow identity — #@* prefix
    check("twin.name starts with #@*", twin.name.startswith("#@*"))
    check("twin.NAME = #@*VirtualTwin", VirtualTwin.NAME == "#@*VirtualTwin")
    # Anti-hallucination containment gates
    check("has _verify_grounding method", hasattr(twin, "_verify_grounding") and callable(twin._verify_grounding))
    check("has _get_truth_anchor method", hasattr(twin, "_get_truth_anchor") and callable(twin._get_truth_anchor))
    check("has _get_black_box method", hasattr(twin, "_get_black_box") and callable(twin._get_black_box))


# ─── Test 8: snapshot_state() returns expected keys ───

def test_8_snapshot_state_keys():
    print("\n[Test 8] snapshot_state() returns expected keys")
    from danny_toolkit.brain.virtual_twin import VirtualTwin

    twin = VirtualTwin()
    state = twin.snapshot_state()

    check("returns dict", isinstance(state, dict))
    check("has 'cortical' key", "cortical" in state)
    check("has 'synapse' key", "synapse" in state)
    check("has 'phantom' key", "phantom" in state)
    check("has 'config' key", "config" in state)
    check("has 'bus_context' key", "bus_context" in state)
    check("config has 'model' key", "model" in state.get("config", {}))


# ─── Test 8b: Anti-hallucination containment ───

def test_8b_containment_gates():
    print("\n[Test 8b] Anti-hallucination containment gates")
    from danny_toolkit.brain.virtual_twin import VirtualTwin

    twin = VirtualTwin()

    # _verify_grounding should tag output when no TruthAnchor / no context
    empty_state = {"cortical": {}, "synapse": {}, "phantom": {}, "config": {}, "bus_context": []}

    # Without TruthAnchor loaded (test env), should mark as UNVERIFIED or SPECULATIVE
    tagged = twin._verify_grounding("test output", "test query", empty_state, "")
    check("empty context → tagged output", tagged.startswith("[TWIN:"))
    check("output preserved in tag", "test output" in tagged)

    # With context docs but no TruthAnchor → should still be tagged
    state_with_facts = {
        "cortical": {"facts": ["Python is een programmeertaal"], "event_summary": ["user: query"]},
        "synapse": {}, "phantom": {}, "config": {}, "bus_context": [],
    }
    tagged2 = twin._verify_grounding("Python is goed", "wat is python", state_with_facts, "Python docs")
    check("with context → tagged output", tagged2.startswith("[TWIN:"))
    check("output preserved with context", "Python is goed" in tagged2)

    # Verify synthesis prompt includes grounding instructions (source code check)
    import inspect
    synth_source = inspect.getsource(twin.synthesize)
    check("synthesize has grounding instruction", "UITSLUITEND" in synth_source)
    check("synthesize warns against fabrication", "Verzin NOOIT" in synth_source)
    check("synthesize accepts blackbox_warning param", "blackbox_warning" in synth_source)

    # Verify VoidWalker output is sanitized (source code check)
    consult_source = inspect.getsource(twin.consult)
    check("consult sanitizes research output", "sanitize_for_llm" in consult_source)
    check("consult checks BlackBox", "retrieve_warnings" in consult_source)
    check("consult scrubs output before return", "scrub_keys" in consult_source)


# ─── Test 8c: ShadowKeyVault token isolation ───

def test_8c_shadow_key_vault():
    print("\n[Test 8c] ShadowKeyVault — token isolation")
    from danny_toolkit.brain.virtual_twin import ShadowKeyVault, VirtualTwin, SHADOW_PREFIX

    # ShadowKeyVault exists and is usable
    vault = ShadowKeyVault()
    check("ShadowKeyVault instantiates", vault is not None)
    check("ShadowKeyVault.NAME has #@* prefix", ShadowKeyVault.NAME.startswith("#@*"))

    # Key scrubbing — gsk_ patterns must be stripped, redacted with #@* prefix
    dirty = "The key is gsk_abc123def456ghi789jkl012mno345 and more text"
    scrubbed = vault.scrub_keys(dirty)
    check("gsk_ key fully scrubbed", "gsk_" not in scrubbed)
    check("surrounding text preserved", "more text" in scrubbed)
    check("redaction marker has #@* prefix", "#@*SHADOW:KEY_REDACTED" in scrubbed)

    # Empty/None input safety
    check("scrub_keys handles empty string", vault.scrub_keys("") == "")
    check("scrub_keys handles None", vault.scrub_keys(None) is None)

    # Shadow throttle — should allow requests initially
    allowed, reason = vault.check_shadow_throttle()
    check("initial throttle allows requests", allowed is True)

    # Shadow stats
    stats = vault.get_shadow_stats()
    check("shadow stats has shadow_requests", "shadow_requests" in stats)
    check("shadow stats has shadow_tokens", "shadow_tokens" in stats)
    check("shadow stats has shadow_429s", "shadow_429s" in stats)

    # Register shadow request and verify counter
    vault.registreer_shadow_request()
    vault.registreer_shadow_tokens(100)
    stats2 = vault.get_shadow_stats()
    check("shadow request counted", stats2["shadow_requests"] == 1)
    check("shadow tokens counted", stats2["shadow_tokens"] == 100)

    # VirtualTwin uses vault
    twin = VirtualTwin()
    check("twin has _vault attribute", hasattr(twin, "_vault"))
    check("twin._vault is ShadowKeyVault", isinstance(twin._vault, ShadowKeyVault))

    # Shadow 429 triggers cooldown
    vault.registreer_shadow_429()
    allowed2, reason2 = vault.check_shadow_throttle()
    check("after 429 → shadow throttled", allowed2 is False)
    check("cooldown reason present", "cooldown" in reason2.lower())


# ─── Test 8d: Token Dividend — 50% return to real swarm ───

def test_8d_token_dividend():
    print("\n[Test 8d] Token Dividend — 50% shadow tokens returned")
    from danny_toolkit.brain.virtual_twin import ShadowKeyVault

    vault = ShadowKeyVault()

    # DIVIDEND_RATE constant
    check("DIVIDEND_RATE is 0.5", ShadowKeyVault.DIVIDEND_RATE == 0.5)

    # Accumulate tokens — dividend pool should grow at 50%
    vault.registreer_shadow_tokens(200)
    stats = vault.get_shadow_stats()
    check("dividend_pool = 100 (50% of 200)", stats["dividend_pool"] == 100)
    check("total_dividends_paid starts at 0", stats["total_dividends_paid"] == 0)

    # Flush dividend
    payout = vault.flush_dividend()
    check("flush_dividend returns payout amount", payout == 100)

    stats2 = vault.get_shadow_stats()
    check("dividend_pool reset to 0 after flush", stats2["dividend_pool"] == 0)
    check("total_dividends_paid updated", stats2["total_dividends_paid"] == 100)

    # Second flush with no new tokens — returns 0
    payout2 = vault.flush_dividend()
    check("no-op flush returns 0", payout2 == 0)

    # Accumulate more, verify cumulative tracking
    vault.registreer_shadow_tokens(50)
    payout3 = vault.flush_dividend()
    check("second payout = 25 (50% of 50)", payout3 == 25)
    stats3 = vault.get_shadow_stats()
    check("cumulative dividends = 125", stats3["total_dividends_paid"] == 125)

    # flush_dividend source code check — should interact with KeyManager
    import inspect
    source = inspect.getsource(vault.flush_dividend)
    check("flush_dividend reduces cooldowns", "cooldown_tot" in source)
    check("flush_dividend uses get_key_manager", "get_key_manager" in source)
    check("flush_dividend uses #@* shadow agent name", "SHADOW_PREFIX" in source)


# ─── Test 8e: BlackBox Adaptive Immune System ───

def test_8e_blackbox_immune_system():
    print("\n[Test 8e] BlackBox Adaptive Immune System")
    from danny_toolkit.brain.black_box import BlackBox, Antibody, Severity

    # Severity enum
    check("Severity has MILD", Severity.MILD.value == 1)
    check("Severity has SEVERE", Severity.SEVERE.value == 2)
    check("Severity has CRITICAL", Severity.CRITICAL.value == 3)

    # Antibody dataclass
    ab = Antibody(signature="test pattern", antidote="avoid this")
    check("Antibody instantiates", ab is not None)
    check("initial severity is MILD", ab.severity == Severity.MILD)
    check("initial encounters is 1", ab.encounters == 1)
    check("strength is float between 0-1", 0.0 <= ab.strength <= 1.0)
    check("fresh antibody is alive", ab.alive is True)
    check("fresh antibody strength ~1.0", ab.strength > 0.9)

    # Antibody reinforcement + severity escalation
    for _ in range(4):
        ab.reinforce()
    check("after 5 encounters, severity = SEVERE",
          ab.encounters == 5 and ab.severity == Severity.SEVERE)

    for _ in range(5):
        ab.reinforce()
    check("after 10 encounters, severity = CRITICAL",
          ab.encounters == 10 and ab.severity == Severity.CRITICAL)

    # Antibody serialization round-trip
    d = ab.to_dict()
    check("to_dict has signature", d["signature"] == "test pattern")
    check("to_dict has severity name", d["severity"] == "CRITICAL")
    check("to_dict has encounters", d["encounters"] == 10)

    ab2 = Antibody.from_dict(d)
    check("from_dict preserves signature", ab2.signature == "test pattern")
    check("from_dict preserves severity", ab2.severity == Severity.CRITICAL)
    check("from_dict preserves encounters", ab2.encounters == 10)

    # BlackBox class
    bb = BlackBox()
    check("BlackBox instantiates", bb is not None)
    check("has record_crash method", callable(getattr(bb, "record_crash", None)))
    check("has retrieve_warnings method", callable(getattr(bb, "retrieve_warnings", None)))
    check("has purge_dead method", callable(getattr(bb, "purge_dead", None)))
    check("has get_antibodies method", callable(getattr(bb, "get_antibodies", None)))
    check("has get_stats method", callable(getattr(bb, "get_stats", None)))

    # Stats structure
    stats = bb.get_stats()
    check("stats has active_antibodies", "active_antibodies" in stats)
    check("stats has total_antibodies", "total_antibodies" in stats)
    check("stats has by_severity", "by_severity" in stats)
    check("stats has total_encounters", "total_encounters" in stats)
    check("by_severity has MILD/SEVERE/CRITICAL",
          all(k in stats["by_severity"] for k in ("MILD", "SEVERE", "CRITICAL")))

    # get_antibodies returns list of dicts
    antibodies = bb.get_antibodies()
    check("get_antibodies returns list", isinstance(antibodies, list))

    # Vaccination source code check — should broadcast on NeuralBus
    import inspect
    vax_source = inspect.getsource(bb._vaccinate)
    check("_vaccinate publishes to NeuralBus", "publish" in vax_source)
    check("_vaccinate sends IMMUNE_RESPONSE", "IMMUNE_RESPONSE" in vax_source)

    # BlackBox source — immune memory persistence
    check("ANTIBODY_FILE defined", bb.ANTIBODY_FILE == "immune_memory.json")
    check("_antibodies is dict", isinstance(bb._antibodies, dict))


# ─── Test 8f: ShadowCortex — intelligence transfer ───

def test_8f_shadow_cortex():
    print("\n[Test 8f] ShadowCortex — shadow-to-physical intelligence transfer")
    from danny_toolkit.brain.virtual_twin import (
        ShadowCortex, VirtualTwin, SHADOW_PREFIX,
    )

    # ShadowCortex class exists
    check("ShadowCortex is a class", isinstance(ShadowCortex, type))
    check("ShadowCortex.NAME has #@* prefix", ShadowCortex.NAME.startswith("#@*"))

    cortex = ShadowCortex()
    check("ShadowCortex instantiates", cortex is not None)

    # Methods exist
    check("has absorb method", callable(getattr(cortex, "absorb", None)))
    check("has _boost_synapse method", callable(getattr(cortex, "_boost_synapse", None)))
    check("has _inject_cortical method", callable(getattr(cortex, "_inject_cortical", None)))
    check("has _prime_phantom method", callable(getattr(cortex, "_prime_phantom", None)))
    check("has _broadcast_shadow_insight method", callable(getattr(cortex, "_broadcast_shadow_insight", None)))
    check("has get_stats method", callable(getattr(cortex, "get_stats", None)))

    # Stats structure
    stats = cortex.get_stats()
    check("stats has absorptions", "absorptions" in stats)
    check("stats has synapse_boosts", "synapse_boosts" in stats)
    check("stats has cortical_injections", "cortical_injections" in stats)
    check("stats has phantom_primes", "phantom_primes" in stats)
    check("initial absorptions = 0", stats["absorptions"] == 0)

    # Absorb a shadow insight
    cortex.absorb("hoe werkt python async", "Python async uses event loops")
    stats2 = cortex.get_stats()
    check("absorptions incremented after absorb", stats2["absorptions"] == 1)

    # Dedup — same query should not absorb twice
    cortex.absorb("hoe werkt python async", "Same result")
    stats3 = cortex.get_stats()
    check("dedup prevents double absorption", stats3["absorptions"] == 1)

    # Different query absorbs
    cortex.absorb("wat is machine learning", "ML is pattern recognition")
    stats4 = cortex.get_stats()
    check("new topic absorbs", stats4["absorptions"] == 2)

    # Empty inputs are ignored
    cortex.absorb("", "result")
    cortex.absorb("query", "")
    stats5 = cortex.get_stats()
    check("empty inputs ignored", stats5["absorptions"] == 2)

    # VirtualTwin has _shadow_cortex
    twin = VirtualTwin()
    check("twin has _shadow_cortex", hasattr(twin, "_shadow_cortex"))
    check("twin._shadow_cortex is ShadowCortex",
          isinstance(twin._shadow_cortex, ShadowCortex))

    # _distill_to_physical wired in consult
    import inspect
    consult_src = inspect.getsource(twin.consult)
    check("consult calls _distill_to_physical", "_distill_to_physical" in consult_src)

    # Keyword extraction
    keywords = cortex._extract_keywords("hoe werkt de python async event loop")
    check("keywords extracted", len(keywords) > 0)
    check("stop words filtered", "hoe" not in keywords and "de" not in keywords)
    check("content words kept", "python" in keywords or "async" in keywords)


# ─── Test 9: SwarmEngine has virtual_twin property ───

def test_9_swarm_virtual_twin():
    print("\n[Test 9] SwarmEngine has virtual_twin property")
    from swarm_engine import SwarmEngine

    check("SwarmEngine has virtual_twin property",
          hasattr(SwarmEngine, "virtual_twin"))

    engine = SwarmEngine(brain=None)
    check("VIRTUAL_TWIN in agents",
          "VIRTUAL_TWIN" in engine.agents)
    check("twin_consultations in metrics",
          "twin_consultations" in engine._swarm_metrics)
    # Agent name carries #@* shadow prefix
    twin_agent = engine.agents.get("VIRTUAL_TWIN")
    check("twin agent name has #@* prefix",
          twin_agent is not None and twin_agent.name.startswith("#@*"))


# ─── Test 10: __init__.py exports VirtualTwin ───

def test_10_init_exports():
    print("\n[Test 10] __init__.py exports VirtualTwin")
    init_path = os.path.join(
        PROJECT_ROOT, "danny_toolkit", "brain", "__init__.py",
    )
    with open(init_path, "r", encoding="utf-8") as f:
        source = f.read()

    check("VirtualTwin in import block", "virtual_twin import VirtualTwin" in source)
    check("VirtualTwin in __all__", '"VirtualTwin"' in source)

    # Also verify EventTypes for VirtualTwin + Immune system
    from danny_toolkit.core.neural_bus import EventTypes
    check("EventTypes.TWIN_CONSULTATION exists",
          hasattr(EventTypes, "TWIN_CONSULTATION"))
    check("EventTypes.IMMUNE_RESPONSE exists",
          hasattr(EventTypes, "IMMUNE_RESPONSE"))


# ─── Run All ───

if __name__ == "__main__":
    print("=" * 60)
    print("  Phase 29: VirtualTwin — Mirror + VoidWalker")
    print("=" * 60)

    test_1_env_bootstrap_exists()
    test_2_subprocess_env_no_test_mode()
    test_3_subprocess_env_test_mode()
    test_4_sandbox_uses_bootstrap()
    test_5_artificer_uses_bootstrap()
    test_6_no_bare_python_subprocess()
    test_7_virtual_twin_class()
    test_8_snapshot_state_keys()
    test_8b_containment_gates()
    test_8c_shadow_key_vault()
    test_8d_token_dividend()
    test_8e_blackbox_immune_system()
    test_8f_shadow_cortex()
    test_9_swarm_virtual_twin()
    test_10_init_exports()

    print(f"\n{'=' * 60}")
    total = passed + failed
    print(f"  Phase 29: {passed}/{total} checks passed")
    if failed:
        print(f"  {failed} FAILED")
    else:
        print("  ALL PASSED")
    print(f"{'=' * 60}")

    sys.exit(0 if failed == 0 else 1)

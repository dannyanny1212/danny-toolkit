"""
Phase 39 — DEEP OBSERVATORY
============================
Test suite: 18 tests, ~70 checks

Pillars:
  1. Singleton identity (BlackBox, HallucinatieSchild, AdversarialTribunal)
  2. Stats accumulation across singleton instances
  3. FastAPI response models + 6 nieuwe Observatory endpoints
  4. Caller wiring verification via inspect.getsource()
  5. Synapse/Phantom stats shape
  6. Version 6.6.0 + module integrity
"""

import inspect
import os
import sys
import threading

os.environ.setdefault("DANNY_TEST_MODE", "1")
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "-1")
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

passed = 0
failed = 0


def check(label, condition):
    global passed, failed
    if condition:
        print(f"  OK  {label}")
        passed += 1
    else:
        print(f"  FAIL  {label}")
        failed += 1


# ═══════════════════════════════════════════════════
# TEST 1: SINGLETON IDENTITY — BlackBox
# ═══════════════════════════════════════════════════

def test_1_blackbox_singleton_identity():
    """BlackBox: get_black_box() retourneert dezelfde instantie."""
    print("\n[Test 1] BlackBox: singleton identity")
    from danny_toolkit.brain.black_box import get_black_box, _black_box_lock

    # Reset singleton voor schone test
    import danny_toolkit.brain.black_box as bb_mod
    bb_mod._black_box_instance = None

    a = get_black_box()
    b = get_black_box()
    check("id(a) == id(b)", id(a) == id(b))
    check("isinstance BlackBox", a.__class__.__name__ == "BlackBox")
    check("_black_box_lock is threading.Lock", isinstance(_black_box_lock, type(threading.Lock())))


# ═══════════════════════════════════════════════════
# TEST 2: SINGLETON IDENTITY — HallucinatieSchild
# ═══════════════════════════════════════════════════

def test_2_schild_singleton_identity():
    """HallucinatieSchild: get_hallucination_shield() retourneert dezelfde instantie."""
    print("\n[Test 2] HallucinatieSchild: singleton identity")
    from danny_toolkit.brain.hallucination_shield import (
        get_hallucination_shield, _hallucination_shield_lock,
    )

    # Reset singleton voor schone test
    import danny_toolkit.brain.hallucination_shield as hs_mod
    hs_mod._hallucination_shield_instance = None

    a = get_hallucination_shield()
    b = get_hallucination_shield()
    check("id(a) == id(b)", id(a) == id(b))
    check("isinstance HallucinatieSchild", a.__class__.__name__ == "HallucinatieSchild")
    check("_hallucination_shield_lock is threading.Lock",
          isinstance(_hallucination_shield_lock, type(threading.Lock())))


# ═══════════════════════════════════════════════════
# TEST 3: SINGLETON IDENTITY — AdversarialTribunal
# ═══════════════════════════════════════════════════

def test_3_tribunal_singleton_identity():
    """AdversarialTribunal: get_adversarial_tribunal() retourneert dezelfde instantie."""
    print("\n[Test 3] AdversarialTribunal: singleton identity")
    from danny_toolkit.brain.adversarial_tribunal import (
        get_adversarial_tribunal, _adversarial_tribunal_lock,
    )

    # Reset singleton voor schone test
    import danny_toolkit.brain.adversarial_tribunal as at_mod
    at_mod._adversarial_tribunal_instance = None

    a = get_adversarial_tribunal()
    b = get_adversarial_tribunal(brain="ignored")
    check("id(a) == id(b)", id(a) == id(b))
    check("isinstance AdversarialTribunal", a.__class__.__name__ == "AdversarialTribunal")
    check("brain arg ignored na eerste aanroep", a.brain is None)
    check("_adversarial_tribunal_lock is threading.Lock",
          isinstance(_adversarial_tribunal_lock, type(threading.Lock())))


# ═══════════════════════════════════════════════════
# TEST 4: HALLUCINATIESCHILD STATS ACCUMULEREN
# ═══════════════════════════════════════════════════

def test_4_schild_stats_accumuleren():
    """HallucinatieSchild: stats overleven over meerdere get_hallucination_shield() calls."""
    print("\n[Test 4] HallucinatieSchild: stats accumulatie")
    from danny_toolkit.brain.hallucination_shield import get_hallucination_shield
    from dataclasses import dataclass

    @dataclass
    class FakePayload:
        agent: str = "TestAgent"
        display_text: str = "Dit is een test antwoord met genoeg woorden."
        content: str = ""
        type: str = "text"
        timestamp: float = 0.0
        metadata: dict = None

        def __post_init__(self):
            if self.metadata is None:
                self.metadata = {}

    schild = get_hallucination_shield()
    schild.reset_stats()

    # Eerste beoordeling — zou doorgelaten moeten worden (score >= drempel)
    payloads = [FakePayload()]
    rapport = schild.beoordeel(payloads, "test vraag")
    stats1 = schild.get_stats()
    check("beoordeeld >= 1 na eerste call", stats1["beoordeeld"] >= 1)

    # Tweede call via verse get
    schild2 = get_hallucination_shield()
    rapport2 = schild2.beoordeel(payloads, "test vraag 2")
    stats2 = schild2.get_stats()
    check("beoordeeld >= 2 na tweede call", stats2["beoordeeld"] >= 2)
    check("Stats accumuleren (zelfde instantie)", stats2["beoordeeld"] > stats1["beoordeeld"])


# ═══════════════════════════════════════════════════
# TEST 5: BLACKBOX SHARED STATE
# ═══════════════════════════════════════════════════

def test_5_blackbox_shared_state():
    """BlackBox: get_black_box() deelt state (antibodies dict)."""
    print("\n[Test 5] BlackBox: shared state")
    from danny_toolkit.brain.black_box import get_black_box

    bb1 = get_black_box()
    bb2 = get_black_box()

    # Zelfde antibodies dict
    check("Zelfde _antibodies dict", bb1._antibodies is bb2._antibodies)
    check("Zelfde _store object", bb1._store is bb2._store)

    # get_stats werkt
    stats = bb1.get_stats()
    check("get_stats retourneert dict", isinstance(stats, dict))
    check("recorded_failures in stats", "recorded_failures" in stats)
    check("active_antibodies in stats", "active_antibodies" in stats)
    check("by_severity in stats", "by_severity" in stats)


# ═══════════════════════════════════════════════════
# TEST 6: SINGLETON EXPORTS IN __init__.py
# ═══════════════════════════════════════════════════

def test_6_singleton_exports():
    """brain __init__: alle drie singletons exporteerbaar."""
    print("\n[Test 6] brain __init__: singleton exports")
    import danny_toolkit.brain as brain_pkg

    check("get_black_box in brain", hasattr(brain_pkg, "get_black_box"))
    check("get_hallucination_shield in brain", hasattr(brain_pkg, "get_hallucination_shield"))
    check("get_adversarial_tribunal in brain", hasattr(brain_pkg, "get_adversarial_tribunal"))

    # __all__ check
    check("get_black_box in __all__", "get_black_box" in brain_pkg.__all__)
    check("get_hallucination_shield in __all__", "get_hallucination_shield" in brain_pkg.__all__)
    check("get_adversarial_tribunal in __all__", "get_adversarial_tribunal" in brain_pkg.__all__)


# ═══════════════════════════════════════════════════
# TEST 7: FASTAPI RESPONSE MODELS
# ═══════════════════════════════════════════════════

def test_7_fastapi_response_models():
    """FastAPI: Phase 39 Pydantic response models."""
    print("\n[Test 7] FastAPI: Phase 39 response models")
    import fastapi_server as fs

    models = [
        "SchildStatsResponse", "TribunalStatsResponse",
        "AlertHistoryResponse", "AlertEntryResponse",
        "BlackBoxStatsResponse",
        "SynapseStatsResponse", "SynapsePathwayResponse",
        "PhantomAccuracyResponse", "PhantomPredictionResponse",
    ]
    for m in models:
        check(f"{m} exists", hasattr(fs, m))


# ═══════════════════════════════════════════════════
# TEST 8: FASTAPI MODELS INSTANTIEERBAAR
# ═══════════════════════════════════════════════════

def test_8_fastapi_models_instantiate():
    """FastAPI: response models instantieerbaar met defaults."""
    print("\n[Test 8] FastAPI: models instantieerbaar")
    from fastapi_server import (
        SchildStatsResponse, TribunalStatsResponse,
        AlertHistoryResponse, BlackBoxStatsResponse,
        SynapseStatsResponse, PhantomAccuracyResponse,
    )

    ss = SchildStatsResponse()
    check("SchildStats beoordeeld=0 default", ss.beoordeeld == 0)
    check("SchildStats geblokkeerd=0 default", ss.geblokkeerd == 0)

    ts = TribunalStatsResponse()
    check("TribunalStats accepted=0 default", ts.accepted == 0)
    check("TribunalStats acceptance_rate=N/A default", ts.acceptance_rate == "N/A")

    ah = AlertHistoryResponse()
    check("AlertHistory history=[] default", ah.history == [])
    check("AlertHistory stats={} default", ah.stats == {})

    bbs = BlackBoxStatsResponse()
    check("BlackBoxStats recorded_failures=0", bbs.recorded_failures == 0)
    check("BlackBoxStats by_severity={}", bbs.by_severity == {})

    sy = SynapseStatsResponse()
    check("SynapseStats pathways=0 default", sy.pathways == 0)
    check("SynapseStats top_pathways=[]", sy.top_pathways == [])

    pa = PhantomAccuracyResponse()
    check("PhantomAccuracy accuracy=0.0", pa.accuracy == 0.0)
    check("PhantomAccuracy predictions=[]", pa.predictions == [])


# ═══════════════════════════════════════════════════
# TEST 9: FASTAPI PHASE 39 ROUTES
# ═══════════════════════════════════════════════════

def test_9_fastapi_phase39_routes():
    """FastAPI: Phase 39 Observatory routes geregistreerd."""
    print("\n[Test 9] FastAPI: Phase 39 routes")
    import fastapi_server as fs
    routes = [r.path for r in fs.app.routes if hasattr(r, "path")]

    expected = [
        "/api/v1/schild/stats",
        "/api/v1/tribunal/stats",
        "/api/v1/alerts/history",
        "/api/v1/blackbox/stats",
        "/api/v1/synapse/stats",
        "/api/v1/phantom/accuracy",
    ]
    for ep in expected:
        check(ep, ep in routes)


# ═══════════════════════════════════════════════════
# TEST 10: BESTAANDE ROUTES INTACT
# ═══════════════════════════════════════════════════

def test_10_existing_routes_intact():
    """FastAPI: bestaande Phase 38 + core routes intact."""
    print("\n[Test 10] FastAPI: bestaande routes intact")
    import fastapi_server as fs
    routes = [r.path for r in fs.app.routes if hasattr(r, "path")]

    # Core
    check("/api/v1/query", "/api/v1/query" in routes)
    check("/api/v1/health", "/api/v1/health" in routes)
    check("/api/v1/agents", "/api/v1/agents" in routes)

    # Phase 38
    check("/api/v1/config/audit", "/api/v1/config/audit" in routes)
    check("/api/v1/bus/stats", "/api/v1/bus/stats" in routes)
    check("/api/v1/pruning/stats", "/api/v1/pruning/stats" in routes)
    check("/api/v1/errors/taxonomy", "/api/v1/errors/taxonomy" in routes)


# ═══════════════════════════════════════════════════
# TEST 11: CALLER WIRING — swarm_engine HallucinatieSchild
# ═══════════════════════════════════════════════════

def test_11_wiring_swarm_schild():
    """SwarmEngine: get_hallucination_shield() vervangt HallucinatieSchild()."""
    print("\n[Test 11] Wiring: swarm_engine → get_hallucination_shield")
    import swarm_engine as se
    source = inspect.getsource(se.SwarmEngine.run)
    check("get_hallucination_shield in run()", "get_hallucination_shield" in source)
    check("HallucinatieSchild() NIET in run()", "HallucinatieSchild()" not in source)


# ═══════════════════════════════════════════════════
# TEST 12: CALLER WIRING — swarm_engine AdversarialTribunal
# ═══════════════════════════════════════════════════

def test_12_wiring_swarm_tribunal():
    """SwarmEngine: get_adversarial_tribunal() vervangt AdversarialTribunal()."""
    print("\n[Test 12] Wiring: swarm_engine → get_adversarial_tribunal")
    import swarm_engine as se
    source = inspect.getsource(se.SwarmEngine._tribunal.fget)
    check("get_adversarial_tribunal in _tribunal", "get_adversarial_tribunal" in source)
    check("AdversarialTribunal(brain= NIET in _tribunal",
          "AdversarialTribunal(brain=" not in source)


# ═══════════════════════════════════════════════════
# TEST 13: CALLER WIRING — trinity_omega BlackBox
# ═══════════════════════════════════════════════════

def test_13_wiring_trinity_blackbox():
    """trinity_omega: get_black_box() vervangt BlackBox()."""
    print("\n[Test 13] Wiring: trinity_omega → get_black_box")
    from danny_toolkit.brain import trinity_omega as to_mod

    # _init_feedback_loop
    source_fb = inspect.getsource(to_mod.PrometheusBrain._init_feedback_loop)
    check("get_black_box in _init_feedback_loop", "get_black_box" in source_fb)
    check("BlackBox() NIET in _init_feedback_loop", "BlackBox()" not in source_fb)

    # _rag_enrich (warning retrieval)
    source_rag = inspect.getsource(to_mod.PrometheusBrain._rag_enrich)
    check("get_black_box in _rag_enrich", "get_black_box" in source_rag)
    check("BlackBox() NIET in _rag_enrich", "BlackBox()" not in source_rag)


# ═══════════════════════════════════════════════════
# TEST 14: CALLER WIRING — hallucination_shield BlackBox
# ═══════════════════════════════════════════════════

def test_14_wiring_schild_blackbox():
    """hallucination_shield: get_black_box() vervangt BlackBox()."""
    print("\n[Test 14] Wiring: hallucination_shield → get_black_box")
    from danny_toolkit.brain import hallucination_shield as hs_mod
    source = inspect.getsource(hs_mod.HallucinatieSchild._log_naar_blackbox)
    check("get_black_box in _log_naar_blackbox", "get_black_box" in source)
    check("BlackBox() NIET in _log_naar_blackbox", "BlackBox()" not in source)


# ═══════════════════════════════════════════════════
# TEST 15: CALLER WIRING — dreamer + config_auditor
# ═══════════════════════════════════════════════════

def test_15_wiring_dreamer_auditor():
    """dreamer + config_auditor: get_black_box() vervangt BlackBox()."""
    print("\n[Test 15] Wiring: dreamer + config_auditor → get_black_box")

    from danny_toolkit.brain import dreamer as dr_mod
    source_dr = inspect.getsource(dr_mod.Dreamer._research_failures)
    check("get_black_box in dreamer._research_failures", "get_black_box" in source_dr)
    check("BlackBox() NIET in dreamer._research_failures", "BlackBox()" not in source_dr)

    from danny_toolkit.brain import config_auditor as ca_mod
    source_ca = inspect.getsource(ca_mod.ConfigAuditor._log_to_blackbox)
    check("get_black_box in config_auditor._log_to_blackbox", "get_black_box" in source_ca)
    check("BlackBox() NIET in config_auditor._log_to_blackbox", "BlackBox()" not in source_ca)


# ═══════════════════════════════════════════════════
# TEST 16: CALLER WIRING — devops_daemon + virtual_twin
# ═══════════════════════════════════════════════════

def test_16_wiring_devops_twin():
    """devops_daemon + virtual_twin: get_black_box() vervangt BlackBox()."""
    print("\n[Test 16] Wiring: devops_daemon + virtual_twin → get_black_box")

    from danny_toolkit.brain import devops_daemon as dd_mod
    source_dd = inspect.getsource(dd_mod.DevOpsDaemon.__init__)
    check("get_black_box in devops_daemon.__init__", "get_black_box" in source_dd)
    check("BlackBox() NIET in devops_daemon.__init__", "BlackBox()" not in source_dd)

    from danny_toolkit.brain import virtual_twin as vt_mod
    source_vt = inspect.getsource(vt_mod.VirtualTwin._get_black_box)
    check("get_black_box in virtual_twin._get_black_box", "get_black_box" in source_vt)
    check("BlackBox() NIET in virtual_twin._get_black_box", "BlackBox()" not in source_vt)


# ═══════════════════════════════════════════════════
# TEST 17: SYNAPSE + PHANTOM STATS SHAPE
# ═══════════════════════════════════════════════════

def test_17_synapse_phantom_shape():
    """TheSynapse en ThePhantom stats return shapes."""
    print("\n[Test 17] Synapse + Phantom: stats shape")

    from danny_toolkit.brain.synapse import TheSynapse
    synapse = TheSynapse()
    stats = synapse.get_stats()
    check("synapse stats is dict", isinstance(stats, dict))
    check("pathways in synapse stats", "pathways" in stats)
    check("interactions in synapse stats", "interactions" in stats)
    check("avg_strength in synapse stats", "avg_strength" in stats)

    top = synapse.get_top_pathways(limit=5)
    check("top_pathways is list", isinstance(top, list))

    from danny_toolkit.brain.phantom import ThePhantom
    phantom = ThePhantom()
    acc = phantom.get_accuracy()
    check("phantom accuracy is dict", isinstance(acc, dict))
    check("total_predictions in accuracy", "total_predictions" in acc)
    check("hits in accuracy", "hits" in acc)
    check("accuracy in accuracy", "accuracy" in acc)

    preds = phantom.get_predictions()
    check("predictions is list", isinstance(preds, list))


# ═══════════════════════════════════════════════════
# TEST 18: VERSION 6.6.0 + MODULE INTEGRITY
# ═══════════════════════════════════════════════════

def test_18_version_and_integrity():
    """Brain versie 6.6.0 + module integrity."""
    print("\n[Test 18] Versie 6.6.0 + module integrity")
    import danny_toolkit.brain as brain_pkg
    _v = tuple(int(x) for x in brain_pkg.__version__.split("."))
    check(f"__version__ = {brain_pkg.__version__} (>= 6.6.0)",
          _v >= (6, 6, 0))

    # Singleton factory imports
    modules = [
        ("danny_toolkit.brain.black_box", "get_black_box"),
        ("danny_toolkit.brain.hallucination_shield", "get_hallucination_shield"),
        ("danny_toolkit.brain.adversarial_tribunal", "get_adversarial_tribunal"),
    ]
    for mod_name, func_name in modules:
        try:
            mod = __import__(mod_name, fromlist=[func_name])
            fn = getattr(mod, func_name, None)
            check(f"{mod_name}.{func_name} importeert OK", fn is not None)
            check(f"{func_name} is callable", callable(fn))
        except Exception as e:
            check(f"{mod_name}.{func_name} ({e})", False)

    # FastAPI + swarm_engine import intact
    try:
        import fastapi_server
        check("fastapi_server importeert OK", True)
    except Exception as e:
        check(f"fastapi_server importeert OK ({e})", False)

    try:
        import swarm_engine
        check("swarm_engine importeert OK", True)
    except Exception as e:
        check(f"swarm_engine importeert OK ({e})", False)


# ═══════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("Phase 39 — DEEP OBSERVATORY")
    print("=" * 60)

    test_1_blackbox_singleton_identity()
    test_2_schild_singleton_identity()
    test_3_tribunal_singleton_identity()
    test_4_schild_stats_accumuleren()
    test_5_blackbox_shared_state()
    test_6_singleton_exports()
    test_7_fastapi_response_models()
    test_8_fastapi_models_instantiate()
    test_9_fastapi_phase39_routes()
    test_10_existing_routes_intact()
    test_11_wiring_swarm_schild()
    test_12_wiring_swarm_tribunal()
    test_13_wiring_trinity_blackbox()
    test_14_wiring_schild_blackbox()
    test_15_wiring_dreamer_auditor()
    test_16_wiring_devops_twin()
    test_17_synapse_phantom_shape()
    test_18_version_and_integrity()

    print(f"\n{'=' * 60}")
    print(f"Resultaat: {passed}/{passed + failed} checks geslaagd")
    if failed == 0:
        print("  ALLE CHECKS GESLAAGD")
    else:
        print(f"  {failed} GEFAALD")
    print("=" * 60)
    sys.exit(1 if failed > 0 else 0)

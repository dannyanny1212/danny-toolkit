"""
Phase 30 Tests — SCHILD EN VRIEND: Monitoring + Anti-Hallucinatie.

18 tests, ~154 checks:
  Tests 1-7:  HallucinatieSchild
  Tests 8-12: WaakhuisMonitor
  Tests 13-18: Enhanced modules (Governor, Alerter, TruthAnchor, NeuralBus, SwarmEngine, __init__)
"""

import os
import re
import sys
import time
import threading

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


# ═══════════════════════════════════════════════════
# Tests 1-7: HallucinatieSchild
# ═══════════════════════════════════════════════════

def test_1_schild_module_exists():
    """HallucinatieSchild module importeerbaar + klasse aanwezig."""
    print("\n[Test 1] HallucinatieSchild module + klasse")
    path = os.path.join(
        PROJECT_ROOT, "danny_toolkit", "brain", "hallucination_shield.py",
    )
    check("hallucination_shield.py exists", os.path.isfile(path))

    from danny_toolkit.brain.hallucination_shield import (
        HallucinatieSchild,
        HallucinatieRapport,
        ClaimBeoordeling,
        BeoordelingNiveau,
        _bepaal_niveau,
    )
    check("HallucinatieSchild klasse importeerbaar", HallucinatieSchild is not None)
    check("HallucinatieRapport dataclass importeerbaar", HallucinatieRapport is not None)
    check("ClaimBeoordeling dataclass importeerbaar", ClaimBeoordeling is not None)
    check("BeoordelingNiveau enum importeerbaar", BeoordelingNiveau is not None)

    # Enum waarden
    check("GEVERIFIEERD in enum", BeoordelingNiveau.GEVERIFIEERD.value == "geverifieerd")
    check("WAARSCHIJNLIJK in enum", BeoordelingNiveau.WAARSCHIJNLIJK.value == "waarschijnlijk")
    check("ONZEKER in enum", BeoordelingNiveau.ONZEKER.value == "onzeker")
    check("VERDACHT in enum", BeoordelingNiveau.VERDACHT.value == "verdacht")

    # Niveau bepaling
    check("_bepaal_niveau(0.80) = GEVERIFIEERD",
          _bepaal_niveau(0.80) == BeoordelingNiveau.GEVERIFIEERD)
    check("_bepaal_niveau(0.55) = WAARSCHIJNLIJK",
          _bepaal_niveau(0.55) == BeoordelingNiveau.WAARSCHIJNLIJK)
    check("_bepaal_niveau(0.35) = ONZEKER",
          _bepaal_niveau(0.35) == BeoordelingNiveau.ONZEKER)
    check("_bepaal_niveau(0.20) = VERDACHT",
          _bepaal_niveau(0.20) == BeoordelingNiveau.VERDACHT)


def test_2_schild_drempels():
    """HallucinatieSchild drempels en gewichten."""
    print("\n[Test 2] Schild drempels en gewichten")
    from danny_toolkit.brain.hallucination_shield import HallucinatieSchild

    schild = HallucinatieSchild()
    check("BLOKKADE_DREMPEL = 0.35", schild.BLOKKADE_DREMPEL == 0.35)
    check("WAARSCHUWING_DREMPEL = 0.55", schild.WAARSCHUWING_DREMPEL == 0.55)
    check("GEWICHT_TRUTH_ANCHOR = 0.40", schild.GEWICHT_TRUTH_ANCHOR == 0.40)
    check("GEWICHT_TRIBUNAL = 0.35", schild.GEWICHT_TRIBUNAL == 0.35)
    check("GEWICHT_REGELCHECK = 0.25", schild.GEWICHT_REGELCHECK == 0.25)
    check("Gewichten sommeren ~1.0",
          abs(schild.GEWICHT_TRUTH_ANCHOR + schild.GEWICHT_TRIBUNAL + schild.GEWICHT_REGELCHECK - 1.0) < 0.01)


def test_3_schild_beoordeel_hoge_score():
    """Beoordeling met context docs -> hoge score -> doorgelaten."""
    print("\n[Test 3] Schild beoordeel: hoge score (doorgelaten)")
    from danny_toolkit.brain.hallucination_shield import HallucinatieSchild, HallucinatieRapport

    # Mock payload
    class MockPayload:
        def __init__(self, agent, text):
            self.agent = agent
            self.type = "text"
            self.display_text = text
            self.content = text
            self.metadata = {}

    schild = HallucinatieSchild()
    payloads = [
        MockPayload("CentralBrain", "Python is een programmeertaal die veel wordt gebruikt voor data science."),
    ]
    context_docs = [
        "Python is een populaire programmeertaal voor data science en machine learning.",
    ]

    rapport = schild.beoordeel(
        payloads, "Wat is Python?",
        context_docs=context_docs,
        truth_anchor_score=0.8,
        tribunal_gevalideerd=True,
    )

    check("rapport is HallucinatieRapport", isinstance(rapport, HallucinatieRapport))
    check("rapport.totaal_score > 0", rapport.totaal_score > 0)
    check("rapport.geblokkeerd is False", rapport.geblokkeerd is False)
    check("rapport.reden_blokkade is leeg", rapport.reden_blokkade == "")
    check("claims geëxtraheerd", len(rapport.claims) > 0)
    check("tijdstip is recent", abs(rapport.tijdstip - time.time()) < 5)


def test_4_schild_beoordeel_blokkade():
    """Beoordeling met lage scores -> blokkade."""
    print("\n[Test 4] Schild beoordeel: lage score (geblokkeerd)")
    from danny_toolkit.brain.hallucination_shield import HallucinatieSchild

    class MockPayload:
        def __init__(self, agent, text):
            self.agent = agent
            self.type = "text"
            self.display_text = text
            self.content = text
            self.metadata = {}

    schild = HallucinatieSchild()
    payloads = [
        MockPayload("CentralBrain", "De kat heeft 150% succes bij het vangen van sterren in 2090."),
    ]

    rapport = schild.beoordeel(
        payloads, "Vertel me iets",
        context_docs=["Katten zijn huisdieren die muizen vangen."],
        truth_anchor_score=0.1,
        tribunal_gevalideerd=False,
    )

    check("rapport.totaal_score < BLOKKADE_DREMPEL",
          rapport.totaal_score < schild.BLOKKADE_DREMPEL)
    check("rapport.geblokkeerd is True", rapport.geblokkeerd is True)
    check("reden_blokkade bevat score", "score" in rapport.reden_blokkade.lower() or
          "blokkade" in rapport.reden_blokkade.lower())


def test_5_schild_contradicties():
    """Contradictie detectie tussen agents."""
    print("\n[Test 5] Schild contradictie detectie")
    from danny_toolkit.brain.hallucination_shield import HallucinatieSchild

    schild = HallucinatieSchild()

    # Negatie contradictie test
    claims = [
        ("AgentA", "Python is de beste programmeertaal voor webontwikkeling en data science."),
        ("AgentB", "Python is niet de beste programmeertaal voor webontwikkeling."),
    ]
    contradicties = schild._detecteer_contradicties(claims)
    check("Negatie contradictie gedetecteerd", len(contradicties) > 0)

    # Numerieke divergentie test
    claims_num = [
        ("AgentA", "Het project heeft 1000 sterren op GitHub vanwege populariteit."),
        ("AgentB", "Het project heeft 100 sterren op GitHub vanwege beperkt gebruik."),
    ]
    contradicties_num = schild._detecteer_contradicties(claims_num)
    check("Numerieke divergentie gedetecteerd", len(contradicties_num) > 0)

    # Geen contradictie bij 1 agent
    claims_solo = [("AgentA", "Tekst een."), ("AgentA", "Tekst twee.")]
    check("Geen contradictie bij 1 agent",
          len(schild._detecteer_contradicties(claims_solo)) == 0)

    # Geen contradictie bij <2 claims
    check("Geen contradictie bij <2 claims",
          len(schild._detecteer_contradicties([("A", "test")])) == 0)


def test_6_schild_regelcheck():
    """Regelcheck: percentage>100, toekomstige datums, zekerheidswoorden."""
    print("\n[Test 6] Schild regelcheck")
    from danny_toolkit.brain.hallucination_shield import HallucinatieSchild

    schild = HallucinatieSchild()

    # Percentage > 100%
    problemen_pct = schild._regelcheck("Dit heeft een 250% slagingspercentage.")
    check("Percentage >100 gedetecteerd", len(problemen_pct) > 0)
    check("Percentage melding bevat 250", any("250" in p for p in problemen_pct))

    # Toekomstige datum
    problemen_date = schild._regelcheck("In 2099 zal dit gebeuren.")
    check("Toekomstige datum gedetecteerd", len(problemen_date) > 0)

    # Zekerheidswoorden
    problemen_zeker = schild._regelcheck("Dit is absoluut zeker waar.")
    check("Zekerheidswoord gedetecteerd", len(problemen_zeker) > 0)

    # Normaal geval -> geen problemen
    problemen_ok = schild._regelcheck("Python is een programmeertaal.")
    check("Geen problemen bij normale tekst", len(problemen_ok) == 0)


def test_7_schild_stats_en_rapport():
    """Stats tracking en to_dict serialisatie."""
    print("\n[Test 7] Schild stats en rapport serialisatie")
    from danny_toolkit.brain.hallucination_shield import HallucinatieSchild, HallucinatieRapport

    schild = HallucinatieSchild()
    schild.reset_stats()

    stats = schild.get_stats()
    check("stats is dict", isinstance(stats, dict))
    check("beoordeeld in stats", "beoordeeld" in stats)
    check("geblokkeerd in stats", "geblokkeerd" in stats)
    check("waarschuwingen in stats", "waarschuwingen" in stats)
    check("doorgelaten in stats", "doorgelaten" in stats)
    check("alle stats op 0 na reset", all(v == 0 for v in stats.values()))

    # to_dict op rapport
    rapport = HallucinatieRapport(totaal_score=0.75)
    d = rapport.to_dict()
    check("to_dict heeft totaal_score", "totaal_score" in d)
    check("to_dict heeft geblokkeerd", "geblokkeerd" in d)
    check("to_dict heeft tijdstip", "tijdstip" in d)
    check("to_dict score correct", d["totaal_score"] == 0.75)


# ═══════════════════════════════════════════════════
# Tests 8-12: WaakhuisMonitor
# ═══════════════════════════════════════════════════

def test_8_waakhuis_module_exists():
    """WaakhuisMonitor module + singleton."""
    print("\n[Test 8] WaakhuisMonitor module + singleton")
    path = os.path.join(
        PROJECT_ROOT, "danny_toolkit", "brain", "waakhuis.py",
    )
    check("waakhuis.py exists", os.path.isfile(path))

    from danny_toolkit.brain.waakhuis import WaakhuisMonitor, get_waakhuis
    check("WaakhuisMonitor importeerbaar", WaakhuisMonitor is not None)
    check("get_waakhuis importeerbaar", callable(get_waakhuis))

    # Constanten
    check("HEARTBEAT_TIMEOUT = 60", WaakhuisMonitor.HEARTBEAT_TIMEOUT == 60)
    check("_MAX_LATENCIES = 500", WaakhuisMonitor._MAX_LATENCIES == 500)


def test_9_waakhuis_dispatch_en_latency():
    """Registreer dispatches en bereken latency percentiel."""
    print("\n[Test 9] Waakhuis dispatch + latency percentiel")
    from danny_toolkit.brain.waakhuis import WaakhuisMonitor

    # In-memory DB voor test
    wm = WaakhuisMonitor(db_path=":memory:")
    wm.reset_stats()

    # Registreer dispatches
    latencies = [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000]
    for lat in latencies:
        wm.registreer_dispatch("TestAgent", lat)

    check("10 dispatches geregistreerd", wm._dispatch_counts["TestAgent"] == 10)
    check("heartbeat geüpdatet", "TestAgent" in wm._heartbeats)
    check("totaal_dispatches = 10", wm._stats["totaal_dispatches"] == 10)

    # Percentiel berekening
    p50 = wm.bereken_percentiel("TestAgent", 50)
    check("p50 > 0", p50 > 0)
    check("p50 ~ mediaan (450-600)", 400 <= p50 <= 650)

    p95 = wm.bereken_percentiel("TestAgent", 95)
    check("p95 > p50", p95 > p50)
    check("p95 ~ 950", 900 <= p95 <= 1000)

    p99 = wm.bereken_percentiel("TestAgent", 99)
    check("p99 >= p95", p99 >= p95)

    # Leeg geval
    p50_leeg = wm.bereken_percentiel("GeenAgent", 50)
    check("p50 leeg = 0.0", p50_leeg == 0.0)

    # Latency rapport
    rapport = wm.latency_rapport("TestAgent")
    check("rapport heeft p50", "p50" in rapport)
    check("rapport heeft p95", "p95" in rapport)
    check("rapport heeft p99", "p99" in rapport)
    check("rapport heeft count = 10", rapport["count"] == 10)
    check("rapport heeft gem", "gem" in rapport)
    check("gem ~ 550", 500 <= rapport["gem"] <= 600)

    wm.close()


def test_10_waakhuis_fouten():
    """Registreer fouten met ernst classificatie."""
    print("\n[Test 10] Waakhuis fout registratie")
    from danny_toolkit.brain.waakhuis import WaakhuisMonitor, ERNST_CLASSIFICATIE

    wm = WaakhuisMonitor(db_path=":memory:")
    wm.reset_stats()

    # Ernst classificatie
    check("TimeoutError = voorbijgaand",
          ERNST_CLASSIFICATIE["TimeoutError"] == "voorbijgaand")
    check("ValueError = herstelbaar",
          ERNST_CLASSIFICATIE["ValueError"] == "herstelbaar")
    check("RuntimeError = kritiek",
          ERNST_CLASSIFICATIE["RuntimeError"] == "kritiek")
    check("MemoryError = kritiek",
          ERNST_CLASSIFICATIE["MemoryError"] == "kritiek")

    # Registreer fouten
    wm.registreer_fout("TestAgent", "TimeoutError", "API timeout")
    wm.registreer_fout("TestAgent", "ValueError", "Bad input")
    wm.registreer_fout("TestAgent", "TimeoutError", "Nog een timeout")

    check("totaal_fouten = 3", wm._stats["totaal_fouten"] == 3)
    check("error_counts TestAgent = 3", wm._error_counts["TestAgent"] == 3)

    # Fout rapport
    rapport = wm.fout_rapport("TestAgent")
    check("rapport heeft per_type", "per_type" in rapport)
    check("rapport heeft totaal", "totaal" in rapport)
    check("totaal = 3", rapport["totaal"] == 3)
    check("TimeoutError count = 2", rapport["per_type"].get("TimeoutError") == 2)
    check("ValueError count = 1", rapport["per_type"].get("ValueError") == 1)

    wm.close()


def test_11_waakhuis_gezondheidscore():
    """Gezondheidsscore berekening."""
    print("\n[Test 11] Waakhuis gezondheidsscore")
    from danny_toolkit.brain.waakhuis import WaakhuisMonitor

    wm = WaakhuisMonitor(db_path=":memory:")
    wm.reset_stats()

    # Geen data -> 50.0 (neutraal)
    check("Geen data = 50.0", wm.gezondheidscore("Onbekend") == 50.0)

    # Gezonde agent: veel dispatches, lage latency, geen fouten
    for i in range(50):
        wm.registreer_dispatch("GezondAgent", 200 + i * 2)  # 200-298ms

    score_gezond = wm.gezondheidscore("GezondAgent")
    check("Gezonde agent score > 60", score_gezond > 60)
    check("Gezonde agent score <= 100", score_gezond <= 100)

    # Ongezonde agent: fouten
    for i in range(5):
        wm.registreer_dispatch("ZiekAgent", 4000 + i * 100)  # 4000-4400ms
    for i in range(3):
        wm.registreer_fout("ZiekAgent", "RuntimeError", "Crash")

    score_ziek = wm.gezondheidscore("ZiekAgent")
    check("Zieke agent score < gezonde score", score_ziek < score_gezond)
    check("Zieke agent score >= 0", score_ziek >= 0)

    # Gezondheidsrapport
    rapport = wm.gezondheidsrapport()
    check("rapport heeft timestamp", "timestamp" in rapport)
    check("rapport heeft agents", "agents" in rapport)
    check("rapport heeft systeem", "systeem" in rapport)
    check("GezondAgent in rapport", "GezondAgent" in rapport["agents"])
    check("ZiekAgent in rapport", "ZiekAgent" in rapport["agents"])

    wm.close()


def test_12_waakhuis_heartbeat_en_hardware():
    """Heartbeat detectie en hardware status."""
    print("\n[Test 12] Waakhuis heartbeat + hardware")
    from danny_toolkit.brain.waakhuis import WaakhuisMonitor

    wm = WaakhuisMonitor(db_path=":memory:")
    wm.reset_stats()

    # Registreer dispatch (update heartbeat)
    wm.registreer_dispatch("ActiefAgent", 100)

    # Heartbeat check — recent agent is niet stale
    stale = wm.check_heartbeats()
    check("Actieve agent niet stale", "ActiefAgent" not in stale)

    # Forceer stale heartbeat
    wm._heartbeats["OudeAgent"] = time.time() - 120  # 2 minuten geleden

    stale2 = wm.check_heartbeats()
    check("OudeAgent is stale", "OudeAgent" in stale2)
    check("ActiefAgent nog steeds niet stale", "ActiefAgent" not in stale2)

    # Hardware status
    hw = wm.hardware_status()
    check("hardware_status is dict", isinstance(hw, dict))
    check("cpu_percent in hardware", "cpu_percent" in hw)
    check("ram_percent in hardware", "ram_percent" in hw)

    # Get stats
    stats = wm.get_stats()
    check("stats is dict", isinstance(stats, dict))
    check("totaal_dispatches in stats", "totaal_dispatches" in stats)
    check("totaal_fouten in stats", "totaal_fouten" in stats)

    # Export dashboard
    dashboard = wm.export_dashboard()
    check("dashboard heeft gezondheid", "gezondheid" in dashboard)
    check("dashboard heeft hardware", "hardware" in dashboard)
    check("dashboard heeft stale_agents", "stale_agents" in dashboard)

    # Opruimen (geen fout)
    wm.opruimen(dagen=0)  # verwijder alles
    check("opruimen geeft geen fout", True)

    # Reset
    wm.reset_stats()
    check("reset_stats werkt", wm._stats["totaal_dispatches"] == 0)

    wm.close()


# ═══════════════════════════════════════════════════
# Tests 13-18: Enhanced modules
# ═══════════════════════════════════════════════════

def test_13_governor_provider_breakers():
    """Governor: per-provider circuit breakers + fout classificatie."""
    print("\n[Test 13] Governor provider breakers")
    from danny_toolkit.brain.governor import OmegaGovernor

    gov = OmegaGovernor()

    # Provider health check (nieuw)
    check("check_provider_health bestaat", hasattr(gov, "check_provider_health"))
    check("record_provider_failure bestaat", hasattr(gov, "record_provider_failure"))
    check("record_provider_success bestaat", hasattr(gov, "record_provider_success"))
    check("classificeer_fout bestaat", hasattr(gov, "classificeer_fout"))

    # Provider health — geen failures
    gezond = gov.check_provider_health("test_provider")
    check("Nieuw provider is gezond", gezond is True)

    # Record failure
    gov.record_provider_failure("test_provider")
    check("1 failure -> nog gezond", gov.check_provider_health("test_provider") is True)

    # Record success (reset)
    gov.record_provider_success("test_provider")
    check("Success reset -> gezond", gov.check_provider_health("test_provider") is True)

    # Fout classificatie
    from danny_toolkit.brain.governor import OmegaGovernor
    cls_timeout = gov.classificeer_fout(TimeoutError("test"))
    check("TimeoutError classificatie is string", isinstance(cls_timeout, str))

    cls_value = gov.classificeer_fout(ValueError("test"))
    check("ValueError classificatie is string", isinstance(cls_value, str))

    cls_runtime = gov.classificeer_fout(RuntimeError("test"))
    check("RuntimeError classificatie is string", isinstance(cls_runtime, str))

    # _FOUT_CLASSIFICATIE dict bestaat
    check("_FOUT_CLASSIFICATIE is dict", isinstance(OmegaGovernor._FOUT_CLASSIFICATIE, dict))
    check("_FOUT_CLASSIFICATIE heeft entries", len(OmegaGovernor._FOUT_CLASSIFICATIE) > 0)


def test_14_alerter_escalatie():
    """Alerter: escalatie mechanisme."""
    print("\n[Test 14] Alerter escalatie")
    from danny_toolkit.core.alerter import Alerter, AlertLevel

    alerter = Alerter()

    # Escalatie constanten
    check("ESCALATIE_VENSTER = 600", alerter.ESCALATIE_VENSTER == 600)
    check("ESCALATIE_DREMPEL = 3", alerter.ESCALATIE_DREMPEL == 3)

    # _check_escalatie methode
    check("_check_escalatie bestaat", hasattr(alerter, "_check_escalatie"))

    # _escalatie_log
    check("_escalatie_log bestaat", hasattr(alerter, "_escalatie_log"))
    check("_escalatie_log is dict", isinstance(alerter._escalatie_log, dict))

    # Test escalatie: 3x zelfde alert -> verhoogd
    for _ in range(3):
        niveau = alerter._check_escalatie("test_alert_key", AlertLevel.INFO)
    check("Na 3x zelfde alert: escalatie", niveau != AlertLevel.INFO)


def test_15_truth_anchor_tuple():
    """TruthAnchor verify() retourneert (bool, float) tuple."""
    print("\n[Test 15] TruthAnchor tuple return")
    from unittest.mock import patch, MagicMock

    mock_model = MagicMock()

    with patch("danny_toolkit.brain.truth_anchor.CrossEncoder", return_value=mock_model):
        from danny_toolkit.brain.truth_anchor import TruthAnchor
        anchor = TruthAnchor()

        # Hoge score
        mock_model.predict.return_value = [0.8]
        result = anchor.verify("Test answer", ["Test context document"])
        check("verify retourneert tuple", isinstance(result, tuple))
        check("tuple lengte = 2", len(result) == 2)
        grounded, score = result
        check("grounded is bool", isinstance(grounded, bool))
        check("score is float", isinstance(score, float))
        check("hoge score -> grounded=True", grounded is True)
        check("score = 0.8", abs(score - 0.8) < 0.01)

        # Lage score
        mock_model.predict.return_value = [0.2]
        grounded_low, score_low = anchor.verify("Test", ["Other context"])
        check("lage score -> grounded=False", grounded_low is False)
        check("score_low = 0.2", abs(score_low - 0.2) < 0.01)

        # Lege context
        grounded_empty, score_empty = anchor.verify("Test", [])
        check("lege context -> grounded=False", grounded_empty is False)
        check("lege context -> score=0.0", score_empty == 0.0)

        # DEFAULT_DREMPEL
        check("DEFAULT_DREMPEL = 0.45", TruthAnchor.DEFAULT_DREMPEL == 0.45)

        # Custom drempel
        anchor2 = TruthAnchor(drempel=0.7)
        check("Custom drempel = 0.7", anchor2.drempel == 0.7)
        mock_model.predict.return_value = [0.6]
        grounded_custom, _ = anchor2.verify("Test", ["Context"])
        check("0.6 < drempel 0.7 -> niet grounded", grounded_custom is False)


def test_16_neural_bus_event_types():
    """NeuralBus: Phase 30 EventTypes aanwezig."""
    print("\n[Test 16] NeuralBus Phase 30 EventTypes")
    from danny_toolkit.core.neural_bus import EventTypes

    check("HALLUCINATION_BLOCKED bestaat",
          hasattr(EventTypes, "HALLUCINATION_BLOCKED"))
    check("WAAKHUIS_ALERT bestaat",
          hasattr(EventTypes, "WAAKHUIS_ALERT"))
    check("WAAKHUIS_HEALTH bestaat",
          hasattr(EventTypes, "WAAKHUIS_HEALTH"))
    check("ERROR_ESCALATED bestaat",
          hasattr(EventTypes, "ERROR_ESCALATED"))

    # Waarden
    check("HALLUCINATION_BLOCKED waarde",
          EventTypes.HALLUCINATION_BLOCKED == "hallucination_blocked")
    check("WAAKHUIS_ALERT waarde",
          EventTypes.WAAKHUIS_ALERT == "waakhuis_alert")
    check("WAAKHUIS_HEALTH waarde",
          EventTypes.WAAKHUIS_HEALTH == "waakhuis_health")
    check("ERROR_ESCALATED waarde",
          EventTypes.ERROR_ESCALATED == "error_escalated")


def test_17_swarm_engine_wiring():
    """SwarmEngine: schild_blocks metric + HallucinatieSchild in pipeline."""
    print("\n[Test 17] SwarmEngine wiring")

    # Check source code for wiring
    se_path = os.path.join(PROJECT_ROOT, "swarm_engine.py")
    with open(se_path, "r", encoding="utf-8") as f:
        source = f.read()

    # 9a: schild_blocks metric
    check("schild_blocks in _swarm_metrics", '"schild_blocks"' in source)

    # 9b: Waakhuis in _timed_dispatch
    check("get_waakhuis in _timed_dispatch (dispatch)",
          "get_waakhuis().registreer_dispatch" in source)
    check("get_waakhuis in _timed_dispatch (fout)",
          "get_waakhuis().registreer_fout" in source)

    # 9c: Tribunal timeout
    check("asyncio.wait_for in _tribunal_verify",
          "asyncio.wait_for" in source)
    check("timeout=30.0 in tribunal",
          "timeout=30.0" in source)
    check("asyncio.TimeoutError handler",
          "asyncio.TimeoutError" in source)

    # 9d: HallucinatieSchild wiring
    check("HallucinatieSchild import in swarm",
          "from danny_toolkit.brain.hallucination_shield import" in source)
    check("schild.beoordeel in pipeline",
          "schild.beoordeel" in source or "schild_rapport" in source)
    check("schild_blocks increment",
          'schild_blocks' in source)
    check("SCHILD in log output",
          "SCHILD" in source)


def test_18_init_exports():
    """__init__.py: Phase 30 exports + versie."""
    print("\n[Test 18] __init__.py exports + versie")
    import danny_toolkit.brain as brain_mod

    check("__version__ = 6.1.0", brain_mod.__version__ == "6.1.0")

    # Controleer exports in __all__
    check("HallucinatieSchild in __all__",
          "HallucinatieSchild" in brain_mod.__all__)
    check("WaakhuisMonitor in __all__",
          "WaakhuisMonitor" in brain_mod.__all__)
    check("get_waakhuis in __all__",
          "get_waakhuis" in brain_mod.__all__)

    # Importeerbaar via package
    check("HallucinatieSchild importeerbaar",
          hasattr(brain_mod, "HallucinatieSchild"))
    check("WaakhuisMonitor importeerbaar",
          hasattr(brain_mod, "WaakhuisMonitor"))
    check("get_waakhuis importeerbaar",
          hasattr(brain_mod, "get_waakhuis"))

    # run_all_tests.py updated
    rat_path = os.path.join(PROJECT_ROOT, "run_all_tests.py")
    with open(rat_path, "r", encoding="utf-8") as f:
        rat_source = f.read()
    check("run_all_tests: 27 suites docstring", "27 test suites" in rat_source)
    check("run_all_tests: test_phase30.py entry",
          "test_phase30.py" in rat_source)


# ─── Run All ───

if __name__ == "__main__":
    print("=" * 60)
    print("  Phase 30: SCHILD EN VRIEND")
    print("  Monitoring + Anti-Hallucinatie")
    print("=" * 60)

    test_1_schild_module_exists()
    test_2_schild_drempels()
    test_3_schild_beoordeel_hoge_score()
    test_4_schild_beoordeel_blokkade()
    test_5_schild_contradicties()
    test_6_schild_regelcheck()
    test_7_schild_stats_en_rapport()
    test_8_waakhuis_module_exists()
    test_9_waakhuis_dispatch_en_latency()
    test_10_waakhuis_fouten()
    test_11_waakhuis_gezondheidscore()
    test_12_waakhuis_heartbeat_en_hardware()
    test_13_governor_provider_breakers()
    test_14_alerter_escalatie()
    test_15_truth_anchor_tuple()
    test_16_neural_bus_event_types()
    test_17_swarm_engine_wiring()
    test_18_init_exports()

    print(f"\n{'=' * 60}")
    total = passed + failed
    print(f"  Phase 30: {passed}/{total} checks passed")
    if failed:
        print(f"  {failed} FAILED")
    else:
        print("  ALL PASSED")
    print(f"{'=' * 60}")

    sys.exit(1 if failed else 0)

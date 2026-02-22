"""
Tests voor SingularityEngine v1.1 — 22 tests.

Draai: python test_singularity.py
"""

import os
import sys
import time
from unittest.mock import MagicMock, patch

# Test-mode env
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "-1")
os.environ.setdefault("DANNY_TEST_MODE", "1")
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")


# ── Helpers ──

geslaagd = 0
gefaald = 0


def test(naam, expressie):
    """Voer een enkele test uit."""
    global geslaagd, gefaald
    if expressie:
        print(f"  [OK] {naam}")
        geslaagd += 1
    else:
        print(f"  [FOUT] {naam}")
        gefaald += 1


# ── Test 1: Import SingularityEngine ──

def test_01_import():
    """Test dat SingularityEngine importeerbaar is."""
    from danny_toolkit.brain.singularity import (
        SingularityEngine,
    )
    test(
        "SingularityEngine importeerbaar",
        SingularityEngine is not None,
    )


# ── Test 2: Import BewustzijnModus ──

def test_02_bewustzijn_modus():
    """Test BewustzijnModus enum waarden."""
    from danny_toolkit.brain.singularity import (
        BewustzijnModus,
    )
    test(
        "BewustzijnModus.SLAAP",
        BewustzijnModus.SLAAP.value == "slaap",
    )
    test(
        "BewustzijnModus.WAAK",
        BewustzijnModus.WAAK.value == "waak",
    )
    test(
        "BewustzijnModus.DROOM",
        BewustzijnModus.DROOM.value == "droom",
    )
    test(
        "BewustzijnModus.FOCUS",
        BewustzijnModus.FOCUS.value == "focus",
    )
    test(
        "BewustzijnModus.TRANSCEND",
        BewustzijnModus.TRANSCEND.value == "transcend",
    )


# ── Test 3: CosmicRole ANIMA/SYNTHESIS/EVOLUTION ──

def test_03_cosmic_roles():
    """Test nieuwe CosmicRole waarden."""
    from danny_toolkit.brain.trinity_omega import (
        CosmicRole,
    )
    test(
        "CosmicRole.ANIMA exists",
        CosmicRole.ANIMA.value == "consciousness_core",
    )
    test(
        "CosmicRole.SYNTHESIS exists",
        CosmicRole.SYNTHESIS.value == "cross_tier_merge",
    )
    test(
        "CosmicRole.EVOLUTION exists",
        CosmicRole.EVOLUTION.value == "self_evolution",
    )


# ── Test 4: NodeTier SINGULARITY ──

def test_04_node_tier():
    """Test NodeTier.SINGULARITY."""
    from danny_toolkit.brain.trinity_omega import (
        NodeTier,
    )
    test(
        "NodeTier.SINGULARITY exists",
        NodeTier.SINGULARITY.value == "SINGULARITY",
    )


# ── Test 5: get_tier() retourneert 5 ──

def test_05_get_tier():
    """Test get_tier() voor Tier 5 rollen."""
    from danny_toolkit.brain.trinity_omega import (
        CosmicRole,
    )
    test(
        "ANIMA tier = 5",
        CosmicRole.get_tier(CosmicRole.ANIMA) == 5,
    )
    test(
        "SYNTHESIS tier = 5",
        CosmicRole.get_tier(CosmicRole.SYNTHESIS) == 5,
    )
    test(
        "EVOLUTION tier = 5",
        CosmicRole.get_tier(CosmicRole.EVOLUTION) == 5,
    )


# ── Test 6: Backward compat bestaande tiers ──

def test_06_backward_compat_tiers():
    """Test dat bestaande tiers ongewijzigd zijn."""
    from danny_toolkit.brain.trinity_omega import (
        CosmicRole,
    )
    test(
        "PIXEL still tier 1",
        CosmicRole.get_tier(CosmicRole.PIXEL) == 1,
    )
    test(
        "GOVERNOR still tier 2",
        CosmicRole.get_tier(CosmicRole.GOVERNOR) == 2,
    )
    test(
        "WEAVER still tier 3",
        CosmicRole.get_tier(CosmicRole.WEAVER) == 3,
    )
    test(
        "LEGION still tier 4",
        CosmicRole.get_tier(CosmicRole.LEGION) == 4,
    )


# ── Test 7: Constructor default waarden ──

def test_07_constructor():
    """Test SingularityEngine constructor."""
    from danny_toolkit.brain.singularity import (
        SingularityEngine, BewustzijnModus,
    )
    engine = SingularityEngine()
    test(
        "Standaard modus = WAAK",
        engine._modus == BewustzijnModus.WAAK,
    )
    test(
        "Score begint op 0.0",
        engine._bewustzijn_score == 0.0,
    )
    test(
        "Dromen lijst leeg",
        len(engine._dromen) == 0,
    )
    test(
        "Inzichten lijst leeg",
        len(engine._inzichten) == 0,
    )
    test(
        "Synthese log leeg",
        len(engine._synthese_log) == 0,
    )


# ── Test 8: Score berekening ──

def test_08_score():
    """Test bewustzijn score berekening."""
    from danny_toolkit.brain.singularity import (
        SingularityEngine,
    )
    engine = SingularityEngine()
    engine._bereken_bewustzijn_score()
    test(
        "Score >= 0.0",
        engine._bewustzijn_score >= 0.0,
    )
    test(
        "Score <= 1.0",
        engine._bewustzijn_score <= 1.0,
    )


# ── Test 9: Modus bepaling overdag ──

def test_09_modus_bepaling():
    """Test _bepaal_modus() logica."""
    from danny_toolkit.brain.singularity import (
        SingularityEngine, BewustzijnModus,
    )
    engine = SingularityEngine()
    modus = engine._bepaal_modus()
    # Overdag (6:00-23:00) moet WAAK zijn
    # (tenzij nacht bij het draaien)
    uur = time.localtime().tm_hour
    if 6 <= uur < 23:
        test(
            "Overdag modus = WAAK",
            modus == BewustzijnModus.WAAK,
        )
    else:
        test(
            "Nacht modus = SLAAP",
            modus == BewustzijnModus.SLAAP,
        )


# ── Test 10: Droom rate limiet ──

def test_10_droom_limiet():
    """Test droom rate limiting."""
    from danny_toolkit.brain.singularity import (
        SingularityEngine,
    )
    engine = SingularityEngine()
    test(
        "Droom limiet begint True",
        engine._check_droom_limiet() is True,
    )
    engine._dromen_dit_uur = 6
    test(
        "Droom limiet na 6 = False",
        engine._check_droom_limiet() is False,
    )


# ── Test 11: Inzicht rate limiet ──

def test_11_inzicht_limiet():
    """Test inzicht rate limiting."""
    from danny_toolkit.brain.singularity import (
        SingularityEngine,
    )
    engine = SingularityEngine()
    test(
        "Inzicht limiet begint True",
        engine._check_inzicht_limiet() is True,
    )
    engine._inzichten_vandaag = 50
    test(
        "Inzicht limiet na 50 = False",
        engine._check_inzicht_limiet() is False,
    )


# ── Test 12: get_status() dict ──

def test_12_get_status():
    """Test get_status() retour dict."""
    from danny_toolkit.brain.singularity import (
        SingularityEngine,
    )
    engine = SingularityEngine()
    status = engine.get_status()
    test(
        "status heeft 'modus'",
        "modus" in status,
    )
    test(
        "status heeft 'bewustzijn_score'",
        "bewustzijn_score" in status,
    )
    test(
        "status heeft 'versie'",
        status["versie"] == "1.1.0",
    )
    test(
        "status heeft 'actief'",
        status["actief"] is True,
    )


# ── Test 13: TRANSCEND activatie ──

def test_13_transcend():
    """Test activeer_transcend() en deactiveer."""
    from danny_toolkit.brain.singularity import (
        SingularityEngine, BewustzijnModus,
    )
    engine = SingularityEngine()
    engine.activeer_transcend()
    test(
        "TRANSCEND geactiveerd",
        engine._modus == BewustzijnModus.TRANSCEND,
    )
    engine.deactiveer_transcend()
    test(
        "Terug naar WAAK",
        engine._modus == BewustzijnModus.WAAK,
    )


# ── Test 14: Stop functionaliteit ──

def test_14_stop():
    """Test stop() graceful shutdown."""
    from danny_toolkit.brain.singularity import (
        SingularityEngine,
    )
    engine = SingularityEngine()
    engine.stop()
    test(
        "Stop event gezet",
        engine._stop.is_set(),
    )
    test(
        "Status actief = False",
        engine.get_status()["actief"] is False,
    )


# ── Test 15: Tick zonder crash ──

def test_15_tick():
    """Test tick() draait zonder fouten."""
    from danny_toolkit.brain.singularity import (
        SingularityEngine,
    )
    engine = SingularityEngine()
    try:
        engine.tick()
        test("tick() zonder crash", True)
    except Exception as e:
        test(f"tick() crash: {e}", False)


# ── Test 16: Backward compat 17 originele rollen ──

def test_16_backward_compat_roles():
    """Test dat alle 17 originele CosmicRole waarden werken."""
    from danny_toolkit.brain.trinity_omega import (
        CosmicRole,
    )
    originele = [
        "PIXEL", "IOLAAX", "NEXUS",
        "GOVERNOR", "SENTINEL", "ARCHIVIST", "CHRONOS",
        "WEAVER", "CIPHER", "VITA", "ECHO", "SPARK",
        "ORACLE",
        "LEGION", "NAVIGATOR", "ALCHEMIST", "VOID",
    ]
    alle_ok = True
    for naam in originele:
        try:
            role = CosmicRole[naam]
            tier = CosmicRole.get_tier(role)
            if tier not in (1, 2, 3, 4):
                alle_ok = False
        except KeyError:
            alle_ok = False
    test(
        "Alle 17 originele rollen intact",
        alle_ok,
    )


# ── Test 17: Totaal 20 CosmicRole waarden ──

def test_17_totaal_rollen():
    """Test dat er nu 20 CosmicRole waarden zijn."""
    from danny_toolkit.brain.trinity_omega import (
        CosmicRole,
    )
    alle_rollen = list(CosmicRole)
    test(
        f"Totaal rollen = 20 (was 17 + 3 nieuw)",
        len(alle_rollen) == 20,
    )


# ── Test 18: Nachtwacht datum guard ──

def test_18_nachtwacht_guard():
    """Test dat _nachtwacht_datum guard werkt."""
    from danny_toolkit.brain.singularity import (
        SingularityEngine,
    )
    engine = SingularityEngine()

    # Eerste keer: datum is None, moet draaien
    test(
        "Nachtwacht datum begint None",
        engine._nachtwacht_datum is None,
    )

    # Simuleer dat nachtwacht al gedraaid is
    from datetime import datetime
    vandaag = datetime.now().strftime("%Y-%m-%d")
    engine._nachtwacht_datum = vandaag

    # Log tellen voor en na
    log_voor = len(engine._nachtwacht_log)
    engine._nachtwacht_cyclus()
    log_na = len(engine._nachtwacht_log)
    test(
        "Nachtwacht skip bij herhaling",
        log_voor == log_na,
    )


# ── Test 19: Nachtwacht consolideer ──

def test_19_nachtwacht_consolideer():
    """Test _nachtwacht_consolideer() retourneert dict."""
    from danny_toolkit.brain.singularity import (
        SingularityEngine,
    )
    engine = SingularityEngine()

    # Zonder stack: moet leeg dict retourneren
    result = engine._nachtwacht_consolideer(
        "2026-01-01"
    )
    test(
        "Consolideer retourneert dict",
        isinstance(result, dict),
    )
    test(
        "Consolideer heeft events_verwerkt",
        "events_verwerkt" in result,
    )
    test(
        "Consolideer heeft actors",
        "actors" in result,
    )
    test(
        "Consolideer heeft stats_verwerkt",
        "stats_verwerkt" in result,
    )


# ── Test 20: Nachtwacht tuner ──

def test_20_nachtwacht_tuner():
    """Test _nachtwacht_tuner() past DREMPEL aan."""
    from danny_toolkit.brain.singularity import (
        SingularityEngine,
    )
    engine = SingularityEngine()
    result = engine._nachtwacht_tuner()
    test(
        "Tuner retourneert dict",
        isinstance(result, dict),
    )
    test(
        "Tuner heeft oude_drempel",
        "oude_drempel" in result,
    )
    test(
        "Tuner heeft nieuwe_drempel",
        "nieuwe_drempel" in result,
    )
    test(
        "Tuner heeft reden",
        "reden" in result,
    )

    # Check grenzen
    try:
        from swarm_engine import AdaptiveRouter
        drempel = AdaptiveRouter.DREMPEL
        test(
            "DREMPEL >= MIN",
            drempel >= engine.NACHTWACHT_DREMPEL_MIN,
        )
        test(
            "DREMPEL <= MAX",
            drempel <= engine.NACHTWACHT_DREMPEL_MAX,
        )
    except ImportError:
        test("DREMPEL grenzen (skip: geen router)", True)
        test("DREMPEL grenzen (skip: geen router)", True)


# ── Test 21: Nachtwacht voorspeller ──

def test_21_nachtwacht_voorspeller():
    """Test _nachtwacht_voorspeller() vindt patronen."""
    from danny_toolkit.brain.singularity import (
        SingularityEngine,
    )
    engine = SingularityEngine()

    # Zonder stack: moet leeg resultaat geven
    result = engine._nachtwacht_voorspeller(
        "2026-02-10"
    )
    test(
        "Voorspeller retourneert dict",
        isinstance(result, dict),
    )
    test(
        "Voorspeller heeft patronen_gevonden",
        "patronen_gevonden" in result,
    )
    test(
        "Voorspeller heeft regels_toegevoegd",
        "regels_toegevoegd" in result,
    )
    test(
        "Zonder stack: 0 patronen",
        result["patronen_gevonden"] == 0,
    )


# ── Test 22: get_status bevat nachtwacht velden ──

def test_22_status_nachtwacht():
    """Test get_status() bevat nachtwacht velden."""
    from danny_toolkit.brain.singularity import (
        SingularityEngine,
    )
    engine = SingularityEngine()
    status = engine.get_status()
    test(
        "status heeft nachtwacht_datum",
        "nachtwacht_datum" in status,
    )
    test(
        "status heeft nachtwacht_log",
        "nachtwacht_log" in status,
    )
    test(
        "nachtwacht_datum is None bij start",
        status["nachtwacht_datum"] is None,
    )
    test(
        "nachtwacht_log is 0 bij start",
        status["nachtwacht_log"] == 0,
    )


# ── Main ──

def main():
    """Draai alle 22 test suites."""
    print()
    print("=" * 55)
    print("  SINGULARITY ENGINE TESTS — 22 suites")
    print("=" * 55)
    print()

    test_01_import()
    test_02_bewustzijn_modus()
    test_03_cosmic_roles()
    test_04_node_tier()
    test_05_get_tier()
    test_06_backward_compat_tiers()
    test_07_constructor()
    test_08_score()
    test_09_modus_bepaling()
    test_10_droom_limiet()
    test_11_inzicht_limiet()
    test_12_get_status()
    test_13_transcend()
    test_14_stop()
    test_15_tick()
    test_16_backward_compat_roles()
    test_17_totaal_rollen()
    test_18_nachtwacht_guard()
    test_19_nachtwacht_consolideer()
    test_20_nachtwacht_tuner()
    test_21_nachtwacht_voorspeller()
    test_22_status_nachtwacht()

    print()
    print("=" * 55)
    totaal = geslaagd + gefaald
    if gefaald == 0:
        print(
            f"  RESULTAAT: {geslaagd}/{totaal}"
            f" GESLAAGD"
        )
    else:
        print(
            f"  RESULTAAT: {geslaagd}/{totaal}"
            f" geslaagd, {gefaald} GEFAALD"
        )
    print("=" * 55)
    print()

    return gefaald == 0


if __name__ == "__main__":
    succes = main()
    sys.exit(0 if succes else 1)

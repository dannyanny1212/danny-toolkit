"""
Tests voor ProactiveEngine v1.0.

Draai:
    python test_proactive.py
"""

import os
import sys
import time
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta

# Test-mode env
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "-1")
os.environ.setdefault("DANNY_TEST_MODE", "1")
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")


# ── Helpers ──

def _maak_mock_daemon():
    """Maak een mock DigitalDaemon."""
    daemon = MagicMock()
    daemon.sensorium = MagicMock()
    daemon.sensorium.register_listener = MagicMock()
    daemon.sensorium.detect_idle = MagicMock(
        return_value=False
    )
    daemon.sensorium.last_activity = datetime.now()
    daemon.limbic = MagicMock()
    daemon.limbic.get_status = MagicMock(
        return_value={
            "state": {
                "energy": "normal",
                "mood": "neutral",
            }
        }
    )
    return daemon


def _maak_engine(daemon=None):
    """Maak ProactiveEngine met mock daemon."""
    from danny_toolkit.brain.proactive import (
        ProactiveEngine,
    )
    if daemon is None:
        daemon = _maak_mock_daemon()
    return ProactiveEngine(daemon)


# ── Tests ──

def test_01_import():
    """Test import van ProactiveRule en ProactiveEngine."""
    from danny_toolkit.brain.proactive import (
        ProactiveRule,
        ProactiveEngine,
    )
    assert ProactiveRule is not None
    assert ProactiveEngine is not None
    print("  [OK] test_01_import")


def test_02_proactive_rule_constructie():
    """Test ProactiveRule dataclass constructie."""
    from danny_toolkit.brain.proactive import (
        ProactiveRule,
    )
    regel = ProactiveRule(
        naam="test_regel",
        conditie=lambda s: True,
        actie="melding:Test melding",
        cooldown=120,
        prioriteit=2,
        bron="timer",
    )
    assert regel.naam == "test_regel"
    assert regel.cooldown == 120
    assert regel.prioriteit == 2
    assert regel.bron == "timer"
    assert regel.conditie({}) is True
    print("  [OK] test_02_proactive_rule_constructie")


def test_03_engine_init():
    """Test ProactiveEngine initialisatie."""
    engine = _maak_engine()
    assert engine.regels is not None
    assert len(engine.regels) == 8
    assert engine._meldingen == []
    assert not engine._stop.is_set()
    print("  [OK] test_03_engine_init")


def test_04_standaard_regels():
    """Test dat alle 8 standaard regels aanwezig zijn."""
    engine = _maak_engine()
    namen = {r.naam for r in engine.regels}
    verwacht = {
        "cpu_cleanup",
        "error_repair",
        "morning_brief",
        "evening_reflect",
        "memex_ledig",
        "sentinel_alert",
        "idle_growth",
        "heartbeat_check",
    }
    assert namen == verwacht, (
        f"Verwacht {verwacht}, kreeg {namen}"
    )
    print("  [OK] test_04_standaard_regels")


def test_05_cooldown_werkt():
    """Test dat cooldown herhaalde triggers voorkomt."""
    from danny_toolkit.brain.proactive import (
        ProactiveRule,
    )
    engine = _maak_engine()

    teller = {"count": 0}

    def tel_actie(tekst):
        teller["count"] += 1

    engine._voeg_melding_toe = tel_actie

    regel = ProactiveRule(
        naam="test_cooldown",
        conditie=lambda s: True,
        actie="melding:Test",
        cooldown=3600,
        prioriteit=1,
        bron="timer",
    )
    engine.regels = [regel]

    # Eerste keer: moet triggeren
    state = {"uur": 12, "minuut": 0}
    engine._evalueer_regels(state)
    assert teller["count"] == 1

    # Tweede keer: cooldown blokkeert
    engine._evalueer_regels(state)
    assert teller["count"] == 1

    print("  [OK] test_05_cooldown_werkt")


def test_06_governor_blokkeert_bij_red():
    """Test dat Governor lage-prioriteit regels blokkeert."""
    from danny_toolkit.brain.proactive import (
        ProactiveRule,
    )
    engine = _maak_engine()

    # Mock governor met RED status
    mock_gov = MagicMock()
    mock_gov.check_api_health = MagicMock(
        return_value=False
    )
    engine._governor = mock_gov

    teller = {"count": 0}
    original_voer_uit = engine._voer_uit
    def mock_voer_uit(regel, state):
        teller["count"] += 1
        original_voer_uit(regel, state)
    engine._voer_uit = mock_voer_uit

    # Prioriteit 3 regel: moet geblokkeerd worden
    regel_laag = ProactiveRule(
        naam="test_laag",
        conditie=lambda s: True,
        actie="melding:Laag",
        cooldown=60,
        prioriteit=3,
        bron="timer",
    )

    # Prioriteit 1 regel: moet doorgaan
    regel_hoog = ProactiveRule(
        naam="test_hoog",
        conditie=lambda s: True,
        actie="melding:Hoog",
        cooldown=60,
        prioriteit=1,
        bron="timer",
    )

    engine.regels = [regel_laag, regel_hoog]

    state = {"uur": 12}
    engine._evalueer_regels(state)

    # Alleen prioriteit 1 moet getriggerd zijn
    assert teller["count"] == 1
    print("  [OK] test_06_governor_blokkeert_bij_red")


def test_07_timer_regels():
    """Test timer-gebaseerde regels."""
    from danny_toolkit.brain.proactive import (
        ProactiveRule,
    )
    engine = _maak_engine()

    now = datetime.now()
    teller = {"count": 0}

    def tel_actie(tekst):
        teller["count"] += 1

    engine._voeg_melding_toe = tel_actie

    regel = ProactiveRule(
        naam="timer_test",
        conditie=lambda s: (
            s.get("uur") == now.hour
            and s.get("minuut") == now.minute
        ),
        actie="melding:Timer!",
        cooldown=60,
        prioriteit=2,
        bron="timer",
    )
    engine.regels = [regel]

    engine._check_timer_regels()
    assert teller["count"] == 1
    print("  [OK] test_07_timer_regels")


def test_08_melding_queue():
    """Test melding toevoegen, ophalen en legen."""
    engine = _maak_engine()

    engine._voeg_melding_toe("Test melding 1")
    engine._voeg_melding_toe("Test melding 2")

    assert len(engine._meldingen) == 2

    meldingen = engine.haal_meldingen()
    assert len(meldingen) == 2
    assert "Test melding 1" in meldingen[0]
    assert "Test melding 2" in meldingen[1]

    # Queue moet nu leeg zijn
    assert len(engine._meldingen) == 0
    assert engine.haal_meldingen() == []

    print("  [OK] test_08_melding_queue")


def test_09_voeg_regel_toe():
    """Test custom regel toevoegen."""
    from danny_toolkit.brain.proactive import (
        ProactiveRule,
    )
    engine = _maak_engine()
    begin_count = len(engine.regels)

    regel = ProactiveRule(
        naam="custom",
        conditie=lambda s: True,
        actie="melding:Custom",
        cooldown=120,
    )
    engine.voeg_regel_toe(regel)
    assert len(engine.regels) == begin_count + 1

    # Cooldown te laag
    korte_regel = ProactiveRule(
        naam="kort",
        conditie=lambda s: True,
        actie="melding:Kort",
        cooldown=30,
    )
    try:
        engine.voeg_regel_toe(korte_regel)
        assert False, "Moet ValueError geven"
    except ValueError:
        pass

    print("  [OK] test_09_voeg_regel_toe")


def test_10_sensorium_event_dispatch():
    """Test dat Sensorium event → regel evaluatie werkt."""
    from danny_toolkit.brain.proactive import (
        ProactiveRule,
    )
    engine = _maak_engine()

    teller = {"count": 0}

    def tel_actie(tekst):
        teller["count"] += 1

    engine._voeg_melding_toe = tel_actie

    # Regel die altijd triggert
    regel = ProactiveRule(
        naam="event_test",
        conditie=lambda s: True,
        actie="melding:Event!",
        cooldown=60,
        prioriteit=1,
    )
    engine.regels = [regel]

    # Simuleer event
    mock_event = MagicMock()
    mock_event.type = MagicMock()
    mock_event.source = "test"
    mock_event.data = {}
    engine._on_event(mock_event)

    assert teller["count"] == 1
    print("  [OK] test_10_sensorium_event_dispatch")


def test_11_stop():
    """Test graceful stop."""
    engine = _maak_engine()
    assert not engine._stop.is_set()
    engine.stop()
    assert engine._stop.is_set()
    print("  [OK] test_11_stop")


def test_12_get_status():
    """Test engine status rapport."""
    engine = _maak_engine()
    status = engine.get_status()

    assert status["actief"] is True
    assert status["regels"] == 8
    assert status["meldingen_wachtend"] == 0
    assert status["fouten_getrackt"] == 0
    assert isinstance(status["cooldowns"], dict)

    print("  [OK] test_12_get_status")


def test_13_registreer_fout():
    """Test error tracking."""
    engine = _maak_engine()

    assert len(engine._recente_fouten) == 0
    engine.registreer_fout("TestFout1")
    engine.registreer_fout("TestFout2")
    assert len(engine._recente_fouten) == 2

    # Error repair regel triggert bij 3+ fouten
    engine.registreer_fout("TestFout3")
    state = engine._bouw_state()
    assert state["fouten_count"] == 3

    print("  [OK] test_13_registreer_fout")


def test_14_prioriteit_volgorde():
    """Test dat prioriteit 1 regels voor 3 gaan."""
    from danny_toolkit.brain.proactive import (
        ProactiveRule,
    )
    engine = _maak_engine()
    volgorde = []

    original = engine._voer_uit
    def mock_voer_uit(regel, state):
        volgorde.append(regel.naam)
        # Registreer cooldown handmatig
        engine._cooldowns[regel.naam] = time.time()

    engine._voer_uit = mock_voer_uit

    regels = [
        ProactiveRule(
            naam="laag",
            conditie=lambda s: True,
            actie="melding:Laag",
            cooldown=60,
            prioriteit=3,
        ),
        ProactiveRule(
            naam="hoog",
            conditie=lambda s: True,
            actie="melding:Hoog",
            cooldown=60,
            prioriteit=1,
        ),
        ProactiveRule(
            naam="midden",
            conditie=lambda s: True,
            actie="melding:Midden",
            cooldown=60,
            prioriteit=2,
        ),
    ]
    engine.regels = regels

    engine._evalueer_regels({"uur": 12})

    assert volgorde == ["hoog", "midden", "laag"], (
        f"Verwacht hoog→midden→laag, kreeg {volgorde}"
    )
    print("  [OK] test_14_prioriteit_volgorde")


# ── Runner ──

def main():
    """Draai alle tests."""
    tests = [
        test_01_import,
        test_02_proactive_rule_constructie,
        test_03_engine_init,
        test_04_standaard_regels,
        test_05_cooldown_werkt,
        test_06_governor_blokkeert_bij_red,
        test_07_timer_regels,
        test_08_melding_queue,
        test_09_voeg_regel_toe,
        test_10_sensorium_event_dispatch,
        test_11_stop,
        test_12_get_status,
        test_13_registreer_fout,
        test_14_prioriteit_volgorde,
    ]

    print(f"\n{'='*50}")
    print(f"  ProactiveEngine Tests — {len(tests)} suites")
    print(f"{'='*50}\n")

    geslaagd = 0
    mislukt = 0

    for test in tests:
        try:
            test()
            geslaagd += 1
        except Exception as e:
            mislukt += 1
            print(f"  [FAIL] {test.__name__}: {e}")

    print(f"\n{'='*50}")
    print(
        f"  Resultaat: {geslaagd}/{len(tests)}"
        f" geslaagd"
    )
    if mislukt:
        print(f"  {mislukt} tests MISLUKT")
    else:
        print("  ALLE TESTS GESLAAGD")
    print(f"{'='*50}\n")

    return 0 if mislukt == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

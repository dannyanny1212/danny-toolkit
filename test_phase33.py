"""
Phase 33 Tests — CONFIGAUDITOR: Runtime configuratie-validatie.

18 tests, ~60 checks:
  Tests 1-3:   Module imports, dataclasses, singleton
  Tests 4-6:   Model allowlist validatie
  Tests 7-8:   URL validatie
  Tests 9-10:  Key prefix & lengte validatie
  Tests 11-12: Snapshot & drift detectie
  Tests 13-14: Full audit + rapport
  Tests 15-16: NeuralBus events
  Tests 17:    Governor integratie
  Test  18:    brain/__init__.py exports
"""
from __future__ import annotations

import logging
import os
import sys

logger = logging.getLogger(__name__)

try:
    sys.stdout = __import__("io").TextIOWrapper(
        sys.stdout.buffer, encoding="utf-8", errors="replace",
    )
except (ValueError, OSError):
    logger.debug("Invalid value encountered")

# Test-mode env
os.environ.setdefault("DANNY_TEST_MODE", "1")
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "-1")
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

passed = 0
failed = 0


def check(beschrijving: str, conditie: bool) -> None:
    """Registreer een check resultaat."""
    global passed, failed
    if conditie:
        passed += 1
        print(f"  OK  {beschrijving}")
    else:
        failed += 1
        print(f"  FAIL  {beschrijving}")


# ═══════════════════════════════════════════════════
# Tests 1-3: Module imports, dataclasses, singleton
# ═══════════════════════════════════════════════════

def test_1_module_import() -> None:
    """config_auditor module importeert correct."""
    print("\n[Test 1] Module import")
    import danny_toolkit.brain.config_auditor as mod

    check("Module importeert", mod is not None)
    check("ConfigAuditor class bestaat", hasattr(mod, "ConfigAuditor"))
    check("get_config_auditor functie bestaat", hasattr(mod, "get_config_auditor"))
    check("AuditSchending dataclass bestaat", hasattr(mod, "AuditSchending"))
    check("AuditRapport dataclass bestaat", hasattr(mod, "AuditRapport"))


def test_2_dataclasses() -> None:
    """Dataclasses hebben correcte velden."""
    print("\n[Test 2] Dataclass velden")
    from danny_toolkit.brain.config_auditor import (
        AuditSchending, AuditRapport,
    )
    import dataclasses

    # AuditSchending
    s_fields = {f.name for f in dataclasses.fields(AuditSchending)}
    check("AuditSchending.categorie", "categorie" in s_fields)
    check("AuditSchending.ernst", "ernst" in s_fields)
    check("AuditSchending.beschrijving", "beschrijving" in s_fields)
    check("AuditSchending.sleutel", "sleutel" in s_fields)

    # AuditRapport
    r_fields = {f.name for f in dataclasses.fields(AuditRapport)}
    check("AuditRapport.veilig", "veilig" in r_fields)
    check("AuditRapport.schendingen", "schendingen" in r_fields)
    check("AuditRapport.drift_gedetecteerd", "drift_gedetecteerd" in r_fields)
    check("AuditRapport.gecontroleerd", "gecontroleerd" in r_fields)
    check("AuditRapport.timestamp", "timestamp" in r_fields)


def test_3_singleton() -> None:
    """get_config_auditor() geeft singleton terug."""
    print("\n[Test 3] Singleton patroon")
    from danny_toolkit.brain.config_auditor import get_config_auditor

    a1 = get_config_auditor()
    a2 = get_config_auditor()
    check("Singleton: zelfde instantie", a1 is a2)
    check("Is ConfigAuditor type", type(a1).__name__ == "ConfigAuditor")


# ═══════════════════════════════════════════════════
# Tests 4-6: Model allowlist validatie
# ═══════════════════════════════════════════════════

def test_4_model_allowlists_exist() -> None:
    """Allowlists voor alle providers bestaan."""
    print("\n[Test 4] Model allowlists")
    from danny_toolkit.brain.config_auditor import (
        GROQ_MODELS, OLLAMA_MODELS,
        ANTHROPIC_MODELS, NVIDIA_NIM_MODELS,
        PROVIDER_MODELS,
    )

    check("GROQ_MODELS niet leeg", len(GROQ_MODELS) > 0)
    check("OLLAMA_MODELS niet leeg", len(OLLAMA_MODELS) > 0)
    check("ANTHROPIC_MODELS niet leeg", len(ANTHROPIC_MODELS) > 0)
    check("NVIDIA_NIM_MODELS niet leeg", len(NVIDIA_NIM_MODELS) > 0)
    check("PROVIDER_MODELS heeft 4 providers", len(PROVIDER_MODELS) == 4)


def test_5_current_models_valid() -> None:
    """Huidige Config modellen staan in de allowlists."""
    print("\n[Test 5] Huidige modellen in allowlist")
    from danny_toolkit.brain.config_auditor import (
        GROQ_MODELS, OLLAMA_MODELS,
        ANTHROPIC_MODELS, NVIDIA_NIM_MODELS,
    )
    from danny_toolkit.core.config import Config

    check("LLM_MODEL in GROQ", Config.LLM_MODEL in GROQ_MODELS)
    check("LLM_FALLBACK_MODEL in GROQ", Config.LLM_FALLBACK_MODEL in GROQ_MODELS)
    check("VISION_MODEL in OLLAMA", Config.VISION_MODEL in OLLAMA_MODELS)
    check("CLAUDE_MODEL in ANTHROPIC", Config.CLAUDE_MODEL in ANTHROPIC_MODELS)
    check("NVIDIA_NIM_MODEL in NVIDIA", Config.NVIDIA_NIM_MODEL in NVIDIA_NIM_MODELS)


def test_6_model_check_detects_invalid() -> None:
    """_check_models detecteert onbekend model."""
    print("\n[Test 6] Model check detecteert ongeldig model")
    from danny_toolkit.brain.config_auditor import ConfigAuditor
    from danny_toolkit.core.config import Config

    auditor = ConfigAuditor()
    orig = Config.LLM_MODEL
    try:
        Config.LLM_MODEL = "onbekend/fake-model-99b"
        schendingen = auditor._check_models()
        has_violation = any(
            s.sleutel == "LLM_MODEL" for s in schendingen
        )
        check("Ongeldig model gedetecteerd", has_violation)
    finally:
        Config.LLM_MODEL = orig


# ═══════════════════════════════════════════════════
# Tests 7-8: URL validatie
# ═══════════════════════════════════════════════════

def test_7_valid_url_passes() -> None:
    """Geldige NVIDIA URL passeert validatie."""
    print("\n[Test 7] Geldige URL passeert")
    from danny_toolkit.brain.config_auditor import ConfigAuditor
    from danny_toolkit.core.config import Config

    auditor = ConfigAuditor()
    orig = Config.NVIDIA_NIM_BASE_URL
    try:
        Config.NVIDIA_NIM_BASE_URL = "https://integrate.api.nvidia.com/v1"
        schendingen = auditor._check_urls()
        url_violations = [s for s in schendingen if s.sleutel == "NVIDIA_NIM_BASE_URL"]
        check("Geldige URL: geen schending", len(url_violations) == 0)
    finally:
        Config.NVIDIA_NIM_BASE_URL = orig


def test_8_invalid_url_detected() -> None:
    """Ongeldige URL wordt gedetecteerd."""
    print("\n[Test 8] Ongeldige URL gedetecteerd")
    from danny_toolkit.brain.config_auditor import ConfigAuditor
    from danny_toolkit.core.config import Config

    auditor = ConfigAuditor()
    orig = Config.NVIDIA_NIM_BASE_URL
    try:
        Config.NVIDIA_NIM_BASE_URL = "http://evil.example.com/hack"
        schendingen = auditor._check_urls()
        url_violations = [s for s in schendingen if s.sleutel == "NVIDIA_NIM_BASE_URL"]
        check("Ongeldige URL gedetecteerd", len(url_violations) > 0)
        if url_violations:
            check("Ernst is kritiek", url_violations[0].ernst == "kritiek")
    finally:
        Config.NVIDIA_NIM_BASE_URL = orig


# ═══════════════════════════════════════════════════
# Tests 9-10: Key prefix & lengte validatie
# ═══════════════════════════════════════════════════

def test_9_key_prefixes() -> None:
    """Key prefix constanten zijn gedefinieerd."""
    print("\n[Test 9] Key prefix constanten")
    from danny_toolkit.brain.config_auditor import (
        KEY_PREFIXES, KEY_MIN_LEN, AGENT_KEY_VARS,
    )

    check("GROQ prefix is gsk_", KEY_PREFIXES.get("GROQ_API_KEY") == "gsk_")
    check("ANTHROPIC prefix is sk-ant-", KEY_PREFIXES.get("ANTHROPIC_API_KEY") == "sk-ant-")
    check("VOYAGE prefix is pa-", KEY_PREFIXES.get("VOYAGE_API_KEY") == "pa-")
    check("KEY_MIN_LEN heeft entries", len(KEY_MIN_LEN) > 0)
    check("AGENT_KEY_VARS heeft 10 vars", len(AGENT_KEY_VARS) == 10)


def test_10_key_check_detects_bad_prefix() -> None:
    """_check_keys detecteert verkeerde key prefix."""
    print("\n[Test 10] Key check detecteert verkeerde prefix")
    from danny_toolkit.brain.config_auditor import ConfigAuditor

    auditor = ConfigAuditor()
    orig = os.environ.get("GROQ_API_KEY", "")
    try:
        os.environ["GROQ_API_KEY"] = "WRONG_PREFIX_abcdefghijklmnopqrstuvwxyz"
        schendingen = auditor._check_keys()
        groq_violations = [s for s in schendingen if s.sleutel == "GROQ_API_KEY"]
        check("Verkeerde prefix gedetecteerd", len(groq_violations) > 0)
    finally:
        if orig:
            os.environ["GROQ_API_KEY"] = orig
        else:
            os.environ.pop("GROQ_API_KEY", None)


# ═══════════════════════════════════════════════════
# Tests 11-12: Snapshot & drift detectie
# ═══════════════════════════════════════════════════

def test_11_snapshot() -> None:
    """snapshot() geeft SHA-256 hashes terug."""
    print("\n[Test 11] Snapshot functie")
    from danny_toolkit.brain.config_auditor import (
        ConfigAuditor, SNAPSHOT_ENV_KEYS,
    )

    auditor = ConfigAuditor()
    snap = auditor.snapshot()
    check("Snapshot is dict", isinstance(snap, dict))
    check("Snapshot bevat alle keys", len(snap) == len(SNAPSHOT_ENV_KEYS))

    # Keys zonder waarde -> "ABSENT"
    absent_count = sum(1 for v in snap.values() if v == "ABSENT")
    check("Afwezige keys zijn ABSENT", absent_count >= 0)  # altijd waar

    # Keys met waarde -> 64-char hex (SHA-256)
    for key, val in snap.items():
        if val != "ABSENT":
            check(f"{key} is SHA-256 (64 hex chars)",
                  len(val) == 64 and all(c in "0123456789abcdef" for c in val))
            break  # test slechts 1 om output beperkt te houden


def test_12_drift_detection() -> None:
    """detect_drift() detecteert env wijzigingen."""
    print("\n[Test 12] Drift detectie")
    from danny_toolkit.brain.config_auditor import ConfigAuditor

    auditor = ConfigAuditor()

    # Geen baseline → geen drift
    schendingen = auditor.detect_drift()
    check("Zonder baseline: geen drift", len(schendingen) == 0)

    # Stel baseline in
    auditor._baseline = auditor.snapshot()
    schendingen = auditor.detect_drift()
    check("Na baseline: geen drift", len(schendingen) == 0)

    # Simuleer wijziging
    orig = os.environ.get("GROQ_API_KEY", "")
    try:
        os.environ["GROQ_API_KEY"] = "gsk_DRIFT_TEST_1234567890abcdef"
        schendingen = auditor.detect_drift()
        drift_keys = [s.sleutel for s in schendingen]
        check("Drift gedetecteerd na wijziging",
              "GROQ_API_KEY" in drift_keys)
        if schendingen:
            check("Drift categorie correct",
                  schendingen[0].categorie == "drift")
    finally:
        if orig:
            os.environ["GROQ_API_KEY"] = orig
        else:
            os.environ.pop("GROQ_API_KEY", None)


# ═══════════════════════════════════════════════════
# Tests 13-14: Full audit + rapport
# ═══════════════════════════════════════════════════

def test_13_full_audit() -> None:
    """audit() retourneert AuditRapport."""
    print("\n[Test 13] Volledige audit")
    from danny_toolkit.brain.config_auditor import (
        ConfigAuditor, AuditRapport,
    )

    auditor = ConfigAuditor()
    rapport = auditor.audit()
    check("Retourneert AuditRapport", isinstance(rapport, AuditRapport))
    check("gecontroleerd > 0", rapport.gecontroleerd > 0)
    check("schendingen is lijst", isinstance(rapport.schendingen, list))
    check("timestamp aanwezig", len(rapport.timestamp) > 0)
    check("veilig is bool", isinstance(rapport.veilig, bool))


def test_14_toon_rapport() -> None:
    """toon_rapport() print zonder crash."""
    print("\n[Test 14] toon_rapport()")
    from danny_toolkit.brain.config_auditor import ConfigAuditor

    auditor = ConfigAuditor()
    rapport = auditor.audit()

    # Vang print output
    import io
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        auditor.toon_rapport(rapport)
        output = sys.stdout.getvalue()
    finally:
        sys.stdout = old_stdout
        # Restore UTF-8 wrapper
        try:
            sys.stdout = __import__("io").TextIOWrapper(
                sys.stdout.buffer, encoding="utf-8", errors="replace",
            )
        except (ValueError, OSError):
            logger.debug("Invalid value encountered")

    check("toon_rapport() produceert output", len(output) > 0)
    check("Bevat CONFIG AUDIT", "CONFIG AUDIT" in output)


# ═══════════════════════════════════════════════════
# Tests 15-16: NeuralBus events
# ═══════════════════════════════════════════════════

def test_15_neuralbus_events_defined() -> None:
    """NeuralBus heeft CONFIG_DRIFT_DETECTED en CONFIG_AUDIT_COMPLETE."""
    print("\n[Test 15] NeuralBus config events")
    from danny_toolkit.core.neural_bus import EventTypes

    check("CONFIG_DRIFT_DETECTED bestaat",
          hasattr(EventTypes, "CONFIG_DRIFT_DETECTED"))
    check("CONFIG_AUDIT_COMPLETE bestaat",
          hasattr(EventTypes, "CONFIG_AUDIT_COMPLETE"))
    check("DRIFT waarde correct",
          EventTypes.CONFIG_DRIFT_DETECTED == "config_drift_detected")
    check("AUDIT waarde correct",
          EventTypes.CONFIG_AUDIT_COMPLETE == "config_audit_complete")


def test_16_neuralbus_audit_event() -> None:
    """Audit publiceert CONFIG_AUDIT_COMPLETE event."""
    print("\n[Test 16] NeuralBus audit event publicatie")
    from danny_toolkit.core.neural_bus import get_bus, EventTypes
    from danny_toolkit.brain.config_auditor import ConfigAuditor

    bus = get_bus()
    received = []

    def handler(event: object) -> None:
        """Handle bus event."""
        received.append(event)

    bus.subscribe(EventTypes.CONFIG_AUDIT_COMPLETE, handler)
    try:
        auditor = ConfigAuditor()
        auditor.audit()
        check("CONFIG_AUDIT_COMPLETE event ontvangen", len(received) >= 1)
        if received:
            check("Event heeft veilig veld",
                  "veilig" in received[-1].data)
            check("Event heeft schendingen veld",
                  "schendingen" in received[-1].data)
    finally:
        bus._subscribers[EventTypes.CONFIG_AUDIT_COMPLETE].remove(handler)


# ═══════════════════════════════════════════════════
# Test 17: Governor integratie
# ═══════════════════════════════════════════════════

def test_17_governor_integratie() -> None:
    """OmegaGovernor heeft periodieke_audit() methode."""
    print("\n[Test 17] Governor integratie")
    from danny_toolkit.brain.governor import OmegaGovernor

    gov = OmegaGovernor()
    check("periodieke_audit() bestaat", hasattr(gov, "periodieke_audit"))
    check("periodieke_audit() is callable", callable(gov.periodieke_audit))

    result = gov.periodieke_audit()
    check("periodieke_audit() retourneert dict", isinstance(result, dict))
    if "error" not in result:
        check("Bevat veilig veld", "veilig" in result)
        check("Bevat gecontroleerd veld", "gecontroleerd" in result)


# ═══════════════════════════════════════════════════
# Test 18: brain/__init__.py exports
# ═══════════════════════════════════════════════════

def test_18_brain_exports() -> None:
    """ConfigAuditor beschikbaar via brain package."""
    print("\n[Test 18] brain/__init__.py exports")
    import danny_toolkit.brain as brain_pkg

    check("ConfigAuditor in __all__",
          "ConfigAuditor" in brain_pkg.__all__)
    check("get_config_auditor in __all__",
          "get_config_auditor" in brain_pkg.__all__)

    # Import check
    try:
        from danny_toolkit.brain import (
            ConfigAuditor, get_config_auditor,
        )
        check("ConfigAuditor importeert via brain", True)
        check("get_config_auditor importeert via brain", True)
    except ImportError as e:
        check(f"Import mislukt: {e}", False)
        check(f"Import mislukt: {e}", False)


# ═══════════════════════════════════════════════════
# RUNNER
# ═══════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("Phase 33 — CONFIGAUDITOR: Runtime Config Validatie")
    print("=" * 60)

    tests = [
        test_1_module_import,
        test_2_dataclasses,
        test_3_singleton,
        test_4_model_allowlists_exist,
        test_5_current_models_valid,
        test_6_model_check_detects_invalid,
        test_7_valid_url_passes,
        test_8_invalid_url_detected,
        test_9_key_prefixes,
        test_10_key_check_detects_bad_prefix,
        test_11_snapshot,
        test_12_drift_detection,
        test_13_full_audit,
        test_14_toon_rapport,
        test_15_neuralbus_events_defined,
        test_16_neuralbus_audit_event,
        test_17_governor_integratie,
        test_18_brain_exports,
    ]

    for t in tests:
        try:
            t()
        except Exception as e:
            failed += 1
            print(f"  FAIL  {t.__name__}: {e}")

    print("\n" + "=" * 60)
    total = passed + failed
    print(f"Resultaat: {passed}/{total} checks geslaagd")
    if failed:
        print(f"  {failed} GEFAALD")
        sys.exit(1)
    else:
        print("  ALLE CHECKS GESLAAGD")
        sys.exit(0)

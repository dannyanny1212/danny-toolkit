"""
Danny Toolkit — Startup Validator (Phase 26B)
==============================================
Valideert kritieke configuratie bij opstart: API keys, paden,
afhankelijkheden. Faalt snel bij ontbrekende GROQ_API_KEY i.p.v.
cryptische runtime errors 30+ seconden later.

Gebruik:
    from danny_toolkit.core.startup_validator import valideer_opstart
    rapport = valideer_opstart()
"""

import os
import sys
import uuid
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def valideer_opstart(strict: bool = False) -> dict:
    """Voer 6 opstartchecks uit en retourneer rapport.

    Args:
        strict: Als True, exit ook bij waarschuwingen.

    Returns:
        dict met status, checks, fouten, waarschuwingen.
    """
    rapport = {
        "status": "OK",
        "checks": [],
        "fouten": [],
        "waarschuwingen": [],
    }

    # ── Check 1: GROQ_API_KEY (FATAAL) ──
    _check_api_key(
        rapport, "GROQ_API_KEY", "Groq", fataal=True,
    )

    # ── Check 2: ANTHROPIC_API_KEY (waarschuwing) ──
    _check_api_key(
        rapport, "ANTHROPIC_API_KEY", "Anthropic", fataal=False,
    )

    # ── Check 3: VOYAGE_API_KEY (waarschuwing) ──
    _check_api_key(
        rapport, "VOYAGE_API_KEY", "Voyage", fataal=False,
    )

    # ── Check 4: DATA_DIR schrijfbaar (FATAAL) ──
    _check_data_dir(rapport)

    # ── Check 5: Optionele dependencies (informatief) ──
    _check_optional_deps(rapport)

    # ── Check 6: .env bestand (informatief) ──
    _check_env_file(rapport)

    # Bepaal eindstatus
    if rapport["fouten"]:
        rapport["status"] = "FATAAL"
    elif rapport["waarschuwingen"]:
        rapport["status"] = "WAARSCHUWING"

    # Log resultaat
    n_checks = len(rapport["checks"])
    n_fouten = len(rapport["fouten"])
    n_warn = len(rapport["waarschuwingen"])
    logger.info(
        "Startup validatie: %d checks, %d fouten, %d waarschuwingen",
        n_checks, n_fouten, n_warn,
    )

    # Print samenvatting
    if rapport["fouten"]:
        print(f"  [STARTUP] FATAAL: {', '.join(rapport['fouten'])}")
    if rapport["waarschuwingen"]:
        print(f"  [STARTUP] Waarschuwingen: {', '.join(rapport['waarschuwingen'])}")
    if not rapport["fouten"] and not rapport["waarschuwingen"]:
        print(f"  [STARTUP] Alle {n_checks} checks OK")

    # Exit bij fatale fouten (tenzij test mode)
    if rapport["fouten"] and not os.environ.get("DANNY_TEST_MODE"):
        sys.exit(1)

    # In strict mode ook exit bij waarschuwingen
    if strict and rapport["waarschuwingen"] and not os.environ.get("DANNY_TEST_MODE"):
        sys.exit(1)

    return rapport


def _check_api_key(rapport, env_var, provider, fataal=True):
    """Controleer API key aanwezigheid en format."""
    check = {"naam": env_var, "status": "OK", "fataal": fataal}

    value = os.environ.get(env_var, "")
    if not value:
        check["status"] = "ONTBREEKT"
        msg = f"{env_var} niet ingesteld"
        if fataal:
            rapport["fouten"].append(msg)
        else:
            rapport["waarschuwingen"].append(msg)
        rapport["checks"].append(check)
        return

    # Gebruik ConfigValidator als beschikbaar
    try:
        from danny_toolkit.core.config import ConfigValidator
        is_valid, message = ConfigValidator.valideer_api_key(
            value, provider,
        )
        if not is_valid:
            check["status"] = "ONGELDIG"
            msg = f"{env_var}: {message}"
            if fataal:
                rapport["fouten"].append(msg)
            else:
                rapport["waarschuwingen"].append(msg)
    except ImportError:
        # Fallback: alleen lengte check
        if len(value) < 20:
            check["status"] = "VERDACHT"
            msg = f"{env_var} lijkt te kort"
            if fataal:
                rapport["fouten"].append(msg)
            else:
                rapport["waarschuwingen"].append(msg)

    rapport["checks"].append(check)


def _check_data_dir(rapport):
    """Controleer of DATA_DIR schrijfbaar is."""
    check = {"naam": "DATA_DIR_schrijfbaar", "status": "OK", "fataal": True}

    try:
        from danny_toolkit.core.config import Config
        data_dir = Config.DATA_DIR
    except ImportError:
        data_dir = Path("data")

    try:
        data_dir.mkdir(parents=True, exist_ok=True)
        test_file = data_dir / f".startup_test_{uuid.uuid4().hex[:8]}"
        test_file.write_text("test", encoding="utf-8")
        test_file.unlink()
    except Exception as e:
        check["status"] = "NIET_SCHRIJFBAAR"
        msg = f"DATA_DIR niet schrijfbaar: {e}"
        rapport["fouten"].append(msg)

    rapport["checks"].append(check)


def _check_optional_deps(rapport):
    """Controleer optionele dependencies."""
    deps = ["chromadb", "ollama", "groq"]
    beschikbaar = []
    ontbreekt = []

    for dep in deps:
        try:
            __import__(dep)
            beschikbaar.append(dep)
        except ImportError:
            ontbreekt.append(dep)

    check = {
        "naam": "optionele_deps",
        "status": "OK" if not ontbreekt else "DEELS",
        "beschikbaar": beschikbaar,
        "ontbreekt": ontbreekt,
        "fataal": False,
    }
    rapport["checks"].append(check)


def _check_env_file(rapport):
    """Controleer of .env bestand bestaat."""
    try:
        from danny_toolkit.core.config import Config
        env_path = Config.BASE_DIR / ".env"
    except ImportError:
        env_path = Path(".env")

    check = {
        "naam": "env_bestand",
        "status": "OK" if env_path.exists() else "ONTBREEKT",
        "fataal": False,
    }
    if not env_path.exists():
        rapport["waarschuwingen"].append(
            ".env bestand niet gevonden"
        )
    rapport["checks"].append(check)

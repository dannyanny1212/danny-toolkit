"""
Env Bootstrap — Single source of truth voor venv python pad en subprocess env.

Centraliseert de logica die eerder gedupliceerd was in sandbox.py,
artificer.py, will_protocol.py en run_all_tests.py.

Gebruik:
    from danny_toolkit.core.env_bootstrap import VENV_PYTHON, get_subprocess_env
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# Project root: danny-toolkit/
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)

# Locked interpreter — venv311 voor consistente executie
VENV_PYTHON = os.path.join(_PROJECT_ROOT, "venv311", "Scripts", "python.exe")
if not os.path.isfile(VENV_PYTHON):
    VENV_PYTHON = sys.executable  # fallback


def get_subprocess_env(test_mode: bool = False) -> dict:
    """Bouw een schone env dict met isolatie-vars.

    Args:
        test_mode: Als True, voeg DANNY_TEST_MODE=1 toe.
                   Production sandbox moet dit NIET zetten.

    Returns:
        dict met os.environ + isolatie overrides.
    """
    env = os.environ.copy()
    env["CUDA_VISIBLE_DEVICES"] = "-1"
    env["ANONYMIZED_TELEMETRY"] = "False"
    env["PYTHONIOENCODING"] = "utf-8"
    if test_mode:
        env["DANNY_TEST_MODE"] = "1"
    return env


def bootstrap() -> None:
    """Idempotent bootstrap: laad .env en activeer GPU guard.

    Veilig om meerdere keren aan te roepen.
    """
    # 1. Laad secrets — triple fallback: vault → .env → dotenv
    # Danny moet ALTIJD verbonden zijn met zijn keys.
    # Geen enkele failure mag de connectie verbreken.
    _keys_loaded = False

    # Poging 1: DPAPI Vault (meest veilig)
    try:
        from danny_toolkit.core.env_vault import unseal_env
        count = unseal_env()
        if count != 0:
            _keys_loaded = True
            logger.info("Keys geladen via DPAPI vault (%s)", count)
    except FileNotFoundError:
        logger.debug("Geen env vault gevonden, probeer .env")
    except (ImportError, OSError) as e:
        logger.debug("Vault unavailable (%s), fallback", e)

    # Poging 2: Plain .env via dotenv
    if not _keys_loaded:
        _env_path = Path(_PROJECT_ROOT) / ".env"
        try:
            from dotenv import load_dotenv
            if _env_path.exists():
                load_dotenv(_env_path, override=False)
                _keys_loaded = True
                logger.info("Keys geladen via plain .env (dotenv)")
        except ImportError:
            logger.debug("dotenv niet beschikbaar")

    # Poging 3: Manual .env parse (als dotenv niet geïnstalleerd)
    if not _keys_loaded:
        _env_path = Path(_PROJECT_ROOT) / ".env"
        if _env_path.exists():
            for line in _env_path.read_text("utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                k, v = k.strip(), v.strip().strip('"').strip("'")
                if k and k not in os.environ:
                    os.environ[k] = v
            _keys_loaded = True
            logger.info("Keys geladen via manual .env parse")

    if not _keys_loaded:
        logger.warning(
            "GEEN KEYS GELADEN — geen vault, geen .env. "
            "API calls zullen falen."
        )

    # 2. GPU guard
    try:
        import danny_toolkit.core.gpu  # noqa: F401
    except ImportError:
        logger.debug("GPU guard module not available")

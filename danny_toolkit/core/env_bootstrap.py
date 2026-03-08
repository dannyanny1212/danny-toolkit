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
    # 1. Laad .env
    try:
        from dotenv import load_dotenv
        load_dotenv(Path(_PROJECT_ROOT) / ".env", override=False)
    except ImportError:
        logger.debug("dotenv not available, skipping .env load")

    # 2. GPU guard
    try:
        import danny_toolkit.core.gpu  # noqa: F401
    except ImportError:
        logger.debug("GPU guard module not available")

"""
Security Utils — Gedeelde helpers voor de security subpackage.

Bevat:
- _fetch_json()   — JSON ophalen van URL
- _scrub_adres()  — Wallet adres maskering
- HAS_REQUESTS    — requests beschikbaarheid flag
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


def _fetch_json(url, timeout=10) -> dict | list | None:
    """Haal JSON op van een URL.

    Returns:
        Parsed JSON of None bij fout.
    """
    if not HAS_REQUESTS:
        return None
    try:
        resp = requests.get(
            url,
            timeout=timeout,
            headers={
                "User-Agent": "DannyToolkit/2.0",
            },
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.debug("JSON fetch failed for %s: %s", url[:80], e)
        return None


def _scrub_adres(adres: str) -> str:
    """Maskeer een wallet adres voor display.

    Toont eerste 6 en laatste 4 karakters.
    Voorbeeld: bc1q4x...7k2m
    """
    if not adres or len(adres) < 12:
        return adres or ""
    return f"{adres[:6]}...{adres[-4:]}"

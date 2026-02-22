"""
Log Rotation — Verwijder oude log/JSON bestanden.

Voorkomt dat data/logs/ onbeperkt groeit tijdens 24/7 daemon uptime.

Gebruik:
    from danny_toolkit.core.log_rotation import roteer_logs
    verwijderd = roteer_logs(Path("data/logs"), max_leeftijd_dagen=30)
"""

import logging
import time
from pathlib import Path

logger = logging.getLogger(__name__)


def roteer_logs(
    log_dir: Path,
    max_leeftijd_dagen: int = 30,
    max_bestanden: int = 100,
) -> int:
    """
    Verwijder oude log- en JSON-bestanden uit een directory.

    1. Scan *.json + *.log recursief
    2. Verwijder bestanden ouder dan max_leeftijd_dagen
    3. Als nog > max_bestanden, verwijder oudste tot limiet

    Args:
        log_dir: Directory om te scannen.
        max_leeftijd_dagen: Maximale leeftijd in dagen.
        max_bestanden: Maximaal aantal bestanden na opschoning.

    Returns:
        Aantal verwijderde bestanden.
    """
    if not log_dir.exists():
        return 0

    verwijderd = 0
    cutoff = time.time() - (max_leeftijd_dagen * 86400)

    # Verzamel alle log/json bestanden
    bestanden = []
    for patroon in ("**/*.json", "**/*.log"):
        try:
            bestanden.extend(log_dir.glob(patroon))
        except Exception as e:
            logger.debug("Glob error voor %s: %s", patroon, e)

    # Fase 1: verwijder bestanden ouder dan max_leeftijd_dagen
    overgebleven = []
    for pad in bestanden:
        try:
            if pad.stat().st_mtime < cutoff:
                pad.unlink()
                verwijderd += 1
            else:
                overgebleven.append(pad)
        except Exception as e:
            logger.debug("Log rotation fout voor %s: %s", pad.name, e)
            overgebleven.append(pad)

    # Fase 2: als nog te veel, verwijder oudste
    if len(overgebleven) > max_bestanden:
        # Sorteer op mtime (oudste eerst)
        try:
            overgebleven.sort(key=lambda p: p.stat().st_mtime)
        except Exception:
            pass
        te_verwijderen = overgebleven[:len(overgebleven) - max_bestanden]
        for pad in te_verwijderen:
            try:
                pad.unlink()
                verwijderd += 1
            except Exception as e:
                logger.debug("Log rotation fout voor %s: %s", pad.name, e)

    if verwijderd > 0:
        logger.info("Log rotation: %d bestand(en) verwijderd uit %s", verwijderd, log_dir)

    return verwijderd

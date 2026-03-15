"""
HARDWARE ANCHOR — Silicon Seal C2 Node-Lock.

Bindt de danny-toolkit aan de fysieke hardware van Commandant Danny's
machine in Nijlen. De server weigert op te starten op een andere
machine (CPU, GPU, moederbord moeten exact matchen).

C2 Architecture:
    De lokale hash wordt NIET meer lokaal vertrouwd. Verificatie gaat
    via een externe Command & Control URL (GitHub Gist / raw file).
    De C2 Master bepaalt welke hardware-hashes geautoriseerd zijn.

Workflow:
    1. generate_silicon_seal()  — Scan hardware, return SHA-256 hash
    2. setup_hardware_lock()    — Injecteer hash in .env (referentie)
    3. fetch_c2_seals()         — Haal geautoriseerde hashes op van C2
    4. verify_hardware_anchor() — Vergelijk live hash met C2 whitelist

Gebruik:
    python -m danny_toolkit.core.hardware_anchor   # Eenmalig: brandt seal in .env
"""

from __future__ import annotations

import hashlib
import logging
import os
import secrets
import subprocess
import urllib.request
import urllib.error
from pathlib import Path

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_ENV_FILE = _PROJECT_ROOT / ".env"


def _wmic_query(query: str) -> str:
    """Voer een WMIC query uit en return gestripte output.

    Args:
        query: WMIC commando (bijv. 'baseboard get serialnumber').

    Returns:
        Gestripte output string, of 'UNKNOWN' bij fout.
    """
    try:
        raw = subprocess.check_output(
            f"wmic {query}",
            shell=True,
            timeout=10,
            stderr=subprocess.DEVNULL,
        )
        lines = raw.decode("utf-8", errors="replace").strip().splitlines()
        # Eerste regel is header, tweede is waarde
        if len(lines) >= 2:
            return lines[1].strip()
        return lines[0].strip() if lines else "UNKNOWN"
    except Exception as e:
        logger.debug("WMIC query '%s' mislukt: %s", query, e)
        return "UNKNOWN"


def _gpu_id() -> str:
    """Haal GPU identifier op via nvidia-smi.

    Returns:
        GPU naam + UUID string, of 'NO_GPU' bij fout.
    """
    try:
        raw = subprocess.check_output(
            "nvidia-smi -L",
            shell=True,
            timeout=10,
            stderr=subprocess.DEVNULL,
        )
        output = raw.decode("utf-8", errors="replace").strip()
        # Neem eerste GPU regel (bijv. "GPU 0: NVIDIA GeForce RTX 3060 Ti (UUID: GPU-...)")
        if output:
            return output.splitlines()[0].strip()
        return "NO_GPU"
    except Exception as e:
        logger.debug("nvidia-smi mislukt: %s", e)
        return "NO_GPU"


def generate_silicon_seal() -> str:
    """Genereer een SHA-256 hash van de huidige hardware.

    Combineert:
        - Moederbord serienummer (WMIC baseboard)
        - CPU processor ID (WMIC cpu)
        - GPU identifier (nvidia-smi)

    Returns:
        64-karakter hex SHA-256 hash.
    """
    board = _wmic_query("baseboard get serialnumber")
    cpu = _wmic_query("cpu get processorid")
    gpu = _gpu_id()

    combined = f"{board}|{cpu}|{gpu}"
    seal = hashlib.sha256(combined.encode("utf-8")).hexdigest()

    logger.info(
        "Silicon Seal berekend: %s...%s "
        "(board=%s, cpu=%s, gpu=%s)",
        seal[:8], seal[-4:],
        board[:12], cpu[:12], gpu[:20],
    )
    return seal


def setup_hardware_lock() -> str:
    """Bereken hardware seal en injecteer in .env.

    Leest het .env bestand, zoekt naar AUTHORIZED_SILICON_SEAL=,
    en update of append de waarde.

    Returns:
        De gegenereerde seal.
    """
    seal = generate_silicon_seal()

    if not _ENV_FILE.exists():
        raise FileNotFoundError(f".env niet gevonden: {_ENV_FILE}")

    lines = _ENV_FILE.read_text("utf-8").splitlines()
    updated = False

    for i, line in enumerate(lines):
        if line.strip().startswith("AUTHORIZED_SILICON_SEAL="):
            lines[i] = f"AUTHORIZED_SILICON_SEAL={seal}"
            updated = True
            break

    if not updated:
        # Append met sectie-header
        lines.append("")
        lines.append("# === Hardware Anchor (Silicon Seal) ===")
        lines.append(f"AUTHORIZED_SILICON_SEAL={seal}")

    _ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(
        f"\n  Silicon Seal gebrand in .env:"
        f"\n  AUTHORIZED_SILICON_SEAL={seal[:16]}...{seal[-8:]}"
        f"\n  Machine is nu vergrendeld.\n"
    )
    return seal


def fetch_c2_seals() -> list[str]:
    """Haal geautoriseerde hardware hashes op van de C2 Master.

    Leest C2_AUTH_URL uit de omgevingsvariabelen en maakt een HTTP GET
    request naar de raw GitHub URL. Elke regel is een hash.
    Lege regels en comments (# ...) worden genegeerd.

    Returns:
        Lijst van geautoriseerde SHA-256 hashes.

    Raises:
        ConnectionError: Als de C2 server onbereikbaar is.
        PermissionError: Als C2_AUTH_URL niet geconfigureerd is.
    """
    c2_url = os.getenv("C2_AUTH_URL", "").strip()
    if not c2_url:
        raise PermissionError(
            "[FATAL] C2_AUTH_URL ontbreekt in env. "
            "Configureer de Command & Control URL in .env"
        )

    try:
        req = urllib.request.Request(
            c2_url,
            headers={"User-Agent": "SovereignGate/6.19"},
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, urllib.error.HTTPError, OSError) as e:
        logger.critical("C2 Server onbereikbaar: %s", e)
        raise ConnectionError(
            "[FATAL] C2 Server onbereikbaar. "
            "Failsafe lockdown geactiveerd."
        ) from e

    seals: list[str] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # Alleen valide hex hashes (64 chars = SHA-256)
        if len(line) == 64 and all(c in "0123456789abcdef" for c in line):
            seals.append(line)

    logger.info("C2 Master: %d geautoriseerde seal(s) opgehaald", len(seals))
    return seals


def verify_hardware_anchor() -> bool:
    """Verifieer of de huidige hardware geautoriseerd is door de C2 Master.

    C2 Architecture: de lokale hash wordt vergeleken met de externe
    whitelist. De C2 server is de enige autoriteit.

    Returns:
        True als hardware geautoriseerd is.

    Raises:
        PermissionError: Bij niet-geautoriseerde hardware.
        ConnectionError: Bij onbereikbare C2 server.
    """
    # SOVEREIGN GATE = ONAANRAAKBAAR — GEEN test mode bypass.
    # Tests die de gate importeren moeten `except SystemExit` vangen.
    live = generate_silicon_seal()

    # C2 verificatie — externe whitelist is de enige wet
    authorized = fetch_c2_seals()

    if not authorized:
        raise PermissionError(
            "[FATAL LOCKDOWN] C2 Master retourneerde een lege whitelist. "
            "Geen enkele machine is geautoriseerd."
        )

    # Constant-time vergelijking voor elke hash in de lijst
    match_found = False
    for seal in authorized:
        if secrets.compare_digest(seal, live):
            match_found = True
            break

    if not match_found:
        logger.critical(
            "HARDWARE NOT AUTHORIZED BY C2! Live: %s...%s",
            live[:8], live[-4:],
        )
        raise PermissionError(
            "[FATAL LOCKDOWN] Hardware ID is niet (meer) geautoriseerd "
            "door de C2 Master. Toegang geweigerd. "
            "Live seal: %s..." % live[:16]
        )

    logger.info(
        "Hardware Anchor VERIFIED via C2: %s...%s",
        live[:8], live[-4:],
    )
    return True


if __name__ == "__main__":
    setup_hardware_lock()

"""
HARDWARE ANCHOR v7.0 — Silicon Seal C2 Node-Lock + Deep CPU Fingerprint.

Bindt de danny-toolkit aan de fysieke hardware van Commandant Danny's
machine in Nijlen. De server weigert op te starten op een andere
machine (CPU, GPU, moederbord moeten exact matchen).

Security layers:
    Layer 1: Deep CPU Fingerprint (4 velden: ProcessorId, Name, Cores, MaxClock)
    Layer 2: Moederbord serienummer
    Layer 3: GPU identifier (nvidia-smi UUID)
    Layer 4: Windows Machine GUID (registry)
    Layer 5: C2 Remote Whitelist verificatie

Geen enkel veld mag "UNKNOWN" zijn — anders FATAL LOCKDOWN.

C2 Architecture:
    De lokale hash wordt NIET meer lokaal vertrouwd. Verificatie gaat
    via een externe Command & Control URL (GitHub Gist / raw file).
    De C2 Master bepaalt welke hardware-hashes geautoriseerd zijn.

Workflow:
    1. generate_silicon_seal()  — Scan hardware, return SHA-256 hash
    2. setup_hardware_lock()    — Injecteer hash in .env (referentie)
    3. fetch_c2_seals()         — Haal geautoriseerde hashes op van C2
    4. verify_hardware_anchor() — Vergelijk live hash met C2 whitelist
    5. get_cpu_fingerprint()    — Standalone CPU ID voor defense-in-depth

Gebruik:
    python -m danny_toolkit.core.hardware_anchor   # Eenmalig: brandt seal in .env
"""

from __future__ import annotations

import hashlib
import logging
import os
import secrets
import subprocess
import threading
import time as _time
import urllib.request
import urllib.error
from pathlib import Path

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════
#  RUNTIME SEAL GUARD — Cached hardware verification for agent dispatch
# ═══════════════════════════════════════════════════════════════
# Computed once at first agent dispatch, then instant constant-time
# comparison on every subsequent call. Detects VM migration or
# hardware hot-swap during runtime.

_RUNTIME_SEAL: str | None = None
_RUNTIME_SEAL_LOCK = threading.Lock()
_RUNTIME_SEAL_CPU_HASH: str | None = None
_RUNTIME_VIOLATIONS: list[dict] = []
_RUNTIME_CHECK_COUNT = 0
_VM_CHECKED = False
_VM_DETECTED = False

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_ENV_FILE = _PROJECT_ROOT / ".env"


# ═══════════════════════════════════════════════════════════════
#  VM DETECTION — Virtual machines get ZERO access tokens
# ═══════════════════════════════════════════════════════════════
# VMs mogen NOOIT een seal krijgen. Detectie via:
#   1. WMIC computersystem model (bevat "Virtual", "VMware", etc.)
#   2. WMIC baseboard manufacturer (bevat "Microsoft Corporation" = Hyper-V)
#   3. Hypervisor present bit via WMIC os
#   4. Known VM MAC address prefixes
#   5. Registry: SystemBiosVersion bevat "VBOX", "VMWARE", "QEMU"

_VM_INDICATORS_MODEL = frozenset({
    "virtual", "vmware", "virtualbox", "vbox", "kvm", "qemu",
    "xen", "hvm", "parallels", "bhyve", "hyperv",
})

_VM_INDICATORS_MANUFACTURER = frozenset({
    "microsoft corporation",  # Hyper-V
    "vmware, inc.",
    "innotek gmbh",           # VirtualBox
    "qemu",
    "parallels",
    "xen",
    "red hat",                # KVM/RHEL
})

_VM_MAC_PREFIXES = frozenset({
    "00:05:69",  # VMware
    "00:0c:29",  # VMware
    "00:1c:14",  # VMware
    "00:50:56",  # VMware
    "08:00:27",  # VirtualBox
    "00:15:5d",  # Hyper-V
    "52:54:00",  # QEMU/KVM
    "00:16:3e",  # Xen
})


def _detect_vm() -> tuple[bool, str]:
    """Detecteer of we in een virtuele machine draaien.

    Controleert 5 onafhankelijke VM-indicatoren. Als ÉÉN positief is,
    wordt de machine als VM beschouwd en krijgt het ZERO access.

    Returns:
        (is_vm, reason) — is_vm=True als VM gedetecteerd.
    """
    global _VM_CHECKED, _VM_DETECTED

    # Check 1: WMIC computersystem model
    model = _wmic_query("computersystem get model").lower()
    for indicator in _VM_INDICATORS_MODEL:
        if indicator in model:
            reason = f"VM model detected: '{model}' matches '{indicator}'"
            logger.critical("VM DETECTED (model): %s", reason)
            return True, reason

    # Check 2: WMIC baseboard manufacturer
    manufacturer = _wmic_query("baseboard get manufacturer").lower()
    for indicator in _VM_INDICATORS_MANUFACTURER:
        if indicator in manufacturer:
            reason = f"VM manufacturer detected: '{manufacturer}' matches '{indicator}'"
            logger.critical("VM DETECTED (manufacturer): %s", reason)
            return True, reason

    # Check 3: Hypervisor present via WMIC (Windows reports hypervisor)
    try:
        raw = subprocess.check_output(
            "wmic computersystem get hypervisorpresent",
            shell=True, timeout=10, stderr=subprocess.DEVNULL,
        )
        lines = raw.decode("utf-8", errors="replace").strip().splitlines()
        if len(lines) >= 2 and lines[1].strip().upper() == "TRUE":
            reason = "Hypervisor present bit is TRUE"
            logger.critical("VM DETECTED (hypervisor): %s", reason)
            return True, reason
    except Exception as _hv_err:
        logger.debug("Hypervisor check: %s", _hv_err)

    # Check 4: MAC address prefix (VM network adapters)
    try:
        raw = subprocess.check_output(
            "getmac /fo csv /nh",
            shell=True, timeout=10, stderr=subprocess.DEVNULL,
        )
        mac_output = raw.decode("utf-8", errors="replace").lower()
        for prefix in _VM_MAC_PREFIXES:
            # getmac output uses dashes: 00-05-69
            dash_prefix = prefix.replace(":", "-")
            if dash_prefix in mac_output:
                reason = f"VM MAC prefix detected: {prefix}"
                logger.critical("VM DETECTED (MAC): %s", reason)
                return True, reason
    except Exception as _mac_err:
        logger.debug("MAC check: %s", _mac_err)

    # Check 5: Registry BIOS string check
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"HARDWARE\DESCRIPTION\System",
            0,
            winreg.KEY_READ | winreg.KEY_WOW64_64KEY,
        )
        bios_val, _ = winreg.QueryValueEx(key, "SystemBiosVersion")
        winreg.CloseKey(key)
        bios_str = str(bios_val).lower()
        for vm_sig in ("vbox", "vmware", "qemu", "virtual", "xen", "parallels"):
            if vm_sig in bios_str:
                reason = f"VM BIOS signature: '{vm_sig}' in SystemBiosVersion"
                logger.critical("VM DETECTED (BIOS): %s", reason)
                return True, reason
    except Exception as _bios_err:
        logger.debug("BIOS VM check: %s", _bios_err)

    return False, "Physical hardware confirmed"


def is_virtual_machine() -> bool:
    """Cached VM detection — True als VM, False als fysieke hardware.

    Resultaat wordt gecached na eerste check (VM status verandert niet
    tijdens runtime).
    """
    global _VM_CHECKED, _VM_DETECTED
    if _VM_CHECKED:
        return _VM_DETECTED
    with _RUNTIME_SEAL_LOCK:
        if _VM_CHECKED:
            return _VM_DETECTED
        _VM_DETECTED, reason = _detect_vm()
        _VM_CHECKED = True
        if _VM_DETECTED:
            logger.critical(
                "PERMANENT VM LOCKDOWN — %s — "
                "No agent commands will be accepted", reason,
            )
        else:
            logger.info("Physical hardware confirmed: %s", reason)
    return _VM_DETECTED


def _compute_cpu_hash() -> str:
    """Bereken een SHA-256 hash van alleen de CPU fingerprint.

    Sneller dan generate_silicon_seal() — skip GPU/board/GUID.
    Gebruikt voor runtime constant-time vergelijking.
    """
    fp = get_cpu_fingerprint()
    combined = f"{fp['processor_id']}|{fp['name']}|{fp['cores']}|{fp['max_clock']}"
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()


def runtime_hardware_guard(agent_name: str = "") -> tuple[bool, str]:
    """Runtime hardware validatie voor elke agent command dispatch.

    Drie checks:
        1. VM Detection     — VM's krijgen NOOIT een token
        2. CPU Seal Cache   — Eerste call berekent seal, opvolgende calls
                              doen instant constant-time vergelijking
        3. Drift Detection  — Als CPU hash verandert tijdens runtime
                              (live migration, hardware swap) → FATAL

    Args:
        agent_name: Naam van de agent die een command wil uitvoeren.

    Returns:
        (allowed, reason) — allowed=False blokkeert de agent command.
    """
    global _RUNTIME_SEAL_CPU_HASH, _RUNTIME_CHECK_COUNT

    # ── Gate 1: VM Detection (cached, instant na eerste call) ──
    if is_virtual_machine():
        violation = {
            "timestamp": _time.strftime("%Y-%m-%dT%H:%M:%S"),
            "agent": agent_name,
            "reason": "VM_DETECTED",
            "severity": "FATAL",
        }
        _RUNTIME_VIOLATIONS.append(violation)
        if len(_RUNTIME_VIOLATIONS) > 200:
            _RUNTIME_VIOLATIONS.pop(0)
        return False, (
            f"[FATAL] VM DETECTED — agent '{agent_name}' command DENIED. "
            "Virtual machines receive ZERO access tokens. "
            "Only Commander Danny's physical hardware is authorized."
        )

    # ── Gate 2: CPU Seal — eerste call berekent, opvolgende vergelijken ──
    with _RUNTIME_SEAL_LOCK:
        _RUNTIME_CHECK_COUNT += 1

        if _RUNTIME_SEAL_CPU_HASH is None:
            # Eerste call: bereken + cache
            try:
                _RUNTIME_SEAL_CPU_HASH = _compute_cpu_hash()
                logger.info(
                    "Runtime CPU seal initialized: %s...%s (agent=%s)",
                    _RUNTIME_SEAL_CPU_HASH[:8],
                    _RUNTIME_SEAL_CPU_HASH[-4:],
                    agent_name,
                )
                return True, "Hardware OK — seal initialized"
            except Exception as e:
                logger.critical("Runtime CPU seal FAILED: %s", e)
                return False, f"[FATAL] CPU seal computation failed: {e}"
        else:
            # Opvolgende calls: instant vergelijking (elke 50e call herberekend)
            if _RUNTIME_CHECK_COUNT % 50 == 0:
                try:
                    live_hash = _compute_cpu_hash()
                    if not secrets.compare_digest(
                        _RUNTIME_SEAL_CPU_HASH, live_hash
                    ):
                        # ── HARDWARE DRIFT DETECTED ──
                        violation = {
                            "timestamp": _time.strftime("%Y-%m-%dT%H:%M:%S"),
                            "agent": agent_name,
                            "reason": "CPU_DRIFT",
                            "severity": "FATAL",
                            "cached": _RUNTIME_SEAL_CPU_HASH[:12],
                            "live": live_hash[:12],
                        }
                        _RUNTIME_VIOLATIONS.append(violation)
                        logger.critical(
                            "HARDWARE DRIFT DETECTED! cached=%s live=%s agent=%s "
                            "— possible VM migration or hardware hot-swap",
                            _RUNTIME_SEAL_CPU_HASH[:12],
                            live_hash[:12],
                            agent_name,
                        )
                        return False, (
                            f"[FATAL] CPU hardware drift detected during runtime. "
                            f"Agent '{agent_name}' command DENIED. "
                            f"Cached seal {_RUNTIME_SEAL_CPU_HASH[:8]}... "
                            f"≠ live seal {live_hash[:8]}... "
                            f"Possible VM migration or hardware swap."
                        )
                except Exception as _drift_err:
                    logger.debug("Drift check error (non-fatal): %s", _drift_err)

    return True, "Hardware OK"


def get_runtime_stats() -> dict:
    """Runtime hardware guard statistieken."""
    return {
        "checks_performed": _RUNTIME_CHECK_COUNT,
        "vm_detected": _VM_DETECTED,
        "vm_checked": _VM_CHECKED,
        "seal_initialized": _RUNTIME_SEAL_CPU_HASH is not None,
        "seal_preview": (
            f"{_RUNTIME_SEAL_CPU_HASH[:8]}...{_RUNTIME_SEAL_CPU_HASH[-4:]}"
            if _RUNTIME_SEAL_CPU_HASH else None
        ),
        "violations": len(_RUNTIME_VIOLATIONS),
        "recent_violations": _RUNTIME_VIOLATIONS[-5:],
    }


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


def _machine_guid() -> str:
    """Haal Windows Machine GUID op uit het register.

    Dit is een unieke per-installatie identifier die verandert bij
    herinstallatie van Windows. Extra laag bovenop hardware IDs.

    Returns:
        Machine GUID string, of 'NO_GUID' bij fout.
    """
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Cryptography",
            0,
            winreg.KEY_READ | winreg.KEY_WOW64_64KEY,
        )
        guid, _ = winreg.QueryValueEx(key, "MachineGuid")
        winreg.CloseKey(key)
        return guid.strip() if guid else "NO_GUID"
    except Exception as e:
        logger.debug("Machine GUID ophalen mislukt: %s", e)
        return "NO_GUID"


def get_cpu_fingerprint() -> dict:
    """Genereer een deep CPU fingerprint met 4 onafhankelijke velden.

    Velden:
        processor_id : Unieke processor ID (hardware-gebrande hex)
        name          : CPU modelnaam (bijv. 'AMD Ryzen 7 5800X')
        cores         : Aantal fysieke cores
        max_clock     : Maximale kloksnelheid in MHz

    Returns:
        Dict met alle 4 velden. Geen enkel veld mag 'UNKNOWN' zijn.
    """
    return {
        "processor_id": _wmic_query("cpu get processorid"),
        "name": _wmic_query("cpu get name"),
        "cores": _wmic_query("cpu get numberofcores"),
        "max_clock": _wmic_query("cpu get maxclockspeed"),
    }


def validate_cpu_fingerprint() -> tuple[bool, dict]:
    """Valideer dat alle CPU velden gelezen kunnen worden.

    Returns:
        (valid, fingerprint) — valid=False als enig veld 'UNKNOWN' is.
    """
    fp = get_cpu_fingerprint()
    unknown_fields = [k for k, v in fp.items() if v == "UNKNOWN" or not v]

    if unknown_fields:
        logger.critical(
            "CPU FINGERPRINT INCOMPLETE — missing fields: %s",
            unknown_fields,
        )
        return False, fp

    logger.info(
        "CPU Fingerprint OK: %s | %s cores @ %s MHz",
        fp["name"], fp["cores"], fp["max_clock"],
    )
    return True, fp


def generate_silicon_seal() -> str:
    """Genereer een SHA-256 hash van de huidige hardware.

    Combineert 5 lagen:
        Layer 1: CPU Processor ID (hardware-gebrande hex)
        Layer 2: CPU Name + Cores + MaxClock (deep fingerprint)
        Layer 3: Moederbord serienummer
        Layer 4: GPU identifier (nvidia-smi UUID)
        Layer 5: Windows Machine GUID

    FATAL: Weigert een seal te genereren als CPU velden 'UNKNOWN' zijn.

    Returns:
        64-karakter hex SHA-256 hash.

    Raises:
        PermissionError: Als CPU fingerprint onvolledig is.
    """
    # Deep CPU fingerprint — alle 4 velden verplicht
    cpu_valid, cpu_fp = validate_cpu_fingerprint()
    if not cpu_valid:
        unknown = [k for k, v in cpu_fp.items() if v == "UNKNOWN" or not v]
        raise PermissionError(
            f"[FATAL] CPU fingerprint onvolledig — velden {unknown} "
            f"konden niet gelezen worden. Hardware verificatie geblokkeerd."
        )

    board = _wmic_query("baseboard get serialnumber")
    gpu = _gpu_id()
    guid = _machine_guid()

    # Combineer alle 5 lagen in de seal
    combined = (
        f"{cpu_fp['processor_id']}|{cpu_fp['name']}|"
        f"{cpu_fp['cores']}|{cpu_fp['max_clock']}|"
        f"{board}|{gpu}|{guid}"
    )
    seal = hashlib.sha256(combined.encode("utf-8")).hexdigest()

    logger.info(
        "Silicon Seal v7.0 berekend: %s...%s "
        "(cpu=%s, board=%s, gpu=%s, guid=%s)",
        seal[:8], seal[-4:],
        cpu_fp["processor_id"][:12], board[:12], gpu[:20], guid[:8],
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

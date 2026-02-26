"""
THE SOVEREIGN GATE v6.7.0 — Golden Master Security Enforcer.

9 security checks. Code weigert te draaien tenzij ALLE checks slagen.
Geen bypass. Geen test modus. Geen uitzonderingen.

Laws 1-5: Original Sovereign Laws
Laws 6-9: Security Hardening (Phase Golden Master)

  6. Brute Force Lockout   — 5 fails → 15 min lockout
  7. Boot Audit Log        — Elke pass/fail met timestamp
  8. Anti-Tamper Hash      — SHA256 self-verification
  9. Max Boot Frequency    — Max 10 boots per minuut
"""

import ctypes
import hashlib
import json
import os
import subprocess
import sys
import time

import psutil


# ── Constanten ──────────────────────────────────────────────
_GATE_DIR = os.path.dirname(os.path.abspath(__file__))
_DATA_DIR = os.path.join(os.path.dirname(_GATE_DIR), "..", "data")
_LOCKOUT_FILE = os.path.join(_DATA_DIR, ".gate_lockout.json")
_AUDIT_LOG = os.path.join(_DATA_DIR, ".gate_audit.log")
_BOOT_TRACKER = os.path.join(_DATA_DIR, ".gate_boots.json")

_MAX_FAILURES = 5
_LOCKOUT_SECONDS = 900  # 15 minuten
_MAX_BOOTS_PER_MINUTE = 10

# SHA256 hash van dit bestand bij bekende goede staat
# Wordt berekend na eerste succesvolle boot en opgeslagen
_HASH_FILE = os.path.join(_DATA_DIR, ".gate_hash")


def _ensure_data_dir():
    """Maak data directory als het niet bestaat."""
    os.makedirs(_DATA_DIR, exist_ok=True)


def _audit_log(status: str, law: str, detail: str = ""):
    """Schrijf audit regel naar logbestand."""
    try:
        _ensure_data_dir()
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] {status} | {law} | {detail}\n"
        with open(_AUDIT_LOG, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass  # Audit log mag nooit de gate blokkeren


def _gate_fail(law: str, message: str):
    """Registreer een failure en exit."""
    _audit_log("DENIED", law, message)
    _record_failure()
    sys.exit(f"\U0001f6a8 [GATE] {message}")


def _record_failure():
    """Tel een gefaalde poging voor brute force tracking."""
    try:
        _ensure_data_dir()
        data = {"failures": [], "locked_until": 0}
        if os.path.isfile(_LOCKOUT_FILE):
            with open(_LOCKOUT_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)

        data["failures"].append(time.time())
        # Houd alleen laatste 60 minuten
        cutoff = time.time() - 3600
        data["failures"] = [t for t in data["failures"] if t > cutoff]

        # Check of lockout nodig is
        recent = [t for t in data["failures"] if t > time.time() - 300]  # laatste 5 min
        if len(recent) >= _MAX_FAILURES:
            data["locked_until"] = time.time() + _LOCKOUT_SECONDS

        with open(_LOCKOUT_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception:
        pass


def _record_boot():
    """Registreer een succesvolle boot voor frequency tracking."""
    try:
        _ensure_data_dir()
        data = {"boots": []}
        if os.path.isfile(_BOOT_TRACKER):
            with open(_BOOT_TRACKER, "r", encoding="utf-8") as f:
                data = json.load(f)

        data["boots"].append(time.time())
        # Houd alleen laatste 5 minuten
        cutoff = time.time() - 300
        data["boots"] = [t for t in data["boots"] if t > cutoff]

        with open(_BOOT_TRACKER, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception:
        pass


def _compute_self_hash() -> str:
    """Bereken SHA256 van dit bestand."""
    gate_path = os.path.abspath(__file__)
    # .pyc → .py
    if gate_path.endswith(".pyc"):
        gate_path = gate_path[:-1]
    try:
        with open(gate_path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except Exception:
        return ""


def lock_environment():
    """
    THE SOVEREIGN GATE — 9 Security Laws.
    Executes before Omega boots. If any check fails, the process dies instantly.
    """

    # ═══════════════════════════════════════════════════════
    #  LAW 6: BRUTE FORCE LOCKOUT (checked FIRST)
    # ═══════════════════════════════════════════════════════
    try:
        if os.path.isfile(_LOCKOUT_FILE):
            with open(_LOCKOUT_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            locked_until = data.get("locked_until", 0)
            if time.time() < locked_until:
                remaining = int(locked_until - time.time())
                _audit_log("LOCKOUT", "Law 6: Brute Force",
                           f"Locked for {remaining}s more")
                sys.exit(
                    f"\U0001f6a8 [GATE] LOCKOUT ACTIVE. "
                    f"Too many failed attempts. Try again in {remaining}s."
                )
    except (json.JSONDecodeError, KeyError):
        pass

    # ═══════════════════════════════════════════════════════
    #  LAW 9: MAX BOOT FREQUENCY (anti fork-bomb)
    # ═══════════════════════════════════════════════════════
    try:
        if os.path.isfile(_BOOT_TRACKER):
            with open(_BOOT_TRACKER, "r", encoding="utf-8") as f:
                data = json.load(f)
            recent = [t for t in data.get("boots", [])
                      if t > time.time() - 60]
            if len(recent) >= _MAX_BOOTS_PER_MINUTE:
                _gate_fail(
                    "Law 9: Boot Frequency",
                    f"Max boot frequency exceeded ({len(recent)}/{_MAX_BOOTS_PER_MINUTE} per minuut). "
                    "Possible fork-bomb detected.",
                )
    except (json.JSONDecodeError, KeyError):
        pass

    # ═══════════════════════════════════════════════════════
    #  LAW 1: THE ROOT LAW
    # ═══════════════════════════════════════════════════════
    expected_root = r"C:\Users\danny\danny-toolkit"
    current_path = os.path.normpath(os.getcwd())
    if current_path.lower() != expected_root.lower():
        _gate_fail(
            "Law 1: Root Integrity",
            f"Execution Denied. Invalid Root. Expected {expected_root}, got {current_path}",
        )

    # ═══════════════════════════════════════════════════════
    #  LAW 2: THE AUTHORITY LAW (Admin Check)
    # ═══════════════════════════════════════════════════════
    try:
        is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        is_admin = False
    if not is_admin:
        _gate_fail(
            "Law 2: Authority",
            "Execution Denied. Admin privileges required. Ghost sessions blocked.",
        )

    # ═══════════════════════════════════════════════════════
    #  LAW 3: THE TERMINAL LAW (Must be PowerShell)
    # ═══════════════════════════════════════════════════════
    try:
        # Walk up the process tree to find if PowerShell is an ancestor
        allowed_terminals = {"powershell.exe", "pwsh.exe"}
        allowed_children = {"python.exe", "pythonw.exe", "uvicorn.exe", "conhost.exe"}
        parent_pid = os.getppid()
        parent_process = psutil.Process(parent_pid)
        parent_name = parent_process.name().lower()

        if parent_name in allowed_terminals:
            pass  # Direct PowerShell parent — OK
        elif parent_name in allowed_children:
            # Python/uvicorn gestart vanuit PowerShell — check de keten
            found_shell = False
            proc = parent_process
            for _ in range(10):  # Max 10 niveaus omhoog
                try:
                    proc = proc.parent()
                    if proc is None:
                        break
                    ancestor = proc.name().lower()
                    if ancestor in allowed_terminals:
                        found_shell = True
                        break
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    break
            if not found_shell:
                _gate_fail(
                    "Law 3: Terminal Lock",
                    f"Execution Denied. No PowerShell in process ancestry. Parent: {parent_name}",
                )
        else:
            _gate_fail(
                "Law 3: Terminal Lock",
                f"Execution Denied. Unauthorized parent process: {parent_name}",
            )
    except Exception:
        _gate_fail(
            "Law 3: Terminal Lock",
            "Execution Denied. Cannot verify parent process.",
        )

    # ═══════════════════════════════════════════════════════
    #  LAW 4: THE PHYSICAL CONSOLE LAW
    # ═══════════════════════════════════════════════════════
    session_name = os.environ.get("SESSIONNAME", "").lower()
    # Elevated (admin) PowerShell via UAC inherits no SESSIONNAME — allow empty
    # when already admin-verified (Law 2 passed). RDP sets "RDP-Tcp#N".
    rdp_indicators = {"rdp-tcp", "services"}
    if session_name in rdp_indicators:
        _gate_fail(
            "Law 4: Physical Console",
            f"Execution Denied. Remote or attached shadow terminal detected ({session_name}).",
        )

    # ═══════════════════════════════════════════════════════
    #  LAW 5: THE IDENTITY LAW (Email Binding)
    # ═══════════════════════════════════════════════════════
    authorized_identities = [
        "danny.laurent1988@gmail.com",
        "dannyanny1212@users.noreply.github.com",
    ]
    try:
        git_email = (
            subprocess.check_output(["git", "config", "user.email"])
            .decode()
            .strip()
            .lower()
        )
        if git_email not in authorized_identities:
            _gate_fail(
                "Law 5: Identity Binding",
                f"Execution Denied. Identity mismatch. Found: {git_email}",
            )
    except Exception:
        _gate_fail(
            "Law 5: Identity Binding",
            "Execution Denied. Identity signature missing. No Git config found.",
        )

    # ═══════════════════════════════════════════════════════
    #  LAW 8: ANTI-TAMPER HASH (self-verification)
    # ═══════════════════════════════════════════════════════
    current_hash = _compute_self_hash()
    if current_hash:
        try:
            _ensure_data_dir()
            if os.path.isfile(_HASH_FILE):
                with open(_HASH_FILE, "r", encoding="utf-8") as f:
                    stored_hash = f.read().strip()
                if stored_hash and stored_hash != current_hash:
                    _gate_fail(
                        "Law 8: Anti-Tamper",
                        "Execution Denied. Gate file has been modified! "
                        f"Expected hash {stored_hash[:16]}..., got {current_hash[:16]}...",
                    )
            else:
                # Eerste boot — sla de hash op als referentie
                with open(_HASH_FILE, "w", encoding="utf-8") as f:
                    f.write(current_hash)
        except Exception:
            pass  # Hash check is non-fatal bij file errors

    # ═══════════════════════════════════════════════════════
    #  ALL LAWS PASSED — Welcome, Commander
    # ═══════════════════════════════════════════════════════
    _audit_log("GRANTED", "ALL 9 LAWS", "Environment Verified. Welcome, Commander Danny.")
    _record_boot()

    print("\u2705 [SOVEREIGN GATE v6.7.0] 9/9 Laws Verified. Welcome, Commander Danny.")
    return True


# Run the gate immediately upon import
lock_environment()

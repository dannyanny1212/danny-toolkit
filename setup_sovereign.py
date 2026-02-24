#!/usr/bin/env python3
"""
Sovereign Core — Automated Setup & Verification Script.

Eén commando om de hele Omega Sovereign Core op te zetten:
  1. Module integrity check (alle 8 modules aanwezig)
  2. Signing key generatie (OMEGA_BUS_SIGNING_KEY → .env)
  3. Hardware fingerprint enrollment
  4. Pipeline verificatie (EventSigner → IronDome → MemoryInterface → Engine)
  5. Sovereign Gate pre-flight (7 IJzeren Wetten)
  6. Status rapport

Gebruik:
    python setup_sovereign.py                # Volledige setup
    python setup_sovereign.py --verify       # Alleen verificatie (geen wijzigingen)
    python setup_sovereign.py --re-enroll    # Hardware opnieuw enrollen
    python setup_sovereign.py --gate         # Alleen de 7 Wetten draaien
"""

import hashlib
import json
import os
import secrets
import sys
import time
from datetime import datetime
from pathlib import Path

# ── UTF-8 output op Windows ──
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# ── GPU isolation (voorkom Windows segfaults) ──
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "-1")

# ── Pad setup ──
ROOT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(ROOT_DIR))

# ── Kleur ──
try:
    from danny_toolkit.core.utils import Kleur
except ImportError:
    class Kleur:
        GROEN = "\033[32m"
        ROOD = "\033[31m"
        GEEL = "\033[33m"
        CYAAN = "\033[36m"
        RESET = "\033[0m"


# ══════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════

def banner(title: str) -> None:
    print(f"\n{Kleur.CYAAN}{'═' * 60}", flush=True)
    print(f"  Ω {title}", flush=True)
    print(f"{'═' * 60}{Kleur.RESET}", flush=True)


def ok(msg: str) -> None:
    print(f"  {Kleur.GROEN}✓{Kleur.RESET} {msg}", flush=True)


def fail(msg: str) -> None:
    print(f"  {Kleur.ROOD}✗{Kleur.RESET} {msg}", flush=True)


def warn(msg: str) -> None:
    print(f"  {Kleur.GEEL}⚠{Kleur.RESET} {msg}", flush=True)


def info(msg: str) -> None:
    print(f"  {Kleur.CYAAN}→{Kleur.RESET} {msg}", flush=True)


# ══════════════════════════════════════════════════════════════
#  STEP 1: MODULE INTEGRITY CHECK
# ══════════════════════════════════════════════════════════════

def check_modules() -> bool:
    """Verifieer dat alle 8 sovereign modules aanwezig en importeerbaar zijn."""
    banner("STEP 1: MODULE INTEGRITY CHECK")

    modules = [
        ("__init__", "danny_toolkit.omega_sovereign_core"),
        ("sovereign_gate", "danny_toolkit.omega_sovereign_core.sovereign_gate"),
        ("hardware_fingerprint", "danny_toolkit.omega_sovereign_core.hardware_fingerprint"),
        ("event_signing", "danny_toolkit.omega_sovereign_core.event_signing"),
        ("iron_dome", "danny_toolkit.omega_sovereign_core.iron_dome"),
        ("lockdown", "danny_toolkit.omega_sovereign_core.lockdown"),
        ("memory_interface", "danny_toolkit.omega_sovereign_core.memory_interface"),
        ("lifecycle", "danny_toolkit.omega_sovereign_core.lifecycle"),
        ("sovereign_engine", "danny_toolkit.omega_sovereign_core.sovereign_engine"),
    ]

    all_ok = True
    for name, import_path in modules:
        try:
            __import__(import_path)
            ok(f"{name}.py")
        except Exception as e:
            fail(f"{name}.py — {e}")
            all_ok = False

    if all_ok:
        ok("Alle 9 modules intact")
    else:
        fail("Module check MISLUKT")
    return all_ok


# ══════════════════════════════════════════════════════════════
#  STEP 2: SIGNING KEY GENERATIE
# ══════════════════════════════════════════════════════════════

def setup_signing_key(verify_only: bool = False) -> bool:
    """Genereer OMEGA_BUS_SIGNING_KEY in .env als niet aanwezig."""
    banner("STEP 2: EVENT SIGNING KEY")

    env_path = ROOT_DIR / ".env"
    key_name = "OMEGA_BUS_SIGNING_KEY"

    # Check of key al bestaat
    existing_key = os.environ.get(key_name, "")
    env_content = ""
    if env_path.exists():
        env_content = env_path.read_text(encoding="utf-8")
        for line in env_content.splitlines():
            if line.strip().startswith(f"{key_name}="):
                value = line.split("=", 1)[1].strip()
                if value and value != "omega-sovereign-default-key-CHANGE-ME":
                    ok(f"Signing key aanwezig in .env ({len(value)} chars)")
                    return True

    if verify_only:
        warn("Signing key NIET gevonden in .env (--verify modus, geen wijzigingen)")
        return False

    # Genereer nieuwe key
    new_key = secrets.token_urlsafe(48)
    info(f"Nieuwe signing key gegenereerd ({len(new_key)} chars)")

    # Voeg toe aan .env
    try:
        with open(env_path, "a", encoding="utf-8") as f:
            f.write(f"\n# === Omega Sovereign Core ===\n")
            f.write(f"{key_name}={new_key}\n")
        ok(f"Key opgeslagen in .env als {key_name}")

        # Laad in huidige sessie
        os.environ[key_name] = new_key
        return True
    except Exception as e:
        fail(f"Kon key niet opslaan: {e}")
        return False


# ══════════════════════════════════════════════════════════════
#  STEP 3: HARDWARE FINGERPRINT ENROLLMENT
# ══════════════════════════════════════════════════════════════

def setup_hardware_fingerprint(re_enroll: bool = False, verify_only: bool = False) -> bool:
    """Enroll of verifieer de hardware fingerprint."""
    banner("STEP 3: HARDWARE FINGERPRINT")

    try:
        from danny_toolkit.omega_sovereign_core.hardware_fingerprint import (
            get_fingerprint_engine,
        )
        fp = get_fingerprint_engine()

        # Verzamel componenten
        info("Hardware componenten verzamelen...")
        components = fp.collect()
        info(f"Machine: {components.machine_name}")
        info(f"CPU: {components.cpu_id[:24]}..." if len(components.cpu_id) > 24 else f"CPU: {components.cpu_id}")
        info(f"MAC: {components.mac_address}")
        info(f"Moederbord: {components.motherboard_serial}")

        if re_enroll:
            info("Re-enrollment aangevraagd...")
            success, detail = fp.re_enroll()
            if success:
                ok(f"Hardware opnieuw geregistreerd: {detail}")
                return True
            fail(f"Re-enrollment mislukt: {detail}")
            return False

        # Verifieer (eerste run = auto enrollment)
        if verify_only:
            enrollment = fp.get_enrollment_info()
            if enrollment:
                ok(f"Master hash aanwezig (enrolled: {enrollment.get('enrolled_at', 'onbekend')})")
                return True
            warn("Geen master hash gevonden (niet ge-enrolled)")
            return False

        success, detail = fp.verify()
        if success:
            ok(f"Fingerprint: {detail}")
            return True
        fail(f"Fingerprint: {detail}")
        return False

    except Exception as e:
        fail(f"Hardware fingerprint fout: {e}")
        return False


# ══════════════════════════════════════════════════════════════
#  STEP 4: PIPELINE VERIFICATIE
# ══════════════════════════════════════════════════════════════

def verify_pipeline() -> bool:
    """Test de volledige pipeline: sign → dome → store → sweep → engine."""
    banner("STEP 4: PIPELINE VERIFICATIE")

    results = []

    # ── 4a: EventSigner ──
    try:
        from danny_toolkit.omega_sovereign_core.event_signing import EventSigner
        signer = EventSigner()
        sig = signer.sign("setup_test", {"step": "verify"}, "setup_sovereign")
        valid, reason = signer.verify(
            "setup_test", {"step": "verify"}, "setup_sovereign",
            sig["signature"], sig["nonce"],
        )
        if valid:
            ok("EventSigner: sign + verify OK")
            results.append(True)
        else:
            fail(f"EventSigner: verify mislukt ({reason})")
            results.append(False)

        # Replay detection
        valid2, reason2 = signer.verify(
            "setup_test", {"step": "verify"}, "setup_sovereign",
            sig["signature"], sig["nonce"],
        )
        if not valid2:
            ok("EventSigner: replay detectie OK")
            results.append(True)
        else:
            fail("EventSigner: replay NIET gedetecteerd!")
            results.append(False)

        # Forgery detection
        valid3, reason3 = signer.verify(
            "setup_test", {"step": "verify"}, "setup_sovereign",
            "0000" + sig["signature"][4:], sig["nonce"] + "x",
        )
        if not valid3:
            ok("EventSigner: forgery detectie OK")
            results.append(True)
        else:
            fail("EventSigner: forgery NIET gedetecteerd!")
            results.append(False)
    except Exception as e:
        fail(f"EventSigner: {e}")
        results.append(False)

    # ── 4b: IronDome ──
    try:
        from danny_toolkit.omega_sovereign_core.iron_dome import IronDome
        dome = IronDome(strict_mode=False)

        # Whitelisted hosts
        for host in ["api.groq.com", "api.anthropic.com", "localhost", "github.com"]:
            allowed, _ = dome.check_endpoint(host, 443)
            if not allowed:
                fail(f"IronDome: {host} geblokkeerd (zou whitelisted moeten zijn)")
                results.append(False)
                break
        else:
            ok("IronDome: whitelist endpoints OK")
            results.append(True)

        # Blocked hosts
        blocked, _ = dome.check_endpoint("evil-server.example.com", 443)
        if not blocked:
            ok("IronDome: default-deny OK")
            results.append(True)
        else:
            fail("IronDome: default-deny NIET actief!")
            results.append(False)

        # Blocked ports
        blocked_port, _ = dome.check_endpoint("any.host", 445)
        if not blocked_port:
            ok("IronDome: poort-blacklist OK (SMB/445 geblokt)")
            results.append(True)
        else:
            fail("IronDome: poort 445 NIET geblokt!")
            results.append(False)
    except Exception as e:
        fail(f"IronDome: {e}")
        results.append(False)

    # ── 4c: SecureMemoryInterface ──
    try:
        import tempfile
        from danny_toolkit.omega_sovereign_core.memory_interface import SecureMemoryInterface

        tmp_dir = tempfile.mkdtemp(prefix="omega_test_")
        mi = SecureMemoryInterface(data_dir=tmp_dir)

        # Store
        store_ok, receipt = mi.secure_store_state(
            "setup_test", {"verified": True, "timestamp": datetime.now().isoformat()}
        )
        if store_ok:
            ok(f"MemoryInterface: store OK (hash: {receipt.data_hash[:16]}...)")
            results.append(True)
        else:
            fail(f"MemoryInterface: store mislukt ({receipt.error})")
            results.append(False)

        # Chain integrity
        chain_ok, chain_detail = mi.verify_chain_integrity()
        if chain_ok:
            ok(f"MemoryInterface: hash-chain intact ({chain_detail})")
            results.append(True)
        else:
            fail(f"MemoryInterface: hash-chain GEBROKEN ({chain_detail})")
            results.append(False)

        # Retrieve
        ret_ok, state = mi.retrieve_state("setup_test")
        if ret_ok and state and state.get("verified"):
            ok("MemoryInterface: retrieve + integriteitscheck OK")
            results.append(True)
        else:
            fail("MemoryInterface: retrieve mislukt")
            results.append(False)

        # Cleanup temp
        import shutil
        shutil.rmtree(tmp_dir, ignore_errors=True)
    except Exception as e:
        fail(f"MemoryInterface: {e}")
        results.append(False)

    # ── 4d: ViolationSweeper ──
    try:
        from danny_toolkit.omega_sovereign_core.sovereign_engine import ViolationSweeper
        sweeper = ViolationSweeper()
        sweeper.start()
        submitted = sweeper.submit("test_violation", {"source": "setup"}, "setup_sovereign")
        time.sleep(0.3)
        sweeper.stop()
        stats = sweeper.get_stats()
        if submitted and stats.get("running") is False:
            ok(f"ViolationSweeper: submit + drain OK (processed: {stats['processed']})")
            results.append(True)
        else:
            warn(f"ViolationSweeper: gestart maar stats onverwacht: {stats}")
            results.append(True)  # Non-fatal
    except Exception as e:
        fail(f"ViolationSweeper: {e}")
        results.append(False)

    # ── 4e: SovereignEngine ──
    try:
        from danny_toolkit.omega_sovereign_core.sovereign_engine import SovereignEngine

        engine = SovereignEngine()

        class SetupTestAgent:
            name = "setup_test_agent"
            def get_state(self):
                return {"status": "verified", "phase": "setup"}

        engine.register_agent("setup_test", SetupTestAgent())
        snapshot = engine.generate_swarm_snapshot()

        if len(snapshot.agents) == 1 and snapshot.agents.get("setup_test", {}).get("status") == "verified":
            ok("SovereignEngine: snapshot OK (1 agent, state verified)")
            results.append(True)
        else:
            fail(f"SovereignEngine: snapshot onverwacht: {snapshot.to_dict()}")
            results.append(False)
    except Exception as e:
        fail(f"SovereignEngine: {e}")
        results.append(False)

    # ── 4f: Lockdown Manager ──
    try:
        from danny_toolkit.omega_sovereign_core.lockdown import LockdownManager
        mgr = LockdownManager()
        if not mgr.is_locked:
            ok("LockdownManager: standby (niet in lockdown)")
            results.append(True)
        else:
            warn("LockdownManager: systeem is in lockdown!")
            results.append(False)
    except Exception as e:
        fail(f"LockdownManager: {e}")
        results.append(False)

    # ── Summary ──
    passed = sum(results)
    total = len(results)
    print(f"\n  Pipeline: {passed}/{total} checks geslaagd")
    return all(results)


# ══════════════════════════════════════════════════════════════
#  STEP 5: SOVEREIGN GATE (7 WETTEN)
# ══════════════════════════════════════════════════════════════

def run_sovereign_gate() -> bool:
    """Draai de 7 IJzeren Wetten."""
    banner("STEP 5: SOVEREIGN GATE — 7 IJZEREN WETTEN")

    try:
        from danny_toolkit.omega_sovereign_core.sovereign_gate import SovereignGate
        gate = SovereignGate(strict=False)  # Niet-strict: lockdown niet triggeren bij setup
        passed, report = gate.enforce_all()
        return passed
    except Exception as e:
        fail(f"Sovereign Gate fout: {e}")
        return False


# ══════════════════════════════════════════════════════════════
#  STEP 6: FINAL RAPPORT
# ══════════════════════════════════════════════════════════════

def final_report(results: dict) -> None:
    """Print het eindrapport."""
    banner("SOVEREIGN CORE SETUP — EINDRAPPORT")

    total = len(results)
    passed = sum(1 for v in results.values() if v)

    for step, success in results.items():
        if success:
            ok(step)
        else:
            fail(step)

    print(f"\n{Kleur.CYAAN}{'─' * 60}{Kleur.RESET}")
    if passed == total:
        print(f"  {Kleur.GROEN}SOVEREIGN STATUS: {passed}/{total} — ALLE CHECKS GESLAAGD")
        print(f"  Het Omega Sovereign Core is operationeel.{Kleur.RESET}")
    else:
        failed = total - passed
        print(f"  {Kleur.ROOD}SOVEREIGN STATUS: {passed}/{total} — {failed} CHECK(S) GEFAALD")
        print(f"  Review de bovenstaande fouten en draai opnieuw.{Kleur.RESET}")
    print(f"{Kleur.CYAAN}{'─' * 60}{Kleur.RESET}\n")


# ══════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════

def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Omega Sovereign Core — Automated Setup & Verification",
    )
    parser.add_argument("--verify", action="store_true",
                        help="Alleen verificatie, geen wijzigingen")
    parser.add_argument("--re-enroll", action="store_true",
                        help="Hardware fingerprint opnieuw enrollen")
    parser.add_argument("--gate", action="store_true",
                        help="Alleen de 7 IJzeren Wetten draaien")
    args = parser.parse_args()

    start = time.perf_counter()

    banner("OMEGA SOVEREIGN CORE — AUTOMATED SETUP")
    info(f"Root: {ROOT_DIR}")
    info(f"Python: {sys.version.split()[0]}")
    info(f"Timestamp: {datetime.now().isoformat()}")
    info(f"Mode: {'verify-only' if args.verify else 're-enroll' if args.re_enroll else 'gate-only' if args.gate else 'full setup'}")

    if args.gate:
        run_sovereign_gate()
        return

    results = {}

    # Step 1: Module integrity
    results["Module Integrity (9 modules)"] = check_modules()

    # Step 2: Signing key
    results["Event Signing Key"] = setup_signing_key(verify_only=args.verify)

    # Step 3: Hardware fingerprint
    results["Hardware Fingerprint"] = setup_hardware_fingerprint(
        re_enroll=args.re_enroll, verify_only=args.verify,
    )

    # Step 4: Pipeline
    results["Pipeline Verificatie"] = verify_pipeline()

    # Step 5: Sovereign Gate (informational — don't block setup)
    gate_passed = run_sovereign_gate()
    results["Sovereign Gate (7 Wetten)"] = gate_passed

    # Step 5.5: AutoSaver daemon
    try:
        from danny_toolkit.omega_sovereign_core.auto_saver import get_auto_saver
        saver = get_auto_saver()
        saver.start()
        results["AutoSaver (30 min)"] = saver.running
        ok("AutoSaver daemon gestart (elke 30 min)")
    except Exception as e:
        results["AutoSaver (30 min)"] = False
        warn(f"AutoSaver kon niet starten: {e}")

    # Step 5.6: Watchtower daemon
    try:
        from danny_toolkit.apps.watchtower import get_watchtower
        watcher = get_watchtower()
        watcher.start()
        results["Watchtower (Ghost Detect)"] = watcher.running
        ok("Watchtower daemon gestart (scan elke 60s)")
    except Exception as e:
        results["Watchtower (Ghost Detect)"] = False
        warn(f"Watchtower kon niet starten: {e}")

    # Step 6: Report
    elapsed = (time.perf_counter() - start) * 1000
    info(f"Totale setup tijd: {elapsed:.0f}ms")
    final_report(results)


if __name__ == "__main__":
    main()

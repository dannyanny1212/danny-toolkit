"""
Omega Sovereign Core v3.0 — Unified Sovereign Package.

De complete kern van Project Omega. Eén import voor alles:
    from danny_toolkit.omega_sovereign_core import boot_sovereign

boot_sovereign() start het volledige systeem:
  1. Sovereign Gate (11 Laws)
  2. NeuralBus + OmegaSeal (Aegis)
  3. CorticalStack (geheugen)
  4. SwarmEngine (agents)
  5. HeartbeatDaemon (achtergrond)
  6. FastAPI (uvicorn daemon thread)

Submodules (lazy loaded):
    sovereign_gate, hardware_fingerprint, event_signing,
    iron_dome, lockdown, memory_interface, lifecycle,
    sovereign_engine, auto_saver
"""

from __future__ import annotations

import logging
import threading

logger = logging.getLogger(__name__)

__all__ = [
    # Submodules
    "sovereign_gate",
    "hardware_fingerprint",
    "event_signing",
    "iron_dome",
    "lockdown",
    "memory_interface",
    "lifecycle",
    "sovereign_engine",
    "auto_saver",
    # Unified boot
    "boot_sovereign",
]

__version__ = "3.0.0"
__author__ = "Danny"


def __getattr__(name: str):
    """Lazy submodule loading — voorkomt circulaire imports."""
    if name in __all__ and name != "boot_sovereign":
        import importlib
        return importlib.import_module(f".{name}", __name__)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def boot_sovereign(
    start_api: bool = True,
    start_daemon: bool = True,
    api_port: int = 8001,
) -> dict:
    """Boot het volledige Omega Sovereign systeem.

    Eén functie die alles opstart in de juiste volgorde.
    Kan aangeroepen worden vanuit omega_sovereign_app.py of standalone.

    Args:
        start_api: Start FastAPI via uvicorn daemon thread.
        start_daemon: Start HeartbeatDaemon in achtergrond thread.
        api_port: Poort voor FastAPI server.

    Returns:
        Dict met status van elk subsysteem.
    """
    import time
    status = {}

    # 1. NeuralBus + OmegaSeal
    try:
        from danny_toolkit.core.neural_bus import get_bus
        bus = get_bus()
        stats = bus.statistieken()
        status["neural_bus"] = {
            "ok": True,
            "armed": stats.get("omega_seal_armed", False),
            "hardware_bound": stats.get("hardware_bound", False),
        }
        logger.info("[SOVEREIGN] NeuralBus: armed=%s", stats.get("omega_seal_armed"))
    except Exception as e:
        status["neural_bus"] = {"ok": False, "error": str(e)[:80]}
        logger.debug("[SOVEREIGN] NeuralBus failed: %s", e)

    # 2. CorticalStack
    try:
        from danny_toolkit.brain.cortical_stack import get_cortical_stack
        cs = get_cortical_stack()
        cs.log_event(actor="sovereign_boot", action="boot_start", details=status)
        status["cortical_stack"] = {"ok": True}
        logger.info("[SOVEREIGN] CorticalStack: OK")
    except Exception as e:
        status["cortical_stack"] = {"ok": False, "error": str(e)[:80]}

    # 3. FastAPI (uvicorn daemon thread)
    if start_api:
        try:
            import socket
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                if s.connect_ex(("127.0.0.1", api_port)) == 0:
                    status["api"] = {"ok": True, "url": f"http://localhost:{api_port}", "mode": "already_running"}
                else:
                    import uvicorn
                    from fastapi_server import app as sovereign_api
                    config = uvicorn.Config(sovereign_api, host="127.0.0.1", port=api_port, log_level="warning")
                    server = uvicorn.Server(config)
                    api_thread = threading.Thread(target=server.run, daemon=True, name="uvicorn-sovereign")
                    api_thread.start()
                    time.sleep(2.0)
                    status["api"] = {"ok": True, "url": f"http://localhost:{api_port}", "mode": "in_process"}
                    logger.info("[SOVEREIGN] API: http://localhost:%d (in-process)", api_port)
        except Exception as e:
            status["api"] = {"ok": False, "error": str(e)[:80]}
    else:
        status["api"] = {"ok": True, "mode": "disabled"}

    # 4. HeartbeatDaemon (headless background thread — geen Rich Live)
    if start_daemon:
        try:
            from danny_toolkit.daemon.heartbeat import HeartbeatDaemon
            daemon = HeartbeatDaemon()
            daemon_thread = threading.Thread(
                target=daemon.start_headless, daemon=True, name="heartbeat-sovereign",
            )
            daemon_thread.start()
            status["daemon"] = {"ok": True, "mode": "headless"}
            logger.info("[SOVEREIGN] HeartbeatDaemon: headless started")
        except Exception as e:
            status["daemon"] = {"ok": False, "error": str(e)[:80]}
    else:
        status["daemon"] = {"ok": True, "mode": "disabled"}

    # 5. Summary
    ok_count = sum(1 for v in status.values() if v.get("ok"))
    total = len(status)
    status["summary"] = f"{ok_count}/{total} systems online"

    logger.info("[SOVEREIGN] Boot complete: %s", status["summary"])
    return status

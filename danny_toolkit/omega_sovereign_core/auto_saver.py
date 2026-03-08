"""
AUTO SAVER — Periodieke State Backup Daemon
=============================================

Daemon thread die elke 30 minuten automatisch:
  1. CorticalStack flush() + backup(compress=True)
  2. Hash-chain integriteit snapshot
  3. NeuralBus SYSTEM_EVENT publiceert

Start:
    from danny_toolkit.omega_sovereign_core.auto_saver import get_auto_saver
    saver = get_auto_saver()
    saver.start()

Stop:
    saver.stop()
"""

from __future__ import annotations

import atexit
import logging
import os
import threading
import time
from datetime import datetime
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

try:
    from danny_toolkit.core.utils import Kleur
except ImportError:
    class Kleur:
        GROEN = ROOD = GEEL = CYAAN = RESET = ""

try:
    from danny_toolkit.core.config import Config
    _DATA_DIR = Config.DATA_DIR
except ImportError:
    from pathlib import Path
    _DATA_DIR = Path(__file__).parent.parent.parent / "data"

# ── Constanten ──

_DEFAULT_INTERVAL_SEC = 30 * 60  # 30 minuten
_MIN_INTERVAL_SEC = 60           # Minimum 1 minuut (safety)


class AutoSaver:
    """Periodieke state backup daemon (daemon thread).

    Voert elke ``interval_sec`` seconden uit:
    1. CorticalStack ``flush()`` + ``backup(compress=True)``
    2. Hash-chain integriteit controle
    3. NeuralBus ``SYSTEM_EVENT`` publicatie

    De thread is een daemon thread — sterft automatisch bij
    proces-exit. ``atexit`` handler voert een laatste flush uit.

    Args:
        interval_sec: Interval in seconden (default 1800 = 30 min).
    """

    def __init__(self, interval_sec: int = _DEFAULT_INTERVAL_SEC) -> None:
        """Init  ."""
        self._interval = max(interval_sec, _MIN_INTERVAL_SEC)
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._stats = {
            "cycles": 0,
            "last_save": None,
            "last_error": None,
            "errors": 0,
            "cortical_flushes": 0,
            "cortical_backups": 0,
            "bus_publishes": 0,
        }

        # Lazy backend refs
        self._stack = None
        self._bus = None
        self._backends_loaded = False

    # ── Backend Loading ──

    def _ensure_backends(self) -> None:
        """Lazy-load CorticalStack en NeuralBus."""
        if self._backends_loaded:
            return
        self._backends_loaded = True

        if os.environ.get("DANNY_TEST_MODE") == "1":
            return

        try:
            from danny_toolkit.brain.cortical_stack import get_cortical_stack
            self._stack = get_cortical_stack()
        except ImportError:
            logger.debug("AutoSaver: CorticalStack niet beschikbaar")

        try:
            from danny_toolkit.core.neural_bus import get_bus
            self._bus = get_bus()
        except ImportError:
            logger.debug("AutoSaver: NeuralBus niet beschikbaar")

    # ── Core Cycle ──

    def _save_cycle(self) -> Dict[str, Any]:
        """Eén save cycle: flush, backup, publish.

        Returns:
            Dict met resultaten van deze cycle.
        """
        self._ensure_backends()
        result = {
            "timestamp": datetime.now().isoformat(),
            "flushed": False,
            "backed_up": False,
            "published": False,
            "error": None,
        }

        # 1. CorticalStack flush + backup
        if self._stack:
            try:
                self._stack.flush()
                result["flushed"] = True
                self._stats["cortical_flushes"] += 1
            except Exception as e:
                logger.warning("AutoSaver: flush failed: %s", e)
                result["error"] = f"flush: {e}"

            try:
                backup_path = self._stack.backup(compress=True)
                result["backed_up"] = True
                result["backup_path"] = str(backup_path) if backup_path else None
                self._stats["cortical_backups"] += 1
            except Exception as e:
                logger.warning("AutoSaver: backup failed: %s", e)
                if result["error"]:
                    result["error"] += f"; backup: {e}"
                else:
                    result["error"] = f"backup: {e}"

        # 2. Hash-chain integriteit check
        try:
            from danny_toolkit.omega_sovereign_core.memory_interface import (
                get_memory_interface,
            )
            mi = get_memory_interface()
            chain_stats = mi.statistieken()
            result["chain_length"] = chain_stats.get("chain_length", 0)
        except Exception as e:
            logger.debug("AutoSaver: hash-chain check: %s", e)

        # 3. NeuralBus event
        if self._bus:
            try:
                from danny_toolkit.core.neural_bus import EventTypes
                self._bus.publish(
                    EventTypes.SYSTEM_EVENT,
                    {
                        "type": "auto_save",
                        "flushed": result["flushed"],
                        "backed_up": result["backed_up"],
                        "chain_length": result.get("chain_length", 0),
                        "cycle": self._stats["cycles"],
                    },
                    bron="auto_saver",
                )
                result["published"] = True
                self._stats["bus_publishes"] += 1
            except Exception as e:
                logger.debug("AutoSaver: NeuralBus publish: %s", e)

        # 4. CorticalStack log
        if self._stack:
            try:
                self._stack.log_event(
                    actor="auto_saver",
                    action="periodic_save",
                    details={
                        "cycle": self._stats["cycles"],
                        "flushed": result["flushed"],
                        "backed_up": result["backed_up"],
                    },
                    source="auto_saver",
                )
            except Exception as e:
                logger.debug("AutoSaver: cortical log: %s", e)

        return result

    # ── Thread Loop ──

    def _loop(self) -> None:
        """Daemon thread main loop."""
        logger.info(
            "AutoSaver gestart (interval=%ds)", self._interval
        )
        try:
            print(
                f"{Kleur.CYAAN}[AutoSaver] actief"
                f" (elke {self._interval // 60} min){Kleur.RESET}",
                flush=True,
            )
        except UnicodeEncodeError as e:
            logger.debug("AutoSaver banner print failed: %s", e)

        while not self._stop_event.is_set():
            # Wacht op interval of stop event
            if self._stop_event.wait(timeout=self._interval):
                break  # stop_event gezet

            try:
                result = self._save_cycle()
                self._stats["cycles"] += 1
                self._stats["last_save"] = result["timestamp"]

                if result.get("error"):
                    self._stats["errors"] += 1
                    self._stats["last_error"] = result["error"]
                    logger.warning(
                        "AutoSaver cycle %d: %s",
                        self._stats["cycles"],
                        result["error"],
                    )
                else:
                    logger.info(
                        "AutoSaver cycle %d: OK (flush=%s, backup=%s)",
                        self._stats["cycles"],
                        result["flushed"],
                        result["backed_up"],
                    )

            except Exception as e:
                self._stats["errors"] += 1
                self._stats["last_error"] = str(e)
                logger.error("AutoSaver cycle fout: %s", e)

        logger.info("AutoSaver gestopt na %d cycles", self._stats["cycles"])

    # ── Finale flush bij shutdown ──

    def _atexit_flush(self) -> None:
        """Laatste flush bij proces-exit."""
        try:
            self._ensure_backends()
            if self._stack:
                self._stack.flush()
                logger.info("AutoSaver: finale flush bij shutdown")
        except Exception as e:
            logger.debug("AutoSaver atexit flush: %s", e)

    # ── Public API ──

    def start(self) -> None:
        """Start de auto-save daemon thread."""
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                logger.info("AutoSaver draait al")
                return

            self._stop_event.clear()
            self._thread = threading.Thread(
                target=self._loop,
                name="AutoSaver",
                daemon=True,
            )
            self._thread.start()
            atexit.register(self._atexit_flush)

    def stop(self) -> None:
        """Stop de daemon thread (graceful)."""
        with self._lock:
            if self._thread is None or not self._thread.is_alive():
                return

            self._stop_event.set()
            self._thread.join(timeout=5)
            self._thread = None

        # Finale flush
        self._atexit_flush()

    def force_save(self) -> Dict[str, Any]:
        """Voer onmiddellijk een save cycle uit (handmatig).

        Returns:
            Dict met cycle resultaten.
        """
        result = self._save_cycle()
        self._stats["cycles"] += 1
        self._stats["last_save"] = result["timestamp"]
        if result.get("error"):
            self._stats["errors"] += 1
            self._stats["last_error"] = result["error"]
        return result

    def statistieken(self) -> Dict[str, Any]:
        """Huidige statistieken.

        Returns:
            Dict met cycles, errors, timestamps, interval.
        """
        return {
            **self._stats,
            "interval_sec": self._interval,
            "interval_min": self._interval // 60,
            "running": (
                self._thread is not None
                and self._thread.is_alive()
            ),
        }

    @property
    def running(self) -> bool:
        """Of de daemon thread draait."""
        return self._thread is not None and self._thread.is_alive()


# ── Singleton ──

_instance: Optional[AutoSaver] = None
_singleton_lock = threading.Lock()


def get_auto_saver(interval_sec: int = _DEFAULT_INTERVAL_SEC) -> AutoSaver:
    """Thread-safe singleton factory.

    Args:
        interval_sec: Interval (alleen bij eerste aanroep).

    Returns:
        AutoSaver singleton.
    """
    global _instance
    if _instance is not None:
        return _instance
    with _singleton_lock:
        if _instance is None:
            _instance = AutoSaver(interval_sec=interval_sec)
    return _instance

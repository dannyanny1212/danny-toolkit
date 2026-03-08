"""
Lifecycle Manager — Universal Save Protocol (USP).

DE ENIGE geautoriseerde methode voor elk script om state op te slaan en af te sluiten.
Voorkomt dat de Mind (/brain/) direct de Soul (/data/) aanraakt.

Flow:
    1. Broadcast SYSTEM_SUSPEND over NeuralBus (alle agents pauzeren)
    2. Onderteken de state via EventSigner
    3. Route naar SecureMemoryInterface (hash-chain + archief)
    4. Log naar CorticalStack
    5. Controleer lockdown status

Gebruik:
    from danny_toolkit.omega_sovereign_core.lifecycle import safe_shutdown

    # In elk script's finally-block:
    safe_shutdown(component_name="brain_cli", state_data=agent.get_state())
"""

from __future__ import annotations

import atexit
import logging
import sys
import threading
import time
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    from danny_toolkit.core.utils import Kleur
except ImportError:
    class Kleur:
        GROEN = ROOD = GEEL = CYAAN = RESET = ""


class LifecycleManager:
    """
    Centraal lifecycle management voor alle Omega componenten.

    Beheert:
    - Registratie van componenten (wie draait er?)
    - Gecoördineerde shutdown (in volgorde van afhankelijkheid)
    - Pre-shutdown hooks (agents krijgen kans om state te dumpen)
    - Post-shutdown verificatie (is alles veilig opgeslagen?)
    """

    def __init__(self) -> None:
        """Init  ."""
        self._lock = threading.Lock()
        self._registered: Dict[str, dict] = {}  # component -> metadata
        self._pre_shutdown_hooks: List[Callable] = []
        self._shutdown_in_progress = False
        self._bus = None
        self._signer = None
        self._stack = None

    def _lazy_init(self) -> None:
        """Lazy initialisatie van backends (voorkom import deadlocks)."""
        if self._bus is not None:
            return
        try:
            self._bus = get_bus()
        except (ImportError, Exception) as e:
            logger.debug("NeuralBus niet beschikbaar voor lifecycle: %s", e)
        try:
            self._signer = get_event_signer()
        except (ImportError, Exception) as e:
            logger.debug("EventSigner niet beschikbaar voor lifecycle: %s", e)
        try:
            self._stack = get_cortical_stack()
        except (ImportError, Exception) as e:
            logger.debug("CorticalStack niet beschikbaar voor lifecycle: %s", e)

    # ── Component Registration ──

    def register(self, component_name: str, metadata: Optional[dict] = None) -> None:
        """
        Registreer een actief component bij de lifecycle manager.

        Args:
            component_name: Unieke naam (bijv. "brain_cli", "oracle_agent")
            metadata: Extra info (pid, start_time, etc.)
        """
        with self._lock:
            self._registered[component_name] = {
                "registered_at": datetime.now().isoformat(),
                "metadata": metadata or {},
                "state_saved": False,
            }
        logger.debug("Lifecycle: '%s' geregistreerd", component_name)

    def unregister(self, component_name: str) -> None:
        """Verwijder een component uit de registratie."""
        with self._lock:
            self._registered.pop(component_name, None)

    def add_pre_shutdown_hook(self, hook: Callable[[], None]) -> None:
        """Voeg een hook toe die vóór shutdown wordt aangeroepen."""
        with self._lock:
            self._pre_shutdown_hooks.append(hook)

    # ── Shutdown Protocol ──

    @property
    def is_shutting_down(self) -> bool:
        """Is er een shutdown in uitvoering?"""
        with self._lock:
            return self._shutdown_in_progress

    def get_registered_components(self) -> List[str]:
        """Lijst van actief geregistreerde componenten."""
        with self._lock:
            return list(self._registered.keys())


# ── Module-level singleton ──

_lifecycle: Optional[LifecycleManager] = None
_lifecycle_lock = threading.Lock()


def get_lifecycle_manager() -> LifecycleManager:
    """Verkrijg de singleton LifecycleManager."""
    global _lifecycle
    if _lifecycle is None:
        with _lifecycle_lock:
            if _lifecycle is None:
                _lifecycle = LifecycleManager()
    return _lifecycle


# ══════════════════════════════════════════════════════════════
#  THE UNIVERSAL SAVE PROTOCOL
# ══════════════════════════════════════════════════════════════

def safe_shutdown(
    component_name: str,
    state_data: Optional[dict] = None,
    exit_code: int = 0,
    do_exit: bool = True,
) -> bool:
    """
    DE UNIVERSELE SAVE PROTOCOL.

    De enige geautoriseerde methode voor elk script om state op te slaan
    en het proces veilig af te sluiten. Voorkomt dat de Mind direct
    de Soul aanraakt (Boundary Violation).

    Args:
        component_name: Naam van het afsluitende component
        state_data: Dict met de state die bewaard moet worden (of None)
        exit_code: Process exit code (0 = normaal)
        do_exit: Of sys.exit() aangeroepen moet worden

    Returns:
        True als state succesvol opgeslagen, False bij falen

    Usage in elk script:
        try:
            agent.run()
        except KeyboardInterrupt:
            pass
        finally:
            safe_shutdown("brain_cli", agent.get_state())
    """
    lifecycle = get_lifecycle_manager()

    # Voorkom dubbele shutdown
    if lifecycle.is_shutting_down:
        logger.debug("Shutdown al in uitvoering — overgeslagen voor %s", component_name)
        return False

    with lifecycle._lock:
        lifecycle._shutdown_in_progress = True

    print(f"\n{Kleur.CYAAN}{'─' * 50}")
    print(f"  SOVEREIGN SHUTDOWN PROTOCOL")
    print(f"  Component: {component_name}")
    print(f"{'─' * 50}{Kleur.RESET}")

    success = True

    # ── Step 1: Pre-shutdown hooks ──
    print(f"{Kleur.GEEL}  [1/4] Pre-shutdown hooks uitvoeren...{Kleur.RESET}")
    for hook in lifecycle._pre_shutdown_hooks:
        try:
            hook()
        except Exception as e:
            logger.debug("Pre-shutdown hook fout: %s", e)

    # ── Step 2: Broadcast SYSTEM_SUSPEND ──
    print(f"{Kleur.GEEL}  [2/4] Broadcasting SYSTEM_SUSPEND...{Kleur.RESET}")
    lifecycle._lazy_init()
    if lifecycle._bus:
        try:
            lifecycle._bus.publish(
                event_type="system_event",
                data={
                    "action": "SYSTEM_SUSPEND",
                    "target": component_name,
                    "timestamp": datetime.now().isoformat(),
                },
                bron="lifecycle_manager",
            )
        except Exception as e:
            logger.debug("SYSTEM_SUSPEND broadcast mislukt: %s", e)

    # ── Step 3: Route state naar Soul via Memory Interface ──
    if state_data:
        print(f"{Kleur.GEEL}  [3/4] Routing state naar Soul via Memory Interface...{Kleur.RESET}")
        try:
            ok, receipt = secure_store_state(component_name, state_data)
            if ok:
                print(f"{Kleur.GROEN}  [OK] State veilig opgeslagen "
                      f"(hash: {receipt.data_hash[:16]}...){Kleur.RESET}")
            else:
                print(f"{Kleur.ROOD}  [FAIL] State opslag mislukt: "
                      f"{receipt.error}{Kleur.RESET}")
                success = False
        except Exception as e:
            print(f"{Kleur.ROOD}  [FAIL] Memory Interface fout: {e}{Kleur.RESET}")
            logger.error("Lifecycle state save fout: %s", e)
            success = False
    else:
        print(f"{Kleur.GEEL}  [3/4] Geen state data — overgeslagen{Kleur.RESET}")

    # ── Step 4: CorticalStack log ──
    print(f"{Kleur.GEEL}  [4/4] Logging naar CorticalStack...{Kleur.RESET}")
    if lifecycle._stack:
        try:
            lifecycle._stack.log_event(
                bron="LifecycleManager",
                event_type="sovereign.lifecycle.shutdown",
                data={
                    "component": component_name,
                    "state_saved": success,
                    "exit_code": exit_code,
                    "timestamp": datetime.now().isoformat(),
                },
            )
        except Exception as e:
            logger.debug("CorticalStack lifecycle log mislukt: %s", e)

try:
    from danny_toolkit.omega_sovereign_core.memory_interface import secure_store_state
except ImportError:
    pass
try:
    from danny_toolkit.core.neural_bus import get_bus
except ImportError:
    pass
try:
    from danny_toolkit.omega_sovereign_core.event_signing import get_event_signer
except ImportError:
    pass
try:
    from danny_toolkit.brain.cortical_stack import get_cortical_stack
except ImportError:
    pass

    # ── Final status ──
    if success:
        print(f"\n{Kleur.GROEN}  {component_name} veilig offline.{Kleur.RESET}")
    else:
        print(f"\n{Kleur.ROOD}  {component_name} offline met fouten!{Kleur.RESET}")

    print(f"{Kleur.CYAAN}{'─' * 50}{Kleur.RESET}\n")

    with lifecycle._lock:
        lifecycle._shutdown_in_progress = False

    if do_exit:
        sys.exit(exit_code)

    return success


def register_component(component_name: str, metadata: Optional[dict] = None) -> None:
    """Shortcut: registreer een component bij de lifecycle manager."""
    get_lifecycle_manager().register(component_name, metadata)

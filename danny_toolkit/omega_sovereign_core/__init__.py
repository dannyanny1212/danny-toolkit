"""
Omega Sovereign Core — Hardened Security Package v2.0.

De beveiligingskern van Project Omega. Alle imports zijn lazy
om circulaire import-deadlocks te voorkomen.

Gebruik per module:
    from danny_toolkit.omega_sovereign_core.sovereign_gate import get_sovereign_gate
    from danny_toolkit.omega_sovereign_core.event_signing import get_event_signer
    from danny_toolkit.omega_sovereign_core.iron_dome import get_iron_dome
    from danny_toolkit.omega_sovereign_core.lockdown import get_lockdown_manager
    from danny_toolkit.omega_sovereign_core.memory_interface import secure_store_state
    from danny_toolkit.omega_sovereign_core.lifecycle import safe_shutdown
    from danny_toolkit.omega_sovereign_core.sovereign_engine import get_sovereign_engine
"""

__all__ = [
    # Modules (import individueel)
    "sovereign_gate",
    "hardware_fingerprint",
    "event_signing",
    "iron_dome",
    "lockdown",
    "memory_interface",
    "lifecycle",
    "sovereign_engine",
]

__version__ = "2.0.0"
__author__ = "Danny"

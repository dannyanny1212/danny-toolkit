"""
Memory Interface — Grens-bewaker tussen /core/ en /brain/.

from __future__ import annotations

Core modules importeren HIER vandaan, nooit direct uit /brain/.
Brain modules registreren hun implementaties via register_*().

Dit voorkomt /core/ -> /brain/ imports die de architectuurgrenzen schenden.

Gebruik:
    # In /core/ modules:
    from danny_toolkit.core.memory_interface import log_to_cortical
    log_to_cortical("alerter", "alert_sent", {"niveau": "CRITICAL"})

    # In /brain/ startup:
    from danny_toolkit.core.memory_interface import register_cortical_stack
    register_cortical_stack(get_cortical_stack())
"""

import logging

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Registry — brain modules registreren hun singletons hier
# ------------------------------------------------------------------

_cortical_stack = None
_governor_factory = None
_unified_memory_factory = None


def register_cortical_stack(stack: object) -> None:
    """Registreer CorticalStack singleton (aangeroepen vanuit brain startup)."""
    global _cortical_stack
    _cortical_stack = stack


def register_governor_factory(factory: object) -> None:
    """Registreer OmegaGovernor factory (callable die instantie retourneert)."""
    global _governor_factory
    _governor_factory = factory


def register_unified_memory_factory(factory: object) -> None:
    """Registreer UnifiedMemory factory."""
    global _unified_memory_factory
    _unified_memory_factory = factory


# ------------------------------------------------------------------
# Accessors — core modules gebruiken deze functies
# ------------------------------------------------------------------

def get_cortical_stack() -> None:
    """Haal CorticalStack op als geregistreerd, anders lazy-load poging.

    Returns None als niet beschikbaar.
    """
    global _cortical_stack
    if _cortical_stack is not None:
        return _cortical_stack
    # Lazy-load poging (voor het geval brain nog niet geregistreerd heeft)
    try:
        from danny_toolkit.brain.cortical_stack import (
            get_cortical_stack as _get_stack,
        )
        _cortical_stack = _get_stack()
        return _cortical_stack
    except Exception:
        return None


def get_governor() -> None:
    """Haal OmegaGovernor op via factory, of None."""
    if _governor_factory is not None:
        try:
            return _governor_factory()
        except Exception:
            return None
    # Lazy-load poging
    try:
        from danny_toolkit.brain.governor import OmegaGovernor
        return OmegaGovernor()
    except Exception:
        return None


def get_unified_memory() -> None:
    """Haal UnifiedMemory op via factory, of None."""
    if _unified_memory_factory is not None:
        try:
            return _unified_memory_factory()
        except Exception:
            return None
    try:
        from danny_toolkit.brain.unified_memory import UnifiedMemory
        return UnifiedMemory()
    except Exception:
        return None


# ------------------------------------------------------------------
# Convenience — veelgebruikte operaties (fire-and-forget)
# ------------------------------------------------------------------

def log_to_cortical(actor: object, action: object, details: object=None, source: object="system") -> None:
    """Log event naar CorticalStack als beschikbaar (fire-and-forget).

    Gooit nooit een exception — veilig om overal te gebruiken.
    """
    stack = get_cortical_stack()
    if stack is None:
        return
    try:
        stack.log_event(
            actor=actor,
            action=action,
            details=details,
            source=source,
        )
    except Exception as e:
        logger.debug("Cortical log failed: %s", e)

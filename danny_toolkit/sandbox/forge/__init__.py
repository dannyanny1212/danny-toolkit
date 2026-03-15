"""Sovereign Forge Registry — AI-gegenereerde tools kluis.

Bevat alle door de Artificer gegenereerde en geverifieerde tools.
Dynamisch geladen door forge_loader.py + Artificer execute loop.

v6.19.0: Smart __init__ met expliciete __all__ voor forge discovery.
Nieuwe tools worden automatisch toegevoegd door de Artificer na
Diamond Polish verificatie (score >= 9.0 A+).
"""
from __future__ import annotations

__all__ = [
    "calculator",
    "phoenix_ping",
]

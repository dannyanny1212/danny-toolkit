"""Interfaces module — CLI en Console interfaces."""
from __future__ import annotations

try:
    from danny_toolkit.interfaces.cli import CosmicConsole
    _HAS_CLI = True
except ImportError:
    _HAS_CLI = False

__all__ = []
if _HAS_CLI:
    __all__.append("CosmicConsole")

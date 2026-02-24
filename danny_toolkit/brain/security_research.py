"""
Security & Crypto Research Engine v2.0 — Thin shim.

Alle logica is verplaatst naar danny_toolkit.brain.security/ subpackage.
Dit bestand herexporteert voor backward compatibiliteit.

Consumers: launcher.py, heartbeat.py.
"""

from danny_toolkit.brain.security.config import Ernst, SecurityConfig
from danny_toolkit.brain.security.engine import SecurityResearchEngine

__all__ = ["Ernst", "SecurityConfig", "SecurityResearchEngine"]

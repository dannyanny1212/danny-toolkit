"""
Security subpackage — Re-exports voor backward compatibility.
"""
from __future__ import annotations

from danny_toolkit.brain.security.config import Ernst, SecurityConfig
from danny_toolkit.brain.security.engine import SecurityResearchEngine

__all__ = ["Ernst", "SecurityConfig", "SecurityResearchEngine"]

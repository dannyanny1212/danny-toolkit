"""Agents module — Agent framework + Protocol Cerberus Honeypot.

Actieve agents (wired in SwarmEngine):
    PhantomAgent    — Cerberus Honeypot (Agent 9042), decoy voor inbreukdetectie

Reference implementations (niet actief in SwarmEngine, standalone bruikbaar):
    Agent           — BaseAgent met agentic loop, multi-provider
    Orchestrator    — Multi-agent task queue met workflows
    Tool, ToolRegistry — Tool systeem met permissions en caching
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

from danny_toolkit.agents.base import Agent, AgentMessage, AgentConfig
from danny_toolkit.agents.tool import Tool, ToolRegistry
from danny_toolkit.agents.orchestrator import Orchestrator

try:
    from danny_toolkit.agents.phantom_agent import PhantomAgent, PHANTOM_ID
    _HAS_PHANTOM = True
except ImportError:
    _HAS_PHANTOM = False

__all__ = [
    # Active (wired in SwarmEngine)
    "PhantomAgent",
    "PHANTOM_ID",
    # Reference implementations
    "Agent",
    "AgentMessage",
    "AgentConfig",
    "Tool",
    "ToolRegistry",
    "Orchestrator",
]

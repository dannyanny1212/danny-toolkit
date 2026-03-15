# danny_toolkit/brain/__init__.py
"""
Danny's AI Ecosysteem - Central Brain Module v6.0

Componenten:
- Core Intelligence: CentralBrain, PrometheusBrain, Governor, CorticalStack
- v6.0 Inventions: Strategist, Tribunal, VoidWalker, Artificer, BlackBox, etc.
- Anti-Hallucination: CitationMarshall, RealityAnchor, TruthAnchor
- Subsystems: NexusBridge, VisualNexus, SingularityEngine, etc.
"""

# --- CORE INTELLIGENCE ---
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

from danny_toolkit.brain.central_brain import CentralBrain
from danny_toolkit.brain.trinity_omega import PrometheusBrain
from danny_toolkit.brain.trinity_models import (
    CosmicRole, NodeTier, TaskPriority,
    AgentNode, OmegaSwarm, SwarmMetrics, TaskResult,
)
from danny_toolkit.brain.governor import OmegaGovernor
from danny_toolkit.brain.cortical_stack import CorticalStack, get_cortical_stack
from danny_toolkit.brain.unified_memory import UnifiedMemory

# --- v6.0 INVENTIONS (SELF-EFFICIENCY) ---
# Lazy — heavy deps (groq, sentence-transformers, duckduckgo-search)
try:
    from danny_toolkit.brain.strategist import Strategist
    from danny_toolkit.brain.tribunal import Tribunal
    from danny_toolkit.brain.adversarial_tribunal import AdversarialTribunal
    from danny_toolkit.brain.void_walker import VoidWalker
    from danny_toolkit.brain.artificer import Artificer
    from danny_toolkit.brain.black_box import BlackBox
    from danny_toolkit.brain.the_mirror import TheMirror
    from danny_toolkit.brain.ghost_writer import GhostWriter
    from danny_toolkit.brain.dreamer import Dreamer
    from danny_toolkit.brain.devops_daemon import DevOpsDaemon
    from danny_toolkit.brain.cortex import TheCortex
    from danny_toolkit.brain.oracle_eye import TheOracleEye
    from danny_toolkit.brain.synapse import TheSynapse
    from danny_toolkit.brain.phantom import ThePhantom
    from danny_toolkit.brain.virtual_twin import VirtualTwin, ShadowCortex
    from danny_toolkit.brain.shadow_governance import ShadowGovernance
    from danny_toolkit.brain.shadow_permissions import ShadowPermissions
    from danny_toolkit.brain.waakhuis import WaakhuisMonitor, get_waakhuis
    from danny_toolkit.brain.hallucination_shield import HallucinatieSchild, get_hallucination_shield
    from danny_toolkit.brain.black_box import get_black_box
    from danny_toolkit.brain.adversarial_tribunal import get_adversarial_tribunal
    from danny_toolkit.brain.config_auditor import ConfigAuditor, get_config_auditor
    from danny_toolkit.brain.arbitrator import TaskArbitrator, get_arbitrator, GoalManifest, SwarmTask
    from danny_toolkit.brain.model_sync import (
        ModelWorker, ModelRegistry, get_model_registry,
        ModelProfile, ModelResponse, ModelBid, ModelCapability,
    )
    from danny_toolkit.brain.introspector import SystemIntrospector, get_introspector
    from danny_toolkit.brain.claude_memory import ClaudeMemory, get_claude_memory
    from danny_toolkit.brain.observatory_sync import ObservatorySync, get_observatory_sync
    from danny_toolkit.brain.agent_factory import AgentFactory, get_agent_factory
    from danny_toolkit.brain.oracle import OracleAgent
    from danny_toolkit.brain.ultimate_hunt import UltimateHunt, HuntStatus, HuntAnimator
    from danny_toolkit.brain.dream_monitor import dream_monitor, quick_peek
    from danny_toolkit.brain.ghost_amplifier import GhostAmplifier, get_ghost_amplifier
    from danny_toolkit.brain.sanctuary_dashboard import SanctuaryDashboard, get_sanctuary
    from danny_toolkit.brain.tool_dispatcher import ToolDispatcher, get_tool_dispatcher
except ImportError:
    logger.debug("Optional brain inventions not available (heavy deps)")

# --- ANTI-HALLUCINATION & TRUTH ---
try:
    from danny_toolkit.brain.citation_marshall import CitationMarshall
    from danny_toolkit.brain.reality_anchor import RealityAnchor
    from danny_toolkit.brain.truth_anchor import TruthAnchor
except ImportError:
    logger.debug("Anti-hallucination modules not available")

# --- SUBSYSTEMS & INFRASTRUCTURE ---
from danny_toolkit.brain.nexus_bridge import NexusBridge
from danny_toolkit.brain.visual_nexus import VisualNexus
from danny_toolkit.brain.singularity import SingularityEngine
from danny_toolkit.brain.proactive import ProactiveEngine
from danny_toolkit.brain.file_guard import FileGuard
from danny_toolkit.brain.workflows import WorkflowEngine
from danny_toolkit.brain.project_map import ProjectMap

__all__ = [
    # Core Intelligence
    "CentralBrain", "PrometheusBrain", "OmegaGovernor",
    "CorticalStack", "get_cortical_stack", "UnifiedMemory",
    # Trinity Models
    "CosmicRole", "NodeTier", "TaskPriority",
    "AgentNode", "OmegaSwarm", "SwarmMetrics", "TaskResult",
    # v6.0 Inventions
    "Strategist", "Tribunal", "AdversarialTribunal",
    "VoidWalker", "Artificer", "BlackBox",
    "TheMirror", "GhostWriter", "Dreamer", "DevOpsDaemon",
    "TheCortex", "TheOracleEye", "TheSynapse", "ThePhantom",
    "VirtualTwin", "ShadowCortex",
    "ShadowGovernance", "ShadowPermissions",
    "WaakhuisMonitor", "get_waakhuis",
    "HallucinatieSchild", "get_hallucination_shield",
    "get_black_box", "get_adversarial_tribunal",
    "ConfigAuditor", "get_config_auditor",
    "TaskArbitrator", "get_arbitrator", "GoalManifest", "SwarmTask",
    # Phase 41: Multi-Model Sync
    "ModelWorker", "ModelRegistry", "get_model_registry",
    "ModelProfile", "ModelResponse", "ModelBid", "ModelCapability",
    # Phase 42: Self-Awareness
    "SystemIntrospector", "get_introspector",
    # Phase 42b: Observatory Sync
    "ObservatorySync", "get_observatory_sync",
    # Dynamic Agent Factory
    "AgentFactory", "get_agent_factory",
    # Phase 43: Claude Memory
    "ClaudeMemory", "get_claude_memory",
    # Fase C.3: Agents (moved from /core/)
    "OracleAgent", "UltimateHunt", "HuntStatus", "HuntAnimator",
    # Phase 43: Dream Monitor
    "dream_monitor", "quick_peek",
    # Phase 46: Ghost Amplifier + Sanctuary
    "GhostAmplifier", "get_ghost_amplifier",
    "SanctuaryDashboard", "get_sanctuary",
    # Phase 56: Hierarchical Tool Dispatch
    "ToolDispatcher", "get_tool_dispatcher",
    # Anti-Hallucination
    "CitationMarshall", "RealityAnchor", "TruthAnchor",
    # Subsystems
    "NexusBridge", "VisualNexus", "SingularityEngine",
    "ProactiveEngine", "FileGuard", "WorkflowEngine",
    # Utils
    "ProjectMap",
]

__version__ = "7.1.0"
__author__ = "Danny"

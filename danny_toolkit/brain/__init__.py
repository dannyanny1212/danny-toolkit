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
from .central_brain import CentralBrain
from .trinity_omega import PrometheusBrain
from .trinity_models import (
    CosmicRole, NodeTier, TaskPriority,
    AgentNode, OmegaSwarm, SwarmMetrics, TaskResult,
)
from .governor import OmegaGovernor
from .cortical_stack import CorticalStack, get_cortical_stack
from .unified_memory import UnifiedMemory

# --- v6.0 INVENTIONS (SELF-EFFICIENCY) ---
# Lazy — heavy deps (groq, sentence-transformers, duckduckgo-search)
try:
    from .strategist import Strategist
    from .tribunal import Tribunal
    from .adversarial_tribunal import AdversarialTribunal
    from .void_walker import VoidWalker
    from .artificer import Artificer
    from .black_box import BlackBox
    from .the_mirror import TheMirror
    from .ghost_writer import GhostWriter
    from .dreamer import Dreamer
    from .devops_daemon import DevOpsDaemon
    from .cortex import TheCortex
    from .oracle_eye import TheOracleEye
    from .synapse import TheSynapse
    from .phantom import ThePhantom
    from .virtual_twin import VirtualTwin, ShadowCortex
    from .shadow_governance import ShadowGovernance
    from .shadow_permissions import ShadowPermissions
    from .waakhuis import WaakhuisMonitor, get_waakhuis
    from .hallucination_shield import HallucinatieSchild, get_hallucination_shield
    from .black_box import get_black_box
    from .adversarial_tribunal import get_adversarial_tribunal
    from .config_auditor import ConfigAuditor, get_config_auditor
    from .arbitrator import TaskArbitrator, get_arbitrator, GoalManifest, SwarmTask
    from .model_sync import (
        ModelWorker, ModelRegistry, get_model_registry,
        ModelProfile, ModelResponse, ModelBid, ModelCapability,
    )
    from .introspector import SystemIntrospector, get_introspector
    from .claude_memory import ClaudeMemory, get_claude_memory
    from .observatory_sync import ObservatorySync, get_observatory_sync
    from .agent_factory import AgentFactory, get_agent_factory
    from .oracle import OracleAgent
    from .ultimate_hunt import UltimateHunt, HuntStatus, HuntAnimator
    from .dream_monitor import dream_monitor, quick_peek
    from .ghost_amplifier import GhostAmplifier, get_ghost_amplifier
    from .sanctuary_dashboard import SanctuaryDashboard, get_sanctuary
    from .tool_dispatcher import ToolDispatcher, get_tool_dispatcher
except ImportError:
    pass

# --- ANTI-HALLUCINATION & TRUTH ---
try:
    from .citation_marshall import CitationMarshall
    from .reality_anchor import RealityAnchor
    from .truth_anchor import TruthAnchor
except ImportError:
    pass

# --- SUBSYSTEMS & INFRASTRUCTURE ---
from .nexus_bridge import NexusBridge
from .visual_nexus import VisualNexus
from .singularity import SingularityEngine
from .proactive import ProactiveEngine
from .file_guard import FileGuard
from .workflows import WorkflowEngine
from .project_map import ProjectMap

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

__version__ = "6.11.0"
__author__ = "Danny"

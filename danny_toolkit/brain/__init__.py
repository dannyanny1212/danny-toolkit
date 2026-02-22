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
from .brain_cli import BrainCLI
from .project_map import ProjectMap

__all__ = [
    # Core Intelligence
    "CentralBrain", "PrometheusBrain", "OmegaGovernor",
    "CorticalStack", "get_cortical_stack", "UnifiedMemory",
    # v6.0 Inventions
    "Strategist", "Tribunal", "AdversarialTribunal",
    "VoidWalker", "Artificer", "BlackBox",
    "TheMirror", "GhostWriter", "Dreamer", "DevOpsDaemon",
    "TheCortex", "TheOracleEye", "TheSynapse", "ThePhantom",
    # Anti-Hallucination
    "CitationMarshall", "RealityAnchor", "TruthAnchor",
    # Subsystems
    "NexusBridge", "VisualNexus", "SingularityEngine",
    "ProactiveEngine", "FileGuard", "WorkflowEngine",
    # Utils
    "ProjectMap", "BrainCLI",
]

__version__ = "6.0.0"
__author__ = "Danny"

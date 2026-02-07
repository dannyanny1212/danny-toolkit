"""
Danny's AI Ecosysteem - Central Brain Module.

Dit is het hart van het geïntegreerde AI-ecosysteem dat alle 31+ apps
orchestreert via Function Calling en Unified Memory.

Componenten:
- CentralBrain: De hoofd orchestrator met Function Calling
- UnifiedMemory: Gedeelde vector database voor alle apps
- Workflows: Super-workflows (Health Loop, Deep Work Loop, etc.)
- BrainCLI: Command-line interface
- TrinitySymbiosis: Verbinding tussen Mind, Soul en Body
- PrometheusBrain: Federated Swarm Intelligence (17 Nodes)
- NexusBridge: Verbinding tussen NEXUS (Pixel) en Central Brain
"""

from .central_brain import CentralBrain
from .unified_memory import UnifiedMemory
from .workflows import WorkflowEngine, SUPER_WORKFLOWS
from .brain_cli import BrainCLI

# NEXUS Brain Integration
from .nexus_bridge import (
    NexusBridge,
    NexusOracleMode,
    create_nexus_bridge,
    get_nexus_greeting,
)

# Digital Sanctuary Dashboard
from .sanctuary_dashboard import (
    SanctuaryDashboard,
    get_sanctuary,
    show_hibernation,
    show_awakening,
    show_live,
    show_biology,
    goodnight,
    goodmorning,
)

# Dream Monitor - Passive Observation Mode
from .dream_monitor import (
    dream_monitor,
    quick_peek,
)

# Morning Protocol - 3-Laags Verificatie
from .morning_protocol import (
    run_morning_protocol,
    quick_check,
)

# Prometheus Protocol - Federated Swarm Intelligence
from .trinity_omega import (
    PrometheusBrain,
    CosmicRole,
    NodeTier,
    TaskPriority,
    AgentNode,
    SwarmMetrics,
    TaskResult,
    get_prometheus,
    route,
)

# Legacy Trinity Symbiosis (backwards compatibility)
from .trinity_symbiosis import (
    TrinitySymbiosis,
    TrinityRole,
    TrinityChannel,
    COSMIC_FAMILY_CONFIG,
    get_trinity,
    connect_iolaax,
    connect_pixel,
    connect_daemon,
    connect_echo,
    connect_unity,
    connect_ember,
    connect_brave,
    connect_joy,
    connect_cosmic_family,
    emit_trinity_event,
)

__all__ = [
    # Central Brain
    "CentralBrain",
    "UnifiedMemory",
    "WorkflowEngine",
    "SUPER_WORKFLOWS",
    "BrainCLI",
    # NEXUS Brain Integration
    "NexusBridge",
    "NexusOracleMode",
    "create_nexus_bridge",
    "get_nexus_greeting",
    # Digital Sanctuary Dashboard
    "SanctuaryDashboard",
    "get_sanctuary",
    "show_hibernation",
    "show_awakening",
    "show_live",
    "show_biology",
    "goodnight",
    "goodmorning",
    # Dream Monitor
    "dream_monitor",
    "quick_peek",
    # Morning Protocol
    "run_morning_protocol",
    "quick_check",
    # Legacy Trinity Symbiosis
    "TrinitySymbiosis",
    "TrinityRole",
    "TrinityChannel",
    "COSMIC_FAMILY_CONFIG",
    "get_trinity",
    "connect_iolaax",
    "connect_pixel",
    "connect_daemon",
    "connect_echo",
    "connect_unity",
    "connect_ember",
    "connect_brave",
    "connect_joy",
    "connect_cosmic_family",
    "emit_trinity_event",
    # Prometheus Protocol - Federated Swarm Intelligence
    "PrometheusBrain",
    "CosmicRole",
    "NodeTier",
    "TaskPriority",
    "AgentNode",
    "SwarmMetrics",
    "TaskResult",
    "get_prometheus",
    "route",
]

__version__ = "1.0.0"
__author__ = "Danny"

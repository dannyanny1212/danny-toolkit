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
"""

from .central_brain import CentralBrain
from .unified_memory import UnifiedMemory
from .workflows import WorkflowEngine, SUPER_WORKFLOWS
from .brain_cli import BrainCLI
from .trinity_symbiosis import (
    TrinitySymbiosis,
    TrinityRole,
    TrinityChannel,
    get_trinity,
    connect_iolaax,
    connect_pixel,
    connect_daemon,
    emit_trinity_event,
)

__all__ = [
    "CentralBrain",
    "UnifiedMemory",
    "WorkflowEngine",
    "SUPER_WORKFLOWS",
    "BrainCLI",
    "TrinitySymbiosis",
    "TrinityRole",
    "TrinityChannel",
    "get_trinity",
    "connect_iolaax",
    "connect_pixel",
    "connect_daemon",
    "emit_trinity_event",
]

__version__ = "1.0.0"
__author__ = "Danny"

"""
Danny's AI Ecosysteem - Central Brain Module.

Dit is het hart van het geïntegreerde AI-ecosysteem dat alle 31+ apps
orchestreert via Function Calling en Unified Memory.

Componenten:
- CentralBrain: De hoofd orchestrator met Function Calling
- UnifiedMemory: Gedeelde vector database voor alle apps
- Workflows: Super-workflows (Health Loop, Deep Work Loop, etc.)
- BrainCLI: Command-line interface
"""

from .central_brain import CentralBrain
from .unified_memory import UnifiedMemory
from .workflows import WorkflowEngine, SUPER_WORKFLOWS
from .brain_cli import BrainCLI

__all__ = [
    "CentralBrain",
    "UnifiedMemory",
    "WorkflowEngine",
    "SUPER_WORKFLOWS",
    "BrainCLI",
]

__version__ = "1.0.0"
__author__ = "Danny"

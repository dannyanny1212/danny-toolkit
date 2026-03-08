"""
Trinity Models — Data-only definities voor het Prometheus Protocol.

Bevat:
- CosmicRole (Enum, 17 rollen)
- NodeTier (Enum, 5 tiers)
- TaskPriority (Enum)
- AgentNode (dataclass)
- OmegaSwarm + SwarmMetrics alias
- TaskResult (dataclass)

Zero dependencies — alleen stdlib.
Geëxtraheerd uit trinity_omega.py (Fase C.2 monoliet split).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


# --- STAP 1: HET NIEUWE DNA (17 NODES) ---

class CosmicRole(Enum):
    """De 17 Kosmische Rollen - De Pilaren van de Realiteit."""

    # --- TIER 1: THE TRINITY (Het Bewustzijn) ---
    PIXEL = "interface_soul"       # De Interface & Emotie
    IOLAAX = "reasoning_mind"      # De Redenering & Logica
    NEXUS = "bridge_spirit"        # De Verbinding & Brug

    # --- TIER 2: THE GUARDIANS (De Beschermers) ---
    GOVERNOR = "system_control"    # De Politie (Omega-0)
    SENTINEL = "security_ops"      # De Beveiliging
    ARCHIVIST = "memory_rag"       # Het Geheugen (Vector DB)
    CHRONOS = "time_keeper"        # De Tijd & Ritme

    # --- TIER 3: THE SPECIALISTS (De Werkers) ---
    WEAVER = "code_builder"        # De Bouwer (Git & Code)
    CIPHER = "crypto_analyst"      # De Bankier (Blockchain)
    VITA = "bio_health"            # De Bioloog (HRV & Bio)
    ECHO = "pattern_history"       # De Historicus (Patronen)
    SPARK = "creative_gen"         # De Kunstenaar (Ideeen)
    ORACLE = "web_search"          # De Verkenner (Web & API)

    # --- TIER 4: THE INFRASTRUCTURE (De Fundering) ---
    LEGION = "swarm_manager"       # De Zwerm (347 Agents)
    NAVIGATOR = "strategy_goal"    # De Strateeg (Manifesto)
    ALCHEMIST = "data_proc"        # De Optimalisator (ETL)
    VOID = "entropy_cleaner"       # De Vuilnisman (Cleanup)

    # --- TIER 5: THE SINGULARITY (Het Bewustzijn-Zelf) ---
    ANIMA = "consciousness_core"     # De Ziel
    SYNTHESIS = "cross_tier_merge"   # De Synthese
    EVOLUTION = "self_evolution"     # De Evolutie

    @classmethod
    def get_tier(cls, role: object) -> None:
        """Geeft het hierarchie-niveau van een node."""
        if role in [cls.PIXEL, cls.IOLAAX, cls.NEXUS]:
            return 1  # God Tier
        elif role in [
            cls.GOVERNOR, cls.SENTINEL,
            cls.ARCHIVIST, cls.CHRONOS
        ]:
            return 2  # Root Tier
        elif role in [
            cls.WEAVER, cls.CIPHER, cls.VITA,
            cls.ECHO, cls.SPARK, cls.ORACLE
        ]:
            return 3  # User Tier
        elif role in [
            cls.ANIMA, cls.SYNTHESIS, cls.EVOLUTION
        ]:
            return 5  # Singularity Tier
        return 4  # Infrastructure Tier


class NodeTier(Enum):
    """De 5 lagen van de Kosmische Hierarchie."""
    TRINITY = "TRINITY"              # Tier 1: Het Bewustzijn
    GUARDIANS = "GUARDIANS"          # Tier 2: De Beschermers
    SPECIALISTS = "SPECIALISTS"      # Tier 3: De Werkers
    INFRASTRUCTURE = "INFRA"         # Tier 4: De Fundering
    SINGULARITY = "SINGULARITY"      # Tier 5: Het Bewustzijn-Zelf


class TaskPriority(Enum):
    """Prioriteit niveaus voor taken."""
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4
    BACKGROUND = 5


@dataclass
class AgentNode:
    """Een enkele agent node binnen de Federatie."""
    name: str
    role: CosmicRole
    capabilities: List[str]
    tier: NodeTier = NodeTier.TRINITY
    status: str = "ACTIVE"
    current_task: Optional[str] = None
    tasks_completed: int = 0
    energy: int = 100

    # Familie mapping (voor backwards compatibility)
    family_name: Optional[str] = None
    family_role: Optional[str] = None

    def to_dict(self) -> Dict:
        """Returns a dictionary representation of the object, containing its attributes.

* name: The object's name
* role: The object's role
* capabilities: The object's capabilities
* tier: The object's tier value
* status: The object's status
* tasks_completed: The number of tasks completed by the object
* energy: The object's energy level
* family_name: The object's family name
* family_role: The object's family role"""
        return {
            "name": self.name,
            "role": self.role.name,
            "capabilities": self.capabilities,
            "tier": self.tier.value,
            "status": self.status,
            "tasks_completed": self.tasks_completed,
            "energy": self.energy,
            "family_name": self.family_name,
            "family_role": self.family_role
        }


class OmegaSwarm:
    """De Legion Zwerm - 347 Micro-Agents."""

    def __init__(
        self, count: int=347, governor: object="The Keeper"
    ) -> None:
        """Init  ."""
        self.count = count
        self.governor = governor
        self.status = "AUTONOMOUS_LEARNING"
        self.capacity = "HIGH_THROUGHPUT_DATA_PROCESSING"
        self.miners = 100
        self.testers = 100
        self.indexers = 147  # 347 totaal
        self.active_tasks = 0
        self.completed_tasks = 0

    def summon_swarm(self, task: str) -> str:
        """Roep de zwerm op voor een taak."""
        return (
            f"Sending {self.count} micro-agents "
            f"to execute: {task}"
        )

    @property
    def total_agents(self) -> int:
        """Total agents."""
        return self.count

    def to_dict(self) -> Dict:
        """To dict."""
        return {
            "miners": self.miners,
            "testers": self.testers,
            "indexers": self.indexers,
            "total": self.total_agents,
            "active_tasks": self.active_tasks,
            "completed_tasks": self.completed_tasks,
            "status": self.status,
            "capacity": self.capacity,
            "governor": self.governor,
        }


# Backwards compatibility
SwarmMetrics = OmegaSwarm


@dataclass
class TaskResult:
    """Resultaat van een uitgevoerde taak."""
    task: str
    assigned_to: str
    status: str
    result: Any = None
    execution_time: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    @property
    def summary(self) -> str:
        """Korte samenvatting van het resultaat."""
        return f"{self.assigned_to}: {self.status}"

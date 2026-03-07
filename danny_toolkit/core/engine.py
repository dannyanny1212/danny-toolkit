"""V6 Bridge — re-exporteert SwarmEngine vanuit root.

Alle danny_toolkit/ modules moeten via deze bridge importeren,
niet direct `from swarm_engine import ...` (Diamond Polish Wet #1).
"""

import sys
from pathlib import Path

# Root toevoegen aan path
_root = Path(__file__).parent.parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from swarm_engine import (  # noqa: E402
    SwarmEngine,
    SwarmPayload,
    AdaptiveRouter,
    get_pipeline_metrics,
    get_circuit_state,
    run_swarm_sync,
)

__all__ = [
    "SwarmEngine",
    "SwarmPayload",
    "AdaptiveRouter",
    "get_pipeline_metrics",
    "get_circuit_state",
    "run_swarm_sync",
]

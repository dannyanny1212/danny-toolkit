"""
Quest 3: Neurale Resonantie — Resonance Optimizer Validator
============================================================
Leest synapse_weights.json, berekent Efficiency Score (SP / avg_latency)
per agent, en print een ASCII-tabel met de Top 3 Most Efficient Agents.
"""

from __future__ import annotations

import json
import logging
import math
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# ── Paths ────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent.parent
WEIGHTS_FILE = ROOT / "data" / "synapse_weights.json"

# ── Synapse constants (mirror from TheSynapse) ───────────────────
MIN_STRENGTH = 0.05
MAX_STRENGTH = 0.95
BIAS_MIN = 0.5
BIAS_MAX = 1.3


def compute_sp(pathways: dict, agent_name: str) -> int:
    """Compute Synaptic Power for an agent from pathway data."""
    strengths = []
    total_fires = 0
    for _cat, agents in pathways.items():
        if agent_name in agents:
            info = agents[agent_name]
            strengths.append(info.get("strength", 0.5))
            total_fires += info.get("fires", 0)

    if not strengths:
        return 50

    avg_strength = sum(strengths) / len(strengths)
    normalized = (avg_strength - MIN_STRENGTH) / (MAX_STRENGTH - MIN_STRENGTH)
    raw_bias = BIAS_MIN + normalized * (BIAS_MAX - BIAS_MIN)
    confidence = min(1.0, math.log2(total_fires + 1) / 5.0)
    effective_bias = 1.0 + confidence * (raw_bias - 1.0)
    return round(effective_bias * 100)


def main() -> int:
    """Lees synapse weights, bereken efficiency scores, print top 3."""
    if not WEIGHTS_FILE.exists():
        print(f"ERROR: {WEIGHTS_FILE} niet gevonden")
        return 1

    with open(WEIGHTS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    pathways = data.get("pathways", {})
    telemetry = data.get("telemetry", {})

    if not telemetry:
        print("WARN: Geen telemetry data in synapse_weights.json")
        print("      Run eerst het systeem zodat record_telemetry() wordt aangeroepen.")
        return 1

    # Bereken Efficiency Score per agent
    scores = []
    for agent_name, telem in telemetry.items():
        sp = compute_sp(pathways, agent_name)
        avg_lat = max(telem.get("avg_latency", 1.0), 0.001)
        efficiency = sp / avg_lat
        scores.append({
            "agent": agent_name,
            "sp": sp,
            "avg_latency": round(avg_lat, 4),
            "efficiency": round(efficiency, 2),
            "success_count": telem.get("success_count", 0),
        })

    scores.sort(key=lambda x: x["efficiency"], reverse=True)

    # ASCII tabel
    print()
    print("  ╔══════════════════════════════════════════════════════════════╗")
    print("  ║   RESONANCE OPTIMIZER — Top 3 Most Efficient Agents        ║")
    print("  ╠══════════════════════════════════════════════════════════════╣")
    print(f"  ║  {'Rank':<5} {'Agent':<16} {'SP':>4}  {'Latency':>8}  {'Eff.Score':>10}  ║")
    print("  ╠══════════════════════════════════════════════════════════════╣")

    for i, entry in enumerate(scores[:3], 1):
        medal = ["★", "▲", "●"][i - 1]
        print(
            f"  ║  {medal} {i:<3} {entry['agent']:<16} "
            f"{entry['sp']:>4}  "
            f"{entry['avg_latency']:>7.3f}s  "
            f"{entry['efficiency']:>10.2f}  ║"
        )

    print("  ╠══════════════════════════════════════════════════════════════╣")

    # Alle agents
    if len(scores) > 3:
        print(f"  ║  {'':5} {'... overige agents':>40}{'':>15} ║")
        for entry in scores[3:]:
            print(
                f"  ║  {'':5} {entry['agent']:<16} "
                f"{entry['sp']:>4}  "
                f"{entry['avg_latency']:>7.3f}s  "
                f"{entry['efficiency']:>10.2f}  ║"
            )

    print("  ╚══════════════════════════════════════════════════════════════╝")
    print()

    if scores:
        winner = scores[0]
        print(f"  TURBO-BOOST KANDIDAAT: {winner['agent']}")
        print(f"  Efficiency Score: {winner['efficiency']:.2f} (SP={winner['sp']} / lat={winner['avg_latency']:.3f}s)")
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())

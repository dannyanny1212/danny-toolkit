"""Synapse Weight Scanner — S-TIER Diagnostic Tool.

Scans synapse_weights.json, computes swarm-wide averages,
identifies the Alpha Agent, and renders an ASCII table.
"""
from __future__ import annotations

import json
import os
import sys
from typing import Dict, List, Tuple


DATA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data",
    "synapse_weights.json",
)


def load_weights(path: str) -> Dict:
    """Load the synapse weight matrix from JSON."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def compute_agent_stats(data: Dict) -> List[Tuple[str, float, int, int, int, float]]:
    """Compute per-agent averages from the weight matrix.

    Returns list of (name, avg_bias, total_fires, total_succ, total_fail, success_rate).
    """
    pathways = data.get("pathways", {})
    agent_data: Dict[str, Dict] = {}

    for _cat, agents in pathways.items():
        for agent_name, info in agents.items():
            if agent_name not in agent_data:
                agent_data[agent_name] = {
                    "biases": [],
                    "fires": 0,
                    "succ": 0,
                    "fail": 0,
                }
            eb = info.get("effective_bias")
            if eb is not None:
                agent_data[agent_name]["biases"].append(eb)
            agent_data[agent_name]["fires"] += info.get("fires", 0)
            agent_data[agent_name]["succ"] += info.get("successes", 0)
            agent_data[agent_name]["fail"] += info.get("fails", 0)

    results = []
    for name, d in agent_data.items():
        biases = d["biases"]
        avg = sum(biases) / len(biases) if biases else 0.0
        fires = d["fires"]
        succ = d["succ"]
        fail = d["fail"]
        rate = (succ / fires * 100) if fires > 0 else 0.0
        results.append((name, avg, fires, succ, fail, rate))

    results.sort(key=lambda x: x[1], reverse=True)
    return results


def sp_bar(bias: float, width: int = 20) -> str:
    """Render a Unicode bar for the given bias value."""
    normalized = min(max(bias / 1.3, 0.0), 1.0)
    filled = int(normalized * width)
    empty = width - filled
    if bias >= 1.1:
        return "\033[33m" + "█" * filled + "░" * empty + "\033[0m"  # gold
    if bias >= 0.9:
        return "\033[32m" + "█" * filled + "░" * empty + "\033[0m"  # green
    if bias >= 0.7:
        return "\033[33m" + "▓" * filled + "░" * empty + "\033[0m"  # amber
    return "\033[31m" + "▒" * filled + "░" * empty + "\033[0m"  # red


def render_table(stats: List[Tuple], swarm_avg: float, alpha: str) -> None:
    """Print an ASCII table with agent stats."""
    sep = "╠" + "═" * 22 + "╬" + "═" * 8 + "╬" + "═" * 22 + "╬" + "═" * 8 + "╬" + "═" * 8 + "╬" + "═" * 8 + "╬" + "═" * 8 + "╣"
    top = "╔" + "═" * 22 + "╦" + "═" * 8 + "╦" + "═" * 22 + "╦" + "═" * 8 + "╦" + "═" * 8 + "╦" + "═" * 8 + "╦" + "═" * 8 + "╗"
    bot = "╚" + "═" * 22 + "╩" + "═" * 8 + "╩" + "═" * 22 + "╩" + "═" * 8 + "╩" + "═" * 8 + "╩" + "═" * 8 + "╩" + "═" * 8 + "╝"

    print()
    print("  \033[36m⚡ SOVEREIGN SYNAPSE — WEIGHT MATRIX SCAN\033[0m")
    print()
    print(top)
    print(f"║ {'Agent':<20} ║ {'SP':>6} ║ {'Power Bar':<20} ║ {'Fires':>6} ║ {'Succ':>6} ║ {'Fail':>6} ║ {'Rate':>6} ║")
    print(sep)

    for name, avg, fires, succ, fail, rate in stats:
        sp = round(avg * 100)
        bar = sp_bar(avg)
        is_alpha = " 👑" if name == alpha else ""
        label = f"{name}{is_alpha}"
        print(f"║ {label:<20} ║ {sp:>6} ║ {bar} ║ {fires:>6} ║ {succ:>6} ║ {fail:>6} ║ {rate:>5.1f}% ║")

    print(bot)

    total_fires = sum(s[3] for s in stats)
    total_succ = sum(s[4] for s in stats)
    print()
    print(f"  \033[36mSwarm Average SP:\033[0m  {round(swarm_avg * 100)}")
    print(f"  \033[33mAlpha Agent:\033[0m       {alpha} 👑")
    print(f"  \033[32mTotal Fires:\033[0m       {sum(s[2] for s in stats)}")
    print(f"  \033[32mGlobal Success:\033[0m    {total_succ}/{total_fires + total_succ} ({total_succ / max(total_fires + total_succ, 1) * 100:.1f}%)")
    print(f"  \033[36mAgents Tracked:\033[0m    {len(stats)}")
    print(f"  \033[36mCategories:\033[0m        {_cat_count}")
    print()


if __name__ == "__main__":
    if not os.path.exists(DATA_PATH):
        print(f"\033[31m❌ File not found: {DATA_PATH}\033[0m")
        sys.exit(1)

    data = load_weights(DATA_PATH)
    _cat_count = len(data.get("pathways", {}))
    stats = compute_agent_stats(data)

    if not stats:
        print("\033[31m❌ No agent data found in weight matrix.\033[0m")
        sys.exit(1)

    swarm_avg = sum(s[1] for s in stats) / len(stats)
    alpha = stats[0][0]

    render_table(stats, swarm_avg, alpha)

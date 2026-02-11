"""
Neural Hub Live Test — Adaptive Routing in actie
=================================================

Toont per query:
  - Welke agent(s) geselecteerd worden
  - De confidence score (cosine similarity)
  - Of embedding of keyword fallback gebruikt werd
  - Pipeline timing via PipelineTuner

Gebruik: python test_neural_hub.py
"""

import asyncio
import math
import os
import sys
import time

if os.name == "nt":
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.dirname(__file__))

from swarm_engine import (
    SwarmEngine,
    AdaptiveRouter,
    PipelineTuner,
    run_swarm_sync,
)


def show_routing_detail(query, router):
    """Toon routing scores voor een query."""
    embed = router._get_embed_fn()
    profielen = router._bereken_profielen()

    if not embed or not profielen:
        print(f"  {query:<45} | EMBEDDING NIET BESCHIKBAAR")
        return

    input_vec = embed(query)

    scores = []
    for agent, sub_vecs in profielen.items():
        best = max(
            router._cosine_sim(input_vec, sv)
            for sv in sub_vecs
        )
        scores.append((agent, best))

    scores.sort(key=lambda x: x[1], reverse=True)

    above = [
        s for s in scores
        if s[1] >= router.DREMPEL
    ]
    targets = [s[0] for s in above[:router.MAX_AGENTS]]

    # Bij overlap: hoogste score wint
    if "MEMEX" in targets and "IOLAAX" in targets:
        score_map = dict(scores)
        if score_map["MEMEX"] > score_map["IOLAAX"]:
            targets.remove("IOLAAX")
        else:
            targets.remove("MEMEX")

    if not targets:
        targets = ["ECHO"]

    # Top 3 scores tonen
    top3 = ", ".join(
        f"{a}={s:.2f}" for a, s in scores[:3]
    )
    target_str = " + ".join(targets)

    print(
        f"  {query:<45} | {target_str:<20}"
        f" | {top3}"
    )


def show_pipeline_timing():
    """Toon pipeline timing voor een echte run."""
    print("\n" + "=" * 80)
    print("  PIPELINE TIMING (echte run, brain=None)")
    print("=" * 80 + "\n")

    logs = []
    payloads = run_swarm_sync(
        "bitcoin blockchain analyse",
        brain=None,
        callback=lambda m: logs.append(m),
    )

    for log_line in logs:
        print(f"  {log_line}")

    print(f"\n  Payloads: {len(payloads)}")
    for p in payloads:
        print(
            f"    - {p.agent}: {p.type}"
            f" ({len(str(p.content))} chars)"
        )


def show_tuner_demo():
    """Demonstreer self-tuning skip-regels."""
    print("\n" + "=" * 80)
    print("  SELF-TUNING DEMO")
    print("=" * 80 + "\n")

    t = PipelineTuner()

    print("  Simulatie: 12 MEMEX calls met 0 fragmenten")
    for i in range(12):
        t.registreer("memex", 15.0, fragmenten=0)
        skip = t.mag_skippen("memex")
        if i >= 8:
            print(
                f"    Call {i+1:>2}: "
                f"{'SKIP' if skip else 'RUN ':>4}"
            )

    print()
    print("  Simulatie: 22 SENTINEL calls, alle schoon")
    t2 = PipelineTuner()
    for i in range(22):
        t2.registreer(
            "sentinel", 25.0, waarschuwingen=0,
        )
        skip = t2.mag_skippen("sentinel")
        if i >= 18:
            print(
                f"    Call {i+1:>2}: "
                f"{'SKIP' if skip else 'RUN ':>4}"
                f"  (count % 5 = {(i+1) % 5})"
            )

    print()
    print(
        f"  Governor mag skippen: "
        f"{t.mag_skippen('governor')}"
    )
    print(
        f"  Route mag skippen:    "
        f"{t.mag_skippen('route')}"
    )


def main():
    print()
    print("=" * 80)
    print("  NEURAL HUB LIVE TEST — Adaptive Routing")
    print("=" * 80)
    print()

    router = AdaptiveRouter()

    scenarios = [
        # Duidelijke single-intent
        "Hoeveel is mijn bitcoin waard?",
        "Mijn code crasht op line 40, help.",
        "Ik voel me moe en slaap slecht.",
        "Wat is de zin van het bestaan?",
        "Verwijder alle tijdelijke bestanden.",
        "Beveilig mijn systeem tegen hackers.",
        "Brainstorm creatieve namen voor mijn app.",
        "Plan mijn agenda voor morgen.",
        # Edge cases
        "debug mijn code",
        "fix de bug in mijn script",
        "schrijf een python functie",
        # Multi-intent
        "Bitcoin prijs en web search nieuws",
        "Debug code en beveilig de firewall",
        # Fallback
        "blorp florp qux",
        "hallo",
    ]

    print(
        f"  {'QUERY':<45} | {'TARGET':<20}"
        f" | TOP 3 SCORES"
    )
    print("  " + "-" * 76)

    for query in scenarios:
        show_routing_detail(query, router)

    # Pipeline timing
    show_pipeline_timing()

    # Self-tuning demo
    show_tuner_demo()

    print()
    print("=" * 80)
    print("  NEURAL HUB TEST VOLTOOID")
    print("=" * 80)


if __name__ == "__main__":
    main()

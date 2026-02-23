#!/usr/bin/env python3
"""
MAIDEN FLIGHT — Generaal Mode v6.8.0 Live Test
================================================
Eén gecontroleerde missie: Analyseer de BlackBox statistieken.

Observeert:
  1. ModelRegistry auto-discover → welke huurlingen beschikbaar?
  2. Arbitrator decompose → sub-taken
  3. Model auction → wie wint de veiling?
  4. Worker.generate() → live API call
  5. HallucinatieSchild 95% Barrière → goedgekeurd of ontslagen?
  6. Performance stats → latency, tokens, success_rate
"""

import asyncio
import os
import sys
import time

# Windows UTF-8
if os.name == "nt":
    sys.stdout.reconfigure(encoding="utf-8")

# Zorg dat project root op sys.path staat
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from danny_toolkit.core.config import Config
from danny_toolkit.core.utils import Kleur


def separator(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


async def maiden_flight():
    """De eerste live inzet van de Generaal."""

    separator("MAIDEN FLIGHT — Generaal Mode v6.8.0")
    t_start = time.time()

    # ── Stap 1: ModelRegistry auto-discover ──
    separator("STAP 1: Auto-Discover — Welke huurlingen zijn beschikbaar?")

    from danny_toolkit.brain.model_sync import get_model_registry
    registry = get_model_registry()
    registry.auto_discover()

    stats = registry.get_stats()
    print(f"\n  {Kleur.GROEN}Totaal workers:{Kleur.RESET} {stats['total_workers']}")
    print(f"  {Kleur.GROEN}Beschikbaar:{Kleur.RESET}    {stats['available_workers']}")

    for w in stats["workers"]:
        status = f"{Kleur.GROEN}ONLINE{Kleur.RESET}" if not w["circuit_open"] else f"{Kleur.ROOD}CIRCUIT OPEN{Kleur.RESET}"
        print(f"    [{status}] {w['provider']}/{w['model_id']}")

    if stats["available_workers"] == 0:
        print(f"\n  {Kleur.ROOD}ABORT:{Kleur.RESET} Geen beschikbare modellen. Check API keys.")
        return

    # ── Stap 2: Decompose het doel ──
    separator("STAP 2: Goal Decomposition")

    from danny_toolkit.brain.arbitrator import get_arbitrator
    arbitrator = get_arbitrator()

    goal = "Analyseer de BlackBox statistieken en geef een korte samenvatting van de gezondheid van het systeem"
    print(f"\n  {Kleur.BLAUW}Goal:{Kleur.RESET} {goal}")

    manifest = await arbitrator.decompose(goal)
    print(f"\n  {Kleur.GEEL}Trace ID:{Kleur.RESET}  {manifest.trace_id}")
    print(f"  {Kleur.GEEL}Status:{Kleur.RESET}    {manifest.status}")
    print(f"  {Kleur.GEEL}Sub-taken:{Kleur.RESET} {len(manifest.taken)}")
    for t in manifest.taken:
        print(f"    - [{t.categorie}] {t.beschrijving[:70]}")

    # ── Stap 3+4: Model Auction + Execute ──
    separator("STAP 3+4: Model Auction + Execute (Generaal Mode)")

    manifest = await arbitrator.execute_with_models(manifest, retry_limit=2)

    # ── Stap 5: Resultaten ──
    separator("STAP 5: Resultaten + 95% Barriere Status")

    for task in manifest.taken:
        print(f"\n  {Kleur.BLAUW}Task:{Kleur.RESET} {task.task_id}")
        print(f"  {Kleur.BLAUW}Status:{Kleur.RESET} {task.status}")

        if task.resultaat:
            r = task.resultaat
            barrier_tag = (
                f"{Kleur.GROEN}APPROVED{Kleur.RESET}"
                if r.passed_barrier
                else f"{Kleur.ROOD}REJECTED{Kleur.RESET}"
            )
            print(f"  {Kleur.GEEL}Model:{Kleur.RESET}   {r.provider}/{r.model_id}")
            print(f"  {Kleur.GEEL}Tokens:{Kleur.RESET}  {r.tokens_used}")
            print(f"  {Kleur.GEEL}Latency:{Kleur.RESET} {r.latency_ms:.0f}ms")
            print(f"  {Kleur.GEEL}Barrier:{Kleur.RESET} {barrier_tag} (score: {r.barrier_score:.3f})")
            print(f"  {Kleur.GEEL}Content:{Kleur.RESET}")
            # Toon eerste 500 tekens van de output
            content_preview = r.content[:500]
            for line in content_preview.split("\n"):
                print(f"    {line}")
            if len(r.content) > 500:
                print(f"    ... ({len(r.content)} tekens totaal)")
        else:
            print(f"  {Kleur.ROOD}Geen resultaat (taak gefaald){Kleur.RESET}")

    # ── Stap 6: Performance Stats ──
    separator("STAP 6: Generaal Performance Stats")

    arb_stats = arbitrator.get_stats()
    print(f"\n  {Kleur.GROEN}Arbitrator Stats:{Kleur.RESET}")
    for k, v in arb_stats.items():
        print(f"    {k}: {v}")

    print(f"\n  {Kleur.GROEN}Worker Performance:{Kleur.RESET}")
    for w in registry.get_all_workers():
        perf = w.get_perf()
        if perf["calls"] > 0:
            print(f"    {perf['provider']}/{perf['model_id']}:")
            print(f"      Calls: {perf['calls']}, Successes: {perf['successes']}, "
                  f"Failures: {perf['failures']}, Barrier Rejections: {perf['barrier_rejections']}")
            print(f"      Success Rate: {perf['success_rate']:.1%}, "
                  f"Avg Latency: {perf['avg_latency_ms']:.0f}ms, "
                  f"Total Tokens: {perf['total_tokens']}")

    # ── Betrouwbaarheid ──
    from danny_toolkit.brain.model_sync import betrouwbaarheid
    # Gebruik de werkelijke success_rate als P_ext
    available = registry.get_available()
    if available:
        best = max(available, key=lambda w: w.success_rate())
        p_ext = best.success_rate()
        p_shield = 0.95  # HallucinatieSchild detectiekans
        r_final = betrouwbaarheid(p_ext, p_shield)
        print(f"\n  {Kleur.GROEN}Betrouwbaarheidsformule:{Kleur.RESET}")
        print(f"    P_ext (beste model):  {p_ext:.2f}")
        print(f"    P_shield (Schild):    {p_shield:.2f}")
        print(f"    R_final:              {r_final:.4f} ({r_final*100:.1f}%)")

    elapsed = time.time() - t_start
    separator(f"MAIDEN FLIGHT COMPLEET — {elapsed:.1f}s")
    print(f"\n  Manifest status: {manifest.status}")
    print(f"  Totale tijd: {elapsed:.1f}s")


if __name__ == "__main__":
    asyncio.run(maiden_flight())

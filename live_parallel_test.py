#!/usr/bin/env python3
"""
PARALLEL INTELLIGENCE — Generaal Mode v6.11.0
=============================================
De Generaal verdeelt een complexe missie over meerdere externe AI-modellen.

Scenario: Na 20 eerdere missies heeft de Generaal geleerd:
  - Groq Llama-4 is snel maar onnauwkeurig (50% barrier pass rate)
  - NVIDIA NIM is uitstekend in code (85% pass rate)
  - Anthropic Claude is de meest betrouwbare verificator (88% pass rate)

Op basis van deze ervaring verdeelt de auction de taken:
  - "code"        → NVIDIA NIM wint  (cap=1.0, sr=0.85, cost+lat=3)
  - "verificatie"  → Anthropic wint   (cap=1.0, sr=0.88, cost+lat=5)
  - "research"    → Groq wint        (cap=1.0, sr=0.50, cost+lat=2)

Formule: S = (cap_match × success_rate) / (cost_tier + latency_class)
"""

import asyncio
import os
import sys
import time

# Windows UTF-8
if os.name == "nt":
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from danny_toolkit.core.utils import Kleur


def sep(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


async def parallel_intelligence():
    """De Generaal verdeelt taken over meerdere modellen."""

    sep("PARALLEL INTELLIGENCE — Generaal Mode v6.11.0")
    t_start = time.time()

    # ── Stap 1: Verse registry met pre-seeded performance ──
    sep("STAP 1: Registry + Ervaringsdata (20 eerdere missies)")

    from danny_toolkit.brain.model_sync import (
        ModelRegistry, ModelCapability,
        GroqModelWorker, AnthropicModelWorker, NVIDIAModelWorker,
    )
    import danny_toolkit.brain.model_sync as ms

    registry = ModelRegistry()

    # Groq — snel, maar slechts 50% barrier pass rate
    groq_w = GroqModelWorker()
    groq_w._perf["calls"] = 20
    groq_w._perf["successes"] = 10   # sr = 0.50
    groq_w._perf["failures"] = 2
    groq_w._perf["barrier_rejections"] = 8
    registry.register(groq_w)

    # Anthropic — duur maar betrouwbaar, 88% pass rate
    anth_w = AnthropicModelWorker()
    anth_w._perf["calls"] = 25
    anth_w._perf["successes"] = 22   # sr = 0.88
    anth_w._perf["failures"] = 0
    anth_w._perf["barrier_rejections"] = 3
    registry.register(anth_w)

    # NVIDIA NIM — goede coder, 85% pass rate
    nim_w = NVIDIAModelWorker()
    nim_w._perf["calls"] = 20
    nim_w._perf["successes"] = 17    # sr = 0.85
    nim_w._perf["failures"] = 1
    nim_w._perf["barrier_rejections"] = 2
    registry.register(nim_w)

    # Toon verwachte auction scores per categorie
    print(f"\n  {Kleur.GROEN}Ervaringsdata (gesimuleerd na 20 missies):{Kleur.RESET}")
    for w in registry.get_all_workers():
        sr = w.success_rate()
        cost_lat = w.profile.cost_tier + w.profile.latency_class
        caps = ", ".join(c.value for c in w.profile.capabilities)
        print(f"    {w.profile.provider}/{w.profile.model_id}:")
        print(f"      Success Rate: {sr:.0%}  |  Cost+Latency: {cost_lat}  |  Caps: [{caps}]")

    print(f"\n  {Kleur.GEEL}Verwachte auction routing:{Kleur.RESET}")
    # Bereken verwachte scores
    models = [
        ("Groq", groq_w, ["code", "verificatie", "research"]),
        ("Anthropic", anth_w, ["code", "verificatie", "research"]),
        ("NIM", nim_w, ["code", "verificatie", "research"]),
    ]
    cat_caps = {
        "code": ModelCapability.CODE,
        "verificatie": ModelCapability.VERIFICATIE,
        "research": ModelCapability.RESEARCH,
    }
    for cat in ["code", "verificatie", "research"]:
        scores = []
        for name, w, _ in models:
            cap = cat_caps[cat]
            cm = 1.0 if cap in w.profile.capabilities else 0.5
            s = (cm * w.success_rate()) / (w.profile.cost_tier + w.profile.latency_class)
            scores.append((name, s))
        scores.sort(key=lambda x: x[1], reverse=True)
        winner = scores[0]
        runner = scores[1]
        print(f"    {cat:14s} → {Kleur.GROEN}{winner[0]}{Kleur.RESET} (S={winner[1]:.3f})"
              f"  > {runner[0]} ({runner[1]:.3f})")

    # Installeer onze registry als singleton
    old_registry = ms._registry_instance
    ms._registry_instance = registry

    try:
        # ── Stap 2: Handmatig manifest met 3 specialisatietaken ──
        sep("STAP 2: Missie-Manifest (3 parallelle taken)")

        from danny_toolkit.brain.arbitrator import (
            TaskArbitrator, GoalManifest, SwarmTask,
        )
        import uuid

        arb = TaskArbitrator()

        manifest = GoalManifest(
            goal="Multi-model analyse: code + verificatie + research",
            trace_id=uuid.uuid4().hex[:12],
            status="decomposed",
        )
        manifest.taken = [
            SwarmTask(
                task_id="PAR-CODE",
                beschrijving=(
                    "Schrijf een korte Python functie die controleert of een "
                    "gegeven string een palindroom is. Gebruik alleen standaard "
                    "Python, geen externe libraries. Geef de functie en een "
                    "korte uitleg."
                ),
                categorie="code",
                prioriteit=1,
            ),
            SwarmTask(
                task_id="PAR-VERIF",
                beschrijving=(
                    "Verifieer de volgende bewering: 'In Python is een lege "
                    "dictionary falsy, maar een lege NetworkX DiGraph is ook "
                    "falsy.' Geef aan of dit klopt en waarom."
                ),
                categorie="verificatie",
                prioriteit=1,
            ),
            SwarmTask(
                task_id="PAR-RSRCH",
                beschrijving=(
                    "Geef 3 best practices voor async error handling in Python "
                    "asyncio. Kort en bondig, maximaal 5 zinnen per practice."
                ),
                categorie="research",
                prioriteit=1,
            ),
        ]

        for t in manifest.taken:
            print(f"\n  {Kleur.GEEL}[{t.task_id}]{Kleur.RESET} categorie={t.categorie}")
            print(f"    {t.beschrijving[:70]}...")

        # ── Stap 3: Generaal Mode — Parallelle Executie ──
        sep("STAP 3: GENERAAL DISPATCH (asyncio.gather)")

        t_exec = time.time()
        manifest = await arb.execute_with_models(manifest, retry_limit=2)
        exec_time = time.time() - t_exec

        # ── Stap 4: Resultaten ──
        sep("STAP 4: Resultaten per Taak")

        providers_used = set()
        for task in manifest.taken:
            print(f"\n  {Kleur.BLAUW}━━━ {task.task_id} ({task.categorie}) ━━━{Kleur.RESET}")
            print(f"  Status: {task.status}")

            if task.resultaat:
                r = task.resultaat
                providers_used.add(r.provider)
                barrier_tag = (
                    f"{Kleur.GROEN}APPROVED{Kleur.RESET}"
                    if r.passed_barrier
                    else f"{Kleur.ROOD}REJECTED{Kleur.RESET}"
                )
                print(f"  Model:   {Kleur.GEEL}{r.provider}/{r.model_id}{Kleur.RESET}")
                print(f"  Tokens:  {r.tokens_used}")
                print(f"  Latency: {r.latency_ms:.0f}ms")
                print(f"  Barrier: {barrier_tag} (score: {r.barrier_score:.3f})")
                print(f"  Content preview:")
                preview = r.content[:300].strip()
                for line in preview.split("\n"):
                    print(f"    {line}")
                if len(r.content) > 300:
                    print(f"    ... ({len(r.content)} tekens totaal)")
            else:
                print(f"  {Kleur.ROOD}Geen resultaat{Kleur.RESET}")

        # ── Stap 5: Parallel Intelligence Rapport ──
        sep("STAP 5: Parallel Intelligence Rapport")

        done = sum(1 for t in manifest.taken if t.status == "done")
        failed = sum(1 for t in manifest.taken if t.status == "failed")

        print(f"\n  {Kleur.GROEN}Manifest status:{Kleur.RESET}    {manifest.status}")
        print(f"  {Kleur.GROEN}Taken voltooid:{Kleur.RESET}     {done}/{len(manifest.taken)}")
        print(f"  {Kleur.GROEN}Taken gefaald:{Kleur.RESET}      {failed}/{len(manifest.taken)}")
        print(f"  {Kleur.GROEN}Providers gebruikt:{Kleur.RESET} {len(providers_used)} "
              f"({', '.join(sorted(providers_used))})")
        print(f"  {Kleur.GROEN}Parallelle exec:{Kleur.RESET}    {exec_time:.1f}s")

        # Worker perf na deze run
        print(f"\n  {Kleur.GROEN}Worker Performance (bijgewerkt):{Kleur.RESET}")
        for w in registry.get_all_workers():
            perf = w.get_perf()
            if perf["calls"] > 0:
                print(f"    {perf['provider']}/{perf['model_id']}:")
                print(f"      Calls: {perf['calls']}, SR: {perf['success_rate']:.0%}, "
                      f"Avg Lat: {perf['avg_latency_ms']:.0f}ms, "
                      f"Barrier Rej: {perf['barrier_rejections']}")

        # Betrouwbaarheid per provider
        from danny_toolkit.brain.model_sync import betrouwbaarheid
        print(f"\n  {Kleur.GROEN}Betrouwbaarheid per provider:{Kleur.RESET}")
        for w in registry.get_all_workers():
            p_ext = w.success_rate()
            r_final = betrouwbaarheid(p_ext, 0.95)
            print(f"    {w.profile.provider}: P_ext={p_ext:.2f} → "
                  f"R_final={r_final:.4f} ({r_final*100:.1f}%)")

        # Arbitrator stats
        arb_stats = arb.get_stats()
        print(f"\n  {Kleur.GROEN}Arbitrator Generaal Stats:{Kleur.RESET}")
        print(f"    Model auctions:  {arb_stats['model_auctions_held']}")
        print(f"    Model completed: {arb_stats['model_tasks_completed']}")
        print(f"    Model failed:    {arb_stats['model_tasks_failed']}")
        print(f"    Barrier rejects: {arb_stats['barrier_rejections']}")

        elapsed = time.time() - t_start
        sep(f"PARALLEL INTELLIGENCE COMPLEET — {elapsed:.1f}s")

    finally:
        # Herstel originele registry
        ms._registry_instance = old_registry


if __name__ == "__main__":
    asyncio.run(parallel_intelligence())

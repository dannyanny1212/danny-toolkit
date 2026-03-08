"""Swarm Stress-Test — vult Observatory met realtime metrics.

Stuurt 3 opdrachten door de SwarmEngine om alle agents te activeren
en Observatory data te genereren (tokens, latencies, agent-interacties).

Gebruik:
    python trigger_swarm.py
"""
import sys
import os
import time

# danny-toolkit root op sys.path
_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# Windows UTF-8
if os.name == "nt":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

from swarm_engine import run_swarm_sync

PROMPTS = [
    "Voer een cross-tier audit uit op alle actieve agents en rapporteer hun energieniveaus en taakstatistieken.",
    "Analyseer de geheugen-paden van de CorticalStack en geef een samenvatting van de meest recente episodische herinneringen.",
    "Optimaliseer de NeuralBus routing: welke event types zijn het meest actief en welke subscribers reageren het snelst?",
]


def main():
    print(f"\n{'='*60}")
    print("  OMEGA SWARM STRESS-TEST — Observatory Data Generator")
    print(f"{'='*60}\n")

    for i, prompt in enumerate(PROMPTS, 1):
        print(f"[{i}/{len(PROMPTS)}] {prompt[:70]}...")
        t0 = time.time()
        try:
            payloads = run_swarm_sync(prompt)
            dt = time.time() - t0
            agents = {p.agent for p in payloads} if payloads else set()
            print(f"  -> {len(payloads or [])} payloads | {len(agents)} agents | {dt:.1f}s")
            for p in (payloads or []):
                preview = (p.display_text or p.content or "")[:120]
                print(f"     [{p.agent}] {preview}")
        except Exception as e:
            print(f"  -> ERROR: {e}")
        print()

    print("Stress-test compleet. Observatory metrics zijn nu gevuld.\n")


if __name__ == "__main__":
    main()

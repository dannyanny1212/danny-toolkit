"""
SWARM CORE — Backend Wrapper met Callback Mechanisme
=====================================================

Clean scheiding tussen frontend (sanctuary_ui.py) en
backend (trinity_omega.py). Elke pipeline-stap vuurt
een callback zodat de UI live kan updaten.

Gebruik:
    from swarm_core import (
        run_hub_spoke_pipeline,
        run_chain_pipeline,
    )

    def update_ui(msg):
        print(msg)  # of st.empty() update

    result = run_hub_spoke_pipeline(
        "Bitcoin analyse", brain, callback=update_ui
    )
"""

import io
from contextlib import redirect_stdout

from danny_toolkit.brain.trinity_omega import (
    CosmicRole,
    TaskPriority,
)


class CallbackWriter:
    """Intercepteert print() en vuurt callback per regel."""

    def __init__(self, callback):
        self.callback = callback

    def write(self, text):
        if text.strip() and self.callback:
            self.callback(text.strip())

    def flush(self):
        pass


def run_hub_spoke_pipeline(prompt, brain, callback=None):
    """Hub & Spoke pipeline met live callback.

    Args:
        prompt: User input string.
        brain: PrometheusBrain instantie.
        callback: Functie(str) die per stap aangeroepen
                  wordt. Mag None zijn (silent mode).

    Returns:
        (result, assigned, output) tuple.
        - result: TaskResult of None bij BLOCKED.
        - assigned: String met node-naam/keten.
        - output: Finale tekst voor de gebruiker.
    """
    def log(msg):
        if callback:
            callback(msg)

    assigned = "?"
    output = ""

    # ── STAP 1: Governor Gate ──
    log("\U0001f6e1\ufe0f Governor: Validating security"
        " protocols...")
    safe, reason = brain._governor_gate(prompt)

    if not safe:
        log(f"\u274c Governor: BLOCKED \u2014 {reason}")
        return None, "Governor", f"BLOCKED: {reason}"

    log("\U0001f6e1\ufe0f Governor: Input SAFE \u2713")

    # ── STAP 2: Chronos Context ──
    log("\u23f3 Chronos: Injecting temporal context...")
    enriched = brain._chronos_enrich(prompt)
    try:
        prefix = enriched[:enriched.index("]") + 1]
    except ValueError:
        prefix = enriched[:40]
    log(f"\u23f3 Chronos: {prefix} \u2713")

    # ── STAP 3: Nexus Classificatie ──
    log("\U0001f9e0 Nexus: Classifying semantic intent...")
    buf = io.StringIO()
    with redirect_stdout(buf):
        category = brain._nexus_classify(enriched)
    role = brain.NEXUS_CATEGORIES.get(
        category, CosmicRole.ECHO
    )
    log(f"\U0001f9e0 Nexus: [{category}] \u2192"
        f" {role.name}")

    # ── STAP 4: Specialist Uitvoering ──
    log(f"\u26a1 {role.name}: Processing payload...")
    buf = io.StringIO()
    with redirect_stdout(buf):
        if category == "SYSTEM":
            result = brain._deploy_swarm(
                enriched, TaskPriority.MEDIUM
            )
        else:
            result = brain._assign(
                role, enriched, TaskPriority.MEDIUM
            )
    log(f"\u26a1 {result.assigned_to}: {result.status}"
        f" ({result.execution_time:.1f}s)")

    assigned = result.assigned_to
    output = (
        str(result.result) if result.result
        else result.status
    )

    # ── STAP 5: Weaver Synthese ──
    if (
        category != "CASUAL"
        and result.status == "TASK_COMPLETED"
        and result.result
    ):
        log("\U0001f4dd Weaver: Synthesizing response...")
        buf = io.StringIO()
        with redirect_stdout(buf):
            synthesized = brain._weaver_synthesize(
                str(result.result), prompt
            )
        if synthesized:
            output = synthesized
            assigned = (
                f"{result.assigned_to} \u2192 Weaver"
            )
            log("\U0001f4dd Weaver: Synthesis complete"
                " \u2713")
        else:
            log("\U0001f4dd Weaver: Skipped (raw output)")

    log("\u2705 PIPELINE COMPLETE")
    return result, assigned, output


def run_chain_pipeline(prompt, brain, callback=None):
    """Chain of Command pipeline met live callback.

    Onderschept alle print() statements van
    chain_of_command() en stuurt ze live naar de
    callback.

    Args:
        prompt: User input string.
        brain: PrometheusBrain instantie.
        callback: Functie(str) per regel.

    Returns:
        dict met chain_of_command resultaten.
    """
    def log(msg):
        if callback:
            callback(msg)

    log("\U0001f4e1 Chain of Command gestart...")
    log(f"\U0001f4e1 Query: \"{prompt[:60]}...\"")

    if callback:
        writer = CallbackWriter(callback)
        with redirect_stdout(writer):
            result = brain.chain_of_command(prompt)
    else:
        result = brain.chain_of_command(prompt)

    log("\u2705 CHAIN COMPLETE")
    return result

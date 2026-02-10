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
import re
from contextlib import redirect_stdout

import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from danny_toolkit.brain.trinity_omega import (
    CosmicRole,
    TaskPriority,
)

# Cortical Stack (persistent memory)
try:
    from danny_toolkit.brain.cortical_stack import (
        get_cortical_stack,
    )
    HAS_CORTICAL = True
except ImportError:
    HAS_CORTICAL = False


def _log_to_cortical(
    actor, action, details=None, source="swarm_core"
):
    """Log naar CorticalStack als beschikbaar. Silent fail."""
    if not HAS_CORTICAL:
        return
    try:
        stack = get_cortical_stack()
        stack.log_event(
            actor=actor,
            action=action,
            details=details,
            source=source,
        )
    except Exception:
        pass


def _learn_from_input(prompt):
    """Extraheer feiten uit user input.

    Herkent patronen als 'mijn naam is X',
    'ik hou van X', 'mijn favoriete X is Y'.
    """
    if not HAS_CORTICAL:
        return
    try:
        stack = get_cortical_stack()
        lower = prompt.lower().strip()

        if "mijn naam is " in lower:
            naam = prompt[lower.index("mijn naam is ") + 13:]
            naam = naam.split(".")[0].split(",")[0].strip()
            if naam and len(naam) < 50:
                stack.remember_fact("user_name", naam, 0.9)

        for trigger in ["ik hou van ", "ik houd van "]:
            if trigger in lower:
                val = prompt[
                    lower.index(trigger) + len(trigger):
                ]
                val = val.split(".")[0].split(",")[0].strip()
                if val and len(val) < 100:
                    stack.remember_fact(
                        f"voorkeur_{hash(val) % 10000}",
                        f"Houdt van: {val}",
                        0.7,
                    )
                break
    except Exception:
        pass


class CallbackWriter:
    """Intercepteert print() en vuurt callback per regel."""

    def __init__(self, callback):
        self.callback = callback

    def write(self, text):
        if text.strip() and self.callback:
            self.callback(text.strip())

    def flush(self):
        pass


# ── MEDIA GENERATORS ──

def _crypto_metrics():
    """Genereer crypto market ticker + 30d chart data.

    Combineert st.metric tickers (Bloomberg-stijl) met
    30-dagen prijs en volume grafieken.
    """
    np.random.seed(42)
    dagen = pd.date_range(
        end=datetime.now(), periods=30, freq="D"
    )
    prijs = 42000 + np.cumsum(
        np.random.randn(30) * 800
    )
    volume = np.abs(
        np.random.randn(30) * 500 + 2000
    )

    # 24h delta berekenen uit de laatste 2 dagen
    delta_pct = (
        (prijs[-1] - prijs[-2]) / prijs[-2] * 100
    )

    return {
        "type": "metrics",
        "category": "CRYPTO",
        "metrics": [
            {
                "label": "Bitcoin (BTC)",
                "value": f"${prijs[-1]:,.2f}",
                "delta": f"{delta_pct:+.2f}%",
            },
            {
                "label": "Ethereum (ETH)",
                "value": "$2,850.10",
                "delta": "-1.12%",
            },
            {
                "label": "Dominance",
                "value": "54.2%",
                "delta": "+0.4%",
            },
            {
                "label": "Fear & Greed",
                "value": "78",
                "delta": "Extreme Greed",
                "delta_color": "off",
            },
        ],
        "data": pd.DataFrame(
            {"Prijs (USD)": prijs}, index=dagen
        ),
        "extra": pd.DataFrame(
            {"Volume": volume}, index=dagen
        ),
    }


def _health_chart():
    """Genereer 24-uur HRV + hartslag data."""
    np.random.seed(7)
    uren = pd.date_range(
        end=datetime.now(), periods=24, freq="h"
    )
    hrv = np.abs(np.random.randn(24) * 15 + 55)
    hartslag = np.abs(np.random.randn(24) * 8 + 72)
    return {
        "type": "area_chart",
        "category": "HEALTH",
        "data": pd.DataFrame(
            {"HRV (ms)": hrv, "Hartslag": hartslag},
            index=uren,
        ),
    }


def _data_chart():
    """Genereer 6 systeem-metrics bar chart."""
    np.random.seed(13)
    labels = [
        "CPU", "RAM", "Disk", "Net",
        "GPU", "Cache",
    ]
    waarden = np.random.randint(20, 95, size=6)
    return {
        "type": "bar_chart",
        "category": "DATA",
        "data": pd.DataFrame(
            {"Gebruik (%)": waarden}, index=labels
        ),
    }


def _code_media(output):
    """Extraheer code blocks uit specialist output."""
    pattern = r"```(?:\w+)?\n(.*?)```"
    matches = re.findall(pattern, str(output), re.DOTALL)
    if matches:
        return {
            "type": "code",
            "category": "CODE",
            "code": matches[0].strip(),
        }
    return None


def _generate_media(category, output):
    """Dispatcher: categorie → visuele media.

    Returns:
        dict met media-info, of None als er geen
        visual bij deze categorie hoort.
    """
    if category == "CRYPTO":
        return _crypto_metrics()
    elif category == "HEALTH":
        return _health_chart()
    elif category == "DATA":
        return _data_chart()
    elif category == "CODE":
        return _code_media(output)
    return None


def run_hub_spoke_pipeline(prompt, brain, callback=None):
    """Hub & Spoke pipeline met live callback.

    Args:
        prompt: User input string.
        brain: PrometheusBrain instantie.
        callback: Functie(str) die per stap aangeroepen
                  wordt. Mag None zijn (silent mode).

    Returns:
        (result, assigned, output, media) tuple.
        - result: TaskResult of None bij BLOCKED.
        - assigned: String met node-naam/keten.
        - output: Finale tekst voor de gebruiker.
        - media: dict met visuele data (chart/code),
                 of None als er geen visual hoort.
    """
    def log(msg):
        if callback:
            callback(msg)

    # Cortical Stack logging
    _log_to_cortical(
        "user", "query", {"prompt": prompt[:500]}
    )
    _learn_from_input(prompt)

    assigned = "?"
    output = ""

    # ── STAP 1: Governor Gate ──
    log("\U0001f6e1\ufe0f Governor: Validating security"
        " protocols...")
    safe, reason = brain._governor_gate(prompt)

    if not safe:
        log(f"\u274c Governor: BLOCKED \u2014 {reason}")
        return None, "Governor", f"BLOCKED: {reason}", None

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

    # ── STAP 6: Media Generatie ──
    media = _generate_media(category, output)
    if media:
        log(f"\U0001f4ca Media: {media['type']}"
            f" ({media['category']})")

    log("\u2705 PIPELINE COMPLETE")

    # Log response naar Cortical Stack
    _log_to_cortical(
        "swarm", "response",
        {
            "assigned": assigned,
            "output_preview": str(output)[:300],
        },
    )

    return result, assigned, output, media


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

    # Cortical Stack logging
    _log_to_cortical(
        "user", "chain_query", {"prompt": prompt[:500]}
    )
    _learn_from_input(prompt)

    log("\U0001f4e1 Chain of Command gestart...")
    log(f"\U0001f4e1 Query: \"{prompt[:60]}...\"")

    if callback:
        writer = CallbackWriter(callback)
        with redirect_stdout(writer):
            result = brain.chain_of_command(prompt)
    else:
        result = brain.chain_of_command(prompt)

    log("\u2705 CHAIN COMPLETE")

    # Log response naar Cortical Stack
    _log_to_cortical("swarm", "chain_response", {})

    return result

"""
HEARTBEAT DAEMON v2.0 — Autonome SwarmEngine Pulse.

Draait als apart proces en roept periodiek de
SwarmEngine aan voor geplande taken. Bewijs dat
de hele pipeline (incl. Memex RAG) ook zonder
UI werkt.

Gebruik:
    python daemon_heartbeat.py
    Ctrl+C om te stoppen.
"""

import asyncio
import io
import logging
import os
import sys
import time
from datetime import datetime
from contextlib import redirect_stdout

logger = logging.getLogger(__name__)

# Windows UTF-8 fix
if os.name == "nt":
    sys.stdout.reconfigure(encoding="utf-8")

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from swarm_engine import SwarmEngine

console = Console()


# ── BRAIN LADEN ──

def _laad_brain():
    """Laad PrometheusBrain (output onderdrukt)."""
    console.print(
        "[dim]Federation wordt gewekt...[/dim]"
    )
    buf = io.StringIO()
    with redirect_stdout(buf):
        from danny_toolkit.brain.trinity_omega import (
            PrometheusBrain,
        )
        brain = PrometheusBrain()
    return brain


# ── HEARTBEAT DAEMON ──

class HeartbeatDaemon:
    """Autonome daemon die SwarmEngine periodiek aanroept.

    Kenmerken:
    - Async loop met asyncio
    - Geplande taken met interval
    - Rich terminal output
    - Gebruikt dezelfde SwarmEngine als UI/CLI
    """

    def __init__(self, brain=None):
        self.brain = brain
        self.engine = SwarmEngine(brain=brain)
        self.is_awake = True
        self.last_check = {}
        self.pulse_count = 0

        # Geplande taken
        self.schedule = [
            {
                "name": "RAG Health Check",
                "interval": 120,
                "prompt": (
                    "Zoek in de documenten:"
                    " wat zijn de python"
                    " best practices?"
                ),
            },
            {
                "name": "System Heartbeat",
                "interval": 60,
                "prompt": "hallo",
            },
        ]

    async def run_task(self, task_config):
        """Voer een geplande taak uit via SwarmEngine."""
        name = task_config["name"]
        prompt = task_config["prompt"]

        console.print(
            f"\n[yellow]⚡ DAEMON TRIGGER:"
            f"[/yellow] {name}"
        )
        console.print(
            f"[dim]  Prompt: {prompt}[/dim]"
        )

        try:
            payloads = await self.engine.run(prompt)

            for p in payloads:
                if p.type == "research_report":
                    data = p.content
                    src_list = []
                    if isinstance(data, dict):
                        src_list = data.get(
                            "sources_list", []
                        )
                    bronnen = (
                        ", ".join(src_list)
                        if src_list
                        else "geen"
                    )
                    console.print(Panel(
                        f"{p.display_text}\n\n"
                        f"[dim]Bronnen:"
                        f" {bronnen}[/dim]",
                        title=(
                            f"✅ {name}"
                            " (RAG Verified)"
                        ),
                        border_style="green",
                    ))
                elif p.type == "text":
                    console.print(Panel(
                        str(p.display_text),
                        title=f"✅ {name}",
                        border_style="blue",
                    ))
                else:
                    console.print(Panel(
                        str(p.display_text),
                        title=(
                            f"✅ {name}"
                            f" ({p.type})"
                        ),
                        border_style="cyan",
                    ))

        except Exception as e:
            console.print(
                f"[red]  ❌ {name}:"
                f" {e}[/red]"
            )

    async def pulse(self):
        """Hoofdloop: periodiek taken uitvoeren."""
        console.print(Panel(
            "[bold cyan]PROJECT OMEGA:"
            " HEARTBEAT ONLINE[/bold cyan]\n"
            f"[dim]{len(self.schedule)}"
            f" taken gepland |"
            f" Brain: {'ACTIVE' if self.brain else 'OFFLINE'}"
            f"[/dim]",
            border_style="cyan",
        ))

        # Toon schedule
        table = Table(
            title="Geplande Taken",
            border_style="dim",
        )
        table.add_column("Taak", style="cyan")
        table.add_column(
            "Interval", style="yellow"
        )
        table.add_column("Prompt", style="dim")

        for t in self.schedule:
            table.add_row(
                t["name"],
                f"{t['interval']}s",
                t["prompt"][:50] + "...",
            )
        console.print(table)
        console.print(
            "[dim]Ctrl+C om te stoppen[/dim]\n"
        )

        while self.is_awake:
            now = time.time()
            self.pulse_count += 1

            for task in self.schedule:
                last_run = self.last_check.get(
                    task["name"], 0
                )
                if now - last_run > task["interval"]:
                    self.last_check[task["name"]] = now
                    await self.run_task(task)

            # Heartbeat indicator
            ts = datetime.now().strftime("%H:%M:%S")
            console.print(
                f"[dim]♥ {ts}"
                f" | pulse #{self.pulse_count}"
                f"[/dim]",
                end="\r",
            )

            await asyncio.sleep(5)


# ── ENTRY POINT ──

def main():
    """Start de Heartbeat Daemon."""
    brain = _laad_brain()
    daemon = HeartbeatDaemon(brain=brain)

    try:
        asyncio.run(daemon.pulse())
    except KeyboardInterrupt:
        try:
            from danny_toolkit.brain.cortical_stack import (
                get_cortical_stack,
            )
            get_cortical_stack().flush()
        except Exception as e:
            logger.debug("CorticalStack flush on shutdown failed: %s", e)
        console.print(
            "\n[red]Daemon gestopt.[/red]"
        )


if __name__ == "__main__":
    main()

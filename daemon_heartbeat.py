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
import atexit
import io
import logging
import os
import signal
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

try:
    from danny_toolkit.core.shadow_airlock import ShadowAirlock
    HAS_AIRLOCK = True
except ImportError:
    HAS_AIRLOCK = False


# ── CLEAN SHUTDOWN ──

def _flush_cortical():
    """Flush CorticalStack bij shutdown (atexit/signal)."""
    try:
        from danny_toolkit.brain.cortical_stack import (
            get_cortical_stack,
        )
        get_cortical_stack().flush()
    except Exception as e:
        logger.debug(
            "CorticalStack flush bij shutdown: %s", e,
        )

atexit.register(_flush_cortical)


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

        # Circuit breaker per taak
        self._task_failures: dict = {}
        self._CIRCUIT_BREAKER_THRESHOLD = 3
        self._CIRCUIT_BREAKER_COOL_CYCLES = 12
        self._task_skip_until: dict = {}

        # Shadow Airlock — periodieke staging scan
        self._airlock = ShadowAirlock() if HAS_AIRLOCK else None
        self._airlock_interval = 60  # seconden
        self._airlock_last_run = 0.0

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

    def _schrijf_heartbeat(self):
        """Schrijf heartbeat status naar bestand voor externe monitors."""
        try:
            from danny_toolkit.core.config import Config
            hb_path = os.path.join(
                Config.DATA_DIR, "daemon_heartbeat.txt",
            )
            os.makedirs(os.path.dirname(hb_path), exist_ok=True)
            with open(hb_path, "w", encoding="utf-8") as f:
                f.write(
                    f"ts={datetime.now().isoformat()}\n"
                    f"pulse={self.pulse_count}\n"
                    f"taken={len(self.schedule)}\n"
                )
        except Exception as e:
            logger.debug("Heartbeat schrijven mislukt: %s", e)

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
                name = task["name"]

                # Circuit breaker: skip als in cooldown
                skip_until = self._task_skip_until.get(
                    name, 0,
                )
                if self.pulse_count < skip_until:
                    continue

                last_run = self.last_check.get(name, 0)
                if now - last_run > task["interval"]:
                    self.last_check[name] = now
                    try:
                        await self.run_task(task)
                        # Reset failures bij succes
                        self._task_failures[name] = 0
                    except Exception as e:
                        # Tel fout op
                        count = self._task_failures.get(
                            name, 0,
                        ) + 1
                        self._task_failures[name] = count
                        logger.warning(
                            "Daemon taak %s crash #%d: %s",
                            name, count, e,
                        )
                        console.print(
                            f"[red]  ⚠ {name} crash"
                            f" #{count}: {e}[/red]"
                        )
                        # Log naar CorticalStack
                        try:
                            from danny_toolkit.brain.cortical_stack import (
                                get_cortical_stack,
                            )
                            get_cortical_stack().log_event(
                                actor="daemon",
                                action="task_crash",
                                details={
                                    "task": name,
                                    "error": str(e)[:200],
                                    "count": count,
                                },
                            )
                        except Exception as e:
                            logger.debug("CorticalStack crash log: %s", e)
                        # Threshold: circuit breaker open
                        if count >= self._CIRCUIT_BREAKER_THRESHOLD:
                            self._task_skip_until[name] = (
                                self.pulse_count
                                + self._CIRCUIT_BREAKER_COOL_CYCLES
                            )
                            console.print(
                                f"[bold red]  ⛔ {name}"
                                f" uitgeschakeld voor"
                                f" {self._CIRCUIT_BREAKER_COOL_CYCLES}"
                                f" cycli[/bold red]"
                            )
                            try:
                                from danny_toolkit.core.alerter import (
                                    get_alerter, AlertLevel,
                                )
                                get_alerter().fire(
                                    AlertLevel.KRITIEK,
                                    f"Daemon taak {name}"
                                    f" circuit breaker open"
                                    f" na {count} crashes",
                                )
                            except ImportError:
                                pass

            # Shadow Airlock — periodieke staging scan
            if self._airlock:
                now_airlock = time.time()
                if now_airlock - self._airlock_last_run > self._airlock_interval:
                    self._airlock_last_run = now_airlock
                    try:
                        resultaat = self._airlock.scan_en_verwerk()
                        if resultaat["bestanden"] > 0:
                            console.print(
                                f"[cyan]🔒 Airlock:"
                                f" {resultaat['gepromoveerd']} gepromoveerd,"
                                f" {resultaat['quarantaine']} quarantaine[/cyan]"
                            )
                    except Exception as e:
                        logger.debug("Airlock scan fout: %s", e)

            # Heartbeat indicator + bestand
            self._schrijf_heartbeat()
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
    # Signal handlers voor clean shutdown
    def _signal_handler(signum, frame):
        _flush_cortical()
        sys.exit(0)

    signal.signal(signal.SIGTERM, _signal_handler)
    if hasattr(signal, "SIGBREAK"):
        signal.signal(signal.SIGBREAK, _signal_handler)

    # Startup validatie (Phase 26)
    try:
        from danny_toolkit.core.startup_validator import valideer_opstart
        valideer_opstart()
    except ImportError:
        pass

    brain = _laad_brain()
    daemon = HeartbeatDaemon(brain=brain)

    try:
        asyncio.run(daemon.pulse())
    except KeyboardInterrupt:
        _flush_cortical()
        console.print(
            "\n[red]Daemon gestopt.[/red]"
        )
    except Exception as e:
        _flush_cortical()
        logger.exception(
            "Daemon onverwacht gestopt: %s", e,
        )
        console.print(
            f"\n[bold red]Daemon crash: {e}[/bold red]"
        )
        sys.exit(1)


if __name__ == "__main__":
    main()

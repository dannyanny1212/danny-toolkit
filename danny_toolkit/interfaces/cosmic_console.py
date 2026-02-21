"""
COSMIC CONSOLE V6 — Nexus Terminal
====================================

Async terminal interface voor Project Omega.
Rich-powered met live spinner, smart payload
rendering en Glass Box transparantie.

V6 versie: gebruikt danny_toolkit package imports.

Features:
  - Async SwarmEngine met live spinner
  - Smart payload rendering per type
  - Governor health status bij boot
  - RAG ingest wizard (/ingest)
  - Chain of Command modus (/chain)
  - Agent status grid (/status)

Gebruik: python -m danny_toolkit.interfaces.cosmic_console
"""

import asyncio
import sys
import os
import io
import time
from contextlib import redirect_stdout
from pathlib import Path

# Root toevoegen aan path
_root = Path(__file__).parent.parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

# Windows UTF-8 fix
if os.name == "nt":
    if hasattr(sys.stdin, "reconfigure"):
        sys.stdin.reconfigure(encoding="utf-8")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.table import Table
from rich.prompt import Prompt
from rich.live import Live
from rich.spinner import Spinner

# --- V6 IMPORTS ---
from danny_toolkit.core.engine import (
    SwarmEngine, SwarmPayload,
)
from danny_toolkit.skills.librarian import (
    TheLibrarian,
)
from danny_toolkit.brain.trinity_omega import (
    PrometheusBrain, NodeTier,
)
from config import DOCS_DIR
from swarm_core import run_chain_pipeline

console = Console()

BANNER = """
    \u2554\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2557
    \u2551  PROJECT OMEGA  //  NEXUS TERMINAL v6.0              \u2551
    \u2551  [bold cyan]System Online[/bold cyan]   [bold green]Swarm Active[/bold green]   [bold magenta]Memory Mounted[/bold magenta]   \u2551
    \u255a\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u255d"""

HELP_TEXT = """[bold cyan]Commando's:[/bold cyan]
  [bold]/help[/bold]     Toon dit overzicht
  [bold]/status[/bold]   Governor health + agent grid
  [bold]/boot[/bold]     Toon boot log opnieuw
  [bold]/chain[/bold]    Toggle Chain of Command modus
  [bold]/ingest[/bold]   RAG ingest wizard
  [bold]/clear[/bold]    Scherm wissen
  [bold]exit[/bold]      Afsluiten"""

AGENT_COLORS = {
    "Cipher": "green",
    "The Legion": "red",
    "Memex": "magenta",
    "Iolaax": "yellow",
    "Pixel": "cyan",
    "Weaver": "blue",
    "Nexus": "bold cyan",
    "Vita": "green",
    "Echo": "dim white",
    "Spark": "bright_magenta",
    "Oracle": "bright_cyan",
    "Sentinel": "red",
    "The Governor": "green",
    "Chronos": "yellow",
    "Navigator": "blue",
    "Alchemist": "dim cyan",
    "Void": "dim white",
}


# --- GOVERNOR & BOOT ---

def show_governor_status(brain):
    """Toon compacte Governor health status."""
    try:
        report = brain.governor.get_health_report()
        cb = report.get("circuit_breaker", {})
        cb_status = cb.get("status", "?")
        cb_fails = cb.get("failures", 0)
        cb_max = cb.get("max", 3)
        learn = report.get("learning", {})
        cycles = learn.get("cycles_this_hour", 0)
        max_cycles = learn.get("max_per_hour", 20)
        state_files = report.get("state_files", {})
        healthy = sum(
            1 for v in state_files.values() if v
        )
        total_sf = len(state_files)

        if cb_status == "CLOSED":
            cb_color = "green"
        elif cb_status == "HALF_OPEN":
            cb_color = "yellow"
        else:
            cb_color = "red"

        console.print(
            f"  [dim]Governor:[/dim]"
            f" CB [{cb_color}]{cb_status}"
            f"[/{cb_color}]"
            f" ({cb_fails}/{cb_max})"
            f" | Learning {cycles}/{max_cycles}/h"
            f" | State {healthy}/{total_sf} OK"
        )
    except Exception:
        console.print(
            "  [dim]Governor: status niet"
            " beschikbaar[/dim]"
        )


def show_boot_log(boot_log):
    """Toon boot log in een dim panel."""
    if boot_log.strip():
        console.print(Panel(
            boot_log.strip(),
            title="[dim]Boot Log[/dim]",
            border_style="dim",
        ))


def show_status(brain):
    """Toon Governor health + agent grid per tier."""
    show_governor_status(brain)
    console.print()

    tier_names = {
        NodeTier.TRINITY: "TRINITY (God Tier)",
        NodeTier.GUARDIANS: "GUARDIANS (Root Tier)",
        NodeTier.SPECIALISTS:
            "SPECIALISTS (User Tier)",
        NodeTier.INFRASTRUCTURE:
            "INFRA (Infra Tier)",
    }

    for tier in NodeTier:
        tier_nodes = [
            node for node in brain.nodes.values()
            if node.tier == tier
        ]
        if not tier_nodes:
            continue

        table = Table(
            title=tier_names.get(tier, str(tier)),
            border_style="cyan",
            show_lines=False,
        )
        table.add_column(
            "Agent", style="bold white",
        )
        table.add_column("Status", width=10)
        table.add_column(
            "Energy", justify="right", width=8,
        )
        table.add_column(
            "Tasks", justify="right", width=6,
        )

        for node in tier_nodes:
            if node.status == "ACTIVE":
                s = "[green]ACTIVE[/green]"
            elif node.status == "DORMANT":
                s = "[dim]DORMANT[/dim]"
            else:
                s = f"[yellow]{node.status}[/yellow]"

            e = node.energy
            if e >= 70:
                e_s = f"[green]{e}%[/green]"
            elif e >= 30:
                e_s = f"[yellow]{e}%[/yellow]"
            else:
                e_s = f"[red]{e}%[/red]"

            table.add_row(
                node.name, s, e_s,
                str(node.tasks_completed),
            )

        console.print(table)
        console.print()


# --- PAYLOAD RENDERING ---

def render_payload(p, elapsed=0.0):
    """Render een SwarmPayload naar de console."""
    color = AGENT_COLORS.get(p.agent, "white")
    console.print(
        f"\n[bold {color}]> {p.agent}"
        f"[/bold {color}]"
        f" [dim]({elapsed:.2f}s)[/dim]"
    )

    if p.type == "research_report":
        console.print(Markdown(str(p.display_text)))
        data = p.content
        if isinstance(data, dict):
            queries = ", ".join(
                f"[cyan]{q}[/cyan]"
                for q in data.get("queries", [])
            )
            sources = data.get("sources_list", [])
            source_lines = ""
            if sources:
                source_lines = (
                    "\n[bold]Bronnen:[/bold]\n"
                    + "\n".join(
                        f"  {s}" for s in sources
                    )
                )
            fallback = ""
            if data.get("is_fallback") or data.get(
                "used_web"
            ):
                fallback = (
                    "\n\n[bold yellow]"
                    "WEB FALLBACK GEBRUIKT"
                    "[/bold yellow]"
                )
            info = (
                f"[bold]Strategie:[/bold]"
                f" {queries}"
                f"{source_lines}{fallback}"
            )
            console.print(Panel(
                info,
                title="Onderzoeksdata",
                border_style="dim white",
                expand=False,
            ))

    elif p.type == "code":
        console.print(
            Markdown(str(p.display_text))
        )
        code = p.content
        if isinstance(code, str) and code.strip():
            syntax = Syntax(
                code, "python",
                theme="monokai",
                line_numbers=True,
            )
            console.print(syntax)

    elif p.type == "metrics":
        console.print(
            Markdown(str(p.display_text))
        )
        data = p.content
        if isinstance(data, dict):
            table = Table(
                show_header=True,
                header_style="bold green",
            )
            table.add_column("Metric")
            table.add_column("Waarde")
            for k, v in data.items():
                table.add_row(str(k), str(v))
            console.print(table)
        if "media" in (p.metadata or {}):
            media = p.metadata["media"]
            metrics = media.get("metrics", [])
            if metrics:
                table = Table(
                    title="Market Ticker",
                    border_style="cyan",
                )
                table.add_column(
                    "Asset", style="bold white",
                )
                table.add_column(
                    "Value", style="yellow",
                )
                table.add_column(
                    "Delta", justify="right",
                )
                for item in metrics:
                    delta = str(
                        item.get("delta", "")
                    )
                    if "+" in delta:
                        d = (
                            f"[green]{delta}"
                            f"[/green]"
                        )
                    elif "-" in delta:
                        d = f"[red]{delta}[/red]"
                    else:
                        d = f"[dim]{delta}[/dim]"
                    table.add_row(
                        item.get("label", ""),
                        str(item.get("value", "")),
                        d,
                    )
                console.print(table)

    elif p.type == "image_analysis":
        content = p.content or {}
        img_path = ""
        if isinstance(content, dict):
            img_path = content.get(
                "image_path", ""
            )
        if img_path:
            console.print(
                f"[dim]Afbeelding:"
                f" {img_path}[/dim]"
            )
        console.print(
            Markdown(str(p.display_text))
        )

    elif p.type in (
        "area_chart", "bar_chart", "line_chart",
    ):
        console.print(
            Markdown(str(p.display_text))
        )
        if "media" in (p.metadata or {}):
            console.print(
                "[dim]Chart data beschikbaar"
                " (gebruik Sanctuary UI voor"
                " visualisatie)[/dim]"
            )

    else:
        console.print(
            Markdown(str(p.display_text))
        )


def render_chain_result(chain_result):
    """Render chain pipeline resultaat."""
    if not isinstance(chain_result, dict):
        console.print(Panel(
            "[red]Chain pipeline gaf geen"
            " geldig resultaat[/red]",
            title="CHAIN REPORT",
            border_style="red",
        ))
        return

    nodes = chain_result.get(
        "nodes_betrokken", []
    ) or []
    keten = " \u2192 ".join(
        str(n) for n in nodes
    )
    antwoord = str(
        chain_result.get(
            "antwoord", "Geen antwoord"
        )
    )
    success = chain_result.get(
        "success_count", 0
    )
    total = len(
        chain_result.get("sub_taken", []) or []
    )

    console.print(Panel(
        Markdown(antwoord),
        title="CHAIN REPORT",
        subtitle=(
            f"[bold]{keten}[/bold]"
            f" | {success}/{total} geslaagd"
        ),
        border_style="yellow",
    ))


# --- COSMIC CONSOLE ---

class CosmicConsole:
    """Async terminal interface voor Project Omega."""

    def __init__(self):
        self.brain = None
        self.boot_log = ""
        self.engine = None
        self.chain_mode = False

    def _load_brain(self):
        """Laad PrometheusBrain met boot capture."""
        console.print(
            "[dim]Federation wordt gewekt...[/dim]"
        )
        buf = io.StringIO()
        with redirect_stdout(buf):
            self.brain = PrometheusBrain()
        self.boot_log = buf.getvalue()
        self.engine = SwarmEngine(self.brain)

    def print_banner(self):
        """Toon header banner."""
        console.clear()
        console.print(Panel(
            BANNER,
            style="bold blue",
            border_style="blue",
        ))

    async def ingest_wizard(self):
        """RAG ingest wizard."""
        try:
            path = Prompt.ask(
                "Pad naar map om te leren",
                default=str(DOCS_DIR),
            )
        except EOFError:
            return

        with console.status(
            "[bold green]Kennis"
            " absorberen...[/bold green]"
        ):
            lib = TheLibrarian()
            await asyncio.to_thread(
                lib.ingest, pad=path,
            )

        count = lib.collection.count()
        console.print(
            f"[bold green]Ingest compleet!"
            f" ({count} chunks in DB)[/bold green]"
        )

    async def start(self):
        """Hoofdloop van de console."""
        self.print_banner()

        try:
            self._load_brain()
        except Exception as e:
            console.print(
                f"[red]Fout bij laden Federation:"
                f" {e}[/red]"
            )
            sys.exit(1)

        show_boot_log(self.boot_log)
        show_governor_status(self.brain)
        console.print(
            "[green]Federation ONLINE[/green]\n"
        )
        console.print(
            "[dim]Type '/help' voor commando's"
            " of begin gewoon te praten...[/dim]"
        )

        try:
            while True:
                mode = (
                    "[yellow]CHAIN[/yellow]"
                    if self.chain_mode
                    else "[cyan]OMEGA[/cyan]"
                )

                try:
                    user_input = Prompt.ask(
                        f"\n{mode}"
                        " [bold white]>[/bold white]"
                    )
                except EOFError:
                    console.print(
                        "\n[red]Shutting down"
                        " (EOF)...[/red]"
                    )
                    break

                cmd = user_input.strip().lower()

                if cmd in ("exit", "quit", "q"):
                    console.print(
                        "[red]Shutting down"
                        " systems...[/red]"
                    )
                    break
                if cmd == "/help":
                    console.print(HELP_TEXT)
                    continue
                if cmd == "/clear":
                    self.print_banner()
                    continue
                if cmd == "/status":
                    show_status(self.brain)
                    continue
                if cmd == "/boot":
                    show_boot_log(self.boot_log)
                    continue
                if cmd == "/chain":
                    self.chain_mode = (
                        not self.chain_mode
                    )
                    status = (
                        "AAN"
                        if self.chain_mode
                        else "UIT"
                    )
                    console.print(
                        f"[yellow]Chain of Command:"
                        f" {status}[/yellow]"
                    )
                    continue
                if cmd == "/ingest":
                    await self.ingest_wizard()
                    continue
                if not cmd:
                    continue

                # --- EXECUTIE ---
                try:
                    t0 = time.time()

                    if self.chain_mode:
                        with Live(
                            Spinner(
                                "dots",
                                text=(
                                    "[yellow]Chain"
                                    " processing..."
                                    "[/yellow]"
                                ),
                                style="yellow",
                            ),
                            refresh_per_second=10,
                            transient=True,
                        ):
                            chain_result = (
                                await asyncio.to_thread(
                                    run_chain_pipeline,
                                    user_input,
                                    self.brain,
                                )
                            )

                        elapsed = (
                            time.time() - t0
                        )
                        console.print(
                            f"[dim]({elapsed:.2f}s)"
                            f"[/dim]"
                        )
                        render_chain_result(
                            chain_result
                        )

                    else:
                        with Live(
                            Spinner(
                                "dots",
                                text=(
                                    "[cyan]Nexus"
                                    " routing..."
                                    "[/cyan]"
                                ),
                                style="cyan",
                            ),
                            refresh_per_second=10,
                            transient=True,
                        ):
                            payloads = (
                                await self.engine.run(
                                    user_input,
                                )
                            )

                        elapsed = (
                            time.time() - t0
                        )
                        for p in payloads:
                            render_payload(
                                p, elapsed,
                            )

                except Exception as e:
                    console.print(
                        f"[bold red]SYSTEM ERROR:"
                        f"[/bold red] {e}"
                    )

        except KeyboardInterrupt:
            console.print(
                "\n[red]Shutting down...[/red]"
            )


if __name__ == "__main__":
    cli = CosmicConsole()
    asyncio.run(cli.start())

"""
NEXUS TERMINAL v2.0 — Cosmic Console CLI
==========================================

Terminal-gebaseerde Mission Control voor de Prometheus
Federation. Async SwarmEngine met Ctrl+C handling,
Governor status en slash commands.

Features:
  - Ctrl+C stopt generatie, niet het programma
  - Governor status (groen/geel/rood)
  - Slash commands: /status, /clear, /help, /boot
  - Rijke UI met panels voor code en tekst
  - Chain of Command modus (/chain)

Gebruik: python danny_toolkit/interfaces/cli.py
"""

import os

# Forceer TQDM en HuggingFace om stil te zijn
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["TQDM_DISABLE"] = "True"
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"

import sys
import io
import asyncio
import time
from contextlib import redirect_stdout
from pathlib import Path

# --- 1. WINDOWS & SILENT FIXES ---
sys.stdout = io.TextIOWrapper(
    sys.stdout.buffer, encoding="utf-8"
)
sys.stderr = io.TextIOWrapper(
    sys.stderr.buffer, encoding="utf-8"
)

import warnings
import logging

warnings.filterwarnings("ignore")
logging.getLogger("transformers").setLevel(
    logging.ERROR
)
logging.getLogger("sentence_transformers").setLevel(
    logging.ERROR
)

# --- 2. SETUP PATHS ---
ROOT_DIR = Path(__file__).parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# --- 3. IMPORTS ---
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.live import Live
from rich.spinner import Spinner

try:
    from danny_toolkit.core.engine import (
        SwarmEngine,
    )
    from danny_toolkit.brain.trinity_omega import (
        PrometheusBrain, NodeTier,
    )
    from swarm_core import run_chain_pipeline
except ImportError as e:
    print(f"CRITICAL Import Error: {e}")
    sys.exit(1)

console = Console()


class CosmicConsole:
    """Async terminal interface voor Project Omega."""

    def __init__(self):
        self.brain = None
        self.engine = None
        self.boot_log = ""
        self.chain_mode = False
        self.session_active = True

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

    def _get_governor_label(self):
        """Geeft governor status als kleur-label."""
        try:
            report = (
                self.brain.governor.get_health_report()
            )
            cb = report.get("circuit_breaker", {})
            status = cb.get("status", "?")
            if status == "CLOSED":
                return "[green]SECURE[/green]"
            elif status == "HALF_OPEN":
                return "[yellow]CAUTION[/yellow]"
            else:
                return "[red]LIMIT REACHED[/red]"
        except Exception:
            return "[dim]UNKNOWN[/dim]"

    def _render_header(self):
        """Toont de HUD (Heads Up Display)."""
        gov = self._get_governor_label()

        grid = Table.grid(expand=True)
        grid.add_column(justify="left", ratio=1)
        grid.add_column(justify="right", ratio=1)

        grid.add_row(
            "[bold cyan]PROJECT OMEGA //"
            " NEXUS TERMINAL v2.0[/bold cyan]",
            f"Governor: {gov}"
            "   Brain: [bold]ONLINE[/bold]",
        )
        console.print(Panel(
            grid,
            style="bold white",
            border_style="cyan",
        ))

    def _handle_command(self, cmd):
        """Verwerkt slash commando's."""
        cmd = cmd.lower().strip()

        if cmd in ("/quit", "/exit"):
            self.session_active = False
            console.print(
                "[yellow]Shutting down"
                " system...[/yellow]"
            )
            return True

        elif cmd == "/clear":
            console.clear()
            self._render_header()
            return True

        elif cmd == "/status":
            self._show_status()
            return True

        elif cmd == "/help":
            console.print(
                "[dim]Commando's:"
                " /status, /clear, /chain,"
                " /boot, /quit[/dim]"
            )
            return True

        elif cmd == "/boot":
            if self.boot_log.strip():
                console.print(Panel(
                    self.boot_log.strip(),
                    title="[dim]Boot Log[/dim]",
                    border_style="dim",
                ))
            else:
                console.print(
                    "[dim]Geen boot log"
                    " beschikbaar[/dim]"
                )
            return True

        elif cmd == "/chain":
            self.chain_mode = not self.chain_mode
            status = (
                "AAN" if self.chain_mode else "UIT"
            )
            console.print(
                f"[yellow]Chain of Command:"
                f" {status}[/yellow]"
            )
            return True

        return False

    def _show_status(self):
        """Toon Governor health + agent grid."""
        try:
            report = (
                self.brain.governor.get_health_report()
            )
            cb = report.get("circuit_breaker", {})
            learn = report.get("learning", {})
            sf = report.get("state_files", {})
            healthy = sum(
                1 for v in sf.values() if v
            )

            table = Table(title="System Status")
            table.add_column("Component")
            table.add_column("State")

            table.add_row(
                "Engine", "Running",
            )
            table.add_row(
                "Governor CB",
                cb.get("status", "?"),
            )
            table.add_row(
                "Failures",
                f"{cb.get('failures', 0)}"
                f"/{cb.get('max', 3)}",
            )
            table.add_row(
                "Learning",
                f"{learn.get('cycles_this_hour', 0)}"
                f"/{learn.get('max_per_hour', 20)}/h",
            )
            table.add_row(
                "State Files",
                f"{healthy}/{len(sf)} OK",
            )
            console.print(table)
        except Exception as e:
            console.print(
                f"[red]Status fout: {e}[/red]"
            )

        # Agent grid per tier
        console.print()
        for tier in NodeTier:
            nodes = [
                n for n in self.brain.nodes.values()
                if n.tier == tier
            ]
            if not nodes:
                continue

            table = Table(
                title=tier.name,
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

            for node in nodes:
                if node.status == "ACTIVE":
                    s = "[green]ACTIVE[/green]"
                elif node.status == "DORMANT":
                    s = "[dim]DORMANT[/dim]"
                else:
                    s = (
                        f"[yellow]{node.status}"
                        f"[/yellow]"
                    )

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

    def _render_payload(self, p, elapsed=0.0):
        """Render een SwarmPayload naar de console."""
        console.print(
            f"\n[bold]> {p.agent}[/bold]"
            f" [dim]({elapsed:.2f}s)[/dim]"
        )

        if p.type == "error":
            console.print(Panel(
                str(p.display_text),
                title="ERROR",
                border_style="red",
            ))

        elif p.type == "code":
            console.print(
                Markdown(str(p.display_text))
            )
            code = p.content
            if isinstance(code, str) and code.strip():
                from rich.syntax import Syntax
                syntax = Syntax(
                    code, "python",
                    theme="monokai",
                    line_numbers=True,
                )
                console.print(syntax)

        elif p.type == "research_report":
            console.print(
                Markdown(str(p.display_text))
            )
            data = p.content
            if isinstance(data, dict):
                queries = data.get("queries", [])
                src = data.get("sources_count", 0)
                if queries or src:
                    q_text = ", ".join(
                        f"[cyan]{q}[/cyan]"
                        for q in queries
                    )
                    console.print(Panel(
                        f"[bold]Strategie:[/bold]"
                        f" {q_text}\n"
                        f"[bold]Bronnen:[/bold]"
                        f" {src} documenten",
                        title="Onderzoeksdata",
                        border_style="dim",
                        expand=False,
                    ))

        else:
            console.print(
                Markdown(str(p.display_text))
            )

        # Metadata (bronnen, execution time)
        meta = p.metadata or {}
        exec_time = meta.get("execution_time", 0)
        sources = meta.get("sources")
        if exec_time or sources:
            info = f"[dim]{exec_time:.2f}s[/dim]"
            if sources:
                info += (
                    f" | [dim]{sources}"
                    f" bronnen[/dim]"
                )
            console.print(info, justify="right")

    def _render_chain_result(self, chain_result):
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

    async def start(self):
        """Hoofdloop van de console."""
        console.clear()

        try:
            self._load_brain()
        except Exception as e:
            console.print(
                f"[red]Fout bij laden Federation:"
                f" {e}[/red]"
            )
            sys.exit(1)

        self._render_header()
        console.print(
            "[dim]Type '/help' voor opties."
            " Druk Ctrl+C om een generatie"
            " te annuleren.[/dim]\n"
        )

        while self.session_active:
            try:
                mode = (
                    "[yellow]CHAIN[/yellow]"
                    if self.chain_mode
                    else "[cyan]OMEGA[/cyan]"
                )

                # 1. INPUT
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

                if not user_input.strip():
                    continue

                # 2. SLASH COMMANDS
                if user_input.startswith("/"):
                    if self._handle_command(user_input):
                        continue

                # Exit zonder slash
                cmd = user_input.strip().lower()
                if cmd in ("exit", "quit", "q"):
                    console.print(
                        "[red]Shutting down...[/red]"
                    )
                    break

                # 3. ENGINE VERWERKING
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

                    elapsed = time.time() - t0
                    console.print(
                        f"[dim]({elapsed:.2f}s)"
                        f"[/dim]"
                    )
                    self._render_chain_result(
                        chain_result
                    )

                else:
                    with Live(
                        Spinner(
                            "dots",
                            text=(
                                "[cyan]Thinking..."
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

                    elapsed = time.time() - t0
                    for p in payloads:
                        self._render_payload(
                            p, elapsed,
                        )

            except KeyboardInterrupt:
                console.print(
                    "\n[bold red]INTERRUPT SIGNAL"
                    " RECEIVED[/bold red]"
                )
                console.print(
                    "[dim]Huidige taak geannuleerd."
                    " Systeem blijft online.[/dim]"
                )
                continue

            except Exception as e:
                console.print(
                    f"[bold red]SYSTEM ERROR:"
                    f"[/bold red] {e}"
                )


if __name__ == "__main__":
    try:
        terminal = CosmicConsole()
        asyncio.run(terminal.start())
    except KeyboardInterrupt:
        print("\nForce Shutdown.")

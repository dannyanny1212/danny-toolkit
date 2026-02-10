"""
SANCTUARY CLI — The Glass Box Terminal v4.0
============================================

Terminal-gebaseerde Mission Control voor de Prometheus
Federation. Rich-powered ASCII visualisaties van dezelfde
backend als sanctuary_ui.py.

Features:
  - Live pipeline log (Rich Live panel)
  - Cipher Market Ticker (ASCII tabel)
  - DataFrame → ASCII bar charts
  - Syntax-highlighted code blocks
  - Markdown-formatted Weaver output

Gebruik: python cli.py
"""

import sys
import time
import os
import io
from contextlib import redirect_stdout

# Windows UTF-8 fix voor Unicode box-drawing chars
if os.name == "nt":
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

from rich.console import Console
from rich.panel import Panel
from rich.live import Live
from rich.table import Table
from rich.markdown import Markdown
from rich.text import Text
from rich.prompt import Prompt

# Backend imports
from swarm_engine import run_swarm_sync, SwarmPayload
from swarm_core import run_chain_pipeline
from danny_toolkit.brain.trinity_omega import (
    PrometheusBrain,
)

# --- CONFIGURATIE ---
console = Console()

HEADER = """
 ╔═══════════════════════════════════════════════════╗
 ║  S A N C T U A R Y  //  N E X U S  C L I  v4.0  ║
 ╚═══════════════════════════════════════════════════╝"""


def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def print_header():
    console.print(f"[bold cyan]{HEADER}[/bold cyan]")
    console.print(
        "[dim]System: ONLINE | Governor: ACTIVE"
        " | Chronos: 2026[/dim]",
        justify="center",
    )
    console.print()


# --- BRAIN LADEN ---

def laad_brain():
    """Laad PrometheusBrain (boot output onderdrukt)."""
    console.print(
        "[dim]Federation wordt gewekt...[/dim]"
    )
    buf = io.StringIO()
    with redirect_stdout(buf):
        brain = PrometheusBrain()
    return brain, buf.getvalue()


# --- VISUALISATIE FUNCTIES ---

def render_metrics(media):
    """Zet Cipher metrics om in een terminal tabel."""
    table = Table(
        title="Cipher Market Ticker",
        border_style="cyan",
    )
    table.add_column("Asset", style="bold white")
    table.add_column("Value", style="yellow")
    table.add_column(
        "Delta (24h)", justify="right",
    )

    for item in media.get("metrics", []):
        delta = str(item.get("delta", ""))
        delta_color = item.get("delta_color", "normal")

        if delta_color == "off":
            delta_str = f"[grey62]{delta}[/grey62]"
        elif "+" in delta:
            delta_str = (
                f"[green]{delta}[/green] [green]▲[/green]"
            )
        elif "-" in delta:
            delta_str = (
                f"[red]{delta}[/red] [red]▼[/red]"
            )
        else:
            delta_str = f"[grey62]{delta}[/grey62]"

        table.add_row(
            item["label"],
            str(item["value"]),
            delta_str,
        )

    return table


def render_chart_ascii(df, title=None):
    """Render DataFrame als ASCII bar chart.

    Args:
        df: pandas DataFrame met numerieke kolommen.
        title: Optionele titel boven de chart.

    Returns:
        String met ASCII bar representatie.
    """
    if df is None or df.empty:
        return "[dim]Geen data beschikbaar[/dim]"

    max_width = 40
    lines = []

    if title:
        lines.append(f"[bold cyan]{title}[/bold cyan]")
        lines.append("")

    for col in df.columns:
        lines.append(f"  [bold]{col}[/bold]")
        values = df[col].values
        if len(values) == 0:
            continue

        vmin = float(min(values))
        vmax = float(max(values))
        span = vmax - vmin if vmax != vmin else 1

        # Max 15 rijen voor leesbaarheid
        step = max(1, len(values) // 15)
        for i in range(0, len(values), step):
            val = float(values[i])
            bar_len = int(
                (val - vmin) / span * max_width
            )
            bar = "\u2588" * max(1, bar_len)
            label = str(df.index[i])[-8:]
            lines.append(
                f"  [grey62]{label:>8}[/grey62]"
                f" \u2502 [blue]{bar}[/blue]"
                f" {val:.1f}"
            )
        lines.append("")

    return "\n".join(lines)


def render_media(media):
    """Render rich media in de terminal.

    Dispatcht op media["type"]:
      metrics   → tabel + ASCII charts
      area/line/bar_chart → ASCII chart
      code      → syntax highlighted panel
    """
    if not media:
        return

    media_type = media.get("type")

    if media_type == "metrics":
        console.print(render_metrics(media))
        # 30d prijs chart
        if "data" in media:
            console.print(Panel(
                render_chart_ascii(
                    media["data"], "30D Prijs"
                ),
                border_style="cyan",
            ))
        # Volume chart
        if "extra" in media:
            console.print(Panel(
                render_chart_ascii(
                    media["extra"], "Volume"
                ),
                border_style="blue",
            ))

    elif media_type in (
        "line_chart", "area_chart", "bar_chart",
    ):
        console.print(Panel(
            render_chart_ascii(media.get("data")),
            title="Data Chart",
            border_style="cyan",
        ))

    elif media_type == "code":
        code = media.get("code", "")
        from rich.syntax import Syntax
        syntax = Syntax(
            code, "python",
            theme="monokai",
            line_numbers=True,
        )
        console.print(Panel(
            syntax,
            title="Code Snippet",
            border_style="green",
        ))


# --- DE CLI LOOP ---

def main():
    clear_screen()
    print_header()

    brain, boot_log = laad_brain()
    console.print(
        "[green]Federation ONLINE[/green]\n"
    )
    console.print(
        "[dim]Typ 'exit' om te stoppen  |"
        "  'chain' voor Chain of Command modus[/dim]"
    )

    chain_mode = False

    while True:
        # Modus indicator
        mode_label = (
            "[yellow]CHAIN[/yellow]"
            if chain_mode
            else "[cyan]HUB&SPOKE[/cyan]"
        )

        user_input = Prompt.ask(
            f"\n{mode_label} [bold green]>[/bold green]"
        )

        # Commando's
        cmd = user_input.strip().lower()
        if cmd in ("exit", "quit", "q"):
            console.print(
                "[red]Shutting down...[/red]"
            )
            break
        if cmd == "chain":
            chain_mode = not chain_mode
            status = "AAN" if chain_mode else "UIT"
            console.print(
                f"[yellow]Chain of Command:"
                f" {status}[/yellow]"
            )
            continue
        if cmd == "clear":
            clear_screen()
            print_header()
            continue
        if not cmd:
            continue

        console.print()

        # --- LIVE PIPELINE ---
        log_content = Text()

        def update_cli_log(message):
            ts = time.strftime("%H:%M:%S")

            if "Nexus" in message:
                style = "bold cyan"
            elif "Governor" in message:
                style = "green"
            elif "Weaver" in message:
                style = "magenta"
            elif "Chronos" in message:
                style = "yellow"
            elif "COMPLETE" in message:
                style = "bold green"
            elif "BLOCKED" in message:
                style = "bold red"
            else:
                style = "white"

            log_content.append(
                f"[{ts}] {message}\n",
                style=style,
            )

        panel = Panel(
            log_content,
            title="SWARM ACTIVITY",
            border_style="blue",
        )

        with Live(
            panel,
            refresh_per_second=4,
            console=console,
        ) as live:

            def live_callback(msg):
                update_cli_log(msg)
                live.update(Panel(
                    log_content,
                    title="SWARM ACTIVITY",
                    border_style="blue",
                ))

            if chain_mode:
                chain_result = run_chain_pipeline(
                    user_input, brain,
                    callback=live_callback,
                )
            else:
                payloads = run_swarm_sync(
                    user_input, brain,
                    callback=live_callback,
                )

        # --- OUTPUT RENDERING ---
        console.print()

        if chain_mode:
            # Chain of Command output
            nodes = chain_result.get(
                "nodes_betrokken", []
            )
            keten = " \u2192 ".join(nodes)
            antwoord = str(
                chain_result.get(
                    "antwoord", "Geen antwoord"
                )
            )
            success = chain_result.get(
                "success_count", 0
            )
            total = len(
                chain_result.get("sub_taken", [])
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

        else:
            # Swarm Engine per-payload rendering
            agents = [p.agent for p in payloads]
            assigned = " \u2192 ".join(agents)
            status = f"{len(payloads)} agent(s)"
            header = (
                f"[bold]{assigned}[/bold]"
                f" | {status}"
            )

            for p in payloads:
                if p.type == "code":
                    # Code block met syntax highlighting
                    from rich.syntax import Syntax
                    syntax = Syntax(
                        str(p.content), "python",
                        theme="monokai",
                        line_numbers=True,
                    )
                    console.print(Panel(
                        syntax,
                        title=(
                            f"\U0001f4bb {p.agent}"
                        ),
                        border_style="green",
                    ))
                elif p.type == "metrics":
                    # Tekst + media tickers/charts
                    console.print(Panel(
                        Markdown(
                            str(p.display_text)
                        ),
                        title=(
                            f"\U0001f4c8 {p.agent}"
                        ),
                        border_style="cyan",
                    ))
                    if "media" in p.metadata:
                        render_media(
                            p.metadata["media"]
                        )
                elif p.type in (
                    "area_chart", "bar_chart",
                ):
                    console.print(Panel(
                        Markdown(
                            str(p.display_text)
                        ),
                        title=(
                            f"\U0001f4ca {p.agent}"
                        ),
                        border_style="cyan",
                    ))
                    if "media" in p.metadata:
                        render_media(
                            p.metadata["media"]
                        )
                else:
                    console.print(Panel(
                        Markdown(
                            str(p.display_text)
                        ),
                        title=(
                            f"{p.agent}"
                        ),
                        subtitle=header,
                        border_style="magenta",
                    ))


if __name__ == "__main__":
    main()

"""
SANCTUARY CLI — The Glass Box Terminal v5.0
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
  - Governor health status bij boot
  - Commando's: status, boot, chain, clear

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
    PrometheusBrain, NodeTier,
)

# --- CONFIGURATIE ---
console = Console()

HEADER = """
 ╔═══════════════════════════════════════════════════╗
 ║  S A N C T U A R Y  //  N E X U S  C L I  v5.0  ║
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


# --- GOVERNOR STATUS ---

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
            f" CB [{cb_color}]{cb_status}[/{cb_color}]"
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


# --- COMMANDO: STATUS ---

def show_status(brain):
    """Toon Governor health + agent grid per tier."""
    show_governor_status(brain)
    console.print()

    tier_names = {
        NodeTier.TRINITY: "TRINITY (God Tier)",
        NodeTier.GUARDIANS: "GUARDIANS (Root Tier)",
        NodeTier.SPECIALISTS: "SPECIALISTS (User Tier)",
        NodeTier.INFRASTRUCTURE: "INFRA (Infra Tier)",
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
        table.add_column("Agent", style="bold white")
        table.add_column("Status", width=10)
        table.add_column(
            "Energy", justify="right", width=8,
        )
        table.add_column(
            "Tasks", justify="right", width=6,
        )

        for node in tier_nodes:
            if node.status == "ACTIVE":
                s_style = "[green]ACTIVE[/green]"
            elif node.status == "DORMANT":
                s_style = "[dim]DORMANT[/dim]"
            else:
                s_style = f"[yellow]{node.status}[/yellow]"

            energy = node.energy
            if energy >= 70:
                e_style = f"[green]{energy}%[/green]"
            elif energy >= 30:
                e_style = f"[yellow]{energy}%[/yellow]"
            else:
                e_style = f"[red]{energy}%[/red]"

            table.add_row(
                node.name,
                s_style,
                e_style,
                str(node.tasks_completed),
            )

        console.print(table)
        console.print()


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
                f"[green]{delta}[/green] [green]\u25b2[/green]"
            )
        elif "-" in delta:
            delta_str = (
                f"[red]{delta}[/red] [red]\u25bc[/red]"
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


# --- PAYLOAD RENDERING (geextraheerd) ---

def render_payload(p, header=""):
    """Render een SwarmPayload naar de console.

    Args:
        p: SwarmPayload object.
        header: Optionele subtitle string.
    """
    if p.type == "code":
        from rich.syntax import Syntax
        syntax = Syntax(
            str(p.content), "python",
            theme="monokai",
            line_numbers=True,
        )
        console.print(Panel(
            syntax,
            title=f"\U0001f4bb {p.agent}",
            border_style="green",
        ))

    elif p.type == "metrics":
        console.print(Panel(
            Markdown(str(p.display_text)),
            title=f"\U0001f4c8 {p.agent}",
            border_style="cyan",
        ))
        if "media" in p.metadata:
            render_media(p.metadata["media"])

    elif p.type in (
        "area_chart", "bar_chart", "line_chart",
    ):
        console.print(Panel(
            Markdown(str(p.display_text)),
            title=f"\U0001f4ca {p.agent}",
            border_style="cyan",
        ))
        if "media" in p.metadata:
            render_media(p.metadata["media"])

    elif p.type == "image_analysis":
        content = p.content or {}
        img_path = ""
        if isinstance(content, dict):
            img_path = content.get("image_path", "")
        console.print(Panel(
            Markdown(str(p.display_text)),
            title=f"\U0001f5bc {p.agent} | Vision",
            subtitle=(
                f"[dim]{img_path}[/dim]"
                if img_path else None
            ),
            border_style="blue",
        ))

    elif p.type == "research_report":
        console.print(Panel(
            Markdown(str(p.display_text)),
            title=(
                f"\U0001f4da {p.agent}"
                " | The Archivist"
            ),
            border_style="yellow",
        ))
        data = p.content
        if isinstance(data, dict):
            queries = data.get("queries", [])
            src = data.get("sources_count", 0)
            q_lines = "\n".join(
                f"  \U0001f50d {q}"
                for q in queries
            )
            console.print(Panel(
                (
                    "[bold]Zoekstrategie"
                    ":[/bold]\n"
                    f"{q_lines}\n\n"
                    "[bold]Bronnen:"
                    f"[/bold] {src}"
                    " documenten\n"
                    "[dim]Geverifieerd"
                    " via CorticalStack"
                    "[/dim]"
                ),
                title=(
                    "\U0001f50d"
                    " Onderzoeksdata"
                ),
                border_style="dim yellow",
            ))

    else:
        console.print(Panel(
            Markdown(str(p.display_text)),
            title=f"{p.agent}",
            subtitle=header,
            border_style="magenta",
        ))


def render_chain_result(chain_result):
    """Render chain pipeline resultaat naar console.

    Args:
        chain_result: Dict of None van run_chain_pipeline.
    """
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


# --- DE CLI LOOP ---

def main():
    clear_screen()
    print_header()

    # 1.2: Exception handling brain loading
    try:
        brain, boot_log = laad_brain()
    except Exception as e:
        console.print(
            f"[red]Fout bij laden Federation:"
            f" {e}[/red]"
        )
        sys.exit(1)

    # 2.1: Boot log panel
    show_boot_log(boot_log)

    # 2.4: Governor status bij boot
    show_governor_status(brain)

    console.print(
        "[green]Federation ONLINE[/green]\n"
    )
    console.print(
        "[dim]Commando's: exit | chain | clear"
        " | status | boot[/dim]"
    )

    chain_mode = False

    # 1.1: KeyboardInterrupt handling
    try:
        while True:
            mode_label = (
                "[yellow]CHAIN[/yellow]"
                if chain_mode
                else "[cyan]HUB&SPOKE[/cyan]"
            )

            # 1.5: EOFError handling bij Prompt.ask()
            try:
                user_input = Prompt.ask(
                    f"\n{mode_label}"
                    " [bold green]>[/bold green]"
                )
            except EOFError:
                console.print(
                    "\n[red]Shutting down"
                    " (EOF)...[/red]"
                )
                break

            # Commando's
            cmd = user_input.strip().lower()
            if cmd in ("exit", "quit", "q"):
                console.print(
                    "[red]Shutting down...[/red]"
                )
                break
            if cmd == "chain":
                chain_mode = not chain_mode
                status = (
                    "AAN" if chain_mode else "UIT"
                )
                console.print(
                    f"[yellow]Chain of Command:"
                    f" {status}[/yellow]"
                )
                continue
            if cmd == "clear":
                clear_screen()
                print_header()
                continue
            # 2.5: Commando status
            if cmd == "status":
                show_status(brain)
                continue
            # 2.6: Commando boot
            if cmd == "boot":
                show_boot_log(boot_log)
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

            # 1.3: Exception handling executie
            try:
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
                        chain_result = (
                            run_chain_pipeline(
                                user_input, brain,
                                callback=live_callback,
                            )
                        )
                    else:
                        payloads = run_swarm_sync(
                            user_input, brain,
                            callback=live_callback,
                        )

            except Exception as e:
                console.print(Panel(
                    f"[red]Fout tijdens executie:"
                    f" {e}[/red]",
                    title="ERROR",
                    border_style="red",
                ))
                continue

            # --- OUTPUT RENDERING ---
            console.print()

            if chain_mode:
                # 1.4 + 3.2: Chain result validatie
                render_chain_result(chain_result)
            else:
                # 3.1: Payload rendering
                agents = [
                    p.agent for p in payloads
                ]
                assigned = " \u2192 ".join(agents)
                status = (
                    f"{len(payloads)} agent(s)"
                )
                header = (
                    f"[bold]{assigned}[/bold]"
                    f" | {status}"
                )

                for p in payloads:
                    render_payload(p, header)

    except KeyboardInterrupt:
        console.print(
            "\n[red]Shutting down...[/red]"
        )


if __name__ == "__main__":
    main()

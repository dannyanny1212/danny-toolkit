"""
Zesde Zintuig — Omega Sovereign Neural Monitor (Textual TUI)

Interactive command center voor real-time inzicht in het zenuwstelsel
van het Omega ecosysteem. 3-panel layout: Vitals | Neural Stream | Intelligence.

Phase 53 — Gebouwd door WEAVER + IOLAAX agents.
"""
from __future__ import annotations

import sys
import os
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional

# Windows UTF-8
try:
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    logger.debug("Suppressed error")

# ── Textual imports ──────────────────────────────────────────────
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Header, Footer, Static, RichLog, Input, Label
from textual.reactive import reactive
from textual import work

# ── Omega singletons (lazy, graceful degradation) ───────────────
def _safe_import(factory_path: str, factory_name: str) -> Any:
    """Import a singleton factory, return None on failure."""
    try:
        mod = __import__(factory_path, fromlist=[factory_name])
        return getattr(mod, factory_name, None)
    except (ImportError, Exception):
        return None


def _get_singleton(factory_path: str, factory_name: str) -> Any:
    """Call a singleton factory, return None on failure."""
    factory = _safe_import(factory_path, factory_name)
    if factory is None:
        return None
    try:
        return factory()
    except Exception:
        return None


# ── Hardware helpers ─────────────────────────────────────────────
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

try:
    from danny_toolkit.core.vram_manager import vram_rapport
    HAS_VRAM = True
except ImportError:
    HAS_VRAM = False
    def vram_rapport() -> dict:
        """Vram rapport."""
        return {"beschikbaar": False}


# ── Progress bar helper ─────────────────────────────────────────
def _bar(pct: float, width: int = 15) -> str:
    """Render a percentage as a Unicode bar: ████░░░░ 62%."""
    filled = int(pct / 100 * width)
    empty = width - filled
    if pct >= 90:
        color = "red"
    elif pct >= 70:
        color = "yellow"
    else:
        color = "green"
    bar = "█" * filled + "░" * empty
    return f"[{color}]{bar}[/] {pct:5.1f}%"


# ── Tri-Color event styling ─────────────────────────────────────
_EVENT_COLORS = {
    "HEALTH": "green",
    "MOOD": "green",
    "SYSTEM": "cyan",
    "WEATHER": "cyan",
    "AGENDA": "cyan",
    "ERROR": "red",
    "HALLUCINATION": "red",
    "IMMUNE": "yellow",
    "FORGE": "yellow",
    "SANDBOX": "yellow",
    "SYNAPSE": "magenta",
    "PHANTOM": "magenta",
    "WAAKHUIS": "blue",
    "CONFIG": "blue",
    "PRUNING": "blue",
    "SHARD": "blue",
    "TWIN": "magenta",
    "LEARNING": "cyan",
    "KNOWLEDGE": "cyan",
    "RESOURCE": "yellow",
    "MISSION": "green",
    "STEP": "green",
    "AGENT": "yellow",
    "REQUEST": "blue",
}


def _event_color(event_type: str) -> str:
    """Return Rich color tag for an event type."""
    for prefix, color in _EVENT_COLORS.items():
        if event_type.upper().startswith(prefix):
            return color
    return "white"


# ═══════════════════════════════════════════════════════════════
#  VITALS PANEL — Hardware + Immuunsysteem
# ═══════════════════════════════════════════════════════════════
class VitalsPanel(Static):
    """Left panel: hardware bars, shield stats, agent health."""

    DEFAULT_CSS = """
    VitalsPanel {
        width: 1fr;
        min-width: 30;
        height: 100%;
        border: solid green;
        padding: 0 1;
    }
    """

    def on_mount(self) -> None:
        """On mount."""
        self.set_interval(2.0, self._refresh_vitals)
        self._refresh_vitals()

    def _refresh_vitals(self) -> None:
        """Refresh vitals."""
        lines: List[str] = []
        lines.append("[bold cyan]═══ VITALS ═══[/]\n")

        # ── Hardware ──
        lines.append("[bold]HARDWARE[/]")
        if HAS_PSUTIL:
            cpu = psutil.cpu_percent(interval=0)
            mem = psutil.virtual_memory()
            lines.append(f"  CPU:  {_bar(cpu)}")
            lines.append(f"  RAM:  {_bar(mem.percent)}")
        else:
            lines.append("  [dim]psutil unavailable[/]")

        vram = vram_rapport()
        if vram.get("beschikbaar"):
            totaal = vram.get("totaal_mb", 0)
            gebruik = vram.get("in_gebruik_mb", 0)
            pct = (gebruik / totaal * 100) if totaal > 0 else 0
            lines.append(f"  VRAM: {_bar(pct)}")
            lines.append(f"         {gebruik}/{totaal} MB")
        else:
            lines.append("  VRAM: [dim]not available[/]")

        # ── Shield stats ──
        lines.append("")
        lines.append("[bold]HALLUCINATION SHIELD[/]")
        schild = _get_singleton(
            "danny_toolkit.brain.hallucination_shield",
            "get_hallucination_shield",
        )
        if schild:
            try:
                s = schild.get_stats()
                total = s.get("beoordeeld", 0)
                blocked = s.get("geblokkeerd", 0)
                rate = ((total - blocked) / total * 100) if total > 0 else 100
                lines.append(f"  Checked:  {total}")
                lines.append(f"  Blocked:  [red]{blocked}[/]")
                lines.append(f"  Pass:     [green]{rate:.1f}%[/]")
            except Exception:
                lines.append("  [dim]stats error[/]")
        else:
            lines.append("  [dim]not loaded[/]")

        # ── BlackBox immunity ──
        lines.append("")
        lines.append("[bold]IMMUNE SYSTEM[/]")
        bb = _get_singleton("danny_toolkit.brain.black_box", "get_black_box")
        if bb:
            try:
                bs = bb.get_stats()
                lines.append(f"  Antibodies: {bs.get('active_antibodies', 0)}")
                lines.append(f"  Failures:   {bs.get('recorded_failures', 0)}")
                sev = bs.get("by_severity", {})
                if sev:
                    parts = [f"{k}:{v}" for k, v in sev.items() if v > 0]
                    if parts:
                        lines.append(f"  Severity:   {', '.join(parts)}")
            except Exception:
                lines.append("  [dim]stats error[/]")
        else:
            lines.append("  [dim]not loaded[/]")

        # ── Waakhuis health ──
        lines.append("")
        lines.append("[bold]WAAKHUIS[/]")
        waakhuis = _get_singleton(
            "danny_toolkit.brain.waakhuis", "get_waakhuis"
        )
        if waakhuis:
            try:
                rapport = waakhuis.gezondheidsrapport()
                sys_info = rapport.get("systeem", {})
                lines.append(
                    f"  Dispatches: {sys_info.get('totaal_dispatches', 0)}"
                )
                lines.append(f"  Errors:     {sys_info.get('totaal_fouten', 0)}")
                agents_info = rapport.get("agents", {})
                if agents_info:
                    scores = [
                        v.get("score", 0) for v in agents_info.values()
                    ]
                    avg = sum(scores) / len(scores) if scores else 0
                    lines.append(f"  Avg Health: {avg:.0f}/100")
            except Exception:
                lines.append("  [dim]rapport error[/]")
        else:
            lines.append("  [dim]not loaded[/]")

        # ── NeuralBus stats ──
        lines.append("")
        lines.append("[bold]NEURAL BUS[/]")
        bus = _get_singleton("danny_toolkit.core.neural_bus", "get_bus")
        if bus:
            try:
                bs = bus.statistieken()
                lines.append(f"  Published: {bs.get('events_gepubliceerd', 0)}")
                lines.append(f"  Delivered: {bs.get('events_afgeleverd', 0)}")
                lines.append(f"  Errors:    {bs.get('fouten', 0)}")
            except Exception:
                lines.append("  [dim]stats error[/]")
        else:
            lines.append("  [dim]not loaded[/]")

        self.update("\n".join(lines))


# ═══════════════════════════════════════════════════════════════
#  NEURAL STREAM PANEL — Live NeuralBus feed
# ═══════════════════════════════════════════════════════════════
class NeuralStreamPanel(RichLog):
    """Center panel: scrolling live NeuralBus event stream."""

    DEFAULT_CSS = """
    NeuralStreamPanel {
        width: 2fr;
        min-width: 40;
        height: 100%;
        border: solid cyan;
    }
    """

    def __init__(self, **kwargs: Any) -> None:
        """Init  ."""
        super().__init__(highlight=True, markup=True, wrap=True, **kwargs)
        self._subscribed = False

    def on_mount(self) -> None:
        """On mount."""
        self.write("[bold cyan]═══ NEURAL STREAM ═══[/]\n")
        self._subscribe_bus()
        # Load recent history
        self._load_history()

    def _subscribe_bus(self) -> None:
        """Subscribe to all NeuralBus events."""
        if self._subscribed:
            return
        bus = _get_singleton("danny_toolkit.core.neural_bus", "get_bus")
        if bus:
            try:
                bus.subscribe("*", self._on_bus_event)
                self._subscribed = True
                self.write("[green]Connected to NeuralBus[/]")
            except Exception as e:
                self.write(f"[red]Bus subscribe error: {e}[/]")
        else:
            self.write("[dim]NeuralBus not available[/]")

    def _load_history(self) -> None:
        """Load recent bus context on startup."""
        bus = _get_singleton("danny_toolkit.core.neural_bus", "get_bus")
        if bus:
            try:
                stream = bus.get_context_stream(count=15)
                if stream:
                    self.write("[dim]── recent history ──[/]")
                    for line in stream.strip().split("\n"):
                        if line.strip():
                            self.write(f"[dim]{line}[/]")
                    self.write("[dim]── live feed ──[/]\n")
            except Exception:
                logger.debug("Suppressed error")

    def _on_bus_event(self, event: Any) -> None:
        """Handle incoming NeuralBus event (called from any thread)."""
        try:
            ts = datetime.now().strftime("%H:%M:%S")
            etype = getattr(event, "event_type", str(event))
            bron = getattr(event, "bron", "?")
            data = getattr(event, "data", {})
            color = _event_color(etype)

            # Truncate data for display
            data_str = str(data)
            if len(data_str) > 120:
                data_str = data_str[:117] + "..."

            line = (
                f"[dim]{ts}[/] [{color}]{etype}[/] "
                f"[dim]({bron})[/] {data_str}"
            )
            # Thread-safe write via call_from_thread
            self.app.call_from_thread(self.write, line)
        except Exception:
            logger.debug("Suppressed error")


# ═══════════════════════════════════════════════════════════════
#  INTELLIGENCE PANEL — Predictions & Knowledge
# ═══════════════════════════════════════════════════════════════
class IntelligencePanel(Static):
    """Right panel: Phantom predictions, Synapse pathways, Cortex stats."""

    DEFAULT_CSS = """
    IntelligencePanel {
        width: 1fr;
        min-width: 30;
        height: 100%;
        border: solid magenta;
        padding: 0 1;
    }
    """

    def on_mount(self) -> None:
        """On mount."""
        self.set_interval(5.0, self._refresh_intelligence)
        self._refresh_intelligence()

    def _refresh_intelligence(self) -> None:
        """Refresh intelligence."""
        lines: List[str] = []
        lines.append("[bold magenta]═══ INTELLIGENCE ═══[/]\n")

        # ── Phantom predictions ──
        lines.append("[bold]PHANTOM PREDICTIONS[/]")
        phantom = _get_singleton("danny_toolkit.brain.phantom", "get_phantom")
        if phantom:
            try:
                preds = phantom.get_predictions(max_results=5)
                if preds:
                    for p in preds:
                        cat = p.get("category", "?")
                        conf = p.get("confidence", 0) * 100
                        lines.append(f"  {cat:20s} {conf:5.1f}%")
                else:
                    lines.append("  [dim]no predictions[/]")

                acc = phantom.get_accuracy()
                if acc.get("total_predictions", 0) > 0:
                    lines.append(
                        f"  [dim]Accuracy: "
                        f"{acc.get('accuracy', 0) * 100:.1f}% "
                        f"({acc.get('hits', 0)}/{acc.get('total_predictions', 0)})[/]"
                    )
            except Exception:
                lines.append("  [dim]error[/]")
        else:
            lines.append("  [dim]not loaded[/]")

        # ── Synapse pathways ──
        lines.append("")
        lines.append("[bold]SYNAPSE TOP ROUTES[/]")
        synapse = _get_singleton("danny_toolkit.brain.synapse", "get_synapse")
        if synapse:
            try:
                pathways = synapse.get_top_pathways(limit=8)
                if pathways:
                    for pw in pathways:
                        cat = pw.get("category", "?")
                        agent = pw.get("agent", "?")
                        strength = pw.get("strength", 0)
                        fires = pw.get("fires", 0)
                        lines.append(
                            f"  {cat[:10]}→{agent[:10]:10s} "
                            f"[green]{strength:.2f}[/] ({fires}x)"
                        )
                else:
                    lines.append("  [dim]no pathways[/]")

                ss = synapse.get_stats()
                lines.append(
                    f"  [dim]Total: {ss.get('pathways', 0)} pathways, "
                    f"{ss.get('interactions', 0)} interactions[/]"
                )
            except Exception:
                lines.append("  [dim]error[/]")
        else:
            lines.append("  [dim]not loaded[/]")

        # ── Cortex graph ──
        lines.append("")
        lines.append("[bold]CORTEX KNOWLEDGE GRAPH[/]")
        cortex = _get_singleton("danny_toolkit.brain.cortex", "get_cortex")
        if cortex:
            try:
                cs = cortex.get_stats()
                lines.append(f"  Nodes:   {cs.get('graph_nodes', 0)}")
                lines.append(f"  Edges:   {cs.get('graph_edges', 0)}")
                lines.append(f"  Triples: {cs.get('db_triples', 0)}")
            except Exception:
                lines.append("  [dim]error[/]")
        else:
            lines.append("  [dim]not loaded[/]")

        # ── CorticalStack ──
        lines.append("")
        lines.append("[bold]CORTICAL STACK[/]")
        cs = _get_singleton(
            "danny_toolkit.brain.cortical_stack", "get_cortical_stack"
        )
        if cs:
            try:
                recent = cs.get_recent_events(count=3)
                lines.append(f"  Recent events: {len(recent)}")
                for ev in recent[:3]:
                    actor = ev.get("actor", "?")
                    action = ev.get("action", "?")
                    lines.append(f"  [dim]{actor}: {action[:30]}[/]")
            except Exception:
                lines.append("  [dim]error[/]")
        else:
            lines.append("  [dim]not loaded[/]")

        self.update("\n".join(lines))


# ═══════════════════════════════════════════════════════════════
#  COMMAND BAR — Interactive commands
# ═══════════════════════════════════════════════════════════════
class CommandBar(Input):
    """Bottom bar: interactive command input."""

    DEFAULT_CSS = """
    CommandBar {
        dock: bottom;
        height: 3;
        border: solid green;
    }
    """

    def __init__(self, **kwargs: Any) -> None:
        """Init  ."""
        super().__init__(
            placeholder="flush | backup | antibodies | predict | scan | agents | quit",
            **kwargs,
        )


# ═══════════════════════════════════════════════════════════════
#  MAIN APP — Zesde Zintuig
# ═══════════════════════════════════════════════════════════════
class ZesdeZintuigApp(App):
    """Omega Sovereign Neural Monitor — Textual TUI."""

    TITLE = "ZESDE ZINTUIG — Omega Sovereign Neural Monitor"
    SUB_TITLE = "Phase 53 | Real-time Ecosystem Intelligence"

    CSS = """
    Screen {
        layout: vertical;
    }

    #main-panels {
        height: 1fr;
    }

    #status-bar {
        dock: bottom;
        height: 1;
        background: $surface;
        color: $text-muted;
        padding: 0 1;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("f", "cmd_flush", "Flush"),
        ("b", "cmd_backup", "Backup"),
        ("s", "cmd_scan", "Scan"),
        ("a", "cmd_antibodies", "Antibodies"),
        ("p", "cmd_predict", "Predict"),
        ("r", "cmd_refresh", "Refresh"),
    ]

    def compose(self) -> ComposeResult:
        """Compose."""
        yield Header()
        with Horizontal(id="main-panels"):
            yield VitalsPanel()
            yield NeuralStreamPanel()
            yield IntelligencePanel()
        yield CommandBar()
        yield Label(
            "[dim]Keys: [q]uit [f]lush [b]ackup [s]can [a]ntibodies [p]redict [r]efresh[/]",
            id="status-bar",
        )
        yield Footer()

    def on_mount(self) -> None:
        """On mount."""
        self._log_stream("ZESDE ZINTUIG online — monitoring active")

    # ── Command input handler ─────────────────────────────────
    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle command bar input."""
        cmd = event.value.strip().lower()
        event.input.value = ""

        if cmd in ("quit", "exit", "q"):
            self.exit()
        elif cmd == "flush":
            self.action_cmd_flush()
        elif cmd == "backup":
            self.action_cmd_backup()
        elif cmd == "antibodies":
            self.action_cmd_antibodies()
        elif cmd == "predict":
            self.action_cmd_predict()
        elif cmd == "scan":
            self.action_cmd_scan()
        elif cmd == "agents":
            self.action_cmd_agents()
        elif cmd == "refresh":
            self.action_cmd_refresh()
        elif cmd == "help":
            self._log_stream(
                "[bold]Commands:[/] flush, backup, antibodies, predict, "
                "scan, agents, refresh, quit"
            )
        else:
            self._log_stream(f"[yellow]Unknown command: {cmd}[/]")

    # ── Actions ───────────────────────────────────────────────
    def action_cmd_flush(self) -> None:
        """Flush CorticalStack to disk."""
        cs = _get_singleton(
            "danny_toolkit.brain.cortical_stack", "get_cortical_stack"
        )
        if cs:
            try:
                cs.flush()
                self._log_stream("[green]CorticalStack flushed[/]")
            except Exception as e:
                self._log_stream(f"[red]Flush error: {e}[/]")
        else:
            self._log_stream("[dim]CorticalStack not available[/]")

    def action_cmd_backup(self) -> None:
        """Backup CorticalStack."""
        cs = _get_singleton(
            "danny_toolkit.brain.cortical_stack", "get_cortical_stack"
        )
        if cs:
            try:
                path = cs.backup(compress=True)
                self._log_stream(f"[green]Backup created: {path}[/]")
            except Exception as e:
                self._log_stream(f"[red]Backup error: {e}[/]")
        else:
            self._log_stream("[dim]CorticalStack not available[/]")

    def action_cmd_antibodies(self) -> None:
        """Show BlackBox antibodies."""
        bb = _get_singleton("danny_toolkit.brain.black_box", "get_black_box")
        if bb:
            try:
                antibodies = bb.get_antibodies()
                if antibodies:
                    self._log_stream(
                        f"[bold yellow]═══ ANTIBODIES ({len(antibodies)}) ═══[/]"
                    )
                    for ab in antibodies[:10]:
                        sig = ab.get("signature", "?")[:40]
                        sev = ab.get("severity", "?")
                        strength = ab.get("strength", 0)
                        enc = ab.get("encounters", 0)
                        color = (
                            "red" if sev == "CRITICAL"
                            else "yellow" if sev == "SEVERE"
                            else "white"
                        )
                        self._log_stream(
                            f"  [{color}]{sev:8s}[/] {sig} "
                            f"[dim](str={strength:.2f}, enc={enc})[/]"
                        )
                else:
                    self._log_stream("[dim]No active antibodies[/]")
            except Exception as e:
                self._log_stream(f"[red]Antibodies error: {e}[/]")
        else:
            self._log_stream("[dim]BlackBox not available[/]")

    def action_cmd_predict(self) -> None:
        """Show Phantom predictions + accuracy."""
        phantom = _get_singleton("danny_toolkit.brain.phantom", "get_phantom")
        if phantom:
            try:
                preds = phantom.get_predictions(max_results=10)
                acc = phantom.get_accuracy()
                self._log_stream("[bold magenta]═══ PHANTOM PREDICTIONS ═══[/]")
                if preds:
                    for p in preds:
                        cat = p.get("category", "?")
                        conf = p.get("confidence", 0) * 100
                        basis = p.get("basis", "?")
                        self._log_stream(
                            f"  {cat:25s} {conf:5.1f}% [dim]({basis})[/]"
                        )
                else:
                    self._log_stream("  [dim]No predictions[/]")
                total = acc.get("total_predictions", 0)
                if total > 0:
                    self._log_stream(
                        f"  [dim]Overall accuracy: "
                        f"{acc.get('accuracy', 0) * 100:.1f}% "
                        f"({acc.get('hits', 0)}/{total})[/]"
                    )
            except Exception as e:
                self._log_stream(f"[red]Predict error: {e}[/]")
        else:
            self._log_stream("[dim]Phantom not available[/]")

    def action_cmd_scan(self) -> None:
        """Run OmegaCore system scan."""
        self._log_stream("[yellow]Running system scan...[/]")
        self._run_scan()

    @work(thread=True)
    def _run_scan(self) -> None:
        """Run scan in background thread."""
        try:
            core = OmegaCore()
            result = core.system_scan()
            lines = [
                "[bold cyan]═══ SYSTEM SCAN ═══[/]",
                f"  Modules: {result.get('active_modules', '?')}/{result.get('total_modules', '?')}",
                f"  Health:  {result.get('health_score', '?')}",
                f"  Wirings: {result.get('wirings', '?')}",
            ]
            security = result.get("security", {})
            if security:
                sec_score = security.get("security_score", "?")
                lines.append(f"  Security: {sec_score}")
            tiers = result.get("tiers", {})
            for tier_key in sorted(tiers.keys()):
                tier_modules = tiers[tier_key]
                if isinstance(tier_modules, list):
                    lines.append(
                        f"  {tier_key}: {len(tier_modules)} modules"
                    )
            for line in lines:
                self.app.call_from_thread(self._log_stream, line)
        except Exception as e:
            self.app.call_from_thread(
                self._log_stream, f"[red]Scan error: {e}[/]"
            )

    def action_cmd_agents(self) -> None:
        """Show agent health from Waakhuis."""
        waakhuis = _get_singleton(
            "danny_toolkit.brain.waakhuis", "get_waakhuis"
        )
        if waakhuis:
            try:
                rapport = waakhuis.gezondheidsrapport()
                agents = rapport.get("agents", {})
                self._log_stream(
                    f"[bold blue]═══ AGENTS ({len(agents)}) ═══[/]"
                )
                for name, info in sorted(agents.items()):
                    score = info.get("score", 0)
                    color = (
                        "green" if score >= 80
                        else "yellow" if score >= 50
                        else "red"
                    )
                    latency = info.get("latency", {})
                    p50 = latency.get("p50", 0)
                    self._log_stream(
                        f"  [{color}]{score:5.0f}[/] {name:20s} "
                        f"[dim]p50={p50:.0f}ms[/]"
                    )
                stale = waakhuis.check_heartbeats()
                if stale:
                    self._log_stream(
                        f"  [red]Stale: {', '.join(stale)}[/]"
                    )
            except Exception as e:
                self._log_stream(f"[red]Agents error: {e}[/]")
        else:
            self._log_stream("[dim]Waakhuis not available[/]")

    def action_cmd_refresh(self) -> None:
        """Force refresh all panels."""
        try:
            self.query_one(VitalsPanel)._refresh_vitals()
            self.query_one(IntelligencePanel)._refresh_intelligence()
            self._log_stream("[green]All panels refreshed[/]")
        except Exception:
            logger.debug("Suppressed error")

    # ── Log helper ────────────────────────────────────────────
    def _log_stream(self, text: str) -> None:
        """Write a line to the NeuralStream panel."""
        try:
            stream = self.query_one(NeuralStreamPanel)
            ts = datetime.now().strftime("%H:%M:%S")
            stream.write(f"[dim]{ts}[/] {text}")
        except Exception:
            logger.debug("Suppressed error")
import logging

try:
    from danny_toolkit.brain.omega_core import OmegaCore
except ImportError:
    logger.debug("Optional import not available: danny_toolkit.brain.omega_core")

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
#  ENTRY POINT
# ═══════════════════════════════════════════════════════════════
def main() -> None:
    """Launch the Zesde Zintuig TUI."""
    app = ZesdeZintuigApp()
    app.run()


if __name__ == "__main__":
    main()
